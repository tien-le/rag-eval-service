"""Guardrail node implementations."""

import re
from typing import Any

from app.core.config.logging import get_logger
from app.domain.workflows.nodes.base import NodeExecutionError, WorkflowNode

logger = get_logger(__name__)


class InputGuardrailNode(WorkflowNode):
    """Input validation and sanitization."""

    def __init__(self):
        self.default_config = {
            "max_length": 10000,
            "blocked_patterns": [],
            "required_fields": [],
            "pii_detection": False,
        }

    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate and sanitize input."""
        merged_config = {**self.default_config, **config}

        violations = []

        # Check max length
        text = input_data.get("text", "")
        if len(text) > merged_config["max_length"]:
            violations.append(f"Input exceeds max length of {merged_config['max_length']}")

        # Check blocked patterns
        for pattern in merged_config["blocked_patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(f"Input contains blocked pattern: {pattern}")

        # Check required fields
        for field in merged_config["required_fields"]:
            if field not in input_data or not input_data[field]:
                violations.append(f"Required field missing: {field}")

        passed = len(violations) == 0

        logger.debug(
            "input_guardrail passed=%s violations=%d",
            passed,
            len(violations),
        )

        if violations and merged_config.get("block_on_violation", True):
            raise NodeExecutionError(
                node_type="guardrails",
                node_id="input_guardrail",
                message=f"Input guardrail violations: {'; '.join(violations)}",
                details={"violations": violations},
            )

        return {
            "passed": passed,
            "violations": violations,
            "sanitized_text": text[: merged_config["max_length"]],
        }


class OutputGuardrailNode(WorkflowNode):
    """Output validation and filtering."""

    def __init__(self):
        self.default_config = {
            "max_length": 50000,
            "blocked_patterns": [],
            "sensitive_topics": [],
            "pii_redaction": False,
        }

    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate and filter output."""
        merged_config = {**self.default_config, **config}

        answer = input_data.get("answer", input_data.get("text", ""))
        violations = []

        # Check max length
        if len(answer) > merged_config["max_length"]:
            violations.append(f"Output exceeds max length")

        # Check for blocked patterns
        for pattern in merged_config["blocked_patterns"]:
            if re.search(pattern, answer, re.IGNORECASE):
                violations.append("Output contains blocked content")

        passed = len(violations) == 0

        logger.debug(
            "output_guardrail passed=%s violations=%d",
            passed,
            len(violations),
        )

        # Redact PII if configured
        redacted_answer = answer
        if merged_config["pii_redaction"]:
            redacted_answer = self._redact_pii(answer)

        return {
            "passed": passed,
            "violations": violations,
            "filtered_answer": redacted_answer,
            "was_modified": redacted_answer != answer,
        }

    def _redact_pii(self, text: str) -> str:
        """Basic PII redaction patterns."""
        import re

        # Email
        text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", text)
        # Phone (basic)
        text = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]", text)
        # SSN
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]", text)

        return text


# Node registry entry
GuardrailNode = InputGuardrailNode
