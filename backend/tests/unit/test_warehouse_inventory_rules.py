import pytest

from app.modules.inventory.rules import StockStatus, coverage_ratio, shortfall, stock_status
from app.modules.warehouses.rules import UtilizationLevel, utilization_level, utilization_pct


@pytest.mark.parametrize(
    ("pct", "level"),
    [
        (0.0, UtilizationLevel.NORMAL),
        (84.9, UtilizationLevel.NORMAL),
        (85.0, UtilizationLevel.HIGH),  # boundaries are inclusive
        (94.9, UtilizationLevel.HIGH),
        (95.0, UtilizationLevel.CRITICAL),
        (100.0, UtilizationLevel.CRITICAL),
    ],
)
def test_utilization_level_boundaries(pct: float, level: UtilizationLevel) -> None:
    assert utilization_level(pct) == level


def test_utilization_pct() -> None:
    assert utilization_pct(345, 360) == pytest.approx(95.8333, rel=1e-4)


@pytest.mark.parametrize(
    ("available", "threshold", "status"),
    [
        (0, 10, StockStatus.OUT_OF_STOCK),
        (1, 10, StockStatus.LOW),
        (10, 10, StockStatus.LOW),  # at the threshold means reorder now
        (11, 10, StockStatus.OK),
        (0, 0, StockStatus.OUT_OF_STOCK),
        (5, 0, StockStatus.OK),
    ],
)
def test_stock_status(available: int, threshold: int, status: StockStatus) -> None:
    assert stock_status(available, threshold) == status


def test_coverage_ratio_handles_missing_threshold() -> None:
    assert coverage_ratio(5, 10) == 0.5
    assert coverage_ratio(5, 0) is None


@pytest.mark.parametrize(
    ("available", "threshold", "expected"), [(4, 10, 7), (10, 10, 1), (20, 10, 0)]
)
def test_shortfall(available: int, threshold: int, expected: int) -> None:
    assert shortfall(available, threshold) == expected
