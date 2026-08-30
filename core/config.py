from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Any


@dataclass
class Config:
    sub2api_base_url: str = "http://127.0.0.1:3000"
    admin_token: str = ""
    group_a_id: int = 0
    group_b_id: int = 0
    interval_seconds: int = 180
    downgrade_rule: str = "严格"
    listen: str = "127.0.0.1:8787"

    @classmethod
    def default(cls) -> "Config":
        return cls()

    def updated(self, updates: dict[str, Any]) -> "Config":
        data = asdict(self)
        for key, value in updates.items():
            if key in data and value is not None:
                data[key] = value
        data["sub2api_base_url"] = str(data["sub2api_base_url"]).strip() or self.sub2api_base_url
        data["admin_token"] = str(data["admin_token"]).strip()
        data["group_a_id"] = int(data["group_a_id"] or 0)
        data["group_b_id"] = int(data["group_b_id"] or 0)
        data["interval_seconds"] = max(1, int(data["interval_seconds"] or 180))
        rule = str(data["downgrade_rule"] or "严格").strip()
        data["downgrade_rule"] = "严格" if rule == "严格" else "宽松"
        data["listen"] = str(data["listen"] or "127.0.0.1:8787").strip() or "127.0.0.1:8787"
        return Config(**data)

    def public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["admin_token_set"] = bool(self.admin_token.strip())
        data.pop("admin_token", None)
        return data


def load_config(path: Path) -> Config:
    if not path.is_file():
        save_config(path, Config.default())
        return Config.default()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return Config.default()
    return Config.default().updated(raw)


def save_config(path: Path, config: Config) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data_dict = asdict(config)
    data_dict["admin_token"] = ""
    data = json.dumps(data_dict, ensure_ascii=False, indent=2)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(data, encoding="utf-8")
    temp.replace(path)
