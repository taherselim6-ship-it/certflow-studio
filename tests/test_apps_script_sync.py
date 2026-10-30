"""
tests/test_apps_script_sync.py
Automated unit & integration tests for Google Apps Script doPost synchronization,
redirect handling, payload validation, and error reporting.
"""

import json
import unittest
from unittest.mock import patch, MagicMock
import httpx
from fastapi.testclient import TestClient
from app import app
from engine import batch_exporter


class TestGoogleAppsScriptSync(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.sample_template = {
            "id": "tpl_test_apps_script",
            "name": "البرنامج القيادي المتقدم",
            "base_pdf_filename": "default_certificate_base.pdf",
            "fields": [
                {
                    "id": "trainee_name",
                    "label": "اسم المتدرب",
                    "x_mm": 50,
                    "y_mm": 50,
                    "width_mm": 100,
                    "height_mm": 20,
                    "font_family": "Cairo Regular",
                    "font_size": 24,
                }
            ],
        }
        self.sample_records = [
            {"trainee_name": "أحمد محمد", "training_date": "2026-10-30"},
            {"trainee_name": "سارة علي", "training_date": "2026-10-30"},
        ]

    @patch("httpx.Client.post")
    def test_batch_export_apps_script_success(self, mock_post):
        # Mock successful Google Apps Script doPost response after 302 redirect
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps({"status": "success", "updated": 2})
        mock_resp.json.return_value = {"status": "success", "updated": 2}
        mock_post.return_value = mock_resp

        result = batch_exporter.execute_batch_export(
            template_config=self.sample_template,
            records=self.sample_records,
            export_mode="combined_pdf",
            range_str="ALL",
            apps_script_url="https://script.google.com/macros/s/TEST_SCRIPT_ID/exec",
            sheet_url="https://docs.google.com/spreadsheets/d/TEST_SHEET_ID/edit",
        )

        self.assertTrue(result["apps_script_synced"])
        self.assertEqual(result["apps_script_updated"], 2)
        self.assertEqual(result["apps_script_error"], "")

        # Verify payload structure matches requirement:
        # { "sheet_url": "...", "updates": [{ "trainee_name": "...", "template_name": "..." }] }
        call_args, call_kwargs = mock_post.call_args
        payload = call_kwargs["json"]
        self.assertIn("sheet_url", payload)
        self.assertEqual(payload["sheet_url"], "https://docs.google.com/spreadsheets/d/TEST_SHEET_ID/edit")
        self.assertIn("updates", payload)
        self.assertEqual(len(payload["updates"]), 2)
        self.assertEqual(payload["updates"][0]["trainee_name"], "أحمد محمد")
        self.assertEqual(payload["updates"][0]["template_name"], "البرنامج القيادي المتقدم")

    @patch("httpx.Client.post")
    def test_batch_export_apps_script_cleans_script_url_from_sheet_url(self, mock_post):
        # When sheet_url is set to the Apps Script URL itself, it should be cleared
        # so Apps Script doesn't crash trying to open a script URL as a spreadsheet.
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps({"status": "success", "updated": 2})
        mock_resp.json.return_value = {"status": "success", "updated": 2}
        mock_post.return_value = mock_resp

        result = batch_exporter.execute_batch_export(
            template_config=self.sample_template,
            records=self.sample_records,
            export_mode="combined_pdf",
            range_str="ALL",
            apps_script_url="https://script.google.com/macros/s/TEST_SCRIPT_ID/exec",
            sheet_url="https://script.google.com/macros/s/TEST_SCRIPT_ID/exec",
        )

        self.assertTrue(result["apps_script_synced"])
        call_args, call_kwargs = mock_post.call_args
        payload = call_kwargs["json"]
        self.assertEqual(payload["sheet_url"], "")  # Successfully cleaned!

    @patch("httpx.Client.post")
    def test_batch_export_apps_script_login_redirect_error(self, mock_post):
        # Mock HTML login page (occurs when not deployed as 'Anyone')
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<!DOCTYPE html><html><head><title>Sign in - Google Accounts</title></head><body>...</body></html>"
        mock_post.return_value = mock_resp

        result = batch_exporter.execute_batch_export(
            template_config=self.sample_template,
            records=self.sample_records,
            export_mode="combined_pdf",
            range_str="ALL",
            apps_script_url="https://script.google.com/macros/s/TEST_SCRIPT_ID/exec",
        )

        self.assertFalse(result["apps_script_synced"])
        self.assertIn("تسجيل الدخول", result["apps_script_error"])

    @patch("httpx.Client.post")
    def test_batch_export_apps_script_internal_error_reporting(self, mock_post):
        # Mock script error JSON
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps({"status": "error", "message": "Spreadsheet not found"})
        mock_resp.json.return_value = {"status": "error", "message": "Spreadsheet not found"}
        mock_post.return_value = mock_resp

        result = batch_exporter.execute_batch_export(
            template_config=self.sample_template,
            records=self.sample_records,
            export_mode="combined_pdf",
            range_str="ALL",
            apps_script_url="https://script.google.com/macros/s/TEST_SCRIPT_ID/exec",
        )

        self.assertFalse(result["apps_script_synced"])
        self.assertEqual(result["apps_script_error"], "Spreadsheet not found")

    @patch("httpx.Client.post")
    def test_batch_export_apps_script_timeout_handling(self, mock_post):
        # Mock timeout exception
        mock_post.side_effect = httpx.TimeoutException("Connection timed out after 40s")

        result = batch_exporter.execute_batch_export(
            template_config=self.sample_template,
            records=self.sample_records,
            export_mode="combined_pdf",
            range_str="ALL",
            apps_script_url="https://script.google.com/macros/s/TEST_SCRIPT_ID/exec",
        )

        self.assertFalse(result["apps_script_synced"])
        self.assertIn("مهلة", result["apps_script_error"])

    @patch("httpx.AsyncClient.post")
    def test_standalone_sync_endpoint_success(self, mock_async_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps({"status": "success", "updated": 1})
        mock_resp.json.return_value = {"status": "success", "updated": 1}
        mock_async_post.return_value = mock_resp

        resp = self.client.post(
            "/api/trainer/sync-apps-script",
            json={
                "script_url": "https://script.google.com/macros/s/TEST/exec",
                "template_name": "Test Template",
                "updates": [{"trainee_name": "محمد علي", "template_name": "Test Template"}],
                "sheet_url": "https://docs.google.com/spreadsheets/d/TEST_ID/edit",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["updated_count"], 1)


if __name__ == "__main__":
    unittest.main()

