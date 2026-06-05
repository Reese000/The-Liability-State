#!/usr/bin/env python3
"""Global Sensitivity Analysis for Phase 6 simulation.

Tests each of the 10 Phase 6 parameters at 3 levels (×0.5, ×1.0, ×1.5)
across all 9 systems and 3 seeds (42, 43, 44).

Total: 10 params × 3 levels × 9 systems × 3 seeds = 810 runs.

Reports robust system rankings (never flip across all variations of a parameter)
and fragile rankings (any level causes a ranking flip).
"""

import sys
import os
import copy
import json
import math
import traceback
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# ─── Reduce steps for speed ───────────────────────────────
import comparison_phase6 as _cp6
_cp6.STEPS = 120

from comparison_phase6 import run_phase6, gen_population, PHASE6_CONFIGS

SEEDS = [42, 43, 44]

# The 10 parameters to vary
PARAMETERS = [
    'corruption_level',
    'admin_overhead',
    'income_effect_labor',
    'economies_of_scale',
    'monopoly_markup_max',
    'banking_multiplier',
    'enforcement_quality',
    'information_asymmetry',
    'inheritance_rate',
    'detection_probability_base',
]

# Human-readable descriptions
PARAM_DESCRIPTIONS = {
    'corruption_level': 'corruption_level (default: 0.02→1.0 across systems)',
    'admin_overhead': 'admin_overhead (default: 0.01→0.08 across systems)',
    'income_effect_labor': 'income_effect_labor (default: 0.0→0.10 across systems)',
    'economies_of_scale': 'economies_of_scale (default: 0.0→0.15 across systems)',
    'monopoly_markup_max': 'monopoly_markup_max (default: 1.1→1.6 across systems)',
    'banking_multiplier': 'banking_multiplier (default: 0→5 across systems)',
    'enforcement_quality': 'enforcement_quality (default: 0.2→0.95 across systems)',
    'information_asymmetry': 'information_asymmetry (default: 0.0→0.35 across systems)',
    'inheritance_rate': 'inheritance_rate (default: 0.0→0.25 across systems)',
    'detection_probability_base': 'detection_probability_base (default: 0.3→0.8 across systems)',
}

LEVELS = {
    'low': 0.5,
    'default': 1.0,
    'high': 1.5,
}

# Systems to analyze (the 9 from the task description)
SYSTEMS = ['LS_Full', 'US_Style', 'Nordic', 'Singapore',
           'Pure_Georgist', 'Mutualist_LS', 'Laissez_Faire',
           'Worker_Coop', 'UBI_VAT']

NUM_SYSTEMS = len(SYSTEMS)
NUM_PAIRS = NUM_SYSTEMS * (NUM_SYSTEMS - 1) // 2  # 36


def run_single(system, seed, config):
    """Run a single simulation safely, returning result or None."""
    try:
        pop = gen_population(seed)
        result = run_phase6(*copy.deepcopy(pop[:3]), seed, config)
        return result
    except Exception as e:
        traceback.print_exc()
        return None


def compute_rankings(results):
    """Convert results dict {seed: {system: result}} to rankings by w_mean.

    Returns {seed: {rank: system}} where rank 1 = highest w_mean.
    """
    rankings = {}
    for seed in results:
        sys_vals = {}
        for sys_name, r in results[seed].items():
            if r is not None and r.get('w_mean', 0) is not None:
                val = r['w_mean']
                if not (math.isnan(val) or math.isinf(val)):
                    sys_vals[sys_name] = val
        sorted_sys = sorted(sys_vals.items(), key=lambda x: x[1], reverse=True)
        rankings[seed] = {sys_name: rank + 1 for rank, (sys_name, _) in enumerate(sorted_sys)}
    return rankings


def analyze_pair_stability(param_results):
    """Analyze pairwise ranking stability across levels for a single parameter.

    param_results: {level_name: {seed: {system: result}}}

    Returns dict of {(sys_a, sys_b): {'stable': bool, 'flip_details': [...]}}
    """
    pairs = {}
    sys_names = SYSTEMS

    for i in range(len(sys_names)):
        for j in range(i + 1, len(sys_names)):
            a, b = sys_names[i], sys_names[j]
            pair_key = tuple(sorted((a, b)))
            pairs[pair_key] = {'flips': [], 'always_a_wins': True, 'always_b_wins': True}

            for level_name in LEVELS:
                for seed in SEEDS:
                    r_a = param_results[level_name].get(seed, {}).get(a)
                    r_b = param_results[level_name].get(seed, {}).get(b)

                    if r_a is None or r_b is None:
                        continue

                    w_a = r_a.get('w_mean', 0)
                    w_b = r_b.get('w_mean', 0)

                    if w_a is None or w_b is None or math.isnan(w_a) or math.isnan(w_b):
                        continue

                    if w_a > w_b:
                        pairs[pair_key]['always_b_wins'] = False
                    elif w_b > w_a:
                        pairs[pair_key]['always_a_wins'] = False
                    else:
                        # Equal - not considered a flip, but neither wins
                        pass

            flip = pairs[pair_key]['flips']

            if not pairs[pair_key]['always_a_wins'] and not pairs[pair_key]['always_b_wins']:
                # Mixed: sometimes A wins, sometimes B wins → fragile
                flip.append('mixed_direction')

    return pairs


