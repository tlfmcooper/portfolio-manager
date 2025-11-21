"""Utility script to create or promote a user to superuser status."""
import argparse
import asyncio
from getpass import getpass
from typing import Optional

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User


async def create_or_update_superuser(
    username: str,
    email: Optional[str],
    password: str,
    full_name: Optional[str] = None,
) -> str:
    """Create a new superuser or update an existing user."""
    hashed_password = get_password_hash(password)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user:
            if email:
                user.email = email
            if full_name:
                user.full_name = full_name
            user.hashed_password = hashed_password
            user.is_active = True
            user.is_superuser = True
            session.add(user)
            action = "updated"
        else:
            if not email:
                raise ValueError("Email is required when creating a new user")

            user = User(
                username=username,
                email=email,
                full_name=full_name,
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
            action = "created"

        await session.commit()
        return action


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update a superuser")
    parser.add_argument("username", help="Username of the superuser")
    parser.add_argument("--email", help="Email for the user (required when creating)")
    parser.add_argument("--full-name", dest="full_name", help="Optional full name")
    parser.add_argument(
        "--password",
        help="Password for the user. If omitted, you will be prompted to enter one.",
    )
    return parser.parse_args()


def prompt_for_password(existing: Optional[str]) -> str:
    if existing:
        return existing

    password = getpass("Password: ")
    confirm = getpass("Confirm password: ")
    if password != confirm:
        raise ValueError("Passwords do not match")
    if not password:
        raise ValueError("Password cannot be empty")
    return password


async def main() -> None:
    args = parse_args()
    password = prompt_for_password(args.password)
    action = await create_or_update_superuser(
        username=args.username,
        email=args.email,
        password=password,
        full_name=args.full_name,
    )
    print(f"Superuser '{args.username}' {action} successfully.")


if __name__ == "__main__":
    asyncio.run(main())
