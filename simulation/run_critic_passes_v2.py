#!/usr/bin/env python3
"""Critic Pass V2 — comprehensive test of all new mechanisms, models, and backtests.

Critic Pass 1: UK backtest WITH housing wealth + financial services premium
Critic Pass 2: Germany backtest WITH reunification shock + Hartz reforms
Critic Pass 3: Money creation test WITH redesigned banking-channel multiplier
Critic Pass 4: Japan, Brazil, France backtests
Critic Pass 5: Leave-one-out decomposition of 5 inequality mechanisms
Critic Pass 6: Cross-system comparison with all mechanisms ON
"""
import sys, os, json, copy, math
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))

from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS
from comparison_models import COUNTRY_DATA

OUTPUT = {}
RESULTS_DIR = os.path.join(os.path.dirname(__file__), 'output')

def compute_gini(values):
    if not values or len(values) < 2:
        return 0.0
    values = sorted(values)
    n = len(values)
    cum = np.cumsum(values)
    return float((2 * np.sum(cum) - cum[-1]) / (cum[-1] * n) - (n + 1) / n)
def classify_trend(values):
    """Classify a list of values as RISING, FALLING, or STABLE.
    Threshold 0.02 Gini points — filters noise floor (~0.01-0.02 from seed variance)."""
    if not values or len(values) < 2:
        return "STABLE"
    delta = values[-1] - values[0]
    if abs(delta) <= 0.02:
        return "STABLE"
    return "RISING" if delta > 0 else "FALLING"

def run_periods(periods, label, seed=42, extra_cfg=None):
    """Run chained simulation across periods, return Gini trajectory."""
    results = []
    w, r, b = gen_population(seed)
    for i, (period_name, params) in enumerate(periods):
        cfg = {'system_name': f'{label}_{period_name}', 'tax_type': 'income',
               'income_tax_rate': params.get('income_tax_rate', 0.2),
               'corp_tax_rate': params.get('corp_tax_rate', 0.21),
               'welfare_rate': params.get('welfare_rate', 0.1),
               'healthcare_gdp_share': params.get('healthcare_gdp_share', 0.05),
               'education_gdp_share': params.get('education_gdp_share', 0.04),
               'carbon_tax_rate': params.get('carbon_tax_rate', 0.0),
               'union_premium': params.get('union_premium', 1.0),
               'cpf_rate': params.get('cpf_rate', 0),
               'use_adversarial': False, 'use_events': False,
               'use_harberger': False, 'inheritance_rate': 0,
               'money_creation_rate': params.get('money_creation_rate', 0.0),
               # Inequality toggles
               'skill_premium_growth': params.get('skill_premium_growth', 0.0),
               'union_coverage': params.get('union_coverage', 0.0),
               'capital_income_share': params.get('capital_income_share', 0.0),
               'import_competition': params.get('import_competition', 0.0),
               'use_progressive_tax': params.get('use_progressive_tax', False),
               # UK-specific
               'housing_wealth_concentration': params.get('housing_wealth_concentration', 0.0),
               'financial_services_premium': params.get('financial_services_premium', 0.0),
               # Germany-specific
               'reunification_shock': params.get('reunification_shock', 0.0),
               'hartz_reform': params.get('hartz_reform', 0.0),
               'banking_multiplier': params.get('banking_multiplier', 0),
               'elite_capture_intensity': params.get('elite_capture_intensity', 0.0),
               }
        if extra_cfg:
            cfg.update(extra_cfg)
        steps = 120
        r_out = run_phase8(w, r, b, seed + i, cfg)
        results.append({'period': period_name, 'gini': r_out['gini'],
                        'wealth': r_out['wealth'], 'w_mean': r_out['w_mean'],
                        'crra': r_out.get('crra_welfare', 0)})
        print(f'  {label} {period_name}: Gini={r_out["gini"]:.4f} Mean=${r_out["w_mean"]:>8,.0f}')
    return results

# ═══════════════════════════════════════════════════════════════════════════
print('=' * 80)
print('  CRITIC PASS 1: UK BACKTEST — WITH HOUSING WEALTH + FINANCIAL SERVICES')
print('=' * 80)

# UK historical data
UK_GINI_ACTUAL = [0.28, 0.33, 0.44, 0.42]

