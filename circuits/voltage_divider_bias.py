"""
Voltage-Divider-Bias CE Amplifier
===================================
Extends the common-emitter design with an explicit stability-factor
constraint (Giacoletto / Millman stability factor S):

    S = dIC/dICO ≈ (1 + hFE) / (1 + hFE·RE/(Rth+RE))

where Rth = R1||R2 is the Thevenin base resistance.

Lower S → better stability.  Typical target: S ≤ 10.

Design strategy: same E24 grid search as common_emitter, but the
scoring function penalises S > S_max and the bias is sized to keep
S within target.
"""

import numpy as np
from circuits.base import BaseCircuit
from circuits._fmt import _fmt_r, _fmt_c
from core.models import DesignSpec, DesignResult
from solvers.e_series import nearest_e24

VT   = 0.02585
VBE  = 0.70
HFE  = 150   # BC550 / 2N3904 typical

_E24_BASE = [1.0,1.1,1.2,1.3,1.5,1.6,1.8,2.0,
             2.2,2.4,2.7,3.0,3.3,3.6,3.9,4.3,
             4.7,5.1,5.6,6.2,6.8,7.5,8.2,9.1]
_E24_R = [round(b * 10**e, 4)
          for e in range(2, 7)
          for b in _E24_BASE]


def _eval(RC, RE, R1, R2, VCC, RL):
    if R1 <= 0 or R2 <= 0:
        return None
    VB  = VCC * R2 / (R1 + R2)
    VE  = VB - VBE
    if VE < 0.05:
        return None
    IC  = VE / RE
    if IC <= 0 or IC > 0.1:
        return None
    gm  = IC / VT
    VC  = VCC - IC * RC
    VCE = VC - VE
    if VCE < 0.3:
        return None
    Rp  = RC * RL / (RC + RL)
    Av  = gm * Rp
    Rin = 1.0 / (1/R1 + 1/R2 + gm/HFE)
    Rth = R1 * R2 / (R1 + R2)
    S   = (1 + HFE) / (1 + HFE * RE / (Rth + RE + 1e-12))
    return dict(IC=IC, gm=gm, VB=VB, VE=VE, VC=VC, VCE=VCE,
                Av=Av, Rin=Rin, S=S)


