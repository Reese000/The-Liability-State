#!/usr/bin/env python3
"""
run_system_comparison.py — Multi-seed system comparison.

Runs all 11 Phase 8 systems across N seeds with both
Harberger OFF and ON (configurable). Saves to output/.

Usage:
    python run_system_comparison.py              # 5 seeds, Harberger OFF
    python run_system_comparison.py --harberger   # 5 seeds, Harberger ON
    python run_system_comparison.py --quick       # 2 seeds, Harberger OFF
"""
import sys, os, json, time, copy
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS, SEEDS, summarize

HARBERGER_SYSTEMS = ['Pure_Georgist', 'LS_Full', 'Mutualist_LS', 'Worker_Coop',
                     'Harberger_Georgist', 'Laissez_Faire']

def run_batch(seeds, configs, name_suffix=''):
    results = {}
    t0 = time.time()
    for cfg in configs:
        sys_name = cfg.get('system_name', 'unknown') + name_suffix
        sys_out = []
        for seed in seeds:
            w, r, b = gen_population(seed)
            # Deep copy to prevent mutation across seeds
            cfg_copy = copy.deepcopy(cfg)
            result = run_phase8(
                [dict(w2) for w2 in w],
                [dict(r2) for r2 in r],
                [dict(b2) for b2 in b],
                seed, cfg_copy
            )
            sys_out.append(result)
        results[sys_name] = sys_out
        wmean = np.mean([r['w_mean'] for r in sys_out])
        gini = np.mean([r['gini'] for r in sys_out])
        crra = np.mean([r.get('crra_welfare', 0) for r in sys_out])
        print(f'  {sys_name:<22} Mean=${wmean:>8,.0f} Gini={gini:.4f} CRRA={crra:.1f}')
    print(f'  Time: {time.time()-t0:.0f}s')
    return results

def main():
    use_harberger = '--harberger' in sys.argv
    quick = '--quick' in sys.argv
    seeds = [1, 2] if quick else SEEDS  # SEEDS = [1,2,3,4,5]
    
    print(f'System Comparison — {len(seeds)} seeds × {len(PHASE8_CONFIGS)} systems')
    print(f'Harberger: {"ON" if use_harberger else "OFF"}')
    
    configs = list(PHASE8_CONFIGS.values())
    
    if use_harberger:
        # Only systems with LVT-based tax get Harberger
        configs_h = []
        for cfg in configs:
            cfg = copy.deepcopy(cfg)
            if cfg.get('system_name') in HARBERGER_SYSTEMS:
                cfg['use_harberger'] = True
            configs_h.append(cfg)
        configs = configs_h
    
    results = run_batch(seeds, configs, '_H' if use_harberger else '')
    
    summarize(results)
    
    # Save
    suffix = '_harberger' if use_harberger else ''
    fname = f'output/system_comparison{suffix}.json'
    os.makedirs('output', exist_ok=True)
    with open(fname, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'Saved: {fname}')

if __name__ == '__main__':
    main()
