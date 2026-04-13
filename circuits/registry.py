"""
Central registry mapping circuit-type strings → circuit classes.
To add a new circuit:
  1. Create circuits/my_circuit.py  with a class that extends BaseCircuit
  2. Import it here and add to CIRCUIT_REGISTRY
"""
from circuits.common_emitter import CommonEmitterAmplifier
from circuits.voltage_divider_bias import VoltageDividerBiasAmplifier
from circuits.rc_filter import RCFilter

CIRCUIT_REGISTRY = {
    "common_emitter":        CommonEmitterAmplifier,
    "voltage_divider_bias":  VoltageDividerBiasAmplifier,
    "rc_filter":             RCFilter,
}