class VoltageDividerBiasAmplifier(BaseCircuit):

    def __init__(self, spec: DesignSpec):
        super().__init__(spec)
        self.VCC   = float(spec.get("vcc",  12.0))
        self.Av_t  = abs(float(spec.get("gain", 100.0)))
        self.RL    = float(spec.get("load_resistance", 10e3))
        self.RS    = float(spec.get("source_resistance", 600.0))
        self.freq  = float(spec.get("frequency", 1e3))
        self.S_max = float(spec.get("stability_factor", 10.0))

    def optimize(self) -> DesignResult:
        best = None
        best_score = np.inf

        for RC_try in _E24_R:
            if RC_try > self.RL * 4:
                continue

            Rp  = RC_try * self.RL / (RC_try + self.RL)
            if Rp < 1.0:
                continue
            IC  = self.Av_t * VT / Rp
            if IC < 10e-6 or IC > 50e-3:
                continue

            # Size RE to achieve target S:
            #   S = (1+hFE)/(1 + hFE·RE/(Rth+RE))  ≤ S_max
            # Solve for minimum RE given Rth:
            # Rth = R1||R2;  choose Rth = VCC/(IC/10) * (VB/VCC)*(1-VB/VCC)
            VE    = max(0.20 * self.VCC, 1.4)
            RE    = VE / IC
            RE_s  = nearest_e24(RE)

            IC_s  = VE / RE_s
            VB_s  = VE + VBE
            Idiv  = IC_s / 10.0
            R_tot = self.VCC / Idiv
            R2_s  = nearest_e24((VB_s / self.VCC) * R_tot)
            R1_s  = nearest_e24(R_tot - (VB_s / self.VCC) * R_tot)

            d = _eval(RC_try, RE_s, R1_s, R2_s, self.VCC, self.RL)
            if d is None:
                continue

            e_gain  = (d["Av"] / self.Av_t - 1.0) ** 2
            e_bias  = (d["VCE"] / (self.VCC / 2) - 1.0) ** 2
            e_stab  = max(0.0, d["S"] / self.S_max - 1.0) ** 2 * 5.0
            score   = 2.5 * e_gain + 1.0 * e_bias + e_stab

            if score < best_score:
                best_score = score
                best = (RC_try, RE_s, R1_s, R2_s, d)

        if best is None:
            raise RuntimeError(
                "Could not find a valid design. "
                "Try increasing VCC, adjusting stability factor, or reducing gain."
            )

        RC_s, RE_s, R1_s, R2_s, d = best
        IC_b = d["IC"]
        gm   = d["gm"]
        Av_a = d["Av"]
        VCE  = d["VCE"]
        Rin  = d["Rin"]
        S_f  = d["S"]

        f_lo = self.freq / 10.0
        re_e = 1/gm + RE_s/(HFE + 1)
        CE   = max(1.0 / (2 * np.pi * f_lo * re_e),               1e-6)
        CC1  = max(1.0 / (2 * np.pi * f_lo * (Rin + self.RS)),    0.1e-6)
        CC2  = max(1.0 / (2 * np.pi * f_lo * (RC_s + self.RL)),   0.1e-6)

        warnings = []
        if S_f > self.S_max:
            warnings.append(f"Stability factor S={S_f:.1f} exceeds target {self.S_max:.0f}")
        if VCE < 1.0:
            warnings.append(f"VCE={VCE:.2f} V is marginal")
        if abs(Av_a / self.Av_t - 1) > 0.20:
            warnings.append(f"Gain error {abs(Av_a/self.Av_t-1)*100:.1f}% > 20%")

        return DesignResult(
            circuit_type="voltage_divider_bias",
            component_values={
                "RC":  RC_s, "RE":  RE_s,
                "R1":  R1_s, "R2":  R2_s,
                "CE":  CE,   "CC1": CC1,
                "CC2": CC2,  "RL":  self.RL,
            },
            operating_point={
                "IC (mA)":  IC_b * 1e3,
                "VB (V)":   d["VB"],
                "VE (V)":   d["VE"],
                "VC (V)":   d["VC"],
                "VCE (V)":  VCE,
                "gm (mS)":  gm * 1e3,
                "S":        S_f,
            },
            achieved_performance={
                "Av (V/V)":  Av_a,
                "Rin (kΩ)":  Rin / 1e3,
                "S":         S_f,
            },
            target_performance={
                "Av (V/V)": self.Av_t,
                "S":        self.S_max,
            },
            optimization_error=float(best_score),
            warnings=warnings,
        )

    def netlist_lines(self, result: DesignResult) -> list[str]:
        cv = result.component_values
        op = result.operating_point
        av = result.achieved_performance.get("Av (V/V)", 0)
        ic = op.get("IC (mA)", 0)
        S  = op.get("S", 0)

        return [
            "* Voltage-Divider-Bias CE Amplifier  (BC550 NPN)",
            f"* Target Av={self.Av_t:.1f} V/V  |  VCC={self.VCC:.1f} V  |  S_max={self.S_max:.0f}",
            f"* Achieved Av\u2248{av:.2f} V/V  |  IC\u2248{ic:.3f} mA  |  S\u2248{S:.1f}",
            "* Generated by Python EDA System",
            "",
            f"VCC  vcc  0  DC {self.VCC}",
            f"Vin  in   0  AC 1m  SIN(0 1m {self.freq:.0f})",
            f"CC1  in   base  {_fmt_c(cv['CC1'])}",
            f"R1   vcc  base  {_fmt_r(cv['R1'])}",
            f"R2   base  0    {_fmt_r(cv['R2'])}",
            "Q1   col  base  emit  BC550",
            f"RC   vcc  col   {_fmt_r(cv['RC'])}",
            f"RE   emit  0    {_fmt_r(cv['RE'])}",
            f"CE   emit  0    {_fmt_c(cv['CE'])}",
            f"CC2  col   out  {_fmt_c(cv['CC2'])}",
            f"RL   out   0    {_fmt_r(cv['RL'])}",
            "",
            "* BC550 NPN (low-noise, high-hFE variant)",
            ".MODEL BC550 NPN(IS=1e-14 BF=150 VAF=120",
            "+              RB=8 RC=0.4 RE=0.1",
            "+              CJC=3.5p CJE=9p TF=0.25n)",
            "",
            ".OP",
            ".AC DEC 100 10 100MEG",
            ".END",
        ]
