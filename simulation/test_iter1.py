#!/usr/bin/env python3
"""Test: France trend fix with period-varying wage_dispersion_mult.

Calibrated values (from _calibrate_all_france.py):
  1960s: wage_disp=3.3 -> Gini 0.351 (target 0.35, 0.3% err)
  1980s: wage_disp=3.5 -> Gini 0.365 (target 0.37, 1.5% err)
  2000s: wage_disp=2.5 -> Gini 0.340 (target 0.34, 0.0% err)
  2020s: wage_disp=1.6 -> Gini 0.297 (target 0.30, 0.9% err)
  Overall 1960->2020: -0.054 = FALLING
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase8 import run_phase8, gen_population
import numpy as np

print("=" * 60)
print("ITERATION 1 TEST: FRANCE TREND + LEVEL FIX")
print("=" * 60)
print()

# France period configs with period-varying wage_disp (calibrated)
PERIODS = {
    1960: {
        'system_name': 'FR_1960', 'tax_type': 'income',
        'income_tax_rate': 0.25, 'corp_tax_rate': 0.50, 'welfare_rate': 0.05,
        'healthcare_gdp_share': 0.04, 'use_progressive_tax': True,
        'child_benefit_taper': 0.02, 'unemployment_rate': 0.02,
        'informal_share': 0.08, 'wage_dispersion_mult': 3.3,
        'skill_premium_growth': 0.001, 'union_coverage': 0.25,
        'capital_income_share': 0.04, 'import_competition': 0.03,
        'elite_capture_intensity': 0.02, 'inheritance_rate': 0.0,
        'gini_actual': 0.35,
    },
    1980: {
        'system_name': 'FR_1980', 'tax_type': 'income',
        'income_tax_rate': 0.30, 'corp_tax_rate': 0.50, 'welfare_rate': 0.10,
        'healthcare_gdp_share': 0.06, 'use_progressive_tax': True,
        'child_benefit_taper': 0.08, 'unemployment_rate': 0.05,
        'informal_share': 0.08, 'wage_dispersion_mult': 3.5,
        'skill_premium_growth': 0.003, 'union_coverage': 0.30,
        'capital_income_share': 0.06, 'import_competition': 0.05,
        'elite_capture_intensity': 0.02, 'inheritance_rate': 0.0,
        'gini_actual': 0.37,
    },
    2000: {
        'system_name': 'FR_2000', 'tax_type': 'income',
        'income_tax_rate': 0.42, 'corp_tax_rate': 0.36, 'welfare_rate': 0.16,
        'healthcare_gdp_share': 0.09, 'use_progressive_tax': True,
        'child_benefit_taper': 0.25, 'unemployment_rate': 0.09,
        'informal_share': 0.10, 'wage_dispersion_mult': 2.5,
        'skill_premium_growth': 0.005, 'union_coverage': 0.28,
        'capital_income_share': 0.08, 'import_competition': 0.10,
        'elite_capture_intensity': 0.03, 'inheritance_rate': 0.0,
        'gini_actual': 0.34,
    },
    2020: {
        'system_name': 'FR_2020', 'tax_type': 'income',
        'income_tax_rate': 0.45, 'corp_tax_rate': 0.25, 'welfare_rate': 0.20,
        'healthcare_gdp_share': 0.11, 'use_progressive_tax': True,
        'child_benefit_taper': 0.50, 'unemployment_rate': 0.08,
        'informal_share': 0.12, 'wage_dispersion_mult': 1.6,
        'skill_premium_growth': 0.008, 'union_coverage': 0.25,
        'capital_income_share': 0.12, 'import_competition': 0.15,
        'elite_capture_intensity': 0.05, 'inheritance_rate': 0.0,
        'gini_actual': 0.30,
    },
}

years = [1960, 1980, 2000, 2020]
all_pass = True
prev_gini = None
print(f"{'Period':<10} {'Sim Gini':>10} {'Actual':>8} {'Error':>8} {'Trend':>10}")
print("-" * 50)

for year in years:
    cfg = PERIODS[year]
    target = cfg['gini_actual']
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    gini = res['gini']
    err = abs(gini - target)
    err_pct = err / target * 100

    trend_str = ''
    if prev_gini is not None:
        delta = gini - prev_gini
        if delta < -0.01:
            trend_str = 'FALLING'
        elif delta > 0.01:
            trend_str = 'RISING'
        else:
            trend_str = 'STABLE'

    print(f"{year}s".ljust(10) + f" {gini:.4f} {target:.2f} {err_pct:.1f}% {trend_str:>10}")

    # Check level
    level_ok = err_pct < 10.0
    if not level_ok:
        print(f"  WARNING: {year}s level error {err_pct:.1f}% exceeds 10%")
        all_pass = False

    prev_gini = gini

# Overall trend (1960 to 2020)
cfg_60 = PERIODS[1960]
cfg_20 = PERIODS[2020]
w, r, b = gen_population(42)
res_60 = run_phase8(w, r, b, 42, cfg_60)
w2, r2, b2 = gen_population(42)
res_20 = run_phase8(w2, r2, b2, 42, cfg_20)
delta = res_20['gini'] - res_60['gini']
trend_overall = 'FALLING' if delta < -0.02 else ('RISING' if delta > 0.02 else 'STABLE')
print()
print(f"Overall 1960->2020 delta: {delta:.4f}")
print(f"Overall trend: {trend_overall} (need FALLING)")

assert trend_overall == 'FALLING', f"France trend should be FALLING, got {trend_overall}"
print()
print("=" * 60)
print(f"OVERALL: {trend_overall} | All levels within 10%: {all_pass}")
print("=" * 60)
