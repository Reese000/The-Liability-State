"""
event_injection_bridge.py — Wire EventManager into the comparison framework.

Provides two exports for use by system runners in comparison_batch.py:

    setup_events(step_shock: int = 120) -> EventManager
        Creates an EventManager pre-loaded with a MassTort and a Recession
        event that both fire at *step_shock* (default 120, halfway through
        the standard 240-step run).

    apply_event_modifiers(mods, workers, businesses, ledger, rng, step)
        -> dict
        Applies the active modifier dict returned by
        ``EventManager.get_active_modifiers(step)`` to the simulation state.
        Returns a summary dict of applied effects for logging / metrics.

    Modifier key contract (verified against existing event types):
        demand_multiplier      — PRODUCIBLE by Recession (0.3 mag, 20-step
                                 exponential decay). Reduces business revenue.
        claim_freq_multiplier  — PRODUCIBLE by NaturalDisaster or
                                 InsuranceMarketStress (neither included in
                                 setup_events defaults). Increases claim freq.
        land_value_multiplier  — FUTURE — no event currently produces this key.
                                 Handled here for forward compatibility.
"""

from __future__ import annotations

import logging
import random
from typing import Any

from src.events import EventManager, MassTort, Recession

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
#  Event Setup
# ════════════════════════════════════════════════════════════════════════


def setup_events(step_shock: int = 120) -> EventManager:
    """Create an EventManager with MassTort and Recession at *step_shock*.

    Both events fire simultaneously at *step_shock*:

    * ``MassTort`` (magnitude=6.0, duration=0, target='all')
      — injects 6 liability cases into the court system.  No ongoing
      modifiers (instant-only).

    * ``Recession`` (magnitude=0.30, duration=20, target='all')
      — reduces business demand by 30 % at peak, decaying exponentially
      over the next 20 steps.  Produces the ``demand_multiplier`` modifier.

    Parameters
    ----------
    step_shock : int
        The simulation step at which both events fire (default 120,
        halfway through the standard 240-step run).

    Returns
    -------
    EventManager
        Configured event manager with the two events registered.
    """
    em = EventManager(
        events=[
            MassTort(
                name="MassTort_Shock",
                trigger_step=step_shock,
                magnitude=6.0,
                duration=0,
                target="all",
            ),
            Recession(
                name="Recession_Shock",
                trigger_step=step_shock,
                magnitude=0.30,
                duration=20,
                target="all",
            ),
        ]
    )
    return em


# ════════════════════════════════════════════════════════════════════════
#  Modifier Application
# ════════════════════════════════════════════════════════════════════════


