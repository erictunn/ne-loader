"""Handles downloading and fetching of NE data."""

import logging
from pathlib import Path
from typing import Literal, overload

import geopandas as gpd

from .cacher import PathLike, get_cache_dir
from .data_loader import _download_dataset
from .error_handler import ErrorMode, error_handler, validate_error_mode

fallback_logger: logging.Logger = logging.getLogger(__name__)

Resolution = Literal["10m", "50m", "110m"]


def build_ne_filename(name: str, res: str = "10m", suffix: str = ".zip") -> str:
    """Build a Natural Earth dataset filename."""
    return f"ne_{res}_{name}{suffix}"


def build_ne_url(category: str, name: str, res: Resolution) -> str:
    """Build the download URL for a Natural Earth vector dataset."""
    return (
        f"https://naciscdn.org/naturalearth/{res}/{category}/"
        f"{build_ne_filename(name, res)}"
    )


def build_ne_zip_path(data_dir: PathLike, name: str, res: Resolution) -> Path:
    """Build the local cache path for a Natural Earth zip file."""
    return Path(data_dir) / build_ne_filename(name, res)


def build_ne_extract_dir(data_dir: PathLike, name: str, res: Resolution) -> Path:
    """Build the local extraction directory for a Natural Earth dataset."""
    return Path(data_dir) / build_ne_filename(name, res, suffix="")


def build_ne_shp_path(data_dir: PathLike, name: str, res: Resolution) -> Path:
    """Build the local shapefile path for an extracted Natural Earth dataset."""
    extract_dir: Path = build_ne_extract_dir(data_dir, name, res)
    return extract_dir / build_ne_filename(name, res, suffix=".shp")


@overload
def get_natural_earth(
    category: str,
    name: str,
    res: Resolution = "10m",
    *,
    dir_override: PathLike | None = None,
    error_mode: Literal["ignore"],
    user_logger: logging.Logger | None = None,
) -> gpd.GeoDataFrame | None: ...


@overload
def get_natural_earth(
    category: str,
    name: str,
    res: Resolution = "10m",
    *,
    dir_override: PathLike | None = None,
    error_mode: Literal["raise"] = "raise",
    user_logger: logging.Logger | None = None,
) -> gpd.GeoDataFrame: ...


@overload
def get_natural_earth(
    category: str,
    name: str,
    res: Resolution = "10m",
    *,
    dir_override: PathLike | None = None,
    error_mode: Literal["return"],
    user_logger: logging.Logger | None = None,
) -> gpd.GeoDataFrame | Exception: ...


def get_natural_earth(
    category: str,
    name: str,
    res: Resolution = "10m",
    *,
    dir_override: PathLike | None = None,
    error_mode: ErrorMode = "raise",
    user_logger: logging.Logger | None = None,
) -> gpd.GeoDataFrame | Exception | None:
    """Download, cache, and load a Natural Earth vector dataset.

    Args:
        category: Natural Earth data category, e.g. "cultural" or
            "physical".
        name: Dataset name without the ``ne_{res}_`` prefix, e.g.
            "admin_0_countries".
        res: Natural Earth resolution. "10m", "50m" and "110m" are accepted.
            However, not all datasets will have all 3 resolutions available.

    Keyword Args:
        dir_override: Optional cache directory override. This takes precedence over the
            ``NATURAL_EARTH_CACHE_DIR`` environment variable.
        error_mode: Error handling mode. Default is raise. Upon error:
            ``"ignore"`` returns None (note: use with caution),
            ``"raise"`` raises the error,
            and ``"return"`` returns the exception object.
        user_logger: Allow user to pass in their own logger to use instead of default.

    Returns:
        A GeoPandas ``GeoDataFrame`` loaded from the cached shapefile.

    """
    logger = user_logger or fallback_logger
    try:
        validate_error_mode(error_mode)
        validate_res(res)

        data_dir: Path = get_cache_dir(dir_override)
        data_dir.mkdir(parents=True, exist_ok=True)

        url: str = build_ne_url(category, name, res)
        zip_path: Path = build_ne_zip_path(data_dir, name, res)
        extract_dir: Path = build_ne_extract_dir(data_dir, name, res)
        shp_file: Path = build_ne_shp_path(data_dir, name, res)

        download_ne_data(
            url=url,
            extract_dir=extract_dir,
            name=name,
            res=res,
            zip_path=zip_path,
            shp_file=shp_file,
            logger=logger,
        )

        return gpd.read_file(shp_file)
    except Exception as error:
        logger.error(
            "ne-loader: error caught fetching data with get_natural_earth():%s",
            error,
        )
        return error_handler(error, error_mode)


def download_ne_data(
    url: str,
    extract_dir: Path,
    name: str,
    res: Resolution,
    zip_path: Path,
    shp_file: Path,
    logger: logging.Logger,
) -> None:
    """Download and extract a dataset when the expected shapefile is absent."""
    _download_dataset(
        url=url,
        zip_path=zip_path,
        extract_dir=extract_dir,
        expected_file=shp_file,
        logger=logger,
        error_mode="raise",
        log_name=f"{name} ({res})",
    )


def validate_res(res: Resolution) -> None:
    """Validate the resolution against "10m", "50m", "110m".

    Args:
        res (Resolution): The resolution to be validated.

    Raises:
        ValueError: If res is invalid, raises ValueError.

    """
    if res not in ("10m", "50m", "110m"):
        raise ValueError(
            f"Invalid resolution: {res}.\n"
            'Resolution must be one of ("10m", "50m", "110m")'
        )
