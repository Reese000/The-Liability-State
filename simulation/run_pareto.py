#!/usr/bin/env python3
"""Pareto analysis of system comparison results."""
import json, numpy as np

with open('output/system_comparison.json') as f:
    data = json.load(f)

systems = {}
for sn, rs in data.items():
    systems[sn] = {
        'mean': np.mean([r['w_mean'] for r in rs]),
        'gini': np.mean([r['gini'] for r in rs]),
        'crra': np.mean([r['crra_welfare'] for r in rs]),
        'wb': np.mean([r['wellbeing'] for r in rs]),
        'nw_gini': np.mean([r['net_worth_gini'] for r in rs]),
    }

metrics = ['mean', 'crra', 'wb']
antimetrics = ['gini', 'nw_gini']

def dominates(a, b):
    """Returns 1 if a strictly dominates b, -1 if b dominates a, 0 otherwise.
    Strict domination: a is better on ALL metrics, strictly (not equal)."""
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
        return 1  # a dominates b
    if b_better and not a_better:
        return -1  # b dominates a
    return 0  # non-dominated or tied

names = list(systems.keys())
pareto_front = [a for a in names if not any(dominates(b, a) == 1 for b in names if b != a)]

print("=" * 80)
print("PARETO ANALYSIS — System Comparison")
print("=" * 80)
print("Pareto-optimal: no other system is strictly better on ALL metrics")
print()

print("PARETO FRONTIER SYSTEMS:")
for sn in sorted(pareto_front):
    s = systems[sn]
    print(f"  {sn:<20} Mean=${s['mean']:>7,.0f} Gini={s['gini']:.4f} CRRA={s['crra']:.1f} WB={s['wb']:.3f}")

print()
print("DOMINATED SYSTEMS:")
for sn in sorted(names):
    if sn not in pareto_front:
        s = systems[sn]
        dom = [b for b in names if b != sn and dominates(b, sn) == 1]
        print(f"  {sn:<20} Mean=${s['mean']:>7,.0f} Gini={s['gini']:.4f} Dominated by: {', '.join(dom[:3])}")

print()
print("COMPOSITE SCORE (CRRA + WB*100 - Gini*500 - NW_Gini*100):")
ranked = sorted(names, key=lambda x: -(systems[x]['crra'] + systems[x]['wb']*100 - systems[x]['gini']*500 - systems[x]['nw_gini']*100))
print(f"{'Rank':>4} {'System':<20} {'Score':>8}")
print("-" * 34)
for i, sn in enumerate(ranked, 1):
    s = systems[sn]
    score = s['crra'] + s['wb']*100 - s['gini']*500 - s['nw_gini']*100
    print(f"{i:>4} {sn:<20} {score:>8.0f}")
