"""Integration tests for v1 and v2 API routes.

These tests use FastAPI's TestClient with mocked infra dependencies
(Redis, Celery, Kafka) so no external services are required.
"""
