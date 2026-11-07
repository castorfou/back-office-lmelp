"""Tests du package back_office_lmelp."""

import back_office_lmelp as package


def test_package_importable() -> None:
    """Le package s'importe depuis src/."""
    assert package.__name__ == "back_office_lmelp"
