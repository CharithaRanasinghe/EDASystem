"""
Abstract base class that every circuit model must implement.
"""
from abc import ABC, abstractmethod
from core.models import DesignSpec, DesignResult


class BaseCircuit(ABC):
    """
    Contract every circuit module must satisfy:

      1.  __init__(spec)   — parse user spec, validate, set defaults
      2.  optimize()       — run solver, return DesignResult
      3.  netlist_lines()  — return list[str] for the .cir netlist
      4.  parse_sim_output() — optional: ingest LTspice raw output
    """

    def __init__(self, spec: DesignSpec):
        self.spec = spec

    @abstractmethod
    def optimize(self) -> DesignResult:
        """Run numerical optimization; return populated DesignResult."""
        ...

    @abstractmethod
    def netlist_lines(self, result: DesignResult) -> list[str]:
        """Return a list of SPICE netlist lines for this design."""
        ...

    def parse_sim_output(self, raw_output: str, result: DesignResult) -> None:
        """
        Optional hook to parse LTspice .raw or .log output and update
        result.achieved_performance with simulated values.
        Default: no-op.
        """
        pass
