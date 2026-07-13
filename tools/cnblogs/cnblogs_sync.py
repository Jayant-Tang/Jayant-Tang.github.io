from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from cnblogs_common import (
    as_list,
    build_article_url,
    compute_source_hash,
    create_or_update_article,
    ensure_blog_id,
    extract_remote_post_id,
    extract_remote_post_url,
    load_config_from_env,
    load_index,
    load_markdown_post,
    make_mapping_record,
    match_remote_posts_by_title,
    relative_posix_path,
    save_index,
    update_index_record,
    write_mapping_to_front_matter,
    dump_markdown_post,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Hexo markdown posts to cnblogs")
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace root used to resolve relative post paths and index path",
    )
    parser.add_argument(
        "--index",
        default=".cnblogs/posts-index.json",
        help="Mapping index JSON path, relative to workspace root",
    )
    parser.add_argument(
        "--changed-file-list",
        help="Optional newline-delimited file that lists changed markdown paths",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=[],
        help="Markdown files to sync, relative to workspace root",
    )
    parser.add_argument(
        "--publish",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Publish posts immediately instead of saving drafts",
    )
    parser.add_argument(
        "--write-back",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write cnblogs mapping back to front matter and index file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force publish even when source hash is unchanged",
    )
    parser.add_argument(
        "--fail-on-conflict",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Exit non-zero when multiple remote posts match the same title",
    )
    return parser.parse_args()


def collect_input_files(args: argparse.Namespace, workspace_root: Path) -> list[Path]:
    file_set: list[str] = []
    file_set.extend(args.files)

    if args.changed_file_list:
        changed_file_list_path = workspace_root / args.changed_file_list
        if changed_file_list_path.exists():
            lines = changed_file_list_path.read_text(encoding="utf-8").splitlines()
            file_set.extend(lines)

    normalized: list[Path] = []
    seen: set[Path] = set()
    for item in file_set:
        if not item:
            continue
        resolved = (workspace_root / item).resolve()
        if resolved.suffix.lower() != ".md":
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        normalized.append(resolved)

    return normalized


def resolve_known_post_id(
    front_matter: dict[str, Any],
    relative_path: str,
    index_data: dict[str, Any],
) -> str:
    cnblogs_meta = front_matter.get("cnblogs") or {}
    if isinstance(cnblogs_meta, dict):
        post_id = cnblogs_meta.get("postId")
        if post_id:
            return str(post_id)

    index_record = index_data.get("posts", {}).get(relative_path, {})
    if isinstance(index_record, dict) and index_record.get("postId"):
        return str(index_record["postId"])

    return ""


def resolve_known_hash(
    front_matter: dict[str, Any],
    relative_path: str,
    index_data: dict[str, Any],
) -> str:
    cnblogs_meta = front_matter.get("cnblogs") or {}
    if isinstance(cnblogs_meta, dict):
        source_hash = cnblogs_meta.get("sourceHash")
        if source_hash:
            return str(source_hash)

    index_record = index_data.get("posts", {}).get(relative_path, {})
    if isinstance(index_record, dict) and index_record.get("sourceHash"):
        return str(index_record["sourceHash"])

    return ""


def resolve_known_url(
    front_matter: dict[str, Any],
    relative_path: str,
    index_data: dict[str, Any],
) -> str:
    cnblogs_meta = front_matter.get("cnblogs") or {}
    if isinstance(cnblogs_meta, dict):
        url = cnblogs_meta.get("url")
        if url:
            return str(url)

    index_record = index_data.get("posts", {}).get(relative_path, {})
    if isinstance(index_record, dict) and index_record.get("url"):
        return str(index_record["url"])

    return ""


def should_skip_cnblogs_publish(front_matter: dict[str, Any]) -> bool:
    if front_matter.get("published") is False:
        return True
    cnblogs_meta = front_matter.get("cnblogs") or {}
    if isinstance(cnblogs_meta, dict) and cnblogs_meta.get("published") is False:
        return True
    return False


