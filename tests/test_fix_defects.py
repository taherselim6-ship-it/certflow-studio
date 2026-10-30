import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from starlette.background import BackgroundTask

from app import app, safe_cleanup_file
from engine import github_sync, template_manager, trainer_manager, font_manager, batch_exporter


class TestTask6DefectFixes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.orig_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)
        github_sync.set_hydration_status("unconfigured", None)

    # =========================================================================
    # FIX 1: Prevent Data Loss After Failed Startup Hydration
    # =========================================================================
    def test_fix1_unconfigured_allows_normal_operations(self):
        """Unconfigured GITHUB_TOKEN (local mode) allows normal read/write operations."""
        os.environ.pop("GITHUB_TOKEN", None)
        os.environ.pop("GITHUB_DATA_REPO", None)
        self.assertFalse(github_sync.is_configured())
        self.assertTrue(github_sync.is_hydration_healthy())
        self.assertEqual(github_sync.get_hydration_status()["status"], "unconfigured")

    def test_fix1_degraded_hydration_blocks_destructive_empty_store_creation(self):
        """When GitHub is configured but hydration is degraded, ensure_store_dirs does not create empty stores."""
        os.environ["GITHUB_TOKEN"] = "fake-token"
        os.environ["GITHUB_DATA_REPO"] = "user/repo"
        github_sync.set_hydration_status("degraded", "Connection failed")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            fake_templates_json = tmp_path / "templates.json"
            fake_trainers_json = tmp_path / "trainers.json"

            with patch.object(template_manager, "TEMPLATES_STORE", tmp_path), \
                 patch.object(template_manager, "TEMPLATES_JSON_PATH", fake_templates_json), \
                 patch.object(trainer_manager, "TRAINERS_STORE_DIR", tmp_path), \
                 patch.object(trainer_manager, "TRAINERS_FILE", fake_trainers_json):
                
                template_manager.ensure_store_dirs()
                trainer_manager.ensure_store_dirs()

                # Files must NOT be created because hydration is degraded
                self.assertFalse(fake_templates_json.exists())
                self.assertFalse(fake_trainers_json.exists())

    def test_fix1_degraded_hydration_blocks_persistent_mutations(self):
        """When hydration is degraded, mutation attempts raise RuntimeError and return 503."""
        os.environ["GITHUB_TOKEN"] = "fake-token"
        os.environ["GITHUB_DATA_REPO"] = "user/repo"
        github_sync.set_hydration_status("degraded", "Network timeout on startup")

        # 1. Direct manager call raises RuntimeError
        with self.assertRaises(RuntimeError) as ctx:
            template_manager.save_template({"id": "t1", "name": "Test"})
        self.assertIn("read-only emergency mode", str(ctx.exception))

        with self.assertRaises(RuntimeError) as ctx:
            trainer_manager.create_trainer(name="Test Trainer")
        self.assertIn("read-only emergency mode", str(ctx.exception))

        with self.assertRaises(RuntimeError) as ctx:
            font_manager.save_font("test.ttf", b"fake-data")
        self.assertIn("read-only emergency mode", str(ctx.exception))

        # 2. API endpoints return 503 Service Unavailable
        res_tpl = self.client.post("/api/templates", json={"id": "t1", "name": "Test"})
        self.assertEqual(res_tpl.status_code, 503)
        self.assertIn("وضع القراءة فقط", res_tpl.json()["detail"])

        res_trainer = self.client.post("/api/trainers", data={"name": "Test Trainer"})
        self.assertEqual(res_trainer.status_code, 503)
        self.assertIn("وضع القراءة فقط", res_trainer.json()["detail"])

    def test_fix1_recovery_after_successful_pull(self):
        """A subsequent successful pull restores healthy hydration and normal operations."""
        os.environ["GITHUB_TOKEN"] = "fake-token"
        os.environ["GITHUB_DATA_REPO"] = "user/repo"
        github_sync.set_hydration_status("degraded", "Previous failure")
        self.assertFalse(github_sync.is_hydration_healthy())

        # Simulate successful manual sync pull
        with patch.object(github_sync, "_sync_pull_directory") as mock_dir:
            stats = github_sync.sync_pull_on_startup()
            self.assertEqual(stats["status"], "ok")
            self.assertTrue(github_sync.is_hydration_healthy())
            self.assertEqual(github_sync.get_hydration_status()["status"], "healthy")

    # =========================================================================
    # FIX 2: Protect Read-Modify-Write Lifecycles & 409 Conflict JSON Merge
    # =========================================================================
    def test_fix2_store_lock_is_reentrant_and_non_blocking(self):
        """store_lock uses RLock allowing nested execution within the same thread without deadlock."""
        with github_sync.store_lock("templates"):
            with github_sync.store_lock("templates"):
                # Nested acquisition succeeds without hanging
                pass

    def test_fix2_merge_json_manifest_records(self):
        """merge_json_manifest_records merges records preserving non-overlapping IDs and keeping newer updates."""
        remote_records = [
            {"id": "t1", "name": "Remote T1", "updated_at": "2026-10-30 10:00:00"},
            {"id": "t2", "name": "Remote T2", "updated_at": "2026-10-30 10:00:00"},
        ]
        local_records = [
            {"id": "t2", "name": "Local T2 Newer", "updated_at": "2026-10-30 12:00:00"},
            {"id": "t3", "name": "Local T3", "updated_at": "2026-10-30 11:00:00"},
        ]

        merged_bytes = github_sync.merge_json_manifest_records(
            json.dumps(remote_records).encode("utf-8"),
            json.dumps(local_records).encode("utf-8"),
        )
        merged = json.loads(merged_bytes.decode("utf-8"))

        by_id = {item["id"]: item for item in merged}
        self.assertEqual(len(by_id), 3)
        self.assertEqual(by_id["t1"]["name"], "Remote T1")
        self.assertEqual(by_id["t2"]["name"], "Local T2 Newer")
        self.assertEqual(by_id["t3"]["name"], "Local T3")

    # =========================================================================
    # FIX 3: Eliminate Path Traversal in File Resolvers
    # =========================================================================
    def test_fix3_path_traversal_prevention_templates(self):
        """get_base_pdf_path and get_base_preview_path reject directory traversal, absolute paths, and null bytes."""
        traversal_attempts = [
            "../../app.py",
            "../engine/github_sync.py",
            "/etc/passwd",
            "test\0evil.pdf",
            "....//....//app.py",
            "valid_name.exe",
            "valid_name.sh",
        ]
        for bad_filename in traversal_attempts:
            pdf_res = template_manager.get_base_pdf_path(bad_filename)
            self.assertIsNone(pdf_res, f"Expected None for PDF path traversal: {bad_filename}")

            preview_res = template_manager.get_base_preview_path(bad_filename)
            self.assertIsNone(preview_res, f"Expected None for preview path traversal: {bad_filename}")

    def test_fix3_path_traversal_prevention_fonts(self):
        """get_font_path rejects directory traversal, absolute paths, and null bytes."""
        traversal_attempts = [
            "../../app.py",
            "/etc/passwd",
            "my_font\0evil.ttf",
            "test.sh",
        ]
        for bad_font in traversal_attempts:
            res = font_manager.get_font_path(bad_font)
            self.assertIsNone(res, f"Expected None for font path traversal: {bad_font}")

    # =========================================================================
    # FIX 4: Clean Up Temporary Export Files
    # =========================================================================
    def test_fix4_safe_cleanup_file(self):
        """safe_cleanup_file deletes the temporary file and safely ignores non-existent files."""
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"test export content")
            temp_path = tf.name

        self.assertTrue(os.path.exists(temp_path))
        safe_cleanup_file(temp_path)
        self.assertFalse(os.path.exists(temp_path))

        # Re-running on non-existent file does not raise an exception
        try:
            safe_cleanup_file(temp_path)
        except Exception as e:
            self.fail(f"safe_cleanup_file raised unexpected error: {e}")

    def test_fix4_export_failure_cleans_up_partial_file(self):
        """When PDF or ZIP export generation fails, partial output file is unlinked immediately."""
        broken_template = {
            "id": "broken",
            "name": "Broken",
            "dimensions": {"width_mm": 297, "height_mm": 210},
            "elements": {}
        }
        records = [{"Trainee_Name": "Alice"}]

        with patch("engine.pdf_engine.build_certificate_pdf", side_effect=RuntimeError("Rendering failed")):
            with self.assertRaises(RuntimeError):
                batch_exporter.execute_batch_export(
                    template_config=broken_template,
                    records=records,
                    export_mode="combined_pdf",
                    range_str="1",
                    filename_prefix="TestCrash",
                )

        # Ensure no leftover files with prefix TestCrash exist in EXPORTS_DIR
        leftovers = list(batch_exporter.EXPORTS_DIR.glob("TestCrash_*.pdf"))
        self.assertEqual(len(leftovers), 0, f"Expected partial export file to be cleaned up, found: {leftovers}")

    # =========================================================================
    # FIX 5: Correct Google Sheets Zero-Trainee Feedback
    # =========================================================================
    def test_fix5_empty_trainee_names_sets_skipped_without_apps_script_error(self):
        """When batch records have no trainee names, execute_batch_export sets apps_script_skipped=True."""
        import pymupdf

        records_no_trainee_names = [
            {"Score": "100", "Course": "Math"},
            {"Score": "95", "Course": "Physics"},
        ]
        template = {
            "id": "t_clean",
            "name": "Template Clean",
            "dimensions": {"width_mm": 297, "height_mm": 210},
            "elements": {}
        }

        def mock_builder(*args, **kwargs):
            d = pymupdf.open()
            d.new_page(width=100, height=100)
            d._render_metrics = {}
            return d

        with patch("engine.pdf_engine.build_certificate_pdf", side_effect=mock_builder):
            result = batch_exporter.execute_batch_export(
                template_config=template,
                records=records_no_trainee_names,
                export_mode="combined_pdf",
                range_str="1-2",
                filename_prefix="TestSkipped",
                apps_script_url="https://script.google.com/macros/s/AKfycbyFake/exec",
            )

            # Cleanup generated test file
            if os.path.exists(result["file_path"]):
                os.unlink(result["file_path"])

            self.assertTrue(result["apps_script_skipped"])
            self.assertFalse(result["apps_script_synced"])
            self.assertIn("لم يتم العثور على أي أسماء", result["apps_script_error"])


if __name__ == "__main__":
    unittest.main()
