"""
Schemas module initialization.
"""
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserPasswordUpdate,
    UserInDB,
    UserPublic,
    UserProfile,
)
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    Token,
    TokenData,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePasswordRequest,
)
from app.schemas.portfolio import PortfolioBase
from app.schemas.portfolio_extended import (
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioInDB,
    PortfolioSummary,
)
from app.schemas.asset import (
    AssetBase,
    AssetCreate,
    AssetUpdate,
)
from app.schemas.holding import (
    HoldingBase,
    HoldingCreate,
    HoldingUpdate,
    HoldingInDB,
)

__all__ = [
    # User schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserPasswordUpdate",
    "UserInDB",
    "UserPublic", 
    "UserProfile",
    # Auth schemas
    "LoginRequest",
    "RegisterRequest",
    "Token",
    "TokenData",
    "RefreshTokenRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "ChangePasswordRequest",
    # Portfolio schemas
    "PortfolioBase",
    "PortfolioCreate",
    "PortfolioUpdate",
    "PortfolioInDB",
    "PortfolioSummary",
    # Asset schemas
    "AssetBase",
    "AssetCreate",
    "AssetUpdate",
    # Holding schemas
    "HoldingBase",
    "HoldingCreate",
    "HoldingUpdate",
    "HoldingInDB",
]
