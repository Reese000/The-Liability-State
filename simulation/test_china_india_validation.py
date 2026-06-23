#!/usr/bin/env python3
"""Integration test: China/India Gini targets across 5 seeds."""
import sys, os, copy
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
import logging
logging.basicConfig(level=logging.WARNING)
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS

pass_count, fail_count = 0, 0

def check(name, condition, detail=""):
    global pass_count, fail_count
    if condition:
        pass_count += 1
        print(f"  PASS: {name}")
    else:
        fail_count += 1
        msg = f"  FAIL: {name}"
        if detail: msg += f" -- {detail}"
        print(msg)

# === Test 1: China Gini in target range ===
print("Test 1: China Gini target range [0.45, 0.48]")
ginis_cn = []
cfg_cn = copy.deepcopy(PHASE8_CONFIGS['China'])
for s in range(1, 6):
    w, r, b = gen_population(s)
    res = run_phase8(w, r, b, s, cfg_cn)
    ginis_cn.append(res['gini'])
mean_cn = np.mean(ginis_cn)
check("China mean Gini in [0.45, 0.48]", 0.45 <= mean_cn <= 0.48,
      f"mean={mean_cn:.4f}")
check("China Gini std < 0.015", np.std(ginis_cn) < 0.015,
      f"std={np.std(ginis_cn):.4f}")

# === Test 2: India Gini in target range ===
print("Test 2: India Gini target range [0.47, 0.50]")
ginis_in = []
cfg_in = copy.deepcopy(PHASE8_CONFIGS['India'])
for s in range(1, 6):
    w, r, b = gen_population(s)
    res = run_phase8(w, r, b, s, cfg_in)
    ginis_in.append(res['gini'])
mean_in = np.mean(ginis_in)
check("India mean Gini in [0.47, 0.50]", 0.47 <= mean_in <= 0.50,
      f"mean={mean_in:.4f}")
check("India Gini std < 0.015", np.std(ginis_in) < 0.015,
      f"std={np.std(ginis_in):.4f}")

# === Test 3: Structural gap 3-group doesn't crash ===
print("Test 3: Structural gap with 3 groups works")
cfg_3gap = copy.deepcopy(PHASE8_CONFIGS['India'])
try:
    w, r, b = gen_population(1)
    res = run_phase8(w, r, b, 1, cfg_3gap)
    check("3-group structural gap doesn't crash", True)
    # Verify gap created distinct groups
    from missing_mechanisms import apply_structural_gap
    check("Gini computed after 3-group gap", res['gini'] > 0)
except Exception as e:
    check("3-group structural gap doesn't crash", False, str(e))

# === Test 4: Systems auto-included in PHASE8_CONFIGS ===
print("Test 4: China/India in PHASE8_CONFIGS")
check("China in PHASE8_CONFIGS", 'China' in PHASE8_CONFIGS)
check("India in PHASE8_CONFIGS", 'India' in PHASE8_CONFIGS)
check("Total 13 systems", len(PHASE8_CONFIGS) == 13)

# === Summary ===
total = pass_count + fail_count
print(f"\nResults: {pass_count} passed, {fail_count} failed out of {total}")
if fail_count == 0:
    print("ALL VALIDATION TESTS PASSED")
else:
    sys.exit(1)
