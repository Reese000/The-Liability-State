#!/usr/bin/env python3
"""Monte Carlo uncertainty quantification for Phase 6.

Draws ALL numeric Phase 6 parameters from uniform [default×0.5, default×1.5],
runs 50 samples each for LS_Full and US_Style, reports means, 95% CI,
and probability that LS_Full outperforms US_Style.

Usage:
    python validate_montecarlo.py

Output:
    stdout: text report
    output/montecarlo_results.json: full results
"""

import sys, os, copy, json, time, math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))

# ─── Reduce steps for speed ───────────────────────────────
import comparison_phase6 as _cp6
_cp6.STEPS = 120

from comparison_phase6 import run_phase6, gen_population, PHASE6_CONFIGS

N_SAMPLES = 50
SEED = 42
STEPS = 120

# ─── All numeric Phase 6 parameters to vary ──────────────
ALL_NUMERIC_PARAMS = [
    # Phase 4 base
    'lvt_rate', 'income_tax_rate', 'corp_tax_rate', 'welfare_rate',
    'union_premium', 'cpf_rate', 'wage_ratio_cap', 'vat_rate',
    # Phase 4 dynamics
    'corruption_level', 'income_effect_labor', 'admin_overhead',
    'economies_of_scale', 'monopoly_markup_max', 'banking_multiplier',
    'interest_rate', 'inheritance_rate', 'enforcement_quality',
    'detection_probability_base', 'information_asymmetry',
    # Phase 5
    'harberger_buyer_frequency', 'harberger_learning_rate',
    'agricultural_lvt_rate', 'minimum_wage',
    'constitutional_amendment_rate', 'bank_initial_reserve',
    # Phase 6 (no additional numeric params beyond bool flags)
]

# Bool/string params that are NOT varied
# 'tax_type', 'system_name', 'use_adversarial', 'use_pooled_insurance',
# 'use_events', 'use_worker_coop', 'use_vat', 'use_harberger',
# 'foreign_ownership_allowed', 'migration_enabled', 'compact_voting',
# 'wire_lvt_evasion', 'use_families'


def draw_random_config(base_config, rng):
    """Create a new config by drawing each numeric param from
    uniform [default×0.5, default×1.5].

    Non-numeric params are copied verbatim.
    """
    cfg = copy.deepcopy(base_config)
    for param in ALL_NUMERIC_PARAMS:
        if param not in cfg:
            continue
        default_val = cfg[param]
        if not isinstance(default_val, (int, float)):
            continue
        if default_val == 0:
            # If default is 0, range is also 0 to avoid degenerate [0, 0]
            lo, hi = 0.0, 0.0
        else:
            lo = default_val * 0.5
            hi = default_val * 1.5
        cfg[param] = rng.uniform(lo, hi)
    return cfg


