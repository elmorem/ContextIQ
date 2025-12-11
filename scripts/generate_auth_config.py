#!/usr/bin/env python3
"""
Generate authentication configuration.

Helps developers generate JWT secrets and API keys for development.
"""

import secrets
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.auth.api_key import APIKeyHandler


def generate_jwt_secret() -> str:
    """Generate a secure JWT secret key."""
    return secrets.token_urlsafe(32)


def generate_api_key() -> str:
    """Generate a secure API key."""
    handler = APIKeyHandler()
    return handler.generate_api_key()


def main() -> None:
    """Main function to generate auth configuration."""
    print("=" * 60)
    print("ContextIQ Authentication Configuration Generator")
    print("=" * 60)
    print()

    # Generate JWT secret
    jwt_secret = generate_jwt_secret()
    print("JWT Secret Key:")
    print(f"  AUTH_JWT_SECRET_KEY={jwt_secret}")
    print()

    # Generate API keys
    print("Example API Keys (for development):")
    print()

    for i in range(3):
        api_key = generate_api_key()
        print(f"  API Key #{i + 1}:")
        print(f"    Key: {api_key}")
        print(f"    User ID: user_{i + 1}")
        print(f"    Org ID: org_123")
        print()

    print("=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print()
    print("1. Copy .env.auth.example to .env:")
    print("   cp .env.auth.example .env")
    print()
    print("2. Update .env with the generated JWT secret")
    print()
    print("3. Store API keys securely (database or secrets manager)")
    print()
    print("4. Configure your application to use the auth handlers")
    print()
    print("For more information, see shared/auth/README.md")
    print()


if __name__ == "__main__":
    main()
