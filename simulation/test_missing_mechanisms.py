#!/usr/bin/env python3
"""Isolated unit tests for all 10 missing mechanisms."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from missing_mechanisms import (
    apply_public_goods, apply_inflation, apply_bankruptcy,
    apply_gov_service_productivity, apply_forced_savings_externalities,
    apply_endogenous_tfp, apply_occupational_mobility,
    apply_wage_competition, apply_capital_ownership, apply_olg,
    MISSING_MECH_DEFAULTS,
)

PASS, FAIL = 0, 0
rng = np.random.RandomState(42)

def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ✅ {name}')
    else:
        FAIL += 1
        print(f'  ❌ {name}')

def make_workers(n=5):
    return [{'id': f'w{i:03d}', 'hourly': 20.0 + i*2, 'monthly': (20+i*2)*160,
             'land': 50000 + i*10000, 'cash': 50000} for i in range(n)]

def make_businesses(n=3):
    return [{'id': f'b{i}', 'tfp': 1.0 + i*0.2, 'capital': 100000 + i*50000} for i in range(n)]

def make_retirees(n=2):
    return [{'id': f'r{i:03d}', 'hourly': 0, 'monthly': 0, 'land': 100000, 'cash': 100000} for i in range(n)]

# ─── 1. Public Goods ────────────────────────────────────────────────

print('=== 1. Public Goods ===')
config = {'use_public_goods': True, 'tax_type': 'none', 'public_goods_penalty': 0.3}
workers = make_workers()
bal = {w['id']: 50000 for w in workers}
bal['sys'] = 500000000
result = apply_public_goods(config, rng, workers, [], [], bal, 1, {'total_tax': 0})
check('No-tax system triggers penalty', 'public_goods_penalty' in (result or {}))
# Check wages were reduced
check('Wages reduced by penalty', workers[0]['hourly'] < 20.0)

config2 = {'use_public_goods': True, 'tax_type': 'income', 'public_goods_target': 0.05}
w2 = make_workers()
b2 = {w2[0]['id']: 50000, 'sys': 500000000}
result2 = apply_public_goods(config2, rng, w2, [], [], b2, 1, {'total_tax': 10000})
check('Sufficient tax revenue triggers no penalty', result2 is None or 'public_goods_penalty' not in result2)

config3 = {'use_public_goods': False}
result3 = apply_public_goods(config3, rng, make_workers(), [], [], {}, 1, {})
check('Disabled returns empty dict', result3 == {})

# ─── 2. Inflation ──────────────────────────────────────────────────

print('\n=== 2. Inflation ===')
config_inf = {'inflation_rate': 0.02}
bal_inf = {'w000': 1000000, 'w001': 500000, 'sys': 0}
# Step 12 triggers inflation (yearly)
result_inf = apply_inflation(config_inf, rng, [], [], [], bal_inf, 12, {})
check('Inflation erodes cash (w000)', bal_inf['w000'] < 1000000)
check('Inflation doesn\'t fire on non-12 steps', 
      apply_inflation(config_inf, rng, [], [], [], {}, 1, {}) == {})

config_noinf = {'inflation_rate': 0.0}
check('Zero rate returns empty', apply_inflation(config_noinf, rng, [], [], [], {}, 1, {}) == {})

# ─── 3. Bankruptcy ─────────────────────────────────────────────────

print('\n=== 3. Bankruptcy ===')
config_bk = {'bankruptcy_threshold': -5000}
bal_bk = {'w000': -10000, 'w001': 50000, 'sys': 0}
workers_bk = [{'id': 'w000', 'land': 50000}, {'id': 'w001', 'land': 30000}]
result_bk = apply_bankruptcy(config_bk, rng, workers_bk, [], [], bal_bk, 1, {})
check('Bankrupt agent reset to 0', bal_bk['w000'] == 0)
check('Healthy agent unchanged', bal_bk['w001'] == 50000)
check('Land liquidated from bankrupt', workers_bk[0]['land'] == 0)
check('At least 1 bankruptcy', result_bk.get('bankruptcies', 0) >= 1)

config_nobk = {'bankruptcy_threshold': 0.0}
check('Positive threshold skips', apply_bankruptcy(config_nobk, rng, [], [], [], {}, 1, {}) == {})

# ─── 4. Government Services Productivity ───────────────────────────

print('\\n=== 4. Government Services ===')
config_gov = {'gov_service_productivity': 0.5, 'gov_service_elasticity': 0.15}
w_gov = make_workers()
bal_gov = {w['id']: 50000 for w in w_gov}
bal_gov['sys'] = 500000000
bal_gov['trust'] = 0
# Need step=13 (12+1 = annual trigger) with positive total_tax
result_gov = apply_gov_service_productivity(config_gov, rng, w_gov, [], [], bal_gov, 13, {'total_tax': 50000})
check('Hourly wage set', '_base_hourly' in w_gov[0])
hourly_after = w_gov[0]['hourly']
check('Productivity multiplier applied', hourly_after > 20.0)

config_nogov = {'gov_service_productivity': 0.0}
check('Disabled returns empty', apply_gov_service_productivity(config_nogov, rng, [], [], [], {}, 1, {}) == {})

# ─── 5. Forced Savings Externalities ───────────────────────────────

print('\n=== 5. Forced Savings Externalities ===')
config_fs = {'cpf_liquidity_trap': 0.10, 'cpf_demand_suppression': 0.10,
             'cpf_housing_feedback': 0.05, 'cpf_rate': 0.37}
w_fs = make_workers()
b_fs = make_businesses()
for b in b_fs:
    b['_base_tfp'] = b['tfp']
result_fs = apply_forced_savings_externalities(config_fs, rng, w_fs, [], b_fs, {}, 13, {})  # step 13 = annual trigger
check('Base hourly initialized', '_base_hourly' in w_fs[0])
check('Wage reduced (liquidity trap)', w_fs[0]['hourly'] < 20.0)
check('TFP reduced (demand suppression)', b_fs[0]['tfp'] < 1.0)

config_nofs = {'cpf_liquidity_trap': 0.0, 'cpf_demand_suppression': 0.0, 'cpf_housing_feedback': 0.0}
check('All zero returns empty', apply_forced_savings_externalities(config_nofs, rng, [], [], [], {}, 1, {}) == {})

# ─── 6. Endogenous TFP ─────────────────────────────────────────────

print('\n=== 6. Endogenous TFP ===')
config_tfp = {'endogenous_tfp': True, 'rnd_investment_rate': 0.05, 'tfp_growth_elasticity': 0.02}
b_tfp = make_businesses()
tfp_before = [b['tfp'] for b in b_tfp]
result_tfp = apply_endogenous_tfp(config_tfp, rng, [], [], b_tfp, {}, 1, {})
tfp_after = [b['tfp'] for b in b_tfp]
check('TFP grows over time', all(a > b for a, b in zip(tfp_after, tfp_before)))

config_notfp = {'endogenous_tfp': False}
check('Disabled returns empty', apply_endogenous_tfp(config_notfp, rng, [], [], [], {}, 1, {}) == {})

# ─── 7. Occupational Mobility ──────────────────────────────────────

print('\n=== 7. Occupational Mobility ===')
config_mob = {'mobility_cost': 0.02}
w_mob = make_workers(10)
bal_mob = {w['id']: 50000 for w in w_mob}
bal_mob['sys'] = 0
# Set one worker far from median to trigger mobility
w_mob[0]['hourly'] = 5.0
w_mob[0]['monthly'] = 5.0 * 160
result_mob = apply_occupational_mobility(config_mob, rng, w_mob, [], [], bal_mob, 1, {})
check('Some job switches occurred', result_mob.get('job_switches', 0) > 0)
check('Mobility cost deducted from balance', bal_mob[w_mob[0]['id']] < 50000)

config_nomob = {'mobility_cost': 0.0}
check('Zero cost returns empty', apply_occupational_mobility(config_nomob, rng, [], [], [], {}, 1, {}) == {})

# ─── 8. Wage Competition ───────────────────────────────────────────

print('\n=== 8. Wage Competition ===')
config_wc = {'wage_competition': True, 'wage_competition_intensity': 0.3}
w_wc = make_workers(10)
# Make one very low wage and one very high wage
w_wc[0]['hourly'] = 5.0
w_wc[-1]['hourly'] = 50.0
low_before = w_wc[0]['hourly']
high_before = w_wc[-1]['hourly']
result_wc = apply_wage_competition(config_wc, rng, w_wc, [], [], {}, 1, {})
check('Bottom wage increased', w_wc[0]['hourly'] > low_before)
check('Compression applied', result_wc.get('wage_compression', 0) > 0)

config_nowc = {'wage_competition': False}
check('Disabled returns empty', apply_wage_competition(config_nowc, rng, [], [], [], {}, 1, {}) == {})

# ─── 9. Capital Ownership ──────────────────────────────────────────

print('\n=== 9. Capital Ownership ===')
config_co = {'capital_ownership_share': 0.5, 'capital_ownership_concentration': 0.0}
w_co = make_workers()
b_co = make_businesses()
bal_co = {w['id']: 50000 for w in w_co}
bal_co['sys'] = 500000000
result_co = apply_capital_ownership(config_co, rng, w_co, [], b_co, bal_co, 1, {})
check('Capital income distributed', result_co.get('capital_income_distributed', 0) > 0)
check('All workers received income', all(bal_co[w['id']] > 50000 for w in w_co))

config_noco = {'capital_ownership_share': 0.0}
check('Zero share returns empty', apply_capital_ownership(config_noco, rng, [], [], [], {}, 1, {}) == {})

# ─── 10. Overlapping Generations ───────────────────────────────────

print('\n=== 10. Overlapping Generations ===')
config_olg = {'use_olg': True, 'olg_retirement_periods': 10, 'olg_entry_cash': 20000}
w_olg = make_workers(10)
bal_olg = {w['id']: 50000 for w in w_olg}
bal_olg['sys'] = 500000000
result_olg = apply_olg(config_olg, rng, w_olg, [], [], bal_olg, 10, {})  # step 10 = period boundary
check('OLG triggered at period boundary', result_olg.get('olg_retired', 0) > 0)
check('New workers entered', result_olg.get('olg_entered', 0) > 0)

config_no_olg = {'use_olg': False}
check('Disabled returns empty', apply_olg(config_no_olg, rng, [], [], [], {}, 1, {}) == {})

# ─── Summary ────────────────────────────────────────────────────────

total = PASS + FAIL
print(f'\n{"="*50}')
print(f'RESULTS: {PASS} passed, {FAIL} failed out of {total}')
if FAIL == 0:
    print('ALL TESTS PASSED ✅')
else:
    print(f'SOME TESTS FAILED ❌')
    sys.exit(1)
