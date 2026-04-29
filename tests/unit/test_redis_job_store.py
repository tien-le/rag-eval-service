"""Unit tests for app/infra/jobs/redis_job_store.py.

All tests use a mocked Redis client — no real Redis required.
"""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch


def _make_redis_mock(stored: dict | None = None) -> AsyncMock:
    """Return an AsyncMock that behaves like a redis.asyncio.Redis client."""
    r = AsyncMock()
    r.get.return_value = json.dumps(stored) if stored is not None else None
    r.set.return_value = True
    return r


class CreateJobTests(unittest.TestCase):
    def test_returns_uuid_string(self) -> None:
        from app.infra.jobs.redis_job_store import create_job

        mock_r = _make_redis_mock()
        with patch("app.infra.jobs.redis_job_store.get_redis", AsyncMock(return_value=mock_r)):
            job_id = asyncio.run(create_job("ragas_single_turn"))

        self.assertIsInstance(job_id, str)
        self.assertEqual(len(job_id), 36)  # UUID4 canonical form

    def test_stores_pending_status(self) -> None:
        from app.infra.jobs.redis_job_store import create_job

        mock_r = _make_redis_mock()
        with patch("app.infra.jobs.redis_job_store.get_redis", AsyncMock(return_value=mock_r)):
            asyncio.run(create_job("ragas_single_turn"))

        mock_r.set.assert_called_once()
        stored = json.loads(mock_r.set.call_args.args[1])
        self.assertEqual(stored["status"], "pending")
        self.assertEqual(stored["job_type"], "ragas_single_turn")
        self.assertIsNone(stored["result"])
        self.assertIsNone(stored["error"])

    def test_stores_idempotency_key_when_provided(self) -> None:
        from app.infra.jobs.redis_job_store import create_job

        mock_r = _make_redis_mock()
        with patch("app.infra.jobs.redis_job_store.get_redis", AsyncMock(return_value=mock_r)):
            asyncio.run(create_job("ragas_single_turn", idempotency_key="idem-xyz"))

        stored = json.loads(mock_r.set.call_args.args[1])
        self.assertEqual(stored["idempotency_key"], "idem-xyz")

    def test_set_is_called_with_ttl(self) -> None:
        from app.infra.jobs.redis_job_store import JOB_TTL_SECONDS, create_job

        mock_r = _make_redis_mock()
        with patch("app.infra.jobs.redis_job_store.get_redis", AsyncMock(return_value=mock_r)):
            asyncio.run(create_job("ragas_single_turn"))

        kwargs = mock_r.set.call_args.kwargs
        self.assertEqual(kwargs["ex"], JOB_TTL_SECONDS)


class GetJobTests(unittest.TestCase):
    def test_returns_none_for_missing_key(self) -> None:
        from app.infra.jobs.redis_job_store import get_job

        mock_r = _make_redis_mock(stored=None)
        with patch("app.infra.jobs.redis_job_store.get_redis", AsyncMock(return_value=mock_r)):
            result = asyncio.run(get_job("nonexistent-id"))

        self.assertIsNone(result)

    def test_returns_dict_for_existing_key(self) -> None:
        from app.infra.jobs.redis_job_store import get_job

        stored = {
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
        mock_r = _make_redis_mock(stored=stored)
        with patch("app.infra.jobs.redis_job_store.get_redis", AsyncMock(return_value=mock_r)):
            result = asyncio.run(get_job("abc-123"))

        self.assertIsNotNone(result)
        self.assertEqual(result["job_id"], "abc-123")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"]["scores"]["faithfulness"], 0.9)


class UpdateJobTests(unittest.TestCase):
    def _existing_job(self) -> dict:
        return {
            "job_id": "abc-123",
            "job_type": "ragas_single_turn",
            "status": "pending",
            "result": None,
            "error": None,
            "idempotency_key": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "started_at": None,
            "completed_at": None,
        }

    def test_patches_status_field(self) -> None:
        from app.infra.jobs.redis_job_store import update_job

        mock_r = _make_redis_mock(stored=self._existing_job())
        with patch("app.infra.jobs.redis_job_store.get_redis", AsyncMock(return_value=mock_r)):
            asyncio.run(update_job("abc-123", status="running", started_at="2026-01-01T00:00:01+00:00"))

        updated = json.loads(mock_r.set.call_args.args[1])
        self.assertEqual(updated["status"], "running")
        self.assertEqual(updated["started_at"], "2026-01-01T00:00:01+00:00")
        self.assertIsNone(updated["result"])  # unchanged field preserved

    def test_is_noop_when_job_does_not_exist(self) -> None:
        from app.infra.jobs.redis_job_store import update_job

        mock_r = _make_redis_mock(stored=None)
        with patch("app.infra.jobs.redis_job_store.get_redis", AsyncMock(return_value=mock_r)):
            asyncio.run(update_job("missing-id", status="running"))  # must not raise

        mock_r.set.assert_not_called()

    def test_reset_ttl_on_update(self) -> None:
        from app.infra.jobs.redis_job_store import JOB_TTL_SECONDS, update_job

        mock_r = _make_redis_mock(stored=self._existing_job())
        with patch("app.infra.jobs.redis_job_store.get_redis", AsyncMock(return_value=mock_r)):
            asyncio.run(update_job("abc-123", status="completed"))

        kwargs = mock_r.set.call_args.kwargs
        self.assertEqual(kwargs["ex"], JOB_TTL_SECONDS)


if __name__ == "__main__":
    unittest.main()
