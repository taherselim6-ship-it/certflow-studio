"""
engine/github_sync.py
Automatic GitHub storage synchronization helper for Render free tier.
Persists templates_store/, trainers_store/, and fonts/ across ephemeral container restarts
into a dedicated private data repository (certflow-data).

Features:
- Thread-safe verified commits (create/update/delete) via GitHub REST API.
- Synchronous verified push/delete on critical user actions to eliminate data loss.
- Appends '[skip render] [skip ci]' to all commit messages to prevent Render redeploy loops.
- Targets dedicated private data repo (GITHUB_DATA_REPO) with fallback to GITHUB_REPO.
- SHA1 hash comparison matching git blob format to avoid redundant commits.
- Automatic retry on 409 Conflict with exponential backoff and SHA refresh.
- Automatic pull/sync on server startup to restore state from GitHub repo into container.
- Zero extra dependencies (uses Python standard library urllib + json + base64).
- Safe graceful fallback when GITHUB_TOKEN is not configured (offline local development).
"""

import base64
import contextlib
import hashlib
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

logger = logging.getLogger("certflow.github_sync")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
ALLOWED_SYNC_DIRS = ("templates_store", "trainers_store", "fonts")
DEFAULT_DATA_REPO = "taherselim6-ship-it/certflow-data"
_sync_lock = threading.Lock()

# Hydration verification state
_hydration_status: str = "unconfigured"  # "unconfigured", "healthy", "degraded"
_hydration_error: Optional[str] = None
_hydration_lock = threading.Lock()

# Domain level locks (cross-thread and cross-process)
_domain_mem_locks: Dict[str, threading.RLock] = {}
_domain_mem_locks_mutex = threading.Lock()


def is_hydration_healthy() -> bool:
    """Returns True if local storage is verified in sync with GitHub, or local mode."""
    if not is_configured():
        return True
    with _hydration_lock:
        return _hydration_status == "healthy"


def get_hydration_status() -> Dict[str, Any]:
    """Returns detailed hydration status dictionary."""
    with _hydration_lock:
        return {
            "status": _hydration_status,
            "healthy": is_hydration_healthy(),
            "error": _hydration_error,
        }


def set_hydration_status(status_val: str, error_val: Optional[str] = None) -> None:
    """Sets current hydration status ('unconfigured', 'healthy', 'degraded')."""
    global _hydration_status, _hydration_error
    with _hydration_lock:
        _hydration_status = status_val
        _hydration_error = error_val


def get_domain_lock(name: str) -> threading.RLock:
    """Returns or creates a named re-entrant in-memory lock."""
    with _domain_mem_locks_mutex:
        if name not in _domain_mem_locks:
            _domain_mem_locks[name] = threading.RLock()
        return _domain_mem_locks[name]


@contextlib.contextmanager
def store_lock(domain_name: str, lock_file: Optional[Path] = None):
    """
    Acquires both an in-memory RLock and an OS file lock (fcntl.flock)
    to protect the entire read-modify-write-push lifecycle across threads and processes.
    """
    mem_lock = get_domain_lock(domain_name)
    with mem_lock:
        if HAS_FCNTL and lock_file is not None:
            lock_file.parent.mkdir(parents=True, exist_ok=True)
            with open(lock_file, "a") as f:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    yield
                finally:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass
        else:
            yield


