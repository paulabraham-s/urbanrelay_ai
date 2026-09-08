"""Explainable weighted scoring.

Each agent produces components in [0, 1] where higher is better, combines them
with configured weights, and emits the score plus per-component reasons so the
AI Decision Center can explain every decision.
"""

from typing import Callable


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def normalize(value: float, lo: float, hi: float, higher_better: bool = True) -> float:
    """Linearly map `value` in [lo, hi] to [0, 1]."""
    if hi <= lo:
        return 1.0
    f = (value - lo) / (hi - lo)
    f = clamp01(f)
    return f if higher_better else 1.0 - f


def weighted_score(
    components: dict[str, float],
    weights: dict[str, float],
    weight_label: Callable[[str], str] | None = None,
) -> tuple[float, list[dict]]:
    """Combine normalized components -> (score in [0,1], reasons).

    reasons: [{key, label, value, weight, contribution}]
    """
    total_w = sum(weights.get(k, 0.0) for k in components)
    if total_w <= 0:
        return 0.0, []
    score = sum(clamp01(v) * weights.get(k, 0.0) for k, v in components.items()) / total_w
    reasons = []
    for key, value in sorted(components.items(), key=lambda kv: kv[1], reverse=True):
        w = weights.get(key, 0.0)
        if w <= 0:
            continue
        label = weight_label(key) if weight_label else key.replace("_", " ").title()
        reasons.append(
            {
                "key": key,
                "label": label,
                "value": round(clamp01(value), 3),
                "weight": w,
                "contribution": round(clamp01(value) * w / total_w, 3),
            }
        )
    return round(score, 3), reasons