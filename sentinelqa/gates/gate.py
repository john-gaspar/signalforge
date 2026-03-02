import json
from pathlib import Path
import yaml
import sys

def main():
    metrics_path = Path("artifacts/runs")  # choose latest run folder in CI; you’ll pass it in later
    thresholds = yaml.safe_load(Path("sentinelqa/gates/thresholds.yaml").read_text())

    # Simplest: find newest metrics.json
    metrics_files = sorted(metrics_path.glob("**/metrics.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not metrics_files:
        print("No metrics.json found; failing gate.")
        sys.exit(1)

    metrics = json.loads(metrics_files[0].read_text())
    failures = []

    for key, rule in thresholds.items():
        if not isinstance(rule, dict):
            continue
        if "max" not in rule and "min" not in rule:
            # Config sections (e.g., trend) are ignored by this gate.
            continue
        if key not in metrics:
            failures.append(f"Missing metric: {key}")
            continue
        val = metrics[key]
        if "max" in rule and val > rule["max"]:
            failures.append(f"{key}={val} > max {rule['max']}")
        if "min" in rule and val < rule["min"]:
            failures.append(f"{key}={val} < min {rule['min']}")

    if failures:
        print("QUALITY GATE FAILED")
        for f in failures:
            print(f"- {f}")
        sys.exit(1)

    print("QUALITY GATE PASSED")
    sys.exit(0)

if __name__ == "__main__":
    main()
