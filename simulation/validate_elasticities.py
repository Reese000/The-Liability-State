#!/usr/bin/env python3
"""
validate_elasticities.py — Validate that simulation responses match economic theory.

Tests:
  (a) Labor supply response to income tax (higher tax → lower labor supply)
  (b) Savings/wealth response to interest rate (higher rate → higher wealth)

For each test: runs US_Style with two parameter values, same seed (42),
reports key metrics in a comparison table, and PASS/FAIL based on whether
the direction of the effect matches economic theory.
"""

import sys, os, copy, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))

from comparison_phase4 import gen_population, LABOR_SUPPLY_ELASTICITY
from comparison_phase5 import PHASE5_CONFIGS, run_phase5

SEED = 42
SEP = "─" * 70


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

def fmt_usd(v):
    """Format number as USD (or raw if very small)."""
    if abs(v) >= 100:
        return f"${v:>10,.0f}"
    return f"{v:>10.4f}"


def fmt_pct(v):
    return f"{v:>+8.2f}%"


def theoretical_labor_supply_ratio(inc_tax_rate):
    """
    Compute the labor supply ratio implied by the simulation's own formula.

    The simulation computes:
        after = hourly * (1 - inc_tax_rate)
        lr = (after / hourly) ** LABOR_SUPPLY_ELASTICITY
    So:  lr = (1 - inc_tax_rate) ** LABOR_SUPPLY_ELASTICITY
    """
    return (1.0 - inc_tax_rate) ** LABOR_SUPPLY_ELASTICITY


def fmt_pass_fail(passed):
    return "✓  PASS" if passed else "✗  FAIL"


# ═══════════════════════════════════════════════════════════════
#  Test (a): Labor supply response to income tax
# ═══════════════════════════════════════════════════════════════