def apply_event_modifiers(
    mods: dict[str, float],
    workers: list[dict],
    businesses: list[dict],
    ledger: Any = None,
    rng: random.Random | Any = None,
    step: int = 0,
) -> dict[str, Any]:
    """Apply active event modifiers to workers and businesses.

    Parameters
    ----------
    mods : dict[str, float]
        Active modifier dict from ``EventManager.get_active_modifiers(step)``.
        May contain any of:

            * ``demand_multiplier``     — float, e.g. 0.7 = −30 % revenue.
              **Producible by**: Recession (included in setup_events defaults).
            * ``claim_freq_multiplier`` — float, e.g. 1.5 = +50 % claims.
              **Producible by**: NaturalDisaster or InsuranceMarketStress
              (not included in default setup_events — add manually).
            * ``land_value_multiplier`` — float, e.g. 0.8 = −20 % land values.
              **Future**: no event currently produces this key.  Handled
              here for forward compatibility.

    workers : list[dict]
        Worker population dicts.  Must have ``'id'`` and ``'land'`` keys.
    businesses : list[dict]
        Business population dicts.  ``'id'`` key required.
    ledger : LedgerEngine, optional
        The simulation ledger.  If provided, land-value changes are also
        synced to the ledger's balance-sheet.
    rng : random.Random | numpy.random.RandomState, optional
        Random state for any stochastic effects.  Falls back to the
        ``random`` module if not supplied.
    step : int
        Current simulation step (used for ledger synchronisation).

    Returns
    -------
    dict
        Summary of effects applied, with keys:

            ``demand_multiplier``
                The active demand multiplier value (1.0 = no change).
                *The caller should multiply this into business revenue
                during the step loop.*

            ``claim_freq_multiplier``
                The active claim-frequency multiplier (1.0 = no change).
                *The caller should multiply this into per-worker claim
                probabilities during the step loop.*

            ``land_value_reduction``
                Total dollar amount of land value reduced across all
                workers (float).  Zero if no land_value_multiplier active.
    """
    # ── Input validation ──────────────────────────────────────────
    if not isinstance(mods, dict):
        raise TypeError(f"mods must be a dict, got {type(mods).__name__}")
    if not isinstance(workers, list):
        raise TypeError(f"workers must be a list, got {type(workers).__name__}")
    if not isinstance(businesses, list):
        raise TypeError(f"businesses must be a list, got {type(businesses).__name__}")

    _rng = rng if rng is not None else random

    # ── Snapshot the modifier values ────────────────────────────────
    # These are always available in the return dict even if absent from
    # mods (defaults to 1.0 = no effect).
    demand_mult = float(mods.get("demand_multiplier", 1.0))
    claim_mult = float(mods.get("claim_freq_multiplier", 1.0))
    lv_mult = float(mods.get("land_value_multiplier", 1.0))

    # Warn if non-numeric values slip in
    for key, val in [("demand_multiplier", demand_mult),
                     ("claim_freq_multiplier", claim_mult),
                     ("land_value_multiplier", lv_mult)]:
        if not isinstance(val, (int, float)):
            logger.warning("mods[%r] is not numeric (%s), defaulting to 1.0",
                           key, type(val).__name__)

    effects: dict[str, Any] = {
        "demand_multiplier": demand_mult,
        "claim_freq_multiplier": claim_mult,
        "land_value_reduction": 0.0,
    }

    # ── 1. demand_multiplier — report only (applied by caller) ──────
    #   Reason: revenue is computed inside the system-runner step loop
    #   where we don't have a hook.  The caller should do:
    #       rev *= effects["demand_multiplier"]

    # ── 2. claim_freq_multiplier — report only (applied by caller) ──
    #   Reason: same — claim probability computation lives in the
    #   runner.  The caller should do:
    #       prob *= effects["claim_freq_multiplier"]

    # ── 3. land_value_multiplier — reduce worker land values ────────
    #   Directly mutates the worker dicts because the bridge has access
    #   to them.  This modifier is not yet produced by any existing event
    #   (future extension), but the handler is here for when it is.
    if lv_mult < 1.0:
        total_reduction = 0.0
        for i, w in enumerate(workers):
            if not isinstance(w, dict):
                logger.warning("worker[%d] is not a dict, skipping land-value reduction", i)
                continue
            original_land = float(w.get("land", 0.0))
            new_land = max(0.0, original_land * lv_mult)
            reduction = original_land - new_land
            w["land"] = new_land
            total_reduction += reduction

            # Sync ledger balance-sheet if available
            if ledger is not None:
                wid = w.get("id")
                if wid is None:
                    logger.warning("worker[%d] has no 'id' key, cannot sync ledger", i)
                    continue
                try:
                    bs = ledger.balances.get(wid)
                    if bs is not None:
                        if hasattr(bs, "land_value"):
                            bs.land_value = max(0.0, bs.land_value - reduction)
                except (AttributeError, KeyError, TypeError) as exc:
                    logger.warning(
                        "Failed to sync land-value reduction for %s: %s", wid, exc
                    )

        effects["land_value_reduction"] = total_reduction

        logger.info(
            "step %d: land_value_multiplier=%.2f, total reduction=$%.2f across %d workers",
            step, lv_mult, total_reduction, len(workers),
        )

    # Log modifier state for traceability
    logger.debug(
        "step %d: active modifiers — demand=%.4f, claim_freq=%.4f, land_val=%.4f",
        step, demand_mult, claim_mult, lv_mult,
    )

    return effects


