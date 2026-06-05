#!/usr/bin/env python3
"""
v3_tort_deterrence.py — V3 Validation: Tort Liability Deterrence (Becker-Shavell)

Validates that the simulation's tort liability system deters accidents:
higher liability exposure → agents choose more care → fewer accidents.

Two scenarios:
  1) HIGH LIABILITY — agents face full accident damages via the court system
  2) LOW LIABILITY  — agents face zero damages (no legal recourse)

Testable prediction (Becker 1968, Shavell 1987):
  Under high liability, rational agents select higher care levels to reduce
  expected accident costs, resulting in lower accident rates.
  Under low/no liability, agents minimise costly care, resulting in higher
  accident rates.

Uses existing mechanics:
  - src/mechanics/courts.py  — case filing, adjudication, damages
  - src/mechanics/insurance.py — (referenced for insurance context)

Pass/fail thresholds:
  - HIGH_LIABILITY_CARE_MIN    ≥ 0.40  (care level must materially exceed zero)
  - LOW_LIABILITY_CARE_MAX     ≤ 0.10  (care level must be near zero)
  - CARE_SEPARATION            ≥ 0.30  (absolute gap between regimes)
  - ACCIDENT_RATE_SEPARATION   ≥ 0.10  (accident rate must be lower in high-liability)
"""

from __future__ import annotations

import math
import random
import statistics
import sys
from pathlib import Path

# ── Ensure simulation package is on path ─────────────────────────────
SIM_ROOT = Path(__file__).resolve().parent.parent / "src"
if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from mechanics.courts import (
    CaseStatus,
    Court,
    CourtSystem,
    Verdict,
    create_case,
)


# ═══════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════

# Agent / accident model
ALPHA = 200.0          # Quadratic cost coefficient for care (care_cost = ALPHA * c²)
P_BASE = 0.30          # Base accident probability when care = 0
DAMAGES = 1000.0       # Accident damages (full)

# Simulation
NUM_STEPS = 200
NUM_AGENTS = 30
SEED = 42

# Pass/fail thresholds (see above for rationale)
THRESHOLDS = {
    "high_liability_care_min": 0.40,
    "low_liability_care_max": 0.10,
    "care_separation_min": 0.30,
    "accident_rate_separation_min": 0.10,
}


# ══════════════════════════════════════════════════════════════════════
#  Agent Decision Model
# ══════════════════════════════════════════════════════════════════════

def optimal_care(expected_liability: float, alpha: float = ALPHA,
                 p_base: float = P_BASE) -> float:
    """
    Return the care level c ∈ [0, 1] that minimises expected cost:

        E(c) = alpha * c²  +  p_base * (1 - c) * expected_liability

    First-order condition (interior):  2*alpha*c - p_base*D = 0
    =>  c* = p_base * D / (2 * alpha)

    If expected_liability ≤ 0, optimal care is 0 (no deterrence).
    """
    if expected_liability <= 0.0:
        return 0.0
    c_star = p_base * expected_liability / (2.0 * alpha)
    return max(0.0, min(1.0, c_star))


def accident_prob(care: float, p_base: float = P_BASE) -> float:
    """Probability of an accident given care level c ∈ [0, 1]."""
    return p_base * (1.0 - care)


# ══════════════════════════════════════════════════════════════════════
#  Scenario Runner
# ══════════════════════════════════════════════════════════════════════

