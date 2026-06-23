#!/usr/bin/env python3
"""Calibration sweep for US_Style and Singapore mechanism parameters.
Tests by modulating only the overshooting parameters to hit Gini targets."""
import sys, os, json, copy, time
import numpy as np
sys.path.insert(0, 'src')
import logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(message)s')
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS

SEED = 1  # Single seed for calibration speed

# ── US Calibration ──────────────────────────────────────────────
# Target: Gini ~0.49. Current: 0.737
# Active: power_law_exponent=0.28, immigrant_share=0.15, structural_gap=[1.0,0.15], inheritance_conc=0.85

us_cfg = copy.deepcopy(PHASE8_CONFIGS['US_Style'])
us_base = {k: v for k, v in us_cfg.items()
           if k in ('inheritance_flow_fraction', 'inheritance_concentration',
                    'use_immigrant_labor', 'immigrant_share', 'immigrant_wage_penalty',
                    'use_power_law_wealth', 'power_law_exponent', 'wealth_tail_fraction',
                    'use_structural_gap', 'structural_gap_groups', 'structural_gap_multipliers',
                    'structural_gap_recurrence')}

print("=" * 70)
print("US CALIBRATION — Vary power_law_exponent")
print("=" * 70)
print(f"{'exponent':<10} {'Gini':>8} {'Wealth':>12}")
print("-" * 32)
for exp in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.28]:
    cfg = copy.deepcopy(us_cfg)
    cfg['power_law_exponent'] = exp
    w, r, b = gen_population(SEED)
    res = run_phase8(w, r, b, SEED, cfg)
    print(f"{exp:<10.2f} {res['gini']:>8.4f} ${res['w_mean']:>9,.0f}")

print()
print("US CALIBRATION — Vary immigrant_share (exp=0.20)")
print("-" * 55)
for imm_share in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]:
    cfg = copy.deepcopy(us_cfg)
    cfg['power_law_exponent'] = 0.20
    cfg['immigrant_share'] = imm_share
    w, r, b = gen_population(SEED)
    res = run_phase8(w, r, b, SEED, cfg)
    print(f"  imm_share={imm_share:<.2f}  Gini={res['gini']:.4f}  Wealth=${res['w_mean']:>9,.0f}")

print()
print("US CALIBRATION — Vary structural_gap_multipliers (exp=0.20, imm=0.10)")
print("-" * 70)
for gap_mul in [0.05, 0.10, 0.20, 0.30, 0.50]:
    cfg = copy.deepcopy(us_cfg)
    cfg['power_law_exponent'] = 0.20
    cfg['immigrant_share'] = 0.10
    cfg['structural_gap_multipliers'] = [1.0, gap_mul]
    w, r, b = gen_population(SEED)
    res = run_phase8(w, r, b, SEED, cfg)
    print(f"  gap_mult={gap_mul:<.2f}  Gini={res['gini']:.4f}  Wealth=${res['w_mean']:>9,.0f}")

# ── Singapore Calibration ──────────────────────────────────────────
print()
print("=" * 70)
print("SINGAPORE CALIBRATION — Vary immigrant_share")
print("=" * 70)
sg_cfg = copy.deepcopy(PHASE8_CONFIGS['Singapore'])
for imm_share in [0.0, 0.10, 0.20, 0.30, 0.42]:
    cfg = copy.deepcopy(sg_cfg)
    cfg['immigrant_share'] = imm_share
    w, r, b = gen_population(SEED)
    res = run_phase8(w, r, b, SEED, cfg)
    print(f"  imm_share={imm_share:<.2f}  Gini={res['gini']:.4f}  Wealth=${res['w_mean']:>9,.0f}")

print()
print("SINGAPORE CALIBRATION — Vary immigrant_wage_penalty (imm_share=0.35)")
print("-" * 70)
for penalty in [0.0, 0.20, 0.40, 0.50, 0.60, 0.70]:
    cfg = copy.deepcopy(sg_cfg)
    cfg['immigrant_share'] = 0.35
    cfg['immigrant_wage_penalty'] = penalty
    w, r, b = gen_population(SEED)
    res = run_phase8(w, r, b, SEED, cfg)
    print(f"  penalty={penalty:<.2f}  Gini={res['gini']:.4f}  Wealth=${res['w_mean']:>9,.0f}")
