#!/usr/bin/env python3
"""Edge-case tests for forced_reinvestment mechanism."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from missing_mechanisms import apply_forced_reinvestment

rng = np.random.RandomState(42)
passed = 0; failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        passed += 1; print(f"  PASS: {name}")
    else:
        failed += 1; print(f"  FAIL: {name}")

# 1. Disabled
r = apply_forced_reinvestment({'forced_reinvestment': False}, rng, [], [], [], {}, 1, {})
check("disabled returns {}", r == {})

# 2. No businesses
r = apply_forced_reinvestment({'forced_reinvestment': True}, rng, [], [], [], {}, 1, {})
check("no businesses returns {}", r == {})

# 3. Normal case
b = [{'id': 'b1', 'capital': 500000.0}]
bl = {'b1': 500000.0, 'sys': 1_000_000}
r = apply_forced_reinvestment({'forced_reinvestment': True}, rng, [], [], b, bl, 1, {})
check("returns dict", isinstance(r, dict))
check("reinvested > 0", r.get('reinvested', 0) > 0)
check("capital increased", abs(b[0]['capital'] - 610250) < 1)
check("cash decreased", abs(bl['b1'] - 395000) < 1)

# 4. Zero capital
b2 = [{'id': 'b1', 'capital': 0}]
bl2 = {'b1': 500000.0, 'sys': 1_000_000}
r = apply_forced_reinvestment({'forced_reinvestment': True}, rng, [], [], b2, bl2, 1, {})
check("zero capital skips", r.get('businesses_affected', 0) == 0)

# 5. Negative cash
b3 = [{'id': 'b1', 'capital': 500000.0}]
bl3 = {'b1': -1000.0, 'sys': 1_000_000}
r = apply_forced_reinvestment({'forced_reinvestment': True}, rng, [], [], b3, bl3, 1, {})
check("negative cash skips", r.get('businesses_affected', 0) == 0)

# 6. Below threshold
b4 = [{'id': 'b1', 'capital': 500000.0}]
bl4 = {'b1': 100000.0, 'sys': 1_000_000}
r = apply_forced_reinvestment({'forced_reinvestment': True}, rng, [], [], b4, bl4, 1, {})
check("below threshold skips", r.get('businesses_affected', 0) == 0)

# 7. Multiple businesses
b5 = [{'id': 'b1', 'capital': 500000.0}, {'id': 'b2', 'capital': 200000.0}]
bl5 = {'b1': 500000.0, 'b2': 800000.0, 'sys': 1_000_000}
r = apply_forced_reinvestment({'forced_reinvestment': True}, rng, [], [], b5, bl5, 1, {})
check("multiple businesses", r.get('businesses_affected', 0) == 2)

# 8-10. Clamping
b6 = [{'id': 'b1', 'capital': 500000.0}]
bl6 = {'b1': 500000.0, 'sys': 1_000_000}
r = apply_forced_reinvestment({'forced_reinvestment': True, 'reinvestment_rate': 2.0}, rng, [], [], b6, bl6, 1, {})
check("rate clamped to 1.0 (doesn't crash)", isinstance(r, dict))
r = apply_forced_reinvestment({'forced_reinvestment': True, 'reinvestment_boost': -0.5}, rng, [], [], b6, bl6, 1, {})
check("negative boost clamped (doesn't crash)", isinstance(r, dict))
r = apply_forced_reinvestment({'forced_reinvestment': True, 'reinvestment_boost': 0.5}, rng, [], [], b6, bl6, 1, {})
check("boost clamped to 0.2 (doesn't crash)", isinstance(r, dict))

total = passed + failed
print(f"\nResults: {passed} passed, {failed} failed out of {total}")
if failed == 0:
    print("ALL TESTS PASSED")
