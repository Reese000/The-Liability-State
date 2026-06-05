#!/usr/bin/env python3
"""Broader Germany calibration."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase8 import run_phase8, gen_population

BASE60 = {
    'system_name': 'DE_1960', 'tax_type': 'income',
    'income_tax_rate': 0.35, 'corp_tax_rate': 0.50, 'welfare_rate': 0.06,
    'healthcare_gdp_share': 0.05,
    'skill_premium_growth': 0.005, 'union_coverage': 0.30,
    'capital_income_share': 0.05, 'import_competition': 0.02,
    'inheritance_rate': 0.0,
}

BASE20 = {
    'system_name': 'DE_2020', 'tax_type': 'income',
    'income_tax_rate': 0.40, 'corp_tax_rate': 0.15, 'welfare_rate': 0.13,
    'healthcare_gdp_share': 0.10,
    'skill_premium_growth': 0.012, 'union_coverage': 0.22,
    'capital_income_share': 0.12, 'import_competition': 0.12,
    'inheritance_rate': 0.0,
}

print("=" * 70)
print("GERMANY BROAD SCAN")
print("=" * 70)

# First, find 1960s wage_disp that gives Gini ~0.30
print("\n--- 1960s: finding wage_disp for Gini~0.30 ---")
for wd in [1.5, 1.6, 1.8, 2.0, 2.2]:
    cfg = dict(BASE60, wage_dispersion_mult=wd)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f}")

# Second, find 2020s wage_disp that gives Gini~0.30 with NO reuni/hartz
print("\n--- 2020s (no reuni/hartz): finding wage_disp for Gini~0.30 ---")
for wd in [1.5, 1.8, 2.0, 2.2, 2.5]:
    cfg = dict(BASE20, wage_dispersion_mult=wd, reunification_shock=0.0, hartz_reform=0.0)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f}")

# Third: try different d60/d20 combinations for STABLE trend
print("\n--- Trend check (no reuni/hartz) ---")
for d60 in [1.5, 1.8, 2.0, 2.2]:
    for d20 in [1.8, 2.0, 2.2, 2.5]:
        cfg60 = dict(BASE60, wage_dispersion_mult=d60)
        cfg20 = dict(BASE20, wage_dispersion_mult=d20, reunification_shock=0.0, hartz_reform=0.0)
        w, r, b = gen_population(42)
        r60 = run_phase8(w, r, b, 42, cfg60)
        w2, r2, b2 = gen_population(42)
        r20 = run_phase8(w2, r2, b2, 42, cfg20)
        delta = r20['gini'] - r60['gini']
        trend = 'STABLE' if abs(delta) <= 0.02 else ('RISING' if delta > 0 else 'FALLING')
        err60 = abs(r60['gini'] - 0.30)
        err20 = abs(r20['gini'] - 0.30)
        ok = ""
        if trend == 'STABLE' and err60 < 0.02 and err20 < 0.02:
            ok = " <<< GOOD"
        print(f"  d60={d60:.1f} d20={d20:.1f} -> "
              f"Gini60={r60['gini']:.4f} Gini20={r20['gini']:.4f} "
              f"delta={delta:.4f} trend={trend}{ok}")

# Fourth: with mild reuni+hartz
print("\n--- With mild reuni=0.1 hartz=0.1 ---")
for d60 in [1.5, 1.8, 2.0]:
    for d20 in [1.8, 2.0, 2.2]:
        cfg60 = dict(BASE60, wage_dispersion_mult=d60)
        cfg20 = dict(BASE20, wage_dispersion_mult=d20, reunification_shock=0.1, hartz_reform=0.1)
        w, r, b = gen_population(42)
        r60 = run_phase8(w, r, b, 42, cfg60)
        w2, r2, b2 = gen_population(42)
        r20 = run_phase8(w2, r2, b2, 42, cfg20)
        delta = r20['gini'] - r60['gini']
        trend = 'STABLE' if abs(delta) <= 0.02 else ('RISING' if delta > 0 else 'FALLING')
        err60 = abs(r60['gini'] - 0.30)
        err20 = abs(r20['gini'] - 0.30)
        ok = ""
        if trend == 'STABLE' and err60 < 0.02 and err20 < 0.02:
            ok = " <<< GOOD"
        print(f"  d60={d60:.1f} d20={d20:.1f} -> "
              f"Gini60={r60['gini']:.4f} Gini20={r20['gini']:.4f} "
              f"delta={delta:.4f} trend={trend}{ok}")

print("\nDone.")
