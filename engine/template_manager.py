"""
engine/template_manager.py
Manages Certificate Template configurations (.json) and Base PDF assets in ./templates_store/
Handles base PDF uploads, high-res canvas previews, prepress box inspection, and template CRUD.
"""

import os
import json
import time
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import pymupdf
from engine import pdf_engine, github_sync

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_STORE = BASE_DIR / "templates_store"
BASES_DIR = TEMPLATES_STORE / "bases"
TEMPLATES_JSON_PATH = TEMPLATES_STORE / "templates.json"


def save_templates_store(templates: List[Dict[str, Any]], sync: bool = True) -> None:
    TEMPLATES_STORE.mkdir(parents=True, exist_ok=True)
    BASES_DIR.mkdir(parents=True, exist_ok=True)
    with open(TEMPLATES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)
    if sync:
        github_sync.push_file_async(
            TEMPLATES_JSON_PATH,
            commit_message=f"Auto-sync: update templates.json ({len(templates)} templates)",
        )


def ensure_store_dirs() -> None:
    TEMPLATES_STORE.mkdir(parents=True, exist_ok=True)
    BASES_DIR.mkdir(parents=True, exist_ok=True)
    if not TEMPLATES_JSON_PATH.exists():
        save_templates_store([], sync=False)


def create_default_template_config() -> Dict[str, Any]:
    """Generates the default factory template configuration."""
    base_default_name = "default_certificate_base.pdf"
    base_file = TEMPLATES_STORE / base_default_name
    if not base_file.exists():
        doc = pdf_engine.create_default_certificate_base()
        doc.save(str(base_file))
        doc.close()
        github_sync.push_file_async(
            base_file,
            commit_message=f"Auto-sync: default base PDF {base_default_name}",
        )

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    return {
        "id": "tpl_default",
        "name": "قالب الشهادة الافتراضي (Default Master Template)",
        "company": "",
        "base_pdf_filename": base_default_name,
        "base_pdf_url": f"/api/templates/base/{base_default_name}",
        "base_preview_url": f"/api/templates/base-preview/{base_default_name}",
        "page_setup": {
            "width_mm": 297.0,
            "height_mm": 210.0,
            "bleed_mm": 3.0,
            "is_landscape": True,
        },
        "boxes_metadata": {
            "trimbox": {"width_mm": 297.0, "height_mm": 210.0},
            "bleed_offsets_mm": {"top": 3.0, "bottom": 3.0, "left": 3.0, "right": 3.0},
        },
        "fields": [
            {
                "id": "certificate_title",
                "label": "عنوان الشهادة",
                "default_text": "شهادة إتمام برنامج تدريبي",
                "x_mm": 35.0,
                "y_mm": 35.0,
                "width_mm": 227.0,
                "height_mm": 20.0,
                "font_family": "Cairo Regular",
                "font_size": 34.0,
                "color": "#004B87",
                "horizontal_align": "center",
                "vertical_align": "middle",
                "baseline_offset_mm": 0.0,
                "max_shrink_percent": 15.0,
                "direction": "auto",
                "is_locked": False,
            },
            {
                "id": "trainee_label",
                "label": "نص التقديم",
                "default_text": "تُمنح هذه الشهادة تقديراً لاجتياز المتدرب/ـة بنجاح:",
                "x_mm": 40.0,
                "y_mm": 65.0,
                "width_mm": 217.0,
                "height_mm": 12.0,
                "font_family": "Cairo Regular",
                "font_size": 14.0,
                "color": "#64748B",
                "horizontal_align": "center",
                "vertical_align": "middle",
                "baseline_offset_mm": 0.0,
                "max_shrink_percent": 10.0,
                "direction": "auto",
                "is_locked": True,
            },
            {
                "id": "trainee_name",
                "label": "اسم المتدرب",
                "default_text": "اسم المتدرب",
                "x_mm": 30.0,
                "y_mm": 80.0,
                "width_mm": 237.0,
                "height_mm": 24.0,
                "font_family": "Cairo Regular",
                "font_size": 32.0,
                "color": {"c": 0, "m": 0, "y": 0, "k": 100},  # Pure Print Black
                "horizontal_align": "center",
                "vertical_align": "middle",
                "baseline_offset_mm": 0.0,
                "max_shrink_percent": 25.0,
                "direction": "auto",
                "is_locked": False,
            },
            {
                "id": "course_desc",
                "label": "وصف البرنامج",
                "default_text": "في المسار المتقدم للتصميم الطباعي وإدارة بيانات الشهادات فائقة الدقة",
                "x_mm": 40.0,
                "y_mm": 110.0,
                "width_mm": 217.0,
                "height_mm": 14.0,
                "font_family": "Cairo Regular",
                "font_size": 14.5,
                "color": "#1E293B",
                "horizontal_align": "center",
                "vertical_align": "middle",
                "baseline_offset_mm": 0.0,
                "max_shrink_percent": 15.0,
                "direction": "auto",
                "is_locked": False,
            },
            {
                "id": "training_date",
                "label": "تاريخ الاعتماد",
                "default_text": "تاريخ الاعتماد: 2026-10-29",
                "x_mm": 35.0,
                "y_mm": 155.0,
                "width_mm": 80.0,
                "height_mm": 12.0,
                "font_family": "Cairo Regular",
                "font_size": 13.0,
                "color": "#475569",
                "horizontal_align": "right",
                "vertical_align": "middle",
                "baseline_offset_mm": 0.0,
                "max_shrink_percent": 10.0,
                "direction": "auto",
                "is_locked": False,
            },
        ],
        "signature_frames": [
            {
                "id": "trainer_signature",
                "label": "توقيع المدرب",
                "x_mm": 195.0,
                "y_mm": 140.0,
                "width_mm": 68.0,
                "height_mm": 30.0,
                "baseline_offset_mm": 0.0,
                "anchor_mode": "bottom_center",
                "scale": 100.0,
                "blend_multiply": True,
            }
        ],
        "created_at": now,
        "updated_at": now,
    }


