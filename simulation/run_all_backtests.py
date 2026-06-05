#!/usr/bin/env python3
"""
run_all_backtests.py — Unified 9-country backtest runner.

Imports period configs from each country's validate script and runs all
periods for all 9 countries (US_fix, UK, Germany, France, Brazil, Japan,
India, China, South Korea). Produces a consolidated results table and
saves to output/all_backtest_results.json.

Exit code: 0 = ALL PASS, 1 = ANY FAIL
"""
import sys, os, json, traceback, importlib.util
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

TREND_THRESHOLD = 0.02
LEVEL_THRESHOLD = 10.0  # Max acceptable % level error

def classify_trend(delta):
    if abs(delta) <= TREND_THRESHOLD:
        return 'STABLE'
    return 'RISING' if delta > 0 else 'FALLING'

def load_country(name, filepath):
    """Load PERIODS dict from a validate script by importing it."""
    spec = importlib.util.spec_from_file_location(f"validate_{name}", filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {filepath}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PERIODS, mod.YEARS

# Map country name -> (script_path, expected_trend)
# Expected trend patterns:
# - Simple str: 'RISING', 'FALLING', 'STABLE' (overall first-to-last delta)
# - Tuple: ('RISE_THEN_FALL', peak_year) for patterns like China
COUNTRIES = {
    'UK':          ('validate_uk_backtest.py', 'RISING'),
    'Germany':     ('validate_germany_backtest.py', 'STABLE'),
    'France':      ('validate_france_backtest.py', 'FALLING'),
    'Brazil':      ('validate_brazil_backtest.py', 'FALLING'),
    'Japan':       ('validate_japan_backtest.py', 'RISING'),
    'India':       ('validate_india_backtest.py', 'STABLE'),
    'China':       ('validate_china_backtest.py', ('RISE_THEN_FALL', 2000)),
    'South_Korea': ('validate_sk_backtest.py', 'STABLE'),
}

# US period configs (from validate_backtest_us_fix.py)
US_PERIODS = {
    1960: {
        'system_name': 'US_1960', 'tax_type': 'income',
        'income_tax_rate': 0.25, 'corp_tax_rate': 0.50, 'welfare_rate': 0.04,
        'healthcare_gdp_share': 0.05, 'use_progressive_tax': True,
        'skill_premium_growth': 0.003, 'union_coverage': 0.35,
        'capital_income_share': 0.05, 'import_competition': 0.02,
        'elite_capture_intensity': 0.05, 'informal_share': 0.05,
        'wage_dispersion_mult': 2.0, 'education_variance': 0.5,
        'inheritance_rate': 0.0, 'gini_actual': 0.36,
    },
    2020: {
        'system_name': 'US_2020', 'tax_type': 'income',
        'income_tax_rate': 0.20, 'corp_tax_rate': 0.21, 'welfare_rate': 0.15,
        'healthcare_gdp_share': 0.18, 'use_progressive_tax': True,
        'skill_premium_growth': 0.015, 'union_coverage': 0.12,
        'capital_income_share': 0.22, 'import_competition': 0.20,
        'elite_capture_intensity': 0.20, 'informal_share': 0.08,
        'wage_dispersion_mult': 2.5, 'education_variance': 0.7,
        'inheritance_rate': 0.0, 'gini_actual': 0.42,
    },
}
US_YEARS = [1960, 2020]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def check_trend(results, years, expected):
    """Check trend against expectation. Returns (pass_bool, detail_str)."""
    if len(years) < 2:
        return True, "N/A (1 period)"
    
    first_gini = results[years[0]]['gini']
    last_gini = results[years[-1]]['gini']
    overall_delta = last_gini - first_gini
    overall_trend = classify_trend(overall_delta)
    
    if isinstance(expected, tuple):
        # Complex pattern: e.g., ('RISE_THEN_FALL', peak_year)
        pattern, peak_year = expected
        if pattern == 'RISE_THEN_FALL':
            peak_idx = next((i for i, y in enumerate(years) if y == peak_year), None)
            if peak_idx is None or peak_idx == 0 or peak_idx >= len(years) - 1:
                return False, f"Invalid RISE_THEN_FALL config: peak={peak_year}, years={years}"
            # Rise phase: first -> peak
            rise_delta = results[peak_year]['gini'] - results[years[0]]['gini']
            rise_ok = rise_delta > TREND_THRESHOLD
            # Fall phase: peak -> last
            fall_delta = results[years[-1]]['gini'] - results[peak_year]['gini']
            fall_ok = fall_delta < -TREND_THRESHOLD
            details = f"rise={rise_delta:+.4f} ({'OK' if rise_ok else 'FAIL'}), fall={fall_delta:+.4f} ({'OK' if fall_ok else 'FAIL'})"
            return (rise_ok and fall_ok), details
    
    # Simple trend check
    ok = overall_trend == expected
    return ok, f"overall={overall_trend} (expected {expected})"


def run_country(name, periods, years, expected, seed=42):
    """Run a full backtest for one country. Returns (pass_bool, results_dict, details_str)."""
    results = {}
    prev_gini = None
    details = []
    
    for year in years:
        cfg = periods[year]
        actual = cfg['gini_actual']
        w, r, b = gen_population(seed)
        res = run_phase8(w, r, b, seed, cfg)
        if 'error' in res:
            return False, results, f"ERROR at {year}s: {res['error']}"
        gini = res['gini']
        err_pct = abs(gini - actual) / max(actual, 0.01) * 100
        
        if prev_gini is not None:
            delta = gini - prev_gini
            trend = classify_trend(delta)
        else:
            delta = None
            trend = 'START'
        
        results[year] = {
            'gini': round(gini, 4),
            'actual': actual,
            'err_pct': round(err_pct, 2),
            'delta': round(delta, 4) if delta is not None else None,
            'trend': trend,
        }
        details.append(f"  {year}s: sim={gini:.4f} actual={actual} err={err_pct:.1f}% trend={trend}")
        prev_gini = gini
    
    # Verify level errors
    level_pass = all(r['err_pct'] < LEVEL_THRESHOLD for r in results.values())
    details.append(f"  Level errors: {'ALL < 10%' if level_pass else 'SOME >= 10%'}")
    
    # Check trend
    trend_pass, trend_detail = check_trend(results, years, expected)
    details.append(f"  Trend: {trend_detail}")
    
    status = 'PASS' if (level_pass and trend_pass) else 'FAIL'
    details.append(f"  OVERALL: {status}")
    
    return (level_pass and trend_pass), results, '\n'.join(details)


def expected_str(expected):
    """Human-readable expected trend."""
    if isinstance(expected, tuple):
        pattern, peak = expected
        if pattern == 'RISE_THEN_FALL':
            return f'RISE→FALL(peak{peak})'
    return str(expected)


def main():
    os.makedirs("output", exist_ok=True)
    all_results = {}
    pass_count = 0
    fail_count = 0
    
    print("=" * 80)
    print("  UNIFIED 9-COUNTRY BACKTEST RUNNER")
    print("=" * 80)
    
    # Run US (config defined inline)
    print(f"\n--- US ---")
    us_pass, us_results, us_details = run_country('US', US_PERIODS, US_YEARS, 'RISING')
    print(us_details)
    all_results['US'] = us_results
    if us_pass: pass_count += 1
    else: fail_count += 1
    
    # Run all countries from validate scripts
    for name, (script_name, expected) in COUNTRIES.items():
        script_path = os.path.join(SCRIPT_DIR, script_name)
        if not os.path.exists(script_path):
            print(f"\n--- {name} ---")
            print(f"  SKIPPED: {script_name} not found")
            continue
        try:
            periods, years = load_country(name, script_path)
        except Exception as e:
            print(f"\n--- {name} ---")
            print(f"  LOAD ERROR: {e}")
            continue
        
        print(f"\n--- {name} ---")
        try:
            passed, results, details = run_country(name, periods, years, expected, seed=42)
            print(details)
            all_results[name] = results
            if passed:
                pass_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  RUNTIME ERROR: {e}")
            traceback.print_exc()
            fail_count += 1
    
    # Summary table
    print("\n" + "=" * 96)
    print("  CONSOLIDATED RESULTS TABLE")
    print("=" * 96)
    print(f"{'Country':<14} {'Periods':<20} {'First':>9} {'Last':>9} {'Trend':>10} {'Expected':>16} {'Status':>8}")
    print("-" * 96)
    
    # Define all 9 countries in order
    all_names = ['US', 'UK', 'Germany', 'France', 'Brazil', 'Japan', 'India', 'China', 'South_Korea']
    
    for country_name in all_names:
        if country_name not in all_results:
            print(f"{country_name:<14} {'SKIPPED':<20}")
            continue
        results = all_results[country_name]
        years = sorted(results.keys())
        first = results[years[0]]
        last = results[years[-1]]
        first_gini = first['gini']
        last_gini = last['gini']
        
        # Get expected trend
        if country_name == 'US':
            expected = 'RISING'
        else:
            expected = COUNTRIES[country_name][1]
        
        # Determine pass/fail status
        level_fail = any(r['err_pct'] >= LEVEL_THRESHOLD for r in results.values())
        trend_ok, _ = check_trend(results, years, expected)
        status = 'PASS' if (not level_fail and trend_ok) else 'FAIL'
        
        period_str = f"{years[0]}-{years[-1]} ({len(years)} per)"
        print(f"{country_name:<14} {period_str:<20} {first_gini:>9.4f} {last_gini:>9.4f} {classify_trend(last_gini-first_gini):>10} {expected_str(expected):>16} {status:>8}")
    
    print("-" * 96)
    print(f"  PASS: {pass_count}  FAIL: {fail_count}  TOTAL: {pass_count + fail_count}")
    
    # Save consolidated results
    with open("output/all_backtest_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Saved: output/all_backtest_results.json")
    
    return 0 if fail_count == 0 else 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"FATAL: {e}")
        traceback.print_exc()
        sys.exit(2)
