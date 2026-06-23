#!/usr/bin/env python3
"""13-system comparison: 5 seeds x 13 systems"""
import sys, os, json, time, copy
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
import logging
logging.basicConfig(level=logging.WARNING)
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS

SEEDS = list(range(1, 6))
results = {}
t0 = time.time()
for name in sorted(PHASE8_CONFIGS.keys()):
    cfg = copy.deepcopy(PHASE8_CONFIGS[name])
    sys_out = []
    for seed in SEEDS:
        w, r, b = gen_population(seed)
        res = run_phase8(w, r, b, seed, cfg)
        sys_out.append(res)
    results[name] = sys_out
    wm = np.mean([r['w_mean'] for r in sys_out])
    gm = np.mean([r['gini'] for r in sys_out])
    print(f'{name:<22} Mean=${wm:>9,.0f} Gini={gm:.4f}')

elapsed = time.time() - t0
print(f'\nTime: {elapsed:.0f}s for {len(SEEDS)*len(PHASE8_CONFIGS)} simulations')
os.makedirs('output', exist_ok=True)
json.dump(results, open('output/phase8_13system.json', 'w'), indent=2)
print('Saved: output/phase8_13system.json')
