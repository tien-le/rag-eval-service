"""Chunking node implementations."""

from typing import Any

from app.core.config.logging import get_logger
from app.domain.workflows.nodes.base import NodeExecutionError, WorkflowNode

logger = get_logger(__name__)


class RecursiveTextSplitterNode(WorkflowNode):
    """Text chunking using recursive character splitting."""

    def __init__(self):
        self.default_config = {
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "separators": ["\n\n", "\n", ". ", " ", ""],
        }

    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Split text into chunks."""
        merged_config = {**self.default_config, **config}

        text = input_data.get("text", "")
        if not text:
            return {"chunks": [], "chunk_count": 0}

        # Simple recursive splitting implementation
        chunks = self._split_recursive(
            text,
            chunk_size=merged_config["chunk_size"],
            chunk_overlap=merged_config["chunk_overlap"],
            separators=merged_config["separators"],
        )

        logger.debug(
            "text_chunked chunk_count=%d chunk_size=%d",
            len(chunks),
            merged_config["chunk_size"],
        )

        return {
            "chunks": chunks,
            "chunk_count": len(chunks),
            "chunk_size": merged_config["chunk_size"],
            "chunk_overlap": merged_config["chunk_overlap"],
        }

    def _split_recursive(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        separators: list[str],
    ) -> list[str]:
        """Recursively split text by separators."""
        chunks: list[str] = []
        current_chunk = ""

        # Split by first separator
        if separators:
            parts = text.split(separators[0])
        else:
            parts = [text]

        for part in parts:
            if len(current_chunk) + len(part) <= chunk_size:
                current_chunk += part + (separators[0] if separators else "")
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # Handle overlap
                overlap_start = max(0, len(current_chunk) - chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + part + (separators[0] if separators else "")

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate chunking configuration."""
        errors = []

        chunk_size = config.get("chunk_size", 1000)
        chunk_overlap = config.get("chunk_overlap", 200)

        if chunk_size < 100:
            errors.append("chunk_size must be at least 100")
        if chunk_size > 10000:
            errors.append("chunk_size must be at most 10000")
        if chunk_overlap >= chunk_size:
            errors.append("chunk_overlap must be less than chunk_size")
        if chunk_overlap < 0:
            errors.append("chunk_overlap must be non-negative")

        return errors


class MarkdownHeaderSplitterNode(WorkflowNode):
    """Split markdown by headers."""

    def __init__(self):
        self.default_config = {
            "headers_to_split_on": ["#", "##", "###"],
            "return_each_line": False,
        }

    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Split markdown by headers."""
        merged_config = {**self.default_config, **config}

        text = input_data.get("text", "")
        if not text:
            return {"chunks": [], "headers": []}

        import re

        headers = merged_config["headers_to_split_on"]
        header_pattern = "|".join(re.escape(h) for h in headers)
        pattern = f"^({header_pattern}) "

        chunks = []
        current_chunk = ""
        current_header = ""

        for line in text.split("\n"):
            if re.match(pattern, line):
                if current_chunk:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "header": current_header,
                    })
                current_header = line.strip()
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"

        if current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "header": current_header,
            })

        return {
            "chunks": chunks,
            "chunk_count": len(chunks),
            "headers": [c["header"] for c in chunks if c["header"]],
        }


# Node registry entry
ChunkingNode = RecursiveTextSplitterNode
