"""Inventory business definitions. The model's SQL expressions mirror these functions; a test
checks that Python and SQL always agree."""

from enum import StrEnum


class StockStatus(StrEnum):
    OK = "OK"
    LOW = "LOW"  # available stock at or below the reorder threshold: reorder now
    OUT_OF_STOCK = "OUT_OF_STOCK"  # nothing available to pick


def available_quantity(quantity: int, reserved: int) -> int:
    """Stock that can still be promised to new orders."""
    return quantity - reserved


def stock_status(available: int, reorder_threshold: int) -> StockStatus:
    if available <= 0:
        return StockStatus.OUT_OF_STOCK
    if available <= reorder_threshold:
        return StockStatus.LOW
    return StockStatus.OK


def coverage_ratio(available: int, reorder_threshold: int) -> float | None:
    """Available stock relative to the reorder threshold (1.0 = exactly at threshold).

    Lower is more urgent. None when no threshold is configured.
    """
    if reorder_threshold == 0:
        return None
    return available / reorder_threshold


def shortfall(available: int, reorder_threshold: int) -> int:
    """Units needed to bring available stock back above the reorder threshold."""
    return max(0, reorder_threshold - available + 1)
