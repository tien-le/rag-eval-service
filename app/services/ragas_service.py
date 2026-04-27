# services/ragas_service.py

import asyncio
from datasets import Dataset
from ragas import evaluate

from schemas.evaluation import EvaluationItemInput
from core.enums import MetricName


class RagasService:
    async def evaluate_single(
        self,
        run_id: str,
        item: EvaluationItemInput,
        metrics: list[MetricName],
        judge_model: str,
    ):
        try:
            return await asyncio.wait_for(
                self._evaluate_single_sync(item, metrics),
                timeout=90,
            )
        except TimeoutError:
            return {
                "query_id": item.query_id,
                "status": "timeout",
                "scores": {},
                "error": "Evaluation timed out",
            }
        except Exception as exc:
            return {
                "query_id": item.query_id,
                "status": "failed",
                "scores": {},
                "error": str(exc),
            }

    async def _evaluate_single_sync(
        self,
        item: EvaluationItemInput,
        metrics: list[MetricName],
    ):
        dataset = Dataset.from_list(
            [
                {
                    "question": item.question,
                    "answer": item.answer,
                    "contexts": [ctx.text for ctx in item.contexts],
                    "ground_truth": item.ground_truth,
                }
            ]
        )

        ragas_metrics = self._map_metrics(metrics)

        result = evaluate(
            dataset=dataset,
            metrics=ragas_metrics,
            raise_exceptions=False,
        )

        row = result.to_pandas().iloc[0].to_dict()

        return {
            "query_id": item.query_id,
            "status": "completed",
            "scores": {metric.value: row.get(metric.value) for metric in metrics},
        }

    def _map_metrics(self, metrics: list[MetricName]):
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )

        registry = {
            MetricName.FAITHFULNESS: faithfulness,
            MetricName.ANSWER_RELEVANCY: answer_relevancy,
            MetricName.CONTEXT_PRECISION: context_precision,
            MetricName.CONTEXT_RECALL: context_recall,
        }

        return [registry[metric] for metric in metrics]
