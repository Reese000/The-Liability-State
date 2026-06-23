#!/usr/bin/env python3
"""Pareto analysis of calibrated system comparison results."""
import json, numpy as np

# Use the calibrated comparison
with open('output/calibrated_comparison.json') as f:
    data = json.load(f)

systems = {}
for sn, rs in data.items():
    systems[sn] = {
        'mean': np.mean([r['w_mean'] for r in rs]),
        'gini': np.mean([r['gini'] for r in rs]),
        'crra': np.mean([r['crra_welfare'] for r in rs]),
        'wb': np.mean([r['wellbeing'] for r in rs]),
        'nw_gini': np.mean([r['net_worth_gini'] for r in rs]),
        'mean_std': np.std([r['w_mean'] for r in rs]),
        'gini_std': np.std([r['gini'] for r in rs]),
    }

metrics = ['mean', 'crra', 'wb']
antimetrics = ['gini', 'nw_gini']

def dominates(a, b):
    sa = systems[a]
    sb = systems[b]
    a_better = True
    b_better = True
    for m in metrics:
        if sa[m] <= sb[m]:
            a_better = False
        if sb[m] <= sa[m]:
            b_better = False
    for m in antimetrics:
        if sa[m] >= sb[m]:
            a_better = False
        if sb[m] >= sa[m]:
            b_better = False
    if a_better and not b_better:
        return 1
    if b_better and not a_better:
        return -1
    return 0

names = sorted(systems.keys())
pareto_front = [a for a in names if not any(dominates(b, a) == 1 for b in names if b != a)]

print("=" * 80)
print("PARETO ANALYSIS — Calibrated System Comparison (5 seeds)")
print("=" * 80)
print()

# Print all systems
print(f"{'System':<22} {'Mean$':>10} {'Gini':>8} {'CRRA':>10} {'NW_Gini':>8} {'Frontier':>9}")
print("-" * 70)
for name in names:
    s = systems[name]
    frontier = "✅ PARETO" if name in pareto_front else "—"
    print(f"{name:<22} ${s['mean']:>7,.0f}  {s['gini']:.4f}  {s['crra']:.4f}  {s['nw_gini']:.4f}  {frontier}")

print()
print("PARETO FRONTIER SYSTEMS:")
for name in pareto_front:
    print(f"  ✅ {name}")

print()
print("DOMINATION MATRIX (row dominates column):")
print(f"{'':<22}", end="")
for name in names:
    print(f"{name[:8]:>8}", end="")
print()
for a in names:
    print(f"{a:<22}", end="")
    for b in names:
        if a == b:
            print(f"{'—':>8}", end="")
        else:
            d = dominates(a, b)
            if d == 1:
                print(f"{'✅':>8}", end="")
            elif d == -1:
                print(f"{'❌':>8}", end="")
            else:
                print(f"{'·':>8}", end="")
    print()

# Composite score (simple normalized sum)
print()
print("COMPOSITE SCORE (higher is better):")
print(f"{'System':<22} {'Score':>8}")
print("-" * 32)
for name in sorted(names, key=lambda n: -sum(
    (systems[n][m] - min(systems[x][m] for x in names)) / max(1, max(systems[x][m] for x in names) - min(systems[x][m] for x in names))
    for m in metrics) - sum(
    (min(systems[x][m] for x in names) - systems[n][m]) / max(1, max(systems[x][m] for x in names) - min(systems[x][m] for x in names))
    for m in antimetrics)):
    score = sum(
        (systems[name][m] - min(systems[x][m] for x in names)) / max(1, max(systems[x][m] for x in names) - min(systems[x][m] for x in names))
        for m in metrics
    ) + sum(
        (min(systems[x][m] for x in names) - systems[name][m]) / max(1, max(systems[x][m] for x in names) - min(systems[x][m] for x in names))
        for m in antimetrics
    )
    print(f"  {name:<22} {score:>8.2f}")
