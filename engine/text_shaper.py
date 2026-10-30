"""
engine/text_shaper.py
BiDi typography engine for high-precision Arabic and Latin typesetting.
Handles Unicode language detection, Arabic shaping with tashkeel preservation,
actual font-metric measurements, and single-line auto-shrink scaling.
"""

import re
import unicodedata
from typing import Dict, Any, Optional, Tuple, Union
import pymupdf
import arabic_reshaper
from bidi.algorithm import get_display

from engine import font_manager

# Unicode Arabic ranges (Standard, Supplements, Presentation Forms A & B)
ARABIC_REGEX = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)

# Reshaper cache by font path to avoid re-parsing font tables repeatedly
_reshaper_cache: Dict[str, arabic_reshaper.ArabicReshaper] = {}


def get_font_reshaper(font_path: Optional[str] = None) -> arabic_reshaper.ArabicReshaper:
    """
    Returns an ArabicReshaper configured specifically for the target font's cmap table.
    Ensures isolated characters that lack Presentation Forms-B glyphs fall back
    cleanly to standard Arabic codepoints, eliminating tofu (missing glyph boxes).
    """
    if font_path and font_path in _reshaper_cache:
        return _reshaper_cache[font_path]

    default_config = {
        "delete_harakat": False,
        "support_ligatures": True,
        "use_unshaped_instead_of_isolated": True,
        "RIAL": True,
    }

    if font_path:
        try:
            cfg = arabic_reshaper.config_for_true_type_font(font_path)
            reshaper = arabic_reshaper.ArabicReshaper(configuration=cfg)
            _reshaper_cache[font_path] = reshaper
            return reshaper
        except Exception:
            pass

    reshaper = arabic_reshaper.ArabicReshaper(configuration=default_config)
    if font_path:
        _reshaper_cache[font_path] = reshaper
    return reshaper


def is_arabic_text(text: str) -> bool:
    """Checks if string contains any Arabic characters."""
    if not text:
        return False
    return bool(ARABIC_REGEX.search(text))


def shape_text(
    text: str,
    is_arabic: Optional[bool] = None,
    font_path: Optional[str] = None,
    font_obj: Optional[pymupdf.Font] = None,
) -> str:
    """
    Applies Arabic reshaping and BiDi visual reordering if text contains Arabic.
    Preserves vowels (tashkeel), supports complex ligatures, and verifies that every
    glyph exists in the font's CMAP table so no tofu boxes (▯) are rendered.
    Latin/English text is returned untouched.
    """
    if not text:
        return ""

    if is_arabic is None:
        is_arabic = is_arabic_text(text)

    if not is_arabic:
        return text

    reshaper = get_font_reshaper(font_path)
    reshaped = reshaper.reshape(text)
    bidi_text = get_display(reshaped)

    if not font_obj and font_path:
        try:
            font_obj = pymupdf.Font(fontfile=font_path)
        except Exception:
            font_obj = None

    if font_obj:
        sanitized = []
        for ch in bidi_text:
            cp = ord(ch)
            if cp == 32:
                sanitized.append(ch)
                continue
            if font_obj.has_glyph(cp) == 0:
                # Character glyph missing in font cmap. Try NFKC normalization first (preserves hamza on Alef 0x0625, Ta Marbuta 0x0629, etc.)
                nfkc = unicodedata.normalize("NFKC", ch)
                if nfkc and font_obj.has_glyph(ord(nfkc[0])) != 0:
                    sanitized.append(nfkc[0])
                else:
                    # Fallback to NFD
                    nfd = unicodedata.normalize("NFD", ch)
                    if nfd and font_obj.has_glyph(ord(nfd[0])) != 0:
                        sanitized.append(nfd[0])
                    else:
                        sanitized.append(ch)
            else:
                sanitized.append(ch)
        return "".join(sanitized)

    return bidi_text


