#!/usr/bin/env python3
"""
validate_intergen.py — Intergenerational Gini validation.

Runs LS_Full, US_Style, Pure_Georgist (from PHASE5_CONFIGS) at seeds=[42, 43],
extracts 'gini_by_decade' from each run_phase5 result, and prints a table
showing System × Seed × Decade → Gini.  Optionally plots to
output/intergen_gini.png.
"""

import sys, os, copy, json

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase4 import gen_population
from comparison_phase5 import run_phase5, PHASE5_CONFIGS

# ── Systems to validate ─────────────────────────────────────
TARGET_SYSTEMS = ['LS_Full', 'US_Style', 'Pure_Georgist']
SEEDS = [42, 43]
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Gather results: dict[system_name][seed_index] -> result dict
    results = {}

    for sys_name in TARGET_SYSTEMS:
        cfg = copy.deepcopy(PHASE5_CONFIGS[sys_name])
        cfg['system_name'] = sys_name
        results[sys_name] = []
        print(f"\n  Running {sys_name} ...")

        for seed in SEEDS:
            pop = gen_population(seed)
            r = run_phase5(*pop, seed, cfg)
            results[sys_name].append(r)
            gbd = r.get('gini_by_decade', [])
            print(f"    seed={seed}:  {len(gbd)} decade entries, "
                  f"final Gini={r['gini']:.4f}")

    # ── Print table ──────────────────────────────────────────
    header = f"{'System':<18} {'Seed':>5} {'Decade':>6} {'Gini':>8}"
    sep = "-" * len(header)
    rows = []

    for sys_name in TARGET_SYSTEMS:
        for i, seed in enumerate(SEEDS):
            gbd = results[sys_name][i].get('gini_by_decade', [])
            for d_idx, gval in enumerate(gbd):
                rows.append((sys_name, seed, d_idx + 1, gval))

    print(f"\n\n{'=' * len(header)}")
    print("  INTERGENERATIONAL GINI BY SYSTEM & DECADE")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)
    for sys_name, seed, decade, gini in rows:
        print(f"{sys_name:<18} {seed:>5} {decade:>6} {gini:>8.4f}")
    print(sep)

    # ── Per-system summary ──────────────────────────────────
    print(f"\nSystem-level averages (across seeds & decades):")
    print(f"{'System':<18} {'Mean Gini':>10} {'Min':>8} {'Max':>8} {'Decades':>8}")
    print("-" * 52)
    for sys_name in TARGET_SYSTEMS:
        ginis = []
        for i, seed in enumerate(SEEDS):
            ginis.extend(results[sys_name][i].get('gini_by_decade', []))
        if ginis:
            print(f"{sys_name:<18} {np.mean(ginis):>10.4f} {np.min(ginis):>8.4f} "
                  f"{np.max(ginis):>8.4f} {len(ginis):>8}")
        else:
            print(f"{sys_name:<18} {'N/A':>10} {'N/A':>8} {'N/A':>8} {'0':>8}")

    # ── Optional plot ────────────────────────────────────────
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 6))
        markers = {'LS_Full': 'o', 'US_Style': 's', 'Pure_Georgist': '^'}
        colors = {'LS_Full': '#2E86AB', 'US_Style': '#A23B72',
                  'Pure_Georgist': '#F18F01'}

        for sys_name in TARGET_SYSTEMS:
            for i, seed in enumerate(SEEDS):
                gbd = results[sys_name][i].get('gini_by_decade', [])
                decades = list(range(1, len(gbd) + 1))
                label = f"{sys_name} (seed={seed})"
                ax.plot(decades, gbd, marker=markers.get(sys_name, 'o'),
                        color=colors.get(sys_name, 'gray'),
                        linestyle='--' if i == 1 else '-',
                        alpha=0.7, label=label)

        ax.set_xlabel("Decade", fontsize=12)
        ax.set_ylabel("Gini Coefficient", fontsize=12)
        ax.set_title("Intergenerational Gini by System", fontsize=14)
        ax.legend(fontsize=8, loc='best')
        ax.grid(alpha=0.3)
        fig.tight_layout()

        plot_path = os.path.join(OUT_DIR, 'intergen_gini.png')
        fig.savefig(plot_path, dpi=150)
        plt.close(fig)
        print(f"\nPlot saved: {plot_path}")
    except ImportError:
        print("\n(Plotting skipped — matplotlib not available)")
    except Exception as e:
        print(f"\n(Plotting failed: {e})")

    # ── Save raw data ────────────────────────────────────────
    data_path = os.path.join(OUT_DIR, 'intergen_gini.json')
    json.dump({
        sys_name: [
            {'seed': seed, 'gini_by_decade': results[sys_name][i].get('gini_by_decade', [])}
            for i, seed in enumerate(SEEDS)
        ]
        for sys_name in TARGET_SYSTEMS
    }, open(data_path, 'w'), indent=2)
    print(f"Raw data saved: {data_path}")


if __name__ == '__main__':
    main()
