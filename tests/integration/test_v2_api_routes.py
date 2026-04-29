"""Integration tests for v2 API routes.

Tests cover:
  - 503 response when KAFKA_ENABLED=false (default for dev/test)
  - 200 + job_id response when Kafka publisher is injected via app.state
  - Job status endpoint (/api/v2/jobs/{job_id})

The Kafka publisher is always mocked — no real Kafka broker required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Payloads
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
def v2_client_no_kafka(app_client):
    """Client where Kafka is NOT configured (KAFKA_ENABLED=false, default)."""
    client, _ = app_client
    return client


@pytest.fixture()
def v2_client_with_kafka(app_client):
    """Client where a mock KafkaPublisher is injected into app.state."""
    client, app = app_client
    mock_publisher = AsyncMock()
    mock_publisher.publish = AsyncMock()
    app.state.kafka_publisher = mock_publisher
    yield client, mock_publisher
    app.state.kafka_publisher = None


# ---------------------------------------------------------------------------
# 503 when Kafka not configured
# ---------------------------------------------------------------------------


def test_v2_single_turn_503_when_kafka_disabled(v2_client_no_kafka):
    response = v2_client_no_kafka.post(
        "/api/v2/eval/ragas/single-turn", json=_SINGLE_TURN_PAYLOAD
    )
    assert response.status_code == 503
    assert "kafka" in response.json()["error"]["detail"].lower()


def test_v2_multi_turn_503_when_kafka_disabled(v2_client_no_kafka):
    response = v2_client_no_kafka.post(
        "/api/v2/eval/ragas/multi-turn", json=_MULTI_TURN_PAYLOAD
    )
    assert response.status_code == 503


# ---------------------------------------------------------------------------
# 200 + job_id when Kafka is available
# ---------------------------------------------------------------------------


def test_v2_single_turn_returns_job_id(v2_client_with_kafka):
    client, mock_publisher = v2_client_with_kafka

    with patch(
        "app.api.v2.eval_router.create_job", new=AsyncMock(return_value="v2-job-uuid")
    ):
        response = client.post(
            "/api/v2/eval/ragas/single-turn", json=_SINGLE_TURN_PAYLOAD
        )

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "v2-job-uuid"
    assert body["status"] == "pending"


def test_v2_single_turn_publishes_to_kafka(v2_client_with_kafka):
    client, mock_publisher = v2_client_with_kafka

    with patch(
        "app.api.v2.eval_router.create_job", new=AsyncMock(return_value="v2-jid")
    ):
        client.post("/api/v2/eval/ragas/single-turn", json=_SINGLE_TURN_PAYLOAD)

    mock_publisher.publish.assert_called_once()
    topic, payload = mock_publisher.publish.call_args.args
    assert topic == "eval.requested"
    assert payload["job_id"] == "v2-jid"
    assert payload["eval_type"] == "single_turn"
    assert payload["eval_input"]["user_input"] == "What is RAG?"


def test_v2_single_turn_kafka_payload_has_event_fields(v2_client_with_kafka):
    client, mock_publisher = v2_client_with_kafka

    with patch("app.api.v2.eval_router.create_job", new=AsyncMock(return_value="j")):
        client.post("/api/v2/eval/ragas/single-turn", json=_SINGLE_TURN_PAYLOAD)

    _, payload = mock_publisher.publish.call_args.args
    assert "event_id" in payload
    assert "occurred_at" in payload


def test_v2_multi_turn_returns_job_id(v2_client_with_kafka):
    client, mock_publisher = v2_client_with_kafka

    with patch(
        "app.api.v2.eval_router.create_job", new=AsyncMock(return_value="v2-multi-uuid")
    ):
        response = client.post(
            "/api/v2/eval/ragas/multi-turn", json=_MULTI_TURN_PAYLOAD
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "v2-multi-uuid"
    mock_publisher.publish.assert_called_once()


def test_v2_multi_turn_kafka_payload_has_correct_eval_type(v2_client_with_kafka):
    client, mock_publisher = v2_client_with_kafka

    with patch("app.api.v2.eval_router.create_job", new=AsyncMock(return_value="j")):
        client.post("/api/v2/eval/ragas/multi-turn", json=_MULTI_TURN_PAYLOAD)

    _, payload = mock_publisher.publish.call_args.args
    assert payload["eval_type"] == "multi_turn"
    assert "messages" in payload["eval_input"]


def test_v2_missing_required_field_returns_422(v2_client_with_kafka):
    client, _ = v2_client_with_kafka
    response = client.post(
        "/api/v2/eval/ragas/single-turn",
        json={"user_input": "Q"},  # missing required fields
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Job status endpoint
# ---------------------------------------------------------------------------


def test_v2_get_job_returns_status(v2_client_no_kafka):
    stored_job = {
        "job_id": "v2-job-abc",
        "job_type": "ragas_single_turn",
        "status": "running",
        "result": None,
        "error": None,
        "idempotency_key": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "started_at": "2026-01-01T00:00:01+00:00",
        "completed_at": None,
    }

    with patch(
        "app.api.v2.jobs_router.get_job", new=AsyncMock(return_value=stored_job)
    ):
        response = v2_client_no_kafka.get("/api/v2/jobs/v2-job-abc")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "v2-job-abc"
    assert body["status"] == "running"


def test_v2_get_job_returns_404_when_not_found(v2_client_no_kafka):
    with patch("app.api.v2.jobs_router.get_job", new=AsyncMock(return_value=None)):
        response = v2_client_no_kafka.get("/api/v2/jobs/not-a-real-job")

    assert response.status_code == 404
