"""Handles downloading general datasets."""

import contextlib
import logging
import shutil
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Literal, TypeVar, overload
from urllib.parse import urlsplit

import requests

from .cacher import PathLike, get_cache_dir
from .error_handler import ErrorMode, error_handler, validate_error_mode

fallback_logger: logging.Logger = logging.getLogger(__name__)
T = TypeVar("T")
DatasetReader = Callable[[Path], T]

dataset_providers: dict[str, str] = {
    "naturalearth": "https://naciscdn.org/naturalearth/",
}


def _normalise_extension(file_extension: str) -> str:
    """Return a validated file extension with one leading dot."""
    extension = file_extension.strip()
    if not extension:
        raise ValueError("file_extension must not be empty")
    if "/" in extension or "\\" in extension:
        raise ValueError("file_extension must be a file extension, not a path")
    return f".{extension.lstrip('.')}"


def _dataset_name(path: str) -> str:
    """Return a filesystem-safe dataset name from a provider-relative path."""
    name = Path(urlsplit(path).path).name
    if not name:
        raise ValueError("path must identify a dataset")
    if name.lower().endswith(".zip"):
        name = name[:-4]
    if not name:
        raise ValueError("path must identify a dataset")
    return name


def _build_dataset_url(website: str, path: str) -> str:
    """Build a URL confined to a configured dataset provider.

    Dataset paths are deliberately relative: providers, rather than callers,
    control the scheme and host used for requests.
    """
    parsed_path = urlsplit(path)
    if (
        parsed_path.scheme
        or parsed_path.netloc
        or path.startswith("/")
        or "\\" in parsed_path.path
    ):
        raise ValueError("path must be relative to the configured dataset provider")
    if any(part == ".." for part in PurePosixPath(parsed_path.path).parts):
        raise ValueError("path must not contain parent-directory traversal")
    return f"{website.rstrip('/')}/{path}"


def _extract_archive(archive: zipfile.ZipFile, extract_dir: Path) -> None:
    """Extract an archive while rejecting members outside the cache directory."""
    root = extract_dir.resolve()
    for member in archive.infolist():
        target = (extract_dir / member.filename).resolve()
        try:
            target.relative_to(root)
        except ValueError as error:
            raise ValueError(
                f"Archive member escapes extraction directory: {member.filename!r}"
            ) from error
    archive.extractall(extract_dir)


def build_dataset_zip_path(cache_dir: PathLike, source: str, name: str) -> Path:
    """Build the local cache path for a dataset archive."""
    return Path(cache_dir) / f"{source}_{name}.zip"


def build_dataset_extract_dir(cache_dir: PathLike, source: str, name: str) -> Path:
    """Build the local extraction directory for a dataset."""
    return Path(cache_dir) / f"{source}_{name}"


def build_dataset_file_path(
    source: str,
    name: str,
    extract_dir: PathLike,
    file_extension: str,
) -> Path:
    """Build the expected path of the requested file after extraction."""
    return Path(extract_dir) / f"{source}_{name}{_normalise_extension(file_extension)}"


def _download_dataset(
    *,
    url: str,
    zip_path: Path,
    extract_dir: Path,
    expected_file: Path,
    logger: logging.Logger,
    error_mode: ErrorMode,
    log_name: str = "download_dataset",
) -> Exception | None:
    """Download and extract an archive, using caller-supplied cache paths."""
    if expected_file.exists():
        return None

    try:
        logger.info("ne-loader: Downloading %s...", log_name)
        response = requests.get(url, stream=True, timeout=10, allow_redirects=False)
        response.raise_for_status()

        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zip_path.open("wb") as archive:
            for chunk in response.iter_content(chunk_size=8192):
                archive.write(chunk)

        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            _extract_archive(archive, extract_dir)
        if not expected_file.exists():
            raise FileNotFoundError(
                "Downloaded archive did not contain the expected file: "
                f"{expected_file.name}"
            )
        return None
    except Exception as error:
        logger.error("ne-loader/%s(): error downloading data: %s", log_name, error)
        return error_handler(error, error_mode)
    finally:
        with contextlib.suppress(FileNotFoundError):
            zip_path.unlink()
        if not expected_file.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)


@overload
def download_dataset(
    source: str,
    path: str,
    *,
    file_extension: str,
    dir_override: PathLike | None = None,
    error_mode: Literal["return"],
    user_logger: logging.Logger | None = None,
) -> Exception | None: ...


@overload
def download_dataset(
    source: str,
    path: str,
    *,
    file_extension: str,
    dir_override: PathLike | None = None,
    error_mode: Literal["raise", "ignore"] = "raise",
    user_logger: logging.Logger | None = None,
) -> None: ...


@overload
def download_dataset(
    source: str,
    path: str,
    *,
    file_extension: str,
    dir_override: PathLike | None = None,
    error_mode: ErrorMode,
    user_logger: logging.Logger | None = None,
) -> Exception | None: ...


