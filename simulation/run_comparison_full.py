#!/usr/bin/env python3
"""Full comparison: all 10 systems with proper SECTORAL parameters, 5 seeds."""
import sys, os, copy, json, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS

seeds = list(range(1, 6))  # 5 seeds
results = {}
targets = {
    'US_Style': 0.49, 'Singapore': 0.46, 'Nordic': 0.28,
    'LS_Full': 0.30, 'Laissez_Faire': 0.50, 'Harberger_Georgist': 0.40,
    'Pure_Georgist': 0.30, 'Mutualist_LS': 0.28, 'Worker_Coop': 0.25, 'UBI_VAT': 0.35,
    'Dual_Compact_LS': 0.30,
}

t0 = time.time()
for name in sorted(PHASE8_CONFIGS.keys()):
    cfg = copy.deepcopy(PHASE8_CONFIGS[name])
    sys_out = []
    for seed in seeds:
        w, r, b = gen_population(seed)
        res = run_phase8(w, r, b, seed, cfg)
        sys_out.append(res)
    results[name] = sys_out
    wm = np.mean([r['w_mean'] for r in sys_out])
    gm = np.mean([r['gini'] for r in sys_out])
    ng = np.mean([r['net_worth_gini'] for r in sys_out])
    target = targets.get(name, 0)
    gap = gm - target
    tag = 'OK' if abs(gap) < 0.10 else ('LOW' if gap < 0 else 'HIGH')
    print(f'{name:<22} ${wm:>9,.0f}  G={gm:.4f}  NW_G={ng:.4f}  target={target:.2f}  [{gap:+.3f}] {tag}')

print(f'\nTotal time: {time.time()-t0:.0f}s')

print()
wr = sorted(results.keys(), key=lambda sn: -np.mean([r['w_mean'] for r in results[sn]]))
print('Rank System                      Mean$     Gini    NW_Gini     CRRA')
print('-' * 60)
for i, sn in enumerate(wr, 1):
    wm = np.mean([r['w_mean'] for r in results[sn]])
    gm = np.mean([r['gini'] for r in results[sn]])
    ng = np.mean([r['net_worth_gini'] for r in results[sn]])
    cr = np.mean([r.get('crra_welfare', 0) for r in results[sn]])
    print(f'{i:>3}  {sn:<22} ${wm:>8,.0f}  {gm:.4f}  {ng:.4f}  {cr:.1f}')

print()
print('Gini ranking (lower = more equal):')
ranked = sorted(results.keys(), key=lambda sn: np.mean([r['gini'] for r in results[sn]]))
for i, sn in enumerate(ranked, 1):
    gm = np.mean([r['gini'] for r in results[sn]])
    target = targets.get(sn, 0)
    gap = gm - target
    tag = 'OK' if abs(gap) < 0.10 else ('LOW' if gap < 0 else 'HIGH')
    print(f'{i:>3}. {sn:<22} G={gm:.4f}  target={target:.2f}  [{gap:+.3f}] {tag}')

os.makedirs('output', exist_ok=True)
with open('output/full_comparison_results.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)
print('\nSaved: output/full_comparison_results.json')
