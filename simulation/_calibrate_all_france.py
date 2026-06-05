#!/usr/bin/env python3
"""Calibrate all 4 France periods with period-varying wage_disp."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase8 import run_phase8, gen_population

TARGETS = {1960: 0.35, 1980: 0.37, 2000: 0.34, 2020: 0.30}

CONFIGS = {
    1960: {
        'system_name': 'FR_1960', 'tax_type': 'income',
        'income_tax_rate': 0.25, 'corp_tax_rate': 0.50, 'welfare_rate': 0.05,
        'healthcare_gdp_share': 0.04, 'use_progressive_tax': True,
        'child_benefit_taper': 0.02, 'unemployment_rate': 0.02,
        'informal_share': 0.08, 'inheritance_rate': 0.0,
    },
    1980: {
        'system_name': 'FR_1980', 'tax_type': 'income',
        'income_tax_rate': 0.30, 'corp_tax_rate': 0.50, 'welfare_rate': 0.10,
        'healthcare_gdp_share': 0.06, 'use_progressive_tax': True,
        'child_benefit_taper': 0.08, 'unemployment_rate': 0.05,
        'informal_share': 0.08, 'inheritance_rate': 0.0,
        'skill_premium_growth': 0.003, 'union_coverage': 0.30,
        'capital_income_share': 0.06, 'import_competition': 0.05,
        'elite_capture_intensity': 0.02,
    },
    2000: {
        'system_name': 'FR_2000', 'tax_type': 'income',
        'income_tax_rate': 0.42, 'corp_tax_rate': 0.36, 'welfare_rate': 0.16,
        'healthcare_gdp_share': 0.09, 'use_progressive_tax': True,
        'child_benefit_taper': 0.25, 'unemployment_rate': 0.09,
        'informal_share': 0.10, 'inheritance_rate': 0.0,
        'skill_premium_growth': 0.005, 'union_coverage': 0.28,
        'capital_income_share': 0.08, 'import_competition': 0.10,
        'elite_capture_intensity': 0.03,
    },
    2020: {
        'system_name': 'FR_2020', 'tax_type': 'income',
        'income_tax_rate': 0.45, 'corp_tax_rate': 0.25, 'welfare_rate': 0.20,
        'healthcare_gdp_share': 0.11, 'use_progressive_tax': True,
        'child_benefit_taper': 0.50, 'unemployment_rate': 0.08,
        'informal_share': 0.12, 'inheritance_rate': 0.0,
        'skill_premium_growth': 0.008, 'union_coverage': 0.25,
        'capital_income_share': 0.12, 'import_competition': 0.15,
        'elite_capture_intensity': 0.05,
    },
}

print("=" * 70)
print("FRANCE PERIOD CALIBRATION")
print("=" * 70)

wage_disp_range = {
    1960: [3.0, 3.2, 3.3, 3.4, 3.5],
    1980: [2.5, 2.8, 3.0, 3.2, 3.5],
    2000: [2.0, 2.2, 2.5, 2.8, 3.0],
    2020: [1.4, 1.5, 1.6, 1.7, 1.8],
}

results = {}
for year in [1960, 1980, 2000, 2020]:
    target = TARGETS[year]
    cfg_base = CONFIGS[year]
    print(f"\n--- {year}s (target Gini={target}) ---")
    best = (0, 0, 999)
    for wd in wage_disp_range[year]:
        cfg = dict(cfg_base, wage_dispersion_mult=wd)
        w, r, b = gen_population(42)
        res = run_phase8(w, r, b, 42, cfg)
        err = abs(res['gini'] - target)
        flag = " <<<" if err < 0.01 else ""
        print(f"  d={wd:.1f} -> Gini={res['gini']:.4f} err={err:.4f}{flag}")
        if err < best[2]:
            best = (wd, res['gini'], err)
    results[year] = best
    print(f"  BEST: d={best[0]} -> Gini={best[1]:.4f} err={best[2]:.4f}")

# Full 4-period trend check
print("\n" + "=" * 70)
print("FULL 4-PERIOD TREND")
print("=" * 70)
prev_gini = None
trends = []
for year in [1960, 1980, 2000, 2020]:
    wd, gini, err = results[year]
    cfg = dict(CONFIGS[year], wage_dispersion_mult=wd)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    gini_val = res['gini']
    target = TARGETS[year]
    pct_err = f"{abs(gini_val - target)/target*100:.1f}%"
    if prev_gini is not None:
        delta = gini_val - prev_gini
        trend = 'RISING' if delta > 0.01 else ('FALLING' if delta < -0.01 else 'STABLE')
        trends.append(trend)
        print(f"  {year}s: d={wd:.1f} Gini={gini_val:.4f} (target {target}) err={pct_err} delta={delta:+.4f} trend={trend}")
    else:
        print(f"  {year}s: d={wd:.1f} Gini={gini_val:.4f} (target {target}) err={pct_err}")
    prev_gini = gini_val

# Overall trend (first to last)
total_delta = None
# Get actual values
vals = []
for year in [1960, 1980, 2000, 2020]:
    wd, gini, err = results[year]
    cfg = dict(CONFIGS[year], wage_dispersion_mult=wd)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    vals.append(res['gini'])

delta_60_20 = vals[3] - vals[0]
print(f"\n  Overall 1960->2020 delta: {delta_60_20:+.4f}")
overall_trend = 'FALLING' if delta_60_20 < -0.02 else ('RISING' if delta_60_20 > 0.02 else 'STABLE')
print(f"  Overall trend: {overall_trend} (need FALLING)")

# Final calibrated params
print("\n" + "=" * 70)
print("CALIBRATED PARAMS")
print("=" * 70)
for year in [1960, 1980, 2000, 2020]:
    wd, gini, err = results[year]
    print(f"  {year}s: wage_dispersion_mult={wd:.1f} # Gini {gini:.4f} vs target {TARGETS[year]}")
