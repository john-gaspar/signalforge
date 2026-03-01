from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple


def _sha256_file(path: Path) -> Tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            if chunk:
                h.update(chunk)
                size += len(chunk)
    return h.hexdigest(), size


def _fingerprint(file_entries: List[Dict[str, Any]]) -> str:
    lines = [f"{entry['sha256']}  {entry['path']}\n" for entry in sorted(file_entries, key=lambda e: e["path"])]
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
    return h.hexdigest()


def write_manifest(run_dir: Path, run_id: str, required_files: List[str]) -> Path:
    files: List[Dict[str, Any]] = []
    for rel in sorted(required_files):
        path = run_dir / rel
        if not path.exists():
            raise FileNotFoundError(f"required artifact missing: {path}")
        sha, size = _sha256_file(path)
        files.append({"path": rel, "sha256": sha, "bytes": size})

    fingerprint = _fingerprint(files)
    manifest = {
        "version": 1,
        "run_id": run_id,
        "generated_at": None,  # left null to avoid clock skew; determinism via file hashes
        "required": sorted(required_files),
        "files": sorted(files, key=lambda e: e["path"]),
        "fingerprint_sha256": fingerprint,
    }
    out = run_dir / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return out


def validate_manifest(manifest_path: Path) -> List[str]:
    if not manifest_path.exists():
        return [f"manifest missing at {manifest_path}"]
    try:
        data = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        return [f"manifest invalid json: {exc}"]

    errors: List[str] = []
    required = data.get("required") or []
    files = data.get("files") or []

    # ensure required entries exist
    manifest_paths = {f.get("path") for f in files if isinstance(f, dict)}
    missing = [p for p in required if p not in manifest_paths]
    if missing:
        errors.append(f"required files not listed in manifest: {', '.join(sorted(missing))}")

    entries: List[Dict[str, Any]] = []
    for f in files:
        if not isinstance(f, dict):
            errors.append("manifest files entry is not an object")
            continue
        rel = f.get("path")
        sha_expected = f.get("sha256")
        size_expected = f.get("bytes")
        if not rel or not sha_expected or size_expected is None:
            errors.append(f"manifest entry missing fields: {f}")
            continue
        entries.append({"path": rel, "sha256": sha_expected, "bytes": size_expected})

    # recompute hashes
    for entry in entries:
        path = manifest_path.parent / entry["path"]
        if not path.exists():
            errors.append(f"{entry['path']} missing on disk")
            continue
        sha, size = _sha256_file(path)
        if sha != entry["sha256"]:
            errors.append(f"{entry['path']} sha mismatch (got {sha}, expected {entry['sha256']})")
        if size != entry["bytes"]:
            errors.append(f"{entry['path']} size mismatch (got {size}, expected {entry['bytes']})")

    # fingerprint check
    if not errors:
        computed_fp = _fingerprint(entries)
        if computed_fp != data.get("fingerprint_sha256"):
            errors.append("fingerprint_sha256 mismatch")

    return errors