def format_param_range(param):
    """Get a human-readable description of the default range for a parameter."""
    vals = []
    for sys_name in SYSTEMS:
        v = PHASE6_CONFIGS[sys_name].get(param)
        if v is not None:
            vals.append(v)
    min_v = min(vals)
    max_v = max(vals)
    return f"{param} (default: {min_v}→{max_v} across systems)"


def main():
    all_raw = {}  # {param: {level: {seed: {system: result}}}}

    print("=" * 110)
    print("  GLOBAL SENSITIVITY ANALYSIS — Phase 6")
    print(f"  Parameters: {len(PARAMETERS)}  |  Levels: {len(LEVELS)}"
          f"  |  Systems: {NUM_SYSTEMS}  |  Seeds: {len(SEEDS)}")
    print(f"  Total runs: {len(PARAMETERS) * len(LEVELS) * NUM_SYSTEMS * len(SEEDS)}"
          f"  |  Steps: {_cp6.STEPS} (reduced from 480)")
    print("=" * 110)

    # ─── Run all simulations ──────────────────────────────────
    for param_idx, param in enumerate(PARAMETERS):
        print(f"\n  [{param_idx + 1}/{len(PARAMETERS)}] {param}...")
        param_results = {}
        failures = 0

        for level_name, level_mult in LEVELS.items():
            level_results = {seed: {} for seed in SEEDS}

            for sys_name in SYSTEMS:
                base_cfg = PHASE6_CONFIGS[sys_name]
                default_val = base_cfg.get(param)

                # Compute new value (allow for int params like banking_multiplier)
                new_val = default_val * level_mult
                if isinstance(default_val, int):
                    new_val = int(round(new_val))

                cfg = copy.deepcopy(base_cfg)
                cfg[param] = new_val

                for seed in SEEDS:
                    result = run_single(sys_name, seed, cfg)
                    if result is None:
                        failures += 1
                        # Store a placeholder
                        result = {'name': sys_name, 'w_mean': -1, 'gini': -1,
                                  'wealth': -1, 'steps': 0, 'error': True}
                    level_results[seed][sys_name] = result

                # Progress dot
                print('.', end='', flush=True)
            param_results[level_name] = level_results

        print(f"  done{'  ⚠ ' + str(failures) + ' failures' if failures else ''}")
        all_raw[param] = param_results

    # ─── Analyze each parameter ──────────────────────────────
    print(f"\n{'=' * 110}")
    print("  RESULTS")
    print(f"{'=' * 110}")

    overall_pair_counts = {}  # {(a,b): {'robust_count': N, 'total_params': 10}}

    for sys_a in SYSTEMS:
        for sys_b in SYSTEMS:
            if sys_a < sys_b:
                overall_pair_counts[(sys_a, sys_b)] = {'robust_count': 0, 'fragile_params': []}

    for param_idx, param in enumerate(PARAMETERS):
        param_results = all_raw[param]

        # Analyze pair stability for this parameter
        pair_info = analyze_pair_stability(param_results)

        # Classify robust vs fragile
        robust_pairs = []
        fragile_pairs = []
        for (a, b), info in pair_info.items():
            if info['always_a_wins'] or info['always_b_wins']:
                robust_pairs.append((a, b, 'A' if info['always_a_wins'] else 'B'))
            else:
                fragile_pairs.append((a, b))

        # Update overall counts
        for (a, b), info in pair_info.items():
            if info['always_a_wins'] or info['always_b_wins']:
                overall_pair_counts[(a, b)]['robust_count'] += 1
            else:
                overall_pair_counts[(a, b)]['fragile_params'].append(param)

        # ── Print per-parameter report ───────────────────────
        print()
        print(f"{'─' * 110}")
        print(f"  === GLOBAL SENSITIVITY ANALYSIS ===")
        print(f"  Parameter: {format_param_range(param)}")
        print(f"  Tested at: low (×0.5), default, high (×1.5)")
        print(f"  Systems: {NUM_SYSTEMS} × seeds: {len(SEEDS)}")
        print()

        # Sort robust pairs: first by A's rank at default, then alphabetically
        def sort_key_robust(pair):
            a, b, winner = pair
            default_results = param_results.get('default', {})
            # Use seed 42 default ranking for tiebreaking
            default_vals = {}
            for seed in SEEDS:
                for sys_n in [a, b]:
                    if seed in default_results and sys_n in default_results[seed]:
                        v = default_results[seed][sys_n].get('w_mean', 0) or 0
                        if sys_n not in default_vals:
                            default_vals[sys_n] = []
                        default_vals[sys_n].append(v)
            avg_a = np.mean(default_vals.get(a, [0]))
            avg_b = np.mean(default_vals.get(b, [0]))
            # Sort by gap (larger gap = more robust feeling)
            gap = abs(avg_a - avg_b)
            return (-gap, a, b)

        robust_pairs.sort(key=sort_key_robust, reverse=True)

        print(f"  TOP {min(5, len(robust_pairs))} ROBUST PAIRINGS (never flip across all param variations):")
        if robust_pairs:
            for idx, (a, b, winner) in enumerate(robust_pairs[:5], 1):
                if winner == 'A':
                    print(f"  {idx}. {a} > {b} (100% stable)")
                else:
                    print(f"  {idx}. {b} > {a} (100% stable)")
        else:
            print("  (none — all pairings flip under this parameter)")

        print()
        print(f"  FRAGILE PAIRINGS (flip under some variation):")
        if fragile_pairs:
            for idx, (a, b) in enumerate(fragile_pairs, 1):
                print(f"  {idx}. {a} vs {b}")
        else:
            print("  (none — all pairings are robust)")

        num_robust = len(robust_pairs)
        print()
        print(f"  THIS PARAMETER: {num_robust}/{NUM_PAIRS} pairwise comparisons robust (100% stable)")
        print(f"                   {NUM_PAIRS - num_robust}/{NUM_PAIRS} fragile (flip at some level)")

    # ── Overall summary ─────────────────────────────────────
    print()
    print(f"{'=' * 110}")
    print("  OVERALL ACROSS ALL 10 PARAMETERS")
    print(f"{'=' * 110}")
    print()

    total_robust = 0
    total_fragile = 0
    for (a, b), info in overall_pair_counts.items():
        if info['robust_count'] == len(PARAMETERS):
            total_robust += 1
        else:
            total_fragile += 1

    print(f"  {total_robust}/{NUM_PAIRS} pairwise comparisons robust across ALL parameters")
    print(f"  {total_fragile}/{NUM_PAIRS} pairwise comparisons fragile (flip for at least one parameter)")
    print()

    if total_robust > 0:
        print(f"  INVARIANT RANKINGS (never flip for any parameter):")
        for (a, b), info in sorted(overall_pair_counts.items()):
            if info['robust_count'] == len(PARAMETERS):
                # Determine which wins
                default_results = all_raw[PARAMETERS[0]]['default']
                default_vals = {seed: default_results[seed][a]['w_mean']
                                for seed in SEEDS if default_results[seed][a]['w_mean'] is not None}
                default_vals_b = {seed: default_results[seed][b]['w_mean']
                                  for seed in SEEDS if default_results[seed][b]['w_mean'] is not None}
                avg_a = np.mean(list(default_vals.values())) if default_vals else 0
                avg_b = np.mean(list(default_vals_b.values())) if default_vals_b else 0
                if avg_a > avg_b:
                    print(f"    {a} > {b}")
                else:
                    print(f"    {b} > {a}")

    if total_fragile > 0:
        print()
        print(f"  FRAGILE RANKINGS (flip for at least one parameter):")
        for (a, b), info in sorted(overall_pair_counts.items()):
            if info['robust_count'] < len(PARAMETERS):
                params_list = ', '.join(info['fragile_params'])
                print(f"    {a} vs {b}  (fragile under: {params_list})")

    # ── Save raw results ─────────────────────────────────────
    sim_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(sim_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)

    # Convert to serializable format
    serializable = {}
    for param in PARAMETERS:
        serializable[param] = {}
        for level_name in LEVELS:
            serializable[param][level_name] = {}
            for seed in SEEDS:
                serializable[param][level_name][str(seed)] = {}
                for sys_name in SYSTEMS:
                    r = all_raw[param][level_name].get(seed, {}).get(sys_name, {})
                    clean = {}
                    for k, v in r.items():
                        if isinstance(v, (np.integer,)):
                            clean[k] = int(v)
                        elif isinstance(v, (np.floating,)):
                            clean[k] = float(v)
                        elif isinstance(v, (list,)) and k == 'gini_by_decade':
                            clean[k] = [float(x) for x in v]
                        elif isinstance(v, dict) and k == 'policy_path':
                            clean[k] = str(v)  # too verbose
                        else:
                            try:
                                json.dumps({k: v})
                                clean[k] = v
                            except (TypeError, OverflowError):
                                clean[k] = str(v)
                    serializable[param][level_name][str(seed)][sys_name] = clean

    output_path = os.path.join(output_dir, 'sensitivity_results.json')
    with open(output_path, 'w') as f:
        json.dump(serializable, f, indent=2)
    print(f"\n  Raw results saved to: {output_path}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
