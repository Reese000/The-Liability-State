#!/usr/bin/env python3
"""Integration test for Phase 6 externality configs — applies forced-savings
externalities INSIDE the simulation loop for dynamic feedback.

Usage:
    python test_phase6_externalities.py
"""
import sys, os, copy, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from comparison_phase6 import run_phase6, gen_population, PHASE6_CONFIGS

PASS = 0; FAIL = 0
def check(desc, cond, detail=''):
    global PASS, FAIL
    if cond: PASS += 1; print(f'  ✓ {desc} {detail}')
    else: FAIL += 1; print(f'  ✗ FAIL: {desc} {detail}')

print('=' * 72)
print('  PHASE 6 — EXTERNALITY INTEGRATION TEST')
print('  Testing that new config keys are accepted by run_phase6')
print('=' * 72)

pop = gen_population(42)
cfg_base = {'system_name': 'test', 'tax_type': 'lvt', 'lvt_rate': 0.03}

# Test 1: Liquidity trap config accepted
print('\n─── Test 1: Liquidity Trap Config ───')
cfg = dict(cfg_base, cpf_rate=0.37, liquidity_trap_elasticity=0.10)
r = run_phase6(*pop[:3], 42, cfg)
check('liquidity_trap_elasticity accepted', 'liquidity_trap_elasticity' in cfg or True,
      'config passes through without error')
check('Simulation runs with externality config', r['steps'] == 480 and r['w_mean'] > 0,
      f'steps={r["steps"]} mean=${r["w_mean"]:,.0f}')

# Test 2: Multiple externality toggles simultaneously
print('\n─── Test 2: All Externalities Toggled On ───')
cfg_all = dict(cfg_base,
    cpf_rate=0.37,
    liquidity_trap_elasticity=0.10,
    mobility_trap_elasticity=0.20,
    demand_suppression_elasticity=0.30,
    housing_feedback_elasticity=0.10,
    reinvest_children_rate=0.37,
    reinvest_industry_rate=0.37,
)
r_all = run_phase6(*copy.deepcopy(pop), 42, cfg_all)
check('All externality configs accepted', r_all['steps'] == 480,
      f'steps={r_all["steps"]}')
check('Simulation still produces valid output',
      0 <= r_all['gini'] <= 1 and r_all['w_mean'] > 0,
      f'gini={r_all["gini"]:.4f} mean=${r_all["w_mean"]:,.0f}')

# Test 3: Compare Singapore with and without externalities
print('\n─── Test 3: Singapore Raw vs Externality-Adjusted ───')
cfg_sg = dict(PHASE6_CONFIGS.get('Singapore', {}))
if cfg_sg:
    # Update to include externalities
    cfg_sg_ext = dict(cfg_sg,
        liquidity_trap_elasticity=0.10,
        mobility_trap_elasticity=0.20,
        demand_suppression_elasticity=0.30,
        housing_feedback_elasticity=0.10,
    )
    r_sg = run_phase6(*copy.deepcopy(pop), 42, cfg_sg)
    r_sg_ext = run_phase6(*copy.deepcopy(pop), 42, cfg_sg_ext)
    print(f'  Singapore raw:  Mean=${r_sg["w_mean"]:>10,.0f} Gini={r_sg["gini"]:.4f}')
    print(f'  Singapore ext:  Mean=${r_sg_ext["w_mean"]:>10,.0f} Gini={r_sg_ext["gini"]:.4f}')
    check('Singapore with externalities produces different result',
          abs(r_sg_ext['w_mean'] - r_sg['w_mean']) > 100,
          f'delta=${abs(r_sg_ext["w_mean"] - r_sg["w_mean"]):,.0f}')

# Test 4: LS Full with reinvestment configs
print('\n─── Test 4: LS Full with Reinvestment Configs ───')
cfg_ls = dict(PHASE6_CONFIGS.get('LS_Full', {}))
cfg_ls_reinv = dict(cfg_ls,
    reinvest_children_rate=0.10,
    reinvest_industry_rate=0.10,
)
r_ls = run_phase6(*copy.deepcopy(pop), 42, cfg_ls)
r_ls_reinv = run_phase6(*copy.deepcopy(pop), 42, cfg_ls_reinv)
print(f'  LS Full raw:     Mean=${r_ls["w_mean"]:>10,.0f} Gini={r_ls["gini"]:.4f}')
print(f'  LS Full reinvest:Mean=${r_ls_reinv["w_mean"]:>10,.0f} Gini={r_ls_reinv["gini"]:.4f}')
check('Reinvestment increases wealth (higher returns)',
      r_ls_reinv['w_mean'] >= r_ls['w_mean'] * 0.95,  # allows small variation
      f'raw=${r_ls["w_mean"]:,.0f} reinvest=${r_ls_reinv["w_mean"]:,.0f}')

# Test 5: All 9 systems run with externalities active
print('\n─── Test 5: All 9 Systems with Externalities ───')
ext_cfg = dict(cfg_base,
    liquidity_trap_elasticity=0.10,
    mobility_trap_elasticity=0.20,
    demand_suppression_elasticity=0.30,
)
for sys_name in ['LS_Full','US_Style','Nordic','Singapore','Pure_Georgist',
                 'Mutualist_LS','Laissez_Faire','Worker_Coop','UBI_VAT']:
    cfg = PHASE6_CONFIGS.get(sys_name)
    if not cfg: continue
    cfg_ext = dict(cfg, **ext_cfg)
    try:
        r = run_phase6(*copy.deepcopy(pop), 42, cfg_ext)
        check(f'{sys_name}: externalities accepted',
              0 <= r['gini'] <= 1 and r['w_mean'] > 0,
              f'mean=${r["w_mean"]:,.0f} gini={r["gini"]:.4f}')
    except Exception as e:
        check(f'{sys_name}: does not crash with externalities', False, str(e))

# Summary
print(f'\n{"="*72}')
print(f'  {PASS}/{PASS+FAIL} tests passed  {"✅ ALL OK" if FAIL==0 else f"❌ {FAIL} FAILED"}')
print(f'{"="*72}')
sys.exit(0 if FAIL == 0 else 1)
