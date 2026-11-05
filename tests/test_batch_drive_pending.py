import io
import json
import base64
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient

from app import app
from engine import batch_exporter, template_manager, trainer_manager

client = TestClient(app)


class TestBatchDrivePending(unittest.TestCase):
    def setUp(self):
        self.sample_template = {
            "id": "tpl_test_drive",
            "name": "DevOps Leadership Course",
            "dimensions": {"width_mm": 297, "height_mm": 210},
            "page_setup": {"width_mm": 297, "height_mm": 210, "bleed_mm": 3},
            "elements": {}
        }
        self.sample_records = [
            {"Trainee_Name": "Omar Farooq", "training_date": "2026-11-15", "trainer_id": "tr_1"},
            {"Trainee_Name": "Sara Salem", "training_date": "2026-11-15", "trainer_id": "tr_1"}
        ]

    def tearDown(self):
        settings_path = Path(__file__).resolve().parent.parent / "templates_store" / "global_settings.json"
        if settings_path.exists():
            try:
                settings_path.unlink()
            except Exception:
                pass

    def test_extract_drive_folder_id(self):
        # Full URL with /folders/
        url1 = "https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
        self.assertEqual(batch_exporter.extract_drive_folder_id(url1), "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs")

        # Full URL with u/1/folders/ and query params
        url2 = "https://drive.google.com/drive/u/1/folders/1a2b3c4d5e6f7g8h9i0j-k_l?usp=sharing"
        self.assertEqual(batch_exporter.extract_drive_folder_id(url2), "1a2b3c4d5e6f7g8h9i0j-k_l")

        # Open URL with ?id=
        url3 = "https://drive.google.com/open?id=1xyz9876543210_abcdef"
        self.assertEqual(batch_exporter.extract_drive_folder_id(url3), "1xyz9876543210_abcdef")

        # Raw folder ID
        raw_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
        self.assertEqual(batch_exporter.extract_drive_folder_id(raw_id), raw_id)

        # None or empty
        self.assertIsNone(batch_exporter.extract_drive_folder_id(""))
        self.assertIsNone(batch_exporter.extract_drive_folder_id(None))

    def test_batch_export_filename_format(self):
        import pymupdf
        def mock_builder(*args, **kwargs):
            d = pymupdf.open()
            d.new_page(width=100, height=100)
            d._render_metrics = {}
            return d

        with patch("engine.pdf_engine.build_certificate_pdf", side_effect=mock_builder):
            result = batch_exporter.execute_batch_export(
                template_config=self.sample_template,
                records=self.sample_records,
                export_mode="combined_pdf",
                range_str="ALL",
            )
            # Expected filename: DevOps_Leadership_Course_2026-11-15.pdf (NO CertFlow prefix, NO timestamp)
            self.assertEqual(result["filename"], "DevOps_Leadership_Course_2026-11-15.pdf")

            # Clean up
            p = Path(result["file_path"])
            if p.exists():
                p.unlink()

            # Test individual PDFs ZIP
            zip_result = batch_exporter.execute_batch_export(
                template_config=self.sample_template,
                records=self.sample_records,
                export_mode="individual_pdfs_zip",
                range_str="ALL",
            )
            self.assertEqual(zip_result["filename"], "DevOps_Leadership_Course_2026-11-15_PDFs.zip")
            zip_p = Path(zip_result["file_path"])
            if zip_p.exists():
                import zipfile
                with zipfile.ZipFile(zip_p) as zf:
                    namelist = zf.namelist()
                    # Check entry format: {tpl_name}_{clean_date}_{seq:03d}_{safe_name}.pdf
                    self.assertIn("DevOps_Leadership_Course_2026-11-15_001_Omar_Farooq.pdf", namelist)
                    self.assertIn("DevOps_Leadership_Course_2026-11-15_002_Sara_Salem.pdf", namelist)
                zip_p.unlink()

    def test_batch_export_date_extraction_priority(self):
        """Verify date_only / iso_date takes priority over localized training_date."""
        import pymupdf
        def mock_builder(*args, **kwargs):
            d = pymupdf.open()
            d.new_page(width=100, height=100)
            d._render_metrics = {}
            return d

        records_with_localized_date = [
            {
                "Trainee_Name": "أحمد علي",
                "date_only": "2026-11-20",
                "iso_date": "2026-11-20",
                "training_date": "نوفمبر ٢٠، ٢٠٢٦",
                "Training_Date": "نوفمبر ٢٠، ٢٠٢٦",
            }
        ]

        with patch("engine.pdf_engine.build_certificate_pdf", side_effect=mock_builder):
            result = batch_exporter.execute_batch_export(
                template_config=self.sample_template,
                records=records_with_localized_date,
                export_mode="combined_pdf",
                range_str="ALL",
            )
            # Must extract 2026-11-20 rather than localized Arabic text
            self.assertEqual(result["filename"], "DevOps_Leadership_Course_2026-11-20.pdf")
            p = Path(result["file_path"])
            if p.exists():
                p.unlink()

    def test_export_batch_endpoint_content_disposition_arabic(self):
        """Verify /api/export-batch handles Arabic template names without latin-1 encoding crashes."""
        import pymupdf
        def mock_builder(*args, **kwargs):
            d = pymupdf.open()
            d.new_page(width=100, height=100)
            d._render_metrics = {}
            return d

        arabic_template = {
            "id": "tpl_arabic_test",
            "name": "شهادة القيادة المتقدمة",
            "dimensions": {"width_mm": 297, "height_mm": 210},
            "page_setup": {"width_mm": 297, "height_mm": 210, "bleed_mm": 3},
            "elements": {}
        }
        arabic_records = [
            {"Trainee_Name": "محمد عبد الله", "date_only": "2026-11-05"}
        ]

        with patch("engine.pdf_engine.build_certificate_pdf", side_effect=mock_builder):
            res = client.post("/api/export-batch", json={
                "template_config": arabic_template,
                "records": arabic_records,
                "export_mode": "combined_pdf",
                "range_str": "ALL",
            })
            self.assertEqual(res.status_code, 200)
            cd = res.headers.get("Content-Disposition", "")
            self.assertIn("filename*=", cd)
            self.assertIn("UTF-8''", cd)
            # Confirm Latin-1 / ASCII safe fallback is present
            self.assertIn("filename=", cd)

    def test_global_settings_endpoints(self):
        # 1. GET settings
        get_res = client.get("/api/settings")
        self.assertEqual(get_res.status_code, 200)
        data = get_res.json()
        self.assertIn("drive_folder_url", data)
        self.assertIn("drive_folder_id", data)
        self.assertIn("global_apps_script_url", data)

        # 2. POST settings with Drive URL -> automatically extracts folder ID
        post_res = client.post("/api/settings", json={
            "drive_folder_url": "https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs",
            "global_apps_script_url": "https://script.google.com/macros/s/AKfycbxTest/exec"
        })
        self.assertEqual(post_res.status_code, 200)
        saved = post_res.json()["settings"]
        self.assertEqual(saved["drive_folder_id"], "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs")
        self.assertEqual(saved["global_apps_script_url"], "https://script.google.com/macros/s/AKfycbxTest/exec")

    @patch("httpx.Client.post")
    def test_batch_export_drive_upload(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps({
            "status": "success",
            "updated": 2,
            "drive_saved": True,
            "drive_file_url": "https://drive.google.com/file/d/12345/view"
        })
        mock_resp.json.return_value = {
            "status": "success",
            "updated": 2,
            "drive_saved": True,
            "drive_file_url": "https://drive.google.com/file/d/12345/view"
        }
        mock_post.return_value = mock_resp

        import pymupdf
        def mock_builder(*args, **kwargs):
            d = pymupdf.open()
            d.new_page(width=100, height=100)
            d._render_metrics = {}
            return d

        with patch("engine.pdf_engine.build_certificate_pdf", side_effect=mock_builder):
            result = batch_exporter.execute_batch_export(
                template_config=self.sample_template,
                records=self.sample_records,
                export_mode="combined_pdf",
                range_str="ALL",
                apps_script_url="https://script.google.com/macros/s/AKfycbxTest/exec",
                drive_folder_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
            )

            self.assertTrue(result["drive_saved"])
            self.assertEqual(result["drive_file_url"], "https://drive.google.com/file/d/12345/view")
            self.assertEqual(result["drive_error"], "")

            # Verify doPost payload sent to Apps Script
            call_args, call_kwargs = mock_post.call_args
            payload = call_kwargs["json"]
            self.assertTrue(payload.get("save_to_drive"))
            self.assertEqual(payload.get("drive_folder_id"), "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs")
            self.assertEqual(payload.get("filename"), "DevOps_Leadership_Course_2026-11-15.pdf")
            self.assertEqual(payload.get("mime_type"), "application/pdf")
            self.assertIn("file_base64", payload)
            self.assertTrue(len(payload["file_base64"]) > 0)

            # Cleanup
            p = Path(result["file_path"])
            if p.exists():
                p.unlink()

    @patch("engine.data_loader.fetch_google_sheet_records")
    def test_trainers_pending_summary(self, mock_fetch):
        # Mock trainers: trainer 1 has 3 unissued records; trainer 2 has 0 unissued
        mock_trainers = [
            {"id": "tr_pending", "name": "Prof. Ahmed", "sheet_url": "https://docs.google.com/spreadsheets/d/abc/edit"},
            {"id": "tr_completed", "name": "Dr. Sarah", "sheet_url": "https://docs.google.com/spreadsheets/d/xyz/edit"},
            {"id": "tr_no_sheet", "name": "Eng. Khaled", "sheet_url": ""}
        ]

        async def fake_fetch(sheet_url, **kwargs):
            if "abc" in sheet_url:
                return {
                    "unfiltered_records": [
                        {"is_issued": False, "date_only": "2026-11-10"},
                        {"is_issued": False, "date_only": "2026-11-10"},
                        {"is_issued": True, "date_only": "2026-11-01"},
                    ],
                    "unique_dates": [
                        {"date_str": "2026-11-10", "unissued_count": 2, "total_count": 2},
                        {"date_str": "2026-11-01", "unissued_count": 0, "total_count": 1}
                    ]
                }
            else:
                return {
                    "unfiltered_records": [
                        {"is_issued": True, "date_only": "2026-10-20"}
                    ],
                    "unique_dates": [
                        {"date_str": "2026-10-20", "unissued_count": 0, "total_count": 1}
                    ]
                }

        mock_fetch.side_effect = fake_fetch

        with patch("engine.trainer_manager.list_trainers", return_value=mock_trainers):
            res = client.get("/api/trainers/pending-summary")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("pending_trainers", data)
            trainers = data["pending_trainers"]
            self.assertEqual(len(trainers), 1)
            self.assertEqual(trainers[0]["trainer_id"], "tr_pending")
            self.assertEqual(trainers[0]["unissued_count"], 2)
            self.assertEqual(trainers[0]["first_pending_date"], "2026-11-10")

    @patch("httpx.Client.post")
    def test_batch_export_skip_cloud_sync(self, mock_post):
        """Verify execute_batch_export does not contact Apps Script/Drive when skip_cloud_sync=True."""
        import pymupdf
        def mock_builder(*args, **kwargs):
            d = pymupdf.open()
            d.new_page(width=100, height=100)
            d._render_metrics = {}
            return d

        with patch("engine.pdf_engine.build_certificate_pdf", side_effect=mock_builder):
            result = batch_exporter.execute_batch_export(
                template_config=self.sample_template,
                records=self.sample_records,
                export_mode="combined_pdf",
                range_str="ALL",
                apps_script_url="https://script.google.com/macros/s/AKfycbxTest/exec",
                drive_folder_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs",
                skip_cloud_sync=True,
            )

            # Assert no network calls were made
            mock_post.assert_not_called()
            self.assertFalse(result["apps_script_synced"])
            self.assertFalse(result["drive_saved"])
            self.assertEqual(result["exported_count"], 2)

            # File should exist on disk
            out_file = Path(result["file_path"])
            self.assertTrue(out_file.exists())
            out_file.unlink()

    @patch("engine.batch_exporter.httpx.Client")
    def test_sync_exported_file_to_cloud_success_and_cleanup(self, mock_client_cls):
        """Verify sync_exported_file_to_cloud sends payload and cleans up file on success."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps({
            "status": "success",
            "updated": 2,
            "drive_saved": True,
            "drive_file_url": "https://drive.google.com/file/d/test_file/view"
        })
        mock_resp.json.return_value = {
            "status": "success",
            "updated": 2,
            "drive_saved": True,
            "drive_file_url": "https://drive.google.com/file/d/test_file/view"
        }
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        # Create dummy file in EXPORTS_DIR
        test_filename = "test_export_sync.pdf"
        target_path = batch_exporter.EXPORTS_DIR / test_filename
        target_path.write_bytes(b"%PDF-1.4 dummy content")
        self.assertTrue(target_path.exists())

        updates = [
            {"trainee_name": "Omar Farooq", "template_name": "DevOps Leadership Course"},
            {"trainee_name": "Sara Salem", "template_name": "DevOps Leadership Course"},
        ]

        result = batch_exporter.sync_exported_file_to_cloud(
            filename=test_filename,
            template_name="DevOps Leadership Course",
            updates=updates,
            total_records=2,
            apps_script_url="https://script.google.com/macros/s/AKfycbxTest/exec",
            drive_folder_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs",
        )

        self.assertTrue(result["apps_script_synced"])
        self.assertEqual(result["apps_script_updated"], 2)
        self.assertTrue(result["drive_saved"])
        self.assertEqual(result["drive_file_url"], "https://drive.google.com/file/d/test_file/view")

        # Verify payload
        call_args, call_kwargs = mock_client.post.call_args
        payload = call_kwargs["json"]
        self.assertTrue(payload["save_to_drive"])
        self.assertEqual(payload["filename"], test_filename)
        self.assertEqual(payload["mime_type"], "application/pdf")
        self.assertEqual(len(payload["updates"]), 2)

        # File must be deleted in finally block
        self.assertFalse(target_path.exists())

    @patch("engine.batch_exporter.httpx.Client")
    def test_sync_exported_file_to_cloud_cleanup_on_failure(self, mock_client_cls):
        """Verify temporary export file is cleaned up even if Apps Script call raises an exception."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = Exception("Network timeout")
        mock_client_cls.return_value = mock_client

        test_filename = "test_export_fail.pdf"
        target_path = batch_exporter.EXPORTS_DIR / test_filename
        target_path.write_bytes(b"%PDF-1.4 dummy fail content")
        self.assertTrue(target_path.exists())

        result = batch_exporter.sync_exported_file_to_cloud(
            filename=test_filename,
            template_name="DevOps Course",
            updates=[{"trainee_name": "Omar", "template_name": "DevOps Course"}],
            total_records=1,
            apps_script_url="https://script.google.com/macros/s/AKfycbxTest/exec",
            drive_folder_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs",
        )

        self.assertFalse(result["apps_script_synced"])
        self.assertIn("Network timeout", result["apps_script_error"])
        # Crucial check: file must be cleaned up despite the failure
        self.assertFalse(target_path.exists())

    @patch("engine.batch_exporter.httpx.Client")
    def test_export_batch_api_two_stage_pipeline(self, mock_client_cls):
        """Integration test for 2-stage batch export and cloud sync API flow."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps({
            "status": "success",
            "updated": 2,
            "drive_saved": True,
            "drive_file_url": "https://drive.google.com/file/d/stage2/view"
        })
        mock_resp.json.return_value = {
            "status": "success",
            "updated": 2,
            "drive_saved": True,
            "drive_file_url": "https://drive.google.com/file/d/stage2/view"
        }
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        import pymupdf
        def mock_builder(*args, **kwargs):
            d = pymupdf.open()
            d.new_page(width=100, height=100)
            d._render_metrics = {}
            return d

        with patch("engine.pdf_engine.build_certificate_pdf", side_effect=mock_builder):
            # Stage 1: Fast Export with keep_file_for_sync=True and skip_cloud_sync=True
            stage1_res = client.post("/api/export-batch", json={
                "template_config": self.sample_template,
                "records": self.sample_records,
                "export_mode": "combined_pdf",
                "skip_cloud_sync": True,
                "keep_file_for_sync": True,
                "apps_script_url": "https://script.google.com/macros/s/AKfycbxTest/exec",
                "drive_folder_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs",
            })

            self.assertEqual(stage1_res.status_code, 200)
            self.assertEqual(stage1_res.headers.get("x-exported-count"), "2")
            self.assertEqual(stage1_res.headers.get("x-apps-script-synced"), "false")
            self.assertEqual(stage1_res.headers.get("x-drive-saved"), "false")

            # Extract filename from Content-Disposition
            # format: attachment; filename="..."; filename*=UTF-8''...
            cd = stage1_res.headers.get("content-disposition", "")
            self.assertIn("filename*=", cd)
            expected_filename = "DevOps_Leadership_Course_2026-11-15.pdf"

            # Check that file was KEPT on disk in EXPORTS_DIR because keep_file_for_sync=True
            kept_file = batch_exporter.EXPORTS_DIR / expected_filename
            self.assertTrue(kept_file.exists())

            # Stage 2: Cloud Sync call
            sync_payload = {
                "filename": expected_filename,
                "template_name": "DevOps Leadership Course",
                "updates": [
                    {"trainee_name": "Omar Farooq", "template_name": "DevOps Leadership Course"},
                    {"trainee_name": "Sara Salem", "template_name": "DevOps Leadership Course"},
                ],
                "total_records": 2,
                "apps_script_url": "https://script.google.com/macros/s/AKfycbxTest/exec",
                "drive_folder_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs",
            }
            stage2_res = client.post("/api/export-batch/cloud-sync", json=sync_payload)
            self.assertEqual(stage2_res.status_code, 200)
            data = stage2_res.json()
            self.assertTrue(data["apps_script_synced"])
            self.assertEqual(data["apps_script_updated"], 2)
            self.assertTrue(data["drive_saved"])
            self.assertEqual(data["drive_file_url"], "https://drive.google.com/file/d/stage2/view")

            # Verify that the file was deleted after Stage 2
            self.assertFalse(kept_file.exists())


if __name__ == "__main__":
    unittest.main()
