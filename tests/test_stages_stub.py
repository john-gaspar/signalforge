import json
from pathlib import Path

from app.pipeline import stages_stub


def make_fixture(tmp_path: Path, name: str = "ticket1.json") -> Path:
    data = {
        "customer": "Acme",
        "subject": "Login broken",
        "body": "Users cannot log in",
        "created_at": "2026-02-24T00:00:00Z",
    }
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_load_fixture_events_writes_events_json(tmp_path):
    fixtures_dir = tmp_path / "fixtures" / "tickets"
    fixtures_dir.mkdir(parents=True)
    make_fixture(fixtures_dir)

    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    events = stages_stub.load_fixture_events({"fixtures_dir": str(fixtures_dir)}, run_dir)

    events_file = run_dir / "events.json"
    assert events_file.exists()
    assert len(events) == 1
    loaded = json.loads(events_file.read_text())
    assert loaded[0]["source"] == "fixture"
    assert loaded[0]["normalized"]["subject"] == "Login broken"


def test_cluster_and_summary_and_alert(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)
    events = [
        {
            "event_id": "e1",
            "source": "fixture",
            "normalized": {"subject": "Login broken"},
            "raw_file": "x.json",
        }
    ]

    clusters = stages_stub.cluster_stub(events, run_dir)
    assert (run_dir / "clusters.json").exists()
    assert len(clusters) == 1

    summary = stages_stub.summarize_stub(clusters, run_dir)
    assert summary["cluster_count"] == 1
    assert (run_dir / "summary.json").exists()

    alert = stages_stub.alert_stub(summary, run_dir)
    assert alert["decision"] == "sent"
    assert (run_dir / "alert.json").exists()