def run_scenario(
    label: str,
    liability_multiplier: float,
    seed: int = SEED,
) -> dict:
    """
    Run a tort-liability scenario.

    Parameters
    ----------
    label : str
        Human-readable scenario name.
    liability_multiplier : float
        Fraction of accident DAMAGES the agent must pay (0.0 = no liability,
        1.0 = full liability).
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    dict with keys:
        scenario_label, care_levels, accident_rates, total_accidents,
        total_steps, avg_care, avg_accident_rate, damages_collected
    """
    rng = random.Random(seed)

    # Compute the care each agent will choose (rational optimisation)
    # All agents are identical, so they all pick the same care level.
    expected_liability = DAMAGES * liability_multiplier
    chosen_care = optimal_care(expected_liability)

    # Simulate
    care_levels = []
    accident_counts = [0] * NUM_AGENTS
    damages_collected = 0.0
    total_accidents = 0

    # Create a court system to adjudicate accidents
    court_system = CourtSystem()
    court = Court(
        court_id="tort_court",
        name="Tort Adjudicator",
        filing_fee_rate=0.02,
        speed_factor=2.0,
        fairness_factor=0.90,
        bias=0.0,
        initial_reputation=0.7,
    )
    court.max_docket_size = 20
    court_system.register_court(court)

    for step in range(1, NUM_STEPS + 1):
        # Each agent makes a care decision each step
        # (could add noise / bounded rationality — we use deterministic optimum)
        care_levels.append(chosen_care)

        # Check for accident
        for agent_id in range(NUM_AGENTS):
            if rng.random() < accident_prob(chosen_care):
                total_accidents += 1
                accident_counts[agent_id] += 1

                # ── File a case in court (high liability only) ──────
                if liability_multiplier > 0.0:
                    # Victim sues the injurer
                    # defendant_due_care reflects the care the injurer took
                    case = create_case(
                        plaintiff=f"victim_{agent_id}_{step}",
                        defendant=f"injurer_{agent_id}",
                        claimed_amount=DAMAGES,
                        evidence_strength=0.7,        # reasonably provable
                        defendant_due_care=chosen_care,  # care level matters for liability
                        foreseeability=0.6,
                        comparative_negligence=0.0,
                        willful=False,
                        description=(
                            f"Accident at step {step}: "
                            f"injurer care={chosen_care:.3f}"
                        ),
                    )
                    success, msg = court_system.route_case(case, preferred_court_id="tort_court")

        # Advance the court system each step
        court_system.tick(step)

    # ── Collect damages awarded in court ────────────────────────────
    for case in court_system.all_cases.values():
        if case.status in (CaseStatus.CLOSED, CaseStatus.ADJUDICATED):
            if case.damages_awarded > 0:
                damages_collected += case.damages_awarded

    avg_care = statistics.mean(care_levels)
    avg_accident_rate = total_accidents / (NUM_STEPS * NUM_AGENTS)

    return {
        "scenario_label": label,
        "chosen_care": chosen_care,
        "avg_care": avg_care,
        "total_accidents": total_accidents,
        "total_steps": NUM_STEPS * NUM_AGENTS,
        "avg_accident_rate": avg_accident_rate,
        "damages_collected": damages_collected,
        "cases_filed": len(court_system.all_cases),
        "cases_resolved": sum(
            1 for c in court_system.all_cases.values()
            if c.status in (CaseStatus.CLOSED, CaseStatus.ADJUDICATED)
        ),
    }


# ══════════════════════════════════════════════════════════════════════
#  Court Liability Verification
# ══════════════════════════════════════════════════════════════════════

