import httpx
from openai import AsyncOpenAI
from ragas.embeddings.base import embedding_factory
from ragas.llms import llm_factory

from app.core.config.exceptions import EmbeddingServiceError


OLLAMA_URL = "http://localhost:11434"
OLLAMA_OPENAI_URL = f"{OLLAMA_URL}/v1"
EVALUATOR_MODEL = "qwen2.5:latest"
EVALUATOR_EMBEDDING_MODEL = "nomic-embed-text:latest"


class OllamaEmbedding:
    def __init__(
        self,
        url: str = OLLAMA_URL,
        model: str = EVALUATOR_EMBEDDING_MODEL,
    ):
        self.url = url.rstrip("/")
        self.model = model

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.url}/api/embed",
                    json={"model": self.model, "input": texts},
                )
                response.raise_for_status()
                return response.json()["embeddings"]
        except Exception as e:
            raise EmbeddingServiceError(f"Ollama embedding failed: {e}") from e

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_documents([text])
        return results[0]


client = AsyncOpenAI(
    api_key="ollama",
    base_url=OLLAMA_OPENAI_URL,
)

evaluator_model = llm_factory(
    EVALUATOR_MODEL,
    provider="openai",
    client=client,
)

evaluator_embeddings = embedding_factory(
    "openai",
    model=EVALUATOR_EMBEDDING_MODEL,
    client=client,
    interface="modern",
)