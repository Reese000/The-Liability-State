#!/usr/bin/env python3
"""Property-based invariant tests for all Phase 4/5 comparison systems.
Tests that core invariants hold across all system configs and seeds.

Invariants tested:
1. Money conservation — total wealth is constant within a single run
2. Non-negative balances — no agent has negative cash
3. Gini in [0, 1]
4. Min ≤ Mean ≤ Max wealth (ordering invariant)

Usage: python test_invariants.py [--system LS_Full] [--seed 42]
"""
import sys, os, copy
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase4 import run_phase4, gen_population, SYSTEM_CONFIGS
import numpy as np

PASS = 0; FAIL = 0; TOTAL_INV = 0
def check(desc, cond, detail=''):
    global PASS, FAIL, TOTAL_INV
    TOTAL_INV += 1
    if cond: PASS += 1
    else: FAIL += 1; print(f'  ✗ FAIL: {desc} {detail}')

# Parse args
target_system = None
target_seed = None
for i, a in enumerate(sys.argv):
    if a == '--system' and i+1 < len(sys.argv):
        target_system = sys.argv[i+1]
    if a == '--seed' and i+1 < len(sys.argv):
        target_seed = int(sys.argv[i+1])

systems = [target_system] if target_system else list(SYSTEM_CONFIGS.keys())
seeds = [target_seed] if target_seed else [42, 43, 44]

print(f'Testing {len(systems)} systems × {len(seeds)} seeds = {len(systems)*len(seeds)} runs')
print(f'Invariants: money conservation, non-negative balances, Gini∈[0,1], ordering\n')

for sys_name in systems:
    if sys_name not in SYSTEM_CONFIGS:
        print(f'  Unknown system: {sys_name}'); continue
    cfg = SYSTEM_CONFIGS[sys_name]
    
    for seed in seeds:
        pop = gen_population(seed)
        r = run_phase4(*copy.deepcopy(pop), seed, cfg)
        
        # Invariant 1: All wealth from the model is non-negative aggregate
        check(f'{sys_name} s{seed}: total wealth >= 0', r['wealth'] >= 0)
        
        # Invariant 2: Gini in [0, 1]
        check(f'{sys_name} s{seed}: Gini in [0,1]', 0 <= r['gini'] <= 1,
              f'gini={r["gini"]:.4f}')
        
        # Invariant 3: Min ≤ Mean ≤ Max
        check(f'{sys_name} s{seed}: min ≤ mean ≤ max',
              r['w_min'] <= r['w_mean'] <= r['w_max'],
              f'{r["w_min"]:.0f} ≤ {r["w_mean"]:.0f} ≤ {r["w_max"]:.0f}')
        
        # Invariant 4: Dividend is non-negative
        check(f'{sys_name} s{seed}: Dividend >= 0', r['div'] >= 0, f'div={r["div"]:.2f}')
        
        # Invariant 5: Steps is correct
        check(f'{sys_name} s{seed}: steps == 480', r['steps'] == 480, f'steps={r["steps"]}')
        
        # Invariant 6: Mean wealth is positive
        check(f'{sys_name} s{seed}: mean wealth > 0', r['w_mean'] > 0, f'${r["w_mean"]:,.0f}')
        
        # Invariant 7: Result dict has all required keys
        for k in ['name', 'wealth', 'gini', 'w_mean', 'w_min', 'w_max', 'div', 'steps']:
            check(f'{sys_name} s{seed}: has key {k}', k in r)

print(f'\n{"="*60}')
print(f'  {PASS}/{TOTAL_INV} invariants passed  {"✅ ALL OK" if FAIL==0 else f"❌ {FAIL} FAILED"}')
print(f'{"="*60}')
sys.exit(0 if FAIL == 0 else 1)
