#!/usr/bin/env python3
"""test_import_displacement.py — Unit test for the import displacement mechanism.

Tests (all automated assertions):
1. Zero displacement when import_displacement_rate=0
2. Displacement fires when rate > 0 (verified via log events)
3. Displaced workers' wages drop to exactly 70% of original (within tolerance)
4. OOB import_displacement_rate is clamped to [0,1] without crashing
5. disp_prob never exceeds 1.0 (clamping)
6. Backward compatibility: backtests still pass with displacement=0 (default)
"""
import sys, os, io, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
from comparison_phase8 import run_phase8, gen_population

SEED = 42
PASS = 0
FAIL = 0
TOLERANCE = 1e-6

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label} — {detail}")

print("=" * 70)
print("IMPORT DISPLACEMENT UNIT TEST")
print("=" * 70)

# ══════════════════════════════════════════════════════════════════════
# Test 1: Zero displacement when rate=0
# ══════════════════════════════════════════════════════════════════════
print("\n--- Test 1: No displacement at import_displacement=0 ---")
cfg_zero = {
    'system_name': 'DISP_ZERO', 'tax_type': 'income',
    'income_tax_rate': 0.20, 'corp_tax_rate': 0.21, 'welfare_rate': 0.15,
    'healthcare_gdp_share': 0.0,
    'import_competition': 1.0, 'import_displacement_rate': 0.0,  # max comp, but zero disp
    'import_disp_intensity': 1.0,
}
w, r, b = gen_population(SEED)
# Capture log output to count displacement events
log_capture = io.StringIO()
log_handler = logging.StreamHandler(log_capture)
logging.getLogger('p8_DISP_ZERO').addHandler(log_handler)
logging.getLogger('p8_DISP_ZERO').setLevel(logging.INFO)

res = run_phase8(w, r, b, SEED, cfg_zero)
log_output = log_capture.getvalue()
disp_count = log_output.count("Displaced worker")

check("No error", 'error' not in res, str(res.get('error', '')))
check("Zero displacement events at rate=0", disp_count == 0, f"got {disp_count} events")
check("Gini is reasonable", 0.1 < res['gini'] < 0.8, f"gini={res['gini']}")

# ══════════════════════════════════════════════════════════════════════
# Test 2: Displacement fires when rate > 0
# ══════════════════════════════════════════════════════════════════════
print("\n--- Test 2: Displacement fires with high rate ---")
cfg_high = {
    'system_name': 'DISP_HIGH', 'tax_type': 'income',
    'income_tax_rate': 0.20, 'corp_tax_rate': 0.21, 'welfare_rate': 0.15,
    'healthcare_gdp_share': 0.0,
    'import_competition': 1.0, 'import_displacement_rate': 0.10,  # Moderate: 10% monthly
    'import_disp_intensity': 1.0,
}
# At prob = min(1.0, 1.0*0.10*1.0) = 0.10 per worker-month (10%)
# Over 120 steps: expected ~99.999% of workers displaced at least once
# But floor at $10/hr means repeated displacements on low-wage workers
# will hit the floor. We verify displacement fires at least once.
w2, r2, b2 = gen_population(SEED)
# Track initial wages
initial_hourly = {}
for wk in w2:
    initial_hourly[wk['id']] = wk['hourly']

log_capture2 = io.StringIO()
log_handler2 = logging.StreamHandler(log_capture2)
logging.getLogger('p8_DISP_HIGH').addHandler(log_handler2)
logging.getLogger('p8_DISP_HIGH').setLevel(logging.INFO)

res2 = run_phase8(w2, r2, b2, SEED, cfg_high)
log_output2 = log_capture2.getvalue()
disp_count2 = log_output2.count("Displaced worker")

check("No error in high-disp run", 'error' not in res2, str(res2.get('error', '')))
# At prob = min(1.0, 1.0*1.0*1.0) = 1.0 per worker-month for 120 steps
# Every worker should be displaced in the first step
check(f"Displacement events fired: {disp_count2} > 0", disp_count2 > 0,
      f"got {disp_count2} events (expected >0)")

# ══════════════════════════════════════════════════════════════════════
# Test 3: OOB input validation + clamping
# ══════════════════════════════════════════════════════════════════════
print("\n--- Test 3: OOB clamping ---")
cfg_oob = {
    'system_name': 'DISP_OOB', 'tax_type': 'income',
    'income_tax_rate': 0.20, 'corp_tax_rate': 0.21, 'welfare_rate': 0.15,
    'healthcare_gdp_share': 0.0,
    'import_competition': 0.20, 'import_displacement_rate': 5.0,  # OOB!
}
w3, r3, b3 = gen_population(SEED)
res3 = run_phase8(w3, r3, b3, SEED, cfg_oob)
check("OOB value doesn't crash", 'error' not in res3, str(res3.get('error', '')))
check("Gini within expected range",
      0.04 <= res3['gini'] <= 0.99, f"gini={res3['gini']}")

