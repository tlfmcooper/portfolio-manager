"""
API v1 router initialization.
"""

from fastapi import APIRouter

from app.api.v1 import auth, users, portfolios, holdings, assets, transactions, analysis, market, exchange
from app.api.v1.auth_extended import refresh_router

api_router = APIRouter()

# Include authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(refresh_router, prefix="/auth", tags=["authentication"])

# Include user management routes
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Include portfolio management routes
api_router.include_router(portfolios.router, prefix="/portfolios", tags=["portfolios"])

# Include holdings management routes
api_router.include_router(holdings.router, prefix="/holdings", tags=["holdings"])

# Include assets management routes
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])

# Include transactions management routes (no prefix - routes define their own paths)
api_router.include_router(transactions.router, tags=["transactions"])

# Include analysis routes
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])

# Include market data routes
api_router.include_router(market.router, prefix="/market", tags=["market"])

# Include exchange rate routes
api_router.include_router(exchange.router, prefix="/exchange", tags=["exchange"])
