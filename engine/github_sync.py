"""
engine/github_sync.py
Automatic GitHub storage synchronization helper for Render free tier.
Persists templates_store/ and trainers_store/ across ephemeral container restarts.

Features:
- Thread-safe background commits (create/update/delete) via GitHub REST API.
- Instant UI responsiveness (all network sync runs in daemon threads).
- SHA1 hash comparison matching git blob format to avoid redundant commits.
- Automatic pull/sync on server startup to restore state from GitHub repo.
- Zero extra dependencies (uses Python standard library urllib + json + base64).
- Safe graceful fallback when GITHUB_TOKEN or GITHUB_REPO are not configured.
"""

import base64
import hashlib
import json
import logging
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("certflow.github_sync")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
ALLOWED_SYNC_DIRS = ("templates_store", "trainers_store")
_sync_lock = threading.Lock()


def get_token() -> str:
    """Retrieves GitHub Personal Access Token or fine-grained token from environment."""
    return os.environ.get("GITHUB_TOKEN", "").strip()


def get_repo() -> str:
    """
    Retrieves and normalizes repository name in 'owner/repo' format.
    Handles 'owner/repo', 'owner/repo.git', or full 'https://github.com/owner/repo.git' formats.
    """
    repo = os.environ.get("GITHUB_REPO", "").strip()
    if repo.endswith(".git"):
        repo = repo[:-4]
    if "github.com/" in repo:
        repo = repo.split("github.com/")[-1]
    return repo.strip("/")


def get_branch() -> str:
    """Retrieves target git branch from environment, default to 'main'."""
    return os.environ.get("GITHUB_BRANCH", "").strip() or "main"


def is_configured() -> bool:
    """Returns True if both GITHUB_TOKEN and GITHUB_REPO are provided."""
    token = get_token()
    repo = get_repo()
    return bool(token and repo and "/" in repo)


def get_repo_rel_path(file_path: Path | str) -> Optional[str]:
    """
    Normalizes a file path to a forward-slash relative path within BASE_DIR.
    Ensures path is within ALLOWED_SYNC_DIRS and ignores temporary/preview files.
    """
    try:
        p = Path(file_path)
        if p.is_absolute():
            rel = p.resolve().relative_to(BASE_DIR.resolve()).as_posix()
        else:
            # If relative, resolve relative to BASE_DIR if it doesn't already start with an allowed dir
            as_posix = p.as_posix().lstrip("./")
            if any(as_posix == d or as_posix.startswith(f"{d}/") for d in ALLOWED_SYNC_DIRS):
                rel = as_posix
            else:
                rel = (BASE_DIR / p).resolve().relative_to(BASE_DIR.resolve()).as_posix()

        # Clean relative prefix
        rel = rel.lstrip("./")

        # Check allowed directory
        if not any(rel == d or rel.startswith(f"{d}/") for d in ALLOWED_SYNC_DIRS):
            logger.debug(f"[GitHub Sync] Path '{rel}' outside allowed sync dirs; skipped.")
            return None

        # Skip temporary, preview-only, and OS metadata files
        filename = Path(rel).name
        if filename.startswith(".") or filename.startswith("preview_temp") or filename.endswith(".tmp"):
            logger.debug(f"[GitHub Sync] Path '{rel}' is temporary or metadata; skipped.")
            return None

        return rel
    except Exception as e:
        logger.debug(f"[GitHub Sync] Invalid path {file_path}: {e}")
        return None


def _make_headers(token: str, accept: str = "application/vnd.github+json") -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "CertFlow-Studio-Sync",
    }


def calc_git_blob_sha(content_bytes: bytes) -> str:
    """Calculates the standard Git blob SHA1 for the given file content."""
    prefix = f"blob {len(content_bytes)}\0".encode("ascii")
    return hashlib.sha1(prefix + content_bytes).hexdigest()


def get_remote_file_sha(rel_path: str) -> Optional[str]:
    """
    Queries GitHub REST API to get the current blob SHA of a file on the target branch.
    Returns None if file does not exist (404) or on error.
    """
    if not is_configured():
        return None
    token = get_token()
    repo = get_repo()
    branch = get_branch()
    encoded_path = urllib.parse.quote(rel_path, safe="/")
    url = f"https://api.github.com/repos/{repo}/contents/{encoded_path}?ref={urllib.parse.quote(branch)}"
    req = urllib.request.Request(url, headers=_make_headers(token), method="GET")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict):
                return data.get("sha")
            return None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        logger.warning(f"[GitHub Sync] Failed to get SHA for {rel_path}: HTTP {e.code}")
        return None
    except Exception as e:
        logger.warning(f"[GitHub Sync] Network error fetching SHA for {rel_path}: {e}")
        return None


