#!/usr/bin/env python3
"""validate_china_backtest.py — China historical backtest.

3 periods: 1980 (planned economy, egalitarian),
2000 (reform boom, rising inequality),
2020 (moderating inequality, service economy).

Key mechanisms: informal_share (5%->40%->25%), SBTC,
capital_income_share, import_competition.
Sources: World Bank WDI, OECD, Piketty.
"""
import sys, os, json, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

PERIODS = {
    1980: {
        'system_name': 'CN_1980', 'tax_type': 'income',
        'income_tax_rate': 0.05, 'corp_tax_rate': 0.55, 'welfare_rate': 0.01,
        'healthcare_gdp_share': 0.02,
        'informal_share': 0.05, 'skill_premium_growth': 0.002,
        'union_coverage': 0.40, 'capital_income_share': 0.05,
        'import_competition': 0.02, 'elite_capture_intensity': 0.05,
        'wage_dispersion_mult': 1.5, 'inheritance_rate': 0.0, 'gini_actual': 0.28,
    },
    2000: {
        'system_name': 'CN_2000', 'tax_type': 'income',
        'income_tax_rate': 0.10, 'corp_tax_rate': 0.33, 'welfare_rate': 0.03,
        'healthcare_gdp_share': 0.03,
        'informal_share': 0.40, 'skill_premium_growth': 0.015,
        'union_coverage': 0.15, 'capital_income_share': 0.20,
        'import_competition': 0.15, 'elite_capture_intensity': 0.20,
        'wage_dispersion_mult': 2.5, 'inheritance_rate': 0.0, 'gini_actual': 0.43,
    },
    2020: {
        'system_name': 'CN_2020', 'tax_type': 'income',
        'income_tax_rate': 0.15, 'corp_tax_rate': 0.25, 'welfare_rate': 0.07,
        'healthcare_gdp_share': 0.05,
        'informal_share': 0.25, 'skill_premium_growth': 0.012,
        'union_coverage': 0.15, 'capital_income_share': 0.22,
        'import_competition': 0.20, 'elite_capture_intensity': 0.25,
        'wage_dispersion_mult': 1.8, 'inheritance_rate': 0.0, 'gini_actual': 0.36,
    },
}

YEARS = [1980, 2000, 2020]

def classify_trend(delta):
    if abs(delta) <= 0.02: return 'STABLE'
    return 'RISING' if delta > 0 else 'FALLING'

def validate_china():
    print("="*70)
    print("CHINA HISTORICAL BACKTEST — 3-Period Validation")
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
        assert err_pct < 10.0, f"CHINA {year}s: level error {err_pct:.1f}% > 10%"
        prev_gini = gini
    # China: must RISE then FALL
    r1 = results[2000]['gini']-results[1980]['gini']
    r2 = results[2020]['gini']-results[2000]['gini']
    print(f"\n1980->2000: {r1:+.4f} (must RISE), 2000->2020: {r2:+.4f} (must FALL)")
    assert r1 > 0.02, f"CHINA 1980->2000 must RISE, got {r1:+.4f}"
    assert r2 < -0.02, f"CHINA 2000->2020 must FALL, got {r2:+.4f}"
    print(f"\nCHINA BACKTEST: PASS — RISE-THEN-FALL pattern, all levels < 10% err")
    return 0, results

def main():
    try:
        ec, results = validate_china()
        os.makedirs("output", exist_ok=True)
        json.dump(results, open("output/china_backtest_results.json","w"), indent=2)
        sys.exit(ec)
    except AssertionError as e: print(f"FAIL: {e}"); sys.exit(1)
    except (ValueError,RuntimeError) as e: print(f"ERROR: {e}",file=sys.stderr); sys.exit(1)
    except Exception as e: print(f"FATAL: {e}",file=sys.stderr); traceback.print_exc(file=sys.stderr); sys.exit(2)

if __name__ == '__main__':
    main()