UK_PERIODS_HW = [
    ('1960s', {'income_tax_rate': 0.25, 'corp_tax_rate': 0.50, 'welfare_rate': 0.04,
               'healthcare_gdp_share': 0.04, 'union_premium': 1.15,
               'housing_wealth_concentration': 0.15, 'financial_services_premium': 0.10,
               'skill_premium_growth': 0.008, 'union_coverage': 0.40,
               'capital_income_share': 0.05, 'import_competition': 0.02,
               'use_progressive_tax': True}),
    ('1980s', {'income_tax_rate': 0.30, 'corp_tax_rate': 0.45, 'welfare_rate': 0.08,
               'healthcare_gdp_share': 0.05, 'union_premium': 1.10,
               'housing_wealth_concentration': 0.25, 'financial_services_premium': 0.15,
               'skill_premium_growth': 0.012, 'union_coverage': 0.35,
               'capital_income_share': 0.10, 'import_competition': 0.05,
               'use_progressive_tax': True}),
    ('2000s', {'income_tax_rate': 0.28, 'corp_tax_rate': 0.30, 'welfare_rate': 0.10,
               'healthcare_gdp_share': 0.07, 'union_premium': 1.05,
               'housing_wealth_concentration': 0.35, 'financial_services_premium': 0.20,
               'skill_premium_growth': 0.015, 'union_coverage': 0.28,
               'capital_income_share': 0.15, 'import_competition': 0.10,
               'use_progressive_tax': True}),
    ('2020s', {'income_tax_rate': 0.25, 'corp_tax_rate': 0.19, 'welfare_rate': 0.12,
               'healthcare_gdp_share': 0.10, 'union_premium': 1.02,
               'housing_wealth_concentration': 0.40, 'financial_services_premium': 0.25,
               'skill_premium_growth': 0.018, 'union_coverage': 0.22,
               'capital_income_share': 0.18, 'import_competition': 0.15,
               'use_progressive_tax': True}),
]

print('\n--- UK (WITH housing wealth + financial services premium) ---')
uk_fixed = run_periods(UK_PERIODS_HW, 'UK_FIXED')
uk_trend_sim = classify_trend([p['gini'] for p in uk_fixed])
uk_trend_actual = classify_trend(UK_GINI_ACTUAL)
uk_match = uk_trend_sim == uk_trend_actual

print('\n--- Comparison ---')
header = f'{"System":<12} {"Period":<8} {"Sim Gini":>10} {"Actual":>8} {"Delta":>8}'
print(header)
print('-' * 56)
for j, p in enumerate(uk_fixed):
    print(f'{"UK_FIXED":<12} {p["period"]:<8} {p["gini"]:>10.4f} {UK_GINI_ACTUAL[j]:>8.2f} {p["gini"] - UK_GINI_ACTUAL[j]:>+8.4f}')
print(f'  Trend: sim={uk_trend_sim} actual={uk_trend_actual} {"✅ MATCH" if uk_match else "❌ MISMATCH"}')
OUTPUT['critic1_uk_fixed'] = {
    'periods': [{'period': p['period'], 'gini': p['gini'], 'actual': a} for p, a in zip(uk_fixed, UK_GINI_ACTUAL)],
    'trend_match': uk_match, 'sim_trend': uk_trend_sim, 'actual_trend': uk_trend_actual
}

# ═══════════════════════════════════════════════════════════════════════════
print(f'\n{"=" * 80}')
print('  CRITIC PASS 2: GERMANY BACKTEST — WITH REUNIFICATION SHOCK + HARTZ REFORMS')
print('=' * 80)

DE_GINI_ACTUAL = [0.30, 0.28, 0.35, 0.30]

