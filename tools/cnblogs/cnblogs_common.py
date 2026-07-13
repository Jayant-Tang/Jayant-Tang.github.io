from __future__ import annotations

import json
import hashlib
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xmlrpc.client
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


INDEX_SCHEMA_VERSION = 1
FRONT_MATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?", re.DOTALL)


@dataclass
class CnblogsConfig:
    blog_app: str
    username: str
    token: str
    api_url: str
    blog_id: str = ""
    openapi_token: str = ""


ARTICLE_POST_TYPE = 2
ARTICLE_POST_TYPE_NAME = "Article"
BACKEND_BASE_URL = "https://i.cnblogs.com/api"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_config_from_env() -> CnblogsConfig:
    blog_app = os.getenv("CNBLOGS_BLOG_APP", "").strip()
    username = os.getenv("CNBLOGS_USERNAME", "").strip()
    token = os.getenv("CNBLOGS_TOKEN", "").strip()
    blog_id = os.getenv("CNBLOGS_BLOG_ID", "").strip()
    openapi_token = os.getenv("CNBLOGS_OPENAPI_TOKEN", "").strip()
    api_url = os.getenv("CNBLOGS_API_URL", "").strip()

    missing = []
    if not blog_app and not api_url:
        missing.append("CNBLOGS_BLOG_APP or CNBLOGS_API_URL")
    if not username:
        missing.append("CNBLOGS_USERNAME")
    if not token:
        missing.append("CNBLOGS_TOKEN")
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    if not api_url:
        api_url = f"https://rpc.cnblogs.com/metaweblog/{blog_app}"

    return CnblogsConfig(
        blog_app=blog_app,
        username=username,
        token=token,
        api_url=api_url,
        blog_id=blog_id,
        openapi_token=openapi_token,
    )


def get_pat_token(config: CnblogsConfig) -> str:
    token = config.openapi_token.strip() or config.token.strip()
    if not token:
        raise ValueError(
            "Missing PAT token. Set CNBLOGS_OPENAPI_TOKEN to a cnblogs Personal Access Token."
        )
    return token


