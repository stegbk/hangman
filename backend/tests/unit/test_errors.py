"""Unit tests for HangmanError and helpers. Middleware/handler tests live in integration."""

from hangman.errors import HangmanError, build_error_envelope


def test_hangman_error_carries_fields() -> None:
    e = HangmanError(
        code="GAME_NOT_FOUND",
        http_status=404,
        message="no such game",
        details=[{"field": "id"}],
    )
    assert e.code == "GAME_NOT_FOUND"
    assert e.http_status == 404
    assert e.message == "no such game"
    assert e.details == [{"field": "id"}]


def test_hangman_error_defaults_details_to_empty_list() -> None:
    e = HangmanError(code="X", http_status=400, message="m")
    assert e.details == []


def test_build_error_envelope_shape() -> None:
    env = build_error_envelope(code="X", message="m", request_id="req_1")
    assert env == {
        "error": {
            "code": "X",
            "message": "m",
            "details": [],
            "request_id": "req_1",
        }
    }


def test_build_error_envelope_includes_details() -> None:
    env = build_error_envelope(code="X", message="m", request_id=None, details=[{"a": 1}])
    assert env["error"]["details"] == [{"a": 1}]
    assert env["error"]["request_id"] is None
