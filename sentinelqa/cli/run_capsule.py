from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACTS = REPO_ROOT / "artifacts"


def _ensure_repo_path(path: Path) -> Path:
    """Return an absolute path under REPO_ROOT or fail fast."""

    if not path.is_absolute():
        path = REPO_ROOT / path
    path = path.resolve()
    try:
        path.relative_to(REPO_ROOT)
    except ValueError:
        raise SystemExit(f"Path {path} is outside repository root {REPO_ROOT}") from None
    return path


def _resolve_artifacts_root(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    env_dir = os.getenv("ARTIFACTS_DIR")
    if env_dir:
        return Path(env_dir)
    return DEFAULT_ARTIFACTS


def _resolve_run_id(run_id_arg: str | None, artifacts_root: Path) -> Tuple[str, Path]:
    run_id = run_id_arg
    if not run_id:
        hint = artifacts_root / "latest_seed_run_id"
        run_id = hint.read_text().strip() if hint.exists() else None
    if not run_id:
        raise SystemExit("Missing run_id; provide --run-id or ensure artifacts/latest_seed_run_id exists.")
    run_dir = artifacts_root / "runs" / run_id
    if not run_dir.exists():
        raise SystemExit(f"Run artifacts not found at {run_dir}")
    return run_id, run_dir


def pack_capsule(run_id: str | None, artifacts_root: Path) -> Path:
    run_id, run_dir = _resolve_run_id(run_id, artifacts_root)
    capsule_path = run_dir / "capsule.zip"

    include_paths = [
        artifacts_root / "latest_seed_run_id",
        run_dir,
        REPO_ROOT / "sentinelqa" / "gates" / "thresholds.yaml",
        REPO_ROOT / "sentinelqa" / "contracts" / "contracts_index.json",
    ]

    with zipfile.ZipFile(capsule_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in include_paths:
            if not path.exists():
                continue
            if path.is_file():
                resolved = _ensure_repo_path(path)
                arcname = resolved.relative_to(REPO_ROOT)
                zf.write(resolved, arcname)
            else:
                for p in path.rglob("*"):
                    if p.is_file():
                        resolved = _ensure_repo_path(p)
                        arcname = resolved.relative_to(REPO_ROOT)
                        zf.write(resolved, arcname)

    print(f"[capsule] created {capsule_path}")
    return capsule_path


def _run_gate(cmd: List[str], cwd: Path) -> Tuple[bool, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()


def replay_capsule(capsule_path: Path) -> bool:
    if not capsule_path.exists():
        raise SystemExit(f"Capsule not found at {capsule_path}")

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        with zipfile.ZipFile(capsule_path, "r") as zf:
            zf.extractall(tmpdir)

        artifacts_root = tmpdir / "artifacts"
        if not artifacts_root.exists():
            raise SystemExit("Capsule missing artifacts directory")

        gates = [
            [sys.executable, "-m", "sentinelqa.gates.gate_manifest_integrity", "--artifacts-root", str(artifacts_root / "runs")],
            [sys.executable, "-m", "sentinelqa.gates.gate_artifact_schema", "--artifacts-dir", str(artifacts_root)],
            [sys.executable, "-m", "sentinelqa.gates.gate_evidence_diff", "--artifacts-dir", str(artifacts_root), "--mode", "report"],
        ]

        all_ok = True
        for cmd in gates:
            ok, out = _run_gate(cmd, REPO_ROOT)
            name = cmd[2]
            status = "OK" if ok else "FAIL"
            print(f"[capsule replay] {name}: {status}")
            if out:
                print(out)
            all_ok = all_ok and ok

        return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or replay a run capsule")
    sub = parser.add_subparsers(dest="command", required=True)

    pack_p = sub.add_parser("pack", help="Package run artifacts into capsule.zip")
    pack_p.add_argument("--run-id", help="Run id (default from artifacts/latest_seed_run_id)")
    pack_p.add_argument("--artifacts-dir", help="Artifacts root (default ./artifacts)")

    replay_p = sub.add_parser("replay", help="Replay checks against a capsule zip")
    replay_p.add_argument("capsule", help="Path to capsule.zip")

    args = parser.parse_args()

    if args.command == "pack":
        artifacts_root = _resolve_artifacts_root(args.artifacts_dir)
        pack_capsule(args.run_id, artifacts_root)
        sys.exit(0)

    if args.command == "replay":
        ok = replay_capsule(Path(args.capsule))
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
