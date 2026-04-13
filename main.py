#!/usr/bin/env python3
"""
Python EDA – Analog Circuit Designer
======================================
Entry point.  Run:   python main.py
                or:  python main.py --batch examples/ce_example.json
"""

import sys
import os
import argparse
import json

# Make sure the project root is on sys.path
sys.path.insert(0, os.path.dirname(__file__))

from ui.interface import welcome_banner, choose_circuit, collect_params
from core.controller import DesignController
from core.models import DesignSpec


def run_interactive(output_dir: str = "output"):
    welcome_banner()
    circuit_type = choose_circuit()
    spec = collect_params(circuit_type)
    controller = DesignController(output_dir=output_dir)
    result = controller.run(spec)
    print(result.performance_summary())


def run_batch(json_path: str, output_dir: str = "output"):
    """Non-interactive mode for scripting / CI."""
    with open(json_path) as f:
        data = json.load(f)
    spec = DesignSpec(
        circuit_type=data["circuit_type"],
        params=data.get("params", {}),
    )
    controller = DesignController(output_dir=output_dir)
    result = controller.run(spec)
    print(result.performance_summary())
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Python EDA – Analog Circuit Designer")
    parser.add_argument("--batch", metavar="JSON", help="Run in batch mode from JSON spec")
    parser.add_argument("--output", default="output", help="Output directory (default: ./output)")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    if args.batch:
        run_batch(args.batch, output_dir=args.output)
    else:
        run_interactive(output_dir=args.output)
