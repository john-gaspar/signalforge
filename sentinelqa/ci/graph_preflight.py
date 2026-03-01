from __future__ import annotations

import argparse
import os
import re
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Sequence

from sentinelqa.graph.client import get_driver
from sentinelqa.gates import graph_gate

REPO_ROOT = Path(__file__).resolve().parents[2]

SECRET_PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private_key": re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY-----"),
    "slack_token": re.compile(r"xox[baprs]-"),
    "github_token": re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    "neo4j_auth_long": re.compile(r"NEO4J_AUTH=.+.{20,}"),
}


def _load_text(path: Path) -> str:
    return path.read_text()


def check_compose_text(compose_path: Path) -> List[str]:
    issues: List[str] = []
    txt = _load_text(compose_path)
    if "neo4j:" not in txt:
        issues.append("docker-compose.yml missing neo4j service")
    if "7687" not in txt:
        issues.append("neo4j service missing bolt port 7687")
    if "NEO4J_AUTH" not in txt or "neo4j/signalforge" not in txt:
        issues.append("NEO4J_AUTH dev creds not set to neo4j/signalforge")
    return issues


def check_workflow_text(workflow_path: Path) -> List[str]:
    issues: List[str] = []
    txt = _load_text(workflow_path)
    has_direct_graph_gate = "gates.graph_gate" in txt
    has_gate_runner = "sentinelqa.gates.runner" in txt
    if not (has_direct_graph_gate or has_gate_runner):
        issues.append("CI workflow missing graph gate step (direct or via gate runner)")
    if "postgres redis neo4j" not in txt:
        issues.append("CI workflow does not start neo4j with other services")
    neo4j_lines = [l for l in txt.splitlines() if "NEO4J" in l or "neo4j" in l]
    for line in neo4j_lines:
        if "localhost" in line:
            issues.append("CI workflow references localhost for Neo4j; should use service DNS")
            break
    return issues


def check_client_defaults(client_path: Path) -> List[str]:
    issues: List[str] = []
    txt = _load_text(client_path)
    if "bolt://neo4j:7687" not in txt:
        issues.append("Client default URI is not bolt://neo4j:7687")
    if "signalforge" not in txt or "neo4j" not in txt:
        issues.append("Client defaults do not use neo4j/signalforge credentials")
    return issues


def scan_secrets(paths: Sequence[Path]) -> List[str]:
    issues: List[str] = []
    for path in paths:
        try:
            for i, line in enumerate(path.read_text().splitlines(), start=1):
                for name, regex in SECRET_PATTERNS.items():
                    if regex.search(line):
                        issues.append(f"{path}:{i} potential {name}")
        except (UnicodeDecodeError, OSError):
            continue
    return issues


def _git_tracked_files() -> List[Path]:
    try:
        res = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
        return [REPO_ROOT / p for p in res.stdout.splitlines() if p]
    except Exception:
        # fallback: scan a minimal set
        return list(REPO_ROOT.glob("*.md"))


def run_static_checks() -> None:
    issues = []
    issues += check_compose_text(REPO_ROOT / "docker-compose.yml")
    issues += check_workflow_text(REPO_ROOT / ".github" / "workflows" / "ci.yml")
    issues += check_client_defaults(REPO_ROOT / "sentinelqa" / "graph" / "client.py")

    files_to_scan = _git_tracked_files()
    issues += scan_secrets(files_to_scan)

    if issues:
        print("[FAIL] graph preflight static")
        for issue in issues:
            print(f" - {issue}")
        sys.exit(1)
    print("[PASS] graph preflight static")


def _wait_neo4j(timeout: int = 180) -> None:
    driver = get_driver()
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            driver.verify_connectivity()
            driver.close()
            return
        except Exception as exc:
            last_err = exc
            time.sleep(1)
    driver.close()
    raise RuntimeError(f"Neo4j not ready after {timeout}s: {last_err}")


def _run_graph_gate_once() -> int:
    try:
        graph_gate.main()
        return 0
    except SystemExit as exc:
        return int(exc.code)


def run_runtime_checks() -> None:
    _wait_neo4j()
    first = _run_graph_gate_once()
    if first != 0:
        sys.exit("Graph gate failed on first run; see above.")
    second = _run_graph_gate_once()
    if second != 0:
        sys.exit(
            "Graph gate failed on second (idempotency) run; persistence must use MERGE or clear run-scoped graph before write."
        )
    print("[PASS] graph preflight runtime (idempotent)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Graph MVP preflight checks")
    parser.add_argument("--mode", choices=["static", "runtime"], required=True)
    args = parser.parse_args()

    if args.mode == "static":
        run_static_checks()
    else:
        run_runtime_checks()


if __name__ == "__main__":
    main()
