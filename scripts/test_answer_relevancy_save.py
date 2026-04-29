import json

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

with open("/home/lavie/dev/work/work_py/rag-eval-service/response.json", "w") as f:
    json.dump(
        {
            "status": resp.status_code,
            "text": resp.text,
            "json": resp.json()
            if resp.headers.get("content-type", "").startswith("application/json")
            else None,
        },
        f,
        indent=2,
    )

print("Done")
