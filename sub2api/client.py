from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class Sub2APIError(RuntimeError):
    pass


USER_AGENT = "gpt-downgrade-guard/1.0"


@dataclass
class _ResponseData:
    text: str
    json_value: Any


class Sub2APIClient:
    def __init__(self, base_url: str, admin_token: str, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.admin_token = admin_token.strip()
        self.timeout = timeout

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None, body: dict[str, Any] | None = None) -> _ResponseData:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode({key: value for key, value in params.items() if value is not None})}"
        headers = {
            "Accept": "application/json, text/event-stream",
            "User-Agent": USER_AGENT,
        }
        if self.admin_token:
            headers["Authorization"] = f"Bearer {self.admin_token}"
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, method=method, headers=headers)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                text = response.read().decode("utf-8", errors="replace")
                return _ResponseData(text=text, json_value=self._parse_json_payload(text))
        except HTTPError as exc:
            raise Sub2APIError(exc.read().decode("utf-8", errors="replace") or str(exc)) from exc
        except (URLError, TimeoutError, ConnectionError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise Sub2APIError(str(reason)) from exc

    @staticmethod
    def _parse_json_payload(text: str) -> Any:
        stripped = text.strip()
        if not stripped:
            return None
        try:
            raw = json.loads(stripped)
        except Exception:
            return stripped
        if isinstance(raw, dict) and raw.get("code") == 0 and "data" in raw:
            return raw["data"]
        return raw

    def list_groups(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/api/v1/admin/groups/all", {"include_inactive": "true"}).json_value
        return list(payload or [])

    def list_accounts_by_group(self, group_id: int) -> list[dict[str, Any]]:
        page = 1
        items: list[dict[str, Any]] = []
        while True:
            payload = self._request(
                "GET",
                "/api/v1/admin/accounts",
                {
                    "page": page,
                    "page_size": 100,
                    "group": group_id,
                    "platform": "openai",
                    "sort_by": "id",
                    "sort_order": "asc",
                },
            ).json_value
            if not isinstance(payload, dict):
                break
            page_items = list(payload.get("items") or [])
            items.extend(page_items)
            if not page_items:
                break
            if page >= int(payload.get("pages") or 1):
                break
            page += 1
        return items

    def test_account(self, account_id: int, body: dict[str, Any]) -> str:
        request = Request(
            f"{self.base_url}/api/v1/admin/accounts/{account_id}/test",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                text = self._read_sse_response(response)
        except HTTPError as exc:
            raise Sub2APIError(exc.read().decode("utf-8", errors="replace") or str(exc)) from exc
        except (URLError, TimeoutError, ConnectionError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise Sub2APIError(str(reason)) from exc
        if not text.strip():
            raise Sub2APIError("测试没有返回内容")
        return text

    @staticmethod
    def _read_sse_response(response: Any) -> str:
        content = []
        while True:
            line = response.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").strip()
            if not text.startswith("data:"):
                continue
            payload = text[5:].strip()
            if not payload:
                continue
            try:
                event = json.loads(payload)
            except Exception:
                continue
            event_type = str(event.get("type") or "")
            if event_type == "content":
                content.append(str(event.get("text") or ""))
            if event_type == "error":
                raise Sub2APIError(str(event.get("error") or "测试失败"))
            if event_type == "test_complete":
                break
        return "".join(content)

    def update_account_groups(self, account_id: int, group_ids: list[int]) -> dict[str, Any]:
        payload = self._request(
            "PUT",
            f"/api/v1/admin/accounts/{account_id}",
            body={"group_ids": group_ids},
        ).json_value
        if not isinstance(payload, dict):
            return {}
        return payload
