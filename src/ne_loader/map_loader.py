"""Handles downloading and fetching of NE data."""

import contextlib
import logging
import shutil
import zipfile
from pathlib import Path
from typing import Literal, overload

import geopandas as gpd
import requests

from .cacher import PathLike, get_cache_dir
from .error_handler import ErrorMode, error_handler, validate_error_mode

fallback_logger: logging.Logger = logging.getLogger(__name__)

Resolution = Literal["10m", "50m", "110m"]

Dataset_providers = {"naturalearth": "https://naciscdn.org/naturalearth/"}


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
    if shp_file.exists():
        return

    logger.info(f"ne-loader: Downloading {name} ({res})...")

    try:
        response: requests.Response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()

        with zip_path.open("wb") as zip_file:
            chunk: bytes
            for chunk in response.iter_content(chunk_size=8192):
                zip_file.write(chunk)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
        return None

    except requests.exceptions.HTTPError as error:
        logger.error(
            "ne-loader/download_ne_data(): "
            "A HTTP error occurred while attempting to fetch data: %s\n"
            "This may cause an error when attempting to load the data.",
            error,
        )
        raise
    except requests.exceptions.RequestException as error:
        logger.error(
            "ne-loader/download_ne_data(): "
            "A request error occurred while attempting to fetch data: %s\n"
            "This may cause an error when attempting to load the data.",
            error,
        )
        raise

    finally:
        with contextlib.suppress(FileNotFoundError):
            zip_path.unlink()

        expected_extract_dir = build_ne_filename(name, res, suffix="")
        if not shp_file.exists() and extract_dir.name == expected_extract_dir:
            shutil.rmtree(extract_dir, ignore_errors=True)


def download_dataset(
    source: str,
    path: str,
    *,
    dir_override: PathLike,
    error_mode: ErrorMode = "raise",
    user_logger: logging.Logger | None = None,
) -> None:
    """Download, extract and cache a dataset.

    Args:
        source: The source of the dataset, e.g. natural earth or the IMF.
        path: The path to the dataset within the source website.

    Keyword Args:
        dir_override: Optional cache directory override. This takes precedence over the
            ``NATURAL_EARTH_CACHE_DIR`` environment variable.
        error_mode: Error handling mode. Default is raise. Upon error:
            ``"ignore"`` returns None (note: use with caution),
            ``"raise"`` raises the error,
            and ``"return"`` returns the exception object.
        user_logger: Allow user to pass in their own logger to use instead of default.

    """
    logger = user_logger or fallback_logger
    try:
        validate_error_mode(error_mode)

        website: str = Dataset_providers[source]
        url = website + "/" + path
        cache_dir: Path = get_cache_dir(path_override=dir_override)

        response: requests.Response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()

        with zip_path.open("wb") as zip_file:
            chunk: bytes
            for chunk in response.iter_content(chunk_size=8192):
                zip_file.write(chunk)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(cache_dir)
        return None

    except requests.exceptions.HTTPError as error:
        logger.error(
            "ne-loader/download_ne_data(): "
            "A HTTP error occurred while attempting to fetch data: %s\n"
            "This may cause an error when attempting to load the data.",
            error,
        )
        raise
    except requests.exceptions.RequestException as error:
        logger.error(
            "ne-loader/download_ne_data(): "
            "A request error occurred while attempting to fetch data: %s\n"
            "This may cause an error when attempting to load the data.",
            error,
        )
        raise
    finally:
        with contextlib.suppress(FileNotFoundError):
            zip_path.unlink()

        expected_extract_dir = None #TODO fix
        if not shp_file.exists() and extract_dir.name == expected_extract_dir:
            shutil.rmtree(extract_dir, ignore_errors=True)


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