def sync_file_push(file_path: Path | str, commit_message: Optional[str] = None) -> bool:
    """
    Synchronously commits and pushes a single file to GitHub via PUT /contents/{path}.
    Skips push if local file is already identical to remote git blob.
    Retries once on 409 Conflict.
    """
    if not is_configured():
        return False

    rel_path = get_repo_rel_path(file_path)
    if not rel_path:
        return False

    abs_path = BASE_DIR / rel_path
    if not abs_path.is_file():
        logger.warning(f"[GitHub Sync] Cannot push {rel_path}: file does not exist locally.")
        return False

    try:
        content_bytes = abs_path.read_bytes()
    except Exception as e:
        logger.error(f"[GitHub Sync] Could not read local file {rel_path}: {e}")
        return False

    local_sha = calc_git_blob_sha(content_bytes)
    b64_content = base64.b64encode(content_bytes).decode("ascii")

    token = get_token()
    repo = get_repo()
    branch = get_branch()
    encoded_path = urllib.parse.quote(rel_path, safe="/")
    url = f"https://api.github.com/repos/{repo}/contents/{encoded_path}"

    with _sync_lock:
        remote_sha = get_remote_file_sha(rel_path)
        if remote_sha == local_sha:
            logger.info(f"[GitHub Sync] {rel_path} already matches remote ({local_sha[:7]}), skipping push.")
            return True

        msg = commit_message or f"Auto-sync: {'update' if remote_sha else 'add'} {rel_path}"
        payload: Dict[str, Any] = {
            "message": msg,
            "content": b64_content,
            "branch": branch,
        }
        if remote_sha:
            payload["sha"] = remote_sha

        # Try PUT, retry once if conflict (409)
        for attempt in range(2):
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers=_make_headers(token),
                method="PUT",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    if resp.status in (200, 201):
                        logger.info(f"[GitHub Sync] Pushed {rel_path} ({msg}) [HTTP {resp.status}]")
                        return True
            except urllib.error.HTTPError as e:
                err_text = ""
                try:
                    err_text = e.read().decode("utf-8")
                except Exception:
                    pass
                if e.code == 409 and attempt == 0:
                    logger.warning(f"[GitHub Sync] 409 Conflict pushing {rel_path}, refreshing SHA and retrying...")
                    new_sha = get_remote_file_sha(rel_path)
                    if new_sha:
                        payload["sha"] = new_sha
                        continue
                logger.error(f"[GitHub Sync] Failed to push {rel_path}: HTTP {e.code} - {err_text}")
                return False
            except Exception as e:
                logger.error(f"[GitHub Sync] Network error pushing {rel_path}: {e}")
                return False

    return False


