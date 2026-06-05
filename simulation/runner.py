#!/usr/bin/env python3
"""
runner.py — Long-run simulation runner for Phase 4 observation runs.

Creates a full economy with:
  20 workers, 5 businesses, 3 guilds, 2 insurers, 2 courts

Runs for 200 simulation steps. Each step executes the full economic cycle:
  Workers → Businesses → Guilds → Insurance → LVT → Dividends → Courts

Tracks aggregate metrics every 20 steps via the ledger with zero-sum check.
All financial flows go through the LedgerEngine for double-entry accounting.
"""

from __future__ import annotations

import os
import sys
import math
import random
import statistics
from collections import defaultdict
from typing import Any, Optional

# ── Ensure src/ is on the import path ──────────────────────────────
_src_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# ── Imports ─────────────────────────────────────────────────────────
from src.core.ledger import LedgerEngine, EntityType
from src.agents.worker import WorkerAgent
from src.agents.business import BusinessAgent
from src.agents.guild import GuildAgent
from src.mechanics.lvt import LVTEngine, TrustEngine, AllianceSkim
from src.mechanics.insurance import InsuranceMarket
from src.mechanics.harberger import HarbergerMarket
from src.mechanics.courts import (
    CourtSystem,
    Court,
    create_case,
    CaseStatus,
    Verdict,
)

# ── Event system ─────────────────────────────────────────────
from src.events.events import EventManager, build_schedule, DEFAULT_EVENT_SCHEDULE
from src.adversarial.controller import StrategyController


# ══════════════════════════════════════════════════════════════════════
#  Utility Functions
# ══════════════════════════════════════════════════════════════════════


def gini_coefficient(values: list[float]) -> float:
    """Calculate the Gini coefficient of a distribution.

    Handles negative values by working with absolute differences.
    Returns 0.0 for empty or single-element lists.
    The standard formula: G = (2*Σ(i*x_i) - (n+1)*Σ(x_i)) / (n*Σ(x_i))
    For negative values, uses relative mean absolute difference.
    """
    if len(values) < 2:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    # Use the relative mean absolute difference formula which handles negatives
    total = sum(sorted_vals)
    if total == 0:
        # All values zero = perfect equality
        return 0.0
    cumulative = 0.0
    for i, v in enumerate(sorted_vals, 1):
        cumulative += (2.0 * i - n - 1) * v
    # Gini = cumulative / (n * total)  -- works for positive total
    # For negative total, take absolute value for the denominator
    g = cumulative / (n * abs(total))
    # If total is negative, the sign flips; clamp to [0, 1]
    return max(0.0, min(1.0, abs(g)))


def compute_metrics(
    ledger: LedgerEngine,
    workers: list[WorkerAgent],
    businesses: list[BusinessAgent],
    guilds: list[GuildAgent],
    court_system: CourtSystem,
    insurance_market: InsuranceMarket,
    harberger_market: Optional['HarbergerMarket'] = None,
    step: int = 0,
    failed_businesses: Optional[set[str]] = None,
    distressed_workers: Optional[set[str]] = None,
) -> dict[str, Any]:
    """Compute all aggregate metrics at a given simulation step."""
    # ── Wealth aggregation ─────────────────────────────────────────
    worker_wealth = [ledger.get_balance(w.id).cash for w in workers]
    business_wealth = [b.cash + b.capital for b in businesses if b.alive]
    guild_cash = [g.cash for g in guilds]

    total_wealth = sum(worker_wealth) + sum(business_wealth) + sum(guild_cash)

    # Add insurer cash
    for ins_id in insurance_market.insurers:
        if ledger.entity_exists(ins_id):
            total_wealth += ledger.get_balance(ins_id).cash

    # Add court entity cash (if registered)
    for cid in court_system.courts:
        if ledger.entity_exists(cid):
            total_wealth += ledger.get_balance(cid).cash

    # Add system entity cash
    for sys_id in ["__system__", "system", "national_trust", "alliance"]:
        if ledger.entity_exists(sys_id):
            total_wealth += ledger.get_balance(sys_id).cash

    # ── Gini coefficient among workers ─────────────────────────────
    gini = gini_coefficient(worker_wealth)

    # ── Litigation rate ────────────────────────────────────────────
    total_filed = sum(
        c.metrics.total_cases_filed for c in court_system.courts.values()
    )
    total_population = len(workers) + len(businesses) + len(guilds) + 2 + 2
    litigation_rate = total_filed / max(1, total_population)

    # ── Premium-to-claim ratio (total over whole simulation) ───────
    total_premiums = ledger.get_total_flow("premium")
    total_claims = ledger.get_total_flow("claim")
    premium_claim_ratio = total_premiums / max(1.0, total_claims)

    # ── LVT revenue this step ──────────────────────────────────────
    lvt_this_step = ledger.get_total_flow("lvt", step=step)

    # ── Bankruptcy / failure rates ─────────────────────────────────
    total_biz = len(businesses)
    if failed_businesses is not None:
        biz_failures = len(failed_businesses)
    else:
        biz_failures = sum(1 for b in businesses if not b.alive)
    # Current (snapshot) bankruptcy rate: businesses currently dead
    currently_dead = sum(1 for b in businesses if not b.alive)
    snapshot_bankruptcy_rate = currently_dead / max(1, total_biz)
    # Cumulative failure rate: businesses that ever failed
    cumulative_failure_rate = biz_failures / max(1, total_biz)

    # ── Worker distress ─────────────────────────────────────────────
    if distressed_workers is not None:
        distressed_count = len(distressed_workers)
    else:
        distressed_count = sum(1 for w in workers if getattr(w, 'distressed', False))
    worker_distress_rate = distressed_count / max(1, len(workers))

    # ── Court case volume ──────────────────────────────────────────
    pending = sum(len(c.get_active_cases()) for c in court_system.courts.values())

    # ── Zero-sum check ─────────────────────────────────────────────
    all_balanced = True
    if ledger.step_metrics:
        last = ledger.step_metrics[-1]
        all_balanced = last.get("balanced", True)

    # ── Harberger market metrics ──────────────────────────────────
    if harberger_market is not None:
        total_declared = sum(
            p.declared_value for p in harberger_market.parcels.values()
        )
        total_assessed = sum(
            p.assessed_for_lvt for p in harberger_market.parcels.values()
        )
        active_bid_count = sum(
            len(p.active_bids) for p in harberger_market.parcels.values()
        )
        forced_sales = sum(
            1 for p in harberger_market.parcels.values()
            for b in p.bids if b.status.name == "ACCEPTED"
        )
        # Land ownership concentration: fraction of workers who own land
        worker_owners = sum(
            1 for pid, p in harberger_market.parcels.items()
            if any(w.id == p.owner for w in workers)
        )
    else:
        total_declared = 0.0
        total_assessed = 0.0
        active_bid_count = 0
        forced_sales = 0
        worker_owners = 0

    return {
        "step": step,
        "total_wealth": round(total_wealth, 2),
        "gini": round(gini, 4),
        "litigation_rate": round(litigation_rate, 4),
        "premium_claim_ratio": round(premium_claim_ratio, 4),
        "lvt_revenue": round(lvt_this_step, 2),
        "bankruptcy_rate": round(snapshot_bankruptcy_rate, 4),
        "cumulative_failure_rate": round(cumulative_failure_rate, 4),
        "business_failures": biz_failures,
        "worker_count": len(workers),
        "businesses_alive": total_biz - currently_dead,
        "distressed_workers": distressed_count,
        "worker_distress_rate": round(worker_distress_rate, 4),
        "guild_members": sum(g.active_member_count for g in guilds),
        "active_insurance_policies": sum(
            1 for r in insurance_market.policies.values() if r.is_active
        ),
        "court_cases_pending": pending,
        "total_cases_filed": total_filed,
        "all_balanced": all_balanced,
        "harberger_declared_value": round(total_declared, 2),
        "harberger_assessed_lvt": round(total_assessed, 2),
        "harberger_active_bids": active_bid_count,
        "harberger_forced_sales": forced_sales,
        "harberger_worker_owners": worker_owners,
    }


