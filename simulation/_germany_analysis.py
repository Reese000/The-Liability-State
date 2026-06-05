#!/usr/bin/env python3
"""Analyze Germany trend: find why sim is RISING but actual is STABLE."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase8 import run_phase8, gen_population

GERMANY_PERIODS = {
    1960: {
        'system_name': 'DE_1960', 'tax_type': 'income',
        'income_tax_rate': 0.35, 'corp_tax_rate': 0.50, 'welfare_rate': 0.06,
        'healthcare_gdp_share': 0.05,
        'skill_premium_growth': 0.005, 'union_coverage': 0.30,
        'capital_income_share': 0.05, 'import_competition': 0.02,
        'wage_dispersion_mult': 1.2, 'inheritance_rate': 0.0,
        'gini_actual': 0.30,
    },
    2020: {
        'system_name': 'DE_2020', 'tax_type': 'income',
        'income_tax_rate': 0.40, 'corp_tax_rate': 0.15, 'welfare_rate': 0.13,
        'healthcare_gdp_share': 0.10,
        'skill_premium_growth': 0.012, 'union_coverage': 0.22,
        'capital_income_share': 0.12, 'import_competition': 0.12,
        'reunification_shock': 0.5, 'hartz_reform': 0.3,
        'wage_dispersion_mult': 1.5, 'inheritance_rate': 0.0,
        'gini_actual': 0.30,
    },
}

print("=" * 70)
print("GERMANY ANALYSIS")
print("=" * 70)

# Current values
print("\n--- Current config ---")
cfg60 = dict(GERMANY_PERIODS[1960])
w, r, b = gen_population(42)
res60 = run_phase8(w, r, b, 42, cfg60)
print(f"  1960s: Gini={res60['gini']:.4f} (target 0.30) err={abs(res60['gini']-0.30)*100/0.30:.1f}%")

cfg20 = dict(GERMANY_PERIODS[2020])
w2, r2, b2 = gen_population(42)
res20 = run_phase8(w2, r2, b2, 42, cfg20)
print(f"  2020s: Gini={res20['gini']:.4f} (target 0.30) err={abs(res20['gini']-0.30)*100/0.30:.1f}%")
delta = res20['gini'] - res60['gini']
print(f"  Delta: {delta:.4f} Trend: {'RISING' if delta > 0.02 else 'FALLING' if delta < -0.02 else 'STABLE'}")

# Test: disable reunification and hartz
print("\n--- Without reuni+hartz ---")
cfg20b = dict(GERMANY_PERIODS[2020], reunification_shock=0.0, hartz_reform=0.0)
w3, r3, b3 = gen_population(42)
res20b = run_phase8(w3, r3, b3, 42, cfg20b)
print(f"  2020s (no reuni/hartz): Gini={res20b['gini']:.4f}")

# Try with lower reuni+hartz
print("\n--- Tuning reuni+hartz ---")
for reuni in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]:
    for hartz in [0.0, 0.1, 0.2, 0.3]:
        cfg20c = dict(GERMANY_PERIODS[2020], reunification_shock=reuni, hartz_reform=hartz)
        w, r, b = gen_population(42)
        res = run_phase8(w, r, b, 42, cfg20c)
        col = ""
        if abs(res['gini'] - 0.30) < 0.02:
            col = " <<< GOOD"
        print(f"  reuni={reuni:.1f} hartz={hartz:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.30):.4f}{col}")

# Test wage_disp for Germany
print("\n--- Wage_disp scan 2020s ---")
for wd in [1.2, 1.5, 1.8, 2.0, 2.2, 2.5]:
    cfg20d = dict(GERMANY_PERIODS[2020], wage_dispersion_mult=wd, reunification_shock=0.2, hartz_reform=0.2)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg20d)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.30):.4f}")

print("\n--- Wage_disp scan 1960s ---")
for wd in [1.0, 1.2, 1.5, 1.8, 2.0]:
    cfg60d = dict(GERMANY_PERIODS[1960], wage_dispersion_mult=wd)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg60d)
    print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={abs(res['gini']-0.30):.4f}")

# Best trend check
print("\n--- Best trend ---")
best_configs = []
for d60 in [1.0, 1.2, 1.5]:
    for d20 in [1.5, 1.8, 2.0, 2.2]:
        for reuni in [0.0, 0.2, 0.5]:
            for hartz in [0.0, 0.2, 0.3]:
                cfg60e = dict(GERMANY_PERIODS[1960], wage_dispersion_mult=d60)
                cfg20e = dict(GERMANY_PERIODS[2020], wage_dispersion_mult=d20, 
                             reunification_shock=reuni, hartz_reform=hartz)
                w, r, b = gen_population(42)
                r60 = run_phase8(w, r, b, 42, cfg60e)
                w2, r2, b2 = gen_population(42)
                r20 = run_phase8(w2, r2, b2, 42, cfg20e)
                delta = r20['gini'] - r60['gini']
                trend = 'STABLE' if abs(delta) <= 0.02 else ('RISING' if delta > 0 else 'FALLING')
                err60 = abs(r60['gini'] - 0.30)
                err20 = abs(r20['gini'] - 0.30)
                if trend == 'STABLE' and err60 < 0.02 and err20 < 0.04:
                    best_configs.append((d60, d20, reuni, hartz, err60, err20, delta))
                    print(f"  ✓ d60={d60:.1f} d20={d20:.1f} reuni={reuni:.1f} hartz={hartz:.1f} -> "
                          f"Gini60={r60['gini']:.4f} Gini20={r20['gini']:.4f} "
                          f"err60={err60:.4f} err20={err20:.4f} delta={delta:.4f}")

if not best_configs:
    print("  No good config found in scan.")
else:
    best = min(best_configs, key=lambda x: x[4] + x[5])
    print(f"\n  BEST: d60={best[0]} d20={best[1]} reuni={best[2]} hartz={best[3]}")
    print(f"        err60={best[4]:.4f} err20={best[5]:.4f} delta={best[6]:.4f}")
