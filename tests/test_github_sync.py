"""
tests/test_github_sync.py
Comprehensive automated test suite for engine/github_sync.py and its integration
with engine/template_manager.py, engine/trainer_manager.py, engine/font_manager.py, and app.py.
"""

import io
import json
import os
import shutil
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import github_sync, template_manager, trainer_manager, font_manager
import app


class TestGitHubSyncUnit(unittest.TestCase):
    def setUp(self):
        self.orig_env = os.environ.copy()
        self.tpl_json = github_sync.BASE_DIR / "templates_store" / "templates.json"
        self.orig_tpl = self.tpl_json.read_bytes() if self.tpl_json.exists() else None
        self.tr_json = github_sync.BASE_DIR / "trainers_store" / "trainers.json"
        self.orig_tr = self.tr_json.read_bytes() if self.tr_json.exists() else None

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)
        if self.orig_tpl is not None and self.tpl_json.exists():
            self.tpl_json.write_bytes(self.orig_tpl)
        if self.orig_tr is not None and self.tr_json.exists():
            self.tr_json.write_bytes(self.orig_tr)

    def test_configuration_detection(self):
        # 1. Unconfigured when GITHUB_TOKEN is missing or empty
        os.environ["GITHUB_TOKEN"] = ""
        os.environ["GITHUB_REPO"] = ""
        os.environ["GITHUB_DATA_REPO"] = ""
        self.assertFalse(github_sync.is_configured())

        # 2. Configured with default data repo when token is provided
        os.environ["GITHUB_TOKEN"] = "ghp_secrettoken123"
        self.assertTrue(github_sync.is_configured())
        self.assertEqual(github_sync.get_data_repo(), "taherselim6-ship-it/certflow-data")

        # 3. Configured with explicit GITHUB_DATA_REPO
        os.environ["GITHUB_DATA_REPO"] = "custom-owner/custom-data"
        self.assertEqual(github_sync.get_data_repo(), "custom-owner/custom-data")

    def test_repo_normalization_and_priority(self):
        # Default fallback
        os.environ.pop("GITHUB_DATA_REPO", None)
        os.environ.pop("GITHUB_REPO", None)
        self.assertEqual(github_sync.get_data_repo(), "taherselim6-ship-it/certflow-data")

        # Fallback to GITHUB_REPO if GITHUB_DATA_REPO not set
        os.environ["GITHUB_REPO"] = "https://github.com/fallback-org/my-repo.git"
        self.assertEqual(github_sync.get_data_repo(), "fallback-org/my-repo")

        # GITHUB_DATA_REPO overrides GITHUB_REPO
        os.environ["GITHUB_DATA_REPO"] = "dedicated-org/data-repo.git"
        self.assertEqual(github_sync.get_data_repo(), "dedicated-org/data-repo")

        # Normalization cases
        cases = [
            ("taherselim6-ship-it/certflow-data", "taherselim6-ship-it/certflow-data"),
            ("taherselim6-ship-it/certflow-data.git", "taherselim6-ship-it/certflow-data"),
            ("https://github.com/taherselim6-ship-it/certflow-data.git", "taherselim6-ship-it/certflow-data"),
            ("https://github.com/owner/sub-repo/", "owner/sub-repo"),
        ]
        for input_val, expected in cases:
            os.environ["GITHUB_DATA_REPO"] = input_val
            self.assertEqual(github_sync.get_data_repo(), expected)

    def test_branch_default_and_override(self):
        if "GITHUB_BRANCH" in os.environ:
            del os.environ["GITHUB_BRANCH"]
        self.assertEqual(github_sync.get_branch(), "main")

        os.environ["GITHUB_BRANCH"] = "production"
        self.assertEqual(github_sync.get_branch(), "production")

    def test_commit_message_skip_tags(self):
        msg = github_sync.format_commit_message("Auto-sync: add template")
        self.assertIn("[skip render] [skip ci]", msg)

        # Do not duplicate if already present
        msg2 = github_sync.format_commit_message("Update [skip render] [skip ci]")
        self.assertEqual(msg2.count("[skip render]"), 1)

    def test_rel_path_validation(self):
        base = github_sync.BASE_DIR

        # Valid paths across all persistent directories
        p1 = base / "templates_store" / "templates.json"
        self.assertEqual(github_sync.get_repo_rel_path(p1), "templates_store/templates.json")

        p2 = Path("trainers_store/signatures/sig_123.png")
        self.assertEqual(github_sync.get_repo_rel_path(p2), "trainers_store/signatures/sig_123.png")

        p3 = base / "fonts" / "Cairo-Bold.ttf"
        self.assertEqual(github_sync.get_repo_rel_path(p3), "fonts/Cairo-Bold.ttf")

        # Invalid paths outside allowed store
        p4 = base / "app.py"
        self.assertIsNone(github_sync.get_repo_rel_path(p4))

        p5 = Path("/etc/passwd")
        self.assertIsNone(github_sync.get_repo_rel_path(p5))

        # Preview temporary files must be skipped
        p6 = base / "trainers_store" / "signatures" / "preview_temp_123.png"
        self.assertIsNone(github_sync.get_repo_rel_path(p6))

        # OS metadata files must be skipped
        p7 = base / "templates_store" / ".DS_Store"
        self.assertIsNone(github_sync.get_repo_rel_path(p7))

    def test_calc_git_blob_sha(self):
        data = b"Hello CertFlow Studio"
        expected_sha = github_sync.calc_git_blob_sha(data)
        import hashlib
        self.assertEqual(expected_sha, hashlib.sha1(b"blob 21\0Hello CertFlow Studio").hexdigest())

    @patch("urllib.request.urlopen")
    def test_get_remote_file_sha_found(self, mock_urlopen):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_DATA_REPO"] = "user/repo"

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"sha": "abc123def456"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        sha = github_sync.get_remote_file_sha("templates_store/templates.json")
        self.assertEqual(sha, "abc123def456")

    @patch("urllib.request.urlopen")
    def test_get_remote_file_sha_404(self, mock_urlopen):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_DATA_REPO"] = "user/repo"

        err = urllib.error.HTTPError("http://example.com", 404, "Not Found", {}, io.BytesIO(b"{}"))
        mock_urlopen.side_effect = err

        sha = github_sync.get_remote_file_sha("templates_store/non_existent.pdf")
        self.assertIsNone(sha)

    @patch("engine.github_sync.get_remote_file_sha")
    @patch("urllib.request.urlopen")
    def test_sync_file_push_creates_new_with_tags(self, mock_urlopen, mock_get_sha):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_DATA_REPO"] = "user/data-repo"

        mock_get_sha.return_value = None  # file doesn't exist remotely
        mock_resp = MagicMock()
        mock_resp.status = 201
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        test_file = github_sync.BASE_DIR / "templates_store" / "test_unit_push.json"
        test_file.write_text("{\"test\": true}")

        try:
            success = github_sync.sync_file_push(test_file)
            self.assertTrue(success)
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.get_method(), "PUT")
            data = json.loads(req.data.decode("utf-8"))
            self.assertIn("content", data)
            self.assertNotIn("sha", data)
            self.assertIn("[skip render] [skip ci]", data["message"])
        finally:
            if test_file.exists():
                test_file.unlink()

    @patch("engine.github_sync.get_remote_file_sha")
    @patch("urllib.request.urlopen")
    def test_sync_file_push_skips_when_identical(self, mock_urlopen, mock_get_sha):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_DATA_REPO"] = "user/repo"

        test_file = github_sync.BASE_DIR / "templates_store" / "test_unit_identical.json"
        content = b"{\"identical\": true}"
        test_file.write_bytes(content)

        file_sha = github_sync.calc_git_blob_sha(content)
        mock_get_sha.return_value = file_sha

        try:
            success = github_sync.sync_file_push(test_file)
            self.assertTrue(success)
            mock_urlopen.assert_not_called()
        finally:
            if test_file.exists():
                test_file.unlink()

    @patch("time.sleep")
    @patch("engine.github_sync.get_remote_file_sha")
    @patch("urllib.request.urlopen")
    def test_sync_file_push_retries_on_409_conflict(self, mock_urlopen, mock_get_sha, mock_sleep):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_DATA_REPO"] = "user/repo"

        test_file = github_sync.BASE_DIR / "templates_store" / "test_unit_retry.json"
        test_file.write_text("{\"retry\": true}")

        mock_get_sha.side_effect = ["old_sha", "new_sha_from_conflict"]

        # First request raises 409 Conflict, second succeeds 200
        conflict_err = urllib.error.HTTPError("url", 409, "Conflict", {}, io.BytesIO(b"{}"))
        ok_cm = MagicMock()
        ok_resp = MagicMock()
        ok_resp.status = 200
        ok_cm.__enter__.return_value = ok_resp

        mock_urlopen.side_effect = [conflict_err, ok_cm]

        try:
            success = github_sync.sync_file_push(test_file)
            self.assertTrue(success)
            self.assertEqual(mock_urlopen.call_count, 2)
            mock_sleep.assert_called_once_with(0.5)
        finally:
            if test_file.exists():
                test_file.unlink()

    @patch("engine.github_sync.get_remote_file_sha")
    @patch("urllib.request.urlopen")
    def test_sync_file_push_raises_on_unrecoverable_error(self, mock_urlopen, mock_get_sha):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_DATA_REPO"] = "user/repo"

        test_file = github_sync.BASE_DIR / "templates_store" / "test_unit_fail.json"
        test_file.write_text("{\"fail\": true}")

        mock_get_sha.return_value = None
        server_err = urllib.error.HTTPError("url", 500, "Internal Server Error", {}, io.BytesIO(b"error"))
        mock_urlopen.side_effect = server_err

        try:
            with self.assertRaises(RuntimeError):
                github_sync.sync_file_push(test_file, raise_on_error=True)
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_local_mode_graceful_no_op(self):
        os.environ["GITHUB_TOKEN"] = ""
        test_file = github_sync.BASE_DIR / "templates_store" / "templates.json"
        # Should return True without raising or making network calls
        self.assertTrue(github_sync.sync_file_push(test_file, raise_on_error=True))
        self.assertTrue(github_sync.sync_file_delete(test_file, raise_on_error=True))

    @patch("engine.github_sync.get_remote_file_sha")
    @patch("urllib.request.urlopen")
    def test_sync_file_delete(self, mock_urlopen, mock_get_sha):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_DATA_REPO"] = "user/repo"

        mock_get_sha.return_value = "existing_remote_sha"
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        target_path = "trainers_store/signatures/sig_to_delete.png"
        success = github_sync.sync_file_delete(target_path)
        self.assertTrue(success)

        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "DELETE")
        data = json.loads(req.data.decode("utf-8"))
        self.assertEqual(data["sha"], "existing_remote_sha")
        self.assertIn("[skip render] [skip ci]", data["message"])

    @patch("engine.github_sync.sync_file_push")
    def test_template_manager_hooks(self, mock_push):
        templates = template_manager.load_templates()
        template_manager.save_templates_store(templates)
        mock_push.assert_called()
        self.assertTrue(mock_push.call_args[1].get("raise_on_error"))

    @patch("engine.github_sync.sync_file_push")
    def test_trainer_manager_hooks(self, mock_push):
        trainers = trainer_manager.load_trainers()
        trainer_manager.save_trainers_store(trainers)
        mock_push.assert_called()
        self.assertTrue(mock_push.call_args[1].get("raise_on_error"))

    @patch("engine.github_sync.sync_file_push")
    @patch("engine.github_sync.sync_file_delete")
    def test_trainer_lifecycle_sync_hooks(self, mock_del, mock_push):
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGBA", (10, 10), (0, 0, 0, 255)).save(buf, format="PNG")
        dummy_sig = buf.getvalue()

        # 1. Create trainer
        tr = trainer_manager.create_trainer(
            name="Test Sync Trainer",
            signature_bytes=dummy_sig,
            signature_filename="sig_test.png"
        )
        self.assertIsNotNone(tr.get("id"))
        mock_push.assert_called()

        # 2. Update trainer with new signature
        mock_push.reset_mock()
        mock_del.reset_mock()

        trainer_manager.update_trainer(
            trainer_id=tr["id"],
            signature_bytes=dummy_sig,
            signature_filename="sig_updated.png"
        )
        mock_del.assert_called()
        mock_push.assert_called()

        # 3. Delete trainer
        mock_push.reset_mock()
        mock_del.reset_mock()
        trainer_manager.delete_trainer(tr["id"])
        mock_del.assert_called()
        mock_push.assert_called()

    @patch("engine.github_sync.sync_file_push")
    @patch("engine.github_sync.sync_file_delete")
    def test_template_lifecycle_sync_hooks(self, mock_del, mock_push):
        tpl = {
            "id": "tpl_test_sync_lifecycle",
            "name": "Sync Test Template",
            "base_pdf_filename": "default_certificate_base.pdf",
            "fields": []
        }
        template_manager.save_template(tpl)
        mock_push.assert_called()

        mock_push.reset_mock()
        mock_del.reset_mock()
        template_manager.delete_template("tpl_test_sync_lifecycle")
        mock_push.assert_called()

    @patch("engine.github_sync.sync_file_push")
    @patch("engine.github_sync.sync_file_delete")
    def test_font_manager_sync_hooks(self, mock_del, mock_push):
        dummy_font = b"\x00\x01\x00\x00dummy_font_content"
        filename = "TestFont.ttf"

        try:
            # 1. Save font
            font_manager.save_font(filename, dummy_font)
            mock_push.assert_called()
            self.assertTrue(mock_push.call_args[1].get("raise_on_error"))

            # 2. Delete font
            font_manager.delete_font(filename)
            mock_del.assert_called()
        finally:
            p = font_manager.FONTS_DIR / filename
            if p.exists():
                p.unlink()

    @patch("urllib.request.urlopen")
    def test_startup_pull_sync(self, mock_urlopen):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_DATA_REPO"] = "user/repo"

        # Backup real templates.json if present
        tpl_path = github_sync.BASE_DIR / "templates_store" / "templates.json"
        orig_content = tpl_path.read_bytes() if tpl_path.exists() else None

        # Mock directory listing response
        mock_list_resp = MagicMock()
        mock_list_resp.read.return_value = json.dumps([
            {
                "name": "templates.json",
                "path": "templates_store/templates.json",
                "sha": "new_remote_sha_different_from_local",
                "type": "file"
            }
        ]).encode("utf-8")

        mock_raw_resp = MagicMock()
        mock_raw_resp.read.return_value = orig_content or b"[]"

        def fake_urlopen(req, timeout=None):
            cm = MagicMock()
            if req.headers.get("Accept") == "application/vnd.github.raw":
                cm.__enter__.return_value = mock_raw_resp
            else:
                cm.__enter__.return_value = mock_list_resp
            return cm

        mock_urlopen.side_effect = fake_urlopen

        try:
            stats = github_sync.sync_pull_on_startup()
            self.assertEqual(stats["status"], "ok")
            self.assertIn("templates_store/templates.json", stats["pulled"])
            self.assertEqual(stats["repo"], "user/repo")
        finally:
            if orig_content is not None:
                tpl_path.write_bytes(orig_content)


class TestAppEndpointsWithSync(unittest.TestCase):
    def setUp(self):
        self.orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)

    @patch("engine.github_sync.sync_pull_on_startup")
    def test_status_endpoint_reports_github_sync(self, mock_pull):
        os.environ["GITHUB_TOKEN"] = "tok"
        os.environ["GITHUB_DATA_REPO"] = "user/my-data-repo"
        os.environ["GITHUB_BRANCH"] = "main"

        import asyncio
        status_res = asyncio.run(app.get_system_status())

        self.assertIn("github_sync", status_res)
        self.assertTrue(status_res["github_sync"]["configured"])
        self.assertEqual(status_res["github_sync"]["repo"], "user/my-data-repo")
        self.assertEqual(status_res["github_sync"]["branch"], "main")


if __name__ == "__main__":
    unittest.main()