def test_labor_supply():
    print(f"\n{SEP}")
    print("  TEST (a): Labor Supply Response to Income Tax")
    print(f"  Higher income tax → lower after-tax wage → lower labor supply → lower wages")
    print(f"{SEP}\n")

    TAX_LOW = 0.1
    TAX_HIGH = 0.4
    ELASTICITY = LABOR_SUPPLY_ELASTICITY

    # ── 1. Theoretical prediction ──────────────────────────────
    print("  ── 1. Theoretical prediction (from simulation formula) ──")
    print(f"     Labor supply elasticity (η) = {ELASTICITY}")
    print(f"     Formula: lr = (1 - tax_rate)^η\n")

    lr_low = theoretical_labor_supply_ratio(TAX_LOW)
    lr_high = theoretical_labor_supply_ratio(TAX_HIGH)
    lr_change = (lr_high - lr_low) / lr_low * 100

    print(f"     At income_tax = {TAX_LOW}:  lr = (1 - {TAX_LOW})^{ELASTICITY} = {lr_low:.4f}")
    print(f"     At income_tax = {TAX_HIGH}: lr = (1 - {TAX_HIGH})^{ELASTICITY} = {lr_high:.4f}")
    print(f"     Theoretical labor supply change: {lr_change:+.2f}%")
    if lr_high < lr_low:
        print(f"     ✓ Direction: labor supply DECREASES with higher tax (matches theory)\n")
    else:
        print(f"     ✗ Direction: labor supply does not decrease (contradicts theory)\n")

    # ── 2. Simulation ──────────────────────────────────────────
    print("  ── 2. Simulation runs ──")

    # Build configs (deep copy ensures no cross-talk)
    cfg_low = copy.deepcopy(PHASE5_CONFIGS['US_Style'])
    cfg_low['income_tax_rate'] = TAX_LOW

    cfg_high = copy.deepcopy(PHASE5_CONFIGS['US_Style'])
    cfg_high['income_tax_rate'] = TAX_HIGH

    # Run low-tax scenario (fresh population for each run)
    pop = gen_population(SEED)
    res_low = run_phase5(*pop, SEED, cfg_low)

    # Run high-tax scenario
    pop = gen_population(SEED)
    res_high = run_phase5(*pop, SEED, cfg_high)

    # ── 3. Comparison table ────────────────────────────────────
    print("\n  ── 3. Results comparison ──\n")
    header = f"  {'Metric':<24} {'tax=0.1':>14} {'tax=0.4':>14} {'Change':>14}"
    print(header)
    print(f"  {'─' * 24} {'─' * 14} {'─' * 14} {'─' * 14}")

    metrics_a = [
        ("Total Wealth",        res_low['wealth'],  res_high['wealth']),
        ("Mean Worker Wealth",  res_low['w_mean'],  res_high['w_mean']),
        ("Min Worker Wealth",   res_low['w_min'],   res_high['w_min']),
        ("Max Worker Wealth",   res_low['w_max'],   res_high['w_max']),
        ("Gini",                res_low['gini'],    res_high['gini']),
    ]

    for name, v_low, v_high in metrics_a:
        if isinstance(v_low, (int, float)) and abs(v_low) >= 100:
            l_s = fmt_usd(v_low)
            h_s = fmt_usd(v_high)
        else:
            l_s = f"{v_low:>10.4f}"
            h_s = f"{v_high:>10.4f}"
        if v_low != 0:
            chg = (v_high - v_low) / abs(v_low) * 100
        else:
            chg = 0.0
        print(f"  {name:<24} {l_s:>14} {h_s:>14} {fmt_pct(chg):>14}")

    # ── 4. Verdict ─────────────────────────────────────────────
    print(f"\n  ── 4. Verdict ──")
    print(f"     Theory: higher income tax → lower labor supply → lower wages → lower wealth")

    # Primary check: mean worker wealth should be lower at higher tax
    wm_low = res_low['w_mean']
    wm_high = res_high['w_mean']
    wealth_low = res_low['wealth']
    wealth_high = res_high['wealth']

    # Use mean worker wealth as the main signal (less confounded by govt balances)
    # But also check total wealth
    wm_check = wm_high < wm_low
    wealth_check = wealth_high < wealth_low

    print(f"     Mean worker wealth:  tax=0.1 = {fmt_usd(wm_low)}  tax=0.4 = {fmt_usd(wm_high)}")
    print(f"       → Higher tax {'✓ decreases' if wm_check else '✗ does NOT decrease'} mean worker wealth")
    print(f"     Total wealth:        tax=0.1 = {fmt_usd(wealth_low)}  tax=0.4 = {fmt_usd(wealth_high)}")
    print(f"       → Higher tax {'✓ decreases' if wealth_check else '✗ does NOT decrease'} total wealth")

    # Primary pass/fail: mean worker wealth direction
    # (most robust indicator of labor supply effect on workers)
    passed_a = wm_check
    print(f"\n     >>> {fmt_pass_fail(passed_a)} <<<")
    return passed_a, {
        'tax_low': TAX_LOW, 'tax_high': TAX_HIGH,
        'lr_low': round(lr_low, 4), 'lr_high': round(lr_high, 4),
        'lr_change_pct': round(lr_change, 2),
        'wmean_low': wm_low, 'wmean_high': wm_high,
        'wealth_low': wealth_low, 'wealth_high': wealth_high,
        'gini_low': res_low['gini'], 'gini_high': res_high['gini'],
    }


# ═══════════════════════════════════════════════════════════════
#  Test (b): Savings/wealth response to interest rate
#  ═══════════════════════════════════════════════════════════════

