"""
Common-Emitter (CE) NPN BJT Amplifier
======================================

Design methodology (analytic + constrained search)
----------------------------------------------------
The design equations are:

  Av = gm * Rp       where Rp = RC||RL,  gm = IC/VT
  VE = IC * RE       (we choose VE ≥ 0.2·VCC for stability)
  VB = VE + VBE

For a given (RC, RE) the required bias values follow directly:

  IC      = Av * VT / Rp           [from gain equation]
  VE      = max(0.2·VCC, IC·RE)    [stability constraint]
  VB      = VE + VBE
  R2/R1   = VB / (VCC - VB)        [voltage divider ratio]
  R1+R2   = VCC / (IC/10)          [stiff divider: Idiv = IC/10]

Strategy:
  1. Enumerate a grid of E24 RC values
  2. For each RC compute IC, RE, R1, R2 analytically
  3. Snap RE, R1, R2 to E24 then re-evaluate
  4. Score each candidate on gain error + VCE centring
  5. Return the best-scoring valid candidate
  6. Compute coupling/bypass caps from f_lo = freq/10
"""

import numpy as np
from circuits.base import BaseCircuit
from circuits._fmt import _fmt_r, _fmt_c
from core.models import DesignSpec, DesignResult
from solvers.e_series import nearest_e24

VT   = 0.02585   # thermal voltage 300 K (V)
VBE  = 0.70      # base-emitter junction drop (V)
HFE  = 100       # assumed current gain β

# Full E24 table, 100 Ω → 1 MΩ
_E24_BASE = [1.0,1.1,1.2,1.3,1.5,1.6,1.8,2.0,
             2.2,2.4,2.7,3.0,3.3,3.6,3.9,4.3,
             4.7,5.1,5.6,6.2,6.8,7.5,8.2,9.1]
_E24_R = [round(b * 10**e, 4)
          for e in range(2, 7)          # 100 Ω … 1 MΩ
          for b in _E24_BASE]


# ── Operating-point evaluator ────────────────────────────────────────
def _eval(RC, RE, R1, R2, VCC, RL):
    """
    Evaluate DC operating point and small-signal gain for a CE stage.
    Returns a dict, or None if the design is physically invalid.
    """
    if R1 <= 0 or R2 <= 0:
        return None
    VB  = VCC * R2 / (R1 + R2)
    VE  = VB - VBE
    if VE < 0.05:          # emitter voltage too low → unstable bias
        return None
    IC  = VE / RE
    if IC <= 0 or IC > 0.1:  # > 100 mA is unrealistic for small BJT
        return None
    gm  = IC / VT
    VC  = VCC - IC * RC
    VCE = VC - VE
    if VCE < 0.3:           # transistor in saturation
        return None
    Rp  = RC * RL / (RC + RL)
    Av  = gm * Rp
    Rin = 1.0 / (1/R1 + 1/R2 + gm/HFE)
    return dict(IC=IC, gm=gm, VB=VB, VE=VE, VC=VC,
                VCE=VCE, Av=Av, Rin=Rin)


# ── Bias designer ────────────────────────────────────────────────────
def _design_bias(RC, Av_t, VCC, RL):
    """
    Given RC and gain target, compute the ideal (continuous)
    IC, RE, R1, R2.  Returns tuple or None.
    """
    Rp  = RC * RL / (RC + RL)
    if Rp < 1.0:
        return None
    IC  = Av_t * VT / Rp          # from  Av = (IC/VT)·Rp
    if IC < 10e-6 or IC > 50e-3:
        return None

    # Emitter voltage: must be stable (≥ 20 % of VCC) and ≥ 1.4 V
    VE  = max(0.20 * VCC, 1.4)
    RE  = VE / IC

    # Bias divider
    VB    = VE + VBE
    Idiv  = IC / 10.0              # stiff divider rule
    R_tot = VCC / Idiv
    R2    = (VB / VCC) * R_tot
    R1    = R_tot - R2

    if R1 < 100 or R2 < 100:
        return None

    # Quick sanity: VC must be above VE
    VC  = VCC - IC * RC
    if VC < VE + 0.5:
        return None

    return IC, RE, R1, R2


# ── Score function for candidate ranking ─────────────────────────────
def _score(d, Av_t, VCC):
    if d is None:
        return np.inf
    e_gain = (d["Av"] / Av_t - 1.0) ** 2
    e_bias = (d["VCE"] / (VCC / 2) - 1.0) ** 2
    return 2.5 * e_gain + 1.0 * e_bias


