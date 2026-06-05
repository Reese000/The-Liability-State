"""New critic passes: UK/Germany backtests, US+Nordic counterfactual, money creation test."""
import sys, os, json, copy, math
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))

from comparison_phase8 import run_phase8, gen_population, compute_crra_utility

RESULTS = {}
print('='*80)
print('  CRITIC PASS 1: UK + GERMANY BACKTEST')
print('='*80)

# UK historical data (Gini)
# UK Gini: 1960=0.28, 1980=0.33, 2000=0.44, 2020=0.42
UK_PERIODS = [
    ('1960s', {'income_tax_rate':0.25, 'corp_tax_rate':0.50, 'welfare_rate':0.04, 'healthcare_gdp_share':0.04, 'union_premium':1.15}),
    ('1980s', {'income_tax_rate':0.30, 'corp_tax_rate':0.45, 'welfare_rate':0.08, 'healthcare_gdp_share':0.05, 'union_premium':1.10}),
    ('2000s', {'income_tax_rate':0.28, 'corp_tax_rate':0.30, 'welfare_rate':0.10, 'healthcare_gdp_share':0.07, 'union_premium':1.05}),
    ('2020s', {'income_tax_rate':0.25, 'corp_tax_rate':0.19, 'welfare_rate':0.12, 'healthcare_gdp_share':0.10, 'union_premium':1.02}),
]
UK_GINI_ACTUAL = [0.28, 0.33, 0.44, 0.42]

# Germany historical data
# Germany Gini: 1960=0.30, 1980=0.28, 2000=0.35, 2020=0.30
DE_PERIODS = [
    ('1960s', {'income_tax_rate':0.35, 'corp_tax_rate':0.50, 'welfare_rate':0.06, 'healthcare_gdp_share':0.05, 'union_premium':1.20}),
    ('1980s', {'income_tax_rate':0.40, 'corp_tax_rate':0.50, 'welfare_rate':0.10, 'healthcare_gdp_share':0.07, 'union_premium':1.18}),
    ('2000s', {'income_tax_rate':0.45, 'corp_tax_rate':0.38, 'welfare_rate':0.12, 'healthcare_gdp_share':0.08, 'union_premium':1.15}),
    ('2020s', {'income_tax_rate':0.40, 'corp_tax_rate':0.15, 'welfare_rate':0.13, 'healthcare_gdp_share':0.10, 'union_premium':1.10}),
]
DE_GINI_ACTUAL = [0.30, 0.28, 0.35, 0.30]

# US data for comparison
US_GINI_ACTUAL = [0.35, 0.38, 0.46, 0.48]

def run_periods(periods, label, seed=42):
    """Run chained simulation across periods, return Gini trajectory."""
    results = []
    w,r,b = gen_population(seed)
    for i, (period_name, params) in enumerate(periods):
        cfg = {'system_name':f'{label}_{period_name}', 'tax_type':'income',
               'income_tax_rate':params['income_tax_rate'],
               'corp_tax_rate':params['corp_tax_rate'],
               'welfare_rate':params['welfare_rate'],
               'healthcare_gdp_share':params['healthcare_gdp_share'],
               'education_gdp_share':0.04, 'carbon_tax_rate':0.0,
               'union_premium':params.get('union_premium', 1.0),
               'cpf_rate':0, 'use_adversarial':False, 'use_events':False,
               'use_harberger':False, 'inheritance_rate':0,
               'money_creation_rate':0.0,
               'skill_premium_growth':0.015, 'union_coverage':0.35 - i*0.08,
               'capital_income_share':0.15, 'import_competition':0.20 - i*0.05,
               'use_progressive_tax':True}
        steps = 120
        r_out = run_phase8(w, r, b, seed+i, cfg)
        # State chaining: final state becomes initial state
        results.append({'period': period_name, 'gini': r_out['gini'],
                        'wealth': r_out['wealth'], 'w_mean': r_out['w_mean']})
        print(f'  {label} {period_name}: Gini={r_out["gini"]:.4f} Mean=${r_out["w_mean"]:>8,.0f}')
    return results

print('\n--- UK ---')
uk = run_periods(UK_PERIODS, 'UK')
print('\n--- Germany ---')
de = run_periods(DE_PERIODS, 'DE')

