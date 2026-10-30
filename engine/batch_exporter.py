"""
engine/batch_exporter.py
High-throughput Prepress Batch Export Engine for CertFlow Studio.
Handles:
- Combined multi-page print PDF generation (Page Box & Vector preservation)
- Individual PDF ZIP bundling with sanitized names and job reports
- Individual 300 DPI JPEG ZIP bundling
- Flexible Range Selector (ALL, 1-10, 5-, -15, 1,3,5-8)
- Prepress metrics auditing & Export_Report.txt generation
- Optional Webhook callback integration
"""

import io
import re
import os
import zipfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import pymupdf
import httpx

from engine import pdf_engine

logger = logging.getLogger("certflow.batch_exporter")
EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str) -> str:
    """Removes invalid filesystem characters while preserving Arabic & Latin names."""
    if not name:
        return "Certificate"
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", str(name).strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:80] if cleaned else "Certificate"


def parse_record_indices(range_str: Optional[str], total_count: int) -> List[int]:
    """
    Parses user range specifications into a sorted list of 0-based record indices.
    Examples:
      - None, '', 'ALL' -> all records [0 ... total_count - 1]
      - '1-10' -> [0, 1, ..., 9]
      - '5-' -> [4, 5, ..., total_count - 1]
      - '-15' -> [0, 1, ..., 14]
      - '1, 3, 5-7' -> [0, 2, 4, 5, 6]
    """
    if total_count <= 0:
        return []

    if not range_str or not range_str.strip() or range_str.strip().upper() == "ALL":
        return list(range(total_count))

    indices = set()
    parts = [p.strip() for p in range_str.split(",") if p.strip()]

    for part in parts:
        # Match "start-end" or "start-" or "-end"
        if "-" in part:
            dash_idx = part.find("-")
            start_s = part[:dash_idx].strip()
            end_s = part[dash_idx + 1:].strip()

            start = int(start_s) if start_s.isdigit() else 1
            end = int(end_s) if end_s.isdigit() else total_count

            # Convert 1-based to 0-based
            idx_start = max(0, start - 1)
            idx_end = min(total_count - 1, end - 1)

            for i in range(idx_start, idx_end + 1):
                indices.add(i)
        elif part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < total_count:
                indices.add(idx)

    result = sorted(list(indices))
    return result if result else list(range(total_count))