DE_PERIODS_RE = [
    ('1960s', {'income_tax_rate': 0.35, 'corp_tax_rate': 0.50, 'welfare_rate': 0.06,
               'healthcare_gdp_share': 0.05, 'union_premium': 1.20,
               'skill_premium_growth': 0.005, 'union_coverage': 0.30,
               'capital_income_share': 0.05, 'import_competition': 0.02,
               'housing_wealth_concentration': 0.0, 'financial_services_premium': 0.0,
               'reunification_shock': 0.0, 'hartz_reform': 0.0}),
    ('1980s', {'income_tax_rate': 0.40, 'corp_tax_rate': 0.50, 'welfare_rate': 0.10,
               'healthcare_gdp_share': 0.07, 'union_premium': 1.18,
               'skill_premium_growth': 0.008, 'union_coverage': 0.28,
               'capital_income_share': 0.08, 'import_competition': 0.05,
               'housing_wealth_concentration': 0.0, 'financial_services_premium': 0.0,
               'reunification_shock': 0.0, 'hartz_reform': 0.0}),
    ('2000s', {'income_tax_rate': 0.45, 'corp_tax_rate': 0.38, 'welfare_rate': 0.12,
               'healthcare_gdp_share': 0.08, 'union_premium': 1.15,
               'skill_premium_growth': 0.010, 'union_coverage': 0.25,
               'capital_income_share': 0.10, 'import_competition': 0.08,
               'housing_wealth_concentration': 0.0, 'financial_services_premium': 0.0,
               'reunification_shock': 1.0,  # 1990 equivalent: one-time shock
               'hartz_reform': 0.0}),
    ('2020s', {'income_tax_rate': 0.40, 'corp_tax_rate': 0.15, 'welfare_rate': 0.13,
               'healthcare_gdp_share': 0.10, 'union_premium': 1.10,
               'skill_premium_growth': 0.012, 'union_coverage': 0.22,
               'capital_income_share': 0.12, 'import_competition': 0.12,
               'housing_wealth_concentration': 0.0, 'financial_services_premium': 0.0,
               'reunification_shock': 0.0, 'hartz_reform': 0.5}),  # 2000s Hartz reform effect
]

print('\n--- Germany (WITH reunification shock + Hartz reforms) ---')
de_fixed = run_periods(DE_PERIODS_RE, 'DE_FIXED')
de_trend_sim = classify_trend([p['gini'] for p in de_fixed])
de_trend_actual = classify_trend(DE_GINI_ACTUAL)
de_match = de_trend_sim == de_trend_actual

print('\n--- Comparison ---')
print(header)
print('-' * 56)
for j, p in enumerate(de_fixed):
    print(f'{"DE_FIXED":<12} {p["period"]:<8} {p["gini"]:>10.4f} {DE_GINI_ACTUAL[j]:>8.2f} {p["gini"] - DE_GINI_ACTUAL[j]:>+8.4f}')
print(f'  Trend: sim={de_trend_sim} actual={de_trend_actual} {"✅ MATCH" if de_match else "❌ MISMATCH"}')
OUTPUT['critic2_de_fixed'] = {
    'periods': [{'period': p['period'], 'gini': p['gini'], 'actual': a} for p, a in zip(de_fixed, DE_GINI_ACTUAL)],
    'trend_match': de_match, 'sim_trend': de_trend_sim, 'actual_trend': de_trend_actual
}

# ═══════════════════════════════════════════════════════════════════════════
print(f'\n{"=" * 80}')
print('  CRITIC PASS 3: MONEY CREATION — REDESIGNED BANKING-CHANNEL MULTIPLIER')
print('=' * 80)

pop = gen_population(42)
cfg_base = {
    'system_name': 'MC_test', 'tax_type': 'income',
    'income_tax_rate': 0.22, 'corp_tax_rate': 0.21, 'welfare_rate': 0.14,
    'healthcare_gdp_share': 0.18, 'education_gdp_share': 0.05,
    'use_progressive_tax': True,
    'money_creation_rate': 0.0, 'banking_multiplier': 0,
}
# Money creation only (no bank multiplier)
cfg_money_only = dict(cfg_base, money_creation_rate=0.02, banking_multiplier=0)
# Money creation + bank multiplier (redesigned channel)
cfg_money_bank = dict(cfg_base, money_creation_rate=0.02, banking_multiplier=2.0)
# Money creation + high bank multiplier
cfg_money_high = dict(cfg_base, money_creation_rate=0.05, banking_multiplier=5.0)

r_closed = run_phase8(*pop[:3], 42, cfg_base)
r_money_only = run_phase8(*pop[:3], 42, cfg_money_only)
r_money_bank = run_phase8(*pop[:3], 42, cfg_money_bank)
r_money_high = run_phase8(*pop[:3], 42, cfg_money_high)

print(f'\n  Closed system:              Wealth=${r_closed["wealth"]:>12,.0f} Gini={r_closed["gini"]:.4f}')
print(f'  Money 2% (no bank):         Wealth=${r_money_only["wealth"]:>12,.0f} Gini={r_money_only["gini"]:.4f}')
print(f'  Money 2% + bank 2x:         Wealth=${r_money_bank["wealth"]:>12,.0f} Gini={r_money_bank["gini"]:.4f}')
print(f'  Money 5% + bank 5x:         Wealth=${r_money_high["wealth"]:>12,.0f} Gini={r_money_high["gini"]:.4f}')
print(f'  Δ money-only:  +${r_money_only["wealth"] - r_closed["wealth"]:>10,.0f} ({((r_money_only["wealth"]/r_closed["wealth"] - 1)*100):.2f}%)')
print(f'  Δ money+bank:  +${r_money_bank["wealth"] - r_closed["wealth"]:>10,.0f} ({((r_money_bank["wealth"]/r_closed["wealth"] - 1)*100):.2f}%)')
print(f'  Δ money+high:  +${r_money_high["wealth"] - r_closed["wealth"]:>10,.0f} ({((r_money_high["wealth"]/r_closed["wealth"] - 1)*100):.2f}%)')

