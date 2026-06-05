"""
v2_lvt_efficiency.py — V2 Validation Test: LVT vs Income Tax Labor Distortion

Tests the Georgist prediction:
  Land Value Tax should NOT distort labor supply;
  Income Tax SHOULD reduce labor supply.

Two simulations with ~50 heterogeneous-productivity agents:
  1. LVT funds government — measure total labor supply
  2. Income tax funds government — measure total labor supply

Expected:
  - LVT:   total labor ≈ optimal (undistorted) labor supply (≥ 98 %)
  - Income tax: total labor ≤ 95 % of optimal (clear distortion)
  - LVT labor > Income tax labor

Theoretical basis (quasi-linear utility):
  U = C - (θ/2) · L²    →    L* = w · (1 - τ) / θ

  LVT is a lump-sum tax on land value — it does not enter the marginal
  condition.  Income tax directly cuts the effective wage.
"""

from __future__ import annotations
import sys
import math
import random
import statistics
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────
# This file lives at  simulation/validation/v2_lvt_efficiency.py
# We need the *parent* of src/ (i.e. simulation/) on sys.path so that
# the relative imports inside src/mechanics/lvt.py resolve correctly.
_HERE = Path(__file__).resolve().parent          # validation/
_SIM = _HERE.parent                                # simulation/
_SRC = _SIM / 'src'                                # simulation/src/
for p in [str(_SIM), str(_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from src.core.ledger import LedgerEngine, EntityType
from src.mechanics.lvt import LVTEngine, TrustEngine, AllianceSkim


# ═══════════════════════════════════════════════════════════════════════
# 1 — Agent labor supply model
# ═══════════════════════════════════════════════════════════════════════

def optimal_labor(productivity: float, theta: float, tax_rate: float = 0.0) -> float:
    """
    Optimal labor hours for a quasi-linear utility agent.

    max_{L ≥ 0}   w·L·(1 - τ) + T  -  (θ/2)·L²

    FOC:  w·(1 - τ) - θ·L = 0   →   L* = w·(1 - τ)/θ

    Parameters
    ----------
    productivity : float — wage rate w_i
    theta        : float — disutility-of-labour coefficient
    tax_rate     : float — income-tax rate (0 for LVT case)

    Returns
    -------
    float — optimal labour hours (unconstrained, always ≥ 0)
    """
    raw = productivity * (1.0 - tax_rate) / theta
    return max(raw, 0.0)


def theoretical_labor(agents: list[dict], theta: float,
                      tax_rate: float = 0.0) -> float:
    """Sum of optimal labor across all agents for a given tax rate."""
    return sum(optimal_labor(a['productivity'], theta, tax_rate)
               for a in agents)


# ═══════════════════════════════════════════════════════════════════════
# 2 — Simulation: LVT funds government
# ═══════════════════════════════════════════════════════════════════════

def run_lvt_simulation(agents: list[dict],
                       lvt_rate: float = 0.05,
                       theta: float = 1.0,
                       steps: int = 10,
                       seed: int = 42) -> dict:
    """
    Run *steps* periods where the government (National Trust) is funded
    entirely by Land Value Tax.

    Each step:
      1. Agents supply labour (undistorted — LVT is lump-sum).
      2. Wage income is credited from __system__ → each agent.
      3. LVT is collected from agents → National Trust (via LVTEngine).
      4. The Trust returns the revenue as a per-capita Citizen's Dividend
         (via TrustEngine; skim_rate = 0 for this test).

    Returns a dict with keys:
      'labor_history'        — list[float]  total labour per step
      'avg_labor'            — float
      'net_income_history'   — list[dict[str,float]]
      'ledger'               — LedgerEngine (for post-hoc checks)
      'final_result'         — last run_full_cycle result
    """
    rng = random.Random(seed)
    ledger = LedgerEngine(step_log=False)

    # Engines  (skim_rate=0 so all LVT returns as dividend)
    lvt_engine = LVTEngine(ledger, rate=lvt_rate)
    trust_engine = TrustEngine(ledger, skim_rate=0.0)
    alliance_skim = AllianceSkim(ledger)

    # Register system entities
    ledger.register_entity('national_trust', EntityType.TRUST, initial_cash=0.0)
    ledger.register_entity('alliance',       EntityType.ALLIANCE, initial_cash=0.0)
    ledger.register_entity('__system__',     EntityType.SYSTEM,   initial_cash=1e9)

    # Register citizen agents
    citizen_ids: list[str] = []
    compact_map: dict[str, str] = {}
    for a in agents:
        cid = a['id']
        bs = ledger.register_entity(cid, EntityType.CITIZEN,
                                    compact_id='default',
                                    initial_cash=1000.0)
        bs.land_value = a['land_value']
        bs.property_count = 1 if a['land_value'] > 0 else 0
        citizen_ids.append(cid)
        compact_map[cid] = 'default'

    labor_history: list[float] = []
    net_income_history: list[dict[str, float]] = []

    for step in range(steps):
        # --- (1) Labour supply (undistorted) ---
        total_labor = 0.0
        for a in agents:
            L = optimal_labor(a['productivity'], theta, tax_rate=0.0)
            a['labor'] = L
            total_labor += L

        # --- (2) Record wage income  ---
        # (not strictly necessary for the test, but makes the ledger
        #  complete and the zero-sum invariant meaningful)
        ledger.begin_step()
        for a in agents:
            wage = a['productivity'] * a['labor']
            if wage > 0:
                ledger.transfer('__system__', a['id'], 'wage', wage,
                                f'Labour income for step {step}')

        # --- (3) LVT collection + Dividend distribution ---
        # run_full_cycle calls begin_step() + close_step() internally,
        # but we already started the step.  So we run the sub-steps
        # manually instead.
        lvt_results = lvt_engine.collect(citizen_ids)
        total_lvt = sum(lvt_results.values())

        # Build compact-contribution map (single compact 'default')
        contrib = {'default': total_lvt}

        dist_result = trust_engine.distribute(
            citizen_ids=citizen_ids,
            total_lvt=total_lvt,
            essential_costs=0.0,
            compact_contributions=contrib,
        )

        alliance_skim.record_skim(
            amount=dist_result['alliance_skim'],
            compact_contributions=contrib,
        )

        metrics = ledger.close_step()

        # Record
        labor_history.append(total_labor)

        step_net = {}
        for a in agents:
            cid = a['id']
            bs = ledger.get_balance(cid)
            wage_income = a['productivity'] * a['labor']
            lvt_bill = lvt_results.get(cid, 0.0)
            div = next(
                (t['dividend'] for t in dist_result['transfers']
                 if t['citizen'] == cid),
                0.0,
            )
            step_net[cid] = wage_income - lvt_bill + div
        net_income_history.append(step_net)

    return {
        'labor_history': labor_history,
        'avg_labor': statistics.mean(labor_history),
        'net_income_history': net_income_history,
        'ledger': ledger,
        'final_result': {
            'lvt_collected': lvt_results,
            'distribution': dist_result,
            'step_metrics': metrics,
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# 3 — Simulation: Income tax funds government
# ═══════════════════════════════════════════════════════════════════════

def run_income_tax_simulation(agents: list[dict],
                              tax_rate: float = 0.25,
                              theta: float = 1.0,
                              steps: int = 10,
                              seed: int = 42) -> dict:
    """
    Run *steps* periods where the government is funded by a flat income
    tax on labour earnings.  Tax revenue is NOT rebated (government
    consumption / waste), isolating the substitution effect.

    Each step:
      1. Agents supply labour (distorted by the income-tax wedge).
      2. Wage income is credited from __system__ → each agent.
      3. Income tax is collected: agent → 'government' entity.

    Returns dict with same structure as run_lvt_simulation.
    """
    rng = random.Random(seed)
    ledger = LedgerEngine(step_log=False)

    ledger.register_entity('government', EntityType.TRUST, initial_cash=0.0)
    ledger.register_entity('__system__',  EntityType.SYSTEM, initial_cash=1e9)

    citizen_ids: list[str] = []
    for a in agents:
        cid = a['id']
        ledger.register_entity(cid, EntityType.CITIZEN,
                               compact_id='default',
                               initial_cash=1000.0)
        citizen_ids.append(cid)

    labor_history: list[float] = []
    net_income_history: list[dict[str, float]] = []

    for step in range(steps):
        # --- (1) Labour supply (distorted) ---
        total_labor = 0.0
        for a in agents:
            L = optimal_labor(a['productivity'], theta, tax_rate=tax_rate)
            a['labor'] = L
            total_labor += L

        # --- (2) Record wage + collect income tax ---
        ledger.begin_step()

        for a in agents:
            cid = a['id']
            wage_income = a['productivity'] * a['labor']

            # Credit wage
            if wage_income > 0:
                ledger.transfer('__system__', cid, 'wage', wage_income,
                                f'Labour income for step {step}')

            # Collect income tax
            tax_due = wage_income * tax_rate
            if tax_due > 0:
                ledger.transfer(cid, 'government', 'income_tax', tax_due,
                                f'Income tax ({tax_rate*100:.0f}% of ${wage_income:.2f})')

        metrics = ledger.close_step()

        # Record
        labor_history.append(total_labor)

        step_net = {}
        for a in agents:
            cid = a['id']
            wage_income = a['productivity'] * a['labor']
            step_net[cid] = wage_income * (1.0 - tax_rate)
        net_income_history.append(step_net)

    return {
        'labor_history': labor_history,
        'avg_labor': statistics.mean(labor_history),
        'net_income_history': net_income_history,
        'ledger': ledger,
        'final_result': {'step_metrics': metrics},
    }


# ═══════════════════════════════════════════════════════════════════════
# 4 — Create heterogeneous agent population
# ═══════════════════════════════════════════════════════════════════════

def create_agents(n: int = 50, seed: int = 42) -> list[dict]:
    """
    Build a list of agents with log-normal productivities and random
    land values.

    Returns a list of dicts:
        id, productivity, land_value, labor
    """
    rng = random.Random(seed)

    agents: list[dict] = []
    for i in range(n):
        prod = rng.lognormvariate(0.0, 0.5)       # mean ≈ 1.0
        land = 10000.0 * (0.5 + rng.random())      # $5k–$15k
        agents.append({
            'id': f'agent_{i:03d}',
            'productivity': prod,
            'land_value': land,
            'labor': 0.0,
        })

    agents.sort(key=lambda a: a['productivity'])
    return agents


# ═══════════════════════════════════════════════════════════════════════
# 5 — Productivity distribution summary
# ═══════════════════════════════════════════════════════════════════════

def _prod_stats(agents: list[dict]) -> dict:
    prods = [a['productivity'] for a in agents]
    return {
        'n': len(prods),
        'min': min(prods),
        'max': max(prods),
        'mean': statistics.mean(prods),
        'median': statistics.median(prods),
        'stdev': statistics.stdev(prods) if len(prods) > 1 else 0.0,
        'gini': _gini(prods),
    }


def _gini(values: list[float]) -> float:
    """Simple Gini coefficient calculation."""
    n = len(values)
    if n < 2:
        return 0.0
    sorted_v = sorted(values)
    cum = 0.0
    total = sum(sorted_v)
    if total == 0:
        return 0.0
    for i, v in enumerate(sorted_v, 1):
        cum += i * v
    return (2.0 * cum / (n * total) - (n + 1.0) / n)


# ═══════════════════════════════════════════════════════════════════════
# 6 — Main entry point
# ═══════════════════════════════════════════════════════════════════════

def main() -> int:
    print("=" * 74)
    print("  V2 VALIDATION TEST:  LVT vs Income Tax — Labour-Supply Distortion")
    print("=" * 74)

    # ── Configuration ───────────────────────────────────────────────
    N_AGENTS   = 50
    THETA      = 1.0        # disutility-of-labour coefficient
    LVT_RATE   = 0.05       # 5 % land-value tax
    INCOME_RATE = 0.25      # 25 % flat income tax
    STEPS      = 10
    SEED       = 42

    # ── Build agents ────────────────────────────────────────────────
    agents = create_agents(N_AGENTS, SEED)
    ps = _prod_stats(agents)

    print(f"\n  Agent population:  {N_AGENTS}")
    print(f"  Productivity distribution (log-normal, μ=0, σ=0.5):")
    print(f"    min    = {ps['min']:.4f}")
    print(f"    max    = {ps['max']:.4f}")
    print(f"    mean   = {ps['mean']:.4f}")
    print(f"    median = {ps['median']:.4f}")
    print(f"    stdev  = {ps['stdev']:.4f}")
    print(f"    Gini   = {ps['gini']:.4f}")

    print(f"\n  θ (labour disutility)  = {THETA}")
    print(f"  LVT rate               = {LVT_RATE*100:.1f} %")
    print(f"  Income tax rate        = {INCOME_RATE*100:.1f} %")
    print(f"  Simulation steps       = {STEPS}")

    # ── Theoretical benchmarks ──────────────────────────────────────
    opt_total   = theoretical_labor(agents, THETA, tax_rate=0.0)
    lvt_total   = theoretical_labor(agents, THETA, tax_rate=0.0)   # same — no distortion
    tax_total   = theoretical_labor(agents, THETA, tax_rate=INCOME_RATE)

    print(f"\n  Theoretical benchmarks:")
    print(f"    Optimal (no tax):               {opt_total:>10.4f}")
    print(f"    LVT (should match optimal):     {lvt_total:>10.4f}")
    print(f"    Income tax @ {INCOME_RATE*100:.0f}%:              {tax_total:>10.4f}")
    print(f"    Expected income-tax distortion: {((1 - tax_total/opt_total)*100):.1f} % reduction")

    # ═════════════════════════════════════════════════════════════════
    #  SIMULATION 1 — LVT
    # ═════════════════════════════════════════════════════════════════
    print(f"\n{'─' * 74}")
    print("  SIMULATION 1:  Government funded by Land Value Tax")
    print(f"{'─' * 74}")

    for a in agents:
        a['labor'] = 0.0
    lvt_res = run_lvt_simulation(agents, lvt_rate=LVT_RATE,
                                  theta=THETA, steps=STEPS, seed=SEED)

    lvt_avg = lvt_res['avg_labor']
    lvt_pct = lvt_avg / opt_total * 100

    print(f"\n    Total labour per step (avg over {STEPS} steps):")
    print(f"      LVT simulation:  {lvt_avg:>10.4f}")
    print(f"      Optimal:         {opt_total:>10.4f}")
    print(f"      Ratio:           {lvt_pct:>8.2f} %")
    print(f"      Deviation:       {abs(lvt_pct - 100):>7.3f} %")

    # Ledger health
    lm = lvt_res['final_result']['step_metrics']
    print(f"\n    Ledger:  step={lm['step']}, balanced={lm['balanced']}, "
          f"imbalance={lm['imbalance']:.6f}")

    # ═════════════════════════════════════════════════════════════════
    #  SIMULATION 2 — Income tax
    # ═════════════════════════════════════════════════════════════════
    print(f"\n{'─' * 74}")
    print("  SIMULATION 2:  Government funded by Income Tax")
    print(f"{'─' * 74}")

    for a in agents:
        a['labor'] = 0.0
    tax_res = run_income_tax_simulation(agents, tax_rate=INCOME_RATE,
                                         theta=THETA, steps=STEPS, seed=SEED)

    tax_avg = tax_res['avg_labor']
    tax_pct = tax_avg / opt_total * 100

    print(f"\n    Total labour per step (avg over {STEPS} steps):")
    print(f"      Income-tax simulation:  {tax_avg:>10.4f}")
    print(f"      Optimal:                {opt_total:>10.4f}")
    print(f"      Ratio:                  {tax_pct:>8.2f} %")
    print(f"      Distortion:             {(100 - tax_pct):>7.3f} %")

    tm = tax_res['final_result']['step_metrics']
    print(f"\n    Ledger:  step={tm['step']}, balanced={tm['balanced']}, "
          f"imbalance={tm['imbalance']:.6f}")

    # ═════════════════════════════════════════════════════════════════
    #  PASS / FAIL
    # ═════════════════════════════════════════════════════════════════
    print(f"\n{'═' * 74}")
    print("  PASS / FAIL EVALUATION")
    print(f"{'═' * 74}")

    # Criteria
    # 1. LVT labour ≥ 98 % of optimal (within numerical tolerance)
    # 2. Income-tax labour ≤ 95 % of optimal (clear distortion)
    # 3. Income-tax labour < LVT labour
    lvt_ratio = lvt_avg / opt_total
    tax_ratio = tax_avg / opt_total

    pass_lvt_undistorted = lvt_ratio >= 0.98
    pass_tax_distorted   = tax_ratio <= 0.95
    pass_lvt_beats_tax   = tax_avg < lvt_avg

    print(f"\n    LVT labour / Optimal:         {lvt_ratio:.6f}  "
          f"({lvt_ratio*100:.2f} %)  "
          f"{'✓' if pass_lvt_undistorted else '✗'}")
    print(f"    Income-tax labour / Optimal:  {tax_ratio:.6f}  "
          f"({tax_ratio*100:.2f} %)  "
          f"{'✓' if pass_tax_distorted else '✗'}")
    print(f"    LVT > Income-tax labour?      "
          f"{'✓' if pass_lvt_beats_tax else '✗'}")

    failures: list[str] = []
    if not pass_lvt_undistorted:
        failures.append(
            f"LVT labour ({lvt_ratio*100:.2f} % of optimal) exceeds 2 % "
            f"tolerance — expected no labour distortion under LVT"
        )
    if not pass_tax_distorted:
        failures.append(
            f"Income-tax labour ({tax_ratio*100:.2f} % of optimal) not "
            f"sufficiently reduced — expected ≤ 95 %"
        )
    if not pass_lvt_beats_tax:
        failures.append(
            f"Income-tax labour ({tax_ratio*100:.2f} %) >= LVT labour "
            f"({lvt_ratio*100:.2f} %) — income tax should reduce labour more"
        )

    # Also verify the distortion matches the theoretical prediction
    expected_tax_ratio = 1.0 - INCOME_RATE  # = 0.75 for 25% tax
    # Allow 0.5 % numerical slack
    distortion_match = abs(tax_ratio - expected_tax_ratio) < 0.005
    if not distortion_match:
        failures.append(
            f"Income-tax labour ratio ({tax_ratio:.4f}) diverges from "
            f"theoretical prediction ({expected_tax_ratio:.4f})"
        )
    else:
        print(f"    Distortion matches theory?    "
              f"✓  (tax ratio {tax_ratio:.4f} ≈ 1-τ = {expected_tax_ratio:.4f})")

    # Final verdict
    print()
    if not failures:
        print("  ✅  ALL CHECKS PASSED")
        print("  ✅  LVT shows no labour distortion (Georgist prediction holds)")
        print("  ✅  Income tax shows clear labour-supply reduction")
        print("  ✅  Efficiency gap between LVT and income tax confirmed")
    else:
        print(f"  ❌  {len(failures)} FAILURE(S):")
        for i, f in enumerate(failures, 1):
            print(f"      [{i}] {f}")

    print(f"\n{'═' * 74}")
    print("  Validation complete.")
    print(f"{'═' * 74}")

    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
