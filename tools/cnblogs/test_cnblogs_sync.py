from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cnblogs_sync
from cnblogs_common import load_markdown_post


class SyncPostTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_root = Path(self.temp_dir.name)
        self.posts_dir = self.workspace_root / "source" / "_posts"
        self.posts_dir.mkdir(parents=True)
        self.config = SimpleNamespace(blog_app="example")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_post(self, cnblogs: str = "") -> Path:
        post_path = self.posts_dir / "test.md"
        cnblogs_block = f"cnblogs:\n{cnblogs}" if cnblogs else ""
        post_path.write_text(
            "---\n"
            "title: Test Post\n"
            "tags:\n"
            "  - Python\n"
            f"{cnblogs_block}"
            "---\n\n"
            "Body\n",
            encoding="utf-8",
        )
        return post_path

    @staticmethod
    def args(**overrides: object) -> argparse.Namespace:
        values = {
            "publish": True,
            "write_back": True,
            "fail_on_conflict": True,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def sync(self, post_path: Path, **arg_overrides: object) -> tuple[str, str]:
        return cnblogs_sync.sync_post(
            post_path=post_path,
            workspace_root=self.workspace_root,
            args=self.args(**arg_overrides),
            config=self.config,
            remote_posts_cache={"posts": None},
        )

    @patch("cnblogs_common.list_remote_articles", return_value=[])
    @patch(
        "cnblogs_sync.create_or_update_article",
        return_value={"id": 123, "url": "https://www.cnblogs.com/example/articles/123"},
    )
    def test_new_post_writes_only_stable_mapping(self, update_mock, _list_mock) -> None:
        post_path = self.write_post()

        action, _ = self.sync(post_path)

        self.assertEqual(action, "created")
        front_matter, _ = load_markdown_post(post_path)
        self.assertEqual(
            front_matter["cnblogs"],
            {
                "postId": "123",
                "url": "https://www.cnblogs.com/example/articles/123",
                "postType": "Article",
            },
        )
        self.assertIsNone(update_mock.call_args.kwargs["post_id"])

    @patch(
        "cnblogs_common.list_remote_articles",
        return_value=[
            {
                "id": 456,
                "title": "Test Post",
                "postType": 2,
                "url": "https://www.cnblogs.com/example/articles/456",
            }
        ],
    )
    @patch(
        "cnblogs_sync.create_or_update_article",
        return_value={"id": 456, "url": "https://www.cnblogs.com/example/articles/456"},
    )
    def test_unique_title_match_updates_and_writes_mapping(self, update_mock, _list_mock) -> None:
        post_path = self.write_post()

        action, _ = self.sync(post_path)

        self.assertEqual(action, "updated")
        self.assertEqual(update_mock.call_args.kwargs["post_id"], "456")
        front_matter, _ = load_markdown_post(post_path)
        self.assertEqual(front_matter["cnblogs"]["postId"], "456")

    @patch(
        "cnblogs_sync.create_or_update_article",
        return_value={"id": 789, "url": "https://www.cnblogs.com/example/articles/789"},
    )
    def test_existing_mapping_updates_without_touching_file(self, update_mock) -> None:
        post_path = self.write_post(
            "  postId: '789'\n"
            "  url: https://www.cnblogs.com/example/articles/789\n"
            "  postType: Article\n"
        )
        original = post_path.read_bytes()

        action, _ = self.sync(post_path)

        self.assertEqual(action, "updated")
        self.assertEqual(update_mock.call_args.kwargs["post_id"], "789")
        self.assertEqual(post_path.read_bytes(), original)

    @patch("cnblogs_sync.create_or_update_article")
    def test_disabled_post_is_not_sent_or_modified(self, update_mock) -> None:
        post_path = self.write_post("  published: false\n")
        original = post_path.read_bytes()

        action, _ = self.sync(post_path)

        self.assertEqual(action, "skipped")
        update_mock.assert_not_called()
        self.assertEqual(post_path.read_bytes(), original)

    @patch(
        "cnblogs_common.list_remote_articles",
        return_value=[
            {"id": 1, "title": "Test Post"},
            {"id": 2, "title": "Test Post"},
        ],
    )
    @patch("cnblogs_sync.create_or_update_article")
    def test_title_conflict_does_not_write(self, update_mock, _list_mock) -> None:
        post_path = self.write_post()
        original = post_path.read_bytes()

        action, _ = self.sync(post_path, fail_on_conflict=False)

        self.assertEqual(action, "conflict")
        update_mock.assert_not_called()
        self.assertEqual(post_path.read_bytes(), original)

    @patch("cnblogs_common.list_remote_articles", return_value=[])
    @patch(
        "cnblogs_sync.create_or_update_article",
        side_effect=RuntimeError("API failed"),
    )
    def test_api_failure_does_not_write(self, _update_mock, _list_mock) -> None:
        post_path = self.write_post()
        original = post_path.read_bytes()

        with self.assertRaisesRegex(RuntimeError, "API failed"):
            self.sync(post_path)

        self.assertEqual(post_path.read_bytes(), original)

    @patch("cnblogs_common.list_remote_articles", return_value=[])
    @patch(
        "cnblogs_sync.create_or_update_article",
        return_value={"id": 123, "url": "https://www.cnblogs.com/example/articles/123"},
    )
    def test_no_write_back_leaves_new_post_unchanged(self, _update_mock, _list_mock) -> None:
        post_path = self.write_post()
        original = post_path.read_bytes()

        action, _ = self.sync(post_path, write_back=False)

        self.assertEqual(action, "created")
        self.assertEqual(post_path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
