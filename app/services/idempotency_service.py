# services/idempotency_service.py

import hashlib
import json


class IdempotencyService:
    async def get_existing_response(self, idempotency_key: str, payload):
        payload_hash = self._hash_payload(payload)

        # In real implementation:
        # existing = await repo.get(idempotency_key)
        # if existing and existing.payload_hash == payload_hash:
        #     return existing.response
        # if existing and existing.payload_hash != payload_hash:
        #     raise ConflictException()

        return None

    async def save_response(self, idempotency_key: str, payload, response: dict):
        payload_hash = self._hash_payload(payload)

        # In real implementation:
        # await repo.save(idempotency_key, payload_hash, response)

        return None

    def _hash_payload(self, payload) -> str:
        raw = payload.model_dump(mode="json")
        normalized = json.dumps(raw, sort_keys=True)
        return hashlib.sha256(normalized.encode()).hexdigest()
