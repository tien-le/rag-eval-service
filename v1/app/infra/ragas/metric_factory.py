from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextEntityRecall,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
    NoiseSensitivity,
)

# https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/
METRIC_MAP = {
    "context_precision": ContextPrecision,
    "context_recall": ContextRecall,
    "context_entities_recall": ContextEntityRecall,
    "noise_sensitivity": NoiseSensitivity,
    "answer_relevancy": AnswerRelevancy,
    "faithfulness": Faithfulness
}


def build_retrieval_metrics(metric_names: list[str]):
    unknown = set(metric_names) - set(METRIC_MAP)
    if unknown:
        raise ValueError(f"Unsupported retrieval metrics: {sorted(unknown)}")
    return [METRIC_MAP[name] for name in metric_names]
