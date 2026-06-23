#!/usr/bin/env python3
"""Pareto analysis of 13-system comparison results."""
import json, numpy as np

with open('output/phase8_13system.json') as f:
    data = json.load(f)

systems = {}
for sn, rs in data.items():
    systems[sn] = {
        'mean': np.mean([r['w_mean'] for r in rs]),
        'gini': np.mean([r['gini'] for r in rs]),
        'crra': np.mean([r['crra_welfare'] for r in rs]),
        'nw_gini': np.mean([r['net_worth_gini'] for r in rs]),
    }

metrics = ['mean', 'crra']
antimetrics = ['gini', 'nw_gini']

def dominates(a, b):
    sa = systems[a]; sb = systems[b]
    a_better = all(sa[m] > sb[m] for m in metrics) and all(sa[m] < sb[m] for m in antimetrics)
    b_better = all(sb[m] > sa[m] for m in metrics) and all(sb[m] < sa[m] for m in antimetrics)
    if a_better: return 1
    if b_better: return -1
    return 0

names = sorted(systems.keys())
pareto_front = [a for a in names if not any(dominates(b, a) == 1 for b in names if b != a)]

print("PARETO ANALYSIS — 13 Systems (5 seeds)")
print("=" * 65)
print(f"{'System':<22} {'Mean$':>10} {'Gini':>8} {'CRRA':>10} {'Frontier':>9}")
print("-" * 65)
for name in names:
    s = systems[name]
    frontier = "FRONTIER" if name in pareto_front else "dominated"
    print(f"{name:<22} ${s['mean']:>7,.0f}  {s['gini']:.4f}  {s['crra']:.4f}  {frontier}")

print()
print("COMPOSITE SCORE (higher is better):")
all_means = [systems[n]['mean'] for n in names]
all_gini = [systems[n]['gini'] for n in names]
all_crra = [systems[n]['crra'] for n in names]
for name in sorted(names, key=lambda n: -(
    (systems[n]['mean'] - min(all_means)) / max(1, max(all_means) - min(all_means))
    + (systems[n]['crra'] - min(all_crra)) / max(1, max(all_crra) - min(all_crra))
    + (min(all_gini) - systems[n]['gini']) / max(1, max(all_gini) - min(all_gini))
)):
    score = (
        (systems[name]['mean'] - min(all_means)) / max(1, max(all_means) - min(all_means))
        + (systems[name]['crra'] - min(all_crra)) / max(1, max(all_crra) - min(all_crra))
        + (min(all_gini) - systems[name]['gini']) / max(1, max(all_gini) - min(all_gini))
    )
    print(f"  {name:<22} {score:.2f}")