def print_metrics(m: dict[str, Any]) -> None:
    """Pretty-print a metrics dict."""
    print(f"  Wealth:           ${m['total_wealth']:>14,.2f}")
    print(f"  Gini:             {m['gini']:>14.4f}")
    print(f"  Litigation Rate:  {m['litigation_rate']:>14.4f}")
    print(f"  Premium/Claim:    {m['premium_claim_ratio']:>14.4f}")
    print(f"  LVT Revenue:      ${m['lvt_revenue']:>14,.2f}")
    print(f"  Bankruptcy Rate:  {m['bankruptcy_rate']:>14.4f}")
    print(f"  Cumul Fail Rate:  {m['cumulative_failure_rate']:>14.4f}")
    print(f"  Biz Failures:     {m['business_failures']:>14d}")
    print(f"  Bus Alive:        {m['businesses_alive']:>14d}")
    print(f"  Workers Distress: {m['distressed_workers']:>14d}")
    print(f"  Worker Dist Rate: {m['worker_distress_rate']:>14.4f}")
    print(f"  Guild Members:    {m['guild_members']:>14d}")
    print(f"  Active Policies:  {m['active_insurance_policies']:>14d}")
    print(f"  Court Cases Pend: {m['court_cases_pending']:>14d}")
    print(f"  Cases Filed Tot:  {m['total_cases_filed']:>14d}")
    # Harberger property market
    if m.get("harberger_declared_value", 0) > 0:
        print(f"  H Land Declared:  ${m['harberger_declared_value']:>14,.2f}")
        print(f"  H Land Assessed:  ${m['harberger_assessed_lvt']:>14,.2f}")
        print(f"  H Active Bids:    {m['harberger_active_bids']:>14d}")
        print(f"  H Forced Sales:   {m['harberger_forced_sales']:>14d}")
        print(f"  H Worker Owners:  {m['harberger_worker_owners']:>14d}")
    print(f"  All Balanced:     {'Yes' if m['all_balanced'] else '⚠ No'}")


# ══════════════════════════════════════════════════════════════════════
#  Main Setup & Simulation Loop
# ══════════════════════════════════════════════════════════════════════


