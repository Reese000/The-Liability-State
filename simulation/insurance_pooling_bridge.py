"""insurance_pooling_bridge.py — Community-rated insurance pooling.

Adds pooled (community-rated) insurance as an alternative to risk-based pricing.
Charges every worker the same premium based on the population mean risk,
creating cross-subsidisation from low-risk to high-risk workers.

Key difference from risk-based pricing (existing, src/mechanics/insurance.py):
  Risk-based premium = base_rate * individual_risk * coverage * loading factor
  Pooled premium     = mean(population_risks) * loading * coverage / 12
                        (everyone pays the same rate)

Exports:
    setup_pooled_insurance(workers, ledger, loading=1.2) -> dict
        Charges all workers the pooled premium. Returns policy status per worker.

    process_claims_pooled(workers, ledger, mutual_pool, rng, step,
                          claim_prob_mult=0.3) -> (pool_after, total_claims)
        Processes stochastic claims from the pooled fund.

    get_pooled_premium(workers, loading=1.2, coverage_limit=50000.0) -> float
        Utility to compute the raw pooled premium amount.

    risk_based_premium(risk, base_rate=0.05, loading=1.3,
                       coverage_limit=50000.0) -> float
        Utility to compute what a worker *would* pay under risk-based pricing,
        for comparison.

    verify_formula_consistency(loading=1.2) -> dict
        Cross-checks this module's formulas against InsuranceMarket.price_policy.

References:
    Spec: liability_state/simulation/src/mechanics/insurance.py
    Spec: liability_state/simulation/comparison_batch.py (mutualist runner)
"""

from __future__ import annotations

import logging
import os
import sys

# Allow direct import when running from the simulation directory
SIM_DIR = os.path.dirname(os.path.abspath(__file__))
if SIM_DIR not in sys.path:
    sys.path.insert(0, SIM_DIR)

from src.core.ledger import LedgerEngine, EntityType

# Module-level logger
_log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════════════

DEFAULT_COVERAGE_LIMIT = 50_000.0      # Standard coverage per policy ($)
PREMIUM_CAP_RATIO = 0.15               # Max premium as fraction of worker cash
POOL_EXHAUSTION_RATIO = 0.9            # Fraction of remaining pool paid when exhausted
CLAIM_MIN = 500.0                      # Minimum claim amount ($)
CLAIM_MAX = 15_000.0                   # Maximum claim amount ($)
DEFAULT_POOL_ENTITY = 'pool'           # Ledger entity ID for the pooled fund
DEFAULT_MECHANISM_PREM = 'pool_premium'
DEFAULT_MECHANISM_CLAIM = 'pool_claim'

# ═══════════════════════════════════════════════════════════════════════
#  Input validation helpers
# ═══════════════════════════════════════════════════════════════════════


def _validate_numeric(
    value: float,
    name: str,
    *,
    lo: float = 0.0,
    hi: float | None = None,
    lo_inclusive: bool = True,
) -> None:
    """Validate a numeric parameter is within expected bounds.

    Raises ValueError with a descriptive message on failure.
    """
    if lo_inclusive:
        if value < lo:
            raise ValueError(
                f"{name} must be >= {lo}, got {value}"
            )
    else:
        if value <= lo:
            raise ValueError(
                f"{name} must be > {lo}, got {value}"
            )
    if hi is not None and value > hi:
        raise ValueError(
            f"{name} must be <= {hi}, got {value}"
        )


def _validate_worker_dicts(workers: list[dict]) -> None:
    """Validate that all worker dicts have required keys and valid risks."""
    required_keys = ('id', 'risk', 'cash')
    for i, w in enumerate(workers):
        for key in required_keys:
            if key not in w:
                raise ValueError(
                    f"Worker {i} dict missing required key {key!r}: {w}"
                )
        if not isinstance(w['risk'], (int, float)):
            raise TypeError(
                f"Worker {i} 'risk' must be numeric, got {type(w['risk'])}"
            )
        if not (0.0 <= w['risk'] <= 1.0):
            raise ValueError(
                f"Worker {i} 'risk' must be in [0, 1], got {w['risk']}"
            )