OUTPUT['critic3_money_creation'] = {
    'closed': {'wealth': r_closed['wealth'], 'gini': r_closed['gini']},
    'money_only': {'wealth': r_money_only['wealth'], 'gini': r_money_only['gini']},
    'money_bank': {'wealth': r_money_bank['wealth'], 'gini': r_money_bank['gini']},
    'money_high': {'wealth': r_money_high['wealth'], 'gini': r_money_high['gini']},
    'delta_pct_bank': (r_money_bank['wealth'] / r_closed['wealth'] - 1) * 100,
    'delta_pct_high': (r_money_high['wealth'] / r_closed['wealth'] - 1) * 100,
}

# ═══════════════════════════════════════════════════════════════════════════
print(f'\n{"=" * 80}')
print('  CRITIC PASS 4: JAPAN, BRAZIL, FRANCE BACKTESTS')
print('=' * 80)

for country in ['Japan', 'Brazil', 'France']:
    cd = COUNTRY_DATA[country]
    periods_list = sorted(cd['periods'].keys())
    actual_gini = [cd['periods'][y]['gini_actual'] for y in periods_list]

    period_configs = []
    for y in periods_list:
        p = cd['periods'][y]
        period_configs.append((
            f'{y}s',
            {
                'income_tax_rate': p.get('income_tax', 0.2),
                'corp_tax_rate': p.get('corp_tax', 0.2),
                'welfare_rate': p.get('welfare', 0.1),
                'healthcare_gdp_share': p.get('healthcare', 0.05),
                'education_gdp_share': p.get('education', 0.04),
                'carbon_tax_rate': p.get('carbon_tax', 0.0),
                'union_premium': p.get('union_premium', 1.0),
                'cpf_rate': p.get('cpf', 0.0),
                'elite_capture_intensity': p.get('elite_capture', 0.0),
                'skill_premium_growth': p.get('skill_premium_growth', 0.0),
                'union_coverage': p.get('union_coverage', 0.0),
                'capital_income_share': p.get('capital_income_share', 0.0),
                'import_competition': p.get('import_competition', 0.0),
                'use_progressive_tax': p.get('use_progressive_tax', False),
            }
        ))

    print(f'\n--- {country} ---')
    results = run_periods(period_configs, country)
    sim_trend = classify_trend([p['gini'] for p in results])
    actual_trend = classify_trend(actual_gini)
    match = sim_trend == actual_trend

    print('')
    print(header)
    print('-' * 56)
    for j, p in enumerate(results):
        print(f'{country:<12} {p["period"]:<8} {p["gini"]:>10.4f} {actual_gini[j]:>8.2f} {p["gini"] - actual_gini[j]:>+8.4f}')
    print(f'  Trend: sim={sim_trend} actual={actual_trend} {"✅ MATCH" if match else "❌ MISMATCH"}')

    OUTPUT[f'critic4_{country.lower()}'] = {
        'periods': [{'period': p['period'], 'gini': p['gini'], 'actual': a} for p, a in zip(results, actual_gini)],
        'trend_match': match, 'sim_trend': sim_trend, 'actual_trend': actual_trend,
        'mean_delta': np.mean([p['gini'] - a for p, a in zip(results, actual_gini)]),
    }

# ═══════════════════════════════════════════════════════════════════════════
print(f'\n{"=" * 80}')
print('  CRITIC PASS 5: LEAVE-ONE-OUT DECOMPOSITION — US BACKTEST')
print('=' * 80)

US_GINI_ACTUAL = [0.35, 0.38, 0.46, 0.48]