def sync_post(
    *,
    post_path: Path,
    workspace_root: Path,
    index_data: dict[str, Any],
    args: argparse.Namespace,
    config: Any,
    remote_posts_cache: dict[str, Any],
) -> tuple[str, str]:
    relative_path = relative_posix_path(post_path, workspace_root)
    front_matter, body = load_markdown_post(post_path)
    title = str(front_matter.get("title", "")).strip()
    if not title:
        raise ValueError(f"{relative_path} is missing front matter field `title`")
    if should_skip_cnblogs_publish(front_matter):
        return "skipped", f"{relative_path}: cnblogs publish disabled"

    source_hash = compute_source_hash(front_matter, body)
    known_hash = resolve_known_hash(front_matter, relative_path, index_data)
    if known_hash == source_hash and not args.force:
        return "skipped", f"{relative_path}: source hash unchanged"

    post_id = resolve_known_post_id(front_matter, relative_path, index_data)
    post_url = resolve_known_url(front_matter, relative_path, index_data)

    if not post_id:
        if remote_posts_cache["posts"] is None:
            from cnblogs_common import list_remote_articles

            remote_posts_cache["posts"] = list_remote_articles(config)
        matches = match_remote_posts_by_title(title, remote_posts_cache["posts"])
        if len(matches) == 1:
            matched = matches[0]
            post_id = extract_remote_post_id(matched)
            post_url = extract_remote_post_url(matched, config.blog_app)
        elif len(matches) > 1:
            details = ", ".join(extract_remote_post_id(item) for item in matches)
            message = f"{relative_path}: found multiple remote posts with title `{title}` -> {details}"
            if args.fail_on_conflict:
                raise RuntimeError(message)
            return "conflict", message

    response = create_or_update_article(
        config,
        title=title,
        body=body,
        tags=as_list(front_matter.get("tags")),
        post_id=post_id or None,
        publish=args.publish,
    )
    response_id = response.get("id") or response.get("postId")
    if not response_id:
        raise RuntimeError(f"{relative_path}: article API response missing id: {response!r}")
    action = "updated" if post_id else "created"
    post_id = str(response_id)
    post_url = str(response.get("url") or response.get("postUrl") or build_article_url(config.blog_app, post_id))

    record = make_mapping_record(
        title=title,
        post_id=post_id,
        url=post_url,
        source_hash=source_hash,
        status="synced",
    )
    update_index_record(index_data, relative_path, record)

    if args.write_back:
        write_mapping_to_front_matter(front_matter, record)
        post_path.write_text(dump_markdown_post(front_matter, body), encoding="utf-8")

    return action, f"{relative_path}: {action} -> {post_url}"


def main() -> int:
    args = parse_args()
    workspace_root = Path(args.workspace_root).resolve()
    index_path = (workspace_root / args.index).resolve()
    input_files = collect_input_files(args, workspace_root)

    if not input_files:
        print("No markdown files to sync.")
        return 0

    config = load_config_from_env()
    index_data = load_index(index_path)
    remote_posts_cache: dict[str, Any] = {"posts": None}
    ensure_blog_id(config)

    results: list[str] = []
    errors: list[str] = []
    synced_count = 0

    for post_path in input_files:
        try:
            action, message = sync_post(
                post_path=post_path,
                workspace_root=workspace_root,
                index_data=index_data,
                args=args,
                config=config,
                remote_posts_cache=remote_posts_cache,
            )
            if action in {"created", "updated"}:
                synced_count += 1
            prefix = "OK" if action not in {"skipped", "conflict"} else action.upper()
            results.append(f"[{prefix}] {message}")
        except Exception as exc:
            errors.append(f"[ERROR] {post_path.name}: {exc}")

    if args.write_back and synced_count > 0:
        save_index(index_path, index_data)

    for line in results:
        print(line)
    for line in errors:
        print(line, file=sys.stderr)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
