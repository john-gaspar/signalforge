from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class GateDecision:
    passed: bool
    reason: str
    score: float


class Gate:
    """Simple rule-based gate that evaluates payloads against thresholds."""

    def __init__(self, thresholds: Mapping[str, float]):
        self.thresholds = dict(thresholds)

    def evaluate(self, metrics: Mapping[str, float]) -> GateDecision:
        missing = [key for key in self.thresholds if key not in metrics]
        if missing:
            return GateDecision(False, f"missing metrics: {', '.join(missing)}", score=0.0)

        failures = [key for key, limit in self.thresholds.items() if metrics[key] < limit]
        if failures:
            reason = ", ".join(f"{key}<{self.thresholds[key]}" for key in failures)
            return GateDecision(False, f"below threshold: {reason}", score=min(metrics.values()))

        return GateDecision(True, "all thresholds satisfied", score=min(metrics.values()))
