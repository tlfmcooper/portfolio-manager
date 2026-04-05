"""App package metadata."""

import os


# The backend does not use Pydantic plugins. Disabling plugin discovery avoids
# slow importlib.metadata scans during model class creation on startup.
os.environ.setdefault("PYDANTIC_DISABLE_PLUGINS", "__all__")

__version__ = "1.0.0"

__all__ = ["__version__"]
