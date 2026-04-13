"""
UI layer: handles all user interaction.

  - Displays menu of available circuit types
  - Dynamically prompts ONLY the parameters relevant to the chosen circuit
  - Validates and coerces input
  - Returns a populated DesignSpec
"""

from core.models import DesignSpec
from circuits.registry import CIRCUIT_REGISTRY


# ── Parameter schemas ─────────────────────────────────────────────────
# Each entry:  (key, prompt_text, type, default, unit, min, max)
_COMMON_PARAMS = [
    ("vcc",             "Supply voltage VCC",       float, 12.0,  "V",   2.0,  30.0),
    ("load_resistance", "Load resistance RL",        float, 10e3,  "Ω",   100,  1e7),
    ("frequency",       "Operating frequency",       float, 1e3,   "Hz",  1.0,  1e8),
]

_SCHEMA: dict[str, list] = {
    "common_emitter": [
        ("vcc",             "Supply voltage VCC",         float, 12.0,  "V",   2.0,  30.0),
        ("gain",            "Target voltage gain |Av|",   float, 50.0,  "V/V", 1.0,  500.0),
        ("load_resistance", "Load resistance RL",         float, 10e3,  "Ω",   100,  1e7),
        ("frequency",       "Operating frequency",        float, 1e3,   "Hz",  1.0,  1e8),
    ],
    "voltage_divider_bias": [
        ("vcc",              "Supply voltage VCC",        float, 12.0,  "V",   2.0,  30.0),
        ("gain",             "Target voltage gain |Av|",  float, 100.0, "V/V", 1.0,  500.0),
        ("load_resistance",  "Load resistance RL",        float, 10e3,  "Ω",   100,  1e7),
        ("source_resistance","Source resistance RS",      float, 600.0, "Ω",   0,    100e3),
        ("stability_factor", "Max stability factor S",    float, 10.0,  "–",   1.0,  20.0),
        ("frequency",        "Operating frequency",       float, 1e3,   "Hz",  1.0,  1e8),
    ],
    "rc_filter": [
        ("cutoff_frequency", "Cutoff frequency fc",       float, 1e3,   "Hz",  0.001, 1e8),
        ("filter_type",      "Filter type (low_pass / high_pass)", str, "low_pass", "", None, None),
        ("load_resistance",  "Load resistance RL",        float, 10e3,  "Ω",   100,  1e7),
    ],
}

CIRCUIT_NAMES = {
    "common_emitter":       "Common-Emitter NPN Amplifier",
    "voltage_divider_bias": "Voltage-Divider-Bias CE Amplifier",
    "rc_filter":            "RC Filter (Low-Pass / High-Pass)",
}


# ── Public API ───────────────────────────────────────────────────────

def welcome_banner():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║         Python EDA – Analog Circuit Designer         ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()


def choose_circuit() -> str:
    """Interactive circuit-type selection menu."""
    keys = list(CIRCUIT_REGISTRY.keys())
    print("  Available circuit types:")
    for i, key in enumerate(keys, 1):
        label = CIRCUIT_NAMES.get(key, key)
        print(f"    [{i}] {label}")
    print()

    while True:
        raw = input("  Select circuit [1-{}]: ".format(len(keys))).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(keys):
            return keys[int(raw) - 1]
        # also accept type name directly
        if raw in keys:
            return raw
        print(f"  ✗ Invalid choice '{raw}'. Enter a number 1–{len(keys)}.")


def collect_params(circuit_type: str) -> DesignSpec:
    """
    Prompt the user for ONLY the parameters required by circuit_type.
    Returns a DesignSpec with validated values.
    """
    schema = _SCHEMA.get(circuit_type, [])
    params: dict = {}

    print(f"\n  Configure: {CIRCUIT_NAMES.get(circuit_type, circuit_type)}")
    print("  (Press Enter to accept the default value shown in [brackets])\n")

    for key, prompt, dtype, default, unit, vmin, vmax in schema:
        unit_str = f" {unit}" if unit else ""
        default_str = _fmt_default(default, dtype)
        full_prompt = f"    {prompt}{unit_str} [{default_str}]: "

        while True:
            raw = input(full_prompt).strip()
            if raw == "":
                value = default
                break
            try:
                value = dtype(raw)
            except ValueError:
                print(f"      ✗ Expected {dtype.__name__}, got '{raw}'")
                continue

            # Range validation (only for numeric types)
            if dtype in (int, float) and vmin is not None and vmax is not None:
                if not (vmin <= value <= vmax):
                    print(f"      ✗ Value must be in [{vmin}, {vmax}]")
                    continue
            # String validation for filter_type
            if key == "filter_type" and value not in ("low_pass", "high_pass"):
                print("      ✗ Enter 'low_pass' or 'high_pass'")
                continue
            break

        params[key] = value
        print(f"      ✓ {key} = {value}{unit_str}")

    print()
    return DesignSpec(circuit_type=circuit_type, params=params)


# ── Helpers ──────────────────────────────────────────────────────────

def _fmt_default(val, dtype) -> str:
    if dtype == float:
        if val >= 1e6:
            return f"{val/1e6:.3g}M"
        elif val >= 1e3:
            return f"{val/1e3:.3g}k"
        elif val <= 1e-6:
            return f"{val:.2e}"
        else:
            return f"{val:.4g}"
    return str(val)
