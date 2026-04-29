"""Using RAGAS to evaluate the quality of RAG Agent"""

import json

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_correctness, answer_relevancy, answer_similarity
from ragas.run_config import RunConfig


def structure_eval_data(question, contexts, answer, ground_truth):
    """
    Structure the evaluation data into a Dataset format.

    Args:
        question (str): The evaluation question.
        contexts (list): List of contexts for the question.
        answer (str): The answer for the question.
        ground_truth (str): The ground truth for the evaluation.

    Returns:
        Dataset: A structured dataset containing the evaluation data.
    """
    eval_data = {
        "question": [question],
        "answer": [answer],
        "contexts": [contexts],
        "ground_truth": [ground_truth],
    }

    json_formatted_string = json.dumps(eval_data, indent=4)
    print("Structured Evaluation Data (in json format):")
    print(json_formatted_string)

    return Dataset.from_dict(eval_data)


def evaluate_llm_with_ragas(
    dataset, metrics, llm, embeddings, run_config, raise_exceptions=True, callbacks=None
):
    """
    Evaluate a dataset using RAGAS metrics and print the results.

    Args:
        dataset: The dataset to evaluate.
        metrics: List of metrics to use for evaluation.
        llm: The language model wrapper for evaluation.
        embeddings: The embeddings wrapper for evaluation.
        run_config: The run configuration for evaluation.
        raise_exceptions (bool, optional): Whether to raise exceptions during evaluation. Defaults to True.
        callbacks (list, optional): List of callback handlers. Defaults to None.

    Returns:
        None. Prints the evaluation result.
    """
    # Evaluate using RAGAS
    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        run_config=run_config,
        raise_exceptions=raise_exceptions,
        callbacks=callbacks,
    )

    df = result.to_pandas()
    print(df.head())


dataset_repub = structure_eval_data(
    question="Resulting from this Act, which groups would be harmed most?",
    contexts=["Role: you are a staunch Republican"],
    answer="Based on the provided context, as a staunch Republican, I would argue that the groups most harmed by the resulting Act would likely be small business owners and rural communities. The Act appears to include several provisions aimed at expanding access to healthcare and addressing issues related to poverty and inequality. Specifically, Sections 111201 and 111202 of the Act expand the definition of 'rural emergency hospital' under the Medicare program, which could provide additional support for rural hospitals that serve underserved communities. Additionally, Section 44301 expands the exclusion for orphan drugs under the Drug Price Negotiation Program, which could help reduce costs for some patients who rely on these medications. However, it's also worth noting that some provisions of the Act, such as the elimination of certain tax credits and deductions, could have a negative impact on small business owners and low-income families. For example, Section 112005 terminates the energy efficient home improvement credit, which could make it more difficult for low-income households to access affordable housing options.\n\nOverall, while there may be some benefits to certain groups under the Act, I believe that small business owners and rural communities would be among the most harmed by the resulting changes.",
    ground_truth="""Foreign nationals: The unfair foreign tax provision may affect foreign nationals who are subject to taxation by a foreign government.\
            Small businesses: Some provisions, such as the repeal of EPA rules and NHTSA standards, may benefit small businesses by reducing regulations and costs.\
            Low-income individuals: The legislation includes provisions related to health insurance, such as the exchange enrollment verification requirement and the premium adjustment percentage. These provisions may affect low-income individuals who rely on government-subsidized health insurance plans.\
            Environmental groups and advocates: The Act repeals EPA rules related to greenhouse gas emissions standards (Section 42201), which could harm environmental organizations that relied on these regulations to advocate for climate action.\
            Alien populations: The Act revises the definition of "eligible alien" in certain contexts, which could affect non-citizen populations who rely on specific healthcare programs or services.\
            Health care workers: The legislation includes provisions that may impact health care workers, particularly those involved in administering or managing government-subsidized health insurance programs.\
            Clean energy companies: The legislation includes provisions that may impact clean energy companies, particularly those involved in renewable energy projects and environmental regulations.""",
)


dataset_democrat = structure_eval_data(
    question="Resulting from this Act, which groups would be harmed most?",
    contexts=["Role: you are a staunch Democrat"],
    answer="Based on my understanding of the content of the provided text, it appears that the Act is primarily focused on tax reform and regulatory changes.\
                                However, some provisions in the Act could potentially harm certain groups. Some potential groups that might be harmed by this Act include:\
                                    * Low- and middle-income individuals who would face increased taxes under certain provisions\
                                    * Environmentally conscious individuals who would see stricter regulations relaxed regarding greenhouse gas emissions standards for light-duty vehicles\
                                    * Workers in the healthcare industry who may face changes to their job security due to the new requirements on exchange enrollment verification\
                                    * Certain corporations or organizations that might be affected by the new rules on foreign research and experimental expenditures, as well as the restriction on donations made pursuant to settlement agreements.",
    ground_truth="""Foreign nationals: The unfair foreign tax provision may affect foreign nationals who are subject to taxation by a foreign government.\
            Small businesses: Some provisions, such as the repeal of EPA rules and NHTSA standards, may benefit small businesses by reducing regulations and costs.\
            Low-income individuals: The legislation includes provisions related to health insurance, such as the exchange enrollment verification requirement and the premium adjustment percentage. These provisions may affect low-income individuals who rely on government-subsidized health insurance plans.\
            Environmental groups and advocates: The Act repeals EPA rules related to greenhouse gas emissions standards (Section 42201), which could harm environmental organizations that relied on these regulations to advocate for climate action.\
            Alien populations: The Act revises the definition of "eligible alien" in certain contexts, which could affect non-citizen populations who rely on specific healthcare programs or services.\
            Health care workers: The legislation includes provisions that may impact health care workers, particularly those involved in administering or managing government-subsidized health insurance programs.\
            Clean energy companies: The legislation includes provisions that may impact clean energy companies, particularly those involved in renewable energy projects and environmental regulations.""",
)

evaluate_llm_with_ragas(
    dataset=dataset_repub,
    metrics=[
        # faithfulness,
        answer_relevancy,
        answer_correctness,
        # context_precision,
        # context_recall,
        answer_similarity,
    ],
    llm=evaluator_llm,
    embeddings=evaluator_embed,
    run_config=RunConfig(timeout=300, max_retries=10, max_wait=300, log_tenacity=False),
    raise_exceptions=True,
    callbacks=None,
)
