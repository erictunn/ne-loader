"""Minimal tests for the CLI entrypoint."""

import pathlib

import pytest
from click.testing import CliRunner

import ne_loader.cli as cli
from ne_loader.cacher import get_cache_dir
from ne_loader.map_loader import Resolution


def test_cli_delegates_to_get_natural_earth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the CLI forwards arguments properly to map_loader.get_natural_earth."""
    called = {}

    def fake_get(category: str, name: str, res: Resolution):
        called["args"] = (category, name, res)

    monkeypatch.setattr(cli.map_loader, "get_natural_earth", fake_get)

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["download", "Cultural", "admin_0_countries", "--res", "50m"],
    )

    assert result.exit_code == 0
    assert called["args"] == ("Cultural", "admin_0_countries", "50m")


def test_cli_where_errors() -> None:
    """Ensure CLI where command returns without error."""
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["where"],
    )

    assert result.exit_code == 0
    assert result.exception is None


def test_cli_where_output() -> None:
    """Ensure where command output is the same as get_cache_dir()."""
    true_cache_dir = str(get_cache_dir()).strip()

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["where"],
    )
    assert true_cache_dir == str(result.output).strip()


def test_cli_list_empty_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """List succeeds and prints an empty line when nothing is cached."""
    monkeypatch.setattr(cli, "get_cache_dir", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli.main, ["list"])

    assert result.exit_code == 0
    assert result.exception is None
    assert result.output == "\n"


def test_cli_list_missing_cache_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """List succeeds before the cache directory has been created."""
    monkeypatch.setattr(cli, "get_cache_dir", lambda: tmp_path / "missing-cache")

    result = CliRunner().invoke(cli.main, ["list"])

    assert result.exit_code == 0
    assert result.output == "\n"


def test_cli_list_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """List includes cached directories and excludes other cache entries."""
    monkeypatch.setattr(cli, "get_cache_dir", lambda: tmp_path)
    (tmp_path / "countries").mkdir()
    (tmp_path / "rivers").mkdir()
    (tmp_path / "not-a-directory").touch()

    result = CliRunner().invoke(cli.main, ["list"])

    assert result.exit_code == 0
    assert result.exception is None
    listed_entries = result.output.strip().split(", ")
    assert len(listed_entries) == 2
    assert set(listed_entries) == {"countries", "rivers"}
