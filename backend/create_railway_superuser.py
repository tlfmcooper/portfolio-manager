"""
Create superuser directly on Railway database.
This script connects to Railway's database and creates the superuser there.
"""
import asyncio
import os
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User


async def create_railway_superuser():
    """Create superuser on Railway database."""

    # User details
    username = "alkhaf"
    email = "developer0.ali1@gmail.com"
    password = "Password123"  # Change this to your desired password

    hashed_password = get_password_hash(password)

    async with AsyncSessionLocal() as session:
        # Check if user already exists
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user:
            print(f"✅ User '{username}' already exists. Updating password and superuser status...")
            user.hashed_password = hashed_password
            user.is_active = True
            user.is_superuser = True
            user.email = email
            action = "updated"
        else:
            print(f"✨ Creating new superuser '{username}'...")
            user = User(
                username=username,
                email=email,
                full_name="Ali Khaf",
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
            action = "created"

        await session.commit()
        print(f"✅ Superuser '{username}' {action} successfully!")
        print(f"📧 Email: {email}")
        print(f"🔑 Password: {password}")
        print(f"\n🎉 You can now login at: https://pm.alikone.dev")


if __name__ == "__main__":
    print("🚀 Creating superuser on Railway database...")
    print("=" * 60)
    asyncio.run(create_railway_superuser())
