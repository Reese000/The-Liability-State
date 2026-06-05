#!/usr/bin/env python3
"""
validate_kuznets.py — Kuznets Curve Validation

Tests whether inequality follows the inverted-U pattern by running each
system with 3 different starting wealth inequality levels (low/mid/high)
and measuring end-state Gini.

Usage:
    python validate_kuznets.py
"""

import sys, os, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase4 import (
    gen_population, compute_gini, run_phase4, SYSTEM_CONFIGS,
    HOURS_PER_STEP,
)
from comparison_phase5 import run_phase5, PHASE5_CONFIGS

# ═══════════════════════════════════════════════════════════════
#  Custom Population Generators for Inequality Levels
# ═══════════════════════════════════════════════════════════════

def gen_pop_low(seed):
    """Low initial inequality: narrow uniform ranges for cash & land."""
    rng = np.random.RandomState(seed)
    w = [
        {
            "id": f"w{i:03d}",
            "hourly": rng.uniform(20, 30),
            "monthly": rng.uniform(20, 30) * HOURS_PER_STEP,
            "land": rng.uniform(80000, 120000),
            "risk": rng.uniform(0.01, 0.25),
            "cash": rng.uniform(35000, 50000),
            "honesty": rng.uniform(0.3, 0.95),
            "inertia": rng.uniform(0.05, 0.25),
            "concealment": rng.uniform(0, 0.2),
        }
        for i in range(50)
    ]
    r = [
        {
            "id": f"r{i:03d}",
            "cash": rng.uniform(100000, 140000),
            "land": rng.uniform(120000, 160000),
        }
        for i in range(15)
    ]
    b = [
        {
            "id": f"b{i:03d}",
            "cash": rng.uniform(200000, 300000),
            "capital": rng.uniform(150000, 250000),
            "tfp": rng.uniform(1.0, 2.0),
            "markup": rng.uniform(1.1, 1.3),
            "honesty": rng.uniform(0.3, 0.9),
        }
        for i in range(10)
    ]
    return w, r, b


def gen_pop_high(seed):
    """High initial inequality: log-normal distributions with high variance."""
    rng = np.random.RandomState(seed)
    w = [
        {
            "id": f"w{i:03d}",
            "hourly": np.exp(rng.normal(3.2, 0.6)),
            "monthly": np.exp(rng.normal(3.2, 0.6)) * HOURS_PER_STEP,
            "land": np.exp(rng.normal(11.5, 1.0)),
            "risk": rng.uniform(0.01, 0.25),
            "cash": np.exp(rng.normal(10.6, 1.0)),
            "honesty": rng.uniform(0.3, 0.95),
            "inertia": rng.uniform(0.05, 0.25),
            "concealment": rng.uniform(0, 0.2),
        }
        for i in range(50)
    ]
    r = [
        {
            "id": f"r{i:03d}",
            "cash": np.exp(rng.normal(11.8, 0.8)),
            "land": np.exp(rng.normal(12.2, 0.8)),
        }
        for i in range(15)
    ]
    b = [
        {
            "id": f"b{i:03d}",
            "cash": np.exp(rng.normal(12.6, 0.8)),
            "capital": np.exp(rng.normal(12.3, 0.8)),
            "tfp": rng.uniform(1.0, 2.0),
            "markup": rng.uniform(1.1, 1.3),
            "honesty": rng.uniform(0.3, 0.9),
        }
        for i in range(10)
    ]
    return w, r, b


# ═══════════════════════════════════════════════════════════════
#  Measure initial inequality from a population
# ═══════════════════════════════════════════════════════════════

def measure_initial_gini(pop):
    """Compute initial Gini from cash + land of all agents."""
    w, r, b = pop
    wealth = [e['cash'] + e.get('land', 0) for e in w + r + b]
    return compute_gini(wealth)


# ═══════════════════════════════════════════════════════════════
#  Inequality levels registry
# ═══════════════════════════════════════════════════════════════

INEQUALITY_LEVELS = {
    'low':  ('Low (Narrow Uniform)', gen_pop_low),
    'mid':  ('Mid (Default)',        gen_population),
    'high': ('High (Log-normal)',    gen_pop_high),
}

# Systems to exclude (Laissez_Faire has no tax so results are extreme)
EXCLUDE_SYSTEMS = set()