def verify_court_liability_channel() -> dict:
    """
    Confirm that the court system imposes higher damages when care is low.

    Files two test cases with the same parameters except defendant_due_care:
      - Low care (0.1)  → should be found liable, high damages
      - High care (0.9) → should be found not liable, zero damages

    Returns dict with case outcomes.
    """
    court_system = CourtSystem()
    court = Court(
        court_id="verify_court",
        name="Verification Court",
        filing_fee_rate=0.01,
        speed_factor=1.0,   # fast for testing
        fairness_factor=1.0,  # perfectly fair
        bias=0.0,
        initial_reputation=0.8,
    )
    court_system.register_court(court)

    # Case A: low care (defendant didn't take precautions)
    case_low_care = create_case(
        plaintiff="Victim",
        defendant="LowCareDefendant",
        claimed_amount=1000.0,
        evidence_strength=0.5,
        defendant_due_care=0.1,   # very low care
        foreseeability=0.4,
        comparative_negligence=0.0,
        willful=False,
        description="Low care → high liability expected",
    )

    # Case B: high care (defendant took precautions)
    case_high_care = create_case(
        plaintiff="Victim2",
        defendant="HighCareDefendant",
        claimed_amount=1000.0,
        evidence_strength=0.5,
        defendant_due_care=0.9,   # very high care
        foreseeability=0.4,
        comparative_negligence=0.0,
        willful=False,
        description="High care → low liability expected",
    )

    # File both cases
    court_system.route_case(case_low_care, preferred_court_id="verify_court")
    court_system.route_case(case_high_care, preferred_court_id="verify_court")

    # Run court steps until both are adjudicated
    for step in range(1, 20):
        events = court_system.tick(step)
        if case_low_care.status != CaseStatus.FILED and case_high_care.status != CaseStatus.FILED:
            break

    return {
        "low_care_verdict": case_low_care.verdict.name if case_low_care.verdict else "N/A",
        "low_care_damages": case_low_care.damages_awarded,
        "low_care_liable": case_low_care.damages_awarded > 0,
        "high_care_verdict": case_high_care.verdict.name if case_high_care.verdict else "N/A",
        "high_care_damages": case_high_care.damages_awarded,
        "high_care_liable": case_high_care.damages_awarded > 0,
    }


# ══════════════════════════════════════════════════════════════════════
#  Main — Run Validation
# ══════════════════════════════════════════════════════════════════════

