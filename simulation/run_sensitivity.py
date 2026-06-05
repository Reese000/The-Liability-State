#!/usr/bin/env python3
"""Sensitivity analysis: LVT rate and income tax rate sweeps."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS

SEED = 42

def get_base(name):
    matching = [cfg for cfg in PHASE8_CONFIGS.values() if cfg.get('system_name') == name]
    return matching[0] if matching else None

print("LVT RATE SENSITIVITY")
print(f"{'System':<18} {'LVT Rate':>8} {'Gini':>8} {'Mean$':>10} {'CRRA':>10}")
print("-" * 56)

for sys_name in ['LS_Full', 'Pure_Georgist']:
    base = get_base(sys_name)
    if not base:
        continue
    for rate in [0.01, 0.02, 0.03, 0.04, 0.05, 0.07]:
        cfg = dict(base, lvt_rate=rate)
        w, r, b = gen_population(SEED)
        res = run_phase8(w, r, b, SEED, cfg)
        print(f"{sys_name:<18} {rate:>8.2f} {res['gini']:>8.4f} ${res['w_mean']:>7,.0f} {res.get('crra_welfare',0):>10.1f}")

print()
print("INCOME TAX RATE SENSITIVITY")
print(f"{'System':<18} {'Tax Rate':>8} {'Gini':>8} {'Mean$':>10} {'CRRA':>10}")
print("-" * 56)

for sys_name in ['US_Style', 'Nordic']:
    base = get_base(sys_name)
    if not base:
        continue
    base_tax = base.get('income_tax_rate', 0.20)
    for rate in [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]:
        cfg = dict(base, income_tax_rate=rate)
        if base_tax > 0:
            cfg['welfare_rate'] = base.get('welfare_rate', 0.0) * (rate / base_tax)
        else:
            cfg['welfare_rate'] = rate * 0.5
        w, r, b = gen_population(SEED)
        res = run_phase8(w, r, b, SEED, cfg)
        print(f"{sys_name:<18} {rate:>8.2f} {res['gini']:>8.4f} ${res['w_mean']:>7,.0f} {res.get('crra_welfare',0):>10.1f}")
