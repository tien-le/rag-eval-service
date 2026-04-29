"""Contract tests for app/schemas/job.py.

Verifies that AsyncJobResponse and JobStatusResponse honour their public
field contracts so that API clients relying on these schemas are protected
against accidental renames or type changes.
"""

import pytest
from pydantic import ValidationError


class TestAsyncJobResponse:
    def test_required_job_id(self):
        from app.schemas.job import AsyncJobResponse

        r = AsyncJobResponse(job_id="abc-123")
        assert r.job_id == "abc-123"

    def test_default_status_is_pending(self):
        from app.schemas.job import AsyncJobResponse

        r = AsyncJobResponse(job_id="x")
        assert r.status == "pending"

    def test_message_field_present(self):
        from app.schemas.job import AsyncJobResponse

        r = AsyncJobResponse(job_id="x")
        assert isinstance(r.message, str)
        assert len(r.message) > 0

    def test_model_dump_contains_required_keys(self):
        from app.schemas.job import AsyncJobResponse

        d = AsyncJobResponse(job_id="abc").model_dump()
        assert "job_id" in d
        assert "status" in d
        assert "message" in d

    def test_missing_job_id_raises_validation_error(self):
        from app.schemas.job import AsyncJobResponse

        with pytest.raises(ValidationError):
            AsyncJobResponse()  # job_id required


class TestJobStatusResponse:
    def _make(self, **overrides) -> object:
        from app.schemas.job import JobStatusResponse

        defaults = {
            "job_id": "job-1",
            "job_type": "ragas_single_turn",
            "status": "pending",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        return JobStatusResponse(**{**defaults, **overrides})

    def test_required_fields_present(self):
        r = self._make()
        assert r.job_id == "job-1"
        assert r.job_type == "ragas_single_turn"
        assert r.status == "pending"
        assert r.created_at == "2026-01-01T00:00:00+00:00"

    def test_optional_fields_default_to_none(self):
        r = self._make()
        assert r.result is None
        assert r.error is None
        assert r.started_at is None
        assert r.completed_at is None
        assert r.idempotency_key is None

    def test_all_valid_statuses_accepted(self):
        from app.schemas.job import JobStatusResponse

        for status in ("pending", "running", "completed", "failed"):
            r = self._make(status=status)
            assert r.status == status

    def test_invalid_status_raises_validation_error(self):
        from app.schemas.job import JobStatusResponse

        with pytest.raises(ValidationError):
            self._make(status="unknown_state")

    def test_result_field_accepts_nested_dict(self):
        r = self._make(
            status="completed",
            result={"scores": {"faithfulness": 0.95}},
        )
        assert r.result["scores"]["faithfulness"] == 0.95

    def test_model_dump_includes_all_fields(self):
        from app.schemas.job import JobStatusResponse

        r = self._make()
        d = r.model_dump()
        required_keys = {
            "job_id", "job_type", "status", "result",
            "error", "idempotency_key", "created_at",
            "started_at", "completed_at",
        }
        assert required_keys <= set(d.keys())

    def test_missing_required_field_raises_validation_error(self):
        from app.schemas.job import JobStatusResponse

        with pytest.raises(ValidationError):
            JobStatusResponse(job_id="x")  # missing job_type, status, created_at
