from app.domain.evaluation.ports import RetrievalQualityEvaluator


class EvaluationService:
    def __init__(self, evaluator: RetrievalQualityEvaluator) -> None:
        self.evaluator = evaluator

    async def evaluate_retrieval_quality(
        self,
        question: str,
        contexts: list[str],
        reference_answer: str | None,
        metrics: list[str],
    ) -> dict[str, float | None]:
        if not question.strip():
            raise ValueError("question must not be empty")

        if not contexts:
            raise ValueError("contexts must not be empty")

        return await self.evaluator.evaluate(
            question=question,
            contexts=contexts,
            reference_answer=reference_answer,
            metrics=metrics,
        )
