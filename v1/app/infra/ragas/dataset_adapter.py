from datasets import Dataset


# idea: build Dataset from pd.DataFrame
def build_retrieval_dataset(
    question: str,
    contexts: list[str],
    reference_answer: str | None,
) -> Dataset:
    return Dataset.from_list(
        [
            {
                "user_input": question,
                "retrieved_contexts": contexts,
                "reference": reference_answer,
            }
        ]
    )
