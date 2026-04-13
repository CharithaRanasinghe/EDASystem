"""
E-series standard component value utilities.

Supports E24 (resistors) and E12 (capacitors) series.
nearest_e24(val)     → nearest E24 resistor value
nearest_e12_cap(val) → nearest E12 capacitor value
"""

import math

# ── E24 series (24 values per decade) ───────────────────────────────
_E24 = [
    1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0,
    2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3,
    4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1,
]

# ── E12 series (12 values per decade) ───────────────────────────────
_E12 = [
    1.0, 1.2, 1.5, 1.8, 2.2, 2.7,
    3.3, 3.9, 4.7, 5.6, 6.8, 8.2,
]


def _nearest_in_series(value: float, series: list[float]) -> float:
    """Return the nearest standard value from the given E-series."""
    if value <= 0:
        raise ValueError(f"Component value must be > 0, got {value}")

    # Normalise to the decade
    decade = 10 ** math.floor(math.log10(value))
    normalised = value / decade

    # Find closest in the base series
    best = min(series, key=lambda s: abs(s - normalised))

    # Handle wrap-around (e.g. 9.5 → 10.0 which is next decade)
    next_decade = 10 ** math.ceil(math.log10(value + 1e-30))
    if abs(next_decade / decade - normalised) < abs(best - normalised):
        return next_decade

    return best * decade


def nearest_e24(value: float) -> float:
    """Return nearest E24 standard resistor value."""
    return _nearest_in_series(value, _E24)


def nearest_e12_cap(value: float) -> float:
    """Return nearest E12 standard capacitor value."""
    return _nearest_in_series(value, _E12)


# ── Self-test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    for v in [100, 1234, 4750, 9999, 47200, 1e6]:
        print(f"  {v:>10.0f} Ω  →  E24 = {nearest_e24(v):.4g} Ω")
    print()
    for v in [1e-9, 4.7e-9, 100e-9, 10e-6, 220e-6]:
        print(f"  {v:.2e} F  →  E12 = {nearest_e12_cap(v):.2e} F")