# ═══════════════════════════════════════════════════════════════════════
#  Utility formulas
# ═══════════════════════════════════════════════════════════════════════


def get_pooled_premium(
    workers: list[dict],
    loading: float = 1.2,
    coverage_limit: float = DEFAULT_COVERAGE_LIMIT,
) -> float:
    """Compute the community-rated pooled premium.

    Formula (per the spec):
        pooled_premium = mean(worker_risks) * loading * coverage_limit / 12

    Parameters
    ----------
    workers : list[dict]
        Worker dicts with 'risk' keys.
    loading : float
        Loading multiplier (> 0). Default 1.2.
    coverage_limit : float
        Annual coverage amount. Default $50,000.

    Returns
    -------
    float
        The identical premium charged to every worker.
        Returns 0.0 if workers is empty or all risks are 0.
    """
    # Validate inputs
    _validate_numeric(loading, 'loading', lo=0.0, lo_inclusive=False)
    _validate_numeric(coverage_limit, 'coverage_limit', lo=0.0, lo_inclusive=False)

    if not workers:
        _log.warning("get_pooled_premium called with empty workers list")
        return 0.0

    _validate_worker_dicts(workers)

    risks = [w['risk'] for w in workers]
    mean_risk = sum(risks) / len(risks)

    if mean_risk <= 0.0:
        _log.warning(
            "All workers have zero risk; pooled premium is 0.0"
        )

    return mean_risk * loading * coverage_limit / 12.0


def risk_based_premium(
    risk: float,
    base_rate: float = 0.05,
    loading: float = 1.3,
    coverage_limit: float = 50_000.0,
) -> float:
    """Compute what a worker *would* pay under individual risk-based pricing.

    Uses the same formula as ``InsuranceMarket.price_policy`` from
    ``src/mechanics/insurance.py``:
        premium = base_rate * risk * coverage_limit * loading_factor

    Parameters
    ----------
    risk : float
        Individual risk probability in [0, 1].
    base_rate : float
        Base rate applied to risk. Default 0.05.
    loading : float
        Loading factor. Default 1.3.
    coverage_limit : float
        Annual coverage amount. Default $50,000.

    Returns
    -------
    float
        Actuarially fair premium for this individual (with loading).
    """
    _validate_numeric(risk, 'risk', lo=0.0, hi=1.0)
    _validate_numeric(base_rate, 'base_rate', lo=0.0, lo_inclusive=False)
    _validate_numeric(loading, 'loading', lo=0.0, lo_inclusive=False)
    _validate_numeric(coverage_limit, 'coverage_limit', lo=0.0, lo_inclusive=False)

    return base_rate * risk * coverage_limit * loading


