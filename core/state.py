from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._state = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {
                "running": False,
                "paused": False,
                "last_run_started_at": "",
                "last_run_finished_at": "",
                "last_error": "",
                "next_run_at": "",
                "group_a_count": 0,
                "group_b_count": 0,
                "checked_count": 0,
                "groups": {"a": {}, "b": {}},
                "accounts": [],
                "config": {},
            }
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return raw
        except Exception:
            pass
        return {
            "running": False,
            "paused": False,
            "last_run_started_at": "",
            "last_run_finished_at": "",
            "last_error": "",
            "next_run_at": "",
            "group_a_count": 0,
            "group_b_count": 0,
            "checked_count": 0,
            "groups": {"a": {}, "b": {}},
            "accounts": [],
            "config": {},
        }

    def save(self) -> None:
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def update(self, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._state.update(values)
            self.save()
            return self.snapshot()

    def merge_account(
        self,
        *,
        account_id: int,
        name: str,
        platform: str,
        group_ids: list[int],
        group_names: list[str],
        probe_result: dict[str, Any],
        final: dict[str, Any],
        moved_to: str,
        moved: bool,
        move_error: str,
    ) -> dict[str, Any]:
        with self._lock:
            accounts: list[dict[str, Any]] = list(self._state.get("accounts") or [])
            entry = None
            for item in accounts:
                if int(item.get("account_id") or 0) == account_id:
                    entry = item
                    break
            if entry is None:
                entry = {"account_id": account_id, "history": []}
                accounts.append(entry)
            history = list(entry.get("history") or [])
            history.append(
                {
                    "ts": _now(),
                    "result": final["result"],
                    "degraded": bool(final["degraded"]),
                    "moved_to": moved_to if moved and not move_error else "",
                    "move_error": move_error,
                }
            )
            history = history[-100:]
            entry.update(
                {
                    "account_id": account_id,
                    "account_name": name,
                    "platform": platform,
                    "group_ids": group_ids,
                    "group_names": group_names,
                    "last_result": final["result"],
                    "last_degraded": bool(final["degraded"]),
                    "last_checked_at": _now(),
                    "last_scores": final.get("matches") or {},
                    "last_probe_values": probe_result.get("probe_values") or {},
                    "last_probe_rows": final.get("probe_rows") or [],
                    "last_reasons": final.get("reasons") or [],
                    "last_failure": probe_result.get("failure") or move_error,
                    "moved": moved,
                    "move_error": move_error,
                    "history": history,
                }
            )
            self._state["accounts"] = sorted(accounts, key=lambda item: int(item.get("account_id") or 0))
            self.save()
            return entry

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._state, ensure_ascii=False))

    @staticmethod
    def now_iso() -> str:
        return _now()
