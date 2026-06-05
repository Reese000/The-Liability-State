#!/usr/bin/env python3
"""Calibrate France wage_disp values for 1960s and 2020s to get FALLING trend."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase8 import run_phase8, gen_population
import numpy as np

FR_1960_BASE = {
    'system_name': 'FR_1960', 'tax_type': 'income',
    'income_tax_rate': 0.25, 'corp_tax_rate': 0.50, 'welfare_rate': 0.08,
    'healthcare_gdp_share': 0.04, 'use_progressive_tax': True,
    'child_benefit_taper': 0.05, 'unemployment_rate': 0.02,
    'informal_share': 0.08,
    'inheritance_rate': 0.0,
}

FR_2020_BASE = {
    'system_name': 'FR_2020', 'tax_type': 'income',
    'income_tax_rate': 0.45, 'corp_tax_rate': 0.25, 'welfare_rate': 0.20,
    'healthcare_gdp_share': 0.11, 'use_progressive_tax': True,
    'child_benefit_taper': 0.50, 'unemployment_rate': 0.08,
    'informal_share': 0.12,
    'skill_premium_growth': 0.008, 'union_coverage': 0.25,
    'capital_income_share': 0.12, 'import_competition': 0.15,
    'elite_capture_intensity': 0.05, 'inheritance_rate': 0.0,
}

print("=" * 70)
print("FRANCE WAGE_DISP CALIBRATION (1960s target=0.35, 2020s target=0.30)")
print("=" * 70)

# Scan 1960s wage_disp
print("\n--- 1960s SCAN ---")
best_60 = (0, 1.0, 999)
for wd in [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]:
    cfg = dict(FR_1960_BASE, wage_dispersion_mult=wd)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    err = abs(res['gini'] - 0.35)
    print(f"  wage_disp={wd:4.1f} → Gini={res['gini']:.4f} (target 0.35, err={err:.4f})")
    if err < best_60[2]:
        best_60 = (wd, res['gini'], err)
print(f"  BEST: wage_disp={best_60[0]} → Gini={best_60[1]:.4f}, err={best_60[2]:.4f}")

# Scan 2020s wage_disp
print("\n--- 2020s SCAN ---")
best_20 = (0, 1.0, 999)
for wd in [1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]:
    cfg = dict(FR_2020_BASE, wage_dispersion_mult=wd)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    err = abs(res['gini'] - 0.30)
    print(f"  wage_disp={wd:4.1f} → Gini={res['gini']:.4f} (target 0.30, err={err:.4f})")
    if err < best_20[2]:
        best_20 = (wd, res['gini'], err)
print(f"  BEST: wage_disp={best_20[0]} → Gini={best_20[1]:.4f}, err={best_20[2]:.4f}")

# Test best combination for trend
print(f"\n--- BEST TREND CHECK ---")
wd_60 = best_60[0]
wd_20 = best_20[0]
cfg60 = dict(FR_1960_BASE, wage_dispersion_mult=wd_60)
cfg20 = dict(FR_2020_BASE, wage_dispersion_mult=wd_20)
w, r, b = gen_population(42)
res60 = run_phase8(w, r, b, 42, cfg60)
w, r, b = gen_population(42)
res20 = run_phase8(w, r, b, 42, cfg20)
delta = res20['gini'] - res60['gini']
trend = 'FALLING' if delta < -0.02 else ('RISING' if delta > 0.02 else 'STABLE')
print(f"  1960s (d={wd_60}): Gini={res60['gini']:.4f} (target 0.35)")
print(f"  2020s (d={wd_20}): Gini={res20['gini']:.4f} (target 0.30)")
print(f"  Delta: {delta:.4f}  Trend: {trend} (need FALLING)")
print(f"  Level err 60s: {abs(res60['gini']-0.35)/0.35*100:.1f}%")
print(f"  Level err 20s: {abs(res20['gini']-0.30)/0.30*100:.1f}%")

# Refine if needed
print("\n--- REFINEMENT PASS ---")
candidates_60 = [wd_60, wd_60 + 0.5, wd_60 - 0.5, wd_60 + 1.0]
candidates_20 = [wd_20, wd_20 + 0.3, wd_20 - 0.3]
for wd60_test in candidates_60:
    for wd20_test in candidates_20:
        if wd60_test < 1.0 or wd20_test < 1.0:
            continue
        cfg60 = dict(FR_1960_BASE, wage_dispersion_mult=wd60_test)
        cfg20 = dict(FR_2020_BASE, wage_dispersion_mult=wd20_test)
        w, r, b = gen_population(42)
        r60 = run_phase8(w, r, b, 42, cfg60)
        w2, r2, b2 = gen_population(42)
        r20 = run_phase8(w2, r2, b2, 42, cfg20)
        delta = r20['gini'] - r60['gini']
        err60 = abs(r60['gini'] - 0.35)
        err20 = abs(r20['gini'] - 0.30)
        trend = 'FALLING' if delta < -0.02 else ('RISING' if delta > 0.02 else 'STABLE')
        if trend == 'FALLING' and err60 < 0.03 and err20 < 0.03:
            print(f"  ✓ d60={wd60_test:.1f} d20={wd20_test:.1f} → "
                  f"Gini60={r60['gini']:.4f} Gini20={r20['gini']:.4f} "
                  f"delta={delta:.4f} trend={trend} "
                  f"err60={err60:.4f} err20={err20:.4f}")

print("\nDone.")
