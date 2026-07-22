"""tessara_server CLI — administrative commands.

Usage:
    python -m tessara_server.cli create-key --name admin --superuser
    python -m tessara_server.cli create-key --name regular_user
"""

import argparse
import asyncio
import sys


async def _create_key(name: str, is_superuser: bool) -> None:
    from tessara_server.data.database.connection import get_sessionmanager
    from tessara_server.data.repository import api_key_repository

    async with get_sessionmanager().session() as session:
        _key, plaintext = await api_key_repository.create(
            session, name, is_superuser=is_superuser
        )

    role = "superuser" if is_superuser else "regular"
    print(f"\nCreated {role} API key '{name}':")
    print(f"  {plaintext}")
    print("\nCopy it now — it cannot be retrieved again.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tessara_server.cli", description="tessara_server admin CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create-key", help="Create a new API key")
    create_parser.add_argument(
        "--name", required=True, help="Descriptive name for the key"
    )
    create_parser.add_argument(
        "--superuser", action="store_true", help="Grant superuser privileges"
    )

    args = parser.parse_args()

    if args.command == "create-key":
        asyncio.run(_create_key(name=args.name, is_superuser=args.superuser))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
