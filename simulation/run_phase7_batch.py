"""Phase 7 full batch comparison — externality-adjusted results."""
import sys, os, copy, json, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
from comparison_phase7 import run_phase7, gen_population, PHASE7_CONFIGS
from comparison_phase6 import run_phase6, PHASE6_CONFIGS

SEEDS = list(range(1, 4))
t0 = time.time()

results_raw = {}
results_ext = {}

for sys_name in list(PHASE7_CONFIGS.keys()):
    cfg_ext = PHASE7_CONFIGS.get(sys_name)
    cfg_raw = PHASE6_CONFIGS.get(sys_name)
    if not cfg_ext: continue
    
    raw_vals, ext_vals = [], []
    for seed in SEEDS:
        pop = gen_population(seed)
        # Phase 6 (no externalities)
        if cfg_raw:
            r6 = run_phase6(*copy.deepcopy(pop), seed, cfg_raw)
            raw_vals.append(r6['w_mean'])
        # Phase 7 (with externalities)
        r7 = run_phase7(*copy.deepcopy(pop), seed, cfg_ext)
        ext_vals.append(r7['w_mean'])
    
    raw_m = np.mean(raw_vals) if raw_vals else 0
    ext_m = np.mean(ext_vals)
    results_raw[sys_name] = raw_m
    results_ext[sys_name] = ext_m
    
    if raw_m > 0:
        print(f'{sys_name:<22} Raw=${raw_m:>8,.0f}  Ext=${ext_m:>8,.0f}  ({ext_m/raw_m*100-100:+.1f}%)')
    else:
        print(f'{sys_name:<22} Ext=${ext_m:>8,.0f}')

elapsed = time.time()-t0
print(f'\nTime: {elapsed:.0f}s')

# Rankings
print(f'\n{"Rank":<6}{"System":<22}{"Externality-Adj$":>16}{"Raw$":>12}{"Change":>10}')
print('-'*70)
ranked = sorted([(results_ext[sn], sn) for sn in results_ext], reverse=True)
for i, (val, name) in enumerate(ranked, 1):
    raw = results_raw.get(name, 0)
    chg = f'{val/raw*100-100:+.1f}%' if raw > 0 else 'N/A'
    print(f'{i:<6}{name:<22}${val:>10,.0f}   {"${:>9,.0f}".format(raw) if raw > 0 else "N/A":>12} {chg:>10}')

# Save
os.makedirs('output', exist_ok=True)
json.dump({'raw': results_raw, 'ext': results_ext}, open('output/phase7_batch.json', 'w'), indent=2)
print('\nSaved: output/phase7_batch.json')
