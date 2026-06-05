#!/usr/bin/env python3
"""Full comparison with 15 mechanisms including super-wealthy + real trade."""
import sys, os, copy, json, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS

BASE = {
    'inflation_rate': 0.02, 'endogenous_tfp': True,
    'wage_competition': True, 'capital_ownership_share': 0.15,
    'use_housing_market': True,
    'use_super_wealthy': True, 'use_real_trade': True,
}
SYS = {
    'Singapore': {'cpf_liquidity_trap': 0.10, 'cpf_demand_suppression': 0.08, 'cpf_housing_feedback': 0.05, 'gov_service_productivity': 0.1},
    'Laissez_Faire': {'use_public_goods': True, 'gov_service_productivity': 0.0},
    'US_Style': {'gov_service_productivity': 0.4, 'capital_ownership_concentration': 0.7},
    'Nordic': {'gov_service_productivity': 0.6, 'capital_ownership_concentration': 0.3},
    'Worker_Coop': {'capital_ownership_share': 0.4, 'capital_ownership_concentration': 0.1},
}

seeds = [1, 2]
results = {}
t0 = time.time()
for name, base_cfg in PHASE8_CONFIGS.items():
    cfg = copy.deepcopy(base_cfg)
    cfg.update(BASE)
    if name in SYS: cfg.update(SYS[name])
    sys_out = []
    for seed in seeds:
        w, r, b = gen_population(seed)
        res = run_phase8(w, r, b, seed, cfg)
        sys_out.append(res)
    results[name] = sys_out
    wm = np.mean([r['w_mean'] for r in sys_out])
    gm = np.mean([r['gini'] for r in sys_out])
    print('{:<22} Mean=${:>8,.0f} Gini={:.4f}'.format(name, wm, gm))

print('\nRANKINGS:')
wr = sorted(results.keys(), key=lambda sn: -np.mean([r['w_mean'] for r in results[sn]]))
for i, sn in enumerate(wr, 1):
    wm = np.mean([r['w_mean'] for r in results[sn]])
    gm = np.mean([r['gini'] for r in results[sn]])
    print('  {}. {:<22} ${:>8,.0f}  Gini {:.4f}'.format(i, sn, wm, gm))

print('Time: {:.0f}s'.format(time.time()-t0))
os.makedirs('output', exist_ok=True)
json.dump(results, open('output/system_comparison_15mechs.json', 'w'), indent=2)
print('Saved: output/system_comparison_15mechs.json')
