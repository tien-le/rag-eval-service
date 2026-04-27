# services/cost_service.py

from app.core.enums import MetricName


class CostService:
    MODEL_PRICING = {
        "gpt-4o-mini": {
            "input_per_1m": 0.15,
            "output_per_1m": 0.60,
        }
    }

    METRIC_TOKEN_ESTIMATE = {
        MetricName.FAITHFULNESS: {
            "input": 1200,
            "output": 150,
        },
        MetricName.ANSWER_RELEVANCY: {
            "input": 1000,
            "output": 150,
        },
        MetricName.CONTEXT_PRECISION: {
            "input": 900,
            "output": 100,
        },
        MetricName.CONTEXT_RECALL: {
            "input": 1200,
            "output": 150,
        },
    }

    def estimate(
        self,
        item_count: int,
        metrics: list[MetricName],
        judge_model: str,
    ) -> float:
        pricing = self.MODEL_PRICING[judge_model]

        input_tokens = 0
        output_tokens = 0

        for metric in metrics:
            input_tokens += item_count * self.METRIC_TOKEN_ESTIMATE[metric]["input"]
            output_tokens += item_count * self.METRIC_TOKEN_ESTIMATE[metric]["output"]

        return (
            input_tokens / 1_000_000 * pricing["input_per_1m"]
            + output_tokens / 1_000_000 * pricing["output_per_1m"]
        )
