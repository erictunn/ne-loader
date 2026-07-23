"""Tests for the Natural Earth downloader compatibility wrapper."""

import logging
from pathlib import Path

import pytest

import ne_loader.map_loader as map_loader
from ne_loader.map_loader import Resolution, build_ne_filename, download_ne_data


def test_download_ne_data_delegates_to_shared_downloader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure the legacy wrapper passes its paths to the shared implementation."""
    name = "admin_0_countries"
    res: Resolution = "10m"
    extract_dir = tmp_path / build_ne_filename(name, res, suffix="")
    zip_path = tmp_path / build_ne_filename(name, res)
    shp_file = extract_dir / build_ne_filename(name, res, suffix=".shp")
    calls: list[dict[str, object]] = []

    def fake_download_dataset(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(map_loader, "_download_dataset", fake_download_dataset)

    result = download_ne_data(
        url="https://example.org/fake.zip",
        extract_dir=extract_dir,
        name=name,
        res=res,
        zip_path=zip_path,
        shp_file=shp_file,
        logger=logging.getLogger("testing"),
    )

    assert result is None
    assert calls == [
        {
            "url": "https://example.org/fake.zip",
            "zip_path": zip_path,
            "extract_dir": extract_dir,
            "expected_file": shp_file,
            "logger": logging.getLogger("testing"),
            "error_mode": "raise",
            "log_name": "admin_0_countries (10m)",
        }
    ]
