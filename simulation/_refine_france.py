#!/usr/bin/env python3
"""Refine France wage_disp values — finer-grained scan."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase8 import run_phase8, gen_population

FR1960 = {
    'system_name': 'FR_1960', 'tax_type': 'income',
    'income_tax_rate': 0.25, 'corp_tax_rate': 0.50, 'welfare_rate': 0.08,
    'healthcare_gdp_share': 0.04, 'use_progressive_tax': True,
    'child_benefit_taper': 0.05, 'unemployment_rate': 0.02,
    'informal_share': 0.08, 'inheritance_rate': 0.0,
}

FR2020 = {
    'system_name': 'FR_2020', 'tax_type': 'income',
    'income_tax_rate': 0.45, 'corp_tax_rate': 0.25, 'welfare_rate': 0.20,
    'healthcare_gdp_share': 0.11, 'use_progressive_tax': True,
    'child_benefit_taper': 0.50, 'unemployment_rate': 0.08,
    'informal_share': 0.12, 'inheritance_rate': 0.0,
    'skill_premium_growth': 0.008, 'union_coverage': 0.25,
    'capital_income_share': 0.12, 'import_competition': 0.15,
    'elite_capture_intensity': 0.05,
}

print("--- Refine 1960s (target 0.35) ---")
for wd in [3.2, 3.3, 3.4, 3.5]:
    cfg = dict(FR1960, wage_dispersion_mult=wd)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.35):.4f}")

print("--- Refine 2020s (target 0.30) ---")
for wd in [1.4, 1.5, 1.6, 1.7]:
    cfg = dict(FR2020, wage_dispersion_mult=wd)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.30):.4f}")

print("--- Best combo trend check ---")
for d60 in [3.2, 3.3, 3.4]:
    for d20 in [1.5, 1.6, 1.7]:
        cfg60 = dict(FR1960, wage_dispersion_mult=d60)
        cfg20 = dict(FR2020, wage_dispersion_mult=d20)
        w, r, b = gen_population(42)
        r60 = run_phase8(w, r, b, 42, cfg60)
        w2, r2, b2 = gen_population(42)
        r20 = run_phase8(w2, r2, b2, 42, cfg20)
        delta = r20['gini'] - r60['gini']
        trend = 'FALLING' if delta < -0.02 else ('RISING' if delta > 0.02 else 'STABLE')
        err60 = abs(r60['gini'] - 0.35)
        err20 = abs(r20['gini'] - 0.30)
        print(f"  d60={d60:.1f} d20={d20:.1f} -> "
              f"Gini60={r60['gini']:.4f} Gini20={r20['gini']:.4f} "
              f"delta={delta:.4f} trend={trend} "
              f"err60={err60:.4f} err20={err20:.4f}")

print("Done.")
