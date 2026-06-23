#!/usr/bin/env python3
"""End-to-end 13-system comparison + Pareto validation.
Validates: (1) 13 systems produce valid output, (2) Pareto frontier computed,
(3) China/India are dominated, (4) LS cluster systems on frontier."""
import sys, os, copy, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
import logging
logging.basicConfig(level=logging.WARNING)
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS

pass_count, fail_count = 0, 0
def check(name, cond, detail=""):
    global pass_count, fail_count
    if cond:
        pass_count += 1
        print(f"  PASS: {name}")
    else:
        fail_count += 1
        print(f"  FAIL: {name} -- {detail}")

# Step 1: Generate 13-system comparison data
print("=== 13-SYSTEM COMPARISON (5 seeds) ===")
seeds = list(range(1, 6))
results = {}
for name in sorted(PHASE8_CONFIGS.keys()):
    cfg = copy.deepcopy(PHASE8_CONFIGS[name])
    out = []
    for s in seeds:
        w, r, b = gen_population(s)
        out.append(run_phase8(w, r, b, s, cfg))
    results[name] = out

# Step 2: Build Pareto analysis
systems = {}
for sn, rs in results.items():
    systems[sn] = {
        'mean': np.mean([r['w_mean'] for r in rs]),
        'gini': np.mean([r['gini'] for r in rs]),
        'crra': np.mean([r['crra_welfare'] for r in rs]),
    }

metrics = ['mean', 'crra']
antimetrics = ['gini']

def dominates(a, b):
    sa, sb = systems[a], systems[b]
    a_b = all(sa[m] > sb[m] for m in metrics) and all(sa[m] < sb[m] for m in antimetrics)
    b_a = all(sb[m] > sa[m] for m in metrics) and all(sb[m] < sa[m] for m in antimetrics)
    if a_b: return 1
    if b_a: return -1
    return 0

names = sorted(systems.keys())
pareto_front = [a for a in names if not any(dominates(b, a) == 1 for b in names if b != a)]

# Print results
print(f"\n{'System':<22} {'Mean$':>10} {'Gini':>8} {'CRRA':>8} {'Frontier':>9}")
print("-" * 60)
for name in names:
    s = systems[name]
    f = "FRONTIER" if name in pareto_front else "DOMINATED"
    print(f"{name:<22} ${s['mean']:>7,.0f}  {s['gini']:.4f}  {s['crra']:.4f}  {f}")

# Step 3: Validate Pareto frontier
print("\n=== PARETO VALIDATION ===")
ls_systems = ['LS_Full', 'Mutualist_LS', 'Dual_Compact_LS']
check("China is dominated", 'China' not in pareto_front)
check("India is dominated", 'India' not in pareto_front)
check("US_Style is dominated", 'US_Style' not in pareto_front)
check("Nordic is dominated", 'Nordic' not in pareto_front)
check("LS_Full on frontier", 'LS_Full' in pareto_front)
check("Mutualist_LS on frontier", 'Mutualist_LS' in pareto_front)
check("Pure_Georgist on frontier", 'Pure_Georgist' in pareto_front)
check("Worker_Coop on frontier", 'Worker_Coop' in pareto_front)
check("Singapore on frontier", 'Singapore' in pareto_front)
check("At least 8 on frontier (of 13)", len(pareto_front) >= 8,
      f"actual={len(pareto_front)}")
check("13 systems total", len(names) == 13)

total = pass_count + fail_count
print(f"\nResults: {pass_count} passed, {fail_count} failed out of {total}")
if fail_count == 0:
    print("ALL PARETO VALIDATION PASSED")
else:
    sys.exit(1)
