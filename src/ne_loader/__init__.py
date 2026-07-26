"""Natural Earth Loader package.

See data_loader.py and map_loader.py for public API entrypoints.
"""

from .data_loader import download_dataset, fetch_dataset, get_dataset
from .map_loader import Resolution, get_natural_earth

__all__ = [
    "Resolution",
    "download_dataset",
    "fetch_dataset",
    "get_dataset",
    "get_natural_earth",
]