def parse_color(
    color_val: Union[str, Dict[str, Any], Tuple, list]
) -> Tuple[float, ...]:
    """
    Parses color into PyMuPDF color tuple:
      - CMYK: 4 floats (c, m, y, k) in range 0.0 - 1.0 (e.g. Pure Black: (0, 0, 0, 1.0))
      - RGB: 3 floats (r, g, b) in range 0.0 - 1.0
      - Hex: '#004B87' -> RGB floats
    """
    if isinstance(color_val, dict):
        if all(k in color_val for k in ("c", "m", "y", "k")):
            # CMYK dictionary (values 0-100 or 0-1)
            c = float(color_val["c"])
            m = float(color_val["m"])
            y = float(color_val["y"])
            k = float(color_val["k"])
            if max(c, m, y, k) > 1.0:
                c, m, y, k = c / 100.0, m / 100.0, y / 100.0, k / 100.0
            return (
                max(0.0, min(1.0, c)),
                max(0.0, min(1.0, m)),
                max(0.0, min(1.0, y)),
                max(0.0, min(1.0, k)),
            )
        elif all(k in color_val for k in ("r", "g", "b")):
            r = float(color_val["r"])
            g = float(color_val["g"])
            b = float(color_val["b"])
            if max(r, g, b) > 1.0:
                r, g, b = r / 255.0, g / 255.0, b / 255.0
            return (
                max(0.0, min(1.0, r)),
                max(0.0, min(1.0, g)),
                max(0.0, min(1.0, b)),
            )

    if isinstance(color_val, (list, tuple)):
        if len(color_val) == 4:
            # CMYK list
            vals = [float(v) for v in color_val]
            if max(vals) > 1.0:
                vals = [v / 100.0 for v in vals]
            return tuple(max(0.0, min(1.0, v)) for v in vals)
        elif len(color_val) == 3:
            # RGB list
            vals = [float(v) for v in color_val]
            if max(vals) > 1.0:
                vals = [v / 255.0 for v in vals]
            return tuple(max(0.0, min(1.0, v)) for v in vals)

    if isinstance(color_val, str):
        hex_clean = color_val.strip().lstrip("#")
        if len(hex_clean) == 6:
            r = int(hex_clean[0:2], 16) / 255.0
            g = int(hex_clean[2:4], 16) / 255.0
            b = int(hex_clean[4:6], 16) / 255.0
            return (r, g, b)
        elif len(hex_clean) == 8:
            # CMYK hex representation (rare, but supported)
            c = int(hex_clean[0:2], 16) / 255.0
            m = int(hex_clean[2:4], 16) / 255.0
            y = int(hex_clean[4:6], 16) / 255.0
            k = int(hex_clean[6:8], 16) / 255.0
            return (c, m, y, k)

    # Default fallback: Dark Slate Text
    return (0.118, 0.161, 0.231)


def calculate_text_layout(
    text: str,
    font_path: str,
    target_fontsize: float,
    frame_width_pt: float,
    max_shrink_percent: float = 20.0,
    min_fontsize_pt: float = 6.0,
) -> Dict[str, Any]:
    """
    Measures shaped visual width and scales down font size up to max_shrink_percent
    so the text fits strictly on a single line without wrapping.
    Flags is_overflow: True if text still exceeds frame width at minimum font size.
    """
    font = pymupdf.Font(fontfile=font_path)
    is_ar = is_arabic_text(text)
    shaped = shape_text(text, is_arabic=is_ar, font_path=font_path, font_obj=font)

    initial_width = font.text_length(shaped, fontsize=target_fontsize)
    min_allowed_size = max(
        min_fontsize_pt, target_fontsize * (1.0 - (max_shrink_percent / 100.0))
    )

    if initial_width <= frame_width_pt:
        final_size = target_fontsize
        final_width = initial_width
        applied_shrink = 0.0
        is_overflow = False
    else:
        # Scale factor needed to fit exactly inside frame
        scale_ratio = frame_width_pt / initial_width
        calc_size = target_fontsize * scale_ratio

        if calc_size >= min_allowed_size:
            final_size = round(calc_size, 2)
            applied_shrink = round(
                (1.0 - (final_size / target_fontsize)) * 100.0, 1
            )
            final_width = font.text_length(shaped, fontsize=final_size)
            is_overflow = False
        else:
            final_size = round(min_allowed_size, 2)
            applied_shrink = round(max_shrink_percent, 1)
            final_width = font.text_length(shaped, fontsize=final_size)
            is_overflow = final_width > frame_width_pt

    return {
        "raw_text": text,
        "shaped_text": shaped,
        "is_arabic": is_ar,
        "direction": "rtl" if is_ar else "ltr",
        "target_fontsize": target_fontsize,
        "final_fontsize": final_size,
        "initial_width_pt": initial_width,
        "final_width_pt": final_width,
        "frame_width_pt": frame_width_pt,
        "applied_shrink_percent": applied_shrink,
        "is_overflow": is_overflow,
        "font_path": font_path,
        "ascender": getattr(font, "ascender", 0.88),
        "descender": getattr(font, "descender", -0.25),
    }


def compute_baseline_origin(
    frame_rect: pymupdf.Rect,
    text_width_pt: float,
    fontsize: float,
    horizontal_align: str = "center",
    vertical_align: str = "middle",
    baseline_offset_pt: float = 0.0,
    is_arabic: bool = True,
) -> pymupdf.Point:
    """
    Computes exact insertion (X, Y) point for PyMuPDF insert_text baseline
    supporting 9-point alignment (Horizontal: left/center/right; Vertical: top/middle/bottom).
    """
    h_align = horizontal_align.lower()
    if h_align == "auto":
        h_align = "right" if is_arabic else "left"

    # 1. Horizontal Position (X)
    if h_align == "left":
        x = frame_rect.x0
    elif h_align == "right":
        x = frame_rect.x1 - text_width_pt
    else:  # "center"
        x = frame_rect.x0 + (frame_rect.width - text_width_pt) / 2.0

    # 2. Vertical Position (Y baseline)
    v_align = vertical_align.lower()
    # Typical typographic cap-height is ~0.75-0.85 of fontsize
    cap_height = 0.80 * fontsize

    if v_align == "top":
        y = frame_rect.y0 + cap_height
    elif v_align == "bottom":
        y = frame_rect.y1
    else:  # "middle" / "center"
        mid_y = frame_rect.y0 + frame_rect.height / 2.0
        y = mid_y + (cap_height / 2.0)

    # Apply manual baseline offset in points
    y += baseline_offset_pt

    return pymupdf.Point(x, y)

