"""
Authentication API routes.
"""
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.core.config import settings
from app.schemas import (
    LoginRequest,
    RegisterRequest,
    Token,
    AuthBootstrapResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    UserInDB,
)
from app.crud import authenticate_user, create_user, get_user_by_email, get_user_by_username, update_user_password
from app.utils.dependencies import get_current_active_user
from app.models import Portfolio, User

router = APIRouter()


@router.get("/bootstrap", response_model=AuthBootstrapResponse)
async def bootstrap_auth(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Return the minimum authenticated state needed to render the app shell.

    This endpoint intentionally avoids portfolio summary, market data, YTD,
    yfinance, and analytics work so it remains fast during app startup.
    """
    portfolio_result = await db.execute(
        select(Portfolio.id)
        .where(Portfolio.user_id == current_user.id)
        .where(Portfolio.is_active == True)
        .limit(1)
    )
    portfolio_id = portfolio_result.scalar_one_or_none()

    return {
        "user": current_user,
        "portfolio_id": portfolio_id,
        "is_onboarded": portfolio_id is not None,
    }


@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username}, 
        expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/register", response_model=UserInDB)
async def register(
    user_data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create new user account.
    """
    # Check if user already exists
    if await get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    if await get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = await create_user(db, user_data)
    return user
