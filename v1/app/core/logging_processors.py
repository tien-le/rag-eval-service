import re
from typing import Any

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
    "secret",
}


def mask_email(email: str, visible: int = 2) -> str:
    if "@" not in email:
        return email

    local, domain = email.split("@", 1)

    if visible <= 0:
        return f"***@{domain}"

    if len(local) <= visible:
        return f"{'*' * len(local)}@{domain}"

    return f"{local[:visible]}{'*' * (len(local) - visible)}@{domain}"


def redact_sensitive_data(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    for key, value in list(event_dict.items()):
        normalized_key = key.lower()

        if normalized_key in SENSITIVE_KEYS:
            event_dict[key] = "***"
            continue

        if isinstance(value, str):
            event_dict[key] = EMAIL_RE.sub(
                lambda match: mask_email(match.group()),
                value,
            )

    return event_dict
