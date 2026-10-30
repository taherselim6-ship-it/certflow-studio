import io
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response, status
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from engine import font_manager, trainer_manager, template_manager, data_loader, pdf_engine, batch_exporter, github_sync
from engine.excel_template import generate_standard_excel_template

BASE_DIR = Path(__file__).resolve().parent

# Ensure runtime directories exist
for folder in ["fonts", "trainers_store", "templates_store", "exports", "static"]:
    (BASE_DIR / folder).mkdir(parents=True, exist_ok=True)

# Pull/restore latest files from GitHub if configured (Render persistence)
github_sync.sync_pull_on_startup()

trainer_manager.ensure_store_dirs()
template_manager.ensure_store_dirs()
font_manager.ensure_fonts_dir()

app = FastAPI(
    title="CertFlow Studio | منصة الشهادات الطباعية",
    description="Local print certificate generation platform replacing Adobe InDesign Data Merge",
    version="1.0.0"
)

# Enable CORS for local workflows
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/")
async def serve_index():
    index_file = BASE_DIR / "static" / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="UI shell not found")
    return FileResponse(str(index_file))


@app.get("/api/status")
async def get_system_status():
    fonts = font_manager.list_fonts()
    trainers = trainer_manager.list_trainers()
    templates = template_manager.load_templates()
    return {
        "status": "online",
        "app_name": "CertFlow Studio | منصة الشهادات الطباعية",
        "version": "1.0.0",
        "fonts_count": len(fonts),
        "trainers_count": len(trainers),
        "templates_count": len(templates),
        "workspace_ready": True,
        "github_sync": {
            "configured": github_sync.is_configured(),
            "repo": github_sync.get_repo() if github_sync.is_configured() else None,
            "branch": github_sync.get_branch() if github_sync.is_configured() else None,
        },
    }


@app.post("/api/sync/pull")
async def manual_sync_pull():
    """Manually triggers a pull/sync from GitHub repository."""
    stats = github_sync.sync_pull_on_startup()
    return {
        "message": "تم تنفيذ فحص المزامنة مع GitHub بنجاح",
        "stats": stats,
    }


# ==========================================
# Font Manager Endpoints
# ==========================================

@app.get("/api/fonts")
async def get_fonts():
    fonts = font_manager.list_fonts()
    return {"fonts": fonts, "count": len(fonts)}


