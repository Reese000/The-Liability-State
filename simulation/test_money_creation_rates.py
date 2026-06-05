#!/usr/bin/env python3
"""Test money creation with varying rates."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population
import numpy as np

SEED = 42

US_BASELINE = {
    'system_name': 'US_test', 'tax_type': 'income',
    'income_tax_rate': 0.20, 'corp_tax_rate': 0.21, 'welfare_rate': 0.15,
    'healthcare_gdp_share': 0.18, 'use_progressive_tax': True,
    'skill_premium_growth': 0.015, 'union_coverage': 0.12,
    'capital_income_share': 0.22, 'import_competition': 0.20,
    'elite_capture_intensity': 0.20, 'informal_share': 0.08,
    'wage_dispersion_mult': 2.5, 'education_variance': 0.7,
    'inheritance_rate': 0.0,
    'reserve_requirement': 0.1,
}

print(f"{'Rate($/cap/yr)':>15} {'Wealth':>14} {'Gini':>8} {'MeanWage':>10} {'Wealth+%':>10} {'GiniΔ':>8}")
print("-" * 70)

w_off, r_off, b_off = gen_population(SEED)
res_off = run_phase8(w_off, r_off, b_off, SEED, US_BASELINE)
print(f"{'0 (baseline)':>15} {res_off['wealth']:>14,} {res_off['gini']:>8.4f} {res_off['w_mean']:>10,.0f} {'0.00%':>10} {'—':>8}")

for rate in [500, 1000, 2000, 5000, 10000, 25000, 50000]:
    cfg = dict(US_BASELINE, money_creation_rate=rate)
    w, r, b = gen_population(SEED)
    res = run_phase8(w, r, b, SEED, cfg)
    wealth_pct = (res['wealth'] - res_off['wealth']) / res_off['wealth'] * 100
    gini_delta = res['gini'] - res_off['gini']
    print(f"{rate:>15,} {res['wealth']:>14,} {res['gini']:>8.4f} {res['w_mean']:>10,.0f} {wealth_pct:>+9.2f}% {gini_delta:>+8.4f}")