def verify_formula_consistency(
    loading: float = 1.2,
) -> dict:
    """Cross-check this module's risk-based formula against the real
    ``InsuranceMarket.price_policy``.

    This is a runtime verification that the formulas stay in sync if
    ``InsuranceMarket`` ever changes.

    Returns
    -------
    dict
        {'consistent': bool, 'differences': list[dict], 'samples': list[dict]}
    """
    from src.mechanics.insurance import InsuranceMarket

    ledger = LedgerEngine(step_log=False)
    ledger.register_entity('sys', EntityType.SYSTEM, initial_cash=1_000_000)

    # Create an InsuranceMarket with default params
    market = InsuranceMarket(ledger, base_rate=0.05, loading_factor=loading)
    market.register_insurer('verifier', initial_capital=100_000)
    market.register_agent('t_agent', true_risk=0.05, initial_cash=50_000)

    test_risks = [0.01, 0.05, 0.10, 0.15, 0.22]

    differences = []
    samples = []

    for risk in test_risks:
        # Our formula
        our_prem = risk_based_premium(
            risk, base_rate=0.05, loading=loading, coverage_limit=50_000,
        )

        # InsuranceMarket price_policy (need to register an agent with this risk)
        market.register_agent(f'agent_{int(risk*100)}', true_risk=risk, initial_cash=50_000)
        market_prem = market.price_policy(
            'verifier', f'agent_{int(risk*100)}', coverage_limit=50_000,
        )

        diff = abs(our_prem - market_prem)
        match = diff < 0.01

        samples.append({
            'risk': risk,
            'our_formula': round(our_prem, 4),
            'market_price_policy': round(market_prem, 4),
            'diff': round(diff, 6),
            'match': match,
        })

        if not match:
            differences.append({
                'risk': risk,
                'our_formula': round(our_prem, 4),
                'market_price_policy': round(market_prem, 4),
                'diff': round(diff, 6),
            })

    result = {
        'consistent': len(differences) == 0,
        'differences': differences,
        'samples': samples,
    }

    if not result['consistent']:
        _log.error(
            "Formula mismatch detected! %d/%d test cases differ.",
            len(differences), len(test_risks),
        )
    else:
        _log.info(
            "Formula verification passed: %d/%d test cases match.",
            len(samples) - len(differences), len(samples),
        )

    return result


# ═══════════════════════════════════════════════════════════════════════
#  Setup — charge all workers the pooled premium
# ═══════════════════════════════════════════════════════════════════════


def setup_pooled_insurance(
    workers: list[dict],
    ledger: LedgerEngine,
    loading: float = 1.2,
    coverage_limit: float = DEFAULT_COVERAGE_LIMIT,
    pool_entity_id: str = DEFAULT_POOL_ENTITY,
    mechanism: str = DEFAULT_MECHANISM_PREM,
) -> dict[str, dict]:
    """Set up community-rated (pooled) insurance for all workers.

    Charges every worker the **same** premium:
        pooled_premium = mean(worker_risks) * loading * coverage_limit / 12

    Low-risk workers subsidise high-risk workers by design.

    Parameters
    ----------
    workers : list[dict]
        Worker dicts. Each must have 'id' (str), 'risk' (float 0-1),
        and 'cash' (float).
    ledger : LedgerEngine
        Core accounting engine. Workers must already be registered as
        CITIZEN entities.
    loading : float
        Loading factor (>1.0 adds buffer for expenses/pool volatility).
        Default 1.2.
    coverage_limit : float
        Standard coverage amount per policy. Default $50,000.
    pool_entity_id : str
        Ledger entity that holds the pooled premiums. Created if it
        does not exist.
    mechanism : str
        Mechanism label recorded on ledger transfers.

    Returns
    -------
    dict[str, dict]
        Mapping of worker_id -> {
            'premium': float (the pooled premium amount),
            'paid': bool (True if transfer succeeded),
            'active': bool (True if worker is insured = premium paid),
        }

    Raises
    ------
    ValueError
        If any worker dict is missing required keys.
    """
    if not workers:
        _log.warning("setup_pooled_insurance called with empty workers list")
        return {}

    # Validate worker dicts
    _validate_worker_dicts(workers)

    # Compute the pooled premium (same for everyone)
    pooled_premium = get_pooled_premium(workers, loading, coverage_limit)

    _log.info(
        "Setting up pooled insurance for %d workers: "
        "mean_risk=%.4f, pooled_premium=%.2f, loading=%.2f, coverage=%.0f",
        len(workers),
        sum(w['risk'] for w in workers) / len(workers),
        pooled_premium,
        loading,
        coverage_limit,
    )

    # Ensure pool entity exists in the ledger
    if not ledger.entity_exists(pool_entity_id):
        _log.info("Registering pool entity %r in ledger", pool_entity_id)
        ledger.register_entity(pool_entity_id, EntityType.TRUST)

    results: dict[str, dict] = {}
    for w in workers:
        wid = w['id']
        premium = pooled_premium

        # Affordability check: premium must not exceed cap_ratio of cash.
        # Use the LIVE ledger balance as the authoritative source of cash.
        try:
            cash = ledger.balances[wid].cash
        except KeyError:
            _log.warning(
                "Worker %r not found in ledger; falling back to dict 'cash' "
                "value (may be stale)",
                wid,
            )
            cash = w.get('cash', 0.0)

        can_afford = premium <= cash * PREMIUM_CAP_RATIO

        paid = False
        if premium <= 0.0:
            _log.warning(
                "Worker %r: premium is zero or negative (%.4f), skipping transfer",
                wid, premium,
            )
        elif not can_afford:
            _log.info(
                "Worker %r: cannot afford pooled premium $%.2f "
                "(cash=$%.2f, cap=%.2f)",
                wid, premium, cash, cash * PREMIUM_CAP_RATIO,
            )
        else:
            try:
                ledger.transfer(
                    wid,
                    pool_entity_id,
                    mechanism,
                    premium,
                    description=f"Pooled insurance premium for {wid}",
                )
                paid = True
                _log.debug(
                    "Worker %r paid pooled premium $%.2f (cash before: $%.2f)",
                    wid, premium, cash,
                )
            except (ValueError, KeyError) as exc:
                _log.error(
                    "Ledger transfer failed for worker %r premium $%.2f: %s",
                    wid, premium, exc,
                )

        results[wid] = {
            'premium': round(premium, 4),
            'paid': paid,
            'active': paid,  # active iff premium was paid
        }

    # Log summary
    active_count = sum(1 for s in results.values() if s['active'])
    total_collected = sum(s['premium'] for s in results.values() if s['paid'])
    _log.info(
        "Pooled insurance setup complete: %d/%d active, $%.2f collected",
        active_count, len(workers), total_collected,
    )

    return results