def main():
    seed = 1
    os.makedirs("output", exist_ok=True)

    # ── Run Phase 4 and Phase 5 configs ─────────────────────
    all_configs = [
        ('Phase4', list(SYSTEM_CONFIGS.values()), run_phase4),
        ('Phase5', list(PHASE5_CONFIGS.values()), run_phase5),
    ]

    rows = []

    for phase_name, configs, runner in all_configs:
        for cfg in configs:
            sys_name = cfg['system_name']
            if sys_name in EXCLUDE_SYSTEMS:
                continue

            print(f"\n── {phase_name} / {sys_name} ──", flush=True)

            for level_name, (level_desc, pop_gen) in INEQUALITY_LEVELS.items():
                pop = pop_gen(seed)
                init_gini = measure_initial_gini(pop)

                result = runner(*pop, seed, cfg)
                final_gini = result['gini']

                print(f"    {level_desc:<22}  init G={init_gini:.4f}  →  final G={final_gini:.4f}")

                rows.append({
                    'phase': phase_name,
                    'system': sys_name,
                    'inequality': level_name,
                    'inequality_desc': level_desc,
                    'initial_gini': init_gini,
                    'final_gini': final_gini,
                })

    # ── Print detailed table ────────────────────────────────
    print(f"\n{'='*130}")
    print("  KUZNETS CURVE VALIDATION")
    print(f"{'='*130}")
    header = f"{'Phase':<8} {'System':<22} {'Initial Ineq':<22} {'Init Gini':<12} {'Final Gini':<12} {'Change':<10}"
    print(header)
    print("-" * 130)

    for row in rows:
        change = row['final_gini'] - row['initial_gini']
        sign = "+" if change >= 0 else ""
        print(
            f"{row['phase']:<8} "
            f"{row['system']:<22} "
            f"{row['inequality_desc']:<22} "
            f"{row['initial_gini']:<12.4f} "
            f"{row['final_gini']:<12.4f} "
            f"{sign}{change:<8.4f}"
        )

    # ── Inverted-U Pattern Analysis ─────────────────────────
    print(f"\n{'='*130}")
    print("  INVERTED-U PATTERN ANALYSIS")
    print(f"{'='*130}")

    for phase_name, configs, _ in all_configs:
        print(f"\n  >>> {phase_name} <<<")
        sub = f"{'System':<22} {'Low→Final':<12} {'Mid→Final':<12} {'High→Final':<12} {'Pattern':<24}"
        print(sub)
        print("-" * 82)

        for cfg in configs:
            sys_name = cfg['system_name']
            if sys_name in EXCLUDE_SYSTEMS:
                continue

            # Fetch rows for each inequality level
            def get_row(level):
                matches = [
                    r for r in rows
                    if r['system'] == sys_name
                    and r['phase'] == phase_name
                    and r['inequality'] == level
                ]
                return matches[0] if matches else None

            low_r = get_row('low')
            mid_r = get_row('mid')
            high_r = get_row('high')
            if not (low_r and mid_r and high_r):
                continue

            l_f = low_r['final_gini']
            m_f = mid_r['final_gini']
            h_f = high_r['final_gini']

            # Inverted-U: mid-initial-inequality produces LOWER final Gini
            # than both low and high initial inequality
            if m_f <= l_f and m_f <= h_f:
                if l_f <= h_f:
                    pattern = "INVERTED-U (rising right) ✓"
                elif h_f < l_f:
                    pattern = "INVERTED-U (falling right) ✓"
                else:
                    pattern = "INVERTED-U (flat) ✓"
            elif l_f <= m_f <= h_f:
                pattern = "Monotonic ↑"
            elif l_f >= m_f >= h_f:
                pattern = "Monotonic ↓"
            elif l_f <= m_f and m_f >= h_f:
                pattern = "Inverse-U (peak at mid) ✓"
            else:
                pattern = "Other"

            print(
                f"{sys_name:<22} "
                f"{l_f:<12.4f} {m_f:<12.4f} {h_f:<12.4f} "
                f"{pattern:<24}"
            )

    # ── Save JSON data ──────────────────────────────────────
    json.dump(rows, open("output/kuznets_data.json", "w"), indent=2)
    print(f"\n  Data saved → output/kuznets_data.json")

    # ── Plot ────────────────────────────────────────────────
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 1, figsize=(14, 12), sharex=False)

        for pi, (phase_name, configs, _) in enumerate(all_configs):
            ax = axes[pi]
            cmap = plt.colormaps.get('tab20', plt.colormaps['tab20'])
            colors = [cmap(i) for i in np.linspace(0, 1, len(configs))]

            for ci, cfg in enumerate(configs):
                sys_name = cfg['system_name']
                if sys_name in EXCLUDE_SYSTEMS:
                    continue
                sys_rows = [
                    r for r in rows
                    if r['system'] == sys_name and r['phase'] == phase_name
                ]
                if sys_rows:
                    # Sort by initial Gini
                    pairs = sorted((r['initial_gini'], r['final_gini']) for r in sys_rows)
                    inits_s, finals_s = zip(*pairs)
                    ax.plot(
                        inits_s, finals_s,
                        marker='o', linewidth=1.8,
                        color=colors[ci % len(colors)],
                        label=sys_name,
                    )

            ax.set_xlabel('Initial Gini (starting wealth inequality)')
            ax.set_ylabel('Final Gini (end-state inequality)')
            ax.set_title(f'{phase_name} — Kuznets Curve (seed={seed})')
            ax.legend(fontsize=7, loc='best', ncol=2)
            ax.grid(True, alpha=0.3)

            # Reference line y=x
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            lo = min(xlim[0], ylim[0])
            hi = max(xlim[1], ylim[1])
            ax.plot([lo, hi], [lo, hi], 'k--', alpha=0.25, linewidth=1,
                    label='y=x (no change)')
            ax.set_xlim(lo, hi)
            ax.set_ylim(lo, hi)

        plt.tight_layout()
        out = "output/kuznets_curve.png"
        plt.savefig(out, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Plot saved  → {out}")

    except ImportError:
        print("  matplotlib not available — skipping plot")
    except Exception as e:
        print(f"  Plot error: {e}")

    print("\nDone.")


if __name__ == '__main__':
    main()
