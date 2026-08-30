from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse


_LEVELDB_EXTS = {".log", ".ldb", ".sst"}
_PROFILE_NAMES = {"Default", "Guest Profile"}


def find_browser_admin_tokens(base_url: str) -> list[str]:
    parsed = urlparse(base_url.strip())
    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if not origin:
        return []

    files: list[Path] = []
    for user_data_root in _user_data_roots():
        for profile_dir in _profile_dirs(user_data_root):
            leveldb = profile_dir / "Local Storage" / "leveldb"
            if not leveldb.is_dir():
                continue
            files.extend(
                path
                for path in leveldb.iterdir()
                if path.is_file() and path.suffix.lower() in _LEVELDB_EXTS
            )

    files.sort(key=_modified_time, reverse=True)
    tokens: list[str] = []
    seen: set[str] = set()
    for file_path in files:
        for token in _scan_file(file_path, origin):
            if token in seen:
                continue
            seen.add(token)
            tokens.append(token)
    return tokens


def find_browser_admin_token(base_url: str) -> str | None:
    tokens = find_browser_admin_tokens(base_url)
    return tokens[0] if tokens else None


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
    try:
        children = user_data_root.iterdir()
    except OSError:
        return out
    for child in children:
        if child.is_dir() and (child.name in _PROFILE_NAMES or child.name.startswith("Profile ")):
            out.append(child)
    return out


def _scan_file(path: Path, origin: str) -> list[str]:
    try:
        text = path.read_bytes().decode("utf-8", errors="ignore")
    except OSError:
        return []
    marker = origin.lower()
    lowered = text.lower()
    matches: list[tuple[int, str]] = []
    start = lowered.find(marker)
    while start >= 0:
        window = text[start : start + 1000]
        for token_match in re.finditer(
            r"(?<![A-Za-z0-9_\-.])([A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})(?![A-Za-z0-9_\-.])",
            window,
        ):
            matches.append((start + token_match.start(), token_match.group(1)))
        start = lowered.find(marker, start + len(marker))
    matches.sort(reverse=True)
    return [token for _, token in matches]


def _modified_time(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0
