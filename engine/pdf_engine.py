"""
engine/pdf_engine.py
Core Prepress PDF Engine for CertFlow Studio.
Handles:
- PDF Boxes inspection (MediaBox, BleedBox, TrimBox) in pt and mm with bleed offsets
- InDesign-matching Top-Left TrimBox coordinate system (x_mm, y_mm, w_mm, h_mm)
- High-precision BiDi typesetting & auto-shrink text rendering
- Bottom-center anchored vector & raster signature placement
- Print-Ready (300 DPI) PDF generation & High-DPI raster preview
"""

import io
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
import pymupdf

from engine import font_manager, text_shaper, trainer_manager

PT_TO_MM = 25.4 / 72.0
MM_TO_PT = 72.0 / 25.4


def pt_to_mm(val_pt: float) -> float:
    return round(val_pt * PT_TO_MM, 3)


def mm_to_pt(val_mm: float) -> float:
    return val_mm * MM_TO_PT


def inspect_pdf_boxes(pdf_source: Union[str, Path, bytes]) -> Dict[str, Any]:
    """
    Extracts MediaBox, BleedBox, CropBox, and TrimBox from Page 0 in points and mm,
    along with calculated bleed offsets.
    """
    if isinstance(pdf_source, (str, Path)):
        doc = pymupdf.open(str(pdf_source))
    else:
        doc = pymupdf.open(stream=pdf_source, filetype="pdf")

    if len(doc) == 0:
        raise ValueError("PDF document contains no pages.")

    page = doc[0]
    mediabox = page.mediabox
    cropbox = page.cropbox
    bleedbox = getattr(page, "bleedbox", mediabox)
    trimbox = getattr(page, "trimbox", cropbox)

    # Ensure valid rectangles
    if not trimbox or trimbox.is_empty:
        trimbox = cropbox if cropbox and not cropbox.is_empty else mediabox
    if not bleedbox or bleedbox.is_empty:
        bleedbox = mediabox

    # Calculate bleed offsets (difference between TrimBox and BleedBox in mm)
    bleed_top_mm = max(0.0, pt_to_mm(trimbox.y0 - bleedbox.y0))
    bleed_bottom_mm = max(0.0, pt_to_mm(bleedbox.y1 - trimbox.y1))
    bleed_left_mm = max(0.0, pt_to_mm(trimbox.x0 - bleedbox.x0))
    bleed_right_mm = max(0.0, pt_to_mm(bleedbox.x1 - trimbox.x1))

    boxes_info = {
        "mediabox": {
            "pt": [mediabox.x0, mediabox.y0, mediabox.x1, mediabox.y1],
            "width_pt": mediabox.width,
            "height_pt": mediabox.height,
            "width_mm": pt_to_mm(mediabox.width),
            "height_mm": pt_to_mm(mediabox.height),
        },
        "bleedbox": {
            "pt": [bleedbox.x0, bleedbox.y0, bleedbox.x1, bleedbox.y1],
            "width_pt": bleedbox.width,
            "height_pt": bleedbox.height,
            "width_mm": pt_to_mm(bleedbox.width),
            "height_mm": pt_to_mm(bleedbox.height),
        },
        "trimbox": {
            "pt": [trimbox.x0, trimbox.y0, trimbox.x1, trimbox.y1],
            "width_pt": trimbox.width,
            "height_pt": trimbox.height,
            "width_mm": pt_to_mm(trimbox.width),
            "height_mm": pt_to_mm(trimbox.height),
        },
        "cropbox": {
            "pt": [cropbox.x0, cropbox.y0, cropbox.x1, cropbox.y1],
            "width_pt": cropbox.width,
            "height_pt": cropbox.height,
            "width_mm": pt_to_mm(cropbox.width),
            "height_mm": pt_to_mm(cropbox.height),
        },
        "bleed_offsets_mm": {
            "top": bleed_top_mm,
            "bottom": bleed_bottom_mm,
            "left": bleed_left_mm,
            "right": bleed_right_mm,
        },
        "is_landscape": trimbox.width > trimbox.height,
    }
    doc.close()
    return boxes_info


def designer_mm_to_pdf_rect(
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float,
    trimbox: pymupdf.Rect,
) -> pymupdf.Rect:
    """
    Transforms designer coordinates (measured in mm from Top-Left of TrimBox)
    into PyMuPDF page coordinate Rect.
    """
    x_pt = trimbox.x0 + mm_to_pt(x_mm)
    y_pt = trimbox.y0 + mm_to_pt(y_mm)
    w_pt = mm_to_pt(width_mm)
    h_pt = mm_to_pt(height_mm)
    return pymupdf.Rect(x_pt, y_pt, x_pt + w_pt, y_pt + h_pt)


