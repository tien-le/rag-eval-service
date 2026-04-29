"""Utility functions for offline evaluation metrics."""

from collections import Counter


def _safe_divide(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def confusion_counts(actual: list[str], predicted: list[str], positive_label: str) -> dict[str, int]:
    tp = fp = tn = fn = 0
    for actual_label, predicted_label in zip(actual, predicted, strict=True):
        if predicted_label == positive_label and actual_label == positive_label:
            tp += 1
        elif predicted_label == positive_label and actual_label != positive_label:
            fp += 1
        elif predicted_label != positive_label and actual_label != positive_label:
            tn += 1
        else:
            fn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def classification_summary(actual: list[str], predicted: list[str], positive_label: str) -> dict[str, float | int]:
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted lengths must match")
    if not actual:
        raise ValueError("at least one sample is required")

    counts = confusion_counts(actual=actual, predicted=predicted, positive_label=positive_label)
    correct = sum(1 for a, p in zip(actual, predicted, strict=True) if a == p)
    precision = _safe_divide(counts["tp"], counts["tp"] + counts["fp"])
    recall = _safe_divide(counts["tp"], counts["tp"] + counts["fn"])
    f1 = _safe_divide(2 * precision * recall, precision + recall)
    accuracy = _safe_divide(correct, len(actual))
    return {
        "samples": len(actual),
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        **counts,
    }


def class_distribution(labels: list[str]) -> dict[str, int]:
    return dict(Counter(labels))