def main() -> dict[str, Any]:
    """Run the full Phase 4 long-run simulation.

    Returns a dict with all agents, engines, and metrics history.
    """
    random.seed(42)

    STEPS = 200
    REPORT_INTERVAL = 20
    COMPACTS = ["compact_alpha", "compact_beta", "compact_gamma"]
    INSURERS = ["insurer_a", "insurer_b"]

    # ── Tuned parameters ──────────────────────────────────────────
    # These keep the economy stable over 200+ steps:
    LVT_RATE = 0.03               # 3% LVT (down from 5%)
    TRUST_SKIM_RATE = 0.10        # 10% alliance skim
    INS_BASE_RATE = 0.05          # Insurance base premium rate
    INS_LOADING = 1.30            # Insurance loading factor
    INS_AUDIT_PROB = 0.10        # Audit probability
    # Dynamic pricing & bankruptcy parameters
    INS_PREM_RAISE = 1.25         # Premium raise multiplier when losing money
    INS_PREM_LOWER = 1.20         # Premium lower divisor when overcapitalised
    INS_CONSEC_NEG = 3            # Consecutive negative steps before bankruptcy
    BIZ_BANKRUPTCY_CONSEC = 3     # Consecutive (cash<0 AND net_worth<0) before biz bankruptcy
    WORKER_DISTRESS_CONSEC = 5    # Consecutive (cash<0 AND no income) before worker distress

    print("=" * 82)
    print("  THE LIABILITY STATE — PHASE 4 LONG-RUN SIMULATION")
    print("=" * 82)
    print(f"  Economy: 20 workers, 5 businesses, 3 guilds,")
    print(f"           2 insurers, 2 courts")
    print(f"  Steps:   {STEPS}  |  Reports: every {REPORT_INTERVAL}")
    print(f"  LVT:     {LVT_RATE:.0%} | Skim: {TRUST_SKIM_RATE:.0%}")
    print("=" * 82)

    # ═════════════════════════════════════════════════════════════════
    #  SETUP
    # ═════════════════════════════════════════════════════════════════

    ledger = LedgerEngine(step_log=False)

    # ── 0. System entities ─────────────────────────────────────────
    # Two system entity IDs exist in the codebase:
    #   "__system__" (used by WorkerAgent.execute_labor)
    #   "system"     (used by BusinessAgent)
    ledger.register_entity("__system__", EntityType.SYSTEM, initial_cash=10_000_000.0)
    ledger.register_entity("system", EntityType.SYSTEM, initial_cash=10_000_000.0)
    ledger.register_entity("national_trust", EntityType.TRUST, initial_cash=0.0)
    ledger.register_entity("alliance", EntityType.ALLIANCE, initial_cash=0.0)

    # Compacts (for migration / compact tracking)
    for cid in COMPACTS:
        ledger.register_entity(cid, EntityType.COMPACT, initial_cash=0.0)

    # ── 1. Mechanics engines ──────────────────────────────────────
    lvt_engine = LVTEngine(ledger, rate=LVT_RATE)
    trust_engine = TrustEngine(ledger, skim_rate=TRUST_SKIM_RATE)
    alliance_skim = AllianceSkim(ledger)

    # ── 2. Insurance market ───────────────────────────────────────
    insurance_market = InsuranceMarket(
        ledger,
        audit_probability=INS_AUDIT_PROB,
        base_rate=INS_BASE_RATE,
        loading_factor=INS_LOADING,
        evasion_z_threshold=2.0,
        premium_raise_factor=INS_PREM_RAISE,
        premium_lower_factor=INS_PREM_LOWER,
        consecutive_negative_max=INS_CONSEC_NEG,
    )

    for ins_id in INSURERS:
        insurance_market.register_insurer(
            ins_id,
            initial_capital=(
                {"insurer_a": 200_000.0, "insurer_b": 150_000.0}[ins_id]
            ),
            num_pools=2,
        )

    # ── 3. Court system ──────────────────────────────────────────
    court_system = CourtSystem()

    court_a = Court(
        court_id="court_a",
        name="Swift Justice",
        filing_fee_rate=0.03,
        speed_factor=3.0,
        fairness_factor=0.80,
        bias=0.0,
        initial_reputation=0.5,
    )
    court_a.max_docket_size = 5

    court_b = Court(
        court_id="court_b",
        name="Themis Court",
        filing_fee_rate=0.04,
        speed_factor=4.0,
        fairness_factor=0.95,
        bias=0.0,
        initial_reputation=0.6,
    )
    court_b.max_docket_size = 5

    court_system.register_court(court_a)
    court_system.register_court(court_b)

    # Register court entities on ledger for cash tracking
    for cid in ["court_a", "court_b"]:
        if not ledger.entity_exists(cid):
            ledger.register_entity(cid, EntityType.COURT, initial_cash=5_000.0)

    # ── 4. Workers (20) ────────────────────────────────────────────
    # Lower land values relative to productivity so LVT is affordable.
    workers: list[WorkerAgent] = []
    for i in range(20):
        wid = f"worker_{i:03d}"
        # Productivity range: $10-20/hr
        productivity = random.uniform(10.0, 20.0)
        # Land value range: $0-20K (lower to keep LVT manageable)
        land_value = random.uniform(0.0, 20_000.0)
        w = WorkerAgent(
            wid,
            ledger,
            productivity=productivity,
            land_value=land_value,
            risk_profile=random.uniform(0.01, 0.25),
            honesty=random.betavariate(5.0, 2.0),
            inertia=random.uniform(0.1, 0.5),
            compact_id=random.choice(COMPACTS),
            initial_cash=random.uniform(3_000.0, 10_000.0),
        )
        workers.append(w)

    # ── 4b. Harberger property market setup ────────────────────────
    # Create Harberger market and register one parcel per worker.
    # Each worker self-assesses at their initial land_value, which
    # becomes the "true value" they may later deviate from.
    harberger_market = HarbergerMarket(
        ledger,
        lvt_rate=LVT_RATE,
    )
    for w in workers:
        bs = ledger.get_balance(w.id)
        initial_land = bs.land_value
        bs.land_value = 0.0  # reset — register_parcel adds it back
        # Dishonest workers initially under-declare; honest ones are truthful.
        # This creates the gap that drives dynamic adjustment and bidding.
        initial_declared = initial_land * (0.4 + 0.6 * w.honesty)
        harberger_market.register_parcel(
            parcel_id=f"land_{w.id}",
            owner=w.id,
            declared_value=initial_declared,
        )

    # Register workers with the insurance market (honest declarations)
    for w in workers:
        insurance_market.register_agent(
            agent_id=w.id,
            true_risk=w.risk_profile,
            declared_risk=w.risk_profile,  # honest
        )

    # ── 5. Businesses (5) ─────────────────────────────────────────
    # Smaller initial capital to prevent unbounded growth
    businesses: list[BusinessAgent] = []
    for i in range(5):
        bid = f"business_{i:03d}"
        b = BusinessAgent(
            bid,
            ledger,
            initial_cash=random.uniform(30_000.0, 80_000.0),
            initial_capital=random.uniform(30_000.0, 80_000.0),
            liability_exposure=random.uniform(0.03, 0.10),
            market_wage=15.0,
            tfp=random.uniform(0.80, 1.20),
            capital_share=random.uniform(0.25, 0.40),
            markup=random.uniform(1.10, 1.35),
        )
        # Cap max workers to prevent runaway hiring
        b.MAX_WORKERS = 40
        businesses.append(b)

    # ── 6. Guilds (3) ─────────────────────────────────────────────
    guild_configs: list[tuple[str, float, float, float, float]] = [
        ("guild_alpha", 0.01, 0.20, 1.08, 0.50),
        ("guild_beta",  0.015, 0.30, 1.12, 0.50),
        ("guild_gamma", 0.02, 0.40, 1.18, 0.50),
    ]
    guilds: list[GuildAgent] = []
    for gid, dues_rate, min_skill, prod_boost, mutual_frac in guild_configs:
        g = GuildAgent(
            gid,
            ledger,
            dues_rate=dues_rate,
            mutual_allocation_frac=mutual_frac,
            min_skill=min_skill,
            productivity_boost=prod_boost,
            testing_fee=5.0,
            benefit_rate=0.05,
            initial_cash=1_000.0,
        )
        guilds.append(g)

    # Assign workers to guilds (3 guilds × ~7 workers each)
    random.shuffle(workers)
    for i, w in enumerate(workers):
        guild = guilds[i % len(guilds)]
        # Normalise productivity to skill ∈ [0, 1] range
        skill = max(0.0, min(1.0, w.productivity / 25.0))
        try:
            guild.apply_for_membership(w.id, skill)
        except Exception:
            pass

    # ── 7. Compact-utility map (drives migration) ─────────────────
    compact_utilities: dict[str, float] = {
        "compact_alpha": 1.0,
        "compact_beta": 1.1,
        "compact_gamma": 0.9,
    }

    # ── Initial summary ─────────────────────────────────────────────
    print(f"\n  Created {len(workers):>2d} workers ({'|'.join(COMPACTS)})")
    print(f"  Created {len(businesses):>2d} businesses")
    print(f"  Created {len(guilds):>2d} guilds")
    guild_members_init = sum(g.active_member_count for g in guilds)
    print(f"  Guild members: {guild_members_init}")
    print(f"  Created 2 insurers, 2 courts")
    initial_money = sum(bs.cash for bs in ledger.balances.values())
    print(f"  Initial money in system: ${initial_money:>12,.2f}")

    # ── 8. Strategy Controller setup ──────────────────────────────
    # Tracks which adversarial strategy each agent is using.
    strategy_controller = StrategyController()
    agent_strategies: dict[str, str] = {}
    for w in workers:
        agent_strategies[w.id] = "honest"
    for b in businesses:
        agent_strategies[b.id] = "honest"
    print(f"  Strategy Controller: {len(strategy_controller.strategies)} strategies registered")
    print(f"  Tracking {len(agent_strategies)} agents (workers + businesses)")

    # ── 9. Event system setup ──────────────────────────────────────
    event_manager = build_schedule()
    print(f"  Event schedule: {len(event_manager.events)} events loaded")
    for es in event_manager.summary():
        print(f"    {es['type']:25s} '{es['name']}' @ step {es['trigger_step']:>3d}  "
              f"mag={es['magnitude']:.2f} dur={es['duration']} target={es['target']}")
    print(f"  (Modifiers: demand_multiplier, claim_freq_multiplier)")

    # ═════════════════════════════════════════════════════════════════
    #  SIMULATION LOOP
    # ═════════════════════════════════════════════════════════════════

    metrics_history: list[dict[str, Any]] = []
    step_claim_events: list[dict] = []   # Generated this step
    failed_businesses: set[str] = set()  # Track cumulative business failures
    distressed_workers: set[str] = set() # Track distressed workers

    for step_num in range(1, STEPS + 1):
        ledger.begin_step()

        # ── Phase 0a: Fire scheduled shock events ──────────────────
        event_context = {
            "ledger": ledger,
            "workers": workers,
            "businesses": businesses,
            "guilds": guilds,
            "court_system": court_system,
            "insurance_market": insurance_market,
            "harberger_market": harberger_market,
            "compact_utilities": compact_utilities,
        }
        event_logs = event_manager.fire_events(event_context, step_num)
        for msg in event_logs:
            print(f"  {msg}")

        # ── Phase 0: Adversarial Strategy Evaluation ──────────────
        # Evaluate all agents and determine if any switch strategies.
        all_agents = workers + businesses
        strategy_result = strategy_controller.step(all_agents)

        # Log strategy switches — only when the agent actually changes strategy.
        for sw in strategy_result["switches"]:
            old_strat = agent_strategies.get(sw["agent_id"], "honest")
            new_strat = sw["to_strategy"]
            if old_strat != new_strat:
                agent_strategies[sw["agent_id"]] = new_strat
                print(
                    f"  🎭 {sw['agent_id']} ({sw['agent_type']}, "
                    f"θ={sw['honesty']:.3f}) {old_strat} → {new_strat}"
                )

        # Apply strategy-specific behavior modifications per agent.
        # These modify agent parameters so the ensuing phases reflect
        # the adversarial strategy the agent chose.
        for w in workers:
            strat = agent_strategies.get(w.id, "honest")
            if strat == "premium_evasion":
                # Under-declare risk to reduce insurance premiums
                if w.id in insurance_market.agents:
                    declared = w.risk_profile * (0.3 + 0.2 * (1.0 - w.honesty))
                    insurance_market.agents[w.id]['declared_risk'] = max(0.01, min(declared, w.risk_profile))
            elif strat == "insurance_fraud":
                w._insurance_fraud_active = True
            else:
                w._insurance_fraud_active = False
                # Reset declared risk to true value if not evading
                if w.id in insurance_market.agents:
                    insurance_market.agents[w.id]['declared_risk'] = w.risk_profile

        for b in businesses:
            strat = agent_strategies.get(b.id, "honest")
            if strat == "collusion":
                # Store original markup on first activation
                if not getattr(b, '_collusion_ever_active', False):
                    b._original_markup = b.markup
                    b._collusion_ever_active = True
                b.markup = b._original_markup * 1.15  # 15% price increase
            else:
                # Restore honest markup if was colluding
                if getattr(b, '_collusion_ever_active', False):
                    b.markup = getattr(b, '_original_markup', b.markup)

        # Print strategy distribution summary every REPORT_INTERVAL
        if step_num % REPORT_INTERVAL == 0:
            strat_counts: dict[str, int] = {}
            for sid, sname in agent_strategies.items():
                strat_counts[sname] = strat_counts.get(sname, 0) + 1
            exploit_count = sum(v for k, v in strat_counts.items() if k != "honest")
            total_agents = len(agent_strategies)
            print(f"  📊 Strategy distribution @ step {step_num}:")
            for sname, count in sorted(strat_counts.items(), key=lambda x: -x[1]):
                pct = count / total_agents * 100
                print(f"      {sname:20s}: {count:2d}/{total_agents} ({pct:.0f}%)")
            print(f"      {'──'*20}")
            print(f"      {'Total exploiting':20s}: {exploit_count:2d}/{total_agents} ({exploit_count/total_agents*100:.0f}%)")

        # ── Phase 1: Workers — labour, insurance decisions ──────────
        # Dynamically build list of solvent (non-failed) insurers
        solvent_insurers = [
            iid for iid in INSURERS
            if not insurance_market.is_insurer_failed(iid)
        ]
        if not solvent_insurers:
            solvent_insurers = INSURERS[:]  # fallback (all failed — use any)

        for w in workers:
            sr = w.step(
                compact_utilities=compact_utilities,
                insurer_id=random.choice(solvent_insurers),
                insurance_coverage=5_000.0,
            )

            # If worker wants a new policy, purchase via insurance market
            if sr.get("wants_new_policy") and sr.get("wants_new_insurer"):
                # Only allow purchase from solvent insurers
                target = sr["wants_new_insurer"]
                if not insurance_market.is_insurer_failed(target):
                    try:
                        insurance_market.purchase_policy(
                            agent_id=w.id,
                            insurer_id=target,
                            coverage_limit=5_000.0,
                        )
                    except Exception:
                        pass

        # ── Worker distress tracking ────────────────────────────────
        for w in workers:
            if w.distressed:
                distressed_workers.add(w.id)

        # ── Phase 2: Businesses — full operations ──────────────────
        for b in businesses:
            if not b.alive:
                continue
            # Cycle market conditions
            market_wage = 15.0 + 3.0 * math.sin(step_num * 0.05)
            demand_factor = 1.0 + 0.2 * math.sin(step_num * 0.07 + 1.0)
            # Apply event modifiers (e.g. recession cuts demand)
            event_mods = event_manager.get_active_modifiers(step_num)
            if "demand_multiplier" in event_mods:
                demand_factor *= event_mods["demand_multiplier"]
            try:
                result = b.step(
                    market_wage=market_wage,
                    market_demand_factor=demand_factor,
                    available_insurers=solvent_insurers,
                )
                # Track accident events for court case generation
                if result.get("accident", {}).get("accident"):
                    step_claim_events.append({
                        "business_id": b.id,
                        "liability_cost": result["accident"].get("liability_cost", 0.0),
                        "out_of_pocket": result["accident"].get("out_of_pocket", 0.0),
                    })

                # File insurance claim through insurance market
                # (business already handles claim via ledger in handle_accident_risk,
                #  but we also file worker claims below via InsuranceMarket)
            except Exception:
                pass

            # Bankruptcy check — 3 consecutive steps with cash<0 AND net_worth<0
            if b.should_bankrupt:
                liq = b.liquidate()
                failed_businesses.add(b.id)
                print(
                    f"  🚨 BUSINESS BANKRUPTCY: {b.id} — "
                    f"capital liquidated=${liq['capital_liquidated']:,.2f}, "
                    f"workers laid off={liq['workers_laid_off']}, "
                    f"distributed=${liq['distributed_cash']:,.2f}"
                )

        # ── Phase 3: Guilds — dues & mutual benefits ───────────────
        for g in guilds:
            # Identify distressed members (cash below 200)
            distressed: list[str] = []
            for mid in list(g.members.keys()):
                try:
                    rec = g.members[mid]
                    if rec.is_active and ledger.entity_exists(mid):
                        bs = ledger.get_balance(mid)
                        if bs.cash < 200.0:
                            distressed.append(mid)
                except (KeyError, Exception):
                    pass

            try:
                g.step(distressed_members=distressed)
            except Exception:
                pass

        # ── Phase 4: Insurance market — audits, premiums, evasion ──
        try:
            ins_step_result = insurance_market.run_step()
            # Report dynamic pricing adjustments
            for adj in ins_step_result.get('pricing_adjustments', []):
                arrow = '↑' if adj['new_multiplier'] > adj['old_multiplier'] else '↓'
                print(
                    f"  📊 Insurance pricing: {adj['insurer_id']} "
                    f"multiplier {adj['old_multiplier']:.3f} → "
                    f"{adj['new_multiplier']:.3f} {arrow} "
                    f"({adj['reason']}, reserves=${adj['total_reserves']:.2f})"
                )
            # Report bankruptcies
            for bk in ins_step_result.get('bankruptcies', []):
                print(
                    f"  🚨 INSURER FAILED: {bk['insurer_id']} — "
                    f"{bk['reason']} (reserves=${bk['total_reserves']:.2f})"
                )
            # Report policy transfers
            for tr in ins_step_result.get('policy_transfers', []):
                print(
                    f"  🔄 Policy transfer: {tr['agent_id']} "
                    f"{tr['from_insurer']} → {tr['to_insurer']} "
                    f"({tr['status']})"
                )
        except Exception:
            pass

        # ── Phase 5: Worker claims via insurance market ────────────
        # Workers occasionally suffer random losses and file claims
        # Agents with insurance_fraud additionally file fabricated claims.
        # Get event modifiers for claim frequency (e.g. disaster, insurance stress)
        event_mods = event_manager.get_active_modifiers(step_num)
        claim_freq_mult = event_mods.get("claim_freq_multiplier", 1.0)

        for w in workers:
            base_claim_prob = w.risk_profile * 0.5 * claim_freq_mult
            if w.has_insurance and random.random() < base_claim_prob:
                claim_amount = random.uniform(100.0, 2_000.0)
                try:
                    insurance_market.file_claim(w.id, claim_amount)
                except Exception:
                    pass
            # Fraudulent claim: fabricate a loss that never occurred
            if getattr(w, '_insurance_fraud_active', False) and w.has_insurance:
                if random.random() < 0.08:  # ~8% chance per step
                    fraud_amount = random.uniform(500.0, 3_000.0)
                    try:
                        insurance_market.file_claim(w.id, fraud_amount)
                    except Exception:
                        pass

        # ── Phase 5b: Harberger property market ─────────────────────
        # Advance Harberger time (1 step = 1 day), then run:
        #   (i)   Self-assessment — owners adjust declared values
        #   (ii)  Bidding — under-declared parcels attract bids
        #   (iii) Sync — reconcile balance-sheet land values with
        #         Harberger assessed_for_lvt for LVTEngine
        harberger_market.advance_day()

        # 5b.i — Self-assessment: each parcel owner moves declared
        # value toward their true (initial) land value.  Learning rate
        # scales with honesty: honest owners converge faster, dishonest
        # ones lag and under-declare, inviting forced-sale bids.
        # Agents with harberger_gaming strategy deliberately push their
        # declared value farther below true value to reduce LVT.
        worker_ids_set = {w.id for w in workers}
        for pid, parcel in list(harberger_market.parcels.items()):
            ow = next((w for w in workers if w.id == parcel.owner), None)
            if ow is None:
                continue
            true_val = ow.land_value
            current_val = parcel.declared_value
            strat = agent_strategies.get(ow.id, "honest")
            if strat == "harberger_gaming":
                # Push declared value down (away from true value)
                # More dishonest agents push harder
                gaming_factor = 0.08 * (1.0 - ow.honesty)
                delta = (0.0 - current_val) * gaming_factor
                if abs(delta) > 1.0:
                    new_val = max(0.0, current_val + delta)
                    harberger_market.self_assess(pid, new_val)
            else:
                learning_rate = 0.08 * ow.honesty
                delta = (true_val - current_val) * learning_rate
                if abs(delta) > 1.0:
                    new_val = max(0.0, current_val + delta)
                    harberger_market.self_assess(pid, new_val)

        # 5b.ii — Bidding: other workers spot under-declared parcels
        # and place Harberger bids.  Owner randomly accepts (forced
        # sale) or free-refuses (bumps LVT basis to bid price).
        for pid, parcel in list(harberger_market.parcels.items()):
            ow = next((w for w in workers if w.id == parcel.owner), None)
            if ow is None:
                continue
            true_val = ow.land_value
            if true_val <= 0 or parcel.declared_value <= 0:
                continue
            gap = (true_val - parcel.declared_value) / max(true_val, 1.0)
            if gap <= 0.05:
                continue
            if random.random() > gap * 0.25:
                continue

            # Find a buyer who can afford the full bid price
            bid_price = parcel.declared_value
            potential = [
                x.id for x in workers
                if x.id != ow.id
                and ledger.get_balance(x.id).cash >= bid_price
            ]
            if not potential:
                continue
            random.shuffle(potential)
            buyer_id = potential[0]

            try:
                bid = harberger_market.post_bid(
                    pid, buyer_id, bid_price=bid_price,
                )
                # Owner flips a coin: accept (forced sale) or refuse
                if random.random() < 0.40:
                    harberger_market.accept_bid(pid, bid.bid_id)
                else:
                    # Free-window refusal bumps assessed_for_lvt
                    harberger_market.refuse_bid(pid, bid.bid_id)
            except Exception:
                pass

        # 5b.iii — Sync balance-sheet land values for LVTEngine.
        # Zero all workers first, then sum the assessed_for_lvt of
        # every parcel they own (handles multi-parcel ownership after
        # forced sales).
        for w in workers:
            ledger.get_balance(w.id).land_value = 0.0
        for parcel in harberger_market.parcels.values():
            if parcel.owner in worker_ids_set:
                ledger.get_balance(parcel.owner).land_value += (
                    parcel.assessed_for_lvt
                )

        # ── Phase 6: LVT collection ────────────────────────────────
        citizen_ids = [w.id for w in workers]
        compact_map = {w.id: w.compact_id for w in workers}
        lvt_results = lvt_engine.collect(citizen_ids)

        # Build compact contribution map
        compact_contributions: dict[str, float] = defaultdict(float)
        for cid, bill in lvt_results.items():
            comp = compact_map.get(cid, "")
            compact_contributions[comp] += bill

        total_lvt = sum(lvt_results.values())

        # ── Phase 7: Dividend distribution ────────────────────────
        dist_result = trust_engine.distribute(
            citizen_ids=citizen_ids,
            total_lvt=total_lvt,
            essential_costs=0.0,
            compact_contributions=dict(compact_contributions),
        )

        alliance_skim.record_skim(
            amount=dist_result["alliance_skim"],
            compact_contributions=dict(compact_contributions),
        )

        # ── Phase 8: Courts — new litigation & tick ────────────────
        # Generate lawsuits from business accidents
        for ev in step_claim_events:
            if random.random() < 0.30:  # 30% of accidents lead to lawsuits
                plaintiff = random.choice(workers).id
                claimed = ev["liability_cost"] * random.uniform(1.0, 3.0)
                case = create_case(
                    plaintiff=plaintiff,
                    defendant=ev["business_id"],
                    claimed_amount=max(100.0, claimed),
                    evidence_strength=random.uniform(0.30, 0.85),
                    defendant_due_care=1.0 - random.uniform(0.03, 0.10),
                    foreseeability=random.uniform(0.30, 0.80),
                    comparative_negligence=random.uniform(0.0, 0.20),
                    willful=random.random() < 0.10,
                    description=(
                        f"Accident liability: {ev['business_id']} "
                        f"${ev['liability_cost']:.2f}"
                    ),
                )
                court_system.route_case(case, step=step_num)

        # Random contract/wage disputes between workers and businesses
        if random.random() < 0.08:
            w1 = random.choice(workers)
            b1 = random.choice([b for b in businesses if b.alive])
            case = create_case(
                plaintiff=w1.id,
                defendant=b1.id,
                claimed_amount=random.uniform(200.0, 3_000.0),
                evidence_strength=random.uniform(0.25, 0.80),
                description=f"Wage dispute: {w1.id} v. {b1.id}",
            )
            court_system.route_case(case, step=step_num)

        # Court flooding: agents with this strategy file frivolous
        # low-merit lawsuits hoping for nuisance settlements.
        for w in workers:
            if agent_strategies.get(w.id, "honest") == "court_flooding" and w.cash > 5_000:
                if random.random() < 0.15:  # 15% chance per step
                    defendant = random.choice([b.id for b in businesses if b.alive] + [w2.id for w2 in workers if w2.id != w.id])
                    case = create_case(
                        plaintiff=w.id,
                        defendant=defendant,
                        claimed_amount=random.uniform(1_000.0, 5_000.0),
                        evidence_strength=random.uniform(0.10, 0.30),  # Low merit
                        description=f"Frivolous suit by {w.id} (court_flooding)",
                    )
                    court_system.route_case(case, step=step_num)
        for b in businesses:
            if agent_strategies.get(b.id, "honest") == "court_flooding" and b.cash > 10_000:
                if random.random() < 0.15:
                    defendant = random.choice([w2.id for w2 in workers] + [b2.id for b2 in businesses if b2.id != b.id and b2.alive])
                    case = create_case(
                        plaintiff=b.id,
                        defendant=defendant,
                        claimed_amount=random.uniform(2_000.0, 8_000.0),
                        evidence_strength=random.uniform(0.10, 0.30),
                        description=f"Frivolous suit by {b.id} (court_flooding)",
                    )
                    court_system.route_case(case, step=step_num)

        # Tick all courts — process pending cases
        court_system.tick(step_num)

        # ── Clear per-step tracking ─────────────────────────────────
        step_claim_events.clear()

        # ── Close step with zero-sum check ─────────────────────────
        step_metrics = ledger.close_step()

        if not step_metrics.get("balanced", True):
            print(
                f"  ⚠️  Step {step_num}: imbalance "
                f"{step_metrics['imbalance']:.6f}"
            )

        # ── Periodic reporting ─────────────────────────────────────
        if step_num % REPORT_INTERVAL == 0:
            m = compute_metrics(
                ledger,
                workers,
                businesses,
                guilds,
                court_system,
                insurance_market,
                harberger_market=harberger_market,
                step=step_num,
                failed_businesses=failed_businesses,
                distressed_workers=distressed_workers,
            )
            metrics_history.append(m)
            print(f"\n{'─' * 82}")
            print(f"  STATUS @ Step {step_num}")
            print(f"{'─' * 82}")
            print_metrics(m)
            print(f"{'─' * 82}")

    # ═════════════════════════════════════════════════════════════════
    #  FINAL SUMMARY
    # ═════════════════════════════════════════════════════════════════

    print(f"\n{'=' * 82}")
    print("  FINAL SIMULATION SUMMARY")
    print(f"{'=' * 82}")

    print(f"\n  Steps executed:        {ledger.step}")
    print(f"  Total transfers:       {len(ledger.transfers)}")
    print(f"  Total ledger entries:  {len(ledger.entries)}")

    all_balanced = all(m.get("balanced", True) for m in ledger.step_metrics)
    print(f"  All steps balanced:    {'Yes' if all_balanced else '⚠ No'}")
    if not all_balanced:
        imbalances = [
            (m["step"], m["imbalance"])
            for m in ledger.step_metrics
            if not m.get("balanced", True)
        ]
        for s, imb in imbalances[:10]:
            print(f"    Step {s}: imbalance={imb:.6f}")

    print(f"\n  ── Aggregate Flows (all steps) ──")
    for mech in [
        "revenue",
        "wage",
        "lvt",
        "dividend",
        "alliance_skim",
        "premium",
        "claim",
        "guild_dues",
        "guild_benefit",
        "guild_testing_fee",
        "liability",
        "investment",
        "harberger_bond",
        "harberger_bond_refund",
        "harberger_sale",
        "harberger_refusal_penalty",
        "bankruptcy_liquidation",
    ]:
        total = ledger.get_total_flow(mech)
        if total > 0:
            print(f"  Total '{mech:20s}'   ${total:>12,.2f}")

    # ── Harberger property market ────────────────────────────────
    print(f"\n  ── Harberger Property Market ──")
    harv = harberger_market.summary()
    print(f"  Simulation days:          {harv['current_day']}")
    print(f"  Parcels registered:       {harv['parcel_count']}")
    print(f"  Total declared value:     ${sum(p['declared_value'] for p in harv['parcels'].values()):>12,.2f}")
    print(f"  Total assessed for LVT:   ${sum(p['assessed_for_lvt'] for p in harv['parcels'].values()):>12,.2f}")
    # Count active bids and forced sales
    total_active_bids = sum(len(p['active_bids']) for p in harv['parcels'].values())
    total_forced_sales = sum(
        1 for p in harberger_market.parcels.values()
        for b in p.bids if b.status.name == "ACCEPTED"
    )
    print(f"  Active purchase bids:     {total_active_bids}")
    print(f"  Forced sales (all-time):  {total_forced_sales}")
    # Show ownership distribution
    h_parcels_by_owner: dict[str, int] = {}
    for p in harberger_market.parcels.values():
        h_parcels_by_owner[p.owner] = h_parcels_by_owner.get(p.owner, 0) + 1
    multi_owners = sum(1 for c in h_parcels_by_owner.values() if c > 1)
    print(f"  Workers with >1 parcel:   {multi_owners}")

    # ── Worker wealth distribution ─────────────────────────────────
    worker_wealth = sorted([ledger.get_balance(w.id).cash for w in workers])
    print(f"\n  ── Worker Wealth Distribution ──")
    print(f"  Min:    ${worker_wealth[0]:>10,.2f}")
    print(f"  Max:    ${worker_wealth[-1]:>10,.2f}")
    print(f"  Mean:   ${statistics.mean(worker_wealth):>10,.2f}")
    print(f"  Median: ${statistics.median(worker_wealth):>10,.2f}")
    print(f"  Gini:   {gini_coefficient(worker_wealth):>10.4f}")

    # ── Business health ─────────────────────────────────────────
    print(f"\n  ── Business Health (final) ──")
    for b in businesses:
        status = "ALIVE" if b.alive else "⚠ DEAD"
        print(
            f"  {b.id:15s}  cash=${b.cash:>10,.2f}  "
            f"capital=${b.capital:>10,.2f}  "
            f"workers={b.labor_count:>2d}  {status}"
        )

    # ── Cumulative failure summary ─────────────────────────────────
    if failed_businesses:
        print(f"  {'─' * 50}")
        print(f"  Cumulative business failures: {len(failed_businesses)} / {len(businesses)}")
        print(f"  Failed: {', '.join(sorted(failed_businesses))}")
    else:
        print(f"  No business failures (0 / {len(businesses)})")

    # ── Worker distress ────────────────────────────────────────────
    distress_list = [w for w in workers if w.distressed]
    print(f"\n  ── Worker Distress (final) ──")
    if distress_list:
        print(f"  Distressed workers: {len(distress_list)} / {len(workers)}")
        for w in distress_list:
            print(
                f"  {w.id:15s}  cash=${w.cash:>10,.2f}  "
                f"prod={w.productivity:.1f}  "
                f"compacted={w.compact_id}"
            )
    else:
        print(f"  No distressed workers (0 / {len(workers)})")

    # ── Guild membership ────────────────────────────────────────
    print(f"\n  ── Guilds (final) ──")
    for g in guilds:
        print(
            f"  {g.guild_id:15s}  members={g.active_member_count:>2d}  "
            f"cash=${g.cash:>9,.2f}  "
            f"pool=${g.mutual_pool.total_reserves:>9,.2f}  "
            f"boost=×{g.certification.productivity_boost:.2f}  "
            f"dues={g.dues_rate:.1%}"
        )

    # ── Insurance market ─────────────────────────────────────────
    print(f"\n  ── Insurance Market (final) ──")
    istats = insurance_market.get_market_stats()
    print(f"  Insurers:         {istats['insurer_count']}")
    print(f"  Failed insurers:  {istats['failed_insurer_count']}"
          f"  {istats['failed_insurers'] if istats['failed_insurers'] else '(none)'}")
    print(f"  Active policies:  {istats['active_policies']}")
    print(f"  Total premiums:   ${istats['total_premiums_collected']:>10,.2f}")
    print(f"  Total claims:     ${istats['total_claims_paid']:>10,.2f}")
    print(f"  Total reserves:   ${istats['total_reserves']:>10,.2f}")
    print(f"  Evasion flagged:  {istats['total_evasion_flagged']}")
    for ins_id, ins_stats in istats["insurers"].items():
        mult = istats.get('premium_multipliers', {}).get(ins_id, 1.0)
        failed_mark = " ⚠ FAILED" if insurance_market.is_insurer_failed(ins_id) else ""
        print(
            f"    {ins_id:15s}  premiums=${ins_stats['premiums_collected']:>8,.2f}  "
            f"claims=${ins_stats['claims_paid']:>8,.2f}  "
            f"reserves=${ins_stats['reserves']:>8,.2f}  "
            f"mult=×{mult:.3f}{failed_mark}"
        )

    # ── Courts ──────────────────────────────────────────────────
    print(f"\n  ── Court System (final) ──")
    cs = court_system.system_summary()
    print(f"  Courts:           {cs['court_count']}")
    print(f"  Total cases:      filed={cs['total_cases_filed']}, "
          f"resolved={cs['total_cases_resolved']}")
    print(f"  Pending:          {cs['total_cases_pending']}")
    print(f"  Damages awarded:  ${cs['total_damages_awarded']:>10,.2f}")
    print(f"  Filing fees:      ${cs['total_filing_fees_collected']:>10,.2f}")
    for court in court_system.courts.values():
        print(
            f"    {court.name:20s}  rep={court.reputation:.3f}  "
            f"backlog={len(court.backlog):>2d}  "
            f"docket={len(court.docket):>2d}  "
            f"resolved={len(court.resolved):>3d}  "
            f"p-win={court.metrics.plaintiff_win_rate:.0%}"
        )

    # ── Metrics history table ───────────────────────────────────
    print(f"\n  ── Metrics History (every {REPORT_INTERVAL} steps) ──")
    header = (
        f"  {'Step':>5s}  {'Wealth':>12s}  {'Gini':>7s}  "
        f"{'LitRate':>8s}  {'P/C':>7s}  {'LVT':>10s}  "
        f"{'BkRt':>7s}  {'CFail':>7s}  {'Fail':>4s}  "
        f"{'Dist':>4s}  {'Bal':>4s}"
    )
    print(header)
    print(f"  {'─'*5}  {'─'*12}  {'─'*7}  {'─'*8}  "
          f"{'─'*7}  {'─'*10}  {'─'*7}  {'─'*7}  "
          f"{'─'*4}  {'─'*4}  {'─'*4}")
    for m in metrics_history:
        print(
            f"  {m['step']:>5d}  ${m['total_wealth']:>10,.0f}  "
            f"{m['gini']:>7.4f}  {m['litigation_rate']:>8.4f}  "
            f"{m['premium_claim_ratio']:>7.2f}  "
            f"${m['lvt_revenue']:>8,.0f}  "
            f"{m['bankruptcy_rate']:>7.4f}  "
            f"{m['cumulative_failure_rate']:>7.4f}  "
            f"{m['business_failures']:>4d}  "
            f"{m['distressed_workers']:>4d}  "
            f"{'✓' if m['all_balanced'] else '⚠'}"
        )

    print(f"\n{'=' * 82}")
    print(f"  ✅  Simulation complete. "
          f"{STEPS} steps across "
          f"{len(workers)+len(businesses)+len(guilds)+2+2} agents.")
    print(f"{'=' * 82}\n")

    return {
        "ledger": ledger,
        "workers": workers,
        "businesses": businesses,
        "guilds": guilds,
        "court_system": court_system,
        "insurance_market": insurance_market,
        "lvt_engine": lvt_engine,
        "trust_engine": trust_engine,
        "alliance_skim": alliance_skim,
        "harberger_market": harberger_market,
        "metrics_history": metrics_history,
    }


# ══════════════════════════════════════════════════════════════════════
#  Entry Point
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    result = main()
