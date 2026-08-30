from __future__ import annotations

import re
from typing import Any


def normalize_behavior_label(text: Any) -> str:
    value = str(text or "")
    value = value.strip().strip('`"\'.,:;!?()[]{}')
    value = re.sub(r"\s+", " ", value).casefold()
    if not value:
        return "__INVALID_OUTPUT__"
    if len(value) > 128:
        return "__INVALID_OUTPUT__"
    if not re.fullmatch(r"[a-z][a-z .'-]*", value):
        return "__INVALID_OUTPUT__"
    return value


def normalize_b80(text: Any) -> str:
    value = str(text or "").strip()
    if not re.fullmatch(r"[+-]?\d+", value):
        return "__INVALID_OUTPUT__"
    return "exact_3" if int(value) == 3 else "other_integer"


def normalize_probe_answer(probe_id: str, text: Any) -> str:
    if probe_id in {"rand_country", "rand_bird"}:
        return normalize_behavior_label(text)
    if probe_id == "b80_letter_count":
        return normalize_b80(text)
    return str(text or "").strip().casefold() or "__INVALID_OUTPUT__"
