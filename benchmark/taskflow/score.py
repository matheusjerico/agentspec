"""Transparent scoring for the TaskFlow benchmark."""

from __future__ import annotations

import json
from pathlib import Path

WEIGHTS = {
    "correctness": 0.35,
    "requirements_planning": 0.20,
    "tests": 0.15,
    "code_quality": 0.15,
    "review_pr": 0.10,
    "efficiency": 0.05,
}


def weighted_total(
    categories: dict[str, float],
    *,
    persistence_passed: bool = True,
    critical_defect: bool = False,
) -> float:
    total = sum(categories[name] * weight for name, weight in WEIGHTS.items())
    if not persistence_passed:
        total = min(total, 60.0)
    if critical_defect:
        total = min(total, 50.0)
    return round(total, 2)


def main() -> None:
    root = Path(__file__).parent / "runs"
    for framework in ("agentspec", "superpowers"):
        record = json.loads((root / framework / "evidence.json").read_text())
        print(framework, weighted_total(record["run"]["scores"]))


if __name__ == "__main__":
    main()