def merge_json_manifest_records(remote_bytes: bytes, local_bytes: bytes) -> bytes:
    """
    Merges two JSON manifest lists of records (templates or trainers) by unique 'id'.
    Preserves all records from both sides. When the same record exists in both,
    the record with the newer 'updated_at' timestamp is kept.
    """
    try:
        remote_list = json.loads(remote_bytes.decode("utf-8"))
        local_list = json.loads(local_bytes.decode("utf-8"))
        if not isinstance(remote_list, list) or not isinstance(local_list, list):
            return local_bytes

        merged_by_id: Dict[str, Dict[str, Any]] = {}
        for item in remote_list:
            if isinstance(item, dict) and item.get("id"):
                merged_by_id[item["id"]] = item

        for item in local_list:
            if isinstance(item, dict) and item.get("id"):
                item_id = item["id"]
                if item_id not in merged_by_id:
                    merged_by_id[item_id] = item
                else:
                    rem_item = merged_by_id[item_id]
                    loc_time = item.get("updated_at", "")
                    rem_time = rem_item.get("updated_at", "")
                    if loc_time >= rem_time:
                        merged_by_id[item_id] = item
                    else:
                        merged_by_id[item_id] = rem_item

        merged_records = list(merged_by_id.values())
        return json.dumps(merged_records, ensure_ascii=False, indent=2).encode("utf-8")
    except Exception as e:
        logger.warning(f"[GitHub Sync] Failed to merge JSON manifest: {e}")
        return local_bytes


def get_token() -> str:
    """Retrieves GitHub Personal Access Token or fine-grained token from environment."""
    return os.environ.get("GITHUB_TOKEN", "").strip()


def normalize_repo_name(repo: str) -> str:
    """Normalizes a GitHub repo string to 'owner/repo' format."""
    r = repo.strip()
    if r.endswith(".git"):
        r = r[:-4]
    if "github.com/" in r:
        r = r.split("github.com/")[-1]
    return r.strip("/")


def get_data_repo() -> str:
    """
    Retrieves and normalizes target persistent data repository in 'owner/repo' format.
    Priority:
    1. GITHUB_DATA_REPO (e.g. taherselim6-ship-it/certflow-data)
    2. GITHUB_REPO (fallback if user configured GITHUB_REPO)
    3. DEFAULT_DATA_REPO ('taherselim6-ship-it/certflow-data')
    """
    raw = (
        os.environ.get("GITHUB_DATA_REPO", "").strip()
        or os.environ.get("GITHUB_REPO", "").strip()
        or DEFAULT_DATA_REPO
    )
    return normalize_repo_name(raw)


def get_repo() -> str:
    """Alias for get_data_repo() for backward compatibility."""
    return get_data_repo()


def get_branch() -> str:
    """Retrieves target git branch from environment, default to 'main'."""
    return os.environ.get("GITHUB_BRANCH", "").strip() or "main"


def is_configured() -> bool:
    """
    Returns True if GITHUB_TOKEN is provided and a valid repository is resolved.
    If GITHUB_TOKEN is empty, returns False (local offline development mode).
    """
    token = get_token()
    repo = get_data_repo()
    return bool(token and repo and "/" in repo)


def format_commit_message(msg: str) -> str:
    """
    Appends '[skip render] [skip ci]' to commit messages to ensure automated
    commits never trigger Render build/redeploy loops or CI workflows.
    """
    clean_msg = msg.strip()
    tags = "[skip render] [skip ci]"
    if tags not in clean_msg:
        return f"{clean_msg} {tags}"
    return clean_msg


def get_repo_rel_path(file_path: Path | str) -> Optional[str]:
    """
    Normalizes a file path to a forward-slash relative path within BASE_DIR.
    Ensures path is within ALLOWED_SYNC_DIRS and ignores temporary/preview files.
    Works reliably even if the file was already deleted locally.
    """
    try:
        p = Path(file_path)
        if p.is_absolute():
            try:
                rel = p.resolve().relative_to(BASE_DIR.resolve()).as_posix()
            except ValueError:
                try:
                    rel = p.relative_to(BASE_DIR).as_posix()
                except ValueError:
                    return None
        else:
            as_posix = p.as_posix().lstrip("./")
            if any(as_posix == d or as_posix.startswith(f"{d}/") for d in ALLOWED_SYNC_DIRS):
                rel = as_posix
            else:
                try:
                    rel = (BASE_DIR / p).resolve().relative_to(BASE_DIR.resolve()).as_posix()
                except ValueError:
                    rel = (BASE_DIR / p).relative_to(BASE_DIR).as_posix()

        # Clean relative prefix
        rel = rel.lstrip("./")

        # Check allowed directory
        if not any(rel == d or rel.startswith(f"{d}/") for d in ALLOWED_SYNC_DIRS):
            logger.debug(f"[GitHub Sync] Path '{rel}' outside allowed sync dirs; skipped.")
            return None

        # Skip temporary, preview-only, and OS metadata files
        filename = Path(rel).name
        if (
            filename.startswith(".")
            or filename.startswith("preview_temp")
            or filename.endswith(".tmp")
            or filename.endswith("~")
        ):
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
    repo = get_data_repo()
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


