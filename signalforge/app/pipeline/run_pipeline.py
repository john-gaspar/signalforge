import json
import time
from pathlib import Path

from app.core.config import settings
from app.pipeline.stages_stub import load_fixture_events, cluster_stub, summarize_stub, alert_stub

def run_pipeline(run_id: str, config: dict) -> dict:
    """
    Deterministic pipeline runner:
    - reads fixtures
    - runs stub embed/cluster/summarize/alert
    - writes artifacts to artifacts/runs/<run_id>/
    """
    run_dir = Path(settings.artifacts_dir) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()

    events = load_fixture_events(config=config, run_dir=run_dir)
    clusters = cluster_stub(events=events, run_dir=run_dir)
    summary = summarize_stub(clusters=clusters, run_dir=run_dir)
    alert = alert_stub(summary=summary, run_dir=run_dir)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    metrics = {
        "run_id": run_id,
        "events": len(events),
        "clusters": len(clusters),
        "alerts_sent": 1 if alert.get("decision") == "sent" else 0,
        "latency_ms": elapsed_ms,
        "cost_usd_est": 0.0,  # fill later
    }

    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    return metrics