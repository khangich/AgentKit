from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from agentkit import ui
from agentkit.server import create_app
from agentkit.state import store


def test_homepage_and_run(monkeypatch):
    app_path = Path(__file__).resolve().parent.parent / "agent_app.py"

    def fake_run_agent(inputs, files=None):
        run_id = store.create_run(inputs)
        runtime = ui.get_runtime()
        if runtime:
            runtime.record_run(run_id)
        store.append_event(run_id, "final", {"text": "ok"})
        store.finish_run(run_id, "succeeded")
        return run_id

    monkeypatch.setattr("agentkit.run_agent", fake_run_agent)
    monkeypatch.setattr("agentkit.runner.run_agent", fake_run_agent)

    client = TestClient(create_app(app_path))

    response = client.get("/")
    assert response.status_code == 200

    response = client.post(
        "/run",
        data={
            "task": "hello",
            "_trigger": "run-agent",
        },
    )
    assert response.status_code == 200
    run_id = response.json()["run_id"]

    run_meta = client.get(f"/run/{run_id}")
    assert run_meta.status_code == 200
    assert run_meta.json()["status"] == "succeeded"

    logs = client.get(f"/logs/{run_id}")
    assert logs.status_code == 200
    assert "final" in logs.text
