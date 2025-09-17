# Import database components
from .database import Base, SessionLocal, engine, init_db, get_db, user_assets
from .database import User, Asset, Portfolio, Holding

# Make these available when importing from models
__all__ = [
    'Base', 'SessionLocal', 'engine', 'init_db', 'get_db',
    'User', 'Asset', 'Portfolio', 'Holding', 'user_assets'
]
