"""Qdrant vector database client for semantic search and embeddings."""

from typing import List

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings


class QdrantClient:
    """
    Qdrant vector database client wrapper.

    Provides a clean interface for vector operations,
    abstracting Qdrant client details.

    Example:
        ```python
        qdrant_client = QdrantClient()
        await qdrant_client.create_collection("documents", vector_size=384)
        points = [PointStruct(id=1, vector=[0.1, 0.2, ...])]
        await qdrant_client.upsert_vectors("documents", points)
        ```
    """

    def __init__(self) -> None:
        """Initialize Qdrant client."""
        self.client: AsyncQdrantClient | None = None

    async def connect(self) -> None:
        """
        Connect to Qdrant.

        Raises:
            ValueError: If QDRANT_URL is not configured
        """
        if not settings.QDRANT_URL:
            raise ValueError("QDRANT_URL not configured in settings")

        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )

    async def disconnect(self) -> None:
        """Close Qdrant connection."""
        if self.client:
            await self.client.close()
            self.client = None

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int = 384,
        distance: Distance = Distance.COSINE,
    ) -> None:
        """
        Create vector collection.

        Args:
            collection_name: Name of the collection
            vector_size: Size of the vector embeddings
            distance: Distance metric (COSINE, EUCLIDEAN, DOT)

        Raises:
            RuntimeError: If client not connected
        """
        if self.client is None:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")

        await self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance,
            ),
        )

    async def upsert_vectors(
        self,
        collection_name: str,
        points: List[PointStruct],
    ) -> None:
        """
        Insert or update vectors.

        Args:
            collection_name: Name of the collection
            points: List of PointStruct instances with vectors

        Raises:
            RuntimeError: If client not connected
        """
        if self.client is None:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")

        await self.client.upsert(
            collection_name=collection_name,
            points=points,
        )

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> List[dict]:
        """
        Perform semantic search.

        Args:
            collection_name: Name of the collection
            query_vector: Query vector for search
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of search results with scores

        Raises:
            RuntimeError: If client not connected
        """
        if self.client is None:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")

        results = await self.client.search(  # type: ignore[attr-defined]
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results
        ]

    async def delete_collection(self, collection_name: str) -> None:
        """
        Delete collection.

        Args:
            collection_name: Name of the collection to delete

        Raises:
            RuntimeError: If client not connected
        """
        if self.client is None:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")

        await self.client.delete_collection(collection_name=collection_name)

    async def collection_exists(self, collection_name: str) -> bool:
        """
        Check if collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection exists, False otherwise

        Raises:
            RuntimeError: If client not connected
        """
        if self.client is None:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")

        collections = await self.client.get_collections()
        return collection_name in [col.name for col in collections.collections]


# Global Qdrant client instance
qdrant_client = QdrantClient()
