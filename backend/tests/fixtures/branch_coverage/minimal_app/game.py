"""Fixture function with 3 branches — used by call-graph + coverage tests."""


def validate_letter(letter: str) -> str:
    if not letter:
        raise ValueError("empty")
    if len(letter) != 1:
        raise ValueError("not a single character")
    if not letter.isalpha():
        raise ValueError("not alphabetic")
    return letter.lower()
