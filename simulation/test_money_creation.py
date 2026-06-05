#!/usr/bin/env python3
"""Test that money creation now has non-zero Gini effect."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

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

print("=" * 60)
print("MONEY CREATION EFFECT TEST")
print("=" * 60)

# Test with money creation OFF (baseline)
cfg_off = dict(US_BASELINE, money_creation_rate=0.0)
w, r, b = gen_population(SEED)
res_off = run_phase8(w, r, b, SEED, cfg_off)
print(f"\nMoney creation OFF:")
print(f"  Total wealth: ${res_off['wealth']:,.0f}")
print(f"  Gini: {res_off['gini']:.4f}")
print(f"  Mean wage: ${res_off['w_mean']:,.0f}")

# Test with money creation ON ($1000 per-capita annual)
cfg_on = dict(US_BASELINE, money_creation_rate=1000.0)
w2, r2, b2 = gen_population(SEED)
res_on = run_phase8(w2, r2, b2, SEED, cfg_on)
print(f"\nMoney creation ON ($1000/capita annual):")
print(f"  Total wealth: ${res_on['wealth']:,.0f}")
print(f"  Gini: {res_on['gini']:.4f}")
print(f"  Mean wage: ${res_on['w_mean']:,.0f}")

# Compare
wealth_diff_pct = (res_on['wealth'] - res_off['wealth']) / res_off['wealth'] * 100
gini_diff = res_on['gini'] - res_off['gini']
print(f"\n--- Effect ---")
print(f"  Wealth increase: {wealth_diff_pct:+.2f}%")
print(f"  Gini change: {gini_diff:+.4f}")

if wealth_diff_pct > 1.0:
    print(f"\n✅ WEALTH EFFECT: {wealth_diff_pct:.2f}% > 1% — money creation now meaningful")
else:
    print(f"\n❌ WEALTH EFFECT: {wealth_diff_pct:.2f}% <= 1% — still too weak")

if abs(gini_diff) > 0.001:
    print(f"✅ GINI EFFECT: |{gini_diff:.4f}| > 0.001 — money creation now affects inequality")
else:
    print(f"❌ GINI EFFECT: |{gini_diff:.4f}| <= 0.001 — still Gini-invariant")
