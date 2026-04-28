from typing import Protocol


class RetrievalQualityEvaluator(Protocol):
    async def evaluate(
        self,
        question: str,
        contexts: list[str],
        reference_answer: str | None,
        metrics: list[str],
    ) -> dict[str, float | None]:
        ...
