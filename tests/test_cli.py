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


def test_cli_list_output() -> None:
    """Tests list command output before and after adding a directory."""
    runner = CliRunner()
    result_a = runner.invoke(
        cli.main,
        ["list"],
    )
    cache_dir = get_cache_dir()
    pathlib.Path(cache_dir / "test").mkdir(exist_ok=True)

    result_b = runner.invoke(
        cli.main,
        ["list"],
    )
    assert "test" in result_b.output
    assert result_a.exception is None
    assert result_b.exception is None
