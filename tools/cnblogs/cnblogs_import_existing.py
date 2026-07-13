from __future__ import annotations

import argparse
import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from cnblogs_common import (
    compute_source_hash,
    ensure_blog_id,
    extract_remote_post_date,
    extract_remote_post_id,
    extract_remote_post_title,
    extract_remote_post_url,
    load_config_from_env,
    load_index,
    load_markdown_post,
    make_mapping_record,
    match_remote_posts_by_title,
    normalize_title,
    relative_posix_path,
    save_index,
    list_remote_posts,
    write_mapping_to_front_matter,
    dump_markdown_post,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill cnblogs mapping for existing Hexo posts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("scan", "apply"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--workspace-root", default=".")
        subparser.add_argument("--posts-dir", default="source/_posts")
        subparser.add_argument("--index", default=".cnblogs/posts-index.json")
        subparser.add_argument("--candidates", default=".cnblogs/import-candidates.json")

    return parser.parse_args()


def load_local_posts(posts_dir: Path, workspace_root: Path) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for path in sorted(posts_dir.rglob("*.md")):
        front_matter, body = load_markdown_post(path)
        title = str(front_matter.get("title", "")).strip()
        posts.append(
            {
                "path": path,
                "relativePath": relative_posix_path(path, workspace_root),
                "title": title,
                "normalizedTitle": normalize_title(title),
                "date": str(front_matter.get("date", "") or ""),
                "frontMatter": front_matter,
                "body": body,
            }
        )
    return posts


def build_suggestion(local_post: dict[str, Any], remote_post: dict[str, Any], config: Any) -> dict[str, Any] | None:
    remote_title = extract_remote_post_title(remote_post)
    if not remote_title:
        return None

    ratio = SequenceMatcher(
        None,
        local_post["normalizedTitle"],
        normalize_title(remote_title),
    ).ratio()
    same_date = bool(local_post["date"] and extract_remote_post_date(remote_post) and local_post["date"][:10] in str(extract_remote_post_date(remote_post)))

    if ratio < 0.72 and not same_date:
        return None

    return {
        "postId": extract_remote_post_id(remote_post),
        "title": remote_title,
        "url": extract_remote_post_url(remote_post, config.blog_app),
        "date": extract_remote_post_date(remote_post),
        "score": round(ratio, 3),
        "reason": "same_date_and_similar_title" if same_date else "similar_title",
    }


def scan_candidates(args: argparse.Namespace) -> int:
    workspace_root = Path(args.workspace_root).resolve()
    posts_dir = (workspace_root / args.posts_dir).resolve()
    index_path = (workspace_root / args.index).resolve()
    candidates_path = (workspace_root / args.candidates).resolve()

    config = load_config_from_env()
    ensure_blog_id(config)
    local_posts = load_local_posts(posts_dir, workspace_root)
    remote_posts = list_remote_posts(config)
    index_data = load_index(index_path)

    matched_remote_ids: set[str] = set()
    matches: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    unmatched_local: list[dict[str, Any]] = []

    for post in local_posts:
        index_record = index_data.get("posts", {}).get(post["relativePath"], {})
        front_meta = post["frontMatter"].get("cnblogs") or {}
        existing_post_id = ""
        if isinstance(front_meta, dict):
            existing_post_id = str(front_meta.get("postId") or "")
        if not existing_post_id and isinstance(index_record, dict):
            existing_post_id = str(index_record.get("postId") or "")

        if existing_post_id:
            matched_remote_ids.add(existing_post_id)
            continue

        exact_matches = match_remote_posts_by_title(post["title"], remote_posts)
        if len(exact_matches) == 1:
            remote = exact_matches[0]
            remote_id = extract_remote_post_id(remote)
            matched_remote_ids.add(remote_id)
            matches.append(
                {
                    "localPath": post["relativePath"],
                    "localTitle": post["title"],
                    "remotePostId": remote_id,
                    "remoteTitle": extract_remote_post_title(remote),
                    "remoteUrl": extract_remote_post_url(remote, config.blog_app),
                    "remoteDate": extract_remote_post_date(remote),
                    "confidence": "high",
                    "reason": "exact_title",
                    "decision": "accept",
                }
            )
            continue

        if len(exact_matches) > 1:
            conflicts.append(
                {
                    "localPath": post["relativePath"],
                    "localTitle": post["title"],
                    "reason": "multiple_exact_title_matches",
                    "decision": "pending",
                    "selectedPostId": None,
                    "candidates": [
                        {
                            "postId": extract_remote_post_id(item),
                            "title": extract_remote_post_title(item),
                            "url": extract_remote_post_url(item, config.blog_app),
                            "date": extract_remote_post_date(item),
                        }
                        for item in exact_matches
                    ],
                }
            )
            continue

        suggestions = []
        for remote in remote_posts:
            suggestion = build_suggestion(post, remote, config)
            if suggestion is not None:
                suggestions.append(suggestion)
        suggestions.sort(key=lambda item: item["score"], reverse=True)

        unmatched_local.append(
            {
                "localPath": post["relativePath"],
                "localTitle": post["title"],
                "localDate": post["date"],
                "decision": "pending",
                "suggestions": suggestions[:5],
            }
        )

    unmatched_remote = []
    for remote in remote_posts:
        remote_id = extract_remote_post_id(remote)
        if remote_id in matched_remote_ids:
            continue
        unmatched_remote.append(
            {
                "postId": remote_id,
                "title": extract_remote_post_title(remote),
                "url": extract_remote_post_url(remote, config.blog_app),
                "date": extract_remote_post_date(remote),
            }
        )

    payload = {
        "schemaVersion": 1,
        "generatedAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).astimezone().isoformat(timespec="seconds"),
        "blogApp": config.blog_app,
        "summary": {
            "localPostsScanned": len(local_posts),
            "remotePostsScanned": len(remote_posts),
            "matches": len(matches),
            "conflicts": len(conflicts),
            "unmatchedLocal": len(unmatched_local),
            "unmatchedRemote": len(unmatched_remote),
        },
        "matches": matches,
        "conflicts": conflicts,
        "unmatchedLocal": unmatched_local,
        "unmatchedRemote": unmatched_remote,
    }

    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    candidates_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote candidate mapping file to {candidates_path.as_posix()}")
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


def apply_candidates(args: argparse.Namespace) -> int:
    workspace_root = Path(args.workspace_root).resolve()
    index_path = (workspace_root / args.index).resolve()
    candidates_path = (workspace_root / args.candidates).resolve()
    if not candidates_path.exists():
        raise FileNotFoundError(f"Candidate file not found: {candidates_path.as_posix()}")

    payload = json.loads(candidates_path.read_text(encoding="utf-8"))
    index_data = load_index(index_path)
    config = load_config_from_env()
    ensure_blog_id(config)

    accepted: list[dict[str, Any]] = []
    accepted.extend(
        item for item in payload.get("matches", [])
        if item.get("decision") in {"accept", "accepted", "auto_accept"}
    )

    for item in payload.get("conflicts", []):
        if item.get("decision") in {"accept", "accepted"} and item.get("selectedPostId"):
            selected_post_id = str(item["selectedPostId"])
            candidate = next(
                (candidate for candidate in item.get("candidates", []) if str(candidate.get("postId")) == selected_post_id),
                None,
            )
            if candidate is None:
                raise ValueError(
                    f"Conflict entry for {item.get('localPath')} selected unknown postId {selected_post_id}"
                )
            accepted.append(
                {
                    "localPath": item["localPath"],
                    "localTitle": item["localTitle"],
                    "remotePostId": selected_post_id,
                    "remoteTitle": candidate.get("title"),
                    "remoteUrl": candidate.get("url"),
                    "remoteDate": candidate.get("date"),
                    "confidence": "manual",
                    "reason": "manual_conflict_resolution",
                    "decision": "accept",
                }
            )

    for item in payload.get("unmatchedLocal", []):
        if item.get("decision") in {"accept", "accepted"}:
            selected_post_id = str(item.get("selectedPostId") or "")
            suggestions = item.get("suggestions", [])
            candidate = None
            if selected_post_id:
                candidate = next(
                    (entry for entry in suggestions if str(entry.get("postId")) == selected_post_id),
                    None,
                )
            elif len(suggestions) == 1:
                candidate = suggestions[0]

            if candidate is None:
                raise ValueError(
                    f"Unmatched local entry for {item.get('localPath')} is accepted but has no resolvable suggestion"
                )

            accepted.append(
                {
                    "localPath": item["localPath"],
                    "localTitle": item["localTitle"],
                    "remotePostId": str(candidate.get("postId")),
                    "remoteTitle": candidate.get("title"),
                    "remoteUrl": candidate.get("url"),
                    "remoteDate": candidate.get("date"),
                    "confidence": "manual",
                    "reason": "manual_unmatched_resolution",
                    "decision": "accept",
                }
            )

    if not accepted:
        print("No accepted candidate mappings found.")
        return 0

    applied = 0
    for item in accepted:
        local_path = (workspace_root / item["localPath"]).resolve()
        front_matter, body = load_markdown_post(local_path)
        record = make_mapping_record(
            title=str(front_matter.get("title") or item["localTitle"]),
            post_id=str(item["remotePostId"]),
            url=str(item["remoteUrl"] or ""),
            source_hash=compute_source_hash(front_matter, body),
            status="imported",
        )
        if not record["url"]:
            record["url"] = extract_remote_post_url({"postId": record["postId"]}, config.blog_app)

        write_mapping_to_front_matter(front_matter, record)
        local_path.write_text(dump_markdown_post(front_matter, body), encoding="utf-8")
        update_index = index_data.setdefault("posts", {})
        update_index[item["localPath"]] = record
        applied += 1

    save_index(index_path, index_data)
    print(f"Applied {applied} mapping records.")
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "scan":
        return scan_candidates(args)
    if args.command == "apply":
        return apply_candidates(args)
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
