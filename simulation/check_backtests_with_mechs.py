#!/usr/bin/env python3
"""Check if country backtests still pass with missing mechanisms enabled.

Usage:
    python check_backtests_with_mechs.py
"""
import sys, os, importlib.util, copy, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
from comparison_phase8 import run_phase8, gen_population

MECHS = {
    'inflation_rate': 0.02,
    'gov_service_productivity': 0.3,
    'endogenous_tfp': True,
    'wage_competition': True,
    'capital_ownership_share': 0.15,
    'mobility_cost': 0.005,
}
TREND_THRESHOLD = 0.02

def classify(delta):
    if abs(delta) <= TREND_THRESHOLD: return 'STABLE'
    return 'RISING' if delta > 0 else 'FALLING'

def check_trend(results, years, expected):
    if len(years) < 2:
        return True, "N/A", {}
    first = results[years[0]]['gini']
    last = results[years[-1]]['gini']
    delta = last - first
    overall = classify(delta)
    if isinstance(expected, tuple):
        pattern, peak = expected
        pg = results.get(peak, {}).get('gini', first)
        rise_ok = (pg - first) > TREND_THRESHOLD
        fall_ok = (last - pg) < -TREND_THRESHOLD
        ok = rise_ok and fall_ok
        detail = f"rise={pg-first:+.4f} fall={last-pg:+.4f}"
    else:
        ok = overall == expected
        detail = f"delta={delta:+.4f} {overall}"
    return ok, detail, results

def run_country(cname, periods, years, expected):
    results = {}
    w, r, b = gen_population(42)
    for i, yr in enumerate(years):
        p = periods[yr] if isinstance(periods, dict) else periods[i][1]
        cfg = copy.deepcopy(p)
        cfg.update(MECHS)
        res = run_phase8([dict(d) for d in w], [dict(d) for d in r], [dict(d) for d in b], 42+i, cfg)
        results[yr] = {'gini': res['gini'], 'w_mean': res['w_mean']}
    return check_trend(results, years, expected)

# Load all countries
countries = []

# US inline
countries.append(('US', {
    1960: {'system_name':'US_1960','tax_type':'income','income_tax_rate':0.25,'corp_tax_rate':0.50,'welfare_rate':0.04,'use_progressive_tax':True,'skill_premium_growth':0.003,'union_coverage':0.35,'capital_income_share':0.05,'import_competition':0.02,'elite_capture_intensity':0.05,'informal_share':0.05,'wage_dispersion_mult':2.0,'education_variance':0.5,'inheritance_rate':0.0},
    2020: {'system_name':'US_2020','tax_type':'income','income_tax_rate':0.20,'corp_tax_rate':0.21,'welfare_rate':0.15,'use_progressive_tax':True,'skill_premium_growth':0.015,'union_coverage':0.12,'capital_income_share':0.22,'import_competition':0.20,'elite_capture_intensity':0.20,'informal_share':0.08,'wage_dispersion_mult':2.5,'education_variance':0.7,'inheritance_rate':0.0},
}, [1960, 2020], 'RISING'))

# Load from validate scripts
for fname in sorted(os.listdir('.')):
    if fname.startswith('validate_') and fname.endswith('_backtest.py') and fname != 'validate_backtest.py':
        cname = fname.replace('validate_', '').replace('_backtest.py', '')
        spec = importlib.util.spec_from_file_location('vc_' + cname, fname)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, 'PERIODS') and hasattr(mod, 'YEARS'):
            # Determine expected trend from file content
            ftext = open(fname).read()
            if 'RISING' in ftext and 'FALLING' not in ftext.split('RISING')[0]:
                exp = 'RISING'
            elif 'FALLING' in ftext:
                exp = 'FALLING'
            else:
                exp = 'STABLE'
            if cname == 'china': exp = ('RISE_THEN_FALL', 2000)
            countries.append((cname.capitalize(), mod.PERIODS, mod.YEARS, exp))

print(f'Checking {len(countries)} countries with mechanisms ON...\n')
passed = 0
all_results = {}
for cname, periods, years, expected in countries:
    try:
        ok, detail, results = run_country(cname, periods, years, expected)
    except Exception as e:
        ok, detail, results = False, f"ERROR: {e}", {}
    
    if ok: passed += 1
    tag = 'PASS' if ok else 'FAIL'
    print(f'  {cname:<15} {tag} | {detail}')
    for yr in years:
        r = results.get(yr, {})
        g = r.get('gini', 0)
        w = r.get('w_mean', 0)
        print(f'    {yr}: Gini={g:.4f} Mean=${w:>,.0f}')
    all_results[cname] = {str(yr): results.get(yr, {}) for yr in years}

print(f'\nResult: {passed}/{len(countries)} passed')
json.dump(all_results, open('output/backtests_with_mechs.json', 'w'), indent=2)
print('Saved: output/backtests_with_mechs.json')
