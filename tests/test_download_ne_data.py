"""Tests for natural earth data downloader functions."""

import io
import logging
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
import requests

from ne_loader.map_loader import Resolution, build_ne_filename, download_ne_data


def _mock_zip_bytes(name: str, res: str) -> bytes:
    """Build an in-memory Natural Earth zip file containing one shapefile."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        zip_file.writestr(
            build_ne_filename(name, res, suffix=".shp"),
            b"mock shp content",
        )
    return buffer.getvalue()


class MockResponse:
    """Mock successful response object for the downloader's requests.get call."""

    def __init__(self, data: bytes) -> None:
        """Store response bytes for chunked streaming."""
        self._data = data

    def raise_for_status(self) -> None:
        """Match requests.Response.raise_for_status for a successful response."""
        return None

    def iter_content(self, chunk_size: int = 8192) -> Iterator[bytes]:
        """Yield response bytes in the same shape as requests.Response."""
        for start in range(0, len(self._data), chunk_size):
            yield self._data[start : start + chunk_size]


url = "https://example.org/fake.zip"
name = "admin_0_countries"
res: Resolution = "10m"
logger = logging.getLogger("testing")


def test_download_ne_data_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify download_ne_data writes the extracted shapefile on success."""
    mocked_zip = _mock_zip_bytes(name, res)

    def mock_get(request_url: str, stream: bool, timeout: int) -> MockResponse:
        """Return a fake response and verify the downloader's request options."""
        assert request_url == url
        assert stream is True
        assert timeout == 10
        return MockResponse(mocked_zip)

    monkeypatch.setattr(requests, "get", mock_get)
    base = tmp_path / "ne-cache"
    base.mkdir()
    extract_dir = base / build_ne_filename(name, res, suffix="")
    zip_path = base / build_ne_filename(name, res)
    shp_file = extract_dir / build_ne_filename(name, res, suffix=".shp")

    download_ne_data(
        url=url,
        extract_dir=extract_dir,
        name=name,
        res=res,
        zip_path=zip_path,
        shp_file=shp_file,
        logger=logger,
    )

    assert shp_file.exists()
    assert extract_dir.exists()
    assert not zip_path.exists()


class BadResponse:
    """Mock unsuccessful response for the downloader's requests.get call."""

    def raise_for_status(self) -> None:
        """Mock the unsuccessful response."""
        raise requests.exceptions.HTTPError("404 Client Error")


def test_download_ne_data_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests that download_ne_data leaves no artifacts upon HTTP error."""

    def mock_get(request_url: str, stream: bool, timeout: int) -> BadResponse:
        """Return a fake response and verify the downloader's request options."""
        assert request_url == url
        assert stream is True
        assert timeout == 10
        return BadResponse()

    monkeypatch.setattr(requests, "get", mock_get)

    base = tmp_path / "ne-cache"
    base.mkdir()
    extract_dir = base / build_ne_filename(name, res, suffix="")
    zip_path = base / build_ne_filename(name, res)
    shp_file = extract_dir / build_ne_filename(name, res, suffix=".shp")

    with pytest.raises(requests.exceptions.HTTPError):
        download_ne_data(
            url=url,
            extract_dir=extract_dir,
            name=name,
            res=res,
            zip_path=zip_path,
            shp_file=shp_file,
            logger=logger,
        )

    assert not zip_path.exists()
    assert not extract_dir.exists()
