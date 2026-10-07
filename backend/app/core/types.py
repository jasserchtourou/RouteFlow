"""Reusable constrained types for request schemas."""

from typing import Annotated

from pydantic import StringConstraints


def text(max_length: int) -> StringConstraints:
    """Trimmed, non-empty string of bounded length."""
    return StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length)


SearchTerm = Annotated[str, text(80)]
Place = Annotated[str, text(80)]  # city / location name
WarehouseCode = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1, max_length=16)
]
