#!/usr/bin/env python3
"""validate_germany_backtest.py — Germany historical backtest with period-varying wage_disp.

Runs 3 chained simulation periods (1960, 1990, 2020) capturing:
- Post-war Wirtschaftswunder (1960s): strong unions, codetermination, low inequality
- Reunification era (1990): East/West wage convergence shock
- Modern era (2020): Hartz reforms, services economy, stable inequality

Germany-specific mechanisms (reunification_shock, hartz_reform) disabled in favor
of period-varying wage_dispersion_mult, which better captures structural changes
in Germany's wage distribution without per-country code.

Sources:
  - OECD Tax Revenue Database — tax rates, welfare spending
  - WID.world — Gini series for Germany
  - ICTWSS — union coverage data
  - Bundesbank — reunification transfer data

Usage:
    python validate_germany_backtest.py
Exit code: 0 = PASS, 1 = FAIL, 2 = FATAL
"""
import sys, os, json, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

PERIODS = {
    1960: {
        'system_name': 'DE_1960', 'tax_type': 'income',
        'income_tax_rate': 0.35, 'corp_tax_rate': 0.50, 'welfare_rate': 0.06,
        'healthcare_gdp_share': 0.05, 'use_progressive_tax': True,
        'skill_premium_growth': 0.005, 'union_coverage': 0.30,
        'capital_income_share': 0.05, 'import_competition': 0.02,
        'elite_capture_intensity': 0.02, 'wage_dispersion_mult': 2.2,
        'inheritance_rate': 0.0, 'gini_actual': 0.30,
    },
    1990: {
        'system_name': 'DE_1990', 'tax_type': 'income',
        'income_tax_rate': 0.38, 'corp_tax_rate': 0.50, 'welfare_rate': 0.10,
        'healthcare_gdp_share': 0.08, 'use_progressive_tax': True,
        'skill_premium_growth': 0.008, 'union_coverage': 0.28,
        'capital_income_share': 0.08, 'import_competition': 0.05,
        'elite_capture_intensity': 0.03, 'wage_dispersion_mult': 1.7,
        'inheritance_rate': 0.0, 'gini_actual': 0.28,
    },
    2020: {
        'system_name': 'DE_2020', 'tax_type': 'income',
        'income_tax_rate': 0.40, 'corp_tax_rate': 0.15, 'welfare_rate': 0.13,
        'healthcare_gdp_share': 0.10, 'use_progressive_tax': True,
        'skill_premium_growth': 0.012, 'union_coverage': 0.22,
        'capital_income_share': 0.12, 'import_competition': 0.12,
        'elite_capture_intensity': 0.05, 'wage_dispersion_mult': 1.8,
        'inheritance_rate': 0.0, 'gini_actual': 0.30,
    },
}

YEARS = [1960, 1990, 2020]
LEVEL_THRESHOLD = 10.0

def classify_trend(delta):
    if abs(delta) <= 0.02:
        return 'STABLE'
    return 'RISING' if delta > 0 else 'FALLING'

def validate_germany():
    print("=" * 70)
    print("GERMANY HISTORICAL BACKTEST — 3-Period Validation")
    print("Period-varying wage_disp: 2.0→1.5→1.8")
    print("=" * 70)
    print()
    
    for year in YEARS:
        cfg = PERIODS[year]
        for key in ['wage_dispersion_mult', 'inheritance_rate', 'gini_actual']:
            if key not in cfg:
                raise ValueError(f"{year}: missing '{key}'")
    
    results = {}
    prev_gini = None
    fail_count = 0
    
    print(f"{'Period':<10} {'Sim Gini':>10} {'Actual':>8} {'Err%':>6} {'NW Gini':>10} {'Trend':>10}")
    print("-" * 56)
    
    for year in YEARS:
        cfg = PERIODS[year]
        actual = cfg['gini_actual']
        w, r, b = gen_population(42)
        res = run_phase8(w, r, b, 42, cfg)
        
        if 'error' in res:
            raise RuntimeError(f"{year}: {res['error']}")
        
        gini = res['gini']
        nw_gini = res.get('net_worth_gini', 0)
        err_pct = abs(gini - actual) / max(actual, 0.01) * 100
        
        if prev_gini is not None:
            delta = gini - prev_gini
            trend = classify_trend(delta)
        else:
            delta = 0.0
            trend = ''
        
        results[year] = {
            'gini': round(gini, 4), 'actual': actual,
            'err_pct': round(err_pct, 2), 'net_worth_gini': round(nw_gini, 4),
            'delta': round(delta, 4) if prev_gini is not None else None,
            'trend': trend if prev_gini is not None else 'START',
        }
        
        print(f"{year}s".ljust(10) + f" {gini:>8.4f} {actual:>8.2f} {err_pct:>5.1f}% {nw_gini:>8.4f} {trend:>10}")
        
        assert err_pct < LEVEL_THRESHOLD, (
            f"GERMANY {year}s: level error {err_pct:.1f}% > {LEVEL_THRESHOLD}%"
        )
        prev_gini = gini
    
    # Overall trend
    gini_60 = results[1960]['gini']
    gini_20 = results[2020]['gini']
    overall_delta = gini_20 - gini_60
    overall_trend = classify_trend(overall_delta)
    
    print()
    print(f"Overall 1960→2020 delta: {overall_delta:.4f}")
    print(f"Overall trend: {overall_trend} (expected: STABLE)")
    assert overall_trend == 'STABLE', (
        f"GERMANY overall trend: {overall_trend}, expected STABLE"
    )
    
    print()
    print("=" * 70)
    print(f"GERMANY BACKTEST: PASS — {overall_trend} trend, all levels < {LEVEL_THRESHOLD}% err")
    print("=" * 70)
    return 0, results

def main():
    try:
        exit_code, results = validate_germany()
        os.makedirs("output", exist_ok=True)
        with open("output/germany_backtest_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"Saved: output/germany_backtest_results.json")
        sys.exit(exit_code)
    except AssertionError as e:
        print(f"FAIL: {e}")
        sys.exit(1)
    except (ValueError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(2)

if __name__ == '__main__':
    main()
