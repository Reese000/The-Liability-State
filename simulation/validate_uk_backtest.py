#!/usr/bin/env python3
"""validate_uk_backtest.py — UK historical backtest.

2 periods: 1960 (post-war, union strong, low finance) and
2020 (deindustrialized, financialized, high inequality).

Key mechanisms: housing_wealth_concentration, financial_services_premium,
education_variance (PISA ~500), union_decline, capital_income_share.
"""
import sys, os, json, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

PERIODS = {
    1960: {
        'system_name': 'UK_1960', 'tax_type': 'income',
        'income_tax_rate': 0.25, 'corp_tax_rate': 0.50, 'welfare_rate': 0.04,
        'healthcare_gdp_share': 0.04,
        'skill_premium_growth': 0.008, 'union_coverage': 0.40,
        'capital_income_share': 0.05, 'import_competition': 0.02,
        'use_progressive_tax': True, 'housing_wealth_concentration': 0.15,
        'financial_services_premium': 0.10, 'education_variance': 0.5,
        'wage_dispersion_mult': 1.0, 'inheritance_rate': 0.0, 'gini_actual': 0.28,
    },
    2020: {
        'system_name': 'UK_2020', 'tax_type': 'income',
        'income_tax_rate': 0.25, 'corp_tax_rate': 0.19, 'welfare_rate': 0.12,
        'healthcare_gdp_share': 0.10,
        'skill_premium_growth': 0.018, 'union_coverage': 0.22,
        'capital_income_share': 0.18, 'import_competition': 0.15,
        'use_progressive_tax': True, 'housing_wealth_concentration': 0.40,
        'financial_services_premium': 0.25, 'education_variance': 0.5,
        'wage_dispersion_mult': 2.0, 'inheritance_rate': 0.0, 'gini_actual': 0.42,
    },
}

YEARS = [1960, 2020]

def classify_trend(delta):
    if abs(delta) <= 0.02: return 'STABLE'
    return 'RISING' if delta > 0 else 'FALLING'

def validate_uk():
    print("="*70)
    print("UK HISTORICAL BACKTEST — 2-Period Validation")
    print("="*70)
    for year in YEARS:
        for key in ['wage_dispersion_mult','inheritance_rate','gini_actual']:
            if key not in PERIODS[year]: raise ValueError(f"{year}: missing '{key}'")
    results = {}; prev_gini = None
    print(f"{'Period':<10} {'Sim Gini':>10} {'Actual':>8} {'Err%':>6} {'Trend':>10}")
    print("-"*46)
    for year in YEARS:
        cfg = PERIODS[year]; actual = cfg['gini_actual']
        w,r,b = gen_population(42); res = run_phase8(w,r,b,42,cfg)
        if 'error' in res: raise RuntimeError(f"{year}: {res['error']}")
        gini = res['gini']; err_pct = abs(gini-actual)/max(actual,0.01)*100
        if prev_gini is not None: delta = gini-prev_gini; trend = classify_trend(delta)
        else: delta=0.0; trend=''
        results[year] = {'gini':round(gini,4),'actual':actual,'err_pct':round(err_pct,2),
            'delta':round(delta,4) if prev_gini is not None else None,'trend':trend or 'START'}
        print(f"{year}s".ljust(10)+f" {gini:>8.4f} {actual:>8.2f} {err_pct:>5.1f}% {trend:>10}")
        assert err_pct < 10.0, f"UK {year}s: level error {err_pct:.1f}% > 10%"
        prev_gini = gini
    delta = results[2020]['gini']-results[1960]['gini']
    trend = classify_trend(delta)
    print(f"\nOverall 1960->2020 delta: {delta:.4f} trend={trend} (expected RISING)")
    assert trend == 'RISING', f"UK trend: {trend}, expected RISING"
    print(f"\nUK BACKTEST: PASS — {trend} trend, all levels < 10% err")
    return 0, results

def main():
    try:
        ec, results = validate_uk()
        os.makedirs("output", exist_ok=True)
        json.dump(results, open("output/uk_backtest_results.json","w"), indent=2)
        sys.exit(ec)
    except AssertionError as e: print(f"FAIL: {e}"); sys.exit(1)
    except (ValueError,RuntimeError) as e: print(f"ERROR: {e}",file=sys.stderr); sys.exit(1)
    except Exception as e: print(f"FATAL: {e}",file=sys.stderr); traceback.print_exc(file=sys.stderr); sys.exit(2)

if __name__ == '__main__':
    main()
