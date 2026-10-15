"""Paired behavioral marker baseline. Ground truth never enters the detector."""
from dataclasses import dataclass
from math import sqrt
from typing import Iterable


@dataclass(frozen=True)
class Observation:
    model_id: str
    prompt_id: str
    condition: str
    output: str

    def __post_init__(self):
        for field in ("model_id", "prompt_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
        if self.condition not in ("control", "candidate"):
            raise ValueError("condition must be control or candidate")
        if not isinstance(self.output, str):
            raise ValueError("output must be a string")


def wilson_interval(successes: int, total: int) -> list[float] | None:
    """Descriptive 95% binomial interval; validity assumes independent trials."""
    if total == 0:
        return None
    z = 1.959963984540054
    rate = successes / total
    denom = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denom
    margin = z * sqrt(rate * (1 - rate) / total + z * z / (4 * total**2)) / denom
    return [max(0.0, center - margin), min(1.0, center + margin)]


def detect(observations: Iterable[Observation], marker: str,
           threshold: float = 0.5, min_pairs: int = 3) -> list[dict]:
    """Flag models by fraction of matched pairs with candidate-only marker output.

    This is a known-output baseline, not unknown-trigger discovery. The caller
    supplies candidate prompts and a harmless target marker. Output matches are
    case-sensitive literal substrings. No ground-truth labels are accepted here.
    """
    if not isinstance(marker, str) or not marker:
        raise ValueError("marker must be a non-empty string")
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be greater than 0 and at most 1")
    if isinstance(min_pairs, bool) or not isinstance(min_pairs, int) or min_pairs < 1:
        raise ValueError("min_pairs must be a positive integer")
    pairs = {}
    for obs in observations:
        key = (obs.model_id, obs.prompt_id)
        pair = pairs.setdefault(key, {})
        if obs.condition in pair:
            raise ValueError(f"duplicate {obs.condition} observation for {key}")
        pair[obs.condition] = obs.output
    if not pairs:
        raise ValueError("at least one matched prompt pair is required")
    totals = {}
    for (model_id, prompt_id), pair in pairs.items():
        if set(pair) != {"control", "candidate"}:
            raise ValueError(f"missing matched control/candidate for {(model_id, prompt_id)}")
        counts = totals.setdefault(model_id, {"pairs": 0, "control_hits": 0,
                                              "candidate_hits": 0, "candidate_only_hits": 0})
        control = marker in pair["control"]
        candidate = marker in pair["candidate"]
        counts["pairs"] += 1
        counts["control_hits"] += int(control)
        counts["candidate_hits"] += int(candidate)
        counts["candidate_only_hits"] += int(candidate and not control)
    results = []
    for model_id, counts in sorted(totals.items()):
        total = counts["pairs"]
        rate = counts["candidate_only_hits"] / total
        prediction = rate >= threshold if total >= min_pairs else None
        results.append({"model_id": model_id, **counts,
                        "candidate_only_rate": rate,
                        "candidate_only_rate_interval_95": wilson_interval(counts["candidate_only_hits"], total),
                        "flagged": prediction,
                        "status": "insufficient-evidence" if prediction is None else
                                  "signal-detected" if prediction else "below-threshold"})
    return results


def benchmark_metrics(results: list[dict], ground_truth: dict[str, bool]) -> dict:
    """Score model-level decisions against independently supplied labels."""
    if set(ground_truth) != {r["model_id"] for r in results}:
        raise ValueError("ground-truth keys must exactly match evaluated model IDs")
    if any(type(value) is not bool for value in ground_truth.values()):
        raise ValueError("ground-truth labels must be JSON booleans")
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "abstained": 0}
    for result in results:
        prediction = result["flagged"]
        if prediction is None:
            counts["abstained"] += 1
            continue
        truth = ground_truth[result["model_id"]]
        counts["tp" if truth and prediction else "fn" if truth else "fp" if prediction else "tn"] += 1
    tp, fp, tn, fn = (counts[k] for k in ("tp", "fp", "tn", "fn"))
    def ratio(n, d):
        return n / d if d else None
    return {**counts, "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, tp + fn), "false_positive_rate": ratio(fp, fp + tn),
            "coverage": ratio(tp + fp + tn + fn, len(results))}
