"""Ragas evaluator adapter for the application layer."""

from collections.abc import Sequence

from app.domain.evaluation.entities import EvaluationInput, EvaluationResult, EvaluationScore
from app.domain.evaluation.ports import EvaluatorPort


class RagasEvaluator(EvaluatorPort):
    """Evaluate RAG answers using Ragas metrics."""

    _supported_metric_names = {
        "answer_relevancy",
        "answer_correctness",
        "answer_similarity",
    }

    def __init__(self, llm: object, embeddings: object, run_config: object | None = None) -> None:
        self._llm = llm
        self._embeddings = embeddings
        self._run_config = run_config

    def evaluate(self, evaluation_input: EvaluationInput, metrics: Sequence[str]) -> EvaluationResult:
        from ragas import evaluate
        from ragas.run_config import RunConfig

        selected_metrics = [self._resolve_metric(metric_name) for metric_name in metrics]
        dataset = self._build_dataset(evaluation_input)
        run_config = self._run_config or RunConfig(
            timeout=120,
            max_retries=3,
            max_wait=60,
            log_tenacity=False,
        )
        result = evaluate(
            dataset=dataset,
            metrics=selected_metrics,
            llm=self._llm,
            embeddings=self._embeddings,
            run_config=run_config,
            raise_exceptions=True,
            callbacks=None,
        )
        dataframe = result.to_pandas()
        first_row = dataframe.iloc[0].to_dict()
        scores = [
            EvaluationScore(metric_name=metric_name, value=float(first_row[metric_name]))
            for metric_name in metrics
            if metric_name in first_row
        ]
        return EvaluationResult(scores=scores, raw_payload=first_row)

    def _build_dataset(self, evaluation_input: EvaluationInput):
        from datasets import Dataset

        return Dataset.from_dict(
            {
                "question": [evaluation_input.question],
                "answer": [evaluation_input.answer],
                "contexts": [evaluation_input.contexts],
                "ground_truth": [evaluation_input.ground_truth],
            }
        )

    def _resolve_metric(self, metric_name: str):
        if metric_name not in self._supported_metric_names:
            available = ", ".join(sorted(self._supported_metric_names))
            raise ValueError(f"Unsupported metric '{metric_name}'. Available metrics: {available}")

        from ragas.metrics import answer_correctness, answer_relevancy, answer_similarity

        metric_registry = {
            "answer_relevancy": answer_relevancy,
            "answer_correctness": answer_correctness,
            "answer_similarity": answer_similarity,
        }
        return metric_registry[metric_name]