def load_markdown_post(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(raw)
    if not match:
        return {}, raw

    front_matter_text = match.group(1)
    body = raw[match.end() :]
    front_matter = yaml.safe_load(front_matter_text) or {}
    if not isinstance(front_matter, dict):
        raise ValueError(f"Front matter in {path.as_posix()} must be a YAML object")
    return front_matter, body


def dump_markdown_post(front_matter: dict[str, Any], body: str) -> str:
    front_matter_text = yaml.safe_dump(
        front_matter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()
    normalized_body = body.lstrip("\r\n")
    return f"---\n{front_matter_text}\n---\n\n{normalized_body}"


def ensure_cnblogs_meta(front_matter: dict[str, Any]) -> dict[str, Any]:
    cnblogs_meta = front_matter.get("cnblogs")
    if cnblogs_meta is None:
        cnblogs_meta = {}
        front_matter["cnblogs"] = cnblogs_meta
    if not isinstance(cnblogs_meta, dict):
        raise ValueError("front matter field `cnblogs` must be a mapping")
    return cnblogs_meta


def load_index(index_path: Path) -> dict[str, Any]:
    if not index_path.exists():
        return {
            "schemaVersion": INDEX_SCHEMA_VERSION,
            "generatedAt": None,
            "posts": {},
        }

    data = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Index file {index_path.as_posix()} must contain a JSON object")
    data.setdefault("schemaVersion", INDEX_SCHEMA_VERSION)
    data.setdefault("generatedAt", None)
    data.setdefault("posts", {})
    if not isinstance(data["posts"], dict):
        raise ValueError(f"Index file {index_path.as_posix()} field `posts` must be an object")
    return data


def save_index(index_path: Path, index_data: dict[str, Any]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_data["generatedAt"] = now_iso()
    index_path.write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def update_index_record(index_data: dict[str, Any], relative_path: str, record: dict[str, Any]) -> None:
    posts = index_data.setdefault("posts", {})
    posts[relative_path] = record


def normalize_title(title: str) -> str:
    normalized = title.casefold().strip()
    normalized = re.sub(r"\s+", "", normalized)
    normalized = re.sub(r"[\"'“”‘’`·,.;:!?()\[\]{}<>/_-]+", "", normalized)
    return normalized


def build_post_url(blog_app: str, post_id: str | int) -> str:
    return f"https://www.cnblogs.com/{blog_app}/p/{post_id}.html"


def build_article_url(blog_app: str, post_id: str | int) -> str:
    return f"https://www.cnblogs.com/{blog_app}/articles/{post_id}"


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(as_list(item))
        return result
    return [str(value)]


def categories_from_front_matter(front_matter: dict[str, Any]) -> list[str]:
    categories = ["[Markdown]"]
    seen = {categories[0]}
    for category in as_list(front_matter.get("categories")):
        if category not in seen:
            categories.append(category)
            seen.add(category)
    return categories


def parse_post_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    if not text:
        return None

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def xmlrpc_datetime(value: Any) -> xmlrpc.client.DateTime | None:
    parsed = parse_post_datetime(value)
    if parsed is None:
        return None
    return xmlrpc.client.DateTime(parsed)


def compute_source_hash(front_matter: dict[str, Any], body: str) -> str:
    payload = {
        "title": front_matter.get("title"),
        "date": str(front_matter.get("date", "")),
        "categories": as_list(front_matter.get("categories")),
        "tags": as_list(front_matter.get("tags")),
        "body": body,
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def make_metaweblog_server(config: CnblogsConfig) -> xmlrpc.client.ServerProxy:
    return xmlrpc.client.ServerProxy(config.api_url, allow_none=True)


def get_users_blogs(config: CnblogsConfig) -> list[dict[str, Any]]:
    server = make_metaweblog_server(config)
    methods = [
        lambda: server.blogger.getUsersBlogs("", config.username, config.token),
        lambda: server.metaWeblog.getUsersBlogs("", config.username, config.token),
    ]

    last_error: Exception | None = None
    for method in methods:
        try:
            result = method()
            if isinstance(result, list):
                return result
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    return []


def extract_users_blog_id(item: dict[str, Any]) -> str:
    for key in ("blogid", "blogId", "blogID"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    raise ValueError(f"UsersBlogs item is missing blogid field: {item}")


def ensure_blog_id(config: CnblogsConfig) -> str:
    if config.blog_id:
        return config.blog_id

    users_blogs = get_users_blogs(config)
    if not users_blogs:
        raise RuntimeError("Failed to resolve cnblogs blogId from MetaWeblog getUsersBlogs")

    normalized_blog_app = config.blog_app.casefold().strip()
    for item in users_blogs:
        blog_url = str(item.get("url") or item.get("blogUrl") or "").casefold()
        if normalized_blog_app and normalized_blog_app in blog_url:
            config.blog_id = extract_users_blog_id(item)
            return config.blog_id

    config.blog_id = extract_users_blog_id(users_blogs[0])
    return config.blog_id


def build_metaweblog_post(front_matter: dict[str, Any], body: str) -> dict[str, Any]:
    post = {
        "title": front_matter.get("title", "").strip(),
        "description": body,
        "categories": categories_from_front_matter(front_matter),
    }

    created = xmlrpc_datetime(front_matter.get("date"))
    if created is not None:
        post["dateCreated"] = created

    return post


def fetch_openapi_json(url: str, token: str = "") -> Any:
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", "my-hexo-cnblogs-sync/1.0")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAPI request failed: {exc.code} {message}") from exc


def fetch_backend_json(
    config: CnblogsConfig,
    url: str,
    *,
    method: str = "GET",
    payload: Any = None,
) -> Any:
    request = urllib.request.Request(url, method=method)
    request.add_header("Authorization", f"Bearer {get_pat_token(config)}")
    request.add_header("Authorization-Type", "pat")
    request.add_header("User-Agent", "my-hexo-cnblogs-sync/1.0")
    request.add_header("Accept", "application/json")

    if payload is not None:
        request.add_header("Content-Type", "application/json")
        request.data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else None
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Backend API request failed: {exc.code} {message}") from exc


def extract_remote_post_id(item: dict[str, Any]) -> str:
    for key in ("id", "Id", "postId", "PostId"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    raise ValueError(f"Remote post item is missing id field: {item}")


def extract_remote_post_title(item: dict[str, Any]) -> str:
    for key in ("title", "Title"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def extract_remote_post_url(item: dict[str, Any], blog_app: str) -> str:
    for key in ("url", "Url", "postUrl", "PostUrl"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if str(item.get("postType") or "") == str(ARTICLE_POST_TYPE):
        return build_article_url(blog_app, extract_remote_post_id(item))
    return build_post_url(blog_app, extract_remote_post_id(item))


def extract_remote_post_date(item: dict[str, Any]) -> str | None:
    for key in ("dateAdded", "DateAdded", "datePublished", "DateCreated", "dateCreated"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def list_remote_posts_via_openapi(
    blog_app: str,
    token: str = "",
    max_pages: int = 100,
) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for page_index in range(1, max_pages + 1):
        encoded_blog = urllib.parse.quote(blog_app)
        url = f"https://api.cnblogs.com/api/blogs/{encoded_blog}/posts?pageIndex={page_index}"
        page = fetch_openapi_json(url, token=token)
        if not isinstance(page, list) or not page:
            break
        posts.extend(page)
    return posts


def list_remote_posts_via_metaweblog(
    config: CnblogsConfig,
    number_of_posts: int = 1000,
) -> list[dict[str, Any]]:
    server = make_metaweblog_server(config)
    blog_id = ensure_blog_id(config)
    return server.metaWeblog.getRecentPosts(
        blog_id,
        config.username,
        config.token,
        number_of_posts,
    )


def list_backend_posts(
    config: CnblogsConfig,
    *,
    post_type: int,
    max_pages: int = 100,
) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    seen_page_signatures: set[tuple[str, ...]] = set()
    for page_index in range(1, max_pages + 1):
        url = (
            f"{BACKEND_BASE_URL}/posts/list?"
            f"p={page_index}&cid=&tid=&t={post_type}&cfg=0&search=&orderBy=&scid="
        )
        payload = fetch_backend_json(config, url)
        if not isinstance(payload, dict):
            break
        page_posts = payload.get("postList", [])
        if not isinstance(page_posts, list) or not page_posts:
            break
        signature = tuple(str(item.get("id")) for item in page_posts)
        if signature in seen_page_signatures:
            break
        seen_page_signatures.add(signature)
        posts.extend(page_posts)
    return posts


def list_remote_articles(config: CnblogsConfig) -> list[dict[str, Any]]:
    return list_backend_posts(config, post_type=ARTICLE_POST_TYPE)


def list_remote_posts(config: CnblogsConfig) -> list[dict[str, Any]]:
    return list_remote_articles(config)


def get_article_detail(config: CnblogsConfig, post_id: str | int) -> dict[str, Any]:
    payload = fetch_backend_json(config, f"{BACKEND_BASE_URL}/articles/{post_id}")
    if not isinstance(payload, dict) or not isinstance(payload.get("blogPost"), dict):
        raise RuntimeError(f"Unexpected article detail payload for post {post_id}: {payload!r}")
    return payload["blogPost"]


def create_or_update_article(
    config: CnblogsConfig,
    *,
    title: str,
    body: str,
    tags: list[str],
    existing_article: dict[str, Any] | None = None,
    post_id: str | None = None,
    slug: str | None = None,
    publish: bool = True,
) -> dict[str, Any]:
    if existing_article is None and post_id:
        existing_article = get_article_detail(config, post_id)

    if existing_article is None:
        existing_article = {
            "id": None,
            "postType": ARTICLE_POST_TYPE,
            "accessPermission": 0,
            "categoryIds": [],
            "collectionIds": [],
            "inSiteCandidate": False,
            "inSiteHome": False,
            "siteCategoryId": None,
            "blogTeamIds": [],
            "displayOnHomePage": True,
            "isAllowComments": True,
            "includeInMainSyndication": True,
            "isPinned": False,
            "showBodyWhenPinned": False,
            "isOnlyForRegisterUser": False,
            "isUpdateDateAdded": False,
            "entryName": None,
            "description": "",
            "featuredImage": None,
            "tags": [],
            "password": None,
            "publishAt": None,
            "datePublished": now_iso(),
            "isMarkdown": True,
            "isDraft": not publish,
            "autoDesc": None,
            "changePostType": False,
            "blogId": int(ensure_blog_id(config)),
            "author": config.username,
            "removeScript": False,
            "clientInfo": None,
            "changeCreatedTime": False,
            "canChangeCreatedTime": False,
            "isContributeToImpressiveBugActivity": False,
            "usingEditorId": None,
            "sourceUrl": None,
        }
    else:
        existing_article = dict(existing_article)

    existing_article["title"] = title
    existing_article["postBody"] = body
    existing_article["postType"] = ARTICLE_POST_TYPE
    existing_article["isMarkdown"] = True
    existing_article["tags"] = tags
    existing_article["isPublished"] = publish
    existing_article["isDraft"] = not publish
    if slug:
        existing_article["entryName"] = slug

    response = fetch_backend_json(
        config,
        BACKEND_BASE_URL + "/posts",
        method="POST",
        payload=existing_article,
    )
    if not isinstance(response, dict):
        raise RuntimeError(f"Unexpected create/update response: {response!r}")
    return response


def match_remote_posts_by_title(
    title: str,
    remote_posts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    exact_title = title.strip()
    exact_normalized = normalize_title(title)
    matches: list[dict[str, Any]] = []

    for item in remote_posts:
        remote_title = extract_remote_post_title(item)
        if not remote_title:
            continue
        if remote_title == exact_title or normalize_title(remote_title) == exact_normalized:
            matches.append(item)

    return matches


def make_mapping_record(
    *,
    title: str,
    post_id: str,
    url: str,
    source_hash: str,
    status: str,
    post_type: str = ARTICLE_POST_TYPE_NAME,
    last_published_at: str | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "postId": str(post_id),
        "url": url,
        "lastPublishedAt": last_published_at or now_iso(),
        "sourceHash": source_hash,
        "status": status,
        "postType": post_type,
    }


def write_mapping_to_front_matter(front_matter: dict[str, Any], record: dict[str, Any]) -> None:
    cnblogs_meta = ensure_cnblogs_meta(front_matter)
    cnblogs_meta["postId"] = str(record["postId"])
    cnblogs_meta["url"] = record["url"]
    cnblogs_meta["lastPublishedAt"] = record["lastPublishedAt"]
    cnblogs_meta["sourceHash"] = record["sourceHash"]
    cnblogs_meta["status"] = record["status"]
    cnblogs_meta["postType"] = record.get("postType", ARTICLE_POST_TYPE_NAME)


def relative_posix_path(path: Path, workspace_root: Path) -> str:
    return path.resolve().relative_to(workspace_root.resolve()).as_posix()