def run_montecarlo():
    """Run Monte Carlo uncertainty quantification.

    Returns dict with results for LS_Full and US_Style.
    """
    t0 = time.time()
    # RNG for parameter variation (separate from simulation seed)
    mc_rng = np.random.RandomState(SEED + 1000)

    systems = ['LS_Full', 'US_Style']
    results = {sys_name: [] for sys_name in systems}

    for sys_name in systems:
        base_config = PHASE6_CONFIGS[sys_name]
        print(f"\n  {sys_name}: running {N_SAMPLES} Monte Carlo samples...")

        for i in range(N_SAMPLES):
            # Draw random config
            cfg = draw_random_config(base_config, mc_rng)
            cfg['system_name'] = sys_name

            # Generate fresh population at seed
            pop = gen_population(SEED)
            # Deep copy to avoid mutation issues
            workers, retirees, businesses = copy.deepcopy(pop[:3])

            try:
                r = run_phase6(workers, retirees, businesses, SEED, cfg)
                # Ensure all expected keys exist
                results[sys_name].append({
                    'wealth': float(r.get('wealth', 0)),
                    'gini': float(r.get('gini', 0)),
                    'net_worth': float(r.get('net_worth', 0)),
                    'net_worth_mean': float(r.get('net_worth_mean', 0)),
                    'wellbeing': float(r.get('wellbeing', 0)),
                })
            except Exception as e:
                print(f"    ✗ sample {i+1} failed: {e}")
                results[sys_name].append({
                    'wealth': -1, 'gini': -1,
                    'net_worth': -1, 'net_worth_mean': -1,
                    'wellbeing': -1,
                })

            # Progress
            if (i + 1) % 10 == 0:
                print(f"    ... {i+1}/{N_SAMPLES} done")

    elapsed = time.time() - t0

    # ─── Compute statistics ──────────────────────────────────
    metrics = ['wealth', 'gini', 'net_worth', 'wellbeing']
    stats = {}

    for sys_name in systems:
        sys_results = results[sys_name]
        stats[sys_name] = {}
        for metric in metrics:
            vals = [r[metric] for r in sys_results
                    if r[metric] >= 0]
            if not vals:
                stats[sys_name][metric] = {
                    'mean': 0, 'ci_95_low': 0, 'ci_95_high': 0,
                    'std': 0, 'n': 0,
                }
                continue
            mean = float(np.mean(vals))
            std = float(np.std(vals, ddof=1))
            n = len(vals)
            # 95% CI using normal approximation (large n)
            z = 1.96
            ci_low = mean - z * std / math.sqrt(n)
            ci_high = mean + z * std / math.sqrt(n)
            stats[sys_name][metric] = {
                'mean': round(mean, 4),
                'ci_95_low': round(ci_low, 4),
                'ci_95_high': round(ci_high, 4),
                'std': round(std, 4),
                'n': n,
            }

    # ─── Probability LS_Full > US_Style for each metric ──────
    prob_ls_better = {}
    for metric in metrics:
        ls_vals = [r[metric] for r in results['LS_Full']
                   if r[metric] >= 0]
        us_vals = [r[metric] for r in results['US_Style']
                   if r[metric] >= 0]
        n_pairs = min(len(ls_vals), len(us_vals))
        if n_pairs == 0:
            prob_ls_better[metric] = 0.5
            continue
        # For Gini, lower is better → invert logic
        if metric == 'gini':
            better_count = sum(1 for i in range(n_pairs)
                               if ls_vals[i] < us_vals[i])
        else:
            better_count = sum(1 for i in range(n_pairs)
                               if ls_vals[i] > us_vals[i])
        prob_ls_better[metric] = round(better_count / n_pairs, 4)

    # ─── Print report ────────────────────────────────────────
    print()
    print("=" * 90)
    print("  MONTE CARLO UNCERTAINTY QUANTIFICATION — Phase 6")
    print("=" * 90)
    print(f"  Systems: LS_Full, US_Style")
    print(f"  Samples per system: {N_SAMPLES}")
    print(f"  Steps: {STEPS}  |  Seed: {SEED}")
    print(f"  Parameters varied: {len(ALL_NUMERIC_PARAMS)} numeric config keys")
    print(f"  Range: [default × 0.5, default × 1.5]")
    print(f"  Time: {elapsed:.1f}s")
    print()

    for sys_name in systems:
        print(f"  ── {sys_name} ──")
        print(f"  {'Metric':<16} {'Mean':>10} {'95% CI Low':>12} {'95% CI High':>13} {'Std':>10} {'N':>5}")
        print(f"  {'-'*16} {'-'*10} {'-'*12} {'-'*13} {'-'*10} {'-'*5}")
        for metric in metrics:
            s = stats[sys_name][metric]
            print(f"  {metric:<16} {s['mean']:>10.4f} {s['ci_95_low']:>12.4f} {s['ci_95_high']:>13.4f} {s['std']:>10.4f} {s['n']:>5}")
        print()

    print(f"  ── Probability LS_Full outperforms US_Style ──")
    print(f"  {'Metric':<16} {'P(LS > US)':>12}")
    print(f"  {'-'*16} {'-'*12}")
    for metric in metrics:
        p = prob_ls_better[metric]
        direction = "lower is better" if metric == 'gini' else "higher is better"
        label = f"P(LS < US)" if metric == 'gini' else f"P(LS > US)"
        print(f"  {metric:<16} {p:>10.4f}  ({direction})")
    print()

    # ─── Build output ────────────────────────────────────────
    result = {
        'metadata': {
            'n_samples': N_SAMPLES,
            'seed': SEED,
            'steps': STEPS,
            'n_params_varied': len(ALL_NUMERIC_PARAMS),
            'varying_params': ALL_NUMERIC_PARAMS,
            'elapsed_seconds': round(elapsed, 1),
        },
        'systems': {
            sys_name: {
                metric: stats[sys_name][metric]
                for metric in metrics
            }
            for sys_name in systems
        },
        'prob_LS_Full_better': prob_ls_better,
        # Raw sample data
        'samples': {
            sys_name: [
                {metric: r[metric] for metric in metrics}
                for r in results[sys_name]
            ]
            for sys_name in systems
        },
    }

    return result


def main():
    print("=" * 90)
    print("  MONTE CARLO UNCERTAINTY QUANTIFICATION")
    print("  Phase 6 — LS_Full vs US_Style")
    print(f"  {N_SAMPLES} samples × 2 systems = {N_SAMPLES * 2} simulations")
    print(f"  {STEPS} steps each (reduced from 480 for speed)")
    print(f"  Varying {len(ALL_NUMERIC_PARAMS)} config parameters")
    print("=" * 90)

    result = run_montecarlo()

    # Save
    sim_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(sim_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    outpath = os.path.join(output_dir, 'montecarlo_results.json')
    with open(outpath, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"  Saved: {outpath}")
    print()
    print("  Done.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
