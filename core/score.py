from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
from typing import Any

MODELS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna")


def load_baseline(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _softmax(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {model: 1 / len(MODELS) for model in MODELS}
    peak = max(scores.values())
    exps = {model: math.exp(value - peak) for model, value in scores.items()}
    total = sum(exps.values()) or 1.0
    return {model: value / total for model, value in exps.items()}


def _avg_log_likelihood(counts: dict[str, int], distribution: dict[str, float], sample_count: int) -> float:
    if sample_count <= 0:
        return 0.0
    total = 0.0
    for category, count in counts.items():
        probability = float(distribution.get(category, distribution.get("__OTHER__", 1e-12)))
        total += int(count) * math.log(max(probability, 1e-300))
    return total / sample_count


def _normalize_counts(samples: list[str], distribution: dict[str, float]) -> dict[str, int]:
    categories = set(distribution.keys())
    counts = Counter(samples)
    normalized = {category: 0 for category in categories}
    for raw_category, count in counts.items():
        category = raw_category if raw_category in categories else "__OTHER__"
        if category not in normalized:
            normalized[category] = 0
        normalized[category] += count
    return normalized


def score_account(probe_values: dict[str, list[str]], baseline: dict[str, Any]) -> dict[str, Any]:
    probes = baseline.get("probes") or {}
    thresholds = baseline.get("thresholds") or {}
    total_scores = {model: 0.0 for model in MODELS}
    probe_rows: list[dict[str, Any]] = []
    reasons: list[str] = []
    all_complete = True

    for probe_id in ("rand_country", "rand_bird", "b80_letter_count"):
        spec = probes[probe_id]
        samples = [str(value or "__INVALID_OUTPUT__") for value in probe_values.get(probe_id, [])]
        counts = _normalize_counts(samples, spec["distributions"]["gpt-5.6-sol"])
        sample_count = len(samples)
        complete = sample_count >= 3
        all_complete = all_complete and complete
        if not complete:
            reasons.append("candidate_samples_incomplete")

        probe_scores = {}
        for model in MODELS:
            distribution = spec["distributions"][model]
            probe_scores[model] = spec["weight"] * _avg_log_likelihood(counts, distribution, sample_count)
            total_scores[model] += probe_scores[model]

        matches = _softmax(probe_scores)
        winners = [model for model in MODELS if complete and matches[model] > float(thresholds.get(model, 1.0))]
        if complete and not winners:
            reasons.append("no_model_reached_strong_match_threshold")
        if len(winners) > 1:
            reasons.append("multiple_models_reached_threshold")

        probe_rows.append(
            {
                "probe_id": probe_id,
                "prompt": spec["prompt"],
                "samples": samples,
                "counts": counts,
                "complete": complete,
                "weight": spec["weight"],
                "scores": probe_scores,
                "matches": matches,
                "winner": winners[0] if len(winners) == 1 else None,
                "status": "strong_match" if len(winners) == 1 else "unclear",
            }
        )

    matches = _softmax(total_scores)
    winners = [model for model in MODELS if all_complete and matches[model] > float(thresholds.get(model, 1.0))]
    if not all_complete and "candidate_samples_incomplete" not in reasons:
        reasons.append("candidate_samples_incomplete")
    if all_complete and not winners and "no_model_reached_strong_match_threshold" not in reasons:
        reasons.append("no_model_reached_strong_match_threshold")
    if len(winners) > 1 and "multiple_models_reached_threshold" not in reasons:
        reasons.append("multiple_models_reached_threshold")

    status = "strong_match" if len(winners) == 1 and all_complete else "unclear"
    model = winners[0] if len(winners) == 1 and all_complete else None
    return {
        "complete": all_complete,
        "status": status,
        "model": model,
        "matches": matches,
        "scores": total_scores,
        "thresholds": thresholds,
        "probe_rows": probe_rows,
        "reasons": sorted(set(reasons)),
    }


def classify_account(score: dict[str, Any], rule: str) -> dict[str, Any]:
    model = score.get("model")
    result = "证据不足"
    if score.get("complete") and score.get("status") == "strong_match" and model:
        result = {
            "gpt-5.6-sol": "强指向 Sol",
            "gpt-5.6-terra": "强指向 Terra",
            "gpt-5.6-luna": "强指向 Luna",
        }[model]
    degraded = False
    if rule == "严格":
        degraded = result != "强指向 Sol"
    else:
        degraded = result in {"强指向 Terra", "强指向 Luna"}
    return {
        "result": result,
        "degraded": degraded,
        "model": model,
        "matches": score.get("matches") or {},
        "scores": score.get("scores") or {},
        "thresholds": score.get("thresholds") or {},
        "probe_rows": score.get("probe_rows") or [],
        "reasons": score.get("reasons") or [],
        "complete": bool(score.get("complete")),
    }
