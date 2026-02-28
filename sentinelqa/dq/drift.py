from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _bucket_clusters(clusters: List[Dict[str, Any]]) -> Dict[str, int]:
    buckets = {"1": 0, "2-3": 0, "4-7": 0, "8+": 0}
    for c in clusters:
        size = len(c.get("members", []))
        if size <= 1:
            buckets["1"] += 1
        elif size <= 3:
            buckets["2-3"] += 1
        elif size <= 7:
            buckets["4-7"] += 1
        else:
            buckets["8+"] += 1
    return {k: v for k, v in buckets.items() if v > 0}


def _count_distribution(items: List[Dict[str, Any]], field: str) -> Dict[str, int]:
    dist: Dict[str, int] = {}
    for item in items:
        key = item.get(field)
        if key is None and "normalized" in item:
            key = item["normalized"].get(field)
        if key is None:
            continue
        dist[str(key)] = dist.get(str(key), 0) + 1
    return dist


def compute_summary(run_artifacts_dir: Path) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}

    events_path = run_artifacts_dir / "events.json"
    if events_path.exists():
        events = _read_json(events_path)
        summary["events"] = {
            "total": len(events),
            "by_type": _count_distribution(events, "event_type"),
            "by_severity": _count_distribution(events, "severity"),
        }
    else:
        summary["events"] = {"skipped": True}

    clusters_path = run_artifacts_dir / "clusters.json"
    if clusters_path.exists():
        clusters = _read_json(clusters_path)
        summary["clusters"] = {
            "count": len(clusters),
            "size_buckets": _bucket_clusters(clusters),
        }
    else:
        summary["clusters"] = {"skipped": True}

    metrics_path = run_artifacts_dir / "metrics.json"
    if metrics_path.exists():
        metrics = _read_json(metrics_path)
        required_keys = ["events", "clusters", "alerts_sent", "latency_ms"]
        present = [k for k in required_keys if k in metrics]
        summary["metrics"] = {
            "required_keys_present": present,
            "events": metrics.get("events"),
            "clusters": metrics.get("clusters"),
            "alerts_sent": metrics.get("alerts_sent"),
            "stable_flags": {"status": metrics.get("status")} if "status" in metrics else {},
        }
    else:
        summary["metrics"] = {"skipped": True}

    present_files = [p.name for p in run_artifacts_dir.iterdir() if p.is_file()]
    summary["artifacts"] = {"required_files_present": sorted(present_files)}

    return summary


def _get_value(summary: Dict[str, Any], path: str) -> Tuple[bool, Any]:
    parts = path.split(".")
    cur: Any = summary
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def _pct_points(baseline_count: float, current_count: float, baseline_total: float, current_total: float) -> float:
    if baseline_total == 0 and current_total == 0:
        return 0.0
    base_pct = (baseline_count / baseline_total * 100) if baseline_total else 0.0
    cur_pct = (current_count / current_total * 100) if current_total else 0.0
    return abs(cur_pct - base_pct)


def _compare_numeric(field: str, baseline_val: Any, current_val: Any, tolerance: Dict[str, Any]) -> List[str]:
    if not isinstance(current_val, (int, float)):
        return [f"{field}: missing or non-numeric (current={current_val})"]
    tol_type = tolerance.get("type", "absolute")
    tol_value = tolerance.get("value", 0)
    diff = abs(current_val - baseline_val)
    if tol_type == "absolute":
        if diff <= tol_value:
            return []
    elif tol_type == "percent":
        if baseline_val == 0:
            if current_val == 0:
                return []
        else:
            if diff / baseline_val <= tol_value:
                return []
    else:
        return [f"{field}: unknown tolerance type {tol_type}"]
    return [
        f"{field}: current={current_val} baseline={baseline_val} tolerance={tol_type}:{tol_value} diff={diff}"
    ]


def _compare_distribution(
    field: str, baseline_dist: Dict[str, int], current_dist: Dict[str, int], tolerance: Dict[str, Any]
) -> List[str]:
    keys = set(baseline_dist.keys()) | set(current_dist.keys())
    baseline_total = sum(baseline_dist.values())
    current_total = sum(current_dist.values())
    tol_type = tolerance.get("type", "percent_points")
    tol_value = tolerance.get("value", 0)

    diffs: List[str] = []
    for key in sorted(keys):
        base = baseline_dist.get(key, 0)
        cur = current_dist.get(key, 0)
        if tol_type == "percent_points":
            delta = _pct_points(base, cur, baseline_total, current_total)
            if delta > tol_value:
                diffs.append(
                    f"{field}.{key}: Δpct={delta:.2f}pp baseline={base}/{baseline_total} current={cur}/{current_total} tol={tol_value}pp"
                )
        elif tol_type == "absolute":
            if abs(cur - base) > tol_value:
                diffs.append(
                    f"{field}.{key}: current={cur} baseline={base} tolerance=abs:{tol_value}"
                )
        else:
            diffs.append(f"{field}: unknown tolerance type {tol_type}")
    return diffs


def _compare_sets(field: str, baseline_list: List[Any], current_list: Any, mode: str) -> List[str]:
    if not isinstance(current_list, list):
        return [f"{field}: current missing or not list"]
    base_set = set(baseline_list)
    cur_set = set(current_list)
    if mode == "set_exact":
        if base_set != cur_set:
            return [f"{field}: expected {sorted(base_set)} got {sorted(cur_set)}"]
    elif mode == "set_contains":
        missing = base_set - cur_set
        if missing:
            return [f"{field}: missing entries {sorted(missing)} in current"]
    return []


def _compare_object(field: str, baseline_obj: Dict[str, Any], current_obj: Any) -> List[str]:
    if not isinstance(current_obj, dict):
        return [f"{field}: current missing or not object"]
    if baseline_obj != current_obj:
        return [f"{field}: expected {baseline_obj} got {current_obj}"]
    return []


def compare(baseline: Dict[str, Any], current: Dict[str, Any]) -> List[str]:
    diffs: List[str] = []
    checks = baseline.get("checks", {})
    policy = baseline.get("policy", {})
    default_tol_num = policy.get("default_numeric_tolerance", {"type": "absolute", "value": 0})
    default_dist_tol = policy.get("default_dist_tolerance", {"type": "percent_points", "value": 0})

    for field, rule in checks.items():
        mode = rule.get("mode", policy.get("default_mode", "exact"))
        optional = rule.get("optional", False)
        ok, current_val = _get_value(current, field)
        if not ok:
            if optional:
                continue
            diffs.append(f"{field}: missing in current")
            continue

        baseline_val = rule.get("baseline")
        if baseline_val is None:
            # No baseline yet; skip comparison so gate can warn.
            continue

        if mode in ("exact", "numeric"):
            tolerance = rule.get("tolerance", default_tol_num)
            diffs.extend(_compare_numeric(field, baseline_val, current_val, tolerance))
        elif mode == "distribution":
            tolerance = rule.get("tolerance", default_dist_tol)
            if not isinstance(current_val, dict):
                diffs.append(f"{field}: current missing or not dict")
                continue
            if not isinstance(baseline_val, dict):
                diffs.append(f"{field}: baseline missing or not dict")
                continue
            diffs.extend(_compare_distribution(field, baseline_val, current_val, tolerance))
        elif mode in ("set_exact", "set_contains"):
            diffs.extend(_compare_sets(field, baseline_val or [], current_val, mode))
        elif mode == "object_exact":
            diffs.extend(_compare_object(field, baseline_val or {}, current_val))
        else:
            diffs.append(f"{field}: unknown mode {mode}")
    return diffs
