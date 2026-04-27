import logging
import logging.config
import sys
from pathlib import Path
from typing import Any

import structlog

from app.core.config import settings
from app.core.logging_processors import redact_sensitive_data


def setup_logging() -> None:
    log_level = settings.LOG_LEVEL.upper()
    is_local = settings.is_development or settings.is_testing

    log_dir = Path("var/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        redact_sensitive_data,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer = (
        structlog.dev.ConsoleRenderer(colors=True)
        if is_local
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "structlog",
            "level": log_level,
        }
    }

    root_handlers = ["console"]

    if settings.is_production:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_dir / "app.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "structlog",
            "level": log_level,
        }
        root_handlers.append("file")

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "structlog": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": renderer,
                    "foreign_pre_chain": shared_processors,
                },
            },
            "handlers": handlers,
            "loggers": {
                "": {
                    "handlers": root_handlers,
                    "level": log_level,
                    "propagate": False,
                },
                "app": {
                    "handlers": root_handlers,
                    "level": log_level,
                    "propagate": False,
                },
                "uvicorn": {
                    "handlers": root_handlers,
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": root_handlers,
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": root_handlers,
                    "level": "WARNING",
                    "propagate": False,
                },
                "sqlalchemy.engine": {
                    "handlers": root_handlers,
                    "level": "WARNING",
                    "propagate": False,
                },
                "httpx": {
                    "handlers": root_handlers,
                    "level": "WARNING",
                    "propagate": False,
                },
                "httpcore": {
                    "handlers": root_handlers,
                    "level": "WARNING",
                    "propagate": False,
                },
                "langchain": {
                    "handlers": root_handlers,
                    "level": "INFO",
                    "propagate": False,
                },
                "ragas": {
                    "handlers": root_handlers,
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Logging for Various Usages.

    Args:
        name (str): Logger name, typically __name__ of the module

    Returns:
        structlog.stdlib.BoundLogger: Configured logger instance
        
    Usage:
    Usage in normal services
        ```python
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        async def create_user(email: str) -> None:
            logger.info(
                "user_creation_started",
                email=email,
            )

            try:
                ...
            except Exception:
                logger.exception(
                    "user_creation_failed",
                    email=email,
                )
                raise
        ```
        
    Usage in RAG pipeline
        ```python
        logger.info(
            "rag_query_started",
            query=query,
            top_k=top_k,
            collection="documents",
        )

        logger.info(
            "rag_retrieval_completed",
            retrieved_docs=len(documents),
            duration_ms=retrieval_duration_ms,
        )

        logger.info(
            "rag_generation_completed",
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_ms=generation_duration_ms,
        )
        ```
        
    Usage in RAGAS evaluation
        ```python
        logger.info(
            "ragas_eval_started",
            dataset_name=dataset_name,
            sample_count=len(dataset),
        )

        logger.info(
            "ragas_eval_completed",
            faithfulness=faithfulness,
            answer_relevancy=answer_relevancy,
            context_precision=context_precision,
            context_recall=context_recall,
        )
        ```
    """
    return structlog.get_logger(name)

