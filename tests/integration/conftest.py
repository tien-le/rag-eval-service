"""Shared fixtures for integration tests.

Key design: every fixture that touches infra (Redis, Celery, Kafka) is mocked
so these tests run without any external services.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fake evaluation service — replaces Ollama-backed EvaluationService
# ---------------------------------------------------------------------------


class FakeEvaluationService:
    def metric_catalog(self) -> list[dict]:
        return [{"name": "faithfulness", "category": "generation", "description": "test"}]

    def evaluate_classification(
        self, *, actual: list[str], predicted: list[str], positive_label: str
    ) -> dict:
        return {
            "summary": {"samples": len(actual), "accuracy": 1.0},
            "actual_distribution": {positive_label: len(actual)},
            "predicted_distribution": {positive_label: len(predicted)},
        }

    async def evaluate_ragas_single_turn(self, **kwargs: Any) -> dict:
        return {"scores": {"faithfulness": 0.92}}

    async def evaluate_ragas_multi_turn(self, **kwargs: Any) -> dict:
        return {"scores": {"topic_adherence": 0.88}}


# ---------------------------------------------------------------------------
# App client fixture — mocks Redis pool init so lifespan succeeds
# ---------------------------------------------------------------------------


@pytest.fixture()
def app_client():
    """TestClient with mocked Redis pool lifecycle.

    Kafka is disabled by default (KAFKA_ENABLED=false), so no Kafka mocking needed.
    """
    with (
        patch("app.infra.cache.redis_client.init_redis_pool", new_callable=AsyncMock),
        patch("app.infra.cache.redis_client.close_redis_pool", new_callable=AsyncMock),
    ):
        from app.main import app

        with TestClient(app, raise_server_exceptions=True) as client:
            yield client, app