def sync_file_push(
    file_path: Path | str,
    commit_message: Optional[str] = None,
    raise_on_error: bool = False,
) -> bool:
    """
    Synchronously commits and pushes a single file to GitHub via PUT /contents/{path}.
    - Thread-safe via _sync_lock.
    - Compares local Git blob SHA with remote SHA to avoid redundant commits.
    - Appends '[skip render] [skip ci]' to all commit messages.
    - Automatically retries up to 3 times with exponential backoff on 409 Conflict.
    - When raise_on_error=True, raises RuntimeError on unrecoverable failures.
    - In local mode (unconfigured GITHUB_TOKEN), returns True without error.
    """
    if not is_configured():
        logger.debug(f"[GitHub Sync] Storage sync inactive; skipping push for {file_path}")
        return True

    # FIX 1: Prevent persistent writes if startup hydration is in a failed or degraded state
    if not is_hydration_healthy():
        err_msg = (
            f"[GitHub Sync] Storage write operations are locked: remote data could not be verified on startup "
            f"({get_hydration_status().get('error')}). Please re-verify via /api/sync/pull before writing."
        )
        logger.error(err_msg)
        if raise_on_error:
            raise RuntimeError(err_msg)
        return False

    rel_path = get_repo_rel_path(file_path)
    if not rel_path:
        return True

    abs_path = BASE_DIR / rel_path
    if not abs_path.is_file():
        err_msg = f"Cannot push {rel_path}: file does not exist locally."
        logger.warning(f"[GitHub Sync] {err_msg}")
        if raise_on_error:
            raise FileNotFoundError(err_msg)
        return False

    try:
        content_bytes = abs_path.read_bytes()
    except Exception as e:
        err_msg = f"Could not read local file {rel_path}: {e}"
        logger.error(f"[GitHub Sync] {err_msg}")
        if raise_on_error:
            raise RuntimeError(err_msg) from e
        return False

    local_sha = calc_git_blob_sha(content_bytes)
    b64_content = base64.b64encode(content_bytes).decode("ascii")

    token = get_token()
    repo = get_data_repo()
    branch = get_branch()
    encoded_path = urllib.parse.quote(rel_path, safe="/")
    url = f"https://api.github.com/repos/{repo}/contents/{encoded_path}"

    with _sync_lock:
        remote_sha = get_remote_file_sha(rel_path)
        if remote_sha == local_sha:
            logger.info(f"[GitHub Sync] {rel_path} already matches remote ({local_sha[:7]}), skipping push.")
            return True

        raw_msg = commit_message or f"Auto-sync: {'update' if remote_sha else 'add'} {rel_path}"
        msg = format_commit_message(raw_msg)
        payload: Dict[str, Any] = {
            "message": msg,
            "content": b64_content,
            "branch": branch,
        }
        if remote_sha:
            payload["sha"] = remote_sha

        # Retry loop up to 3 attempts with exponential backoff (0.5s, 1.0s, 2.0s)
        max_attempts = 3
        last_error = ""

        for attempt in range(max_attempts):
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
                last_error = f"HTTP {e.code}: {err_text}"

                if e.code == 409 and attempt < max_attempts - 1:
                    backoff = 0.5 * (2 ** attempt)
                    logger.warning(
                        f"[GitHub Sync] 409 Conflict pushing {rel_path} (attempt {attempt + 1}/{max_attempts}). "
                        f"Backing off {backoff:.1f}s, refreshing SHA and retrying..."
                    )
                    time.sleep(backoff)
                    new_sha = get_remote_file_sha(rel_path)
                    if new_sha == local_sha:
                        logger.info(f"[GitHub Sync] Remote already has our content for {rel_path}.")
                        return True

                    # FIX 2: If file is a JSON manifest, download remote version and merge records by ID
                    if rel_path in ("templates_store/templates.json", "trainers_store/trainers.json"):
                        try:
                            logger.info(f"[GitHub Sync] Merging conflicting manifest records for {rel_path}...")
                            remote_raw = _download_raw_file(rel_path)
                            if remote_raw:
                                merged_bytes = merge_json_manifest_records(remote_raw, content_bytes)
                                abs_path.write_bytes(merged_bytes)
                                content_bytes = merged_bytes
                                local_sha = calc_git_blob_sha(content_bytes)
                                b64_content = base64.b64encode(content_bytes).decode("ascii")
                                payload["content"] = b64_content
                        except Exception as merge_err:
                            logger.warning(f"[GitHub Sync] Conflict merge error: {merge_err}")

                    if new_sha:
                        payload["sha"] = new_sha
                    else:
                        payload.pop("sha", None)
                    continue

                logger.error(f"[GitHub Sync] Failed to push {rel_path}: {last_error}")
                if raise_on_error:
                    raise RuntimeError(f"GitHub push failed for {rel_path}: {last_error}")
                return False
            except Exception as e:
                last_error = str(e)
                logger.error(f"[GitHub Sync] Network error pushing {rel_path}: {last_error}")
                if raise_on_error:
                    raise RuntimeError(f"GitHub network error pushing {rel_path}: {last_error}") from e
                return False

    return False


