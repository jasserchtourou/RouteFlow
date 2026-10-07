"""Delivery performance definitions (pure functions)."""


def on_time_rate(on_time: int, delivered: int) -> float | None:
    """Percentage of deliveries made by the time promised to the customer (None if none).

    "On time" = shipment.actual_delivery <= order.promised_delivery_at. Deliberately not the
    shipment ETA: delay reports move the ETA, so measuring against it would let late
    deliveries count as on time.
    """
    if delivered == 0:
        return None
    return round(on_time * 100.0 / delivered, 1)


def change_in_points(current: float | None, previous: float | None) -> float | None:
    """Difference in percentage points (e.g. 92.0 vs 95.5 -> -3.5)."""
    if current is None or previous is None:
        return None
    return round(current - previous, 1)
