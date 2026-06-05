#!/usr/bin/env python3
"""Analyze India trend."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase8 import run_phase8, gen_population

IN_1970 = {
    'system_name': 'IN_1970', 'tax_type': 'income',
    'income_tax_rate': 0.15, 'corp_tax_rate': 0.55, 'welfare_rate': 0.02,
    'healthcare_gdp_share': 0.02,
    'elite_capture_intensity': 0.35, 'informal_share': 0.85,
    'informal_wage_penalty': 0.4, 'inheritance_rate': 0.0,
    'gini_actual': 0.48,
}

IN_2020 = {
    'system_name': 'IN_2020', 'tax_type': 'income',
    'income_tax_rate': 0.25, 'corp_tax_rate': 0.25, 'welfare_rate': 0.08,
    'healthcare_gdp_share': 0.04,
    'skill_premium_growth': 0.015, 'capital_income_share': 0.20,
    'import_competition': 0.25, 'elite_capture_intensity': 0.35,
    'informal_share': 0.80, 'informal_wage_penalty': 0.4,
    'inheritance_rate': 0.0,
    'gini_actual': 0.48,
}

print("=" * 70)
print("INDIA ANALYSIS")
print("=" * 70)

# Scan 1970s
print("\n--- 1970s wage_disp scan ---")
for wd in [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]:
    cfg = dict(IN_1970, wage_dispersion_mult=wd)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.48):.4f}")

# Scan 2020s
print("\n--- 2020s wage_disp scan ---")
for wd in [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]:
    cfg = dict(IN_2020, wage_dispersion_mult=wd)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.48):.4f}")

# Check trends
print("\n--- Trend check ---")
for d70 in [2.5, 3.0, 3.5, 4.0]:
    for d20 in [2.5, 3.0, 3.5, 4.0]:
        cfg70 = dict(IN_1970, wage_dispersion_mult=d70)
        cfg20 = dict(IN_2020, wage_dispersion_mult=d20)
        w, r, b = gen_population(42)
        r70 = run_phase8(w, r, b, 42, cfg70)
        w2, r2, b2 = gen_population(42)
        r20 = run_phase8(w2, r2, b2, 42, cfg20)
        delta = r20['gini'] - r70['gini']
        trend = 'STABLE' if abs(delta) <= 0.02 else ('RISING' if delta > 0 else 'FALLING')
        err70 = abs(r70['gini'] - 0.48)
        err20 = abs(r20['gini'] - 0.48)
        ok = ""
        if trend == 'STABLE' and err70 < 0.04 and err20 < 0.04:
            ok = " <<< GOOD"
        print(f"  d70={d70:.1f} d20={d20:.1f} -> "
              f"Gini70={r70['gini']:.4f} Gini20={r20['gini']:.4f} "
              f"err70={err70:.4f} err20={err20:.4f} delta={delta:.4f} trend={trend}{ok}")

print("\nDone.")
