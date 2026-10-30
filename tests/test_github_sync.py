"""
tests/test_github_sync.py
Comprehensive automated test suite for engine/github_sync.py and its integration
with engine/template_manager.py, engine/trainer_manager.py, and app.py.
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

from engine import github_sync, template_manager, trainer_manager
import app


class TestGitHubSyncUnit(unittest.TestCase):
    def setUp(self):
        self.orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)

    def test_configuration_detection(self):
        os.environ["GITHUB_TOKEN"] = ""
        os.environ["GITHUB_REPO"] = ""
        self.assertFalse(github_sync.is_configured())

        os.environ["GITHUB_TOKEN"] = "ghp_secrettoken123"
        os.environ["GITHUB_REPO"] = ""
        self.assertFalse(github_sync.is_configured())

        os.environ["GITHUB_TOKEN"] = "ghp_secrettoken123"
        os.environ["GITHUB_REPO"] = "user/repo"
        self.assertTrue(github_sync.is_configured())

    def test_repo_normalization(self):
        cases = [
            ("taherselim6-ship-it/certflow-studio", "taherselim6-ship-it/certflow-studio"),
            ("taherselim6-ship-it/certflow-studio.git", "taherselim6-ship-it/certflow-studio"),
            ("https://github.com/taherselim6-ship-it/certflow-studio.git", "taherselim6-ship-it/certflow-studio"),
            ("https://github.com/owner/sub-repo/", "owner/sub-repo"),
        ]
        for input_val, expected in cases:
            os.environ["GITHUB_REPO"] = input_val
            self.assertEqual(github_sync.get_repo(), expected)

    def test_branch_default_and_override(self):
        if "GITHUB_BRANCH" in os.environ:
            del os.environ["GITHUB_BRANCH"]
        self.assertEqual(github_sync.get_branch(), "main")

        os.environ["GITHUB_BRANCH"] = "production"
        self.assertEqual(github_sync.get_branch(), "production")

    def test_rel_path_validation(self):
        base = github_sync.BASE_DIR

        # Valid paths
        p1 = base / "templates_store" / "templates.json"
        self.assertEqual(github_sync.get_repo_rel_path(p1), "templates_store/templates.json")

        p2 = Path("trainers_store/signatures/sig_123.png")
        self.assertEqual(github_sync.get_repo_rel_path(p2), "trainers_store/signatures/sig_123.png")

        # Invalid paths outside allowed store
        p3 = base / "app.py"
        self.assertIsNone(github_sync.get_repo_rel_path(p3))

        p4 = Path("/etc/passwd")
        self.assertIsNone(github_sync.get_repo_rel_path(p4))

        # Preview temporary files must be skipped
        p5 = base / "trainers_store" / "signatures" / "preview_temp_123.png"
        self.assertIsNone(github_sync.get_repo_rel_path(p5))

        # OS metadata files must be skipped
        p6 = base / "templates_store" / ".DS_Store"
        self.assertIsNone(github_sync.get_repo_rel_path(p6))

    def test_calc_git_blob_sha(self):
        data = b"Hello CertFlow Studio"
        expected_sha = github_sync.calc_git_blob_sha(data)
        import hashlib
        self.assertEqual(expected_sha, hashlib.sha1(b"blob 21\0Hello CertFlow Studio").hexdigest())

    @patch("urllib.request.urlopen")
    def test_get_remote_file_sha_found(self, mock_urlopen):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_REPO"] = "user/repo"

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"sha": "abc123def456"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        sha = github_sync.get_remote_file_sha("templates_store/templates.json")
        self.assertEqual(sha, "abc123def456")

    @patch("urllib.request.urlopen")
    def test_get_remote_file_sha_404(self, mock_urlopen):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_REPO"] = "user/repo"

        err = urllib.error.HTTPError("http://example.com", 404, "Not Found", {}, io.BytesIO(b"{}"))
        mock_urlopen.side_effect = err

        sha = github_sync.get_remote_file_sha("templates_store/non_existent.pdf")
        self.assertIsNone(sha)

    @patch("engine.github_sync.get_remote_file_sha")
    @patch("urllib.request.urlopen")
    def test_sync_file_push_creates_new(self, mock_urlopen, mock_get_sha):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_REPO"] = "user/repo"

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
        finally:
            if test_file.exists():
                test_file.unlink()

    @patch("engine.github_sync.get_remote_file_sha")
    @patch("urllib.request.urlopen")
    def test_sync_file_push_skips_when_identical(self, mock_urlopen, mock_get_sha):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_REPO"] = "user/repo"

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

    @patch("engine.github_sync.get_remote_file_sha")
    @patch("urllib.request.urlopen")
    def test_sync_file_delete(self, mock_urlopen, mock_get_sha):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_REPO"] = "user/repo"

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

    @patch("engine.github_sync.push_file_async")
    def test_template_manager_hooks(self, mock_push_async):
        templates = template_manager.load_templates()
        template_manager.save_templates_store(templates)
        mock_push_async.assert_called()

    @patch("engine.github_sync.push_file_async")
    def test_trainer_manager_hooks(self, mock_push_async):
        trainers = trainer_manager.load_trainers()
        trainer_manager.save_trainers_store(trainers)
        mock_push_async.assert_called()

    @patch("urllib.request.urlopen")
    def test_startup_pull_sync(self, mock_urlopen):
        os.environ["GITHUB_TOKEN"] = "test_token"
        os.environ["GITHUB_REPO"] = "user/repo"

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

        # Mock raw file content response
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
        finally:
            if orig_content is not None:
                tpl_path.write_bytes(orig_content)

    @patch("engine.github_sync.push_file_async")
    @patch("engine.github_sync.delete_file_async")
    def test_trainer_lifecycle_sync_hooks(self, mock_del_async, mock_push_async):
        # 1. Create trainer with dummy 1x1 PNG bytes
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGBA", (10, 10), (0, 0, 0, 255)).save(buf, format="PNG")
        dummy_sig = buf.getvalue()

        tr = trainer_manager.create_trainer(
            name="Test Sync Trainer",
            signature_bytes=dummy_sig,
            signature_filename="sig_test.png"
        )
        self.assertIsNotNone(tr.get("id"))
        mock_push_async.assert_called()

        # 2. Update trainer with new signature
        mock_push_async.reset_mock()
        mock_del_async.reset_mock()

        trainer_manager.update_trainer(
            trainer_id=tr["id"],
            signature_bytes=dummy_sig,
            signature_filename="sig_updated.png"
        )
        # Old signature deleted, new signature pushed
        mock_del_async.assert_called()
        mock_push_async.assert_called()

        # 3. Delete trainer
        mock_push_async.reset_mock()
        mock_del_async.reset_mock()
        trainer_manager.delete_trainer(tr["id"])
        mock_del_async.assert_called()
        mock_push_async.assert_called()

    @patch("engine.github_sync.push_file_async")
    @patch("engine.github_sync.delete_file_async")
    def test_template_lifecycle_sync_hooks(self, mock_del_async, mock_push_async):
        # 1. Save new template
        tpl = {
            "id": "tpl_test_sync_lifecycle",
            "name": "Sync Test Template",
            "base_pdf_filename": "default_certificate_base.pdf",
            "fields": []
        }
        template_manager.save_template(tpl)
        mock_push_async.assert_called()

        # 2. Delete template
        mock_push_async.reset_mock()
        mock_del_async.reset_mock()
        template_manager.delete_template("tpl_test_sync_lifecycle")
        mock_push_async.assert_called()


class TestAppEndpointsWithSync(unittest.TestCase):
    def setUp(self):
        self.orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)

    @patch("engine.github_sync.sync_pull_on_startup")
    def test_status_endpoint_reports_github_sync(self, mock_pull):
        os.environ["GITHUB_TOKEN"] = "tok"
        os.environ["GITHUB_REPO"] = "user/my-repo"
        os.environ["GITHUB_BRANCH"] = "main"

        import asyncio
        status_res = asyncio.run(app.get_system_status())

        self.assertIn("github_sync", status_res)
        self.assertTrue(status_res["github_sync"]["configured"])
        self.assertEqual(status_res["github_sync"]["repo"], "user/my-repo")
        self.assertEqual(status_res["github_sync"]["branch"], "main")


if __name__ == "__main__":
    unittest.main()
