"""
CRUD module initialization.
"""
from app.crud.user import (
    get_user,
    get_user_by_email,
    get_user_by_username,
    get_user_by_email_or_username,
    get_users,
)
from app.crud.user_extended import (
    create_user,
    update_user,
    update_user_password,
    update_last_login,
    deactivate_user,
    authenticate_user,
)
from app.crud.portfolio import (
    get_portfolio,
    get_user_portfolio,
    create_portfolio,
)
from app.crud.portfolio_extended import (
    update_portfolio,
    calculate_portfolio_metrics,
    update_portfolio_metrics,
)
from app.crud.asset import (
    get_asset,
    get_asset_by_ticker,
    get_assets,
    create_asset,
    get_or_create_asset,
    update_asset,
)
from app.crud.holding import (
    get_holding,
    get_portfolio_holdings,
    get_holding_by_asset,
)
from app.crud.holding_extended import (
    create_holding,
    update_holding,
    delete_holding,
)

__all__ = [
    # User CRUD
    "get_user",
    "get_user_by_email",
    "get_user_by_username",
    "get_user_by_email_or_username",
    "get_users",
    "create_user",
    "update_user",
    "update_user_password",
    "update_last_login",
    "deactivate_user",
    "authenticate_user",
    # Portfolio CRUD
    "get_portfolio",
    "get_user_portfolio",
    "create_portfolio",
    "update_portfolio",
    "calculate_portfolio_metrics",
    "update_portfolio_metrics",
    # Asset CRUD
    "get_asset",
    "get_asset_by_ticker",
    "get_assets",
    "create_asset",
    "get_or_create_asset",
    "update_asset",
    # Holding CRUD
    "get_holding",
    "get_portfolio_holdings", 
    "get_holding_by_asset",
    "create_holding",
    "update_holding",
    "delete_holding",
]
