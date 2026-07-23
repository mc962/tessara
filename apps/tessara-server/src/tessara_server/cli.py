"""tessara_server CLI — administrative commands.

Usage:
    python -m tessara_server.cli create-user --email admin@example.com --password ... --superuser
    python -m tessara_server.cli create-token --email admin@example.com --name bootstrap
"""

import argparse
import asyncio
import sys


async def _create_user(email: str, password: str, is_superuser: bool) -> None:
    from tessara_server.data.database.connection import get_sessionmanager
    from tessara_server.data.repository import user_repository

    async with get_sessionmanager().session() as session:
        user = await user_repository.create(
            session, email, password, is_superuser=is_superuser, is_verified=True
        )

    role = "superuser" if is_superuser else "regular"
    print(f"\nCreated {role} user '{user.email}' (id={user.id}), pre-verified.\n")


async def _create_token(email: str, name: str) -> None:
    from tessara_server.data.database.connection import get_sessionmanager
    from tessara_server.data.repository import api_token_repository, user_repository

    async with get_sessionmanager().session() as session:
        user = await user_repository.get_by_email(session, email)
        if user is None:
            print(f"No user found with email '{email}'", file=sys.stderr)
            sys.exit(1)
        _token, plaintext = await api_token_repository.create(session, user.id, name)

    print(f"\nCreated API token '{name}' for '{email}':")
    print(f"  {plaintext}")
    print("\nCopy it now — it cannot be retrieved again.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tessara_server.cli", description="tessara_server admin CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_user_parser = subparsers.add_parser(
        "create-user", help="Create a new, pre-verified user"
    )
    create_user_parser.add_argument("--email", required=True, help="User's email address")
    create_user_parser.add_argument("--password", required=True, help="Initial password")
    create_user_parser.add_argument(
        "--superuser", action="store_true", help="Grant superuser privileges"
    )

    create_token_parser = subparsers.add_parser(
        "create-token", help="Create a new API token for an existing user"
    )
    create_token_parser.add_argument("--email", required=True, help="Owning user's email")
    create_token_parser.add_argument(
        "--name", required=True, help="Descriptive name/label for the token"
    )

    args = parser.parse_args()

    if args.command == "create-user":
        asyncio.run(
            _create_user(email=args.email, password=args.password, is_superuser=args.superuser)
        )
    elif args.command == "create-token":
        asyncio.run(_create_token(email=args.email, name=args.name))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
