#!/usr/bin/env python3
"""Stress-test the Phase 5 simulation with extreme parameter values.

Tests 4 stress configurations across all systems x 3 seeds (42, 43, 44).
Reports which systems crash or produce invalid results (NaN, negative wealth, exception).

Stress configs:
  STRESS_CORRUPT:  corruption=1.0, enforcement=0
  STRESS_MONOPOLY: monopoly_markup_max=5.0
  STRESS_BANKING:  banking_multiplier=20, interest_rate=0.05
  STRESS_COMBO:    all extremes together
"""

import sys
import os
import copy
import math
import json
import traceback

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# ─── Imports ──────────────────────────────────────────────
from comparison_phase4 import gen_population
from comparison_phase5 import PHASE5_CONFIGS, run_phase5

# ─── Reduce steps for speed ───────────────────────────────
# run_phase5 reads STEPS from its module globals, so we can
# override it here before calling the function.
import comparison_phase5 as _cp5
_cp5.STEPS = 48  # 48 steps instead of 480 (~1/10 length, still covers dynamics)

STEPS = _cp5.STEPS

# ─── Stress configurations ───────────────────────────────
STRESS_CONFIGS = {
    'STRESS_CORRUPT': {
        'corruption_level': 1.0,
        'enforcement_quality': 0.0,
    },
    'STRESS_MONOPOLY': {
        'monopoly_markup_max': 5.0,
    },
    'STRESS_BANKING': {
        'banking_multiplier': 20,
        'interest_rate': 0.05,
    },
    'STRESS_COMBO': {
        'corruption_level': 1.0,
        'enforcement_quality': 0.0,
        'monopoly_markup_max': 5.0,
        'banking_multiplier': 20,
        'interest_rate': 0.05,
    },
}

SEEDS = [42, 43, 44]


def is_valid_result(r):
    """Check if a simulation result is valid.

    Returns (True, 'OK') if valid, or (False, reason) if invalid.
    """
    if r is None:
        return False, "result is None"

    for key in ('gini', 'wealth', 'w_mean', 'w_min', 'w_max'):
        val = r.get(key)
        if val is None:
            return False, f"missing key '{key}'"
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return False, f"NaN/Inf in '{key}'"

    if r.get('wealth', 0) < 0:
        return False, "negative total wealth"

    if r.get('w_min', 0) < 0:
        return False, "negative min worker wealth"

    return True, "OK"


def main():
    results = []

    header = (
        f"  STRESS TEST: Phase 5 Simulation \u2014 Extreme Parameter Values\n"
        f"  Systems: {len(PHASE5_CONFIGS)}  |  Seeds: {SEEDS}  |  "
        f"Stress configs: {len(STRESS_CONFIGS)}\n"
        f"  Steps: {STEPS} (reduced from 480 for speed)"
    )
    rule = "=" * 130

    print(rule)
    print(header)
    print(rule)

    for stress_name, stress_params in STRESS_CONFIGS.items():
        dash = "\u2500" * 130
        print(f"\n{dash}")
        print(f"  Stress Config: {stress_name}")
        print(f"    Parameters: {stress_params}")
        print(f"{dash}")

        for sys_name in sorted(PHASE5_CONFIGS.keys()):
            base_cfg = PHASE5_CONFIGS[sys_name]

            for seed in SEEDS:
                # Fresh copy of config with stress overrides
                cfg = copy.deepcopy(base_cfg)
                cfg.update(stress_params)

                # Generate population
                workers, retirees, businesses = gen_population(seed)

                # Run simulation
                status = "CRASH"
                gini_val = None
                wealth_val = None
                error_msg = ""

                try:
                    result = run_phase5(workers, retirees, businesses,
                                        seed, cfg)
                    valid, reason = is_valid_result(result)
                    if valid:
                        status = "OK"
                    else:
                        status = "INVALID"
                        error_msg = reason
                    gini_val = result.get('gini')
                    wealth_val = result.get('wealth')
                except Exception as e:
                    status = "CRASH"
                    error_msg = f"{type(e).__name__}: {e}"
                    # Print traceback for debugging, but keep going
                    traceback.print_exc()

                results.append({
                    'system': sys_name,
                    'stress': stress_name,
                    'seed': seed,
                    'status': status,
                    'gini': gini_val,
                    'wealth': wealth_val,
                    'error': error_msg,
                })

                # Print result line
                gini_s = f"{gini_val:.4f}" if gini_val is not None else "  N/A  "
                wealth_s = (f"${wealth_val:>12,.0f}"
                            if wealth_val is not None else "     N/A      ")
                extra = f"  |  {error_msg}" if error_msg else ""
                print(f"  {sys_name:<24} | {stress_name:<16} | "
                      f"s{seed} | {status:<8} | G={gini_s} | "
                      f"W={wealth_s}{extra}")

    # ════════════════════════════════════════════════════════
    #  Summary
    # ════════════════════════════════════════════════════════
    print(f"\n{rule}")
    print("  SUMMARY")
    print(rule)

    total = len(results)
    ok_count = sum(1 for r in results if r['status'] == 'OK')
    crash_count = sum(1 for r in results if r['status'] == 'CRASH')
    invalid_count = sum(1 for r in results if r['status'] == 'INVALID')

    print(f"  Total runs: {total}")
    print(f"  OK:         {ok_count:>4} ({ok_count/total*100:.1f}%)")
    print(f"  CRASH:      {crash_count:>4} ({crash_count/total*100:.1f}%)")
    print(f"  INVALID:    {invalid_count:>4} ({invalid_count/total*100:.1f}%)")

    if crash_count > 0 or invalid_count > 0:
        print(f"\n  \u2500\u2500\u2500 Failures \u2500\u2500\u2500")
        for r in results:
            if r['status'] != 'OK':
                print(f"  {r['system']:<24} | {r['stress']:<16} | "
                      f"s{r['seed']} | {r['status']:<8} | {r['error']}")

    # Per-stress summary
    print(f"\n  \u2500\u2500\u2500 Per Stress Config \u2500\u2500\u2500")
    hdr = f"  {'Stress Config':<20} {'OK':>4} {'CRASH':>6} {'INVALID':>8} {'Total':>6}"
    print(hdr)
    print(f"  {'-' * len(hdr)}")
    for sn in STRESS_CONFIGS:
        sr = [r for r in results if r['stress'] == sn]
        sok = sum(1 for r in sr if r['status'] == 'OK')
        scr = sum(1 for r in sr if r['status'] == 'CRASH')
        sinv = sum(1 for r in sr if r['status'] == 'INVALID')
        print(f"  {sn:<20} {sok:>4} {scr:>6} {sinv:>8} {len(sr):>6}")

    # Per-system summary
    print(f"\n  \u2500\u2500\u2500 Per System \u2500\u2500\u2500")
    hdr2 = f"  {'System':<24} {'OK':>4} {'CRASH':>6} {'INVALID':>8} {'Total':>6}"
    print(hdr2)
    print(f"  {'-' * len(hdr2)}")
    for sn in sorted(PHASE5_CONFIGS.keys()):
        sr = [r for r in results if r['system'] == sn]
        sok = sum(1 for r in sr if r['status'] == 'OK')
        scr = sum(1 for r in sr if r['status'] == 'CRASH')
        sinv = sum(1 for r in sr if r['status'] == 'INVALID')
        print(f"  {sn:<24} {sok:>4} {scr:>6} {sinv:>8} {len(sr):>6}")

    # Save detailed results to JSON
    sim_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(sim_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'stress_test_results.json')
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: {output_path}")
    print(rule)

    return 0 if crash_count == 0 and invalid_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
