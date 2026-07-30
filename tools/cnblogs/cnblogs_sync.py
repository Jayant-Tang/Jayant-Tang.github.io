from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from cnblogs_common import (
    as_list,
    build_article_url,
    create_or_update_article,
    ensure_blog_id,
    extract_remote_post_id,
    load_config_from_env,
    load_markdown_post,
    make_mapping_record,
    match_remote_posts_by_title,
    relative_posix_path,
    write_mapping_to_front_matter,
    dump_markdown_post,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Hexo markdown posts to cnblogs")
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace root used to resolve relative post paths",
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
        help="Write a new cnblogs mapping back to front matter",
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


def resolve_known_post_id(front_matter: dict[str, Any]) -> str:
    cnblogs_meta = front_matter.get("cnblogs") or {}
    if isinstance(cnblogs_meta, dict):
        post_id = cnblogs_meta.get("postId")
        if post_id:
            return str(post_id)
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

    post_id = resolve_known_post_id(front_matter)
    has_mapping = bool(post_id)

    if not post_id:
        if remote_posts_cache["posts"] is None:
            from cnblogs_common import list_remote_articles

            remote_posts_cache["posts"] = list_remote_articles(config)
        matches = match_remote_posts_by_title(title, remote_posts_cache["posts"])
        if len(matches) == 1:
            matched = matches[0]
            post_id = extract_remote_post_id(matched)
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

    if not has_mapping and args.write_back:
        record = make_mapping_record(post_id=post_id, url=post_url)
        write_mapping_to_front_matter(front_matter, record)
        post_path.write_text(dump_markdown_post(front_matter, body), encoding="utf-8")

    return action, f"{relative_path}: {action} -> {post_url}"


def main() -> int:
    args = parse_args()
    workspace_root = Path(args.workspace_root).resolve()
    input_files = collect_input_files(args, workspace_root)

    if not input_files:
        print("No markdown files to sync.")
        return 0

    config = load_config_from_env()
    remote_posts_cache: dict[str, Any] = {"posts": None}
    ensure_blog_id(config)

    results: list[str] = []
    errors: list[str] = []
    for post_path in input_files:
        try:
            action, message = sync_post(
                post_path=post_path,
                workspace_root=workspace_root,
                args=args,
                config=config,
                remote_posts_cache=remote_posts_cache,
            )
            prefix = "OK" if action not in {"skipped", "conflict"} else action.upper()
            results.append(f"[{prefix}] {message}")
        except Exception as exc:
            errors.append(f"[ERROR] {post_path.name}: {exc}")

    for line in results:
        print(line)
    for line in errors:
        print(line, file=sys.stderr)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