@app.post("/api/fonts/upload")
async def upload_fonts(
    files: Optional[list[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None)
):
    upload_list = []
    if files:
        upload_list.extend(files)
    if file:
        upload_list.append(file)

    if not upload_list:
        raise HTTPException(status_code=400, detail="لم يتم إرسال أي ملف خط")

    saved_fonts = []
    errors = []

    for f in upload_list:
        filename = f.filename or "unknown_font.ttf"
        ext = Path(filename).suffix.lower()
        if ext not in font_manager.ALLOWED_EXTENSIONS:
            errors.append(f"{filename}: صيغة غير مدعومة ({ext}). يُسمح فقط بملفات .ttf أو .otf")
            continue

        content = await f.read()
        if len(content) == 0:
            errors.append(f"{filename}: الملف فارغ")
            continue

        try:
            font_info = font_manager.save_font(filename, content)
            saved_fonts.append(font_info)
        except Exception as e:
            errors.append(f"{filename}: فشل الحفظ ({str(e)})")

    if not saved_fonts and errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    msg = f"تم رفع وتثبيت {len(saved_fonts)} خط بنجاح" if len(saved_fonts) > 1 else "تم رفع وتثبيت الخط بنجاح"
    return {
        "message": msg,
        "fonts": saved_fonts,
        "count": len(saved_fonts),
        "errors": errors if errors else None
    }


@app.delete("/api/fonts/{filename}")
async def delete_font(filename: str):
    success = font_manager.delete_font(filename)
    if not success:
        raise HTTPException(status_code=404, detail="ملف الخط غير موجود")
    return {"message": "تم حذف الخط بنجاح", "filename": filename}


@app.get("/api/fonts/{filename}")
async def download_font(filename: str):
    font_path = font_manager.get_font_path(filename)
    if not font_path or not font_path.exists():
        raise HTTPException(status_code=404, detail="ملف الخط غير موجود")
    
    media_type = "font/otf" if font_path.suffix.lower() == ".otf" else "font/ttf"
    return FileResponse(
        str(font_path),
        media_type=media_type,
        filename=font_path.name
    )


# ==========================================
# Trainer Profiles Endpoints
# ==========================================

@app.get("/api/trainers")
async def list_trainers():
    trainers = trainer_manager.list_trainers()
    return {"trainers": trainers, "count": len(trainers)}


@app.get("/api/trainers/{trainer_id}")
async def get_trainer(trainer_id: str):
    trainer = trainer_manager.get_trainer(trainer_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="ملف المدرب غير موجود")
    return trainer


@app.post("/api/trainers")
async def create_trainer(
    name: str = Form(...),
    sheet_url: str = Form(""),
    name_col: str = Form("الاسم"),
    time_col: str = Form("Timestamp"),
    scale: float = Form(100.0),
    signature_file: Optional[UploadFile] = File(None),
    script_url: str = Form("")
):
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="اسم المدرب حقل إلزامي")

    sig_bytes = None
    sig_filename = None
    if signature_file and signature_file.filename:
        sig_bytes = await signature_file.read()
        sig_filename = signature_file.filename

    try:
        record = trainer_manager.create_trainer(
            name=name,
            sheet_url=sheet_url,
            name_col=name_col,
            time_col=time_col,
            scale=scale,
            signature_bytes=sig_bytes,
            signature_filename=sig_filename,
            script_url=script_url
        )
        return {
            "message": "تم إنشاء ملف المدرب ومعالجة التوقيع بنجاح",
            "trainer": record
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء حفظ المدرب: {str(e)}")


@app.put("/api/trainers/{trainer_id}")
async def update_trainer(
    trainer_id: str,
    name: Optional[str] = Form(None),
    sheet_url: Optional[str] = Form(None),
    name_col: Optional[str] = Form(None),
    time_col: Optional[str] = Form(None),
    scale: Optional[float] = Form(None),
    signature_file: Optional[UploadFile] = File(None),
    script_url: Optional[str] = Form(None)
):
    sig_bytes = None
    if signature_file and signature_file.filename:
        sig_bytes = await signature_file.read()

    record = trainer_manager.update_trainer(
        trainer_id=trainer_id,
        name=name,
        sheet_url=sheet_url,
        name_col=name_col,
        time_col=time_col,
        scale=scale,
        signature_bytes=sig_bytes,
        script_url=script_url
    )

    if not record:
        raise HTTPException(status_code=404, detail="ملف المدرب غير موجود")

    return {
        "message": "تم تحديث بيانات المدرب بنجاح",
        "trainer": record
    }


@app.delete("/api/trainers/{trainer_id}")
async def delete_trainer(trainer_id: str):
    success = trainer_manager.delete_trainer(trainer_id)
    if not success:
        raise HTTPException(status_code=404, detail="ملف المدرب غير موجود")
    return {"message": "تم حذف ملف المدرب بنجاح", "trainer_id": trainer_id}


@app.get("/api/trainers/signature/{filename}")
async def get_trainer_signature(filename: str):
    sig_path = trainer_manager.get_signature_path(filename)
    if not sig_path:
        raise HTTPException(status_code=404, detail="ملف التوقيع غير موجود")
    media_type = "application/pdf" if sig_path.suffix.lower() == ".pdf" else "image/png"
    return FileResponse(str(sig_path), media_type=media_type)


@app.post("/api/trainers/preview-signature")
async def preview_signature(file: UploadFile = File(...)):
    """
    On-the-fly signature cleanup and auto-trim preview without persisting to a trainer.
    Supports Vector PDF, Transparent PNG, and Opaque JPG/PNG.
    Always returns transparent PNG stream with bounding box dimension headers.
    """
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="الملف فارغ")

    filename = file.filename or "signature.png"
    try:
        sig_info = trainer_manager.save_processed_signature(
            content, filename_hint=filename, prefix="preview_temp"
        )
        thumb_name = sig_info.get("thumbnail_filename") or sig_info["filename"]
        thumb_path = trainer_manager.get_signature_path(thumb_name)
        if not thumb_path or not thumb_path.exists():
            thumb_path = Path(sig_info["path"])

        with open(thumb_path, "rb") as f:
            thumb_bytes = f.read()

        # Clean up temporary preview files
        try:
            if thumb_path.exists():
                thumb_path.unlink()
            main_path = Path(sig_info["path"])
            if main_path.exists() and main_path != thumb_path:
                main_path.unlink()
        except Exception:
            pass

        return Response(
            content=thumb_bytes,
            media_type="image/png",
            headers={
                "X-Signature-Type": sig_info["signature_type"],
                "X-Is-Vector": str(sig_info.get("is_vector", False)),
                "X-Original-Width": str(sig_info["original_width"]),
                "X-Original-Height": str(sig_info["original_height"]),
                "X-Cleaned-Width": str(sig_info["width"]),
                "X-Cleaned-Height": str(sig_info["height"]),
                "Access-Control-Expose-Headers": "X-Signature-Type, X-Is-Vector, X-Original-Width, X-Original-Height, X-Cleaned-Width, X-Cleaned-Height",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل معالجة التوقيع: {str(e)}")


# ==========================================
# Prepress PDF Engine Endpoints (Task 2)
# ==========================================

from engine import pdf_engine
from pydantic import BaseModel
from typing import Dict, Any

class PreviewRequest(BaseModel):
    template_config: Optional[Dict[str, Any]] = None
    record_data: Optional[Dict[str, Any]] = None
    trainer_id: Optional[str] = None
    show_trim_guide: bool = True
    dpi: int = 150


@app.post("/api/pdf/inspect-boxes")
async def inspect_boxes_endpoint(file: UploadFile = File(...)):
    """
    Inspects prepress boxes (MediaBox, BleedBox, TrimBox, CropBox) of an uploaded base PDF.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="الملف فارغ")
    try:
        boxes = pdf_engine.inspect_pdf_boxes(content)
        return boxes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل قراءة أبعاد PDF: {str(e)}")


@app.get("/api/preview-certificate")
async def preview_certificate_get(show_trim_guide: bool = True, dpi: int = 150):
    """
    GET preview endpoint rendering a high-DPI sample certificate with TrimBox guides.
    """
    default_config = {
        "name": "Default_Template",
        "page_setup": {"width_mm": 297.0, "height_mm": 210.0, "bleed_mm": 3.0},
        "fields": [
            {
                "id": "certificate_title",
                "default_text": "شهادة إتمام برنامج تدريبي",
                "x_mm": 40.0, "y_mm": 35.0, "width_mm": 217.0, "height_mm": 20.0,
                "font_family": "Cairo Regular", "font_size": 34.0,
                "color": "#004B87", "horizontal_align": "center", "vertical_align": "middle"
            },
            {
                "id": "trainee_label",
                "default_text": "تُمنح هذه الشهادة تقديراً لاجتياز المتدرب/ـة بنجاح:",
                "x_mm": 40.0, "y_mm": 65.0, "width_mm": 217.0, "height_mm": 12.0,
                "font_family": "Cairo Regular", "font_size": 14.0,
                "color": "#64748B", "horizontal_align": "center", "vertical_align": "middle"
            },
            {
                "id": "trainee_name",
                "default_text": "اسم المتدرب",
                "x_mm": 40.0, "y_mm": 80.0, "width_mm": 217.0, "height_mm": 24.0,
                "font_family": "Cairo Regular", "font_size": 32.0,
                "color": {"c": 0, "m": 0, "y": 0, "k": 100}, "horizontal_align": "center",
                "vertical_align": "middle", "max_shrink_percent": 25.0
            },
            {
                "id": "course_desc",
                "default_text": "في المسار المتقدم للتصميم الطباعي وإدارة بيانات الشهادات فائقة الدقة",
                "x_mm": 40.0, "y_mm": 110.0, "width_mm": 217.0, "height_mm": 14.0,
                "font_family": "Cairo Regular", "font_size": 15.0,
                "color": "#1E293B", "horizontal_align": "center", "vertical_align": "middle"
            },
            {
                "id": "training_date",
                "default_text": "تاريخ الاعتماد: 2026-10-29",
                "x_mm": 35.0, "y_mm": 155.0, "width_mm": 80.0, "height_mm": 12.0,
                "font_family": "Cairo Regular", "font_size": 13.0,
                "color": "#475569", "horizontal_align": "right", "vertical_align": "middle"
            }
        ],
        "signature_frame": {
            "id": "trainer_signature",
            "x_mm": 195.0, "y_mm": 140.0, "width_mm": 70.0, "height_mm": 32.0,
            "baseline_offset_mm": 0.0
        }
    }
    sample_data = {
        "trainee_name": "اسم المتدرب",
        "training_date": "تاريخ الاعتماد: 2026-10-29"
    }
    png_bytes, metrics = pdf_engine.render_certificate_preview(
        default_config, sample_data, show_trim_guide=show_trim_guide, dpi=dpi, return_metrics=True
    )
    headers = {
        "X-Text-Shrunk": "true" if metrics.get("is_shrunk") else "false",
        "X-Shrink-Percent": str(metrics.get("max_shrink_percent", 0.0)),
        "X-Text-Overflow": "true" if metrics.get("is_overflow") else "false",
        "Access-Control-Expose-Headers": "X-Text-Shrunk, X-Shrink-Percent, X-Text-Overflow",
    }
    return Response(content=png_bytes, media_type="image/png", headers=headers)


@app.post("/api/preview-certificate")
async def preview_certificate_post(req: PreviewRequest):
    """
    POST preview endpoint rendering custom template_config and record_data.
    Returns real prepress shrink and overflow metrics via HTTP response headers.
    """
    try:
        config = req.template_config or {
            "page_setup": {"width_mm": 297.0, "height_mm": 210.0, "bleed_mm": 3.0},
            "fields": [
                {
                    "id": "trainee_name", "default_text": "اسم المتدرب التجريبي",
                    "x_mm": 50.0, "y_mm": 85.0, "width_mm": 197.0, "height_mm": 25.0,
                    "font_family": "Cairo Regular", "font_size": 30.0,
                    "color": "#004B87", "horizontal_align": "center"
                }
            ],
            "signature_frame": {
                "id": "sig", "x_mm": 195.0, "y_mm": 140.0, "width_mm": 70.0, "height_mm": 30.0
            }
        }
        data = req.record_data or {}
        if req.trainer_id:
            data["trainer_id"] = req.trainer_id

        png_bytes, metrics = pdf_engine.render_certificate_preview(
            config, data, show_trim_guide=req.show_trim_guide, dpi=req.dpi, return_metrics=True
        )
        headers = {
            "X-Text-Shrunk": "true" if metrics.get("is_shrunk") else "false",
            "X-Shrink-Percent": str(metrics.get("max_shrink_percent", 0.0)),
            "X-Text-Overflow": "true" if metrics.get("is_overflow") else "false",
            "Access-Control-Expose-Headers": "X-Text-Shrunk, X-Shrink-Percent, X-Text-Overflow",
        }
        return Response(content=png_bytes, media_type="image/png", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل توليد المعاينة: {str(e)}")


# ==========================================
# Template Manager Endpoints (Task 3)
# ==========================================

@app.get("/api/templates")
async def get_templates():
    """Returns list of all saved certificate templates."""
    return {"templates": template_manager.load_templates()}


@app.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    """Retrieves single template configuration by ID."""
    tpl = template_manager.get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="القالب غير موجود")
    return tpl


@app.post("/api/templates")
async def save_template_endpoint(template: Dict[str, Any]):
    """Creates or updates a certificate template configuration."""
    try:
        saved = template_manager.save_template(template)
        return {"message": "تم حفظ القالب بنجاح", "template": saved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل حفظ القالب: {str(e)}")


@app.post("/api/templates/{template_id}/duplicate")
async def duplicate_template_endpoint(template_id: str):
    """Clones an existing template with a new ID."""
    cloned = template_manager.duplicate_template(template_id)
    if not cloned:
        raise HTTPException(status_code=404, detail="القالب غير موجود للنسخ")
    return {"message": "تم نسخ القالب بنجاح", "template": cloned}


@app.delete("/api/templates/{template_id}")
async def delete_template_endpoint(template_id: str):
    """Deletes a certificate template."""
    success = template_manager.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="القالب غير موجود")
    return {"message": "تم حذف القالب بنجاح", "template_id": template_id}


@app.post("/api/templates/upload-base")
async def upload_base_pdf(file: UploadFile = File(...)):
    """
    Uploads a real user certificate PDF, extracts TrimBox & BleedBox metadata,
    and generates a high-res preview image for the visual canvas.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="الملف فارغ")
    try:
        info = template_manager.save_uploaded_base_pdf(content, file.filename or "certificate_base.pdf")
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل معالجة ملف PDF الأساسي: {str(e)}")


@app.get("/api/templates/base/{filename}")
async def get_base_pdf(filename: str):
    """Serves uploaded or default base PDF file."""
    p = template_manager.get_base_pdf_path(filename)
    if not p or not p.exists():
        raise HTTPException(status_code=404, detail="ملف PDF غير موجود")
    return FileResponse(str(p), media_type="application/pdf")


@app.get("/api/templates/base-preview/{filename}")
async def get_base_preview(filename: str):
    """Serves high-res PNG preview of base PDF page."""
    p = template_manager.get_base_preview_path(filename)
    if not p or not p.exists():
        raise HTTPException(status_code=404, detail="صورة معاينة PDF غير موجودة")
    return FileResponse(str(p), media_type="image/png")



@app.get("/api/companies")
async def get_companies():
    """Returns unique list of all companies from templates."""
    return {"companies": template_manager.list_companies()}


class GoogleSheetRequest(BaseModel):
    sheet_url: str
    name_col: Optional[str] = ""
    time_col: Optional[str] = ""
    trainer_name: Optional[str] = ""
    filter_date: Optional[str] = None
    target_date_format: Optional[str] = "YYYY-MM-DD"


@app.post("/api/data/google-sheet")
async def fetch_google_sheet_endpoint(req: GoogleSheetRequest):
    """
    Fetches live Google Sheet, strips time portion from Timestamp,
    and returns unique dates and clean records.
    """
    try:
        data = await data_loader.fetch_google_sheet_records(
            sheet_url=req.sheet_url,
            name_col=req.name_col or "",
            time_col=req.time_col or "",
            trainer_name=req.trainer_name or "",
            filter_date=req.filter_date,
            target_date_format=req.target_date_format or "YYYY-MM-DD",
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/data/parse-file")
async def parse_file_endpoint(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
    name_col: Optional[str] = Form(""),
    date_col: Optional[str] = Form(""),
    custom_col: Optional[str] = Form(""),
    fixed_date: Optional[str] = Form(""),
    trainer_name: Optional[str] = Form(""),
    filter_date: Optional[str] = Form(None),
    target_date_format: Optional[str] = Form("YYYY-MM-DD"),
):
    """
    Parses uploaded Excel (.xlsx, .xls) or CSV file with sheet selection,
    auto-column detection, and text hygiene.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="الملف فارغ")
    try:
        data = data_loader.parse_uploaded_file_records(
            file_bytes=content,
            filename=file.filename or "data.xlsx",
            sheet_name=sheet_name,
            name_col=name_col or "",
            date_col=date_col or "",
            custom_col=custom_col or "",
            fixed_date=fixed_date or "",
            trainer_name=trainer_name or "",
            filter_date=filter_date,
            target_date_format=target_date_format or "YYYY-MM-DD",
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# Excel Template Endpoint
# ==========================================

@app.get("/api/excel-template")
async def download_excel_template():
    """
    Generates and downloads the certified standard Excel template (.xlsx)
    pre-formatted with columns:
      - Trainee_Name | اسم المتدرب
      - Training_Date | تاريخ التدريب
      - Custom_Text | نص إضافي
    """
    try:
        excel_stream = generate_standard_excel_template()
        filename = "CertFlow_Standard_Template.xlsx"
        return StreamingResponse(
            excel_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل إنشاء قالب الإكسل: {str(e)}")


# ==========================================
# Batch Export & Apps Script Sync Endpoints
# ==========================================

class BatchExportRequest(BaseModel):
    template_config: Optional[Dict[str, Any]] = None
    template_id: Optional[str] = None
    records: List[Dict[str, Any]]
    export_mode: str = "combined_pdf"  # "combined_pdf" | "individual_pdfs_zip" | "individual_jpegs_zip"
    range_str: Optional[str] = "ALL"
    filename_prefix: Optional[str] = "CertFlow"
    dpi: int = 300
    webhook_url: Optional[str] = None
    apps_script_url: Optional[str] = None
    trainer_id: Optional[str] = None
    sheet_url: Optional[str] = None


class AppsScriptSyncRequest(BaseModel):
    script_url: str
    template_name: str
    updates: List[Dict[str, str]]
    sheet_url: Optional[str] = None


@app.post("/api/trainer/sync-apps-script")
async def sync_apps_script_endpoint(req: AppsScriptSyncRequest):
    """
    Synchronizes generated certificate template names back to Google Apps Script (doPost).
    Expected payload: {"sheet_url": "...", "updates": [{"trainee_name": "...", "template_name": "..."}, ...]}
    """
    clean_url = req.script_url.strip()
    if not clean_url:
        raise HTTPException(status_code=400, detail="رابط Google Apps Script مطلوب")

    try:
        payload = {
            "sheet_url": req.sheet_url or "",
            "updates": req.updates,
            "template_name": req.template_name,
            "count": len(req.updates)
        }
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers={"Content-Type": "application/json"}) as client:
            res = await client.post(clean_url, json=payload)
            return {
                "status": "success",
                "script_status": res.status_code,
                "updated_count": len(req.updates),
                "message": f"تم إرسال {len(req.updates)} تحديث بنجاح لتطبيق Google Apps Script"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل إرسال التحديثات لـ Google Apps Script: {e}")


@app.post("/api/export-batch")
async def export_batch_endpoint(req: BatchExportRequest):
    """
    Executes high-speed prepress batch export for certificates.
    Returns generated PDF or ZIP as a direct browser download.
    Also handles automatic doPost write-back to Google Apps Script.
    """
    try:
        config = req.template_config
        if not config and req.template_id:
            config = template_manager.get_template(req.template_id)
        if not config:
            raise HTTPException(status_code=400, detail="يرجى تحديد إعدادات قالب الشهادة")
        if not req.records:
            raise HTTPException(status_code=400, detail="قائمة سجلات البيانات فارغة")

        # Resolve target Google Apps Script URL and Sheet URL
        target_apps_script = req.apps_script_url
        target_sheet_url = req.sheet_url
        target_trainer_id = req.trainer_id or (req.records[0].get("trainer_id") if req.records else None)
        if target_trainer_id:
            t = trainer_manager.get_trainer(target_trainer_id)
            if t:
                if not target_sheet_url and t.get("sheet_url"):
                    target_sheet_url = t["sheet_url"]
                if not target_apps_script:
                    if t.get("script_url"):
                        target_apps_script = t["script_url"]
                    elif t.get("sheet_url") and ("script.google.com" in t["sheet_url"] or "script.googleusercontent.com" in t["sheet_url"]):
                        target_apps_script = t["sheet_url"]

        # If apps_script is still not resolved, check if any trainer has a script_url configured
        if not target_apps_script:
            for trainer in trainer_manager.load_trainers():
                if trainer.get("script_url"):
                    target_apps_script = trainer["script_url"]
                    break

        result = batch_exporter.execute_batch_export(
            template_config=config,
            records=req.records,
            export_mode=req.export_mode,
            range_str=req.range_str,
            filename_prefix=req.filename_prefix or "CertFlow",
            dpi=req.dpi or 300,
            webhook_url=req.webhook_url,
            apps_script_url=target_apps_script,
            sheet_url=target_sheet_url,
        )

        file_path = result["file_path"]
        filename = result["filename"]
        media_type = result["media_type"]
        apps_script_synced = "true" if result.get("apps_script_synced") else "false"

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition, X-Exported-Count, X-Warnings-Count, X-Apps-Script-Synced",
                "X-Exported-Count": str(result["exported_count"]),
                "X-Warnings-Count": str(result["warnings_count"]),
                "X-Apps-Script-Synced": apps_script_synced,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل تصدير الشهادات: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

