#!/usr/bin/env python3
"""
Database initialization script.

Creates databases and runs initial migrations.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from shared.config.database import DatabaseSettings  # type: ignore[import-untyped]


async def create_database_if_not_exists() -> None:
    """Create database if it doesn't exist."""
    settings = DatabaseSettings()

    # Connect to postgres database to create our database
    postgres_url = (
        f"postgresql+asyncpg://{settings.user}:{settings.password}"
        f"@{settings.host}:{settings.port}/postgres"
    )

    engine = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")

    try:
        async with engine.connect() as conn:
            # Check if database exists
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": settings.database},
            )
            exists = result.scalar() is not None

            if not exists:
                print(f"Creating database: {settings.database}")
                await conn.execute(text(f'CREATE DATABASE "{settings.database}"'))
                print(f"✓ Database '{settings.database}' created successfully")
            else:
                print(f"✓ Database '{settings.database}' already exists")

    finally:
        await engine.dispose()


async def create_extensions() -> None:
    """Create required PostgreSQL extensions."""
    settings = DatabaseSettings()

    # Connect to our database
    engine = create_async_engine(settings.url)

    try:
        async with engine.connect() as conn:
            # Create uuid-ossp extension for UUID generation
            print("Creating extension: uuid-ossp")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
            await conn.commit()
            print("✓ Extension 'uuid-ossp' created")

            # Create pgcrypto extension for encryption functions
            print("Creating extension: pgcrypto")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            await conn.commit()
            print("✓ Extension 'pgcrypto' created")

    finally:
        await engine.dispose()


async def verify_connection() -> bool:
    """
    Verify database connection.

    Returns:
        True if connection successful
    """
    settings = DatabaseSettings()
    engine = create_async_engine(settings.url)

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
            print(f"✓ Successfully connected to database: {settings.database}")
            return True
    except Exception as e:
        print(f"✗ Failed to connect to database: {e}")
        return False
    finally:
        await engine.dispose()


async def main() -> None:
    """Main function to initialize database."""
    print("=" * 60)
    print("Database Initialization")
    print("=" * 60)
    print()

    try:
        # Create database
        await create_database_if_not_exists()
        print()

        # Create extensions
        await create_extensions()
        print()

        # Verify connection
        if await verify_connection():
            print()
            print("=" * 60)
            print("Database initialization complete!")
            print("=" * 60)
            print()
            print("Next steps:")
            print("  1. Run migrations: python scripts/db_migrate.py upgrade")
            print("  2. Or use: make db-upgrade")
            print()
        else:
            print()
            print("=" * 60)
            print("Database initialization failed!")
            print("=" * 60)
            sys.exit(1)

    except Exception as e:
        print()
        print(f"Error during initialization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
