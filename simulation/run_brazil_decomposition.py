#!/usr/bin/env python3
"""Brazil decomposition — run quickly to see mechanism rankings."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

SEED = 42

BR_1960 = {
    'system_name': 'BR_1960', 'tax_type': 'income',
    'income_tax_rate': 0.15, 'corp_tax_rate': 0.30, 'welfare_rate': 0.05,
    'healthcare_gdp_share': 0.03,
    'skill_premium_growth': 0.001, 'union_coverage': 0.25,
    'capital_income_share': 0.15, 'import_competition': 0.02,
    'elite_capture_intensity': 0.30, 'patrimonial_wealth': 0.40,
    'informal_share': 0.45, 'wage_dispersion_mult': 2.0,
    'inheritance_rate': 0.0,
}

BR_2020 = {
    'system_name': 'BR_2020', 'tax_type': 'income',
    'income_tax_rate': 0.25, 'corp_tax_rate': 0.34, 'welfare_rate': 0.16,
    'healthcare_gdp_share': 0.06,
    'skill_premium_growth': 0.008, 'union_coverage': 0.20,
    'capital_income_share': 0.22, 'import_competition': 0.12,
    'elite_capture_intensity': 0.20, 'patrimonial_wealth': 0.2,
    'informal_share': 0.38, 'use_progressive_tax': True,
    'wage_dispersion_mult': 4.0, 'inheritance_rate': 0.0,
}

MECHS = [
    ('skill_premium_growth', 'SBTC'),
    ('union_coverage', 'Union Coverage'),
    ('capital_income_share', 'Financialization'),
    ('import_competition', 'Import Competition'),
    ('elite_capture_intensity', 'Elite Capture'),
    ('patrimonial_wealth', 'Patrimonial Wealth'),
    ('informal_share', 'Informal Sector'),
    ('use_progressive_tax', 'Progressive Tax'),
]

def make_config(base, key=None):
    cfg = dict(base)
    if key:
        if key == 'use_progressive_tax':
            cfg[key] = False
        else:
            cfg[key] = 0.0
    return cfg

# Full model
w1, r1, b1 = gen_population(SEED)
res_2020 = run_phase8(w1, r1, b1, SEED, BR_2020)
w0, r0, b0 = gen_population(SEED)
res_1960 = run_phase8(w0, r0, b0, SEED, BR_1960)
g60_full = res_1960['gini']
g20_full = res_2020['gini']
delta_full = g20_full - g60_full

print('=' * 60)
print('BRAZIL LEAVE-ONE-OUT DECOMPOSITION')
print('=' * 60)
print(f'Full model: {g60_full:.4f} -> {g20_full:.4f}  delta={delta_full:+.4f}')
print()

rankings = []
for key, label in MECHS:
    c60 = make_config(BR_1960, key)
    c20 = make_config(BR_2020, key)
    w, r, b = gen_population(SEED)
    r60 = run_phase8(w, r, b, SEED, c60)
    w2, r2, b2 = gen_population(SEED)
    r20 = run_phase8(w2, r2, b2, SEED, c20)
    delta = r20['gini'] - r60['gini']
    contrib = delta_full - delta
    rankings.append((abs(contrib), label, contrib))

rankings.sort(key=lambda x: -x[0])
print(f"{'Rank':>4} {'Mechanism':<25} {'Contrib':>10} {'% of Δ':>8}")
print('-' * 49)
for i, (_, label, contrib) in enumerate(rankings, 1):
    pct = abs(contrib) / max(abs(delta_full), 0.001) * 100
    print(f'{i:>4} {label:<25} {contrib:>+10.4f} {pct:>7.0f}%')
print('-' * 49)
print(f"{'Full delta':<25} {delta_full:>+10.4f}")

# Cross-country comparison
print()
print('=' * 60)
print('CROSS-COUNTRY: TOP 3 MECHANISMS')
print('=' * 60)
print(f"{'Rank':>4} {'US':<30} {'UK':<30} {'France':<30} {'Brazil':<30}")
print('-' * 94)
us_data = ['Import Comp (24%)', 'Import Disp (24%)', 'SBTC (20%)']
uk_data = ['Import Comp (15%)', 'Import Disp (15%)', 'SBTC (6%)']
fr_data = ['Prog Tax (179%)', 'SBTC (46%)', 'Import Comp (36%)']
br_data = []
for _, label, contrib in rankings[:3]:
    pct = abs(contrib) / max(abs(delta_full), 0.001) * 100
    br_data.append(f'{label} ({pct:.0f}%)')
for i in range(3):
    us = us_data[i] if i < len(us_data) else ''
    uk = uk_data[i] if i < len(uk_data) else ''
    fr = fr_data[i] if i < len(fr_data) else ''
    br = br_data[i] if i < len(br_data) else ''
    print(f'{i+1:>4} {us:<30} {uk:<30} {fr:<30} {br:<30}')