def download_dataset(
    source: str,
    path: str,
    *,
    file_extension: str,
    dir_override: PathLike | None = None,
    error_mode: ErrorMode = "raise",
    user_logger: logging.Logger | None = None,
) -> Exception | None:
    """Download, extract and cache a dataset.

    Args:
        source: The source of the dataset, e.g. Natural Earth or the IMF.
        path: The path to the dataset within the source website.

    Keyword Args:
        file_extension: If a file extension cannot be determined,
            it will fall back to this.
        dir_override: Optional cache directory override. This takes precedence over the
            ``NATURAL_EARTH_CACHE_DIR`` environment variable.
        error_mode: Error handling mode. Default is raise. Upon error:
            ``"ignore"`` returns None (note: use with caution),
            ``"raise"`` raises the error,
            and ``"return"`` returns the exception object.
        user_logger: Allow user to pass in their own logger to use instead of default.

    """
    logger = user_logger or fallback_logger
    zip_path: Path | None = None
    extract_dir: Path | None = None
    expected_file: Path | None = None

    try:
        validate_error_mode(error_mode)
        try:
            website = dataset_providers[source]
        except KeyError as error:
            raise ValueError(f"Unknown dataset source: {source!r}") from error

        name = _dataset_name(path)
        extension = _normalise_extension(file_extension)
        cache_dir = get_cache_dir(path_override=dir_override)
        zip_path = build_dataset_zip_path(cache_dir, source, name)
        extract_dir = build_dataset_extract_dir(cache_dir, source, name)
        expected_file = build_dataset_file_path(source, name, extract_dir, extension)

        url = _build_dataset_url(website, path)
        return _download_dataset(
            url=url,
            zip_path=zip_path,
            extract_dir=extract_dir,
            expected_file=expected_file,
            logger=logger,
            error_mode=error_mode,
        )
    except Exception as error:
        logger.error("ne-loader/download_dataset(): error preparing data: %s", error)
        return error_handler(error, error_mode)
    finally:
        if zip_path is not None:
            with contextlib.suppress(FileNotFoundError):
                zip_path.unlink()
        if (
            extract_dir is not None
            and expected_file is not None
            and not expected_file.exists()
        ):
            shutil.rmtree(extract_dir, ignore_errors=True)


@overload
def fetch_dataset(
    source: str,
    path: str,
    *,
    file_extension: str,
    reader: DatasetReader[T],
    dir_override: PathLike | None = None,
    error_mode: Literal["ignore"],
    user_logger: logging.Logger | None = None,
) -> T | None: ...


@overload
def fetch_dataset(
    source: str,
    path: str,
    *,
    file_extension: str,
    reader: DatasetReader[T],
    dir_override: PathLike | None = None,
    error_mode: Literal["raise"] = "raise",
    user_logger: logging.Logger | None = None,
) -> T: ...


@overload
def fetch_dataset(
    source: str,
    path: str,
    *,
    file_extension: str,
    reader: DatasetReader[T],
    dir_override: PathLike | None = None,
    error_mode: Literal["return"],
    user_logger: logging.Logger | None = None,
) -> T | Exception: ...


@overload
def fetch_dataset(
    source: str,
    path: str,
    *,
    file_extension: str,
    reader: DatasetReader[T],
    dir_override: PathLike | None = None,
    error_mode: ErrorMode,
    user_logger: logging.Logger | None = None,
) -> T | Exception | None: ...


def fetch_dataset(
    source: str,
    path: str,
    *,
    file_extension: str,
    reader: DatasetReader[T],
    dir_override: PathLike | None = None,
    error_mode: ErrorMode = "raise",
    user_logger: logging.Logger | None = None,
) -> T | Exception | None:
    """Read a cached dataset with ``reader``; never download it.

    The dataset must already have been downloaded and extracted into the cache.
    The reader receives the cached file path and is responsible for parsing it
    into the desired result type.

    Args:
        source: The source of the dataset, e.g. Natural Earth or the IMF.
        path: The path to the dataset within the source website. The final path
            component is used to identify the cached dataset.

    Keyword Args:
        file_extension: The extension of the cached dataset file, with or
            without a leading dot.
        reader: A callable that receives the cached dataset path and returns
            the parsed dataset.
        dir_override: Optional cache directory override. This takes precedence
            over the ``NATURAL_EARTH_CACHE_DIR`` environment variable.
        error_mode: Error handling mode. Default is raise. Upon error:
            ``"ignore"`` returns None (note: use with caution),
            ``"raise"`` raises the error,
            and ``"return"`` returns the exception object.
        user_logger: Allow user to pass in their own logger to use instead of
            default.

    Returns:
        The value returned by ``reader``. Depending on ``error_mode``, an error
        may instead return None or the exception object.

    """
    logger = user_logger or fallback_logger
    try:
        validate_error_mode(error_mode)
        if source not in dataset_providers:
            raise ValueError(f"Unknown dataset source: {source!r}")
        name = _dataset_name(path)
        cache_dir = get_cache_dir(path_override=dir_override)
        extract_dir = build_dataset_extract_dir(cache_dir, source, name)
        cached_file = build_dataset_file_path(
            source,
            name,
            extract_dir,
            file_extension,
        )
        if not cached_file.exists():
            raise FileNotFoundError(f"Dataset is not cached: {cached_file}")
        return reader(cached_file)
    except Exception as error:
        logger.error("ne-loader/fetch_dataset(): error fetching data: %s", error)
        return error_handler(error, error_mode)
