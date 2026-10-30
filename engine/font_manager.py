import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Any
import pymupdf
from engine import github_sync

BASE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = BASE_DIR / "fonts"
ALLOWED_EXTENSIONS = {".ttf", ".otf"}


def ensure_fonts_dir() -> Path:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    return FONTS_DIR


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def get_font_metadata(font_path: Path) -> Dict[str, Any]:
    stat = font_path.stat()
    display_name = font_path.stem
    format_type = font_path.suffix.lower().replace(".", "").upper()

    try:
        font_obj = pymupdf.Font(fontfile=str(font_path))
        if font_obj.name:
            display_name = font_obj.name.strip()
    except Exception:
        # Fallback to sanitized filename
        display_name = font_path.stem.replace("-", " ").replace("_", " ")

    return {
        "filename": font_path.name,
        "name": display_name,
        "format": format_type,
        "size_bytes": stat.st_size,
        "size_formatted": format_file_size(stat.st_size),
        "path": str(font_path.resolve()),
        "modified_at": stat.st_mtime,
    }


def list_fonts() -> List[Dict[str, Any]]:
    ensure_fonts_dir()
    fonts = []
    for item in sorted(FONTS_DIR.iterdir()):
        if item.is_file() and item.suffix.lower() in ALLOWED_EXTENSIONS:
            try:
                meta = get_font_metadata(item)
                fonts.append(meta)
            except Exception as e:
                # Still include with basic info if pymupdf metadata fails
                fonts.append({
                    "filename": item.name,
                    "name": item.stem,
                    "format": item.suffix.lower().replace(".", "").upper(),
                    "size_bytes": item.stat().st_size,
                    "size_formatted": format_file_size(item.stat().st_size),
                    "path": str(item.resolve()),
                    "modified_at": item.stat().st_mtime,
                    "error": str(e)
                })
    return fonts


def save_font(filename: str, content: bytes, sync: bool = True) -> Dict[str, Any]:
    # FIX 1: Emergency read-only check
    if github_sync.is_configured() and not github_sync.is_hydration_healthy():
        raise RuntimeError(
            "Storage is in read-only emergency mode: remote fonts could not be verified on startup. "
            "Font uploads are blocked to prevent data loss. Please trigger a manual sync pull via /api/sync/pull."
        )

    ensure_fonts_dir()
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Invalid font format '{ext}'. Only .ttf and .otf files are allowed.")

    # Sanitize filename
    safe_name = Path(filename).name.replace(" ", "_")
    target_path = FONTS_DIR / safe_name

    with open(target_path, "wb") as f:
        f.write(content)

    if sync:
        github_sync.sync_file_push(
            target_path,
            commit_message=f"Auto-sync: add font {safe_name}",
            raise_on_error=True,
        )

    return get_font_metadata(target_path)


def delete_font(filename: str, sync: bool = True) -> bool:
    # FIX 1: Emergency read-only check
    if github_sync.is_configured() and not github_sync.is_hydration_healthy():
        raise RuntimeError(
            "Storage is in read-only emergency mode: remote fonts could not be verified on startup. "
            "Font deletions are blocked to prevent data loss. Please trigger a manual sync pull via /api/sync/pull."
        )

    safe_name = Path(filename).name
    target_path = FONTS_DIR / safe_name
    if sync:
        github_sync.sync_file_delete(
            target_path,
            commit_message=f"Auto-sync: delete font {safe_name}",
            raise_on_error=False,
        )
    if target_path.exists() and target_path.is_file():
        target_path.unlink()
        return True
    return False


def get_font_path(font_name_or_file: str) -> Optional[Path]:
    """
    Safely finds font file inside FONTS_DIR.
    Rejects path traversal (..), absolute paths, and symlink escapes outside FONTS_DIR.
    """
    ensure_fonts_dir()
    if not font_name_or_file or "\0" in font_name_or_file:
        return None

    # 1. Direct filename match with strict traversal validation (FIX 3)
    p = Path(font_name_or_file)
    if not p.is_absolute() and ".." not in p.parts:
        try:
            fonts_resolved = FONTS_DIR.resolve()
            candidate = (FONTS_DIR / p).resolve()
            if candidate.is_relative_to(fonts_resolved) and candidate.is_file() and candidate.suffix.lower() in ALLOWED_EXTENSIONS:
                return candidate
        except Exception:
            pass

    # 2. Check stem or display name safely within FONTS_DIR
    clean_target = Path(font_name_or_file).name.lower()
    for item in FONTS_DIR.iterdir():
        if item.is_file() and item.suffix.lower() in ALLOWED_EXTENSIONS:
            if item.stem.lower() == clean_target or item.name.lower() == clean_target:
                return item
            try:
                meta = get_font_metadata(item)
                if meta["name"].lower() == clean_target:
                    return item
            except Exception:
                continue

    return None

