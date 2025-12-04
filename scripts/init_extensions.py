#!/usr/bin/env python3
"""
Initialize PostgreSQL database with required extensions.
"""

import asyncio
import sys

import asyncpg


async def init_extensions():
    """Initialize database extensions."""
    try:
        # Connect to the database
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="contextiq",
            password="contextiq_dev_password",
            database="contextiq",
        )

        # Enable pgvector extension
        print("Enabling pgvector extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # Enable uuid-ossp extension
        print("Enabling uuid-ossp extension...")
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

        # Enable pg_trgm extension
        print("Enabling pg_trgm extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

        # Verify extensions
        print("\nVerifying extensions...")
        extensions = await conn.fetch(
            "SELECT extname, extversion FROM pg_extension "
            "WHERE extname IN ('vector', 'uuid-ossp', 'pg_trgm');"
        )

        for ext in extensions:
            print(f"  ✓ {ext['extname']} version {ext['extversion']}")

        await conn.close()
        print("\n✓ Database extensions initialized successfully!")
        return 0

    except Exception as e:
        print(f"\n✗ Error initializing database: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(init_extensions()))