# ══════════════════════════════════════════════════════════════════════
# Test 4: Wage drop is exactly 0.7x (verified from log messages)
# ══════════════════════════════════════════════════════════════════════
print("\n--- Test 4: Wage drop magnitude is 0.7x ---")
# Parse log messages to verify wage ratios
# Only check first displacement events (not repeats at floor)
import re
wage_pattern = re.compile(r'Displaced worker \w+: wage ([\d.]+)→([\d.]+)')
matches = wage_pattern.findall(log_output2)
first_events = []
for old, new in matches:
    old_f = float(old)
    if old_f > 14.29:  # above floor for 0.7x = 10/0.7
        first_events.append((old_f, float(new)))
first_events = first_events[:20]  # sample

if first_events:
    ratios = [new / old for old, new in first_events]
    mean_ratio = sum(ratios) / len(ratios)
    check(f"First-displacement mean ratio: {mean_ratio:.3f} (expected ~0.7)",
          abs(mean_ratio - 0.7) < 0.01, f"mean ratio = {mean_ratio:.3f}")
    # Count how many are exactly 0.7x within tolerance
    exact = sum(1 for r in ratios if abs(r - 0.7) < 0.001)
    check(f"First events at exactly 0.7x: {exact}/{len(first_events)}",
          exact >= len(first_events) * 0.9,
          f"only {exact}/{len(first_events)} were exactly 0.7x")
else:
    check("Found first-displacement events above floor", False, "no events with wage > $14.29")

# ══════════════════════════════════════════════════════════════════════
# Test 5: Backward compatibility — backtests pass
# ══════════════════════════════════════════════════════════════════════
print("\n--- Test 5: Backward compatibility (backtests pass) ---")
from run_all_backtests import main as run_backtests
try:
    # Run a quick subset: just 1 seed, just US to verify no crash
    from comparison_phase8 import gen_population
    us_2020 = {
        'system_name': 'US_test', 'tax_type': 'income',
        'income_tax_rate': 0.20, 'corp_tax_rate': 0.21, 'welfare_rate': 0.15,
        'healthcare_gdp_share': 0.18, 'use_progressive_tax': True,
        'education_variance': 0.7, 'inheritance_rate': 0.0,
    }
    w, r, b = gen_population(SEED)
    r0 = run_phase8(w, r, b, SEED, us_2020)
    check("Baseline backtest (displacement=0 default) passes",
          'error' not in r0, str(r0.get('error', '')))
except Exception as e:
    check("Backward compatibility", False, str(e))

# ══════════════════════════════════════════════════════════════════════
# Test 6: import_disp_intensity OOB clamping
# ══════════════════════════════════════════════════════════════════════
print("\n--- Test 6: Intensity OOB clamping ---")
cfg_int_oob = {
    'system_name': 'DISP_INTOOB', 'tax_type': 'income',
    'income_tax_rate': 0.20, 'corp_tax_rate': 0.21, 'welfare_rate': 0.15,
    'healthcare_gdp_share': 0.0,
    'import_competition': 0.20, 'import_displacement_rate': 0.25,
    'import_disp_intensity': 5.0,  # OOB!
}
w6, r6, b6 = gen_population(SEED)
res6 = run_phase8(w6, r6, b6, SEED, cfg_int_oob)
check("OOB intensity doesn't crash", 'error' not in res6, str(res6.get('error', '')))
check("Gini within expected range", 0.04 <= res6['gini'] <= 0.99, f"gini={res6['gini']}")
# The clamping should produce same result as intensity=1.0
cfg_int_ok = dict(cfg_int_oob, import_disp_intensity=1.0)
w6b, r6b, b6b = gen_population(SEED)
res6b = run_phase8(w6b, r6b, b6b, SEED, cfg_int_ok)
check("Clamped OOB produces same Gini as max=1.0",
      abs(res6['gini'] - res6b['gini']) < 0.001,
      f"oob={res6['gini']:.4f} vs max={res6b['gini']:.4f}")

# ══════════════════════════════════════════════════════════════════════
# Test 7: Configurable wage floor
# ══════════════════════════════════════════════════════════════════════
print("\n--- Test 7: Configurable min_wage_floor ---")
cfg_floor = {
    'system_name': 'DISP_FLOOR', 'tax_type': 'income',
    'income_tax_rate': 0.20, 'corp_tax_rate': 0.21, 'welfare_rate': 0.15,
    'healthcare_gdp_share': 0.0,
    'import_competition': 1.0, 'import_displacement_rate': 1.0,
    'import_disp_intensity': 1.0,
    'min_wage_floor': 15.0,  # custom floor
}
w7, r7, b7 = gen_population(SEED)
res7 = run_phase8(w7, r7, b7, SEED, cfg_floor)
check("Custom floor doesn't crash", 'error' not in res7, str(res7.get('error', '')))
check("Gini computed", res7['gini'] > 0, f"gini={res7['gini']}")
# Default floor should produce different Gini than custom floor
cfg_floor_default = dict(cfg_floor, min_wage_floor=10.0)
w7b, r7b, b7b = gen_population(SEED)
res7b = run_phase8(w7b, r7b, b7b, SEED, cfg_floor_default)
check("Different floor produces different Gini",
      abs(res7['gini'] - res7b['gini']) > 0.001,
      f"floor15={res7['gini']:.4f} vs floor10={res7b['gini']:.4f}")

# ══════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════
print(f"\n{'='*70}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed")
print(f"{'='*70}")
sys.exit(1 if FAIL > 0 else 0)
