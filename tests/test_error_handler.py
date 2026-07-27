"""Basic tests for error_handler.py helpers."""

import pytest

from ne_loader.error_handler import error_handler, validate_error_mode


def test_validate_error_mode_accepts_supported_modes() -> None:
    """Tests that supported error modes pass validation."""
    for error_mode in ("ignore", "raise", "return"):
        validate_error_mode(error_mode)


def test_validate_error_mode_rejects_unsupported_mode() -> None:
    """Tests that unsupported error modes raise a helpful error."""
    with pytest.raises(ValueError, match="Invalid error_mode: 'quiet'"):
        validate_error_mode("quiet")  # type: ignore


def test_error_handler_ignores_error() -> None:
    """Tests that ignore mode returns None."""
    error = RuntimeError("boom")

    assert error_handler(error, "ignore") is None


def test_error_handler_returns_error() -> None:
    """Tests that return mode returns the original error object."""
    error = RuntimeError("boom")

    assert error_handler(error, "return") is error


def test_error_handler_raises_error() -> None:
    """Tests that raise mode re-raises the original error object."""
    error = RuntimeError("boom")

    with pytest.raises(RuntimeError) as exc_info:
        error_handler(error, "raise")

    assert exc_info.value is error
