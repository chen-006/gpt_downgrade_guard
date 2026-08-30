from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse


_LEVELDB_EXTS = {".log", ".ldb", ".sst"}
_PROFILE_NAMES = {"Default", "Profile 1", "Profile 2", "Profile 3", "Profile 4", "Guest Profile"}


def find_browser_admin_token(base_url: str) -> str | None:
    parsed = urlparse(base_url.strip())
    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    host = parsed.netloc
    host_only = parsed.hostname or ""
    search_terms = [term for term in {origin, host, host_only} if term]

    for user_data_root in _user_data_roots():
        for profile_dir in _profile_dirs(user_data_root):
            leveldb = profile_dir / "Local Storage" / "leveldb"
            if not leveldb.is_dir():
                continue
            for file_path in sorted(leveldb.iterdir()):
                if not file_path.is_file() or file_path.suffix.lower() not in _LEVELDB_EXTS:
                    continue
                token = _scan_file(file_path, search_terms)
                if token:
                    return token
    return None


def _user_data_roots() -> list[Path]:
    local = os.environ.get("LOCALAPPDATA", "")
    if not local:
        return []
    roots = [
        Path(local) / "Google" / "Chrome" / "User Data",
        Path(local) / "Microsoft" / "Edge" / "User Data",
        Path(local) / "BraveSoftware" / "Brave-Browser" / "User Data",
        Path(local) / "Chromium" / "User Data",
    ]
    return [root for root in roots if root.is_dir()]


def _profile_dirs(user_data_root: Path) -> list[Path]:
    out: list[Path] = []
    for child in user_data_root.iterdir():
        if child.is_dir() and (child.name in _PROFILE_NAMES or child.name.startswith("Profile ")):
            out.append(child)
    return out


def _scan_file(path: Path, search_terms: list[str]) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if not raw:
        return None
    text = raw.decode("utf-8", errors="ignore")
    lowered = text.lower()
    if "auth_token" not in lowered:
        return None
    if search_terms and not any(term.lower() in lowered for term in search_terms):
        return None

    for match in re.finditer(r'["\']auth_token["\']\s*[:=]\s*["\']([^"\']{16,})["\']', text, re.IGNORECASE):
        token = match.group(1).strip()
        if _looks_like_token(token):
            return token

    for match in re.finditer(r'auth_token[^A-Za-z0-9_\-]{0,16}([A-Za-z0-9_\-\.]{20,})', text, re.IGNORECASE):
        token = match.group(1).strip()
        if _looks_like_token(token):
            return token

    for pos in _find_all(lowered, "auth_token"):
        window = text[max(0, pos - 120) : min(len(text), pos + 600)]
        for match in re.finditer(r'([A-Za-z0-9_\-\.]{24,})', window):
            token = match.group(1).strip()
            if _looks_like_token(token):
                return token
    return None


def _find_all(text: str, needle: str) -> list[int]:
    out: list[int] = []
    start = 0
    while True:
        pos = text.find(needle, start)
        if pos < 0:
            break
        out.append(pos)
        start = pos + len(needle)
    return out


def _looks_like_token(value: str) -> bool:
    if len(value) < 16:
        return False
    bad = {"auth_token", "null", "undefined", "none"}
    return value.lower() not in bad