def sync_file_delete(
    file_path: Path | str,
    commit_message: Optional[str] = None,
    raise_on_error: bool = False,
) -> bool:
    """
    Synchronously deletes a file from the GitHub repository via DELETE /contents/{path}.
    - Thread-safe via _sync_lock.
    - If file does not exist on GitHub, returns True immediately.
    - Appends '[skip render] [skip ci]' to all commit messages.
    - Retries up to 3 times on 409 Conflict with exponential backoff.
    - When raise_on_error=True, raises RuntimeError on unrecoverable failures.
    - In local mode (unconfigured GITHUB_TOKEN), returns True without error.
    """
    if not is_configured():
        return True

    # FIX 1: Prevent deletions if startup hydration is in a failed or degraded state
    if not is_hydration_healthy():
        err_msg = (
            f"[GitHub Sync] Storage delete operations are locked: remote data could not be verified on startup "
            f"({get_hydration_status().get('error')}). Please re-verify via /api/sync/pull before deleting."
        )
        logger.error(err_msg)
        if raise_on_error:
            raise RuntimeError(err_msg)
        return False

    rel_path = get_repo_rel_path(file_path)
    if not rel_path:
        return True

    token = get_token()
    repo = get_data_repo()
    branch = get_branch()
    encoded_path = urllib.parse.quote(rel_path, safe="/")
    url = f"https://api.github.com/repos/{repo}/contents/{encoded_path}"

    with _sync_lock:
        max_attempts = 3
        last_error = ""

        for attempt in range(max_attempts):
            remote_sha = get_remote_file_sha(rel_path)
            if not remote_sha:
                logger.info(f"[GitHub Sync] {rel_path} does not exist on GitHub; nothing to delete.")
                return True

            raw_msg = commit_message or f"Auto-sync: delete {rel_path}"
            msg = format_commit_message(raw_msg)
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
                last_error = f"HTTP {e.code}: {err_text}"

                if e.code == 409 and attempt < max_attempts - 1:
                    backoff = 0.5 * (2 ** attempt)
                    logger.warning(
                        f"[GitHub Sync] 409 Conflict deleting {rel_path} (attempt {attempt + 1}/{max_attempts}). "
                        f"Backing off {backoff:.1f}s and retrying..."
                    )
                    time.sleep(backoff)
                    continue

                logger.error(f"[GitHub Sync] Failed to delete {rel_path}: {last_error}")
                if raise_on_error:
                    raise RuntimeError(f"GitHub delete failed for {rel_path}: {last_error}")
                return False
            except Exception as e:
                last_error = str(e)
                logger.error(f"[GitHub Sync] Network error deleting {rel_path}: {last_error}")
                if raise_on_error:
                    raise RuntimeError(f"GitHub network error deleting {rel_path}: {last_error}") from e
                return False

    return False


