#!/usr/bin/env python3
"""Unit tests for the 4 new inequality mechanisms."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from missing_mechanisms import (
    apply_structural_gap, apply_power_law_wealth,
    apply_immigrant_wedge, apply_inheritance_conc
)

pass_count = 0
fail_count = 0

def check(name, condition, detail=""):
    global pass_count, fail_count
    if condition:
        pass_count += 1
        print(f"  PASS: {name}")
    else:
        fail_count += 1
        print(f"  FAIL: {name} -- {detail}")

rng = np.random.RandomState(42)
workers = [{'id': f'w{i}', 'hourly': 20.0, 'monthly': 3200.0, 'cash': 50000.0} for i in range(100)]
bal = {w['id']: 50000.0 for w in workers}
bal['sys'] = 500_000_000

# --- Test Structural Gap ---
config = {'use_structural_gap': True, 'structural_gap_groups': [0.8, 0.2], 'structural_gap_multipliers': [1.0, 0.1], 'structural_gap_recurrence': 0.2}
r = apply_structural_gap(config, rng, workers, [], [], bal, 1, {})
check("structural_gap returns initialized", r.get('gap_initialized'))
gap_group = [w for w in workers if w.get('_gap_mult', 1.0) < 0.5]
majority = [w for w in workers if w.get('_gap_mult', 1.0) >= 0.5]
check("gap group ~20 workers", len(gap_group) == 20)
gap_wealth = np.mean([bal[w['id']] for w in gap_group]) if gap_group else 0
maj_wealth = np.mean([bal[w['id']] for w in majority]) if majority else 0
check("gap wealth ~10% of majority", abs(gap_wealth/maj_wealth - 0.1) < 0.02 if maj_wealth > 0 else False)

r = apply_structural_gap(config, rng, workers, [], [], bal, 13, {})
check("gap recurrence at step 13", 'gap_recurrence_effect' in r)
r = apply_structural_gap(config, rng, workers, [], [], bal, 2, {})
check("gap no recurrence at non-annual step", r == {})

# --- Test Power-law ---
config_pl = {'use_power_law_wealth': True, 'power_law_exponent': 0.3, 'wealth_tail_fraction': 0.01}
# Give wealth diversity: one very wealthy worker > median for nonzero premium
bal['w0'] = 2_000_000
r = apply_power_law_wealth(config_pl, rng, workers, [], [], bal, 1, {})
check("power_law initializes at step 1", 'power_law_premium' in r)
r = apply_power_law_wealth(config_pl, rng, workers, [], [], bal, 13, {})
check("power_law premium > 0", r.get('power_law_premium', 0) > 0)
check("power_law top share > 0", r.get('power_law_top_share', 0) > 0)
r = apply_power_law_wealth(config_pl, rng, workers, [], [], bal, 14, {})
check("power_law annual only (step 14 skipped)", r == {})

# --- Test Immigrant Wedge ---
config_im = {'use_immigrant_labor': True, 'immigrant_share': 0.15, 'immigrant_wage_penalty': 0.4}
for w in workers:
    w['hourly'] = 20.0
    w['monthly'] = 3200.0
r = apply_immigrant_wedge(config_im, rng, workers, [], [], bal, 1, {})
check("immigrant wedge initializes", 'immigrant_workers' in r)
imm = [w['hourly'] for w in workers if w.get('_immigrant')]
non = [w['hourly'] for w in workers if not w.get('_immigrant')]
ratio = np.mean(imm)/np.mean(non) if non else 0
check("immigrant wage ratio ~0.6", abs(ratio - 0.6) < 0.05)

# --- Test Inheritance ---
for w in workers:
    bal[w['id']] = rng.uniform(1000, 500000)
r = apply_inheritance_conc({'inheritance_flow_fraction': 0.0, 'inheritance_concentration': 0.85}, rng, workers, [], [], bal, 13, {})
check("inheritance disabled with flow=0", r == {})
r = apply_inheritance_conc({'inheritance_flow_fraction': 0.02, 'inheritance_concentration': 0.85}, rng, workers, [], [], bal, 13, {})
check("inheritance pool > 0", r.get('inheritance_pool', 0) > 0)

# --- Edge cases ---
r = apply_power_law_wealth(config_pl, rng, [], [], [], bal, 13, {})
check("power_law no workers returns {}", r == {})
r = apply_immigrant_wedge({'use_immigrant_labor': True, 'immigrant_share': 0.15, 'immigrant_wage_penalty': 0.0}, rng, workers, [], [], bal, 1, {})
check("immigrant wedge zero penalty returns {}", r == {})
r = apply_structural_gap({'use_structural_gap': True, 'structural_gap_groups': [0.8], 'structural_gap_multipliers': [1.0, 0.1]}, rng, workers, [], [], bal, 1, {})
check("structural gap mismatched groups", r == {})

print(f"\nResults: {pass_count} passed, {fail_count} failed")
if fail_count == 0:
    print("ALL UNIT TESTS PASSED")
else:
    print("SOME TESTS FAILED")