US_PERIODS = [
    ('1960s', {'income_tax_rate': 0.25, 'corp_tax_rate': 0.52, 'welfare_rate': 0.03,
               'healthcare_gdp_share': 0.05}),
    ('1980s', {'income_tax_rate': 0.28, 'corp_tax_rate': 0.46, 'welfare_rate': 0.08,
               'healthcare_gdp_share': 0.08}),
    ('2000s', {'income_tax_rate': 0.25, 'corp_tax_rate': 0.35, 'welfare_rate': 0.10,
               'healthcare_gdp_share': 0.13}),
    ('2020s', {'income_tax_rate': 0.22, 'corp_tax_rate': 0.21, 'welfare_rate': 0.14,
               'healthcare_gdp_share': 0.18}),
]

ALL_MECHANISMS_ON = {
    'skill_premium_growth': 0.015, 'union_coverage': 0.12,
    'capital_income_share': 0.15, 'import_competition': 0.20,
    'use_progressive_tax': True,
}

MECHANISM_NAMES = {
    'skill_premium_growth': 'A: SBTC',
    'union_coverage': 'B: Union Decline',
    'capital_income_share': 'C: Financialization',
    'import_competition': 'D: Import Competition',
    'use_progressive_tax': 'E: Progressive Tax',
}

# Base: ALL mechanisms ON
us_base_cfg = {k: v for k, v in ALL_MECHANISMS_ON.items()}
# Fix periods to support extra_cfg mechanism keys
print('\n  Running US backtest with ALL mechanisms ON...')
us_all_on = run_periods([(p, {'income_tax_rate': up['income_tax_rate'],
                               'corp_tax_rate': up['corp_tax_rate'],
                               'welfare_rate': up['welfare_rate'],
                               'healthcare_gdp_share': up['healthcare_gdp_share']})
                         for p, up in US_PERIODS], 'US_ALL_ON', extra_cfg=us_base_cfg)

all_on_gini = us_all_on[-1]['gini']
base_gini_rise = all_on_gini - us_all_on[0]['gini']
print(f'  ALL ON — Final Gini: {all_on_gini:.4f}, Rise: {base_gini_rise:.4f}')

leave_one_out = {}
for mech_key, mech_name in MECHANISM_NAMES.items():
    loo_cfg = {k: v for k, v in ALL_MECHANISMS_ON.items() if k != mech_key}
    print(f'\n  Running WITHOUT {mech_name}...')
    loo_result = run_periods([(p, {'income_tax_rate': up['income_tax_rate'],
                                    'corp_tax_rate': up['corp_tax_rate'],
                                    'welfare_rate': up['welfare_rate'],
                                    'healthcare_gdp_share': up['healthcare_gdp_share']})
                              for p, up in US_PERIODS], f'US_NO_{mech_key}', extra_cfg=loo_cfg)
    loo_gini = loo_result[-1]['gini']
    loo_rise = loo_gini - loo_result[0]['gini']
    contribution = base_gini_rise - loo_rise
    leave_one_out[mech_key] = {
        'name': mech_name,
        'final_gini': loo_gini,
        'gini_rise': loo_rise,
        'contribution': contribution,
        'contribution_pct': (contribution / max(base_gini_rise, 1e-6)) * 100 if base_gini_rise > 1e-6 else 0,
    }

print(f'\n{"=" * 60}')
print('  LEAVE-ONE-OUT DECOMPOSITION RESULTS')
print(f'{"=" * 60}')
print(f'{"Mechanism":<30} {"Final Gini":>10} {"Gini Rise":>10} {"Contrib":>10} {"% of Total":>10}')
print('-' * 70)
for mech_key in sorted(leave_one_out, key=lambda k: leave_one_out[k]['contribution'], reverse=True):
    loo = leave_one_out[mech_key]
    print(f'{loo["name"]:<30} {loo["final_gini"]:>10.4f} {loo["gini_rise"]:>10.4f} '
          f'{loo["contribution"]:>+10.4f} {loo["contribution_pct"]:>9.1f}%')
print(f'{"ALL ON":<30} {all_on_gini:>10.4f} {base_gini_rise:>10.4f} {"—":>10} {"100.0%":>10}')

OUTPUT['critic5_leave_one_out'] = {
    'all_on_final_gini': all_on_gini,
    'all_on_gini_rise': base_gini_rise,
    'decomposition': leave_one_out,
}

# ═══════════════════════════════════════════════════════════════════════════
print(f'\n{"=" * 80}')
print('  CRITIC PASS 6: CROSS-SYSTEM COMPARISON — ALL MECHANISMS ON')
print('=' * 80)

# Run all main systems with inequality mechanisms ON
system_names = ['LS_Full', 'US_Style', 'Nordic', 'Singapore', 'Pure_Georgist',
                'Mutualist_LS', 'Laissez_Faire', 'Worker_Coop', 'UBI_VAT', 'Dual_Compact_LS']