def create_default_certificate_base(
    width_mm: float = 297.0,  # A4 Landscape
    height_mm: float = 210.0,
    bleed_mm: float = 3.0,
) -> pymupdf.Document:
    """
    Synthesizes an elegant, high-end base certificate PDF
    with Deep Navy & Sky Cyan border, gold inner frame, and TrimBox / BleedBox metadata.
    """
    doc = pymupdf.open()
    total_w_pt = mm_to_pt(width_mm + (bleed_mm * 2))
    total_h_pt = mm_to_pt(height_mm + (bleed_mm * 2))

    page = doc.new_page(width=total_w_pt, height=total_h_pt)

    # Set prepress boxes reliably
    bleed_pt = mm_to_pt(bleed_mm)
    page.set_bleedbox(page.rect)
    trimbox = pymupdf.Rect(
        bleed_pt,
        bleed_pt,
        max(bleed_pt, page.rect.width - bleed_pt),
        max(bleed_pt, page.rect.height - bleed_pt),
    )
    page.set_trimbox(trimbox)

    # Draw luxury background
    shape = page.new_shape()
    # Light cream background inside bleed
    shape.draw_rect(page.rect)
    shape.finish(color=None, fill=(0.99, 0.99, 0.98))

    # Outer Navy Border (3mm inside TrimBox)
    margin_pt = mm_to_pt(8.0)
    outer_frame = pymupdf.Rect(
        trimbox.x0 + margin_pt,
        trimbox.y0 + margin_pt,
        trimbox.x1 - margin_pt,
        trimbox.y1 - margin_pt,
    )
    shape.draw_rect(outer_frame)
    shape.finish(color=(0.0, 0.294, 0.529), width=2.5)  # #004B87

    # Inner Cyan/Gold Border
    inner_margin_pt = mm_to_pt(10.5)
    inner_frame = pymupdf.Rect(
        trimbox.x0 + inner_margin_pt,
        trimbox.y0 + inner_margin_pt,
        trimbox.x1 - inner_margin_pt,
        trimbox.y1 - inner_margin_pt,
    )
    shape.draw_rect(inner_frame)
    shape.finish(color=(0.286, 0.659, 0.871), width=1.0)  # #49A8DE

    # Signature baseline decorative rule
    sig_line_y = trimbox.y1 - mm_to_pt(35.0)
    sig_line_x0 = trimbox.x1 - mm_to_pt(90.0)
    sig_line_x1 = trimbox.x1 - mm_to_pt(25.0)
    shape.draw_line(
        pymupdf.Point(sig_line_x0, sig_line_y),
        pymupdf.Point(sig_line_x1, sig_line_y),
    )
    shape.finish(color=(0.7, 0.75, 0.8), width=1.0)

    shape.commit()
    return doc


def place_trainer_signature(
    page: pymupdf.Page,
    frame_rect: pymupdf.Rect,
    trainer: Dict[str, Any],
    baseline_offset_mm: float = 0.0,
    frame_scale_pct: float = 100.0,
) -> bool:
    """
    Places vector or raster signature inside frame_rect with BOTTOM-CENTER line anchoring.
    - If Vector PDF: embeds pure vector page via show_pdf_page()
    - If Raster PNG: inserts image via insert_image()
    Multiplies trainer base scale by signature frame's own scale.
    """
    sig_filename = trainer.get("signature_filename")
    if not sig_filename:
        return False

    sig_path = trainer_manager.get_signature_path(sig_filename)
    if not sig_path or not sig_path.exists():
        return False

    scale_pct = float(trainer.get("scale", 100.0))
    scale_factor = (scale_pct / 100.0) * (frame_scale_pct / 100.0)
    baseline_offset_pt = mm_to_pt(baseline_offset_mm)

    is_pdf = trainer.get("is_vector", False) or sig_path.suffix.lower() == ".pdf"

    if is_pdf:
        try:
            doc_sig = pymupdf.open(str(sig_path))
            sig_page = doc_sig[0]
            cropbox = sig_page.cropbox
            src_w = cropbox.width
            src_h = cropbox.height
            if src_w <= 0 or src_h <= 0:
                doc_sig.close()
                return False

            ar = src_w / src_h

            # Max fit within frame
            if frame_rect.width / frame_rect.height > ar:
                base_h = frame_rect.height
                base_w = frame_rect.height * ar
            else:
                base_w = frame_rect.width
                base_h = frame_rect.width / ar

            placed_w = base_w * scale_factor
            placed_h = base_h * scale_factor

            # Bottom-Center Anchor
            placed_x = frame_rect.x0 + (frame_rect.width - placed_w) / 2.0
            placed_y = (frame_rect.y1 - placed_h) + baseline_offset_pt
            placed_rect = pymupdf.Rect(
                placed_x, placed_y, placed_x + placed_w, placed_y + placed_h
            )

            page.show_pdf_page(
                placed_rect, doc_sig, 0, clip=cropbox, keep_proportion=True
            )
            doc_sig.close()
            return True
        except Exception as e:
            print(f"Error placing vector signature: {e}")
            return False
    else:
        # Raster PNG
        try:
            from PIL import Image

            with Image.open(sig_path) as im:
                src_w, src_h = im.size

            if src_w <= 0 or src_h <= 0:
                return False

            ar = src_w / src_h

            if frame_rect.width / frame_rect.height > ar:
                base_h = frame_rect.height
                base_w = frame_rect.height * ar
            else:
                base_w = frame_rect.width
                base_h = frame_rect.width / ar

            placed_w = base_w * scale_factor
            placed_h = base_h * scale_factor

            # Bottom-Center Anchor
            placed_x = frame_rect.x0 + (frame_rect.width - placed_w) / 2.0
            placed_y = (frame_rect.y1 - placed_h) + baseline_offset_pt
            placed_rect = pymupdf.Rect(
                placed_x, placed_y, placed_x + placed_w, placed_y + placed_h
            )

            page.insert_image(
                placed_rect, filename=str(sig_path), keep_proportion=True
            )
            return True
        except Exception as e:
            print(f"Error placing raster signature: {e}")
            return False


