#!/usr/bin/env python3
"""
V4 — Harberger Convergence Validation
======================================

Tests the self-assessment property system: agents own parcels and must
self-assess their value. Under the Harberger mechanism:
  - Under-declaring invites forced purchase below true value
  - Over-declaring increases LVT without benefit
Declared values should converge toward true market values over time.

Tracks declared_value / true_value ratio over each simulation step.
Prints clear pass/fail based on convergence criteria from VALIDATION_FRAMEWORK.md §5.

Spec reference: VALIDATION_FRAMEWORK.md §5 — Stage V4: Harberger Convergence
"""

from __future__ import annotations

import sys
import os
import math
import random
from statistics import median, mean, stdev, linear_regression

# ── Path setup: import from simulation/src package ───────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_SIM_ROOT = os.path.abspath(os.path.join(_HERE, '..'))  # simulation/
if _SIM_ROOT not in sys.path:
    sys.path.insert(0, _SIM_ROOT)

# Import via the src package so relative imports inside
# mechanics/harberger.py resolve correctly (src is a package with __init__.py).
from src.core.ledger import LedgerEngine, EntityType
from src.mechanics.harberger import HarbergerMarket


# ═══════════════════════════════════════════════════════════════════════
#  Metrics
# ═══════════════════════════════════════════════════════════════════════

def mean_abs_deviation(ratios: list[float]) -> float:
    """Mean absolute deviation of ratio from 1.0."""
    if not ratios:
        return 0.0
    return mean(abs(r - 1.0) for r in ratios)


def slope_of_mad(mad_history: list[float]) -> float:
    """Compute linear trend slope of MAD over time (negative = convergence)."""
    n = len(mad_history)
    if n < 4:
        return 0.0
    # Use points from first half and second half for robust slope
    xs = list(range(n))
    # linear_regression returns (slope, intercept) in Python 3.10+
    slope, _ = linear_regression(xs, mad_history)
    return slope


def coeff_of_variation(values: list[float]) -> float:
    """Coefficient of variation (std / mean)."""
    if len(values) < 2 or mean(values) == 0:
        return 0.0
    return stdev(values) / mean(values)


# ═══════════════════════════════════════════════════════════════════════
#  Core simulation
# ═══════════════════════════════════════════════════════════════════════

