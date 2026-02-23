import hashlib
import json

def stable_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def make_run_id(idempotency_key: str) -> str:
    return sha256_hex(idempotency_key)[:32]

def make_event_id(source: str, normalized_payload: dict) -> str:
    return sha256_hex(f"{source}:{stable_json(normalized_payload)}")[:32]