def load_templates() -> List[Dict[str, Any]]:
    ensure_store_dirs()
    if not TEMPLATES_JSON_PATH.exists():
        return []
    try:
        with open(TEMPLATES_JSON_PATH, "r", encoding="utf-8") as f:
            templates = json.load(f)
            if not isinstance(templates, list):
                templates = []
            return templates
    except Exception as e:
        print(f"Error loading templates.json: {e}")
        return []



def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    templates = load_templates()
    for t in templates:
        if t.get("id") == template_id:
            return t
    return None


def list_companies() -> List[str]:
    templates = load_templates()
    companies = set()
    for t in templates:
        comp = (t.get("company") or "").strip()
        if comp:
            companies.add(comp)
    return sorted(list(companies))


def save_template(template_data: Dict[str, Any]) -> Dict[str, Any]:
    ensure_store_dirs()
    templates = load_templates()
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    t_id = template_data.get("id")
    if not t_id:
        t_id = f"tpl_{uuid.uuid4().hex[:8]}"
        template_data["id"] = t_id
        template_data["created_at"] = now

    template_data["updated_at"] = now

    # Check if updating existing
    updated = False
    for idx, tpl in enumerate(templates):
        if tpl.get("id") == t_id:
            templates[idx] = template_data
            updated = True
            break

    if not updated:
        templates.append(template_data)

    save_templates_store(templates)
    return template_data


def duplicate_template(template_id: str) -> Optional[Dict[str, Any]]:
    tpl = get_template(template_id)
    if not tpl:
        return None

    cloned = json.loads(json.dumps(tpl))
    new_id = f"tpl_{uuid.uuid4().hex[:8]}"
    cloned["id"] = new_id
    cloned["name"] = f"{tpl.get('name', 'قالب')} (نسخة)"
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    cloned["created_at"] = now
    cloned["updated_at"] = now

    return save_template(cloned)


