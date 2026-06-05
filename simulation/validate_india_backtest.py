#!/usr/bin/env python3
"""validate_india_backtest.py — India historical backtest.

2 periods: 1970s (License Raj, high informality) and
2020s (liberalized, services-driven, persistent inequality).

Key mechanisms: informal_share (85%->80%), elite_capture_intensity,
capital_income_share, skill_premium_growth.
Sources: OECD, World Bank WDI, ILO.
"""
import sys, os, json, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

PERIODS = {
    1970: {
        'system_name': 'IN_1970', 'tax_type': 'income',
        'income_tax_rate': 0.15, 'corp_tax_rate': 0.55, 'welfare_rate': 0.02,
        'healthcare_gdp_share': 0.02,
        'elite_capture_intensity': 0.35, 'informal_share': 0.85,
        'informal_wage_penalty': 0.4, 'wage_dispersion_mult': 3.5,
        'inheritance_rate': 0.0, 'gini_actual': 0.48,
    },
    2020: {
        'system_name': 'IN_2020', 'tax_type': 'income',
        'income_tax_rate': 0.25, 'corp_tax_rate': 0.25, 'welfare_rate': 0.08,
        'healthcare_gdp_share': 0.04,
        'skill_premium_growth': 0.015, 'capital_income_share': 0.20,
        'import_competition': 0.25, 'elite_capture_intensity': 0.35,
        'informal_share': 0.80, 'informal_wage_penalty': 0.4,
        'wage_dispersion_mult': 2.5, 'inheritance_rate': 0.0, 'gini_actual': 0.48,
    },
}

YEARS = [1970, 2020]

def classify_trend(delta):
    if abs(delta) <= 0.02: return 'STABLE'
    return 'RISING' if delta > 0 else 'FALLING'

def validate_india():
    print("="*70)
    print("INDIA HISTORICAL BACKTEST — 2-Period Validation")
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
        assert err_pct < 10.0, f"INDIA {year}s: level error {err_pct:.1f}% > 10%"
        prev_gini = gini
    delta = results[2020]['gini']-results[1970]['gini']
    trend = classify_trend(delta)
    print(f"\nOverall 1970->2020 delta: {delta:.4f} trend={trend} (expected STABLE)")
    assert trend == 'STABLE', f"INDIA trend: {trend}, expected STABLE"
    print(f"\nINDIA BACKTEST: PASS — {trend} trend, all levels < 10% err")
    return 0, results

def main():
    try:
        ec, results = validate_india()
        os.makedirs("output", exist_ok=True)
        json.dump(results, open("output/india_backtest_results.json","w"), indent=2)
        sys.exit(ec)
    except AssertionError as e: print(f"FAIL: {e}"); sys.exit(1)
    except (ValueError,RuntimeError) as e: print(f"ERROR: {e}",file=sys.stderr); sys.exit(1)
    except Exception as e: print(f"FATAL: {e}",file=sys.stderr); traceback.print_exc(file=sys.stderr); sys.exit(2)

if __name__ == '__main__':
    main()
