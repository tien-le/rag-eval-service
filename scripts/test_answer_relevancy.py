import requests

resp = requests.post(
    "http://localhost:8000/api/eval/ragas/single-turn",
    json={
        "user_input": "Who built the Eiffel Tower?",
        "response": "The Eiffel Tower was built by Gustave Eiffel.",
        "retrieved_contexts": [
            "The Eiffel Tower was designed by Gustave Eiffel's company."
        ],
        "reference": "The Eiffel Tower was built by Gustave Eiffel's company.",
        "metric_names": ["answer_relevancy"],
    },
)
print("Status:", resp.status_code)
print("Response:", resp.text)