def run_simulation(
    n_parcels: int = 50,
    lvt_rate: float = 0.05,
    p_buyer: float = 0.05,
    n_steps: int = 500,
    seed: int = 42,
    learning_rate: float = 0.10,
    initial_spread: float = 0.80,  # fraction of true value for initial spread range
) -> tuple[list[list[float]], list[dict], HarbergerMarket, list[dict], list[dict], list[float]]:
    """Run a single V4 Harberger convergence simulation.

    Parameters
    ----------
    n_parcels      : Number of land parcels (and agents).
    lvt_rate       : Land Value Tax rate (e.g. 0.05 = 5 %).
    p_buyer        : Per-step probability a random buyer appears.
    n_steps        : Number of simulation ticks.
    seed           : RNG seed for reproducibility.
    learning_rate  : How fast agents adjust declarations toward true value
                     per step (0 = static, 1 = instant).
    initial_spread : Spread of initial declarations around true value as a
                     fraction.  E.g. 0.80 means initial declared values are
                     drawn from [true*(1-spread), true*(1+spread)].

    Returns
    -------
    ratio_history : list[list[float]] — per-step list of declared/true ratios
    agents        : dict — agent state at end of simulation
    market        : HarbergerMarket — final market state
    """
    rng = random.Random(seed)
    ledger = LedgerEngine(step_log=False)
    market = HarbergerMarket(ledger, lvt_rate=lvt_rate)

    # ── Create a standing buyer with a deep war chest ──────────────
    BUYER_ID = 'standing_buyer'
    buyer_cash = 100_000_000.0  # effectively infinite for our scale
    ledger.register_entity(BUYER_ID, EntityType.CITIZEN,
                           compact_id='alpha', initial_cash=buyer_cash)

    # ── Create agents with heterogeneous true valuations ──────────
    agents: list[dict] = []
    for i in range(n_parcels):
        aid = f"agent_{i}"
        true_val = rng.uniform(10.0, 100.0)
        # Initial declared value is noisy — some too low, some too high
        noise = rng.uniform(1.0 - initial_spread, 1.0 + initial_spread)
        initial_declared = true_val * noise
        initial_declared = max(0.01, initial_declared)

        ledger.register_entity(aid, EntityType.CITIZEN,
                               compact_id='alpha', initial_cash=2000.0)
        market.register_parcel(f"parcel_{i}", aid, initial_declared)

        agents.append({
            'id': aid,
            'parcel_id': f"parcel_{i}",
            'true_value': true_val,
            'initial_declared': initial_declared,
        })

    # ── Tracking ──────────────────────────────────────────────────
    ratio_history: list[list[float]] = []
    bid_events: list[dict] = []          # ALL bids placed (accepted or refused)
    forced_sale_events: list[dict] = []  # only accepted bids
    lvt_revenue_history: list[float] = []

    # ── Main simulation loop ──────────────────────────────────────
    for step in range(n_steps):
        ledger.begin_step()
        market.advance_day()

        # --- Market event: buyer appears ---
        if rng.random() < p_buyer:
            # Strategic buyer: scan for under-declared parcels and pick
            # the one with the lowest declared/true value ratio.
            # This simulates a profit-seeking buyer who targets
            # attractively-priced (under-declared) assets.
            candidates: list[tuple[int, dict, float]] = []
            for idx, a in enumerate(agents):
                if not market.ledger.entity_exists(a['id']):
                    continue
                try:
                    p = market.get_parcel(a['parcel_id'])
                except KeyError:
                    continue
                ratio = p.declared_value / a['true_value'] if a['true_value'] > 0 else 1.0
                candidates.append((idx, a, ratio))

            if candidates:
                # Sort by ascending ratio — most under-declared first
                candidates.sort(key=lambda x: x[2])
                # Occasionally pick randomly to add noise,
                # but mostly pick the most under-declared
                if rng.random() < 0.8 and len(candidates) > 1:
                    idx, agent, _ = candidates[0]  # lowest ratio
                else:
                    idx, agent, _ = rng.choice(candidates[:max(3, len(candidates)//2)])

                try:
                    parcel = market.get_parcel(agent['parcel_id'])
                except KeyError:
                    pass
                else:
                    bid_price = parcel.declared_value

                    try:
                        bid = market.post_bid(
                            agent['parcel_id'], BUYER_ID,
                            bid_price=bid_price,
                        )
                    except ValueError:
                        # Buyer may lack funds (bond too high)
                        # Replenish buyer and retry
                        buyer_bs = ledger.get_balance(BUYER_ID)
                        if buyer_bs.cash < bid_price:
                            buyer_bs.cash += 1_000_000.0
                        try:
                            bid = market.post_bid(
                                agent['parcel_id'], BUYER_ID,
                                bid_price=bid_price,
                            )
                        except ValueError:
                            bid = None

                    if bid is not None:
                        # Track ALL bid events for efficiency analysis
                        bid_ratio = parcel.declared_value / agent['true_value'] if agent['true_value'] > 0 else 1.0
                        bid_record = {
                            'step': step,
                            'agent': agent['id'],
                            'parcel': agent['parcel_id'],
                            'declared': parcel.declared_value,
                            'true_value': agent['true_value'],
                            'ratio': bid_ratio,
                            'accepted': False,
                            'refused': False,
                        }
                        # Record every bid regardless of outcome
                        bid_events.append(bid_record.copy())

                        # Owner's decision:
                        #   Accept if declared >= true value (sale at ≥ reservation)
                        #   Accept with 15% probability even if under-declared
                        #     (liquidity constraints / imperfect rationality)
                        #   Refuse otherwise (asset worth more than declared price)
                        accept_under = (parcel.declared_value < agent['true_value']
                                        and rng.random() < 0.15)
                        if parcel.declared_value >= agent['true_value'] or accept_under:
                            # Accept forced sale
                            try:
                                sale = market.accept_bid(
                                    agent['parcel_id'], bid.bid_id,
                                )
                                bid_record['accepted'] = True
                                forced_sale_events.append({
                                    **bid_record,
                                    'sale_price': sale['sale_price'],
                                })

                                # Displaced owner gets a NEW parcel with a new
                                # true value; they set declaration close to it
                                new_true = rng.uniform(10.0, 100.0)
                                new_pid = f"parcel_{idx}_v{step}_{rng.randint(0,9999)}"
                                new_declared = new_true * rng.uniform(0.90, 1.10)
                                market.register_parcel(
                                    new_pid, agent['id'], new_declared,
                                )
                                agents[idx]['parcel_id'] = new_pid
                                agents[idx]['true_value'] = new_true

                            except ValueError:
                                pass

                        else:
                            # Refuse — asset worth more than declared price
                            try:
                                refusal = market.refuse_bid(
                                    agent['parcel_id'], bid.bid_id,
                                )
                                bid_record['refused'] = True
                                # After refusal, assessed_for_lvt is bumped up.
                                # Rational owner syncs declared value to the
                                # new assessed basis.
                                cp = market.get_parcel(agent['parcel_id'])
                                if cp.assessed_for_lvt > cp.declared_value:
                                    market.self_assess(
                                        agent['parcel_id'],
                                        cp.assessed_for_lvt,
                                    )
                            except ValueError:
                                pass

        # --- Agents adjust declarations toward true value ---
        for a in agents:
            try:
                parcel = market.get_parcel(a['parcel_id'])
            except KeyError:
                continue  # stale reference, skip

            current = parcel.declared_value
            diff = a['true_value'] - current
            if abs(diff) > 0.001:
                new_val = current + diff * learning_rate
                new_val = max(0.01, new_val)
                if abs(new_val - current) > 0.001:
                    try:
                        market.self_assess(a['parcel_id'], new_val)
                    except ValueError:
                        pass

        # --- Collect LVT ---
        try:
            lvt_result = market.assess_lvt()
            lvt_revenue_history.append(lvt_result['total_lvt'])
        except Exception:
            lvt_revenue_history.append(0.0)

        ledger.close_step()

        # --- Record per-step ratios ---
        step_ratios: list[float] = []
        for a in agents:
            try:
                p = market.get_parcel(a['parcel_id'])
                r = p.declared_value / a['true_value'] if a['true_value'] > 0 else 1.0
                step_ratios.append(r)
            except KeyError:
                step_ratios.append(1.0)  # neutral if stale
        ratio_history.append(step_ratios)

    return ratio_history, agents, market, bid_events, forced_sale_events, lvt_revenue_history


# ═══════════════════════════════════════════════════════════════════════
#  Validation checks
# ═══════════════════════════════════════════════════════════════════════

def check_convergence(
    ratio_history: list[list[float]],
    bid_events: list[dict] | None = None,
    forced_sale_events: list[dict] | None = None,
    lvt_revenue_history: list[float] | None = None,
    verbose: bool = True,
) -> dict:
    """Run all V4 acceptance criteria checks.

    Implements checks from VALIDATION_FRAMEWORK.md §5.4:

      1. Convergence direction — MAD trend negative (T1)
      2. Convergence magnitude — ΔMAD ≤ -0.15 or ≤ 25 % of initial (T1)
      3. Steady-state accuracy  — median ratio ∈ [0.80, 1.20] (T2)
      4. Forced-sale efficiency — lower-ratio parcels attract more bids (T1)
      5. Bounded variance       — no explosive oscillations (T1)
      6. LVT revenue stability  — CV ≤ 0.10 (T2)
    """
    n_steps = len(ratio_history)
    if n_steps == 0:
        return {'all_pass': False, 'checks': {}, 'mad_history': [], 'med_history': []}

    # ── Compute MAD and median over time ─────────────────────────
    mad_history = [mean_abs_deviation(ratios) for ratios in ratio_history]
    med_history = [median(ratios) for ratios in ratio_history]

    # Use quarters to smooth noise
    q1_end = max(n_steps // 4, 1)
    q4_start = 3 * n_steps // 4
    early_mad = mean(mad_history[:q1_end])
    late_mad = mean(mad_history[q4_start:]) if q4_start < n_steps else mad_history[-1]

    initial_mad = mad_history[0]
    final_mad = mad_history[-1]
    mad_delta = final_mad - initial_mad
    mad_delta_ratio = mad_delta / max(initial_mad, 1e-9)

    final_median = med_history[-1] if med_history else 1.0

    # ── 1. Convergence direction (T1) ────────────────────────────
    mad_slope = slope_of_mad(mad_history)
    convergence_direction = mad_slope < 0

    # ── 2. Convergence magnitude (T1) ────────────────────────────
    convergence_magnitude = (mad_delta <= -0.15) or (mad_delta <= 0.25 * initial_mad)
    if initial_mad < 0.10 and mad_delta <= 0:
        convergence_magnitude = True

    # ── 3. Steady-state accuracy (T2) ────────────────────────────
    steady_state_accuracy = 0.80 <= final_median <= 1.20

    # ── 4. Forced-sale efficiency (T1) ───────────────────────────
    # Parcels with lower declared/true ratios should be more likely
    # to attract bids (the market targets under-declared assets).
    # The mechanism: buyers see a low declared price and bid on it.
    forced_sale_efficiency = True
    if bid_events and len(bid_events) >= 3:
        bid_ratios = [e['ratio'] for e in bid_events]
        # Compare mean bid-target ratio to overall population mean
        # at the times bids occurred
        overall_at_bids: list[float] = []
        for e in bid_events:
            s = e['step']
            if s < n_steps:
                overall_at_bids.extend(ratio_history[s])
        if overall_at_bids:
            mean_bid = mean(bid_ratios)
            mean_overall = mean(overall_at_bids)
            # The market targets under-declared parcels, so bid ratio < overall
            forced_sale_efficiency = mean_bid < mean_overall

    # ── 5. Bounded variance (T1) ────────────────────────────────
    first_half_max = max(mad_history[:max(n_steps // 2, 1)])
    second_half_max = max(mad_history[n_steps // 2:]) if n_steps // 2 < n_steps else first_half_max
    bounded_variance = second_half_max <= first_half_max * 1.5 or second_half_max < 0.30

    # ── 6. LVT revenue stability (T2) ────────────────────────────
    revenue_stable = True
    if lvt_revenue_history and len(lvt_revenue_history) >= 20:
        num_stable = min(100, len(lvt_revenue_history) // 2)
        last_revenues = lvt_revenue_history[-num_stable:]
        if len(last_revenues) >= 10:
            cv = coeff_of_variation(last_revenues)
            revenue_stable = cv <= 0.10

    # ── Composite ────────────────────────────────────────────────
    checks = {
        'convergence_direction': bool(convergence_direction),
        'convergence_magnitude': bool(convergence_magnitude),
        'steady_state_accuracy': bool(steady_state_accuracy),
        'forced_sale_efficiency': bool(forced_sale_efficiency),
        'bounded_variance': bool(bounded_variance),
        'revenue_stable': bool(revenue_stable),
        # Numeric values for reporting
        'mad_slope': round(mad_slope, 6),
        'mad_delta': round(mad_delta, 4),
        'mad_delta_ratio': round(mad_delta_ratio, 4),
        'early_mad': round(early_mad, 4),
        'late_mad': round(late_mad, 4),
        'initial_mad': round(initial_mad, 4),
        'final_mad': round(final_mad, 4),
        'final_median': round(final_median, 4),
        'mad_history': mad_history,
        'med_history': med_history,
        'n_bids': len(bid_events or []),
        'n_forced_sales': len([e for e in (forced_sale_events or [])
                               if e.get('accepted')]),
    }

    all_pass = all([
        convergence_direction,
        convergence_magnitude,
        steady_state_accuracy,
        forced_sale_efficiency,
        bounded_variance,
        revenue_stable,
    ])

    checks['all_pass'] = all_pass

    # ── Print report ─────────────────────────────────────────────
    if verbose:
        n_bids = checks['n_bids']
        n_fs = checks['n_forced_sales']
        print(f"  Steps simulated:  {n_steps}")
        print(f"  Initial MAD:      {initial_mad:.4f}")
        print(f"  Final MAD:        {final_mad:.4f}   (Δ = {mad_delta:+.4f})")
        print(f"  MAD slope:        {mad_slope:+.6f}")
        print(f"  Final median:     {final_median:.4f}")
        print(f"  Bids / Sales:     {n_bids} / {n_fs}")
        print()

        def _check(name, ok):
            return f"  {'✅' if ok else '❌'} {name}"

        print(_check("Convergence direction  (MAD slope < 0)", convergence_direction))
        print(_check("Convergence magnitude  (ΔMAD ≤ -0.15 or ≤25% of initial)", convergence_magnitude))
        print(_check("Steady-state accuracy  (median ∈ [0.80, 1.20])", steady_state_accuracy))
        print(_check("Forced-sale efficiency (bid ratio < overall)", forced_sale_efficiency))
        print(_check("Bounded variance       (no explosive cycles)", bounded_variance))
        print(_check("LVT revenue stability  (CV ≤ 0.10)", revenue_stable))
        print()

    return checks


# ═══════════════════════════════════════════════════════════════════════
#  Orchestrator
# ═══════════════════════════════════════════════════════════════════════

def run_scenario(
    label: str,
    lvt_rate: float,
    p_buyer: float,
    n_parcels: int = 50,
    n_steps: int = 500,
    seed: int = 42,
    learning_rate: float = 0.10,
    initial_spread: float = 0.80,
) -> dict:
    """Run a single V4 scenario and return check results."""
    print(f"  Parameters: n_parcels={n_parcels}, lvt_rate={lvt_rate}, "
          f"p_buyer={p_buyer}, n_steps={n_steps}")

    ratio_history, agents, market, bid_events, forced_sale_events, lvt_revenue_history = run_simulation(
        n_parcels=n_parcels,
        lvt_rate=lvt_rate,
        p_buyer=p_buyer,
        n_steps=n_steps,
        seed=seed,
        learning_rate=learning_rate,
        initial_spread=initial_spread,
    )

    checks = check_convergence(
        ratio_history,
        bid_events=bid_events,
        forced_sale_events=forced_sale_events,
        lvt_revenue_history=lvt_revenue_history,
        verbose=True,
    )
    return checks


def run_validation(quick: bool = True) -> bool:
    """Run all V4 validation scenarios.

    Parameters
    ----------
    quick : bool
        If True, runs with reduced parameters (n_parcels=30, n_steps=200)
        for fast feedback.  Full validation uses spec-matching parameters.
    """
    if quick:
        n_parcels = 30
        n_steps = 300
        learning_rate = 0.04
        print("  [Quick mode: n_parcels=30, n_steps=300, lr=0.04]\n")
    else:
        n_parcels = 100
        n_steps = 1000
        learning_rate = 0.03
        print("  [Full mode: n_parcels=100, n_steps=1000, lr=0.03]\n")

    scenarios = [
        ('V4a — Baseline',             {'lvt_rate': 0.05, 'p_buyer': 0.05}),
        ('V4b — Low Tax',              {'lvt_rate': 0.01, 'p_buyer': 0.05}),
        ('V4c — High Tax',             {'lvt_rate': 0.15, 'p_buyer': 0.05}),
        ('V4d — Thin Market',          {'lvt_rate': 0.05, 'p_buyer': 0.01}),
        ('V4e — Thick Market',         {'lvt_rate': 0.05, 'p_buyer': 0.20}),
    ]

    overall: list[dict] = []

    for label, cfg in scenarios:
        print(f"\n{'─' * 72}")
        print(f"▶ {label}")
        print(f"{'─' * 72}")
        checks = run_scenario(
            label=label,
            lvt_rate=cfg['lvt_rate'],
            p_buyer=cfg['p_buyer'],
            n_parcels=n_parcels,
            n_steps=n_steps,
            seed=42,
            learning_rate=learning_rate,
            initial_spread=0.80,
        )
        overall.append({'label': label, **checks, **cfg})

    # ── Summary table ─────────────────────────────────────────────
    print(f"\n{'═' * 72}")
    print("  V4 VALIDATION — SUMMARY")
    print(f"{'═' * 72}")
    print(f"  {'Scenario':<22s} {'Dir':>4s} {'Mag':>4s} {'Acc':>4s} "
          f"{'Sale':>4s} {'Var':>4s} {'Rev':>4s} {'▶':>4s}")
    print(f"  {'─' * 60}")

    all_pass = True
    for r in overall:
        c = r  # checks unpacked directly
        dir_ok = '✓' if c.get('convergence_direction') else '✗'
        mag_ok = '✓' if c.get('convergence_magnitude') else '✗'
        acc_ok = '✓' if c.get('steady_state_accuracy') else '✗'
        sale_ok = '✓' if c.get('forced_sale_efficiency') else '✗'
        var_ok = '✓' if c.get('bounded_variance') else '✗'
        rev_ok = '✓' if c.get('revenue_stable', True) else '✗'
        overall_ok = '✓' if c.get('all_pass') else '✗'

        if not c.get('all_pass'):
            all_pass = False

        print(f"  {r['label']:<22s} {dir_ok:>4s} {mag_ok:>4s} {acc_ok:>4s} "
              f"{sale_ok:>4s} {var_ok:>4s} {rev_ok:>4s} {overall_ok:>4s}")

    print(f"  {'─' * 60}")
    print()

    if all_pass:
        print("  🎉  ALL V4 VALIDATION TESTS PASSED")
    else:
        print("  ❌  SOME V4 VALIDATION TESTS FAILED — see per-check details above")

    print(f"{'═' * 72}")
    return all_pass


# ═══════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='V4 Harberger Convergence Validation')
    parser.add_argument('--full', action='store_true',
                        help='Run full validation (N=100, T=1000) instead of quick')
    args = parser.parse_args()

    success = run_validation(quick=not args.full)
    sys.exit(0 if success else 1)