# ── Circuit class ─────────────────────────────────────────────────────
class CommonEmitterAmplifier(BaseCircuit):

    def __init__(self, spec: DesignSpec):
        super().__init__(spec)
        self.VCC  = float(spec.get("vcc",  12.0))
        self.Av_t = abs(float(spec.get("gain", 50.0)))
        self.RL   = float(spec.get("load_resistance", 10e3))
        self.freq = float(spec.get("frequency", 1e3))
        self._validate()

    def _validate(self):
        if not (2 <= self.VCC <= 30):
            raise ValueError(f"VCC={self.VCC} out of range [2, 30] V")
        if not (1 <= self.Av_t <= 500):
            raise ValueError(f"|Av|={self.Av_t} out of range [1, 500]")
        if self.RL < 100:
            raise ValueError(f"RL={self.RL} Ω too small")

    def optimize(self) -> DesignResult:
        best = None
        best_score = np.inf

        for RC_try in _E24_R:
            if RC_try > self.RL * 4:   # skip impractically large RC
                continue

            ideal = _design_bias(RC_try, self.Av_t, self.VCC, self.RL)
            if ideal is None:
                continue
            _, RE_i, R1_i, R2_i = ideal

            # Snap RE, then re-derive R1/R2 from the snapped RE
            RE_s   = nearest_e24(RE_i)
            IC_s   = (max(0.20 * self.VCC, 1.4)) / RE_s   # VE/RE
            VE_s   = IC_s * RE_s
            VB_s   = VE_s + VBE
            Idiv_s = IC_s / 10.0
            R_tot  = self.VCC / Idiv_s
            R2_s   = nearest_e24((VB_s / self.VCC) * R_tot)
            R1_s   = nearest_e24(R_tot - (VB_s / self.VCC) * R_tot)

            d = _eval(RC_try, RE_s, R1_s, R2_s, self.VCC, self.RL)
            if d is None:
                continue

            sc = _score(d, self.Av_t, self.VCC)
            if sc < best_score:
                best_score = sc
                best = (RC_try, RE_s, R1_s, R2_s, d)

        if best is None:
            raise RuntimeError(
                "Could not find a valid design. "
                "Try increasing VCC, increasing RL, or reducing gain target."
            )

        RC_s, RE_s, R1_s, R2_s, d = best
        IC_b = d["IC"]
        gm   = d["gm"]
        Av_a = d["Av"]
        VCE  = d["VCE"]
        Rin  = d["Rin"]

        # Coupling / bypass caps  (–3 dB lower edge at freq/10)
        f_lo = self.freq / 10.0
        re_e = 1/gm + RE_s/(HFE + 1)
        CE   = max(1.0 / (2 * np.pi * f_lo * re_e),       1e-6)
        CC1  = max(1.0 / (2 * np.pi * f_lo * (Rin + 50)), 0.1e-6)
        CC2  = max(1.0 / (2 * np.pi * f_lo * (RC_s + self.RL)), 0.1e-6)

        warnings = []
        if VCE < 1.0:
            warnings.append(f"VCE = {VCE:.2f} V is marginal – risk of saturation")
        gain_err = abs(Av_a / self.Av_t - 1)
        if gain_err > 0.20:
            warnings.append(
                f"Gain error {gain_err*100:.1f}% – "
                "E24 component quantisation limit; "
                "try adjusting RL or VCC"
            )

        result = DesignResult(
            circuit_type="common_emitter",
            component_values={
                "RC":  RC_s,  "RE":  RE_s,
                "R1":  R1_s,  "R2":  R2_s,
                "CE":  CE,    "CC1": CC1,
                "CC2": CC2,   "RL":  self.RL,
            },
            operating_point={
                "IC (mA)":  IC_b * 1e3,
                "VB (V)":   d["VB"],
                "VE (V)":   d["VE"],
                "VC (V)":   d["VC"],
                "VCE (V)":  VCE,
                "gm (mS)":  gm * 1e3,
            },
            achieved_performance={
                "Av (V/V)":  Av_a,
                "Rin (kΩ)":  Rin / 1e3,
            },
            target_performance={"Av (V/V)": self.Av_t},
            optimization_error=float(best_score),
            warnings=warnings,
        )
        return result

    # ── Netlist ───────────────────────────────────────────────────────
    def netlist_lines(self, result: DesignResult) -> list[str]:
        cv = result.component_values
        op = result.operating_point
        av = result.achieved_performance.get("Av (V/V)", 0)
        ic = op.get("IC (mA)", 0)

        return [
            "* Common-Emitter NPN Amplifier  (BC547)",
            f"* Target Av = {self.Av_t:.1f} V/V  |  VCC = {self.VCC:.1f} V",
            f"* Achieved Av \u2248 {av:.2f} V/V  |  IC \u2248 {ic:.3f} mA",
            "* Generated by Python EDA System",
            "",
            "* \u2500\u2500 Power supply",
            f"VCC  vcc  0  DC {self.VCC}",
            "",
            f"* \u2500\u2500 AC input  (1 mV pk,  {self.freq:.0f} Hz)",
            f"Vin  in   0  AC 1m  SIN(0 1m {self.freq:.0f})",
            "",
            "* \u2500\u2500 Input coupling cap",
            f"CC1  in   base  {_fmt_c(cv['CC1'])}",
            "",
            "* \u2500\u2500 Voltage-divider bias",
            f"R1   vcc  base  {_fmt_r(cv['R1'])}",
            f"R2   base  0    {_fmt_r(cv['R2'])}",
            "",
            "* \u2500\u2500 BJT  (NPN BC547)",
            "Q1   col  base  emit  BC547",
            "",
            "* \u2500\u2500 Collector resistor",
            f"RC   vcc  col   {_fmt_r(cv['RC'])}",
            "",
            "* \u2500\u2500 Emitter resistor + bypass cap",
            f"RE   emit  0    {_fmt_r(cv['RE'])}",
            f"CE   emit  0    {_fmt_c(cv['CE'])}",
            "",
            "* \u2500\u2500 Output coupling cap \u2192 load",
            f"CC2  col   out  {_fmt_c(cv['CC2'])}",
            f"RL   out   0    {_fmt_r(cv['RL'])}",
            "",
            "* \u2500\u2500 BJT model  (BC547, simplified Gummel-Poon)",
            ".MODEL BC547 NPN(IS=1e-14 BF=100 VAF=100",
            "+              RB=10 RC=0.5 RE=0.1",
            "+              CJC=4p CJE=10p TF=0.3n)",
            "",
            "* \u2500\u2500 Analyses",
            ".OP",
            ".AC DEC 100 10 100MEG",
            f".TRAN 1n {int(5/self.freq*1e9)}n",
            "",
            ".END",
        ]