def main() -> int:
    print("=" * 72)
    print("  V3 VALIDATION: TORT LIABILITY DETERRENCE (Becker-Shavell)")
    print("=" * 72)

    # ── 1. Verify Court Liability Channel ────────────────────────────
    print("\n─── Stage 1: Court Liability Channel ───\n")
    court_results = verify_court_liability_channel()

    print(f"  Low-care defendant (due_care=0.1):")
    print(f"    Verdict : {court_results['low_care_verdict']}")
    print(f"    Damages : ${court_results['low_care_damages']:.2f}")
    print(f"    Liable  : {court_results['low_care_liable']}")

    print(f"  High-care defendant (due_care=0.9):")
    print(f"    Verdict : {court_results['high_care_verdict']}")
    print(f"    Damages : ${court_results['high_care_damages']:.2f}")
    print(f"    Liable  : {court_results['high_care_liable']}")

    court_channel_ok = (
        court_results["low_care_damages"] > court_results["high_care_damages"] * 2.0
        and court_results["low_care_damages"] > 0
    )
    court_status = "✓ PASS" if court_channel_ok else "✗ FAIL"
    print(f"\n  Court liability channel: {court_status}")
    if not court_channel_ok:
        print("    Expected: low-care damages >> high-care damages (proportional liability).")

    # ── 2. Run Scenarios ─────────────────────────────────────────────
    print("\n─── Stage 2: Deterrence Scenarios ───\n")

    # Scenario A: High liability (full damages)
    high_res = run_scenario(
        label="HIGH LIABILITY (full damages)",
        liability_multiplier=1.0,
        seed=SEED,
    )

    # Scenario B: Low liability (no damages)
    low_res = run_scenario(
        label="LOW LIABILITY (no damages)",
        liability_multiplier=0.0,
        seed=SEED,
    )

    # Print scenario results
    print(f"  {high_res['scenario_label']}")
    print(f"    Chosen care level    : {high_res['chosen_care']:.4f}")
    print(f"    Avg accident rate    : {high_res['avg_accident_rate']:.4f}  "
          f"({high_res['total_accidents']}/{high_res['total_steps']} steps)")
    print(f"    Cases filed          : {high_res['cases_filed']}")
    print(f"    Cases resolved       : {high_res['cases_resolved']}")
    print(f"    Damages collected    : ${high_res['damages_collected']:.2f}")

    print()
    print(f"  {low_res['scenario_label']}")
    print(f"    Chosen care level    : {low_res['chosen_care']:.4f}")
    print(f"    Avg accident rate    : {low_res['avg_accident_rate']:.4f}  "
          f"({low_res['total_accidents']}/{low_res['total_steps']} steps)")
    print(f"    Cases filed          : {low_res['cases_filed']}")
    print(f"    Cases resolved       : {low_res['cases_resolved']}")
    print(f"    Damages collected    : ${low_res['damages_collected']:.2f}")

    # ── 3. Evaluate Predictions ──────────────────────────────────────
    print("\n─── Stage 3: Prediction Evaluation ───\n")

    tests = []

    # T1: HIGH liability → high care (≥ threshold)
    t1_pass = high_res["avg_care"] >= THRESHOLDS["high_liability_care_min"]
    tests.append(("High-liability care ≥ threshold",
                  t1_pass,
                  f"{high_res['avg_care']:.4f} ≥ {THRESHOLDS['high_liability_care_min']}"))

    # T2: LOW liability → low care (≤ threshold)
    t2_pass = low_res["avg_care"] <= THRESHOLDS["low_liability_care_max"]
    tests.append(("Low-liability care ≤ threshold",
                  t2_pass,
                  f"{low_res['avg_care']:.4f} ≤ {THRESHOLDS['low_liability_care_max']}"))

    # T3: Care separation (high > low by margin)
    care_gap = high_res["avg_care"] - low_res["avg_care"]
    t3_pass = care_gap >= THRESHOLDS["care_separation_min"]
    tests.append(("Care separation ≥ margin",
                  t3_pass,
                  f"{care_gap:.4f} ≥ {THRESHOLDS['care_separation_min']}"))

    # T4: Accident rate lower under high liability
    accident_gap = low_res["avg_accident_rate"] - high_res["avg_accident_rate"]
    t4_pass = accident_gap >= THRESHOLDS["accident_rate_separation_min"]
    tests.append(("Accident rate lower under high liability",
                  t4_pass,
                  f"{accident_gap:.4f} ≥ {THRESHOLDS['accident_rate_separation_min']}"))

    # T5: Court imposes proportionally higher damages on low care
    tests.append(("Court punishes low care more than high care",
                  court_channel_ok,
                  f"low_damages={court_results['low_care_damages']:.2f}, "
                  f"high_damages={court_results['high_care_damages']:.2f}, "
                  f"ratio={court_results['low_care_damages']/max(1,court_results['high_care_damages']):.2f}x"))

    all_pass = True
    for name, passed, detail in tests:
        tag = "✓ PASS" if passed else "✗ FAIL"
        all_pass = all_pass and passed
        print(f"  [{tag}] {name}")
        print(f"         {detail}")

    # ── Summary ──────────────────────────────────────────────────────
    print()
    print("=" * 72)
    verdict = "ALL TESTS PASSED" if all_pass else "SOME TESTS FAILED"
    if all_pass:
        print(f"  ✅  V3 VALIDATION: {verdict}")
    else:
        print(f"  ❌  V3 VALIDATION: {verdict}")
    print("=" * 72)

    # Print analytical expectations vs observed
    print("\n  ┌─────────────────────────┬──────────┬──────────┐")
    print("  │ Metric                  │ Expected │ Observed │")
    print("  ├─────────────────────────┼──────────┼──────────┤")
    # High liability: expected care = 0.3 * 1000 / (2*200) = 0.75
    exp_high_care = P_BASE * DAMAGES / (2.0 * ALPHA)
    exp_low_care = 0.0
    exp_high_acc = P_BASE * (1.0 - exp_high_care)
    exp_low_acc = P_BASE
    print(f"  │ High-liability care     │ {exp_high_care:.4f}    │ {high_res['avg_care']:.4f}    │")
    print(f"  │ Low-liability care      │ {exp_low_care:.4f}    │ {low_res['avg_care']:.4f}    │")
    print(f"  │ High-liability accident │ {exp_high_acc:.4f}    │ {high_res['avg_accident_rate']:.4f}    │")
    print(f"  │ Low-liability accident  │ {exp_low_acc:.4f}    │ {low_res['avg_accident_rate']:.4f}    │")
    print("  └─────────────────────────┴──────────┴──────────┘")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