def generate_export_report(
    template_config: Dict[str, Any],
    processed_records: List[Dict[str, Any]],
    export_mode: str,
    output_filename: str,
    warnings: List[str],
) -> str:
    """Creates a structured prepress audit text report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tpl_name = template_config.get("name", "Certificate Template")
    page_setup = template_config.get("page_setup", {})
    w_mm = page_setup.get("width_mm", 297.0)
    h_mm = page_setup.get("height_mm", 210.0)
    bleed_mm = page_setup.get("bleed_mm", 3.0)

    report = [
        "============================================================",
        "          CertFlow Studio | تقرير تصدير الشهادات الطباعية    ",
        "============================================================",
        f"تاريخ ووقت التصدير: {now}",
        f"اسم القالب: {tpl_name}",
        f"أبعاد الصفحة: {w_mm} × {h_mm} مم (TrimBox) + {bleed_mm} مم (Bleed)",
        f"صيغة التصدير: {export_mode}",
        f"اسم الملف المخرج: {output_filename}",
        f"إجمالي الشهادات المكتملة: {len(processed_records)}",
        "------------------------------------------------------------",
    ]

    if warnings:
        report.append("تنبيهات ما قبل الطباعة (Prepress Warnings):")
        for w in warnings:
            report.append(f"  * {w}")
        report.append("------------------------------------------------------------")
    else:
        report.append("حالة ما قبل الطباعة: جميع الشهادات مطابقة للمعايير الطباعية بنجاح 100%.")
        report.append("------------------------------------------------------------")

    report.append("سجل الشهادات المصدرة:")
    for idx, rec in enumerate(processed_records, start=1):
        name = rec.get("trainee_name") or rec.get("Trainee_Name") or "بدون اسم"
        date_val = rec.get("training_date") or rec.get("Training_Date") or "بدون تاريخ"
        trainer = rec.get("trainer_name") or rec.get("Trainer_Name") or "المدرب المعتمد"
        report.append(f"  [{idx:03d}] المتدرب: {name:<35} | التاريخ: {date_val:<18} | المدرب: {trainer}")

    report.append("============================================================")
    report.append("تم التوليد بواسطة CertFlow Studio Prepress Engine v2.0")
    report.append("============================================================")

    return "\n".join(report)


def execute_batch_export(
    template_config: Dict[str, Any],
    records: List[Dict[str, Any]],
    export_mode: str = "combined_pdf",  # 'combined_pdf' | 'individual_pdfs_zip' | 'individual_jpegs_zip'
    range_str: Optional[str] = "ALL",
    filename_prefix: str = "Cert",
    dpi: int = 300,
    webhook_url: Optional[str] = None,
    apps_script_url: Optional[str] = None,
    sheet_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes high-speed batch export.
    Returns:
      {
        "file_path": str,
        "filename": str,
        "media_type": str,
        "total_records": int,
        "exported_count": int,
        "warnings_count": int,
        "report_summary": str
      }
    """
    total_records = len(records)
    selected_indices = parse_record_indices(range_str, total_records)
    if not selected_indices:
        raise ValueError("لم يتم تحديد أي سجلات صالحة للتصدير.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_prefix = sanitize_filename(filename_prefix or "CertFlow")
    tpl_name = sanitize_filename(template_config.get("name", "Template"))

    processed_records = []
    warnings = []

    if export_mode == "combined_pdf":
        out_filename = f"{clean_prefix}_{tpl_name}_{timestamp}.pdf"
        out_path = EXPORTS_DIR / out_filename

        master_doc = pymupdf.open()

        for seq, idx in enumerate(selected_indices, start=1):
            rec = records[idx]
            cert_doc = pdf_engine.build_certificate_pdf(
                template_config=template_config,
                record_data=rec,
                show_trim_guide=False,
            )

            metrics = getattr(cert_doc, "_render_metrics", {})
            name = rec.get("trainee_name") or rec.get("Trainee_Name") or f"Record {idx+1}"
            if metrics.get("is_shrunk"):
                warnings.append(
                    f"الشهادة #{seq} ({name}): تم تقليص الخط بنسبة {metrics.get('max_shrink_percent', 0)}% ليتناسب مع الإطار"
                )
            if metrics.get("is_overflow"):
                warnings.append(
                    f"الشهادة #{seq} ({name}): تنبيه! النص يتجاوز إطار الطباعة عند الحد الأدنى للحجم"
                )

            # Insert single page into master document
            master_doc.insert_pdf(cert_doc)
            cert_doc.close()
            processed_records.append(rec)

        master_doc.save(str(out_path), garbage=4, deflate=True)
        master_doc.close()

        media_type = "application/pdf"

    elif export_mode == "individual_pdfs_zip":
        out_filename = f"{clean_prefix}_{tpl_name}_{timestamp}_PDFs.zip"
        out_path = EXPORTS_DIR / out_filename

        with zipfile.ZipFile(out_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zipf:
            for seq, idx in enumerate(selected_indices, start=1):
                rec = records[idx]
                cert_doc = pdf_engine.build_certificate_pdf(
                    template_config=template_config,
                    record_data=rec,
                    show_trim_guide=False,
                )

                metrics = getattr(cert_doc, "_render_metrics", {})
                name = rec.get("trainee_name") or rec.get("Trainee_Name") or f"Record_{idx+1}"
                if metrics.get("is_shrunk"):
                    warnings.append(
                        f"الشهادة #{seq} ({name}): تم تقليص الخط بنسبة {metrics.get('max_shrink_percent', 0)}%"
                    )
                if metrics.get("is_overflow"):
                    warnings.append(
                        f"الشهادة #{seq} ({name}): تنبيه! النص يتجاوز الإطار"
                    )

                pdf_data = cert_doc.tobytes(garbage=4, deflate=True)
                cert_doc.close()

                safe_name = sanitize_filename(name)
                entry_name = f"{clean_prefix}_{seq:03d}_{safe_name}.pdf"
                zipf.writestr(entry_name, pdf_data)
                processed_records.append(rec)

            # Add Prepress Report
            report_text = generate_export_report(
                template_config, processed_records, export_mode, out_filename, warnings
            )
            zipf.writestr("Export_Report.txt", report_text.encode("utf-8"))

        media_type = "application/zip"

    elif export_mode == "individual_jpegs_zip":
        out_filename = f"{clean_prefix}_{tpl_name}_{timestamp}_JPEGs.zip"
        out_path = EXPORTS_DIR / out_filename

        with zipfile.ZipFile(out_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zipf:
            for seq, idx in enumerate(selected_indices, start=1):
                rec = records[idx]
                cert_doc = pdf_engine.build_certificate_pdf(
                    template_config=template_config,
                    record_data=rec,
                    show_trim_guide=False,
                )

                metrics = getattr(cert_doc, "_render_metrics", {})
                name = rec.get("trainee_name") or rec.get("Trainee_Name") or f"Record_{idx+1}"
                if metrics.get("is_shrunk"):
                    warnings.append(
                        f"الشهادة #{seq} ({name}): تم تقليص الخط بنسبة {metrics.get('max_shrink_percent', 0)}%"
                    )
                if metrics.get("is_overflow"):
                    warnings.append(
                        f"الشهادة #{seq} ({name}): تنبيه! النص يتجاوز الإطار"
                    )

                page = cert_doc[0]
                pix = page.get_pixmap(dpi=dpi, alpha=False)
                jpeg_data = pix.tobytes("jpeg", jpg_quality=95)
                cert_doc.close()

                safe_name = sanitize_filename(name)
                entry_name = f"{clean_prefix}_{seq:03d}_{safe_name}.jpg"
                zipf.writestr(entry_name, jpeg_data)
                processed_records.append(rec)

            report_text = generate_export_report(
                template_config, processed_records, export_mode, out_filename, warnings
            )
            zipf.writestr("Export_Report.txt", report_text.encode("utf-8"))

        media_type = "application/zip"
    else:
        raise ValueError(f"صيغة التصدير غير مدعومة: {export_mode}")

    # Prepare updates payload for Google Apps Script doPost
    updates = []
    template_name = template_config.get("name", "")
    for r in processed_records:
        t_name = r.get("Trainee_Name") or r.get("trainee_name") or r.get("name") or ""
        if t_name:
            updates.append({"trainee_name": t_name, "template_name": template_name})

    apps_script_synced = False
    target_script_url = apps_script_url.strip() if (apps_script_url and apps_script_url.strip()) else None
    if not target_script_url and webhook_url and ("script.google.com" in webhook_url or "script.googleusercontent.com" in webhook_url):
        target_script_url = webhook_url.strip()

    # Google Apps Script Write-Back (doPost)
    if target_script_url and updates:
        try:
            script_payload = {
                "sheet_url": sheet_url.strip() if sheet_url else "",
                "updates": updates,
                "template_name": template_name,
                "exported_count": len(processed_records),
                "total_count": total_records,
                "timestamp": timestamp,
            }
            with httpx.Client(timeout=15.0, follow_redirects=True, headers={"Content-Type": "application/json"}) as client:
                post_res = client.post(target_script_url, json=script_payload)
                apps_script_synced = post_res.status_code in (200, 302)
                logger.info(f"Google Apps Script doPost sync completed: status {post_res.status_code}, synced {len(updates)} records")
        except Exception as e:
            logger.warning(f"Failed to sync updates to Google Apps Script {target_script_url}: {e}")

    # General Webhook Notification if provided and different from script_url
    if webhook_url and webhook_url.strip() and webhook_url.strip() != target_script_url:
        try:
            httpx.post(
                webhook_url.strip(),
                json={
                    "event": "certflow_export_completed",
                    "template_name": template_name,
                    "exported_count": len(processed_records),
                    "total_count": total_records,
                    "filename": out_filename,
                    "export_mode": export_mode,
                    "timestamp": timestamp,
                    "updates": updates,
                },
                timeout=5.0,
            )
        except Exception as e:
            logger.warning(f"Failed to trigger webhook {webhook_url}: {e}")

    report_summary = f"تم تصدير {len(processed_records)} شهادة بنجاح بصيغة {export_mode}."
    return {
        "file_path": str(out_path),
        "filename": out_filename,
        "media_type": media_type,
        "total_records": total_records,
        "exported_count": len(processed_records),
        "warnings_count": len(warnings),
        "warnings": warnings,
        "report_summary": report_summary,
        "apps_script_synced": apps_script_synced,
    }