def sync_file_delete(file_path: Path | str, commit_message: Optional[str] = None) -> bool:
    """
    Synchronously deletes a file from the GitHub repository via DELETE /contents/{path}.
    If the file does not exist on GitHub, returns True immediately.
    """
    if not is_configured():
        return False

    rel_path = get_repo_rel_path(file_path)
    if not rel_path:
        return False

    token = get_token()
    repo = get_repo()
    branch = get_branch()
    encoded_path = urllib.parse.quote(rel_path, safe="/")
    url = f"https://api.github.com/repos/{repo}/contents/{encoded_path}"

    with _sync_lock:
        remote_sha = get_remote_file_sha(rel_path)
        if not remote_sha:
            logger.info(f"[GitHub Sync] {rel_path} does not exist on GitHub; nothing to delete.")
            return True

        msg = commit_message or f"Auto-sync: delete {rel_path}"
        payload = {
            "message": msg,
            "sha": remote_sha,
            "branch": branch,
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers=_make_headers(token),
            method="DELETE",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status in (200, 204):
                    logger.info(f"[GitHub Sync] Deleted {rel_path} from GitHub ({msg})")
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return True
            err_text = ""
            try:
                err_text = e.read().decode("utf-8")
            except Exception:
                pass
            logger.error(f"[GitHub Sync] Failed to delete {rel_path}: HTTP {e.code} - {err_text}")
            return False
        except Exception as e:
            logger.error(f"[GitHub Sync] Network error deleting {rel_path}: {e}")
            return False

    return False


def push_file_async(file_path: Path | str, commit_message: Optional[str] = None) -> Optional[threading.Thread]:
    """
    Commits and pushes file change to GitHub in a background daemon thread.
    UI requests remain instant and non-blocking.
    """
    if not is_configured():
        return None

    t = threading.Thread(
        target=sync_file_push,
        args=(file_path, commit_message),
        daemon=True,
        name=f"gh-sync-push-{Path(file_path).name}",
    )
    t.start()
    return t


def delete_file_async(file_path: Path | str, commit_message: Optional[str] = None) -> Optional[threading.Thread]:
    """
    Deletes file from GitHub in a background daemon thread.
    UI requests remain instant and non-blocking.
    """
    if not is_configured():
        return None

    t = threading.Thread(
        target=sync_file_delete,
        args=(file_path, commit_message),
        daemon=True,
        name=f"gh-sync-del-{Path(file_path).name}",
    )
    t.start()
    return t


def _download_raw_file(rel_path: str) -> Optional[bytes]:
    """Downloads raw file content from GitHub repository contents API."""
    token = get_token()
    repo = get_repo()
    branch = get_branch()
    encoded_path = urllib.parse.quote(rel_path, safe="/")
    url = f"https://api.github.com/repos/{repo}/contents/{encoded_path}?ref={urllib.parse.quote(branch)}"
    req = urllib.request.Request(
        url,
        headers=_make_headers(token, accept="application/vnd.github.raw"),
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.read()
    except Exception as e:
        logger.error(f"[GitHub Sync] Failed to download {rel_path}: {e}")
        return None


def _sync_pull_directory(dir_path: str, stats: Dict[str, Any]) -> None:
    """Recursively queries GitHub directory contents and downloads new or changed files."""
    token = get_token()
    repo = get_repo()
    branch = get_branch()
    encoded_dir = urllib.parse.quote(dir_path, safe="/")
    url = f"https://api.github.com/repos/{repo}/contents/{encoded_dir}?ref={urllib.parse.quote(branch)}"
    req = urllib.request.Request(url, headers=_make_headers(token), method="GET")

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            items = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.info(f"[GitHub Sync] Remote directory '{dir_path}' does not exist on GitHub, skipping.")
            return
        logger.error(f"[GitHub Sync] Failed to list remote '{dir_path}': HTTP {e.code}")
        return
    except Exception as e:
        logger.error(f"[GitHub Sync] Error listing '{dir_path}': {e}")
        return

    if not isinstance(items, list):
        return

    for item in items:
        item_path = item.get("path")
        item_type = item.get("type")
        item_name = item.get("name", "")

        # Skip ignored and temporary files
        if item_name.startswith(".") or item_name.startswith("preview_temp") or item_name.endswith(".tmp"):
            continue

        if item_type == "dir":
            _sync_pull_directory(item_path, stats)
        elif item_type == "file":
            local_path = BASE_DIR / item_path
            remote_sha = item.get("sha")

            # Check if local file is already identical
            if local_path.is_file():
                try:
                    local_bytes = local_path.read_bytes()
                    local_sha = calc_git_blob_sha(local_bytes)
                    if local_sha == remote_sha:
                        stats["skipped"].append(item_path)
                        continue
                except Exception:
                    pass

            # Download missing or updated file
            data = _download_raw_file(item_path)
            if data is not None:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(data)
                stats["pulled"].append(item_path)
                logger.info(f"[GitHub Sync] Synced file from GitHub: {item_path} ({len(data)} bytes)")
            else:
                stats["failed"].append(item_path)


def sync_pull_on_startup() -> Dict[str, Any]:
    """
    Pulls and restores latest templates and trainer files from the GitHub repository.
    Called on server startup so Render container restarts never lose user data.
    """
    stats: Dict[str, Any] = {
        "status": "skipped",
        "configured": is_configured(),
        "pulled": [],
        "skipped": [],
        "failed": [],
    }

    if not is_configured():
        logger.info("[GitHub Sync] GITHUB_TOKEN or GITHUB_REPO not configured. Storage sync is inactive (local mode).")
        return stats

    logger.info(f"[GitHub Sync] Starting initial pull from https://github.com/{get_repo()} (branch: {get_branch()})...")

    with _sync_lock:
        for store_dir in ALLOWED_SYNC_DIRS:
            _sync_pull_directory(store_dir, stats)

    stats["status"] = "ok" if not stats["failed"] else "partial"
    logger.info(
        f"[GitHub Sync] Startup pull completed: {len(stats['pulled'])} downloaded, "
        f"{len(stats['skipped'])} already up-to-date, {len(stats['failed'])} failed."
    )
    return stats

