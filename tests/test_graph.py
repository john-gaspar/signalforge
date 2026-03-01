import json
from pathlib import Path

from sentinelqa.graph import persist, invariants


class StubRecord:
    def __init__(self, data):
        self.data = data

    def __getitem__(self, idx):
        if isinstance(idx, int):
            return list(self.data.values())[idx]
        return self.data[idx]

    def get(self, key, default=None):
        return self.data.get(key, default)


class StubResult:
    def __init__(self, data_list):
        self.data_list = data_list

    def single(self):
        return StubRecord(self.data_list[0]) if self.data_list else None

    def __iter__(self):
        for data in self.data_list:
            yield StubRecord(data)


class StubSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def run(self, query, **params):
        self.calls.append(query.strip())
        data = self.responses.pop(0) if self.responses else []
        return StubResult(data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class StubDriver:
    def __init__(self, responses):
        self.responses = responses
        self.last_session: StubSession | None = None

    def session(self):
        self.last_session = StubSession(self.responses)
        return self.last_session

    def close(self):
        pass


def test_load_artifacts_projects_stable_fields(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "events.json").write_text(
        json.dumps(
            [
                {"event_id": "e1", "event_type": "incident", "severity": "high", "source": "fixture", "extra": "x"},
                {"event_id": "e2", "normalized": {"event_type": "ticket"}, "source": "fixture"},
            ]
        )
    )
    (run_dir / "clusters.json").write_text(json.dumps([{"cluster_id": "c1", "members": ["e1", "e2"]}]))

    artifacts = persist.load_artifacts(run_dir)

    assert artifacts["events"] == [
        {"event_id": "e1", "event_type": "incident", "severity": "high", "source": "fixture"},
        {"event_id": "e2", "event_type": "ticket", "source": "fixture"},
    ]
    assert artifacts["clusters"] == [{"cluster_id": "c1", "member_event_ids": ["e1", "e2"]}]


def test_persist_emits_merge_queries():
    artifacts = {
        "events": [{"event_id": "e1", "event_type": "incident"}],
        "clusters": [{"cluster_id": "c1", "member_event_ids": ["e1"]}],
        "alerts": [],
    }
    driver = StubDriver(responses=[])

    persist.persist_to_graph("run123", artifacts, driver)

    queries = driver.last_session.calls
    assert any("MERGE (r:Run" in q for q in queries)
    assert any("MERGE (ev:Event" in q for q in queries)
    assert any("MERGE (cl:Cluster" in q for q in queries)


def test_invariants_detect_no_issues():
    # responses in the order queries are executed in check_invariants
    responses = [
        [{"count": 1}],  # run count
        [{"count": 2}],  # HAS_EVENT count
        [{"ids": ["e1", "e2"]}],  # event ids
        [{"count": 1}],  # cluster count
        [{"ids": ["c1"]}],  # cluster ids
        [{"count": 0}],  # invalid cluster->event edges
        [{"edges": ["c1::e1", "c1::e2"]}],  # cluster edges
    ]
    driver = StubDriver(responses=responses)
    expected = {
        "events": {"count": 2, "ids": {"e1", "e2"}},
        "clusters": {"count": 1, "ids": {"c1"}, "edges": [("c1", "e1"), ("c1", "e2")]},
    }

    issues = invariants.check_invariants(driver, "run123", expected)

    assert issues == []