def build_certificate_pdf(
    template_config: Dict[str, Any],
    record_data: Dict[str, Any],
    show_trim_guide: bool = False,
) -> pymupdf.Document:
    """
    Renders certificate fields, BiDi shaped text, and vector/raster signatures
    onto base PDF strictly preserving MediaBox, BleedBox, and TrimBox.
    """
    base_pdf_path = template_config.get("base_pdf_path")
    doc = None
    if base_pdf_path and Path(base_pdf_path).exists():
        doc = pymupdf.open(str(base_pdf_path))
    else:
        base_pdf_filename = template_config.get("base_pdf_filename")
        if base_pdf_filename:
            from engine import template_manager
            found_base = template_manager.get_base_pdf_path(base_pdf_filename)
            if found_base and found_base.exists():
                doc = pymupdf.open(str(found_base))

    if doc is None:
        # Generate default luxury certificate base
        page_setup = template_config.get("page_setup", {})
        doc = create_default_certificate_base(
            width_mm=float(page_setup.get("width_mm", 297.0)),
            height_mm=float(page_setup.get("height_mm", 210.0)),
            bleed_mm=float(page_setup.get("bleed_mm", 3.0)),
        )

    page = doc[0]
    trimbox = getattr(page, "trimbox", page.rect)
    if not trimbox or trimbox.is_empty:
        trimbox = page.rect

    # 1. Render Dynamic Text Fields
    fields = template_config.get("fields", [])
    render_metrics = {
        "is_shrunk": False,
        "max_shrink_percent": 0.0,
        "is_overflow": False,
        "fields_metrics": [],
    }

    for field in fields:
        field_id = field.get("id")
        text_val = str(record_data.get(field_id, field.get("default_text", "")))
        if not text_val:
            continue

        x_mm = float(field.get("x_mm", 20.0))
        y_mm = float(field.get("y_mm", 20.0))
        w_mm = float(field.get("width_mm", 100.0))
        h_mm = float(field.get("height_mm", 20.0))
        frame_rect = designer_mm_to_pdf_rect(x_mm, y_mm, w_mm, h_mm, trimbox)

        # Dual Fonts: Arabic font vs Latin/English font
        is_ar = text_shaper.is_arabic_text(text_val)
        if is_ar:
            font_name_hint = field.get("font_family", "Cairo Regular")
        else:
            font_name_hint = field.get("english_font") or field.get("font_family", "Cairo Regular")

        font_file_path = font_manager.get_font_path(font_name_hint)
        if not font_file_path:
            # Fallback to first available font
            available = font_manager.list_fonts()
            if available:
                font_file_path = Path(available[0]["path"])
            else:
                font_file_path = font_manager.FONTS_DIR / "Cairo-Regular.ttf"

        target_size = float(field.get("font_size", 24.0))
        max_shrink = float(field.get("max_shrink_percent", 20.0))

        layout = text_shaper.calculate_text_layout(
            text=text_val,
            font_path=str(font_file_path),
            target_fontsize=target_size,
            frame_width_pt=frame_rect.width,
            max_shrink_percent=max_shrink,
        )

        # Track prepress shrink & overflow metrics
        applied_shrink = layout.get("applied_shrink_percent", 0.0)
        overflow_flag = layout.get("is_overflow", False)
        render_metrics["fields_metrics"].append({
            "id": field_id,
            "text": text_val,
            "applied_shrink_percent": applied_shrink,
            "is_overflow": overflow_flag
        })
        if applied_shrink > 0.0:
            render_metrics["is_shrunk"] = True
            if applied_shrink > render_metrics["max_shrink_percent"]:
                render_metrics["max_shrink_percent"] = applied_shrink
        if overflow_flag:
            render_metrics["is_overflow"] = True

        h_align = field.get("horizontal_align", "auto")
        v_align = field.get("vertical_align", "middle")
        baseline_offset_pt = mm_to_pt(float(field.get("baseline_offset_mm", 0.0)))

        origin = text_shaper.compute_baseline_origin(
            frame_rect=frame_rect,
            text_width_pt=layout["final_width_pt"],
            fontsize=layout["final_fontsize"],
            horizontal_align=h_align,
            vertical_align=v_align,
            baseline_offset_pt=baseline_offset_pt,
            is_arabic=layout["is_arabic"],
        )

        color_tuple = text_shaper.parse_color(field.get("color", "#004B87"))

        # Register font and insert shaped text
        font_token = f"F_{Path(font_file_path).stem.replace('-', '_')}"
        page.insert_font(fontname=font_token, fontfile=str(font_file_path))
        page.insert_text(
            origin,
            layout["shaped_text"],
            fontname=font_token,
            fontsize=layout["final_fontsize"],
            color=color_tuple,
        )

        # If trim guides requested, draw subtle bounding box
        if show_trim_guide:
            page.draw_rect(
                frame_rect,
                color=(0.286, 0.659, 0.871),  # Sky cyan
                width=0.75,
                dashes="[3 3] 0",
            )

    # 2. Render Trainer Signature Frame
    sig_frames = template_config.get("signature_frames", [])
    if not sig_frames and "signature_frame" in template_config:
        sig_frames = [template_config["signature_frame"]]

    for s_frame in sig_frames:
        x_mm = float(s_frame.get("x_mm", 200.0))
        y_mm = float(s_frame.get("y_mm", 145.0))
        w_mm = float(s_frame.get("width_mm", 65.0))
        h_mm = float(s_frame.get("height_mm", 30.0))
        frame_rect = designer_mm_to_pdf_rect(x_mm, y_mm, w_mm, h_mm, trimbox)

        trainer_id = record_data.get(
            "trainer_id", s_frame.get("trainer_id", "")
        )
        trainer = trainer_manager.get_trainer(trainer_id) if trainer_id else None

        if not trainer:
            # Fallback to first available trainer
            all_trainers = trainer_manager.list_trainers()
            if all_trainers:
                trainer = all_trainers[0]

        if trainer:
            b_off = float(s_frame.get("baseline_offset_mm", 0.0))
            f_scale = float(s_frame.get("scale", 100.0))
            place_trainer_signature(
                page, frame_rect, trainer, baseline_offset_mm=b_off, frame_scale_pct=f_scale
            )

        if show_trim_guide:
            page.draw_rect(
                frame_rect,
                color=(0.776, 0.365, 0.604),  # Orchid magenta
                width=0.75,
                dashes="[4 2] 0",
            )

    # 3. Draw Prepress Crop Marks / Guides if requested
    if show_trim_guide:
        # Draw TrimBox guide (Solid Navy)
        page.draw_rect(
            trimbox,
            color=(0.0, 0.294, 0.529),
            width=1.0,
            dashes="[6 3] 0",
        )
        bleedbox = getattr(page, "bleedbox", None)
        if bleedbox and not bleedbox.is_empty and bleedbox != trimbox:
            # Draw BleedBox guide (Red/Magenta dashed)
            page.draw_rect(
                bleedbox,
                color=(0.85, 0.2, 0.2),
                width=0.8,
                dashes="[4 4] 0",
            )

    doc._render_metrics = render_metrics
    return doc


def render_certificate_preview(
    template_config: Dict[str, Any],
    record_data: Dict[str, Any],
    show_trim_guide: bool = True,
    dpi: int = 150,
    return_metrics: bool = False,
) -> Union[bytes, Tuple[bytes, Dict[str, Any]]]:
    """
    Renders high-DPI raster preview (PNG) of certificate.
    Optionally returns (png_bytes, metrics).
    """
    doc = build_certificate_pdf(
        template_config, record_data, show_trim_guide=show_trim_guide
    )
    metrics = getattr(doc, "_render_metrics", {
        "is_shrunk": False,
        "max_shrink_percent": 0.0,
        "is_overflow": False,
        "fields_metrics": []
    })
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    png_bytes = pix.tobytes("png")
    doc.close()
    if return_metrics:
        return png_bytes, metrics
    return png_bytes


def generate_certificate_pdf(
    template_config: Dict[str, Any], record_data: Dict[str, Any]
) -> bytes:
    """
    Generates pure vector print-ready PDF output with exact Box metadata.
    """
    doc = build_certificate_pdf(
        template_config, record_data, show_trim_guide=False
    )
    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return pdf_bytes
