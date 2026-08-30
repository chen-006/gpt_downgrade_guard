from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
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


def run_account_probes(client: Any, account: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    probe_values: dict[str, list[str]] = {probe["id"]: [] for probe in PROBES}

    def run_sample(probe: dict[str, str]) -> tuple[str, str, str, int, int]:
        probe_id = probe["id"]
        for attempt in range(RETRY_BUDGET + 1):
            try:
                raw = client.test_account(int(account["id"]), _probe_payload(probe["prompt"]))
                return probe_id, normalize_probe_answer(probe_id, raw), "", attempt + 1, 1
            except Exception as exc:
                if attempt >= RETRY_BUDGET:
                    return probe_id, "", str(exc), attempt + 1, 0
                time.sleep(0.25)
        raise RuntimeError("unreachable")

    samples = [probe for probe in PROBES for _ in range(3)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run_sample, samples))

    failures = []
    for probe_id, value, failure, _, _ in results:
        if failure:
            failures.append(failure)
        else:
            probe_values[probe_id].append(value)
    stats = {
        "request_count": sum(item[3] for item in results),
        "success_count": sum(item[4] for item in results),
    }

    if failures:
        return {
            "complete": False,
            "failure": failures[0],
            **stats,
            "probe_values": probe_values,
            "score": score_account(probe_values, baseline),
        }

    return {
        "complete": True,
        "failure": "",
        **stats,
        "probe_values": probe_values,
        "score": score_account(probe_values, baseline),
    }
