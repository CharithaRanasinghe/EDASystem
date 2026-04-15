# Python EDA – Analog Circuit Designer

This tool allows the user to input requirement-parameters for 3 different types of electronic circuits, where the system is able to design the component values for the circuits according to the requirement, for the selected electronic circuit type. The output is set to LTSpice to where the desigened circuit is simulated and the actual results are analysed visually.

---

## Quick Start

```bash
pip install numpy scipy
python main.py                          # interactive mode
python main.py --batch examples/ce_example.json   # batch mode
```

---

## Supported Circuit Types

| Key                   | Description                              |
|-----------------------|------------------------------------------|
| `common_emitter`      | Common-emitter NPN BJT amplifier (BC547) |
| `voltage_divider_bias`| CE amplifier with stability-factor check |
| `rc_filter`           | First-order RC low-pass or high-pass     |

---

## Interactive Mode

```
╔══════════════════════════════════════════════════════╗
║         Python EDA – Analog Circuit Designer         ║
╚══════════════════════════════════════════════════════╝

  Available circuit types:
    [1] Common-Emitter NPN Amplifier
    [2] Voltage-Divider-Bias CE Amplifier
    [3] RC Filter (Low-Pass / High-Pass)

  Select circuit [1-3]: 1
  Configure: Common-Emitter NPN Amplifier

    Supply voltage VCC V [12]: 
    Target voltage gain |Av| V/V [50]: 80
    Load resistance RL Ω [10k]: 
    Operating frequency Hz [1k]: 
```

The system asks **only the parameters relevant** to the chosen circuit.

---

## Batch Mode

Supply a JSON spec file:

```json
{
  "circuit_type": "common_emitter",
  "params": {
    "vcc": 12.0,
    "gain": 80.0,
    "load_resistance": 10000,
    "frequency": 1000
  }
}
```

```bash
python main.py --batch examples/ce_example.json --output ./output
```

---

## Example Results

### Common-Emitter Amplifier (Av = 80 V/V target)

```
  Component Values:
    RC    =  6.8 kΩ
    RE    =  4.7 kΩ
    R1    =  180 kΩ
    R2    =  62 kΩ
    CE    =  16.3 µF
    CC1   =  342 nF
    CC2   =  100 nF

  Operating Point:
    IC    =  0.505 mA
    VCE   =  6.19 V    ← well centred for maximum swing
    gm    =  19.5 mS

  Performance:
    Av    =  79.1 V/V  (target 80, error 1.1%)
    Rin   =  4.6 kΩ
```

### RC Low-Pass Filter (fc = 3300 Hz target)

```
  Component Values:
    R  =  2.2 kΩ
    C  =  22 nF

  Performance:
    fc =  3288 Hz  (target 3300, error 0.4%)
```

---

## LTspice Usage

1. Open LTspice XVII
2. File → Open → select `output/common_emitter.cir`
3. Run `.OP` to see the DC operating point
4. Run `.AC` to see the frequency response (Bode plot)
5. Run `.TRAN` to see the transient response

The netlist includes:
- `.OP`   – DC operating point
- `.AC DEC 100 10 100MEG` – AC sweep 10 Hz to 100 MHz
- `.TRAN` – transient simulation (5 signal periods)

---

## Project Structure

```
eda_system/
├── main.py               Entry point (interactive + batch)
├── requirements.txt
├── ui/
│   └── interface.py      Menu, parameter prompts, validation
├── circuits/
│   ├── base.py           BaseCircuit abstract class
│   ├── registry.py       Maps string keys → circuit classes
│   ├── _fmt.py           Shared SPICE value formatters
│   ├── common_emitter.py CE NPN amplifier
│   ├── voltage_divider_bias.py  VDB CE amplifier
│   └── rc_filter.py      RC LP/HP filter
├── solvers/
│   └── e_series.py       E24/E12 standard value snap
├── spice/
│   └── runner.py         Netlist writer + LTspice subprocess
├── core/
│   ├── controller.py     Orchestration: spec → result → netlist
│   └── models.py         DesignSpec, DesignResult dataclasses
└── examples/
    ├── ce_example.json
    ├── vdb_example.json
    └── rc_lp_example.json
```

---

## Adding a New Circuit

1. Create `circuits/my_circuit.py` with a class extending `BaseCircuit`:
   - implement `optimize() → DesignResult`
   - implement `netlist_lines(result) → list[str]`

2. Register it in `circuits/registry.py`:
   ```python
   from circuits.my_circuit import MyCircuit
   CIRCUIT_REGISTRY["my_circuit"] = MyCircuit
   ```

3. Add parameter schema to `ui/interface.py` under `_SCHEMA`.

4. Add a batch example JSON to `examples/`.

---

## Design Methodology

### Common-Emitter / Voltage-Divider-Bias Amplifiers

Uses a **grid search over the E24 resistor series** for RC:

1. For each E24 RC value, the required IC is derived analytically:
   `IC = Av_target × VT / (RC ∥ RL)`

2. Bias components are sized from first principles:
   - `VE ≥ 0.2·VCC` (bias stability)
   - `I_divider = IC/10` (stiff voltage divider)
   - RE, R1, R2 derived, then snapped to E24

3. Each candidate is scored on gain error + VCE centering

4. Best-scoring physically-valid design is selected

This avoids the "near-VBE collapse" failure mode that pure gradient
optimizers suffer from after E24 snapping.

### RC Filter

Grid search over practical E24 R values (1 kΩ – 470 kΩ). For each R,
C is derived analytically then snapped to E12. The pair with minimum
`|fc_achieved − fc_target| / fc_target` is selected.

---

## Dependencies

- Python ≥ 3.10
- numpy ≥ 1.24
- scipy ≥ 1.10  (used for L-BFGS-B in voltage_divider_bias)

LTspice is **optional** – the system outputs `.cir` files that can be
opened manually. Automatic simulation runs if LTspice is detected on
your PATH or in its default install location.

---
<img width="1473" height="758" alt="Screenshot 2026-04-13 141140" src="https://github.com/user-attachments/assets/29b82b2b-94c0-4a55-8dd3-cd6e1769482e" />
<img width="1362" height="713" alt="Screenshot 2026-04-13 141216" src="https://github.com/user-attachments/assets/7e3866da-0e66-4f4a-b1ef-767433645813" />

---

## Clone

```
git clone https://github.com/CharithaRanasinghe/EDASystem.git && cd EDASystem
main.py

```
