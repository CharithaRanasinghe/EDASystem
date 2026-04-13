"""
Main controller: orchestrates UI → Circuit Model → Solver → SPICE output.
"""
from core.models import DesignSpec, DesignResult
from circuits.registry import CIRCUIT_REGISTRY
from spice.runner import SpiceRunner


class DesignController:
    """
    Top-level EDA controller.
    Wires together:  UI spec → circuit model → solver → SPICE output.
    """

    def __init__(self, output_dir: str = "."):
        self.output_dir = output_dir
        self.spice_runner = SpiceRunner(output_dir=output_dir)

    # ------------------------------------------------------------------
    def run(self, spec: DesignSpec) -> DesignResult:
        """
        Execute a full design pass for the given spec.
        Returns a DesignResult with components, operating point,
        performance figures, and path to the generated netlist.
        """
        circuit_cls = CIRCUIT_REGISTRY.get(spec.circuit_type)
        if circuit_cls is None:
            raise ValueError(
                f"Unknown circuit type: '{spec.circuit_type}'. "
                f"Available: {list(CIRCUIT_REGISTRY.keys())}"
            )

        print(f"\n[Controller] Designing '{spec.circuit_type}' …")

        # 1. Build the circuit model (encapsulates engineering equations)
        circuit = circuit_cls(spec)

        # 2. Run numerical optimization
        print("[Controller] Running optimizer …")
        result: DesignResult = circuit.optimize()

        # 3. Generate SPICE netlist
        print("[Controller] Generating netlist …")
        netlist_path = self.spice_runner.generate(circuit, result)
        result.netlist_path = netlist_path

        # 4. Optionally run LTspice (graceful fallback)
        sim_output = self.spice_runner.run_ltspice(netlist_path)
        if sim_output:
            print("[Controller] Simulation completed – parsing results …")
            circuit.parse_sim_output(sim_output, result)
        else:
            print("[Controller] LTspice not found – manual run required.")

        return result
