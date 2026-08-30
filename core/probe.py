from __future__ import annotations

import time
from typing import Any

from .score import score_account
from .normalize import normalize_probe_answer


PROBE_MODEL = "gpt-5.6-sol"
SYSTEM_PROMPT = "."
REASONING_EFFORT = "none"
RETRY_BUDGET = 4

PROBES = (
    {
        "id": "rand_country",
        "prompt": "Name a random country. Reply with ONLY the country name.",
    },
    {
        "id": "rand_bird",
        "prompt": "Name a random bird. Reply with ONLY the bird name, one word.",
    },
    {
        "id": "b80_letter_count",
        "prompt": "Count the letter r in strawberry. Reply only with the integer.",
    },
)


def _probe_payload(prompt: str) -> dict[str, Any]:
    return {
        "model_id": PROBE_MODEL,
        "prompt": prompt,
        "system_prompt": SYSTEM_PROMPT,
        "reasoning_effort": REASONING_EFFORT,
        "mode": "",
    }


def _run_single_probe(client: Any, account_id: int, prompt: str) -> str:
    for attempt in range(RETRY_BUDGET + 1):
        try:
            raw = client.test_account(account_id, _probe_payload(prompt))
            return raw
        except Exception:
            if attempt >= RETRY_BUDGET:
                raise
            time.sleep(0.25)
    raise RuntimeError("unreachable")


def run_account_probes(client: Any, account: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    probe_values: dict[str, list[str]] = {probe["id"]: [] for probe in PROBES}
    failure = ""
    for probe in PROBES:
        probe_id = probe["id"]
        for _ in range(3):
            try:
                raw = _run_single_probe(client, int(account["id"]), probe["prompt"])
                probe_values[probe_id].append(normalize_probe_answer(probe_id, raw))
            except Exception as exc:
                failure = str(exc)
                break
        if failure:
            break

    if failure:
        return {
            "complete": False,
            "failure": failure,
            "probe_values": probe_values,
            "score": score_account(probe_values, baseline),
        }

    return {
        "complete": True,
        "failure": "",
        "probe_values": probe_values,
        "score": score_account(probe_values, baseline),
    }
