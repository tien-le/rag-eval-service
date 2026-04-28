import math

from ragas import aevaluate

from app.infra.ragas.dataset_adapter import build_retrieval_dataset
from app.infra.ragas.metric_factory import build_retrieval_metrics


class RagasRetrievalQualityEvaluator:
    async def evaluate(
        self,
        question: str,
        contexts: list[str],
        reference_answer: str | None,
        metrics: list[str],
    ) -> dict[str, float | None]:
        dataset = build_retrieval_dataset(
            question=question,
            contexts=contexts,
            reference_answer=reference_answer,
        )

        ragas_metrics = build_retrieval_metrics(metrics)

        result = await aevaluate(
            dataset=dataset,
            metrics=ragas_metrics,
            raise_exceptions=False,
            show_progress=False,
        )
        row = result.to_pandas().iloc[0]
        scores: dict[str, float | None] = {}
        for metric_name in metrics:
            value = row.get(metric_name)

            if value is None:
                scores[metric_name] = None
            elif isinstance(value, float) and math.isnan(value):
                scores[metric_name] = None
            else:
                scores[metric_name] = float(value)
        return scores