print('\n--- Comparison ---')
header = f'{"System":<10} {"Period":<8} {"Sim Gini":>10} {"Actual":>8} {"Delta":>8}'
print(header)
print('-'*50)
for i, label in enumerate(['UK', 'Germany']):
    data = uk if label == 'UK' else de
    actual = UK_GINI_ACTUAL if label == 'UK' else DE_GINI_ACTUAL
    sim_trend = 'RISING' if data[-1]['gini'] > data[0]['gini'] + 0.01 else ('FALLING' if data[-1]['gini'] < data[0]['gini'] - 0.01 else 'STABLE')
    actual_trend = 'RISING' if actual[-1] > actual[0] + 0.01 else ('FALLING' if actual[-1] < actual[0] - 0.01 else 'STABLE')
    match = sim_trend == actual_trend
    for j, p in enumerate(data):
        print(f'{label:<10} {p["period"]:<8} {p["gini"]:>10.4f} {actual[j]:>8.2f} {p["gini"]-actual[j]:>+8.4f}')
    print(f'  Trend: sim={sim_trend} actual={actual_trend} {"✅ MATCH" if match else "❌ MISMATCH"}')

print('\n' + '='*80)
print('  CRITIC PASS 2: COUNTERFACTUAL — US with Nordic Tax Parameters')
print('='*80)

US_NORDIC_PERIODS = [
    ('1960s', {'income_tax_rate':0.30, 'corp_tax_rate':0.50, 'welfare_rate':0.05, 'healthcare_gdp_share':0.05, 'union_premium':1.10}),
    ('1980s', {'income_tax_rate':0.48, 'corp_tax_rate':0.52, 'welfare_rate':0.15, 'healthcare_gdp_share':0.08, 'union_premium':1.15}),
    ('2000s', {'income_tax_rate':0.52, 'corp_tax_rate':0.28, 'welfare_rate':0.18, 'healthcare_gdp_share':0.13, 'union_premium':1.15}),
    ('2020s', {'income_tax_rate':0.43, 'corp_tax_rate':0.21, 'welfare_rate':0.16, 'healthcare_gdp_share':0.18, 'union_premium':1.10}),
]

print('--- US with Nordic tax/welfare rates but US healthcare/carbon ---')
us_nordic = run_periods(US_NORDIC_PERIODS, 'US+Nordic')
nordic_actual = [0.28, 0.25, 0.27, 0.28]
print(f'\n  Counterfactual Gini: {us_nordic[0]["gini"]:.4f} → {us_nordic[-1]["gini"]:.4f}')
print(f'  Actual US Gini:      0.35 → 0.48')
print(f'  Actual Nordic Gini:  0.28 → 0.28')
print(f'  If US had Nordic taxes, Gini would be: {us_nordic[-1]["gini"]:.4f} vs actual US {US_GINI_ACTUAL[-1]:.2f}')
print(f'  Δ from actual: {us_nordic[-1]["gini"] - US_GINI_ACTUAL[-1]:+.4f}')

print('\n' + '='*80)
print('  CRITIC PASS 3: MONEY CREATION EFFECT')
print('='*80)

# Compare closed vs open system for US_Style
pop = gen_population(42)
cfg_base = {'system_name':'MC_test', 'tax_type':'income', 'income_tax_rate':0.22,
            'corp_tax_rate':0.21, 'welfare_rate':0.14, 'healthcare_gdp_share':0.18,
            'education_gdp_share':0.05, 'use_progressive_tax':True,
            'money_creation_rate':0.0}
cfg_open = dict(cfg_base, money_creation_rate=0.02)  # 2% money growth

r_closed = run_phase8(*pop[:3], 42, cfg_base)
r_open = run_phase8(*gen_population(42), 42, cfg_open)

print(f'\n  Closed system: Wealth=${r_closed["wealth"]:>12,.0f} Gini={r_closed["gini"]:.4f}')
print(f'  Open system:   Wealth=${r_open["wealth"]:>12,.0f} Gini={r_open["gini"]:.4f}')
print(f'  Money creation adds: ${r_open["wealth"] - r_closed["wealth"]:>12,.0f} to total wealth')
print(f'  Gini change: {r_open["gini"] - r_closed["gini"]:+.4f}')

print('\n' + '='*80)
print('  SUMMARY — NEW CRITIC FINDINGS')
print('='*80)

# Save all results
output = {
    'uk_backtest': [{'period':p['period'], 'gini':p['gini'], 'actual':a} for p,a in zip(uk, UK_GINI_ACTUAL)],
    'germany_backtest': [{'period':p['period'], 'gini':p['gini'], 'actual':a} for p,a in zip(de, DE_GINI_ACTUAL)],
    'us_nordic_counterfactual': [{'period':p['period'], 'gini':p['gini']} for p in us_nordic],
    'money_creation_test': {'closed_wealth':r_closed['wealth'], 'closed_gini':r_closed['gini'],
                            'open_wealth':r_open['wealth'], 'open_gini':r_open['gini']},
}
os.makedirs('output', exist_ok=True)
json.dump(output, open('output/critic_passes.json','w'), indent=2)
print('\nSaved: output/critic_passes.json')
