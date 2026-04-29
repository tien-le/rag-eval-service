#!/usr/bin/env python3
"""Initialize admin user script.

This script creates the initial admin user for the RAG Evaluation Service.
It can be run during deployment to set up the first administrator account.

Usage:
    python scripts/init_admin_user.py
    python scripts/init_admin_user.py --username admin --password mypassword
    python scripts/init_admin_user.py --env-file configs/dev.env
"""

from __future__ import annotations

import argparse
import hashlib
import os
import secrets
import sys
from datetime import UTC, datetime
from uuid import uuid4

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


from app.core.config.settings import get_settings


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password with salt.

    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)

    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)

    # Use PBKDF2-like iteration for better security
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100000
    ).hex()

    return hashed, salt


def generate_secure_password(length: int = 16) -> str:
    """Generate a secure random password.

    Args:
        length: Password length

    Returns:
        Secure random password
    """
    # Use URL-safe characters but ensure mix of cases and numbers
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        # Ensure at least one of each type
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
        ):
            return password


def create_admin_user(
    username: str,
    email: str,
    password: str | None = None,
) -> tuple[dict, str]:
    """Create admin user data structure.

    Args:
        username: Admin username
        email: Admin email address
        password: Optional password (generated if not provided)

    Returns:
        User data dictionary
    """
    if password is None:
        password = generate_secure_password()

    password_hash, salt = _hash_password(password)
    user_id = str(uuid4())

    user_data = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "password_salt": salt,
        "permissions": [
            "admin:*",
            "eval:*",
            "workflow:*",
            "user:*",
            "system:*",
        ],
        "is_active": True,
        "is_admin": True,
        "tenant_id": "default",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    return user_data, password


def print_user_info(user_data: dict, plain_password: str | None = None) -> None:
    """Print user creation information.

    Args:
        user_data: User data dictionary
        plain_password: Plain text password (if generated)
    """
    print("\n" + "=" * 60)
    print("ADMIN USER CREATED SUCCESSFULLY")
    print("=" * 60)
    print(f"User ID:    {user_data['user_id']}")
    print(f"Username:   {user_data['username']}")
    print(f"Email:      {user_data['email']}")
    print(f"Admin:      {user_data['is_admin']}")
    print(f"Active:     {user_data['is_active']}")
    print(f"Tenant:     {user_data['tenant_id']}")
    print("-" * 60)
    print(f"Permissions: {', '.join(user_data['permissions'])}")
    print("-" * 60)

    if plain_password:
        print(f"\n⚠️  PASSWORD (SAVE THIS SECURELY): {plain_password}")
        print("\nYou can now login with:")
        print("  POST /api/auth/login")
        print(
            f"  Body: {{'username': '{user_data['username']}', 'password': '{plain_password}'}}"
        )

    print("=" * 60 + "\n")


def save_to_env_file(
    username: str, password: str, env_file: str = "configs/dev.env"
) -> None:
    """Save admin credentials to environment file.

    Args:
        username: Admin username
        password: Admin password
        env_file: Path to environment file
    """
    env_path = os.path.join(os.path.dirname(__file__), "..", env_file)

    # Read existing content
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    # Update or add admin credentials
    admin_vars = {
        "ADMIN_USERNAME": username,
        "ADMIN_PASSWORD": password,
    }

    # Remove existing admin vars
    lines = [
        line
        for line in lines
        if not any(line.startswith(f"{key}=") for key in admin_vars.keys())
    ]

    # Add new admin vars
    lines.append("\n# Admin credentials (set by init_admin_user.py)\n")
    for key, value in admin_vars.items():
        lines.append(f"{key}={value}\n")

    # Write back
    with open(env_path, "w") as f:
        f.writelines(lines)

    print(f"✓ Admin credentials saved to {env_file}")


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Initialize admin user for RAG Evaluation Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create admin with generated password
  python scripts/init_admin_user.py

  # Create admin with specific credentials
  python scripts/init_admin_user.py --username myadmin --password mypass

  # Save credentials to env file
  python scripts/init_admin_user.py --save-env

  # Use different environment file
  python scripts/init_admin_user.py --env-file configs/prod.env
        """,
    )

    parser.add_argument(
        "--username",
        default="admin",
        help="Admin username (default: admin)",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Admin email (default: {username}@local)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Admin password (default: auto-generated)",
    )
    parser.add_argument(
        "--save-env",
        action="store_true",
        help="Save credentials to environment file",
    )
    parser.add_argument(
        "--env-file",
        default="configs/dev.env",
        help="Environment file path (default: configs/dev.env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without creating user",
    )

    args = parser.parse_args()

    # Set default email if not provided
    if args.email is None:
        args.email = f"{args.username}@local"

    print("\n🔧 RAG Evaluation Service - Admin User Initialization\n")

    if args.dry_run:
        print("DRY RUN - No changes will be made\n")

    # Load settings
    try:
        settings = get_settings()
        print(f"Environment: {settings.ENVIRONMENT.value}")
    except Exception as e:
        print(f"Warning: Could not load settings: {e}")

    print(f"Username: {args.username}")
    print(f"Email: {args.email}")

    if args.password:
        print("Password: (provided via command line)")
    else:
        print("Password: (will be auto-generated)")

    if args.dry_run:
        print("\n✓ Dry run complete")
        return 0

    # Create admin user
    try:
        user_data, plain_password = create_admin_user(
            username=args.username,
            email=args.email,
            password=args.password,
        )

        print_user_info(user_data, plain_password)

        # Save to env file if requested
        if args.save_env:
            save_to_env_file(args.username, plain_password, args.env_file)

        # TODO: In production, persist to database
        # For now, we just print the info
        print("⚠️  Note: This script currently only displays the user info.")
        print("   In production, implement database persistence.")
        print("\nTo use this admin user:")
        print("1. Save the credentials to your .env file:")
        print(f"   ADMIN_USERNAME={args.username}")
        print(f"   ADMIN_PASSWORD={plain_password}")
        print("\n2. Login via the API:")
        print("   POST /api/auth/login")
        print(f'   {{"username": "{args.username}", "password": "..."}}')

        return 0

    except Exception as e:
        print(f"\n❌ Error creating admin user: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
