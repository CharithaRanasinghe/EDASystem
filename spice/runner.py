"""
SPICE netlist writer + LTspice subprocess runner.

SpiceRunner.generate(circuit, result)  → writes .cir file, returns path
SpiceRunner.run_ltspice(path)          → tries to invoke LTspice, returns
                                         raw log text or None if unavailable
"""

import os
import subprocess
import platform
from datetime import datetime

from circuits.base import BaseCircuit
from core.models import DesignResult


# Typical LTspice install locations per OS
_LTSPICE_PATHS = {
    "Windows": [
        r"C:\Program Files\LTC\LTspice XVII\XVIIx64.exe",
        r"C:\Program Files (x86)\LTC\LTspiceXVII\XVIIx64.exe",
        r"C:\Users\Public\Documents\LTspiceXVII\XVIIx64.exe",
    ],
    "Darwin": [   # macOS
        "/Applications/LTspice.app/Contents/MacOS/LTspice",
    ],
    "Linux": [
        # Wine-wrapped LTspice
        os.path.expanduser("~/.wine/drive_c/Program Files/LTC/LTspiceXVII/XVIIx64.exe"),
    ],
}


class SpiceRunner:

    def __init__(self, output_dir: str = "."):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    # ── Netlist file generation ──────────────────────────────────────
    def generate(self, circuit: BaseCircuit, result: DesignResult) -> str:
        """
        Ask the circuit for its netlist lines, prepend a header,
        write to <output_dir>/<circuit_type>.cir, return the path.
        """
        lines = self._header(circuit, result)
        lines += circuit.netlist_lines(result)
        lines += self._footer()

        fname = os.path.join(
            self.output_dir,
            f"{result.circuit_type}.cir",
        )
        with open(fname, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

        print(f"[SPICE] Netlist written → {fname}")
        return fname

    def _header(self, circuit: BaseCircuit, result: DesignResult) -> list[str]:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        return [
            f"* ============================================================",
            f"* Circuit  : {result.circuit_type.replace('_', ' ').title()}",
            f"* Generated: {ts}",
            f"* Tool     : Python EDA System",
            f"* ============================================================",
            "",
        ]

    def _footer(self) -> list[str]:
        return ["", "* ── End of netlist ──────────────────────────────────────", ""]

    # ── LTspice execution ────────────────────────────────────────────
    def run_ltspice(self, netlist_path: str) -> str | None:
        """
        Attempt to run LTspice in batch mode.
        Returns the .log content as a string, or None if LTspice is
        not installed / not reachable.
        """
        ltspice_exe = self._find_ltspice()
        if ltspice_exe is None:
            print("[SPICE] LTspice not found – skipping simulation.")
            print(f"[SPICE] Open '{netlist_path}' manually in LTspice.")
            return None

        try:
            print(f"[SPICE] Running LTspice: {ltspice_exe}")
            cmd = [ltspice_exe, "-b", "-Run", netlist_path]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )
            log_path = netlist_path.replace(".cir", ".log")
            if os.path.isfile(log_path):
                with open(log_path, encoding="utf-8", errors="replace") as f:
                    return f.read()
            return proc.stdout or proc.stderr or ""
        except FileNotFoundError:
            print(f"[SPICE] LTspice executable not found at: {ltspice_exe}")
            return None
        except subprocess.TimeoutExpired:
            print("[SPICE] LTspice simulation timed out.")
            return None
        except Exception as exc:
            print(f"[SPICE] LTspice run failed: {exc}")
            return None

    def _find_ltspice(self) -> str | None:
        """Return path to LTspice executable, or None."""
        system = platform.system()
        candidates = _LTSPICE_PATHS.get(system, [])
        for path in candidates:
            if os.path.isfile(path):
                return path
        # Also check PATH
        for name in ("ltspice", "LTspice", "XVIIx64"):
            try:
                result = subprocess.run(
                    ["which", name] if system != "Windows" else ["where", name],
                    capture_output=True, text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip().split("\n")[0]
            except Exception:
                pass
        return None
