from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
BASELINE_DIR = Path(__file__).resolve().parents[1] / "schemas_baseline" / "v1"


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _type_set(t: Any) -> set:
    if isinstance(t, list):
        return set(t)
    return {t}


def compare_schema(current: Dict[str, Any], baseline: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    # required removal
    cur_req = set(current.get("required", []))
    base_req = set(baseline.get("required", []))
    removed = base_req - cur_req
    if removed:
        errors.append(f"required removed: {', '.join(sorted(removed))}")

    # properties type changes for required props
    cur_props = current.get("properties", {})
    base_props = baseline.get("properties", {})
    for prop in base_req:
        if prop not in base_props or prop not in cur_props:
            continue
        base_type = _type_set(base_props[prop].get("type"))
        cur_type = _type_set(cur_props[prop].get("type"))
        if base_type != cur_type:
            errors.append(f"type change for required '{prop}': {base_type} -> {cur_type}")
        # enum tightening
        base_enum = base_props[prop].get("enum")
        cur_enum = cur_props[prop].get("enum")
        if base_enum and cur_enum:
            if set(cur_enum) < set(base_enum):
                errors.append(f"enum narrowed for '{prop}'")

    # additionalProperties tightened at top level
    base_ap = baseline.get("additionalProperties", True)
    cur_ap = current.get("additionalProperties", True)
    if (base_ap is True or base_ap is None) and cur_ap is False:
        errors.append("additionalProperties tightened to false at top level")

    return errors


def main() -> None:
    schema_paths = list(SCHEMA_DIR.glob("*_v1.json"))
    issues: List[str] = []
    for cur_path in sorted(schema_paths):
        base_path = BASELINE_DIR / cur_path.name
        if not base_path.exists():
            continue  # new schema is non-breaking
        cur = _load(cur_path)
        base = _load(base_path)
        errs = compare_schema(cur, base)
        if errs:
            issues.append(f"{cur_path.name}: " + "; ".join(errs))

    if issues:
        print("[FAIL] schema compatibility gate")
        for issue in issues:
            print(f" - {issue}")
        sys.exit(1)

    print("[PASS] schema compatibility gate")
    sys.exit(0)


if __name__ == "__main__":
    main()
