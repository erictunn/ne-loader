"""Tests for the generalized dataset downloader."""

import io
import logging
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
import requests

from ne_loader.data_loader import (
    build_dataset_extract_dir,
    build_dataset_file_path,
    build_dataset_zip_path,
    download_dataset,
)


class MockResponse:
    """Mock successful response object for a requests.get call."""

    def __init__(self, data: bytes) -> None:
        """Store response bytes for chunked streaming."""
        self.data = data

    def raise_for_status(self) -> None:
        """Match requests.Response.raise_for_status for a successful response."""
        return None

    def iter_content(self, chunk_size: int = 8192) -> Iterator[bytes]:
        """Yield response bytes in in the same shape as requests.Response."""
        for start in range(0, len(self.data), chunk_size):
            yield self.data[start : start + chunk_size]


def _mock_zip_bytes(member: str, content: bytes = b"data") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        zip_file.writestr(member, content)
    return buffer.getvalue()


def test_download_dataset_downloads_and_extracts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Download and extract a generalized dataset."""
    response_data = _mock_zip_bytes("naturalearth_rates.json")
    requested: list[str] = []

    def mock_get(url: str, stream: bool, timeout: int) -> MockResponse:
        requested.append(url)
        assert stream is True
        assert timeout == 10
        return MockResponse(response_data)

    monkeypatch.setattr(requests, "get", mock_get)

    result = download_dataset(
        "naturalearth",
        "10m/finance/rates.zip",
        file_extension="json",
        dir_override=tmp_path,
        user_logger=logging.getLogger("testing"),
    )

    assert result is None

    assert requested == ["https://naciscdn.org/naturalearth/10m/finance/rates.zip"]

    extracted = build_dataset_file_path(
        "naturalearth",
        "rates",
        build_dataset_extract_dir(tmp_path, "naturalearth", "rates"),
        ".json",
    )
    assert extracted.read_bytes() == b"data"

    assert not build_dataset_zip_path(tmp_path, "naturalearth", "rates").exists()


def test_download_dataset_uses_cached_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure already cached files are not downloaded."""
    extract_dir = build_dataset_extract_dir(tmp_path, "naturalearth", "rates")
    extracted = build_dataset_file_path("naturalearth", "rates", extract_dir, "json")
    extracted.parent.mkdir(parents=True)
    extracted.write_bytes(b"cached")

    def unexpected_get(*args: object, **kwargs: object) -> MockResponse:
        raise AssertionError("Cached datasets must not be downloaded")

    monkeypatch.setattr(requests, "get", unexpected_get)

    assert (
        download_dataset(
            "naturalearth",
            "rates.zip",
            file_extension=".json",
            dir_override=tmp_path,
        )
        is None
    )


class BadResponse:
    """Mock unsuccessful response for a requests.get call."""

    def raise_for_status(self) -> None:
        """Mock the unsuccessful response."""
        raise requests.exceptions.HTTPError("404 Client Error")


def test_download_dataset_returns_error_and_cleans_up(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return errors according to error_mode and remove partial artifacts."""
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: BadResponse())

    result = download_dataset(
        "naturalearth",
        "rates.zip",
        file_extension="json",
        dir_override=tmp_path,
        error_mode="return",
    )

    assert isinstance(result, requests.exceptions.HTTPError)
    assert not build_dataset_zip_path(tmp_path, "naturalearth", "rates").exists()
    assert not build_dataset_extract_dir(tmp_path, "naturalearth", "rates").exists()
