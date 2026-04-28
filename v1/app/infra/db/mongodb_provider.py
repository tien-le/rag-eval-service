"""MongoDB client for document storage."""

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings


class MongoDBClient:
    """
    MongoDB async client wrapper.

    Provides a clean interface for MongoDB operations,
    abstracting Motor client details.

    Example:
        ```python
        mongodb_client = MongoDBClient()
        await mongodb_client.connect()
        collection = mongodb_client.get_collection("users")
        await collection.insert_one({"email": "user@example.com"})
        ```
    """

    def __init__(self) -> None:
        """Initialize MongoDB client."""
        self.client: AsyncIOMotorClient | None = None
        self.database: AsyncIOMotorDatabase | None = None

    async def connect(self) -> None:
        """
        Connect to MongoDB.

        Raises:
            ValueError: If MONGODB_URL is not configured
        """
        if not settings.MONGODB_URL:
            raise ValueError("MONGODB_URL not configured in settings")

        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.database = self.client[settings.MONGODB_DATABASE]

    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.database = None

    def get_collection(self, name: str) -> Any:
        """
        Get collection by name.

        Args:
            name: Collection name

        Returns:
            Motor collection instance

        Raises:
            RuntimeError: If not connected to database
        """
        if self.database is None:
            raise RuntimeError("MongoDB client not connected. Call connect() first.")

        return self.database[name]

    async def ping(self) -> bool:
        """
        Check database connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        if self.client is None:
            return False

        try:
            await self.client.admin.command("ping")
            return True
        except Exception:
            return False


# Global MongoDB client instance
mongodb_client = MongoDBClient()
