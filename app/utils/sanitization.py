"""Sanitization utilities for preventing XSS and injection attacks."""

import html
import re
from typing import Any

# Pattern for script tags (escaped HTML)
SCRIPT_TAG_PATTERN = re.compile(r"&lt;script.*?&gt;.*?&lt;/script&gt;", flags=re.DOTALL)

# Email validation pattern
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Password strength patterns
UPPERCASE_PATTERN = re.compile(r"[A-Z]")
LOWERCASE_PATTERN = re.compile(r"[a-z]")
DIGIT_PATTERN = re.compile(r"[0-9]")
SPECIAL_CHAR_PATTERN = re.compile(r'[!@#$%^&*(),.?":{}|<>]')


def sanitize_string(value: str) -> str:
    """Sanitize a string to prevent XSS and other injection attacks.

    Args:
        value: The string to sanitize

    Returns:
        The sanitized string

    Example:
        ```python
        safe_input = sanitize_string("<script>alert('xss')</script>")
        ```
    """
    if not isinstance(value, str):
        value = str(value)

    # HTML escape to prevent XSS
    value = html.escape(value)

    # Remove any script tags that might have been escaped
    value = SCRIPT_TAG_PATTERN.sub("", value)

    # Remove null bytes
    value = value.replace("\0", "")

    return value


def sanitize_email(email: str) -> str:
    """Sanitize and validate an email address.

    Args:
        email: The email address to sanitize

    Returns:
        The sanitized email address (lowercased)

    Raises:
        ValueError: If the email format is invalid

    Example:
        ```python
        try:
            clean_email = sanitize_email("User@Example.COM")
            # Returns: "user@example.com"
        except ValueError as e:
            # Handle invalid email
            ...
        ```
    """
    email = sanitize_string(email)

    if not EMAIL_PATTERN.match(email):
        raise ValueError("Invalid email format")

    return email.lower()


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize all string values in a dictionary.

    Args:
        data: The dictionary to sanitize

    Returns:
        A new dictionary with sanitized string values

    Example:
        ```python
        user_data = {
            "name": "<script>alert('xss')</script>",
            "email": "user@example.com",
            "metadata": {"bio": "Hello <b>world</b>"}
        }
        safe_data = sanitize_dict(user_data)
        ```
    """
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = sanitize_list(value)
        else:
            sanitized[key] = value
    return sanitized


def sanitize_list(data: list[Any]) -> list[Any]:
    """Recursively sanitize all string values in a list.

    Args:
        data: The list to sanitize

    Returns:
        A new list with sanitized string values

    Example:
        ```python
        user_inputs = [
            "<script>alert('xss')</script>",
            {"name": "John", "bio": "<b>Hello</b>"},
            ["nested", "<script>bad</script>"]
        ]
        safe_inputs = sanitize_list(user_inputs)
        ```
    """
    sanitized: list[Any] = []
    for item in data:
        if isinstance(item, str):
            sanitized.append(sanitize_string(item))
        elif isinstance(item, dict):
            sanitized.append(sanitize_dict(item))
        elif isinstance(item, list):
            sanitized.append(sanitize_list(item))
        else:
            sanitized.append(item)
    return sanitized


def validate_password_strength(password: str) -> bool:
    """Validate password strength requirements.

    Validates that the password meets the following requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one number
    - Contains at least one special character

    Args:
        password: The password to validate

    Returns:
        True if the password meets all requirements

    Raises:
        ValueError: If the password does not meet requirements, with a
            descriptive error message

    Example:
        ```python
        try:
            validate_password_strength("MyP@ssw0rd")
            # Password is valid
        except ValueError as e:
            # Handle weak password
            print(f"Password validation failed: {e}")
        ```
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if not UPPERCASE_PATTERN.search(password):
        raise ValueError("Password must contain at least one uppercase letter")

    if not LOWERCASE_PATTERN.search(password):
        raise ValueError("Password must contain at least one lowercase letter")

    if not DIGIT_PATTERN.search(password):
        raise ValueError("Password must contain at least one number")

    if not SPECIAL_CHAR_PATTERN.search(password):
        raise ValueError("Password must contain at least one special character")

    return True
