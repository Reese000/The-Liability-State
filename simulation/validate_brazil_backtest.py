#!/usr/bin/env python3
"""validate_brazil_backtest.py — Brazil historical backtest.

3 periods: 1960 (military regime, high land inequality),
1990 (redemocratization, hyperinflation), 2020 (Bolsa Familia, falling inequality).

Key mechanisms: patrimonial_wealth (land oligarchy), informal_share,
progressive tax, elite_capture_intensity.
"""
import sys, os, json, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

PERIODS = {
    1960: {
        'system_name': 'BR_1960', 'tax_type': 'income',
        'income_tax_rate': 0.15, 'corp_tax_rate': 0.30, 'welfare_rate': 0.05,
        'healthcare_gdp_share': 0.03,
        'skill_premium_growth': 0.001, 'union_coverage': 0.25,
        'capital_income_share': 0.15, 'import_competition': 0.02,
        'elite_capture_intensity': 0.30, 'patrimonial_wealth': 0.40,
        'informal_share': 0.45, 'wage_dispersion_mult': 2.0,
        'inheritance_rate': 0.0, 'gini_actual': 0.57,
    },
    1990: {
        'system_name': 'BR_1990', 'tax_type': 'income',
        'income_tax_rate': 0.20, 'corp_tax_rate': 0.40, 'welfare_rate': 0.10,
        'healthcare_gdp_share': 0.04,
        'skill_premium_growth': 0.005, 'union_coverage': 0.22,
        'capital_income_share': 0.18, 'import_competition': 0.08,
        'elite_capture_intensity': 0.25, 'patrimonial_wealth': 0.30,
        'informal_share': 0.42, 'wage_dispersion_mult': 3.0,
        'inheritance_rate': 0.0, 'gini_actual': 0.60,
    },
    2020: {
        'system_name': 'BR_2020', 'tax_type': 'income',
        'income_tax_rate': 0.25, 'corp_tax_rate': 0.34, 'welfare_rate': 0.16,
        'healthcare_gdp_share': 0.06,
        'skill_premium_growth': 0.008, 'union_coverage': 0.20,
        'capital_income_share': 0.22, 'import_competition': 0.12,
        'use_progressive_tax': True, 'elite_capture_intensity': 0.20,
        'patrimonial_wealth': 0.2, 'informal_share': 0.38,
        'wage_dispersion_mult': 4.0, 'inheritance_rate': 0.0, 'gini_actual': 0.53,
    },
}

YEARS = [1960, 1990, 2020]

def classify_trend(delta):
    if abs(delta) <= 0.02: return 'STABLE'
    return 'RISING' if delta > 0 else 'FALLING'

def validate_brazil():
    print("="*70)
    print("BRAZIL HISTORICAL BACKTEST — 3-Period Validation")
    print("="*70)
    for year in YEARS:
        cfg = PERIODS[year]
        for key in ['wage_dispersion_mult','inheritance_rate','gini_actual']:
            if key not in cfg: raise ValueError(f"{year}: missing '{key}'")
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
            'delta':round(delta,4) if prev_gini is not None else None,'trend':trend if prev_gini is not None else 'START'}
        print(f"{year}s".ljust(10)+f" {gini:>8.4f} {actual:>8.2f} {err_pct:>5.1f}% {trend:>10}")
        assert err_pct < 10.0, f"BRAZIL {year}s: level error {err_pct:.1f}% > 10%"
        prev_gini = gini
    delta = results[2020]['gini']-results[1960]['gini']
    trend = classify_trend(delta)
    print(f"\nOverall 1960->2020 delta: {delta:.4f} trend={trend} (expected FALLING)")
    assert trend == 'FALLING', f"BRAZIL trend: {trend}, expected FALLING"
    print(f"\nBRAZIL BACKTEST: PASS — {trend} trend, all levels < 10% err")
    return 0, results

def main():
    try:
        ec, results = validate_brazil()
        os.makedirs("output", exist_ok=True)
        json.dump(results, open("output/brazil_backtest_results.json","w"), indent=2)
        sys.exit(ec)
    except AssertionError as e: print(f"FAIL: {e}"); sys.exit(1)
    except (ValueError,RuntimeError) as e: print(f"ERROR: {e}",file=sys.stderr); sys.exit(1)
    except Exception as e: print(f"FATAL: {e}",file=sys.stderr); traceback.print_exc(file=sys.stderr); sys.exit(2)

if __name__ == '__main__':
    main()
