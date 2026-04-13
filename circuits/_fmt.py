"""
Shared SPICE netlist value formatters.
"""


def _fmt_r(val: float) -> str:
    """Format a resistance for SPICE (e.g. 4.7k, 180k, 1.5Meg)."""
    if val >= 1e6:
        return f"{val/1e6:.3g}Meg"
    elif val >= 1e3:
        return f"{val/1e3:.3g}k"
    else:
        return f"{val:.0f}"


def _fmt_c(val: float) -> str:
    """Format a capacitance for SPICE (e.g. 100n, 10u, 4.7p)."""
    if val >= 1e-3:
        return f"{val*1e3:.3g}m"
    elif val >= 1e-6:
        return f"{val*1e6:.3g}u"
    elif val >= 1e-9:
        return f"{val*1e9:.3g}n"
    elif val >= 1e-12:
        return f"{val*1e12:.3g}p"
    else:
        return f"{val:.3e}"
