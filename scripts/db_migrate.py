#!/usr/bin/env python3
"""
Database migration management script.

Provides utilities for managing Alembic database migrations.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_command(cmd: list[str], description: str) -> int:
    """
    Run a command and display output.

    Args:
        cmd: Command and arguments to run
        description: Description of the command

    Returns:
        Exit code
    """
    print(f"\n{'=' * 60}")
    print(f"{description}")
    print(f"{'=' * 60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def create_migration(message: str, autogenerate: bool = True) -> int:
    """
    Create a new migration.

    Args:
        message: Migration message
        autogenerate: Whether to autogenerate migration from models

    Returns:
        Exit code
    """
    cmd = ["alembic", "revision"]
    if autogenerate:
        cmd.append("--autogenerate")
    cmd.extend(["-m", message])

    return run_command(cmd, f"Creating migration: {message}")


def upgrade_database(revision: str = "head") -> int:
    """
    Upgrade database to a revision.

    Args:
        revision: Target revision (default: head)

    Returns:
        Exit code
    """
    cmd = ["alembic", "upgrade", revision]
    return run_command(cmd, f"Upgrading database to: {revision}")


def downgrade_database(revision: str) -> int:
    """
    Downgrade database to a revision.

    Args:
        revision: Target revision

    Returns:
        Exit code
    """
    cmd = ["alembic", "downgrade", revision]
    return run_command(cmd, f"Downgrading database to: {revision}")


def show_current_revision() -> int:
    """
    Show current database revision.

    Returns:
        Exit code
    """
    cmd = ["alembic", "current"]
    return run_command(cmd, "Current database revision")


def show_history(verbose: bool = False) -> int:
    """
    Show migration history.

    Args:
        verbose: Show verbose output

    Returns:
        Exit code
    """
    cmd = ["alembic", "history"]
    if verbose:
        cmd.append("--verbose")

    return run_command(cmd, "Migration history")


def show_heads() -> int:
    """
    Show head revisions.

    Returns:
        Exit code
    """
    cmd = ["alembic", "heads"]
    return run_command(cmd, "Head revisions")


def stamp_database(revision: str) -> int:
    """
    Stamp database with a revision without running migrations.

    Args:
        revision: Target revision

    Returns:
        Exit code
    """
    cmd = ["alembic", "stamp", revision]
    return run_command(cmd, f"Stamping database with: {revision}")


def main() -> None:
    """Main function to handle database migrations."""
    parser = argparse.ArgumentParser(
        description="Database migration management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new migration (autogenerate from models)
  python scripts/db_migrate.py create "add user table"

  # Create an empty migration
  python scripts/db_migrate.py create "custom migration" --no-autogenerate

  # Upgrade to latest
  python scripts/db_migrate.py upgrade

  # Upgrade to specific revision
  python scripts/db_migrate.py upgrade abc123

  # Downgrade one revision
  python scripts/db_migrate.py downgrade -1

  # Show current revision
  python scripts/db_migrate.py current

  # Show migration history
  python scripts/db_migrate.py history

  # Show migration history (verbose)
  python scripts/db_migrate.py history --verbose

  # Stamp database (mark as migrated without running)
  python scripts/db_migrate.py stamp head
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create migration
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("message", help="Migration message")
    create_parser.add_argument(
        "--no-autogenerate",
        action="store_true",
        help="Create empty migration (don't autogenerate)",
    )

    # Upgrade database
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database")
    upgrade_parser.add_argument(
        "revision", nargs="?", default="head", help="Target revision (default: head)"
    )

    # Downgrade database
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database")
    downgrade_parser.add_argument("revision", help="Target revision (e.g., -1, abc123)")

    # Show current revision
    subparsers.add_parser("current", help="Show current database revision")

    # Show history
    history_parser = subparsers.add_parser("history", help="Show migration history")
    history_parser.add_argument("--verbose", action="store_true", help="Verbose output")

    # Show heads
    subparsers.add_parser("heads", help="Show head revisions")

    # Stamp database
    stamp_parser = subparsers.add_parser("stamp", help="Stamp database with revision")
    stamp_parser.add_argument("revision", help="Target revision")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    exit_code = 0
    if args.command == "create":
        exit_code = create_migration(args.message, autogenerate=not args.no_autogenerate)
    elif args.command == "upgrade":
        exit_code = upgrade_database(args.revision)
    elif args.command == "downgrade":
        exit_code = downgrade_database(args.revision)
    elif args.command == "current":
        exit_code = show_current_revision()
    elif args.command == "history":
        exit_code = show_history(verbose=args.verbose)
    elif args.command == "heads":
        exit_code = show_heads()
    elif args.command == "stamp":
        exit_code = stamp_database(args.revision)
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