def push_file_async(file_path: Path | str, commit_message: Optional[str] = None) -> Optional[threading.Thread]:
    """
    Background worker wrapper for sync_file_push (used when non-blocking async is explicitly needed).
    """
    if not is_configured():
        return None

    t = threading.Thread(
        target=sync_file_push,
        args=(file_path, commit_message, False),
        daemon=True,
        name=f"gh-sync-push-{Path(file_path).name}",
    )
    t.start()
    return t


def delete_file_async(file_path: Path | str, commit_message: Optional[str] = None) -> Optional[threading.Thread]:
    """
    Background worker wrapper for sync_file_delete (used when non-blocking async is explicitly needed).
    """
    if not is_configured():
        return None

    t = threading.Thread(
        target=sync_file_delete,
        args=(file_path, commit_message, False),
        daemon=True,
        name=f"gh-sync-del-{Path(file_path).name}",
    )
    t.start()
    return t


def _download_raw_file(rel_path: str) -> Optional[bytes]:
    """Downloads raw file content from GitHub repository contents API."""
    token = get_token()
    repo = get_data_repo()
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
    repo = get_data_repo()
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
        stats["failed"].append(dir_path)
        return
    except Exception as e:
        logger.error(f"[GitHub Sync] Error listing '{dir_path}': {e}")
        stats["failed"].append(dir_path)
        return

    if not isinstance(items, list):
        return

    for item in items:
        item_path = item.get("path")
        item_type = item.get("type")
        item_name = item.get("name", "")

        # Skip ignored, temporary, and hidden files
        if (
            item_name.startswith(".")
            or item_name.startswith("preview_temp")
            or item_name.endswith(".tmp")
            or item_name.endswith("~")
        ):
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
    Pulls and restores all persistent files (templates, trainers, fonts) from the GitHub repository.
    Called on server startup so Render container restarts never lose user data.
    """
    stats: Dict[str, Any] = {
        "status": "skipped",
        "configured": is_configured(),
        "repo": get_data_repo() if is_configured() else None,
        "branch": get_branch() if is_configured() else None,
        "pulled": [],
        "skipped": [],
        "failed": [],
    }

    if not is_configured():
        set_hydration_status("unconfigured", None)
        logger.info("[GitHub Sync] GITHUB_TOKEN not configured. Storage sync is inactive (local mode).")
        return stats

    logger.info(f"[GitHub Sync] Starting initial pull from https://github.com/{get_data_repo()} (branch: {get_branch()})...")

    with _sync_lock:
        for store_dir in ALLOWED_SYNC_DIRS:
            _sync_pull_directory(store_dir, stats)

    if not stats["failed"]:
        stats["status"] = "ok"
        set_hydration_status("healthy", None)
    else:
        stats["status"] = "partial" if stats["pulled"] or stats["skipped"] else "failed"
        err_msg = f"Startup hydration incomplete: {len(stats['failed'])} directory/file failures"
        set_hydration_status("degraded", err_msg)

    logger.info(
        f"[GitHub Sync] Startup pull completed: {len(stats['pulled'])} downloaded, "
        f"{len(stats['skipped'])} already up-to-date, {len(stats['failed'])} failed. Status: {stats['status']}"
    )
    return stats
