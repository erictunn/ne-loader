"""Natural Earth Loader package.

See map_loader.py for public API entrypoint.
"""

from .data_loader import download_dataset
from .map_loader import Resolution, get_natural_earth

__all__ = ["Resolution", "download_dataset", "get_natural_earth"]
