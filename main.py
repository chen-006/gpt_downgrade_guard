from __future__ import annotations

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from core.config import Config, load_config, save_config
from core.probe import run_account_probes
from core.score import classify_account, load_baseline
from core.state import StateStore
from browser_token import find_browser_admin_tokens
from sub2api.client import Sub2APIClient, Sub2APIError


ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui"
DATA_DIR = ROOT / "data"
CONFIG_PATH = ROOT / "config.json"
BASELINE_PATH = ROOT / "core" / "baseline_low.json"
STATE_PATH = DATA_DIR / "state.json"


class GuardApp:
    def __init__(self, config_path: Path, state_path: Path) -> None:
        self.config_path = config_path
        self.state = StateStore(state_path)
        self.config = load_config(config_path)
        self.baseline = load_baseline(BASELINE_PATH)
        self.client = self._make_client()
        self._lock = threading.Lock()
        self._run_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._wakeup_event = threading.Event()
        self._scheduler_thread: threading.Thread | None = None
        self._httpd: ThreadingHTTPServer | None = None
        self._server_url = ""
        self._ensure_state_defaults()

    def _make_client(self) -> Sub2APIClient | None:
        if not self.config.sub2api_base_url.strip() or not self.config.admin_token.strip():
            return None
        return Sub2APIClient(self.config.sub2api_base_url, self.config.admin_token)

    def _ensure_state_defaults(self) -> None:
        self.state.update(
            {
                "config": self.config.public_dict(),
                "running": False,
                "paused": False,
                "last_error": "",
                "checked_count": 0,
                "group_a_count": 0,
                "group_b_count": 0,
                "groups": {"a": {}, "b": {}},
                "accounts": [],
            }
        )

    def reload_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            refresh_counts = any(
                key in updates for key in ("sub2api_base_url", "admin_token", "group_a_id", "group_b_id")
            )
            self.config = self.config.updated(updates)
            save_config(self.config_path, self.config)
            self.client = self._make_client()
            state_update = {"config": self.config.public_dict(), "last_error": ""}
            if refresh_counts and self.client is not None and self.config.group_a_id > 0 and self.config.group_b_id > 0:
                accounts, _, configured_groups = self._load_accounts()
                state_update.update(
                    {
                        "group_a_count": sum(
                            1 for item in accounts if self.config.group_a_id in (item.get("group_ids") or [])
                        ),
                        "group_b_count": sum(
                            1 for item in accounts if self.config.group_b_id in (item.get("group_ids") or [])
                        ),
                        "groups": configured_groups,
                    }
                )
            self.state.update(state_update)
            return self.config.public_dict()

    def auto_fetch_admin_token(self) -> dict[str, Any]:
        tokens = find_browser_admin_tokens(self.config.sub2api_base_url)
        if not tokens:
            raise Sub2APIError("没有在常见浏览器里找到管理令牌")
        for token in tokens:
            try:
                Sub2APIClient(self.config.sub2api_base_url, token).list_groups()
            except Sub2APIError:
                continue
            return self.reload_config({"admin_token": token})
        raise Sub2APIError("找到了浏览器令牌，但没有可用的管理员令牌")

    def set_paused(self, paused: bool) -> dict[str, Any]:
        with self._lock:
            self.state.update({"paused": paused, "next_run_at": "" if paused else self.state.snapshot().get("next_run_at", "")})
            return self.state.snapshot()

    def request_run(self) -> dict[str, Any]:
        if int(self.config.group_a_id) <= 0 or int(self.config.group_b_id) <= 0:
            message = "请先选择分组 A 和分组 B"
            self.state.update({"last_error": message})
            return {"accepted": False, "busy": False, "error": message}
        if not self._run_lock.acquire(blocking=False):
            return {"accepted": False, "busy": True}
        thread = threading.Thread(target=self._run_once, daemon=True)
        thread.start()
        return {"accepted": True, "busy": False}

    def start_scheduler(self) -> None:
        if self._scheduler_thread is not None:
            return
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._wakeup_event.set()
        if self._httpd is not None:
            self._httpd.shutdown()

    def _scheduler_loop(self) -> None:
        while not self._stop_event.is_set():
            interval = max(1, int(self.config.interval_seconds))
            if self.state.snapshot().get("paused"):
                self._wakeup_event.wait(1.0)
                self._wakeup_event.clear()
                continue
            self._wakeup_event.wait(interval)
            self._wakeup_event.clear()
            if self._stop_event.is_set() or self.state.snapshot().get("paused"):
                continue
            self.request_run()

    def _load_accounts(self) -> tuple[list[dict[str, Any]], dict[int, str], dict[str, Any]]:
        if self.client is None:
            raise Sub2APIError("请先填写 Sub2 API 地址和管理令牌")
        groups = self.client.list_groups()
        group_names = {int(group["id"]): str(group.get("name") or "") for group in groups}
        group_a = int(self.config.group_a_id)
        group_b = int(self.config.group_b_id)
        if group_a <= 0 or group_b <= 0:
            raise Sub2APIError("请先选择分组 A 和分组 B")
        accounts_a = self.client.list_accounts_by_group(group_a)
        accounts_b = self.client.list_accounts_by_group(group_b)
        merged: dict[int, dict[str, Any]] = {}
        selected_groups = {group_a, group_b}
        for item in accounts_a + accounts_b:
            if str(item.get("platform") or "").strip().lower() != "openai":
                continue
            item_groups = {int(value) for value in item.get("group_ids") or []}
            if not item_groups.intersection(selected_groups):
                continue
            account_id = int(item["id"])
            merged[account_id] = dict(item)
        accounts = list(merged.values())
        accounts.sort(key=lambda item: int(item["id"]))
        return accounts, group_names, {
            "a": {"id": group_a, "name": group_names.get(group_a, "")},
            "b": {"id": group_b, "name": group_names.get(group_b, "")},
        }

    def _run_once(self) -> None:
        try:
            interval = max(1, int(self.config.interval_seconds))
            self.state.update(
                {
                    "running": True,
                    "last_run_started_at": self.state.now_iso(),
                    "last_error": "",
                    "next_run_at": self._future_iso(interval),
                }
            )
            self._wakeup_event.clear()

            if self.client is None:
                self.state.update(
                    {
                        "running": False,
                        "last_run_finished_at": self.state.now_iso(),
                        "last_error": "请先填写连接信息",
                    }
                )
                return

            accounts, group_names, configured_groups = self._load_accounts()
            account_rows: list[dict[str, Any]] = []
            checked_count = 0
            group_a_id = int(self.config.group_a_id)
            group_b_id = int(self.config.group_b_id)
            initial_a_count = sum(1 for item in accounts if group_a_id in (item.get("group_ids") or []))
            initial_b_count = sum(1 for item in accounts if group_b_id in (item.get("group_ids") or []))
            self.state.update(
                {
                    "checked_count": 0,
                    "group_a_count": initial_a_count,
                    "group_b_count": initial_b_count,
                    "groups": configured_groups,
                }
            )

            def process_account(account: dict[str, Any]) -> dict[str, Any]:
                probe_result = run_account_probes(self.client, account, self.baseline)
                final = classify_account(probe_result.get("score") or {}, self.config.downgrade_rule)
                current_groups = [int(value) for value in account.get("group_ids") or []]
                request_error = not bool(probe_result.get("complete"))
                if request_error:
                    final["result"] = "网络错误/上游错误"
                    final["degraded"] = False
                    next_groups = current_groups
                else:
                    target_group = group_b_id if final["degraded"] else group_a_id
                    next_groups = self._move_groups(current_groups, group_a_id, group_b_id, target_group)

                moved = False
                move_error = ""
                if next_groups != current_groups:
                    try:
                        self.client.update_account_groups(int(account["id"]), next_groups)
                        moved = True
                        account["group_ids"] = next_groups
                    except Exception as exc:  # pragma: no cover - surfaced in UI
                        move_error = str(exc)

                return self.state.merge_account(
                    account_id=int(account["id"]),
                    name=str(account.get("name") or f"账号 {account['id']}"),
                    platform=str(account.get("platform") or ""),
                    group_ids=current_groups if move_error else next_groups,
                    group_names=[group_names.get(gid, str(gid)) for gid in (current_groups if move_error else next_groups)],
                    probe_result=probe_result,
                    final=final,
                    moved_to="" if request_error else ("B" if final["degraded"] else "A"),
                    moved=moved,
                    move_error=move_error,
                    request_error=request_error,
                )

            with ThreadPoolExecutor(max_workers=max(1, len(accounts))) as pool:
                futures = [pool.submit(process_account, account) for account in accounts]
                for future in as_completed(futures):
                    account_rows.append(future.result())
                    checked_count += 1
                    self.state.update({"checked_count": checked_count})

            account_rows.sort(key=lambda item: int(item.get("account_id") or 0))
            group_a_count = sum(1 for item in account_rows if group_a_id in item.get("group_ids", []))
            group_b_count = sum(1 for item in account_rows if group_b_id in item.get("group_ids", []))
            self.state.update(
                {
                    "running": False,
                    "last_run_finished_at": self.state.now_iso(),
                    "next_run_at": self._future_iso(interval),
                    "checked_count": checked_count,
                    "group_a_count": group_a_count,
                    "group_b_count": group_b_count,
                    "groups": configured_groups,
                    "accounts": account_rows,
                    "config": self.config.public_dict(),
                }
            )
        except Exception as exc:
            self.state.update(
                {
                    "running": False,
                    "last_run_finished_at": self.state.now_iso(),
                    "next_run_at": self._future_iso(max(1, int(self.config.interval_seconds))),
                    "last_error": str(exc),
                }
            )
        finally:
            self._run_lock.release()

    @staticmethod
    def _move_groups(current: list[int], group_a: int, group_b: int, target: int) -> list[int]:
        unique: list[int] = []
        for value in current:
            if value not in unique:
                unique.append(value)
        if target == group_b:
            out = [value for value in unique if value != group_a]
            if group_b not in out:
                out.append(group_b)
            return out
        out = [value for value in unique if value != group_b]
        if group_a not in out:
            out.append(group_a)
        return out

    def serve(self) -> None:
        app = self

        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                return

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/":
                    self._serve_file(UI_DIR / "index.html", "text/html; charset=utf-8")
                    return
                if self.path == "/app.js":
                    self._serve_file(UI_DIR / "app.js", "application/javascript; charset=utf-8")
                    return
                if self.path == "/style.css":
                    self._serve_file(UI_DIR / "style.css", "text/css; charset=utf-8")
                    return
                if self.path == "/api/status":
                    self._send_json(app.state.snapshot())
                    return
                if self.path == "/api/config":
                    payload = app.config.public_dict()
                    payload["admin_token_set"] = bool(app.config.admin_token.strip())
                    self._send_json(payload)
                    return
                if self.path == "/api/groups":
                    if app.client is None:
                        self._send_json({"items": []})
                        return
                    try:
                        self._send_json({"items": app.client.list_groups()})
                    except Sub2APIError as exc:
                        self._send_json({"items": [], "error": str(exc)})
                    return
                if self.path == "/api/token/auto":
                    try:
                        payload = app.auto_fetch_admin_token()
                    except Sub2APIError as exc:
                        self._send_json({"ok": False, "error": str(exc)})
                        return
                    self._send_json({"ok": True, "config": payload})
                    return
                self.send_error(404)

            def do_POST(self) -> None:  # noqa: N802
                body = self._read_json()
                if self.path == "/api/config":
                    updates = dict(body)
                    if not str(updates.get("admin_token", "")).strip():
                        updates.pop("admin_token", None)
                    payload = app.reload_config(updates)
                    app._wakeup_event.set()
                    self._send_json({"ok": True, "config": payload})
                    return
                if self.path == "/api/run-now":
                    result = app.request_run()
                    self._send_json({"ok": True, **result})
                    return
                if self.path == "/api/token/auto":
                    try:
                        payload = app.auto_fetch_admin_token()
                    except Sub2APIError as exc:
                        self._send_json({"ok": False, "error": str(exc)})
                        return
                    app._wakeup_event.set()
                    self._send_json({"ok": True, "config": payload})
                    return
                if self.path == "/api/pause":
                    self._send_json({"ok": True, **app.set_paused(True)})
                    return
                if self.path == "/api/resume":
                    app._wakeup_event.set()
                    self._send_json({"ok": True, **app.set_paused(False)})
                    return
                self.send_error(404)

            def _read_json(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0:
                    return {}
                raw = self.rfile.read(length).decode("utf-8", errors="replace")
                if not raw.strip():
                    return {}
                return json.loads(raw)

            def _send_json(self, payload: dict[str, Any]) -> None:
                data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _serve_file(self, path: Path, content_type: str) -> None:
                if not path.is_file():
                    self.send_error(404)
                    return
                data = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        host, port_text = self.config.listen.split(":", 1)
        port = int(port_text)
        try:
            server = ThreadingHTTPServer((host, port), Handler)
        except OSError:
            server = ThreadingHTTPServer((host, 0), Handler)
        self._httpd = server
        self._server_url = f"http://{server.server_address[0]}:{server.server_address[1]}"
        print(f"Sub2 API 防降智小程序已启动: {self._server_url}")
        self.start_scheduler()
        if not self.state.snapshot().get("paused"):
            self.request_run()
        try:
            server.serve_forever()
        finally:
            self.stop()

    @staticmethod
    def _future_iso(seconds: int) -> str:
        return (datetime.now(timezone.utc).astimezone() + timedelta(seconds=seconds)).isoformat()


def prepare_files(config_path: Path) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config_path.is_file():
        example = ROOT / "config.example.json"
        if example.is_file():
            config_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            save_config(config_path, Config.default())


def main() -> int:
    parser = argparse.ArgumentParser(description="Sub2 API 防降智小程序")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="配置文件路径")
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    prepare_files(config_path)
    app = GuardApp(config_path, STATE_PATH)
    app.serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
