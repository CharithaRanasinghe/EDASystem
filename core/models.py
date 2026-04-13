"""
Core data models shared across the EDA system.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class DesignSpec:
    """User-provided design specifications."""
    circuit_type: str
    params: Dict[str, float] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)


@dataclass
class DesignResult:
    """Computed design result after optimization."""
    circuit_type: str
    component_values: Dict[str, float] = field(default_factory=dict)
    operating_point: Dict[str, float] = field(default_factory=dict)
    achieved_performance: Dict[str, float] = field(default_factory=dict)
    target_performance: Dict[str, float] = field(default_factory=dict)
    optimization_error: float = 0.0
    netlist_path: Optional[str] = None
    warnings: list = field(default_factory=list)

    def performance_summary(self) -> str:
        lines = ["\n" + "=" * 55]
        lines.append("  DESIGN PERFORMANCE SUMMARY")
        lines.append("=" * 55)

        lines.append("\n  Component Values:")
        for k, v in self.component_values.items():
            lines.append(f"    {k:20s} = {_format_value(v)}")

        if self.operating_point:
            lines.append("\n  Operating Point:")
            for k, v in self.operating_point.items():
                lines.append(f"    {k:20s} = {_format_value(v)}")

        lines.append("\n  Performance:")
        all_keys = set(self.achieved_performance) | set(self.target_performance)
        for k in sorted(all_keys):
            achieved = self.achieved_performance.get(k)
            target = self.target_performance.get(k)
            if achieved is not None and target is not None:
                err_pct = abs(achieved - target) / abs(target) * 100 if target != 0 else 0
                lines.append(
                    f"    {k:20s}  target={_format_value(target):>12s}  "
                    f"achieved={_format_value(achieved):>12s}  "
                    f"err={err_pct:.1f}%"
                )
            elif achieved is not None:
                lines.append(f"    {k:20s}  achieved={_format_value(achieved):>12s}")

        lines.append(f"\n  Optimization residual error: {self.optimization_error:.6f}")

        if self.warnings:
            lines.append("\n  ⚠ Warnings:")
            for w in self.warnings:
                lines.append(f"    - {w}")

        if self.netlist_path:
            lines.append(f"\n  Netlist saved to: {self.netlist_path}")

        lines.append("=" * 55 + "\n")
        return "\n".join(lines)


def _format_value(v) -> str:
    """Smart magnitude formatting for circuit values (no unit suffix)."""
    if v is None:
        return "N/A"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    abs_v = abs(v)
    if abs_v == 0:
        return "0"
    if abs_v >= 1e6:
        return f"{v/1e6:.4g} M"
    elif abs_v >= 1e3:
        return f"{v/1e3:.4g} k"
    elif abs_v >= 1:
        return f"{v:.4g}"
    elif abs_v >= 1e-3:
        return f"{v*1e3:.4g} m"
    elif abs_v >= 1e-6:
        return f"{v*1e6:.4g} µ"
    elif abs_v >= 1e-9:
        return f"{v*1e9:.4g} n"
    elif abs_v >= 1e-12:
        return f"{v*1e12:.4g} p"
    else:
        return f"{v:.4e}"
