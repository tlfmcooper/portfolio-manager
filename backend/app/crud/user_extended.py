"""
User CRUD operations continued - Create, Update, Delete, Authentication.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.models import User, Portfolio
from app.schemas import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
    """Create a new user with default portfolio."""
    # Create user
    db_user = User(
        username=user_create.username.lower(),
        email=user_create.email.lower(),
        hashed_password=get_password_hash(user_create.password),
        full_name=user_create.full_name,
        is_active=True,
        is_superuser=False,
    )

    db.add(db_user)
    await db.flush()  # Flush to get the user ID

    # Create default portfolio for the user
    default_portfolio = Portfolio(
        user_id=db_user.id,
        name="My Portfolio",
        description="Default portfolio",
        initial_value=0.0,
        currency="USD",
    )

    db.add(default_portfolio)
    await db.commit()
    await db.refresh(db_user)

    return db_user


async def update_user(
    db: AsyncSession, user_id: int, user_update: UserUpdate
) -> Optional[User]:
    """Update user information."""
    db_user = await get_user(db, user_id)
    if not db_user:
        return None

    update_data = user_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_user, field, value)

    db_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_user)

    return db_user


async def update_user_password(
    db: AsyncSession, user_id: int, new_password: str
) -> bool:
    """Update user password."""
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(
            hashed_password=get_password_hash(new_password),
            updated_at=datetime.utcnow(),
        )
    )

    result = await db.execute(stmt)
    await db.commit()

    return result.rowcount > 0


async def update_last_login(db: AsyncSession, user_id: int) -> bool:
    """Update user's last login timestamp."""
    stmt = update(User).where(User.id == user_id).values(last_login=datetime.utcnow())

    result = await db.execute(stmt)
    await db.commit()

    return result.rowcount > 0


async def deactivate_user(db: AsyncSession, user_id: int) -> bool:
    """Deactivate a user account."""
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(is_active=False, updated_at=datetime.utcnow())
    )

    result = await db.execute(stmt)
    await db.commit()

    return result.rowcount > 0


async def authenticate_user(
    db: AsyncSession, identifier: str, password: str
) -> Optional[User]:
    """Authenticate user with username/email and password."""
    user = await get_user_by_email_or_username(db, identifier)

    if not user:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    # Update last login
    await update_last_login(db, user.id)

    return user


# Import this at the end to avoid circular imports
from app.crud.user import get_user, get_user_by_email_or_username