# ════════════════════════════════════════════════════════════════════════
#  Quick smoke test
# ════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.dirname(__file__))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # ── 1. Test setup_events ─────────────────────────────────────────
    print("=== 1. setup_events ===")
    em = setup_events(step_shock=120)
    summary = em.summary()
    assert len(summary) == 2, f"Expected 2 events, got {len(summary)}"
    print(f"  Events loaded: {len(em.events)}")
    for e in summary:
        print(f"    • {e['name']:20s}  type={e['type']:20s}  "
              f"trigger={e['trigger_step']}  mag={e['magnitude']}  "
              f"dur={e['duration']}  fired={e['fired']}")
    assert summary[0]["name"] == "MassTort_Shock"
    assert summary[1]["name"] == "Recession_Shock"

    # ── 2. Test fire + modifiers ──────────────────────────────────────
    print("\n=== 2. Fire at step 120, check modifiers ===")
    context = {
        "current_step": 120,
        "workers": [],
        "businesses": [],
        "court_system": None,
        "ledger": None,
    }
    logs = em.fire_events(context, 120)
    print(f"  Fire logs ({len(logs)} lines):")
    for line in logs:
        print(f"    {line}")
    assert any("MassTort" in line for line in logs), "MassTort should have fired"
    assert any("RECESSION" in line.upper() for line in logs), "Recession should have fired"

    # Modifier contract: with only MassTort + Recession, the ONLY
    # modifier key produced is demand_multiplier.
    mods = em.get_active_modifiers(current_step=120)
    print(f"  get_active_modifiers(step=120) = {mods}")
    assert "demand_multiplier" in mods
    assert mods["demand_multiplier"] == 0.7  # 1.0 - 0.30 initial magnitude

    # MassTort is instant-only — no modifiers ever
    # claim_freq_multiplier not produced by any default event
    # land_value_multiplier not produced by any existing event type
    assert "claim_freq_multiplier" not in mods, \
        "MassTort+Recession do NOT produce claim_freq_multiplier"
    assert "land_value_multiplier" not in mods, \
        "No event currently produces land_value_multiplier"

    # Recession decays to 0 after 20 steps
    mods_after = em.get_active_modifiers(current_step=140)
    print(f"  get_active_modifiers(step=140) = {mods_after}")
    assert "demand_multiplier" not in mods_after, \
        "Recession should have fully decayed by step 140"

    # ── 3. Test apply_event_modifiers ─────────────────────────────────
    print("\n=== 3. apply_event_modifiers ===")
    test_workers = [
        {"id": "w000", "land": 100_000.0, "cash": 50_000.0},
        {"id": "w001", "land": 200_000.0, "cash": 30_000.0},
    ]
    test_biz = [{"id": "b000", "cash": 500_000.0}]

    # Scenario: all three keys present (some may be future keys)
    test_mods = {
        "demand_multiplier": 0.7,
        "claim_freq_multiplier": 1.5,
        "land_value_multiplier": 0.8,
    }
    applied = apply_event_modifiers(
        test_mods, test_workers, test_biz, ledger=None, rng=None, step=120
    )
    print(f"  Applied effects: {applied}")
    assert applied["demand_multiplier"] == 0.7
    assert applied["claim_freq_multiplier"] == 1.5
    assert applied["land_value_reduction"] == 60_000.0  # confirmed: 100k * 0.8 + 200k * 0.8 = 80k + 160k -> reduction = 20k + 40k = 60k
    assert test_workers[0]["land"] == 80_000.0
    assert test_workers[1]["land"] == 160_000.0
    print("  ✓ demand_multiplier reported ✓ claim_freq_multiplier reported ✓ land values reduced")

    # No-op when land_value_multiplier absent
    no_lv_mods = {"demand_multiplier": 0.7, "claim_freq_multiplier": 1.5}
    no_lv_result = apply_event_modifiers(
        no_lv_mods, test_workers, test_biz, ledger=None, rng=None, step=120
    )
    assert no_lv_result["land_value_reduction"] == 0.0
    print("  ✓ No-op when land_value_multiplier absent")

    # ── 4. Test input validation ──────────────────────────────────────
    print("\n=== 4. Input validation ===")
    try:
        apply_event_modifiers("not_a_dict", [], [], step=0)
        assert False
    except TypeError:
        print("  ✓ TypeError on bad mods type")

    try:
        apply_event_modifiers({}, "not_a_list", [], step=0)
        assert False
    except TypeError:
        print("  ✓ TypeError on bad workers type")

    try:
        apply_event_modifiers({}, [], "not_a_list", step=0)
        assert False
    except TypeError:
        print("  ✓ TypeError on bad businesses type")

    # ── 5. Test negative land guard ───────────────────────────────────
    print("\n=== 5. Negative land guard ===")
    tiny_workers = [{"id": "w_tiny", "land": 10.0}]
    big_lv_result = apply_event_modifiers(
        {"land_value_multiplier": 0.0}, tiny_workers, [], step=0
    )
    assert tiny_workers[0]["land"] == 0.0
    assert big_lv_result["land_value_reduction"] == 10.0
    print("  ✓ Land clamped to 0.0, reduction tracked correctly")

    print("\n✅ All smoke tests passed.")
