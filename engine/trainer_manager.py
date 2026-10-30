"""
engine/trainer_manager.py
CRUD engine for Trainer Profiles with smart signature processing:
- Case 1: Pure Vector PDF (detects tight drawings bounding box & sets cropbox)
- Case 2: Pre-Transparent PNG (preserves alpha without luminance filtering, tight crop)
- Case 3: Opaque Paper JPG/PNG (luminance paper removal & tight crop)
"""

import json
import os
import re
import time
import uuid
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
import numpy as np
from PIL import Image
import pymupdf
from engine import github_sync

BASE_DIR = Path(__file__).resolve().parent.parent
TRAINERS_STORE_DIR = BASE_DIR / "trainers_store"
SIGNATURES_DIR = TRAINERS_STORE_DIR / "signatures"
TRAINERS_FILE = TRAINERS_STORE_DIR / "trainers.json"


def ensure_store_dirs() -> None:
    TRAINERS_STORE_DIR.mkdir(parents=True, exist_ok=True)
    SIGNATURES_DIR.mkdir(parents=True, exist_ok=True)
    if not TRAINERS_FILE.exists():
        # FIX 1: If GitHub sync is configured but hydration has not succeeded,
        # do NOT create an empty trainers.json to prevent wiping historical remote data!
        if github_sync.is_configured() and not github_sync.is_hydration_healthy():
            return
        with open(TRAINERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def get_pdf_drawings_bbox(page: pymupdf.Page) -> pymupdf.Rect:
    """
    Computes tight bounding box of vector paths, drawings, text, and images on a PDF page.
    """
    bbox = None

    # 1. Vector drawings and strokes
    drawings = page.get_drawings()
    for d in drawings:
        r = d.get("rect")
        if r and r.is_valid and not r.is_empty:
            bbox = r if bbox is None else (bbox | r)

    # 2. Text blocks
    text_blocks = page.get_text("blocks")
    for b in text_blocks:
        r = pymupdf.Rect(b[:4])
        if r and r.is_valid and not r.is_empty:
            bbox = r if bbox is None else (bbox | r)

    # 3. Image blocks
    for img in page.get_images():
        for r in page.get_image_rects(img[0]):
            if r and r.is_valid and not r.is_empty:
                bbox = r if bbox is None else (bbox | r)

    # 4. Fallback to bboxlog
    if bbox is None or bbox.is_empty:
        bboxlog = page.get_bboxlog()
        for item in bboxlog:
            r = pymupdf.Rect(item[1])
            if r and r.is_valid and not r.is_empty:
                bbox = r if bbox is None else (bbox | r)

    # 5. Final fallback to page rect
    if bbox is None or bbox.is_empty:
        bbox = page.rect

    # Add 2pt safety margin clamped to page boundaries
    pad = 2.0
    tight_rect = pymupdf.Rect(
        max(page.rect.x0, bbox.x0 - pad),
        max(page.rect.y0, bbox.y0 - pad),
        min(page.rect.x1, bbox.x1 + pad),
        min(page.rect.y1, bbox.y1 + pad),
    )
    return tight_rect


def process_vector_pdf_signature(
    pdf_bytes: bytes, prefix: str = "sig"
) -> Dict[str, Any]:
    """
    Case 1: Vector PDF Signature.
    Preserves vector strokes, computes tight drawings CropBox,
    and generates a transparent PNG thumbnail for UI display.
    """
    ensure_store_dirs()
    unique_id = uuid.uuid4().hex[:10]
    pdf_filename = f"{prefix}_{unique_id}.pdf"
    thumb_filename = f"{prefix}_{unique_id}_thumb.png"

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    orig_rect = page.rect
    tight_bbox = get_pdf_drawings_bbox(page)

    # Set page cropbox so only the tight vector strokes are visible
    page.set_cropbox(tight_bbox)

    # Save tight vector PDF
    pdf_target_path = SIGNATURES_DIR / pdf_filename
    doc.save(str(pdf_target_path), garbage=4, deflate=True)

    # Generate transparent PNG thumbnail at 150 DPI for UI display
    thumb_target_path = SIGNATURES_DIR / thumb_filename
    pix = page.get_pixmap(alpha=True, dpi=150)
    pix.save(str(thumb_target_path))

    # Auto-sync vector signature files to GitHub with verified commits
    if not prefix.startswith("preview_temp"):
        github_sync.sync_file_push(
            pdf_target_path,
            commit_message=f"Auto-sync: vector signature PDF {pdf_filename}",
            raise_on_error=True,
        )
        github_sync.sync_file_push(
            thumb_target_path,
            commit_message=f"Auto-sync: signature thumbnail {thumb_filename}",
            raise_on_error=True,
        )

    return {
        "filename": pdf_filename,
        "signature_type": "pdf",
        "is_vector": True,
        "width": round(tight_bbox.width, 1),
        "height": round(tight_bbox.height, 1),
        "original_width": round(orig_rect.width, 1),
        "original_height": round(orig_rect.height, 1),
        "thumbnail_filename": thumb_filename,
        "thumbnail_url": f"/api/trainers/signature/{thumb_filename}",
        "url": f"/api/trainers/signature/{pdf_filename}",
        "path": str(pdf_target_path.resolve()),
    }


def process_raster_signature(
    image_bytes: bytes,
    prefix: str = "sig",
    high_threshold: float = 225.0,
    low_threshold: float = 140.0,
) -> Dict[str, Any]:
    """
    Handles raster signatures:
    - Case 2: Pre-Transparent PNG (preserves alpha without luminance filtering, tight crop)
    - Case 3: Opaque Paper JPG/PNG (luminance paper removal & tight crop)
    """
    ensure_store_dirs()
    img = Image.open(BytesIO(image_bytes))
    orig_size = img.size

    # Check if image already has alpha transparency (Case 2)
    has_alpha = False
    if img.mode in ("RGBA", "LA") or img.info.get("transparency") is not None:
        rgba_test = img.convert("RGBA")
        a_test = np.array(rgba_test)[:, :, 3]
        # If more than 0.5% of pixels are transparent, it's pre-transparent
        if np.mean(a_test < 240) > 0.005:
            has_alpha = True

    unique_id = uuid.uuid4().hex[:10]
    filename = f"{prefix}_{unique_id}.png"
    target_path = SIGNATURES_DIR / filename

    if has_alpha:
        # Case 2: Already Transparent PNG. Preserve color & alpha, ONLY auto-crop empty margins!
        rgba_img = img.convert("RGBA")
        arr = np.array(rgba_img)
        alpha = arr[:, :, 3]

        alpha_mask = alpha > 15
        if np.any(alpha_mask):
            y_indices, x_indices = np.where(alpha_mask)
            pad = 2
            top = max(0, int(y_indices.min()) - pad)
            bottom = min(img.height, int(y_indices.max()) + 1 + pad)
            left = max(0, int(x_indices.min()) - pad)
            right = min(img.width, int(x_indices.max()) + 1 + pad)
            cropped = rgba_img.crop((left, top, right, bottom))
        else:
            cropped = rgba_img

        cropped.save(target_path, format="PNG", optimize=True)
        if not prefix.startswith("preview_temp"):
            github_sync.sync_file_push(
                target_path,
                commit_message=f"Auto-sync: transparent signature PNG {filename}",
                raise_on_error=True,
            )
        return {
            "filename": filename,
            "signature_type": "png",
            "is_vector": False,
            "width": cropped.width,
            "height": cropped.height,
            "original_width": orig_size[0],
            "original_height": orig_size[1],
            "thumbnail_filename": filename,
            "thumbnail_url": f"/api/trainers/signature/{filename}",
            "url": f"/api/trainers/signature/{filename}",
            "path": str(target_path.resolve()),
        }

    # Case 3: Opaque JPG / PNG with paper background. Run luminance thresholding & tight crop
    rgba_img = img.convert("RGBA")
    arr = np.array(rgba_img, dtype=np.float32)

    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    luminance = 0.299 * r + 0.587 * g + 0.114 * b

    # High luminance (paper) -> 0 alpha; Low luminance (ink) -> 255 alpha
    calc_alpha = np.clip(
        (high_threshold - luminance) / (high_threshold - low_threshold) * 255.0,
        0,
        255,
    )
    final_alpha = np.minimum(calc_alpha, a)

    # De-halo: darken semi-transparent pixels so no white paper fringe remains around dark ink
    mask = final_alpha > 0
    norm_alpha = np.zeros_like(final_alpha)
    norm_alpha[mask] = final_alpha[mask] / 255.0

    for c in range(3):
        arr[:, :, c] = np.where(mask, arr[:, :, c] * np.power(norm_alpha, 0.4), 0)

    arr[:, :, 3] = final_alpha
    processed = Image.fromarray(np.uint8(arr), mode="RGBA")

    # Tight crop
    alpha_mask = final_alpha > 15
    if np.any(alpha_mask):
        y_indices, x_indices = np.where(alpha_mask)
        pad = 2
        top = max(0, int(y_indices.min()) - pad)
        bottom = min(img.height, int(y_indices.max()) + 1 + pad)
        left = max(0, int(x_indices.min()) - pad)
        right = min(img.width, int(x_indices.max()) + 1 + pad)
        cropped = processed.crop((left, top, right, bottom))
    else:
        cropped = processed

    cropped.save(target_path, format="PNG", optimize=True)
    if not prefix.startswith("preview_temp"):
        github_sync.sync_file_push(
            target_path,
            commit_message=f"Auto-sync: signature PNG {filename}",
            raise_on_error=True,
        )
    return {
        "filename": filename,
        "signature_type": "png",
        "is_vector": False,
        "width": cropped.width,
        "height": cropped.height,
        "original_width": orig_size[0],
        "original_height": orig_size[1],
        "thumbnail_filename": filename,
        "thumbnail_url": f"/api/trainers/signature/{filename}",
        "url": f"/api/trainers/signature/{filename}",
        "path": str(target_path.resolve()),
    }


def save_processed_signature(
    file_bytes: bytes,
    filename_hint: str = "",
    prefix: str = "sig",
) -> Dict[str, Any]:
    """
    Unified entry point for signature ingestion:
    Supports Vector PDF, Transparent PNG, and Opaque JPG/PNG.
    """
    ensure_store_dirs()
    is_pdf = (
        file_bytes.startswith(b"%PDF")
        or filename_hint.lower().endswith(".pdf")
    )
    if is_pdf:
        return process_vector_pdf_signature(file_bytes, prefix=prefix)
    else:
        return process_raster_signature(file_bytes, prefix=prefix)


def load_trainers() -> List[Dict[str, Any]]:
    ensure_store_dirs()
    try:
        with open(TRAINERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_trainers_store(trainers: List[Dict[str, Any]], sync: bool = True) -> None:
    ensure_store_dirs()
    with open(TRAINERS_FILE, "w", encoding="utf-8") as f:
        json.dump(trainers, f, ensure_ascii=False, indent=2)
    if sync:
        github_sync.sync_file_push(
            TRAINERS_FILE,
            commit_message=f"Auto-sync: update trainers.json ({len(trainers)} trainers)",
            raise_on_error=True,
        )


def list_trainers() -> List[Dict[str, Any]]:
    return load_trainers()


def get_trainer(trainer_id: str) -> Optional[Dict[str, Any]]:
    trainers = load_trainers()
    for t in trainers:
        if t.get("id") == trainer_id:
            return t
    return None


def create_trainer(
    name: str,
    sheet_url: str = "",
    name_col: str = "الاسم",
    time_col: str = "Timestamp",
    scale: float = 100.0,
    signature_bytes: Optional[bytes] = None,
    signature_filename: Optional[str] = None,
    script_url: str = "",
) -> Dict[str, Any]:
    # FIX 1: Emergency read-only check
    if github_sync.is_configured() and not github_sync.is_hydration_healthy():
        raise RuntimeError(
            "Storage is in read-only emergency mode: remote trainers could not be verified on startup. "
            "Mutations are blocked to prevent data loss. Please trigger a manual sync pull via /api/sync/pull."
        )

    # FIX 2: Domain-level lock for full read-modify-write-push lifecycle
    with github_sync.store_lock("trainers", TRAINERS_STORE_DIR / ".trainers.lock"):
        ensure_store_dirs()
        trainers = load_trainers()

        trainer_id = f"tr_{uuid.uuid4().hex[:8]}"
        sig_info = None

        if signature_bytes and len(signature_bytes) > 0:
            sig_info = save_processed_signature(
                signature_bytes,
                filename_hint=signature_filename or "",
                prefix=trainer_id,
            )

        now = time.strftime("%Y-%m-%d %H:%M:%S")

        trainer_record = {
            "id": trainer_id,
            "name": name.strip(),
            "sheet_url": sheet_url.strip(),
            "script_url": script_url.strip() if script_url else "",
            "name_col": name_col.strip() or "الاسم",
            "time_col": time_col.strip() or "Timestamp",
            "scale": float(scale),
            "signature_filename": sig_info["filename"] if sig_info else None,
            "signature_type": sig_info["signature_type"] if sig_info else None,
            "is_vector": sig_info.get("is_vector", False) if sig_info else False,
            "signature_url": sig_info["url"] if sig_info else None,
            "thumbnail_url": sig_info.get("thumbnail_url") if sig_info else None,
            "signature_width": sig_info["width"] if sig_info else None,
            "signature_height": sig_info["height"] if sig_info else None,
            "created_at": now,
            "updated_at": now,
        }

        trainers.append(trainer_record)
        save_trainers_store(trainers, sync=True)
        return trainer_record


def update_trainer(
    trainer_id: str,
    name: Optional[str] = None,
    sheet_url: Optional[str] = None,
    name_col: Optional[str] = None,
    time_col: Optional[str] = None,
    scale: Optional[float] = None,
    signature_bytes: Optional[bytes] = None,
    signature_filename: Optional[str] = None,
    script_url: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    # FIX 1: Emergency read-only check
    if github_sync.is_configured() and not github_sync.is_hydration_healthy():
        raise RuntimeError(
            "Storage is in read-only emergency mode: remote trainers could not be verified on startup. "
            "Mutations are blocked to prevent data loss. Please trigger a manual sync pull via /api/sync/pull."
        )

    # FIX 2: Domain-level lock
    with github_sync.store_lock("trainers", TRAINERS_STORE_DIR / ".trainers.lock"):
        trainers = load_trainers()
        target_idx = -1
        for idx, t in enumerate(trainers):
            if t.get("id") == trainer_id:
                target_idx = idx
                break

        if target_idx == -1:
            return None

        trainer = trainers[target_idx]

        if name is not None:
            trainer["name"] = name.strip()
        if sheet_url is not None:
            trainer["sheet_url"] = sheet_url.strip()
        if script_url is not None:
            trainer["script_url"] = script_url.strip()
        if name_col is not None:
            trainer["name_col"] = name_col.strip() or "الاسم"
        if time_col is not None:
            trainer["time_col"] = time_col.strip() or "Timestamp"
        if scale is not None:
            trainer["scale"] = float(scale)

        if signature_bytes and len(signature_bytes) > 0:
            # Remove old signature and thumbnail files
            old_filename = trainer.get("signature_filename")
            if old_filename:
                p = SIGNATURES_DIR / old_filename
                github_sync.sync_file_delete(
                    p,
                    commit_message=f"Auto-sync: delete old signature {old_filename}",
                    raise_on_error=False,
                )
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass
                # Check thumbnail file
                thumb_name = p.stem + "_thumb.png"
                p_thumb = SIGNATURES_DIR / thumb_name
                github_sync.sync_file_delete(
                    p_thumb,
                    commit_message=f"Auto-sync: delete old signature thumbnail {thumb_name}",
                    raise_on_error=False,
                )
                if p_thumb.exists():
                    try:
                        p_thumb.unlink()
                    except Exception:
                        pass

            # Save new cleaned signature
            sig_info = save_processed_signature(
                signature_bytes,
                filename_hint=signature_filename or "",
                prefix=trainer_id,
            )
            trainer["signature_filename"] = sig_info["filename"]
            trainer["signature_type"] = sig_info["signature_type"]
            trainer["is_vector"] = sig_info.get("is_vector", False)
            trainer["signature_url"] = sig_info["url"]
            trainer["thumbnail_url"] = sig_info.get("thumbnail_url")
            trainer["signature_width"] = sig_info["width"]
            trainer["signature_height"] = sig_info["height"]

        trainer["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        trainers[target_idx] = trainer
        save_trainers_store(trainers, sync=True)
        return trainer


def delete_trainer(trainer_id: str) -> bool:
    # FIX 1: Emergency read-only check
    if github_sync.is_configured() and not github_sync.is_hydration_healthy():
        raise RuntimeError(
            "Storage is in read-only emergency mode: remote trainers could not be verified on startup. "
            "Deletions are blocked to prevent data loss. Please trigger a manual sync pull via /api/sync/pull."
        )

    # FIX 2: Domain-level lock
    with github_sync.store_lock("trainers", TRAINERS_STORE_DIR / ".trainers.lock"):
        trainers = load_trainers()
        target = None
        remaining = []

        for t in trainers:
            if t.get("id") == trainer_id:
                target = t
            else:
                remaining.append(t)

        if not target:
            return False

        # Delete signature file and thumbnail from GitHub first, then locally
        sig_filename = target.get("signature_filename")
        if sig_filename:
            sig_path = SIGNATURES_DIR / sig_filename
            github_sync.sync_file_delete(
                sig_path,
                commit_message=f"Auto-sync: delete signature {sig_filename}",
                raise_on_error=False,
            )
            if sig_path.exists():
                try:
                    sig_path.unlink()
                except Exception:
                    pass
            thumb_name = sig_path.stem + "_thumb.png"
            p_thumb = SIGNATURES_DIR / thumb_name
            github_sync.sync_file_delete(
                p_thumb,
                commit_message=f"Auto-sync: delete signature thumbnail {thumb_name}",
                raise_on_error=False,
            )
            if p_thumb.exists():
                try:
                    p_thumb.unlink()
                except Exception:
                    pass

        save_trainers_store(remaining, sync=True)
        return True


def get_signature_path(filename: str) -> Optional[Path]:
    ensure_store_dirs()
    safe_name = Path(filename).name
    p = SIGNATURES_DIR / safe_name
    if p.exists() and p.is_file():
        return p
    return None