cross_results = {}
for name in system_names:
    cfg = dict(PHASE8_CONFIGS[name])
    # Add realistic inequality mechanisms (country-appropriate levels)
    # All systems: inherit=0 for fair comparison (no equalization artifact)
    cfg['inheritance_rate'] = 0.0
    if name == 'US_Style':
        cfg.update(ALL_MECHANISMS_ON)
        cfg['elite_capture_intensity'] = 0.15
    elif name == 'Nordic':
        cfg.update({'skill_premium_growth': 0.008, 'union_coverage': 0.6,
                     'capital_income_share': 0.05, 'import_competition': 0.08,
                     'use_progressive_tax': True, 'elite_capture_intensity': 0.05})
    elif name == 'Laissez_Faire':
        cfg.update({'skill_premium_growth': 0.020, 'union_coverage': 0.02,
                     'capital_income_share': 0.30, 'import_competition': 0.30,
                     'use_progressive_tax': False, 'elite_capture_intensity': 0.30,
                     'inheritance_rate': 0.0})  # True laissez-faire: no estate redistribution
    else:
        # LVT-based systems (LS, Georgist, etc.) — mild inequality
        cfg.update({'skill_premium_growth': 0.010, 'union_coverage': 0.1,
                     'capital_income_share': 0.05, 'import_competition': 0.05,
                     'use_progressive_tax': False, 'elite_capture_intensity': 0.02})

    w, r, b = gen_population(42)
    result = run_phase8(w, r, b, 42, cfg)
    cross_results[name] = {
        'mean_wealth': result['w_mean'], 'gini': result['gini'],
        'crra': result.get('crra_welfare', 0), 'wealth': result['wealth'],
    }

print(f'\n{"=" * 90}')
print(f'{"System":<22} {"Mean$":>10} {"Gini":>8} {"Wealth":>12} {"CRRA":>10}')
print('-' * 65)
for name in system_names:
    r = cross_results[name]
    print(f'{name:<22} ${r["mean_wealth"]:>7,.0f} {r["gini"]:>8.4f} ${r["wealth"]:>10,.0f} {r["crra"]:>10.2f}')

# Add country backtest Gini for US, UK, Germany, Japan, Brazil, France
print(f'\n{"=" * 90}')
print('  FINAL SUMMARY — ALL BACKTEST RESULTS')
print('=' * 90)
countries_summary = [
    ('US (all mech ON)', us_all_on[-1]['gini'], US_GINI_ACTUAL[-1], '✅ MATCH' if classify_trend([p['gini'] for p in us_all_on]) == classify_trend(US_GINI_ACTUAL) else '❌ FAIL'),
    ('UK (fixed HW+FS)', uk_fixed[-1]['gini'], UK_GINI_ACTUAL[-1], '✅ MATCH' if uk_match else '❌ FAIL'),
    ('Germany (fixed)', de_fixed[-1]['gini'], DE_GINI_ACTUAL[-1], '✅ MATCH' if de_match else '❌ FAIL'),
]
for country in ['Japan', 'Brazil', 'France']:
    cd = COUNTRY_DATA[country]
    r = OUTPUT.get(f'critic4_{country.lower()}', {})
    periods_r = r.get('periods', [])
    last_gini = periods_r[-1]['gini'] if periods_r else 0
    last_actual = cd['periods'][2020]['gini_actual'] if 2020 in cd['periods'] else 0
    trend_match = r.get('trend_match', False)
    countries_summary.append((country, last_gini, last_actual, '✅ MATCH' if trend_match else '❌ FAIL'))

print(f'{"System":<30} {"Sim Gini 2020":>14} {"Actual":>8} {"Status":>12}')
print('-' * 66)
for name, sim_g, act_g, status in countries_summary:
    print(f'{name:<30} {sim_g:>14.4f} {act_g:>8.2f} {status:>12}')

OUTPUT['critic6_cross_system'] = cross_results
OUTPUT['summary'] = [
    {'system': name, 'sim_gini_2020': sim_g, 'actual': act_g, 'status': status}
    for name, sim_g, act_g, status in countries_summary
]

# Save all results
os.makedirs(RESULTS_DIR, exist_ok=True)
output_path = os.path.join(RESULTS_DIR, 'critic_passes_v2.json')
json.dump(OUTPUT, open(output_path, 'w'), indent=2)
print(f'\n\nSaved: {output_path}')
print('CRITIC PASSES V2 COMPLETE')
