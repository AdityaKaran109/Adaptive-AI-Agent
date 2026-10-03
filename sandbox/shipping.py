"""The code under test in the agent's sandbox task."""

from __future__ import annotations


def shipping_cost(weight_kg: float, express: bool = False) -> float:
    """Flat 4.50 base, 1.20 per kg, doubled for express. Free over 50 kg."""
    if weight_kg <= 0:
        raise ValueError("weight must be positive")
    if weight_kg > 50:
        return 0.0
    cost = 4.50 + 1.20 * weight_kg
    return round(cost * 2 if express else cost, 2)