# ═══════════════════════════════════════════════════════════════════════
#  Claims processing
# ═══════════════════════════════════════════════════════════════════════


def process_claims_pooled(
    workers: list[dict],
    ledger: LedgerEngine,
    mutual_pool: float,
    rng,
    step: int,
    claim_prob_mult: float = 0.3,
    coverage_limit: float = DEFAULT_COVERAGE_LIMIT,
    pool_entity_id: str = DEFAULT_POOL_ENTITY,
    mechanism: str = DEFAULT_MECHANISM_CLAIM,
    policy_status: dict[str, dict] | None = None,
) -> tuple[float, float]:
    """Process stochastic claims against the pooled insurance fund.

    Each actively-insured worker faces accident probability:
        P(accident) = worker['risk'] * claim_prob_mult

    When an accident occurs, a claim between CLAIM_MIN and CLAIM_MAX is
    generated (capped at *coverage_limit*). The claim is paid from the
    pool. If the pool is exhausted, a partial payment is made.

    Parameters
    ----------
    workers : list[dict]
        Worker dicts with 'id' and 'risk' keys.
    ledger : LedgerEngine
        Core accounting engine.
    mutual_pool : float
        Current cash balance of the pooled fund (tracked as a float
        variable by the caller, not via the ledger entity).
    rng : numpy.random.RandomState
        Seeded RNG for deterministic accident and claim generation.
    step : int
        Current simulation step (for ledger transfers).
    claim_prob_mult : float
        Multiplier converting risk to monthly accident probability.
        Default 0.3 (matches mutualist model).
    coverage_limit : float
        Maximum single claim payout.
    pool_entity_id : str
        Ledger entity that holds the pooled premiums.
    mechanism : str
        Mechanism label recorded on ledger transfers.
    policy_status : dict[str, dict] | None
        Output from setup_pooled_insurance(). If provided, only workers
        with policy_status[wid]['active'] == True can file claims.

    Returns
    -------
    tuple[float, float]
        (pool_balance_after_claims, total_claims_paid)
    """
    total_claims = 0.0
    pool = mutual_pool
    pool_exhausted = False

    # Optional consistency check: compare tracked pool float with ledger entity cash
    try:
        ledger_cash = ledger.balances.get(pool_entity_id, None)
        if ledger_cash is not None:
            diff = abs(pool - ledger_cash.cash)
            if diff > 0.01:
                _log.warning(
                    "Pool float ($%.2f) differs from ledger entity '%s' cash "
                    "($%.2f) by $%.2f — caller should reconcile",
                    pool, pool_entity_id, ledger_cash.cash, diff,
                )
    except Exception as exc:
        _log.debug("Could not verify pool entity balance: %s", exc)

    for w in workers:
        wid = w['id']

        # Skip if not actively insured
        if policy_status is not None:
            info = policy_status.get(wid, {})
            if not info.get('active', False):
                _log.debug("Worker %r skipped (no active policy)", wid)
                continue

        # Accident probability
        accident_prob = w['risk'] * claim_prob_mult
        if rng.random() < accident_prob:
            # Generate claim amount
            claim = rng.uniform(CLAIM_MIN, min(CLAIM_MAX, coverage_limit))
            claim = min(claim, coverage_limit)

            if pool >= claim:
                # Full payment
                try:
                    ledger.transfer(
                        pool_entity_id,
                        wid,
                        mechanism,
                        claim,
                        description=f"Pooled claim payout to {wid}",
                    )
                    pool -= claim
                    total_claims += claim
                    _log.info(
                        "Worker %r: claim $%.2f paid in full "
                        "(pool before: $%.2f, pool after: $%.2f)",
                        wid, claim, pool + claim, pool,
                    )
                except (ValueError, KeyError) as exc:
                    _log.error(
                        "Claim payout to worker %r ($%.2f) failed: %s",
                        wid, claim, exc,
                    )
            elif pool > 0.0:
                # Partial payment — pool exhausted
                pool_exhausted = True
                partial = pool * POOL_EXHAUSTION_RATIO
                if partial > 0.0:
                    try:
                        ledger.transfer(
                            pool_entity_id,
                            wid,
                            mechanism,
                            partial,
                            description=(
                                f"Partial pooled claim payout to {wid}"
                                f" (pool exhausted)"
                            ),
                        )
                        pool -= partial
                        total_claims += partial
                        _log.warning(
                            "Worker %r: partial claim $%.2f (of $%.2f) "
                            "— pool exhausted, remaining: $%.2f",
                            wid, partial, claim, pool,
                        )
                    except (ValueError, KeyError) as exc:
                        _log.error(
                            "Partial claim payout to worker %r ($%.2f) failed: %s",
                            wid, partial, exc,
                        )
            else:
                _log.warning(
                    "Worker %r: accident but pool is empty (claim $%.2f unpaid)",
                    wid, claim,
                )

    if total_claims > 0:
        _log.info(
            "Claims round complete: $%.2f total claims paid, "
            "pool $%.2f remaining%s",
            total_claims, pool,
            " (exhausted)" if pool_exhausted else "",
        )

    return pool, total_claims


