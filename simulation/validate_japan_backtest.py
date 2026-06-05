#!/usr/bin/env python3
"""validate_japan_backtest.py — Japan historical backtest with period-varying params.

3 periods: 1960 (high-growth, low inequality), 1985 (bubble, rising),
2020 (lost decades, aging, moderate inequality).

Sources: OECD, WID.world, Ministry of Finance Japan.
"""
import sys, os, json, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

PERIODS = {
    1960: {
        'system_name': 'JP_1960', 'tax_type': 'income',
        'income_tax_rate': 0.15, 'corp_tax_rate': 0.42, 'welfare_rate': 0.04,
        'healthcare_gdp_share': 0.03, 'use_progressive_tax': True,
        'skill_premium_growth': 0.001, 'union_coverage': 0.35,
        'capital_income_share': 0.10, 'import_competition': 0.05,
        'elite_capture_intensity': 0.05, 'informal_share': 0.10,
        'education_variance': 0.3, 'wage_dispersion_mult': 2.0,
        'inheritance_rate': 0.0, 'gini_actual': 0.35,
    },
    1985: {
        'system_name': 'JP_1985', 'tax_type': 'income',
        'income_tax_rate': 0.25, 'corp_tax_rate': 0.50, 'welfare_rate': 0.08,
        'healthcare_gdp_share': 0.06, 'use_progressive_tax': True,
        'skill_premium_growth': 0.003, 'union_coverage': 0.28,
        'capital_income_share': 0.15, 'import_competition': 0.08,
        'elite_capture_intensity': 0.08, 'informal_share': 0.10,
        'education_variance': 0.3, 'wage_dispersion_mult': 2.5,
        'inheritance_rate': 0.0, 'gini_actual': 0.36,
    },
    2020: {
        'system_name': 'JP_2020', 'tax_type': 'income',
        'income_tax_rate': 0.30, 'corp_tax_rate': 0.30, 'welfare_rate': 0.18,
        'healthcare_gdp_share': 0.11, 'use_progressive_tax': True,
        'skill_premium_growth': 0.008, 'union_coverage': 0.17,
        'capital_income_share': 0.22, 'import_competition': 0.20,
        'elite_capture_intensity': 0.18, 'informal_share': 0.35,
        'education_variance': 0.3, 'wage_dispersion_mult': 2.0,
        'inheritance_rate': 0.0, 'gini_actual': 0.40,
    },
}

YEARS = [1960, 1985, 2020]

def classify_trend(delta):
    if abs(delta) <= 0.02: return 'STABLE'
    return 'RISING' if delta > 0 else 'FALLING'

def validate_japan():
    print("="*70)
    print("JAPAN HISTORICAL BACKTEST — 3-Period Validation")
    print("="*70)
    for year in YEARS:
        cfg = PERIODS[year]
        for key in ['wage_dispersion_mult','inheritance_rate','gini_actual']:
            if key not in cfg: raise ValueError(f"{year}: missing '{key}'")
    results = {}
    prev_gini = None
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
        assert err_pct < 10.0, f"JAPAN {year}s: level error {err_pct:.1f}% > 10%"
        prev_gini = gini
    delta = results[2020]['gini']-results[1960]['gini']
    trend = classify_trend(delta)
    print(f"\nOverall 1960->2020 delta: {delta:.4f} trend={trend} (expected RISING)")
    assert trend == 'RISING', f"JAPAN trend: {trend}, expected RISING"
    print(f"\nJAPAN BACKTEST: PASS — {trend} trend, all levels < 10% err")
    return 0, results

def main():
    try:
        ec, results = validate_japan()
        os.makedirs("output", exist_ok=True)
        json.dump(results, open("output/japan_backtest_results.json","w"), indent=2)
        sys.exit(ec)
    except AssertionError as e: print(f"FAIL: {e}"); sys.exit(1)
    except (ValueError,RuntimeError) as e: print(f"ERROR: {e}",file=sys.stderr); sys.exit(1)
    except Exception as e: print(f"FATAL: {e}",file=sys.stderr); traceback.print_exc(file=sys.stderr); sys.exit(2)

if __name__ == '__main__':
    main()