def delete_template(template_id: str) -> bool:
    templates = load_templates()
    target = next((t for t in templates if t.get("id") == template_id), None)
    filtered = [t for t in templates if t.get("id") != template_id]
    if len(filtered) == len(templates):
        return False
    save_templates_store(filtered, sync=True)

    # Check if this template used a custom base PDF that is no longer used by any remaining template
    if target:
        base_filename = target.get("base_pdf_filename")
        if base_filename and base_filename != "default_certificate_base.pdf":
            still_used = any(t.get("base_pdf_filename") == base_filename for t in filtered)
            if not still_used:
                # Delete base PDF
                base_path = get_base_pdf_path(base_filename)
                if base_path and base_path.exists():
                    try:
                        base_path.unlink()
                    except Exception:
                        pass
                    github_sync.delete_file_async(
                        base_path,
                        commit_message=f"Auto-sync: delete base PDF {base_filename}",
                    )
                # Delete preview
                preview_filename = Path(base_filename).stem + "_preview.png"
                preview_path = get_base_preview_path(preview_filename)
                if preview_path and preview_path.exists():
                    try:
                        preview_path.unlink()
                    except Exception:
                        pass
                    github_sync.delete_file_async(
                        preview_path,
                        commit_message=f"Auto-sync: delete base preview {preview_filename}",
                    )
    return True


def save_uploaded_base_pdf(
    file_bytes: bytes, original_filename: str = "certificate_base.pdf"
) -> Dict[str, Any]:
    """
    Saves an uploaded real certificate PDF into templates_store/bases/
    Extracts prepress box metadata and renders a 150 DPI page preview for the canvas.
    """
    ensure_store_dirs()
    unique_id = uuid.uuid4().hex[:10]
    safe_stem = Path(original_filename).stem.replace(" ", "_")[:30]
    filename = f"base_{unique_id}_{safe_stem}.pdf"
    target_path = BASES_DIR / filename

    with open(target_path, "wb") as f:
        f.write(file_bytes)

    # Inspect prepress boxes
    boxes = pdf_engine.inspect_pdf_boxes(str(target_path))

    # Render page 0 preview image for web canvas
    preview_filename = f"base_{unique_id}_{safe_stem}_preview.png"
    preview_path = BASES_DIR / preview_filename

    try:
        doc = pymupdf.open(str(target_path))
        page = doc[0]
        # Render high-resolution preview for interactive canvas (150 DPI)
        pix = page.get_pixmap(dpi=150)
        pix.save(str(preview_path))
        preview_width = pix.width
        preview_height = pix.height
        doc.close()
    except Exception as e:
        print(f"Error rendering base PDF preview: {e}")
        preview_filename = ""
        preview_width = 0
        preview_height = 0

    # Auto-sync uploaded base PDF and preview image to GitHub in background thread
    github_sync.push_file_async(
        target_path,
        commit_message=f"Auto-sync: upload base PDF {filename}",
    )
    if preview_filename and preview_path.exists():
        github_sync.push_file_async(
            preview_path,
            commit_message=f"Auto-sync: base PDF preview {preview_filename}",
        )

    trim_mm = boxes.get("trimbox", {})
    bleed_offsets = boxes.get("bleed_offsets_mm", {})

    return {
        "filename": filename,
        "original_filename": original_filename,
        "path": str(target_path.resolve()),
        "base_pdf_url": f"/api/templates/base/{filename}",
        "preview_filename": preview_filename,
        "preview_url": f"/api/templates/base-preview/{preview_filename}" if preview_filename else "",
        "preview_width": preview_width,
        "preview_height": preview_height,
        "boxes": boxes,
        "page_setup": {
            "width_mm": trim_mm.get("width_mm", 297.0),
            "height_mm": trim_mm.get("height_mm", 210.0),
            "bleed_mm": bleed_offsets.get("left", 3.0),
            "is_landscape": boxes.get("is_landscape", True),
        },
        "bleed_offsets_mm": bleed_offsets,
    }


def get_base_pdf_path(filename: str) -> Optional[Path]:
    """Finds base PDF either in bases/ or templates_store/ directly."""
    p1 = BASES_DIR / filename
    if p1.exists():
        return p1
    p2 = TEMPLATES_STORE / filename
    if p2.exists():
        return p2
    return None


def get_base_preview_path(filename: str) -> Optional[Path]:
    p = BASES_DIR / filename
    if p.exists():
        return p
    return None