# ═══════════════════════════════════════════════════════════════════════
#  Demonstration / Self-test
# ═══════════════════════════════════════════════════════════════════════


def demo():
    """Run a self-contained test of pooled insurance.

    Creates a population of 5 workers with varying risk levels,
    sets up community-rated insurance, processes claims over several
    steps, verifies formula consistency against InsuranceMarket,
    and reports cross-subsidisation behaviour.
    """
    import numpy as np

    print("=" * 72)
    print("  INSURANCE POOLING BRIDGE — DEMONSTRATION")
    print("  Community-rated (pooled) vs. risk-based pricing")
    print("=" * 72)

    # ── 0. Formula consistency check ────────────────────────────
    print("\n  ── Formula Consistency Check (vs InsuranceMarket) ──")
    logging.basicConfig(level=logging.WARNING)
    vresult = verify_formula_consistency(loading=1.3)
    for s in vresult['samples']:
        label = "✓" if s['match'] else "✗"
        print(f"    {label} risk={s['risk']:.2f}: "
              f"our={s['our_formula']:>8.2f}  "
              f"InsuranceMarket={s['market_price_policy']:>8.2f}  "
              f"diff={s['diff']:.6f}")
    print(f"    → Consistent: {vresult['consistent']}")

    rng = np.random.RandomState(42)

    # ── 1. Create workers with varying risks ─────────────────────
    workers = [
        {'id': 'w000', 'risk': 0.01, 'cash': 50_000,
         'hourly': 25, 'monthly': 4_000, 'land': 100_000},
        {'id': 'w001', 'risk': 0.03, 'cash': 40_000,
         'hourly': 22, 'monthly': 3_520, 'land': 80_000},
        {'id': 'w002', 'risk': 0.08, 'cash': 30_000,
         'hourly': 18, 'monthly': 2_880, 'land': 60_000},
        {'id': 'w003', 'risk': 0.15, 'cash': 20_000,
         'hourly': 14, 'monthly': 2_240, 'land': 40_000},
        {'id': 'w004', 'risk': 0.22, 'cash': 10_000,
         'hourly': 12, 'monthly': 1_920, 'land': 35_000},
    ]

    mean_risk = sum(w['risk'] for w in workers) / len(workers)

    # ── 2. Create ledger and register entities ──────────────────
    ledger = LedgerEngine(step_log=False)
    ledger.register_entity('sys', EntityType.SYSTEM, initial_cash=500_000_000)
    for w in workers:
        ledger.register_entity(w['id'], EntityType.CITIZEN, initial_cash=w['cash'])

    # ── 3. Compute and display premium comparison ───────────────
    pooled_prem = get_pooled_premium(workers, loading=1.2)

    print(f"\n  Population mean risk: {mean_risk:.4f}")
    print(f"  Pooled premium (loading=1.2): ${pooled_prem:.2f}/month")
    print(f"  Coverage limit: $50,000")
    print()
    print(f"  {'Worker':<8} {'Risk':>6} {'Risk-based $':>12} {'Pooled $':>10} {'Difference $':>13} {'% of cash':>10}")
    print(f"  {'-'*8} {'-'*6} {'-'*12} {'-'*10} {'-'*13} {'-'*10}")

    for w in workers:
        rb = risk_based_premium(w['risk'])
        diff = pooled_prem - rb
        pct_cash = (pooled_prem / w['cash']) * 100 if w['cash'] > 0 else 0
        subsidy = "subsidises" if diff > 0 else "receives subsidy"
        print(f"  {w['id']:<8} {w['risk']:>6.2f} ${rb:>9,.2f}  ${pooled_prem:>7,.2f}  "
              f"${diff:>+10,.2f}  {pct_cash:>5.1f}%  ← {subsidy}")

    # ── 4. Set up pooled insurance ──────────────────────────────
    print(f"\n  {'─'*72}")
    ledger.begin_step()
    status = setup_pooled_insurance(workers, ledger, loading=1.2)
    ledger.close_step()

    total_premiums = sum(s['premium'] for s in status.values() if s['paid'])
    active_count = sum(1 for s in status.values() if s['active'])
    print(f"\n  Premiums collected: ${total_premiums:.2f} "
          f"({active_count}/{len(workers)} workers active)")

    for wid, info in status.items():
        risk = next(w['risk'] for w in workers if w['id'] == wid)
        print(f"    {wid}: risk={risk:.2f}  premium=${info['premium']:.2f}  "
              f"paid={info['paid']}  active={info['active']}")

    # Check ledger balances after premiums
    print(f"\n  Ledger balances after premium collection:")
    for w in workers:
        bs = ledger.balances[w['id']]
        change = bs.cash - w['cash']
        print(f"    {w['id']}: ${bs.cash:>8,.2f}  (change: ${change:>+8,.2f})")

    pool_entity_bs = ledger.balances.get('pool')
    if pool_entity_bs:
        print(f"    pool:  ${pool_entity_bs.cash:>8,.2f}")

    # ── 5. Run 12 months of claims ──────────────────────────────
    print(f"\n  {'─'*72}")
    print(f"  Running 12 months of pooled claims (seed=42, claim_prob_mult=0.3)")

    mutual_pool = total_premiums
    total_claims_all = 0.0
    total_claim_events = 0
    worker_claims: dict[str, float] = {w['id']: 0.0 for w in workers}

    for sim_step in range(1, 13):
        ledger.begin_step()
        current_ledger_step = ledger.step
        mutual_pool, step_claims = process_claims_pooled(
            workers, ledger, mutual_pool, rng, step=sim_step,
            claim_prob_mult=0.3, policy_status=status,
        )
        ledger.close_step()

        if step_claims > 0:
            total_claims_all += step_claims
            # Count which worker got the claim (check ledger transfers
            # at the current ledger step — calling begin_step above
            # incremented ledger.step, so transfers are recorded there)
            for t in ledger.transfers:
                if t.step == current_ledger_step and t.mechanism == 'pool_claim':
                    worker_claims[t.to_id] = worker_claims.get(t.to_id, 0.0) + t.amount
                    total_claim_events += 1

    print(f"\n  After 12 months:")
    print(f"    Total premiums collected: ${total_premiums:,.2f}")
    print(f"    Total claims paid:        ${total_claims_all:,.2f}")
    print(f"    Claim events:             {total_claim_events}")
    print(f"    Final pool balance:       ${mutual_pool:,.2f}")
    print(f"    Loss ratio:               "
          f"{total_claims_all / total_premiums * 100:.1f}%"
          if total_premiums > 0 else "    N/A (no premiums)")

    print(f"\n  Claims received by worker:")
    for wid, claim_total in sorted(worker_claims.items()):
        risk = next(w['risk'] for w in workers if w['id'] == wid)
        rb = risk_based_premium(risk) * 12  # annual risk-based cost
        pooled_annual = pooled_prem * 12
        print(f"    {wid} (risk={risk:.2f}): "
              f"received ${claim_total:>8,.2f} in claims  |  "
              f"risk-based annual: ${rb:>7,.2f}  |  "
              f"pooled annual: ${pooled_annual:>7,.2f}")

    # ── 6. Verify zero-sum invariant ─────────────────────────────
    print(f"\n  {'─'*72}")
    balanced = all(m['balanced'] for m in ledger.step_metrics)
    total_money = sum(bs.cash for bs in ledger.balances.values())
    print(f"  Zero-sum invariant holds across all steps: {balanced}")
    print(f"  Total money in system: ${total_money:,.2f}")

    # ── 7. Summary ──────────────────────────────────────────────
    print(f"\n  {'─'*72}")
    print(f"  CROSS-SUBSIDISATION SUMMARY")
    print(f"  {'─'*72}")
    print(f"  Under risk-based pricing, a low-risk worker (risk=0.01) "
          f"pays ${risk_based_premium(0.01):.0f}/mo")
    print(f"  Under risk-based pricing, a high-risk worker (risk=0.22) "
          f"pays ${risk_based_premium(0.22):.0f}/mo")
    print(f"  Under pooled pricing, EVERYONE pays ${pooled_prem:.0f}/mo")
    print(f"  → Low-risk workers subsidise high-risk workers by "
          f"${pooled_prem - risk_based_premium(0.01):.0f}/mo each")
    print(f"  → High-risk workers receive subsidy of "
          f"${risk_based_premium(0.22) - pooled_prem:.0f}/mo each")
    print(f"  {'='*72}")

    return status, mutual_pool, total_claims_all


# ═══════════════════════════════════════════════════════════════════════
#  Main — run demo when executed directly
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    demo()
