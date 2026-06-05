#!/usr/bin/env python3
"""
run_us_decomposition.py — US Leave-One-Out Decomposition (Phase 5).

Runs the US backtest (1960→2020) with 5 inequality mechanisms toggled
individually. Ranks each mechanism by its contribution to the Gini rise.

Mechanisms (all default OFF in the engine):
  A: skill_premium_growth (SBTC)
  B: union_coverage
  C: capital_income_share (financialization)
  D: import_competition
  E: use_progressive_tax (progressive taxes, ON = REDUCES inequality)

Method:
  1. Full model (all 5 ON) → Gini rise from 1960 to 2020
  2. Leave-one-out: toggle each mechanism OFF while keeping others ON
  3. Contribution = Gini delta(full) - Gini delta(leave-out)
  4. Rank by absolute contribution magnitude

Usage:
    python run_us_decomposition.py
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

TREND_THRESHOLD = 0.02
SEED = 42

# US 2020 config with all 5 mechanisms ON
US_1960 = {
    'system_name': 'US_1960', 'tax_type': 'income',
    'income_tax_rate': 0.25, 'corp_tax_rate': 0.50, 'welfare_rate': 0.04,
    'healthcare_gdp_share': 0.05, 'use_progressive_tax': True,
    'skill_premium_growth': 0.003, 'union_coverage': 0.35,
    'capital_income_share': 0.05, 'import_competition': 0.02,
    'import_displacement_rate': 0.03,  # Low in 1960s
    'elite_capture_intensity': 0.05, 'informal_share': 0.05,
    'wage_dispersion_mult': 2.0, 'education_variance': 0.5,
    'inheritance_rate': 0.0, 'gini_actual': 0.36,
}

US_2020 = {
    'system_name': 'US_2020', 'tax_type': 'income',
    'income_tax_rate': 0.20, 'corp_tax_rate': 0.21, 'welfare_rate': 0.15,
    'healthcare_gdp_share': 0.18, 'use_progressive_tax': True,
    'skill_premium_growth': 0.015, 'union_coverage': 0.12,
    'capital_income_share': 0.22, 'import_competition': 0.20,
    'import_displacement_rate': 0.25,  # China shock peak: 25% annual displacement risk
    'elite_capture_intensity': 0.20, 'informal_share': 0.08,
    'wage_dispersion_mult': 2.5, 'education_variance': 0.7,
    'inheritance_rate': 0.0, 'gini_actual': 0.42,
}

# 5 inequality mechanisms plus the new displacement channel
MECHANISMS = {
    'skill_premium_growth': 'Skill Premium (SBTC)',
    'union_coverage':       'Union Coverage',
    'capital_income_share': 'Financialization',
    'import_competition':   'Import Competition',
    'import_displacement_rate': 'Import Displacement',
    'use_progressive_tax':  'Progressive Tax',
}

def make_config(base, toggle_off=None):
    """Create a config dict, optionally with one mechanism toggled OFF."""
    cfg = dict(base)
    if toggle_off:
        key = toggle_off
        if key == 'use_progressive_tax':
            cfg[key] = False
        elif key in ('skill_premium_growth', 'union_coverage',
                     'capital_income_share', 'import_competition',
                     'import_displacement_rate'):
            cfg[key] = 0.0
        else:
            raise ValueError(f"Unknown mechanism: {key}")
    return cfg

def run_us_pair(cfg_1960, cfg_2020, label):
    """Run US 1960 and 2020, return (gini_1960, gini_2020, delta)."""
    w1, r1, b1 = gen_population(SEED)
    res1 = run_phase8(w1, r1, b1, SEED, cfg_1960)
    w2, r2, b2 = gen_population(SEED)
    res2 = run_phase8(w2, r2, b2, SEED, cfg_2020)
    g60 = res1['gini']
    g20 = res2['gini']
    delta = g20 - g60
    print(f"  {label:<35} Gini: {g60:.4f} → {g20:.4f}  delta={delta:+.4f}")
    return g60, g20, delta

def classify_trend(delta):
    if abs(delta) <= TREND_THRESHOLD:
        return 'STABLE'
    return 'RISING' if delta > 0 else 'FALLING'

def main():
    os.makedirs("output", exist_ok=True)
    results = {}
    
    print("=" * 80)
    print("  US LEAVE-ONE-OUT DECOMPOSITION (Phase 5)")
    print("=" * 80)
    print()
    
    # ── Step 1: Full model (all 5 mechanisms ON) ──
    print("--- Full Model (all 5 ON) ---")
    g60_full, g20_full, delta_full = run_us_pair(US_1960, US_2020, "All 5 mechanisms ON")
    print(f"  Overall Gini delta: {delta_full:+.4f} ({classify_trend(delta_full)})")
    results['full_model'] = {
        'gini_1960': round(g60_full, 4),
        'gini_2020': round(g20_full, 4),
        'delta': round(delta_full, 4),
        'trend': classify_trend(delta_full),
    }
    print()
    
    # ── Step 2: Leave-one-out runs ──
    print("--- Leave-One-Out (each mechanism OFF) ---")
    contributions = {}
    
    for key, label in MECHANISMS.items():
        # Create configs with this mechanism OFF
        cfg_60_off = make_config(US_1960, key)
        cfg_20_off = make_config(US_2020, key)
        
        leave_label = f"No {label}"
        g60_lo, g20_lo, delta_lo = run_us_pair(cfg_60_off, cfg_20_off, leave_label)
        
        # Contribution = delta_full - delta_lo
        # If removing the mechanism reduces the Gini rise, contribution > 0
        # If removing the mechanism increases the Gini rise (e.g., progressive tax), contribution < 0
        contribution = delta_full - delta_lo
        
        results[f'no_{key}'] = {
            'gini_1960': round(g60_lo, 4),
            'gini_2020': round(g20_lo, 4),
            'delta': round(delta_lo, 4),
            'trend': classify_trend(delta_lo),
            'contribution': round(contribution, 4),
        }
        contributions[key] = contribution
        
        contrib_label = "+" if contribution > 0 else ""
        print(f"    Contribution to Gini rise: {contrib_label}{contribution:.4f}")
        print()
    
    # ── Step 3: Counterfactuals ──
    print("--- Counterfactuals ---")
    
    # What if 2020 had 1960's tax rates (low welfare)?
    cfg_no_welfare = dict(US_2020, welfare_rate=0.04, income_tax_rate=0.25)
    _, _, delta_no_welfare = run_us_pair(US_1960, cfg_no_welfare, "2020 w/ 1960 tax+welfare")
    
    # What if 2020 had 1960's union coverage + no SBTC?
    cfg_low_inequality = dict(US_2020, union_coverage=0.35, skill_premium_growth=0.003,
                              capital_income_share=0.05, import_competition=0.02)
    _, _, delta_low = run_us_pair(US_1960, cfg_low_inequality, "2020 w/ 1960 inequality params")
    
    results['counterfactual_no_welfare'] = {'delta': round(delta_no_welfare, 4)}
    results['counterfactual_low_inequality'] = {'delta': round(delta_low, 4)}
    
    # ── Step 4: Ranking ──
    print()
    print("=" * 80)
    print("  RANKING: Contribution to Gini Rise (US 1960→2020)")
    print("  Positive = mechanism INCREASED inequality")
    print("  Negative = mechanism DECREASED inequality")
    print("=" * 80)
    
    ranked = sorted(contributions.items(), key=lambda x: -abs(x[1]))
    
    print(f"{'Rank':>4} {'Mechanism':<30} {'Contribution':>14} {'Effect':>10}")
    print("-" * 60)
    for i, (key, contrib) in enumerate(ranked, 1):
        label = MECHANISMS[key]
        effect = "↑ Inequality" if contrib > 0 else ("↓ Inequality" if contrib < 0 else "Neutral")
        print(f"{i:>4} {label:<30} {contrib:>+12.4f} {effect:>10}")
    
    print("-" * 60)
    print(f"{'Gini delta (full model)':<30} {delta_full:>+12.4f}")
    print()
    
    # ── Step 5: Summary ──
    print("=" * 80)
    print("  FINDINGS")
    print("=" * 80)
    print(f"  Full model: Gini rises {delta_full:.4f} ({g60_full:.4f} → {g20_full:.4f})")
    print()
    
    for key, contrib in ranked:
        label = MECHANISMS[key]
        pct = abs(contrib) / max(abs(delta_full), 0.001) * 100 if delta_full != 0 else 0
        direction = "RAISES" if contrib > 0 else "LOWERS" if contrib < 0 else "No effect"
        print(f"  {label:<30}: {direction} Gini by {abs(contrib):.4f} ({pct:.0f}% of full delta)")
    
    print()
    print(f"  Counterfactual: 2020 w/ 1960 tax+welfare     delta={delta_no_welfare:.4f}")
    print(f"  Counterfactual: 2020 w/ 1960 inequality      delta={delta_low:.4f}")
    
    # Save
    with open("output/us_decomposition_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: output/us_decomposition_results.json")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
