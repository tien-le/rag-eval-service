"""Integration tests for v1 API routes.

Tests cover:
  - Sync eval endpoints (/api/v1/eval/*)
  - Async eval endpoints (/api/v1/eval/*/async) — Celery dispatch mocked
  - Job status endpoint (/api/v1/jobs/{job_id})

No real Redis, Celery, or Ollama connections are made.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.integration.conftest import FakeEvaluationService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SINGLE_TURN_PAYLOAD = {
    "user_input": "What is RAG?",
    "response": "RAG combines retrieval and generation.",
    "retrieved_contexts": ["RAG is a technique that retrieves context."],
    "metric_names": ["faithfulness"],
}

_MULTI_TURN_PAYLOAD = {
    "messages": [
        {"role": "human", "content": "What is RAG?"},
        {"role": "ai", "content": "RAG stands for Retrieval-Augmented Generation."},
    ],
    "metric_names": ["topic_adherence"],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def v1_client(app_client):
    """TestClient with v1 eval service dependency overridden."""
    client, app = app_client
    from app.api.v1.eval_router import _get_service

    app.dependency_overrides[_get_service] = lambda: FakeEvaluationService()
    yield client
    app.dependency_overrides.pop(_get_service, None)


# ---------------------------------------------------------------------------
# Sync endpoints
# ---------------------------------------------------------------------------


def test_v1_get_metrics_returns_200(v1_client):
    response = v1_client.get("/api/v1/eval/metrics")
    assert response.status_code == 200
    body = response.json()
    assert "metrics" in body
    assert isinstance(body["metrics"], list)


def test_v1_get_metrics_contains_faithfulness(v1_client):
    response = v1_client.get("/api/v1/eval/metrics")
    names = [m["name"] for m in response.json()["metrics"]]
    assert "faithfulness" in names


def test_v1_classification_returns_summary(v1_client):
    response = v1_client.post(
        "/api/v1/eval/classification",
        json={
            "actual": ["positive", "negative"],
            "predicted": ["positive", "negative"],
            "positive_label": "positive",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
    assert body["summary"]["accuracy"] == 1.0


def test_v1_single_turn_sync_returns_scores(v1_client):
    response = v1_client.post("/api/v1/eval/ragas/single-turn", json=_SINGLE_TURN_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert "scores" in body
    assert "faithfulness" in body["scores"]
    assert isinstance(body["scores"]["faithfulness"], float)


def test_v1_multi_turn_sync_returns_scores(v1_client):
    response = v1_client.post("/api/v1/eval/ragas/multi-turn", json=_MULTI_TURN_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert "scores" in body
    assert "topic_adherence" in body["scores"]


def test_v1_single_turn_missing_required_field_returns_422(v1_client):
    response = v1_client.post(
        "/api/v1/eval/ragas/single-turn",
        json={"user_input": "Q"},  # missing response, retrieved_contexts, metric_names
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Async endpoints (Celery dispatch mocked)
# ---------------------------------------------------------------------------


def test_v1_single_turn_async_returns_job_id(app_client):
    client, app = app_client

    with (
        patch(
            "app.api.v1.eval_router.create_job",
            new=AsyncMock(return_value="test-job-uuid"),
        ),
        patch("app.api.v1.eval_router.ragas_single_turn_task") as mock_task,
    ):
        mock_task.delay.return_value = MagicMock()
        response = client.post("/api/v1/eval/ragas/single-turn/async", json=_SINGLE_TURN_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "test-job-uuid"
    assert body["status"] == "pending"
    mock_task.delay.assert_called_once()


def test_v1_multi_turn_async_returns_job_id(app_client):
    client, app = app_client

    with (
        patch(
            "app.api.v1.eval_router.create_job",
            new=AsyncMock(return_value="multi-job-uuid"),
        ),
        patch("app.api.v1.eval_router.ragas_multi_turn_task") as mock_task,
    ):
        mock_task.delay.return_value = MagicMock()
        response = client.post("/api/v1/eval/ragas/multi-turn/async", json=_MULTI_TURN_PAYLOAD)

    assert response.status_code == 200
    assert response.json()["job_id"] == "multi-job-uuid"
    mock_task.delay.assert_called_once()


def test_v1_single_turn_async_celery_receives_correct_payload(app_client):
    client, app = app_client
    captured_payloads: list = []

    def _capture(job_id, payload):
        captured_payloads.append(payload)
        return MagicMock()

    with (
        patch("app.api.v1.eval_router.create_job", new=AsyncMock(return_value="jid")),
        patch("app.api.v1.eval_router.ragas_single_turn_task") as mock_task,
    ):
        mock_task.delay.side_effect = _capture
        client.post("/api/v1/eval/ragas/single-turn/async", json=_SINGLE_TURN_PAYLOAD)

    assert len(captured_payloads) == 1
    payload = captured_payloads[0]
    assert payload["user_input"] == "What is RAG?"
    assert "faithfulness" in payload["metric_names"]


# ---------------------------------------------------------------------------
# Job status endpoint
# ---------------------------------------------------------------------------


def test_v1_get_job_returns_status(app_client):
    client, _ = app_client
    stored_job = {
        "job_id": "abc-123",
        "job_type": "ragas_single_turn",
        "status": "completed",
        "result": {"scores": {"faithfulness": 0.9}},
        "error": None,
        "idempotency_key": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "started_at": "2026-01-01T00:00:01+00:00",
        "completed_at": "2026-01-01T00:00:05+00:00",
    }

    with patch(
        "app.api.v1.jobs_router.get_job", new=AsyncMock(return_value=stored_job)
    ):
        response = client.get("/api/v1/jobs/abc-123")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "abc-123"
    assert body["status"] == "completed"
    assert body["result"]["scores"]["faithfulness"] == 0.9


def test_v1_get_job_returns_404_when_not_found(app_client):
    client, _ = app_client

    with patch("app.api.v1.jobs_router.get_job", new=AsyncMock(return_value=None)):
        response = client.get("/api/v1/jobs/nonexistent-job")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_v1_get_job_pending_has_null_result(app_client):
    client, _ = app_client
    pending_job = {
        "job_id": "pending-job",
        "job_type": "ragas_single_turn",
        "status": "pending",
        "result": None,
        "error": None,
        "idempotency_key": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "started_at": None,
        "completed_at": None,
    }

    with patch("app.api.v1.jobs_router.get_job", new=AsyncMock(return_value=pending_job)):
        response = client.get("/api/v1/jobs/pending-job")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["result"] is None
