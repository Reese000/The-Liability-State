#!/usr/bin/env python3
"""
run_multicountry_decomposition.py — Leave-one-out decomposition for UK and France.

Runs the same methodology as run_us_decomposition.py but for UK and France.
Exports results for cross-country comparison.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

SEED = 42

# ── UK configs (from validate_uk_backtest.py) ──
UK_1960 = {
    'system_name': 'UK_1960', 'tax_type': 'income',
    'income_tax_rate': 0.25, 'corp_tax_rate': 0.50, 'welfare_rate': 0.04,
    'healthcare_gdp_share': 0.04,
    'skill_premium_growth': 0.008, 'union_coverage': 0.40,
    'capital_income_share': 0.05, 'import_competition': 0.02,
    'import_displacement_rate': 0.02,
    'use_progressive_tax': True, 'housing_wealth_concentration': 0.15,
    'financial_services_premium': 0.10, 'education_variance': 0.5,
    'wage_dispersion_mult': 1.0, 'inheritance_rate': 0.0,
}
UK_2020 = {
    'system_name': 'UK_2020', 'tax_type': 'income',
    'income_tax_rate': 0.25, 'corp_tax_rate': 0.19, 'welfare_rate': 0.12,
    'healthcare_gdp_share': 0.10,
    'skill_premium_growth': 0.018, 'union_coverage': 0.22,
    'capital_income_share': 0.18, 'import_competition': 0.15,
    'import_displacement_rate': 0.20,
    'use_progressive_tax': True, 'housing_wealth_concentration': 0.40,
    'financial_services_premium': 0.25, 'education_variance': 0.5,
    'wage_dispersion_mult': 2.0, 'inheritance_rate': 0.0,
}

# ── France configs (from validate_france_backtest.py) ──
FR_1960 = {
    'system_name': 'FR_1960', 'tax_type': 'income',
    'income_tax_rate': 0.25, 'corp_tax_rate': 0.50, 'welfare_rate': 0.05,
    'healthcare_gdp_share': 0.04, 'use_progressive_tax': True,
    'skill_premium_growth': 0.001, 'union_coverage': 0.25,
    'capital_income_share': 0.04, 'import_competition': 0.03,
    'import_displacement_rate': 0.02,
    'child_benefit_taper': 0.02, 'unemployment_rate': 0.02,
    'informal_share': 0.08, 'wage_dispersion_mult': 3.3,
    'elite_capture_intensity': 0.02, 'inheritance_rate': 0.0,
}
FR_2020 = {
    'system_name': 'FR_2020', 'tax_type': 'income',
    'income_tax_rate': 0.45, 'corp_tax_rate': 0.25, 'welfare_rate': 0.20,
    'healthcare_gdp_share': 0.11, 'use_progressive_tax': True,
    'skill_premium_growth': 0.008, 'union_coverage': 0.25,
    'capital_income_share': 0.12, 'import_competition': 0.15,
    'import_displacement_rate': 0.15,
    'child_benefit_taper': 0.50, 'unemployment_rate': 0.08,
    'informal_share': 0.12, 'wage_dispersion_mult': 1.6,
    'elite_capture_intensity': 0.05, 'inheritance_rate': 0.0,
}

MECHANISMS = [
    ('skill_premium_growth', 'Skill Premium (SBTC)'),
    ('union_coverage', 'Union Coverage'),
    ('capital_income_share', 'Financialization'),
    ('import_competition', 'Import Competition'),
    ('import_displacement_rate', 'Import Displacement'),
    ('use_progressive_tax', 'Progressive Tax'),
]

def make_config(base, toggle_off=None):
    cfg = dict(base)
    if toggle_off:
        key = toggle_off
        if key == 'use_progressive_tax':
            cfg[key] = False
        elif key in ('skill_premium_growth', 'union_coverage',
                     'capital_income_share', 'import_competition',
                     'import_displacement_rate'):
            cfg[key] = 0.0
    return cfg

def run_pair(cfg_60, cfg_20):
    w1, r1, b1 = gen_population(SEED)
    res1 = run_phase8(w1, r1, b1, SEED, cfg_60)
    w2, r2, b2 = gen_population(SEED)
    res2 = run_phase8(w2, r2, b2, SEED, cfg_20)
    return res1['gini'], res2['gini']

def decompose(name, cfg_60, cfg_20):
    print(f"\n{'='*70}")
    print(f"  {name} LEAVE-ONE-OUT")
    print(f"{'='*70}")
    
    g60_full, g20_full = run_pair(cfg_60, cfg_20)
    delta_full = g20_full - g60_full
    print(f"  Full model: {g60_full:.4f} → {g20_full:.4f}  delta={delta_full:+.4f}")
    
    results = {'full_gini_1960': g60_full, 'full_gini_2020': g20_full, 'full_delta': delta_full}
    contribs = {}
    
    for key, label in MECHANISMS:
        c60 = make_config(cfg_60, key)
        c20 = make_config(cfg_20, key)
        g60, g20 = run_pair(c60, c20)
        delta = g20 - g60
        contrib = delta_full - delta
        contribs[key] = contrib
        results[f'no_{key}'] = {'gini_1960': g60, 'gini_2020': g20, 'delta': delta, 'contribution': contrib}
        print(f"  No {label:<30} {g60:.4f}→{g20:.4f} delta={delta:+.4f} contrib={contrib:+.4f}")
    
    # Ranking with interaction term
    print(f"\n{'Rank':>4} {'Mechanism':<30} {'Contrib':>10} {'% of Δ':>8}")
    print("-" * 54)
    ranked = sorted(contribs.items(), key=lambda x: -abs(x[1]))
    contrib_sum = sum(abs(v) for v in contribs.values())
    for i, (key, contrib) in enumerate(ranked, 1):
        label = dict(MECHANISMS)[key]
        pct = abs(contrib) / max(abs(delta_full), 0.001) * 100
        print(f"{i:>4} {label:<30} {contrib:>+10.4f} {pct:>7.0f}%")
    # Interaction term: leave-one-out contributions may not sum to |delta_full|
    # because mechanisms interact non-additively. Report the residual.
    abs_sum = sum(abs(v) for v in contribs.values())
    if abs(abs_sum - abs(delta_full)) > 0.001:
        interaction = abs(delta_full) - abs_sum
        print(f"{'':>4} {'[Interaction/residual]':<30} {interaction:>+10.4f} {'--':>8}")
    print("-" * 54)
    print(f"{'Full |delta|':<30} {abs(delta_full):>10.4f}")
    print(f"{'NOTE:':<30} Leave-one-out contributions measure MARGINAL effect of each")
    print(f"{'':<30} mechanism. Due to interaction effects, |contributions| may not")
    
    return results

def main():
    os.makedirs("output", exist_ok=True)
    all_results = {}
    
    all_results['UK'] = decompose('UK', UK_1960, UK_2020)
    all_results['France'] = decompose('France', FR_1960, FR_2020)
    
    # Cross-country table
    print(f"\n{'='*70}")
    print(f"  CROSS-COUNTRY COMPARISON (% contribution to Gini rise)")
    print(f"{'='*70}")
    print(f"{'Mechanism':<30} {'US':>8} {'UK':>8} {'France':>8}")
    print("-" * 56)
    
    # US data from the full US decomposition run
    us_contribs = {
        'import_competition': 0.0259,
        'import_displacement_rate': 0.0256,
        'skill_premium_growth': 0.0220,
        'financialization': 0.0064,
        'union_coverage': 0.0054,
        'use_progressive_tax': -0.0050,
    }
    us_delta = 0.1081
    
    for key, label in MECHANISMS:
        us_pct = abs(us_contribs.get(key, 0)) / abs(us_delta) * 100
        uk_pct = abs(all_results['UK']['no_' + key]['contribution']) / abs(all_results['UK']['full_delta']) * 100
        fr_pct = abs(all_results['France']['no_' + key]['contribution']) / abs(all_results['France']['full_delta']) * 100
        print(f"{label:<30} {us_pct:>7.0f}% {uk_pct:>7.0f}% {fr_pct:>7.0f}%")
    
    print("-" * 56)
    print(f"{'Full Gini delta':<30} {us_delta:>+8.4f} {all_results['UK']['full_delta']:>+8.4f} {all_results['France']['full_delta']:>+8.4f}")
    
    import json
    with open("output/multicountry_decomposition.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Saved: output/multicountry_decomposition.json")

if __name__ == '__main__':
    sys.exit(main())