def test_savings():
    print(f"\n{SEP}")
    print("  TEST (b): Savings/Wealth Response to Interest Rate")
    print(f"  Higher interest rate → more interest income → higher wealth accumulation")
    print(f"{SEP}\n")

    IRT_LOW = 0.0
    IRT_HIGH = 0.01
    BANK_RESERVE = 100_000_000  # Seed the bank so the banking channel can function

    # ── 1. Theoretical prediction ──────────────────────────────
    print("  ── 1. Theoretical prediction ──")
    print(f"     Banking channel (US_Style has banking_multiplier=3):")
    print(f"       Interest paid per step = balance × 0.1 × interest_rate")
    print(f"     At {IRT_LOW}: zero interest payments")
    print(f"     At {IRT_HIGH}: citizens earn 0.1% of balance/step in interest")
    print(f"     → Higher interest rate → more interest income → higher wealth\n")
    print(f"     NOTE: Bank is seeded with ${BANK_RESERVE:,} (bank_initial_reserve)")
    print(f"     because the default bank balance of 0 deadlocks the banking channel.")
    print(f"     (bal['bank']=0 → no loans can be given → no fees accrue →")
    print(f"      bal['bank'] stays 0 → no interest can ever be paid)\n")

    # ── 2. Simulation ──────────────────────────────────────────
    print("  ── 2. Simulation runs ──")

    cfg_low = copy.deepcopy(PHASE5_CONFIGS['US_Style'])
    cfg_low['interest_rate'] = IRT_LOW
    cfg_low['bank_initial_reserve'] = BANK_RESERVE

    cfg_high = copy.deepcopy(PHASE5_CONFIGS['US_Style'])
    cfg_high['interest_rate'] = IRT_HIGH
    cfg_high['bank_initial_reserve'] = BANK_RESERVE

    pop = gen_population(SEED)
    res_low = run_phase5(*pop, SEED, cfg_low)

    pop = gen_population(SEED)
    res_high = run_phase5(*pop, SEED, cfg_high)

    # ── 3. Comparison table ────────────────────────────────────
    print("\n  ── 3. Results comparison ──\n")
    header = f"  {'Metric':<24} {'ir=0.000':>14} {'ir=0.010':>14} {'Change':>14}"
    print(header)
    print(f"  {'─' * 24} {'─' * 14} {'─' * 14} {'─' * 14}")

    metrics_b = [
        ("Total Wealth",        res_low['wealth'],  res_high['wealth']),
        ("Mean Worker Wealth",  res_low['w_mean'],  res_high['w_mean']),
        ("Min Worker Wealth",   res_low['w_min'],   res_high['w_min']),
        ("Max Worker Wealth",   res_low['w_max'],   res_high['w_max']),
        ("Gini",                res_low['gini'],    res_high['gini']),
    ]

    for name, v_low, v_high in metrics_b:
        if isinstance(v_low, (int, float)) and abs(v_low) >= 100:
            l_s = fmt_usd(v_low)
            h_s = fmt_usd(v_high)
        else:
            l_s = f"{v_low:>10.4f}"
            h_s = f"{v_high:>10.4f}"
        if v_low != 0:
            chg = (v_high - v_low) / abs(v_low) * 100
        else:
            chg = 0.0
        print(f"  {name:<24} {l_s:>14} {h_s:>14} {fmt_pct(chg):>14}")

    # ── 4. Verdict ─────────────────────────────────────────────
    print(f"\n  ── 4. Verdict ──")
    print(f"     Theory: higher interest rate → more savings income → higher wealth")

    wm_low = res_low['w_mean']
    wm_high = res_high['w_mean']
    wealth_low = res_low['wealth']
    wealth_high = res_high['wealth']

    wm_check = wm_high > wm_low
    wealth_check = wealth_high > wealth_low

    print(f"     Mean worker wealth:  ir=0.000 = {fmt_usd(wm_low)}  ir=0.010 = {fmt_usd(wm_high)}")
    print(f"       → Higher rate {'✓ increases' if wm_check else '✗ does NOT increase'} mean worker wealth")
    print(f"     Total wealth:        ir=0.000 = {fmt_usd(wealth_low)}  ir=0.010 = {fmt_usd(wealth_high)}")
    print(f"       → Higher rate {'✓ increases' if wealth_check else '✗ does NOT increase'} total wealth")

    passed_b = wealth_check
    print(f"\n     >>> {fmt_pass_fail(passed_b)} <<<")
    return passed_b, {
        'irt_low': IRT_LOW, 'irt_high': IRT_HIGH,
        'wmean_low': wm_low, 'wmean_high': wm_high,
        'wealth_low': wealth_low, 'wealth_high': wealth_high,
        'gini_low': res_low['gini'], 'gini_high': res_high['gini'],
    }


# ═══════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║       VALIDATE ELASTICITIES — Economic Theory Checks        ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  Seed: {SEED}")

    passed_a, details_a = test_labor_supply()
    passed_b, details_b = test_savings()

    # ── Summary ─────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SUMMARY")
    print(f"{SEP}\n")
    print(f"  (a) Labor supply  {fmt_pass_fail(passed_a)}  "
          f"(tax {details_a['tax_low']}→{details_a['tax_high']}: "
          f"lr change {details_a['lr_change_pct']:+.2f}%, "
          f"wmean {fmt_usd(details_a['wmean_low'])}→{fmt_usd(details_a['wmean_high'])})")
    print(f"  (b) Savings/wealth {fmt_pass_fail(passed_b)}  "
          f"(ir {details_b['irt_low']}→{details_b['irt_high']}: "
          f"wmean {fmt_usd(details_b['wmean_low'])}→{fmt_usd(details_b['wmean_high'])})")

    all_pass = passed_a and passed_b
    print(f"\n  OVERALL: {fmt_pass_fail(all_pass)}")
    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
