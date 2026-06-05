"""
events.py — Shock event system for The Liability State simulation.

Provides a framework for injecting economic shocks into the simulation:

  Event types (4+):
    NaturalDisaster      — reduces land values, triggers health claims
    MassTort             — injects liability cases into the court system
    Recession            — reduces business demand for a period
    InsuranceMarketStress — increases claim frequency across pools

  Each event has:
    trigger_step   — when the event fires
    magnitude      — strength of the shock (0..1 or count)
    duration       — steps the ongoing effect lasts (0 = instant)
    target         — which subsystem(s) are affected
    recovery_fn    — function describing how the effect decays

  Integration:
    EventManager holds the schedule, fires events at correct steps,
    and aggregates ongoing modifiers for the runner to apply.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable


# ════════════════════════════════════════════════════════════════════════
#  Recovery Functions
# ════════════════════════════════════════════════════════════════════════


def linear_recovery(initial: float, elapsed: int, duration: int) -> float:
    """Effect decays linearly from *initial* to 0 over *duration* steps."""
    if duration <= 0 or elapsed >= duration:
        return 0.0
    return initial * (1.0 - elapsed / duration)


def exponential_recovery(initial: float, elapsed: int, duration: int) -> float:
    """Effect decays exponentially.  Rate auto-scaled to *duration*."""
    if duration <= 0 or elapsed >= duration:
        return 0.0
    rate = 3.0 / max(duration, 1)
    return initial * math.exp(-rate * elapsed)


def step_recovery(initial: float, elapsed: int, duration: int) -> float:
    """Effect stays at full magnitude for *duration*, then drops to 0."""
    if duration <= 0 or elapsed >= duration:
        return 0.0
    return initial


RecoveryFn = Callable[[float, int, int], float]


# ════════════════════════════════════════════════════════════════════════
#  Base Shock Event
# ════════════════════════════════════════════════════════════════════════


@dataclass
class ShockEvent:
    """Base class for all shock events.

    Lifecycle
    ---------
    1. The runner instantiates events (or uses the default schedule).
    2. Each step the runner calls *apply(context, current_step)* on
       events whose *trigger_step* matches.
    3. apply() fires once, calling _apply_impl() for one-shot effects
       and setting internal state so *residual()* / *get_modifiers()*
       return ongoing-effect values for subsequent steps.
    4. The runner queries *get_modifiers()* each step to apply ongoing
       adjustments (demand_multiplier, claim_freq_multiplier, etc.).

    Parameters
    ----------
    name         : Human-readable label (e.g. "Hurricane_Alpha").
    trigger_step : Simulation step on which the event first fires.
    magnitude    : Strength of the shock (0.0–1.0 for fractions, or a
                   count for mass events).
    duration     : Number of steps the ongoing effect lasts (0 = instant).
    target       : Identifier of the affected subsystem, compact, insurer,
                   or 'all'.
    recovery_fn  : Decay function for the residual effect over *duration*.
    """

    name: str = "ShockEvent"
    trigger_step: int = 0
    magnitude: float = 0.0
    duration: int = 0
    target: str = "all"
    recovery_fn: RecoveryFn = linear_recovery

    # — Internal state ————————————————————————————————————————————
    _fired: bool = False
    _fire_step: int = -1

    # ── Public API ───────────────────────────────────────────────

    def apply(self, context: dict) -> list[str]:
        """Fire the event.  Called exactly once by the runner.

        Returns a list of human-readable log messages describing what
        happened.  Subclasses override _apply_impl() rather than this
        method.
        """
        if self._fired:
            return []
        self._fired = True
        self._fire_step = context.get("current_step", self.trigger_step)
        logs = self._apply_impl(context)
        logs.insert(0, f"🔥 EVENT FIRED: {self.name} (step {self._fire_step})")
        return logs

    def residual(self, current_step: int) -> float:
        """Return the current residual magnitude (decayed by recovery_fn).

        Returns 0.0 if the event hasn't fired, duration is 0, or
        duration has expired.
        """
        if not self._fired:
            return 0.0
        elapsed = current_step - self._fire_step
        if self.duration <= 0 or elapsed >= self.duration:
            return 0.0
        return self.recovery_fn(self.magnitude, elapsed, self.duration)

    def get_modifiers(self, current_step: int) -> dict[str, float]:
        """Per-step modifier dict for ongoing effects.

        Override in subclasses that have ongoing (multi-step) effects.
        Return an empty dict for instant-only events.

        Example return:  {'demand_multiplier': 0.7, 'claim_freq_multiplier': 1.5}
        """
        return {}

    # ── Subclass hook ────────────────────────────────────────────

    def _apply_impl(self, context: dict) -> list[str]:
        """Subclass-specific one-shot effects.  Returns log messages.

        *context* contains (at minimum):
            ledger            — LedgerEngine
            workers           — list[WorkerAgent]
            businesses        — list[BusinessAgent]
            guilds            — list[GuildAgent]
            court_system      — CourtSystem
            insurance_market  — InsuranceMarket
            harberger_market  — HarbergerMarket
            compact_utilities — dict[str, float]
            current_step      — int
        """
        return [f"  {self.name}: base event — no effects defined."]

    @property
    def is_active(self) -> bool:
        return self._fired


# ════════════════════════════════════════════════════════════════════════
#  Event 1: Natural Disaster
# ════════════════════════════════════════════════════════════════════════


class NaturalDisaster(ShockEvent):
    """A natural disaster (hurricane, earthquake, flood) that:

    * Reduces land values in *target* compact by *magnitude* %.
    * Reduces worker productivity (health proxy) by *magnitude*.
    * Triggers health insurance claims for affected workers.
    * Ongoing — claim frequency stays elevated during recovery period.
    """

    def __init__(
        self,
        name: str = "NaturalDisaster",
        trigger_step: int = 50,
        magnitude: float = 0.40,
        duration: int = 10,
        target: str = "compact_alpha",
        recovery_fn: RecoveryFn = linear_recovery,
    ):
        super().__init__(name, trigger_step, magnitude, duration, target, recovery_fn)

    def _apply_impl(self, context: dict) -> list[str]:
        logs: list[str] = []
        workers: list = context.get("workers", [])
        ledger = context.get("ledger")
        insurance_market = context.get("insurance_market")
        harberger_market = context.get("harberger_market")
        compact_name = self.target
        current_step = context.get("current_step", 0)

        # ── Identify affected workers ──────────────────────────────
        affected = [
            w for w in workers
            if getattr(w, "compact_id", None) == compact_name
        ]
        logs.append(
            f"  🌪  {self.name} strikes {compact_name} — "
            f"{len(affected)} workers affected"
        )

        if not affected:
            logs.append("  (no workers in target compact — event has no effect)")
            return logs

        # ── 1. Land value reduction ─────────────────────────────────
        total_land_loss = 0.0
        for w in affected:
            loss = w.land_value * self.magnitude
            w.land_value = max(0.0, w.land_value - loss)
            total_land_loss += loss

            # Sync ledger
            if ledger and ledger.entity_exists(w.id):
                bs = ledger.get_balance(w.id)
                bs.land_value = max(0.0, bs.land_value - loss)

        logs.append(
            f"  💰 Land values reduced by ${total_land_loss:,.2f} "
            f"in {compact_name}"
        )

        # ── 2. Worker productivity reduction (health proxy) ────────
        total_prod_loss = 0.0
        for w in affected:
            if hasattr(w, "productivity") and w.productivity > 0:
                prod_loss = w.productivity * self.magnitude * 0.3
                w.productivity = max(0.5, w.productivity - prod_loss)
                total_prod_loss += prod_loss

        logs.append(
            f"  🤒 Worker productivity reduced by average "
            f"${total_prod_loss / max(1, len(affected)):.2f}/hr (health impact)"
        )

        # ── 3. Trigger health claims ────────────────────────────────
        if insurance_market:
            claim_count = 0
            for w in affected:
                # claim probability proportional to disaster magnitude
                if random.random() < self.magnitude * 0.5:
                    claim_amount = random.uniform(500.0, 5_000.0) * (1.0 + self.magnitude)
                    try:
                        insurance_market.file_claim(w.id, claim_amount)
                        claim_count += 1
                    except Exception:
                        pass
            logs.append(f"  🏥 Filed {claim_count} disaster-related health claims")

        return logs

    def get_modifiers(self, current_step: int) -> dict[str, float]:
        r = self.residual(current_step)
        if r == 0.0:
            return {}
        return {"claim_freq_multiplier": 1.0 + r * 0.5}


# ════════════════════════════════════════════════════════════════════════
#  Event 2: Mass Tort
# ════════════════════════════════════════════════════════════════════════


class MassTort(ShockEvent):
    """A mass tort event that injects liability cases into the court system.

    * Creates *magnitude* cases (fractional values round up to 1).
    * Targets businesses — cases allege product liability / negligence.
    * Instant effect (duration = 0).
    """

    def __init__(
        self,
        name: str = "MassTort",
        trigger_step: int = 80,
        magnitude: float = 6.0,
        duration: int = 0,
        target: str = "all",
        recovery_fn: RecoveryFn = linear_recovery,
    ):
        super().__init__(name, trigger_step, magnitude, duration, target, recovery_fn)

    def _apply_impl(self, context: dict) -> list[str]:
        logs: list[str] = []
        court_system = context.get("court_system")
        businesses: list = context.get("businesses", [])
        workers: list = context.get("workers", [])
        current_step = context.get("current_step", 0)

        if not court_system or not businesses:
            return [f"  {self.name}: missing court_system or businesses, skipping."]

        # ── Determine target businesses ─────────────────────────────
        if self.target == "all":
            target_biz = [b for b in businesses if getattr(b, "alive", True)]
        else:
            target_biz = [
                b for b in businesses
                if getattr(b, "alive", True)
                and (b.id == self.target or self.target == "all")
            ]
            if not target_biz:
                target_biz = [b for b in businesses if getattr(b, "alive", True)]

        if not target_biz:
            return [f"  {self.name}: no targetable businesses, skipping."]

        # ── Import case creation ────────────────────────────────────
        try:
            from src.mechanics.courts import create_case
        except ImportError:
            try:
                from mechanics.courts import create_case
            except ImportError:
                return [f"  {self.name}: could not import create_case, skipping."]

        num_cases = max(1, int(self.magnitude))
        filed_count = 0

        for _ in range(num_cases):
            defendant = random.choice(target_biz)
            plaintiff = random.choice(workers)

            try:
                case = create_case(
                    plaintiff=plaintiff.id,
                    defendant=defendant.id,
                    claimed_amount=random.uniform(10_000.0, 100_000.0)
                    * (self.magnitude / 5.0),
                    evidence_strength=random.uniform(0.40, 0.90),
                    defendant_due_care=1.0 - random.uniform(0.05, 0.20),
                    foreseeability=random.uniform(0.50, 0.90),
                    comparative_negligence=random.uniform(0.0, 0.10),
                    willful=random.random() < 0.30,
                    description=(
                        f"Mass tort: {plaintiff.id} v. {defendant.id} "
                        f"({self.name}, step {current_step})"
                    ),
                )
                court_system.route_case(case, step=current_step)
                filed_count += 1
            except Exception:
                pass

        avg_claim = 50_000.0 * (self.magnitude / 5.0)
        logs.append(
            f"  ⚖️  Filed {filed_count} mass-tort cases against "
            f"{len(target_biz)} businesses"
        )
        logs.append(
            f"  💰 Est. avg. claim: ${avg_claim:,.0f} — "
            f"total exposure: ${filed_count * avg_claim:,.0f}"
        )

        return logs


# ════════════════════════════════════════════════════════════════════════
#  Event 3: Recession
# ════════════════════════════════════════════════════════════════════════


class Recession(ShockEvent):
    """An economic recession that reduces business demand.

    * Reduces the market demand factor by *magnitude* (e.g. 0.30 = −30 %).
    * Ongoing effect — demand gradually recovers via *recovery_fn*.
    * Also reduces worker productivity slightly (economic stress).
    """

    def __init__(
        self,
        name: str = "Recession",
        trigger_step: int = 100,
        magnitude: float = 0.30,
        duration: int = 20,
        target: str = "all",
        recovery_fn: RecoveryFn = exponential_recovery,
    ):
        super().__init__(name, trigger_step, magnitude, duration, target, recovery_fn)

    def _apply_impl(self, context: dict) -> list[str]:
        logs: list[str] = []
        current_step = context.get("current_step", 0)

        # ── Mild productivity hit from economic stress ──────────────
        workers: list = context.get("workers", [])
        for w in workers:
            if hasattr(w, "productivity") and w.productivity > 0:
                w.productivity = max(
                    0.5, w.productivity * (1.0 - self.magnitude * 0.15)
                )

        logs.append(
            f"  📉 RECESSION at step {current_step} — "
            f"demand drops {self.magnitude:.0%}"
        )
        logs.append(
            f"  ⏱  Recovery over {self.duration} steps "
            f"({'exponential' if self.recovery_fn == exponential_recovery else 'linear'})"
        )
        logs.append(f"  🎯 Affecting: {self.target}")
        return logs

    def get_modifiers(self, current_step: int) -> dict[str, float]:
        r = self.residual(current_step)
        if r == 0.0:
            return {}
        return {"demand_multiplier": 1.0 - r}


# ════════════════════════════════════════════════════════════════════════
#  Event 4: Insurance Market Stress
# ════════════════════════════════════════════════════════════════════════


class InsuranceMarketStress(ShockEvent):
    """A shock that increases claim frequency across insurance pools.

    * Claim frequency multiplier rises by *magnitude* (e.g. 0.50 = +50 %).
    * Constant for *duration* (step_recovery), then drops to 0.
    * Optionally targets a specific insurer by ID.
    """

    def __init__(
        self,
        name: str = "InsuranceMarketStress",
        trigger_step: int = 60,
        magnitude: float = 0.50,
        duration: int = 15,
        target: str = "all",
        recovery_fn: RecoveryFn = step_recovery,
    ):
        super().__init__(name, trigger_step, magnitude, duration, target, recovery_fn)

    def _apply_impl(self, context: dict) -> list[str]:
        logs: list[str] = []
        insurance_market = context.get("insurance_market")
        current_step = context.get("current_step", 0)

        logs.append(f"  🚑 Insurance market stress at step {current_step}")
        logs.append(
            f"  📈 Claim frequency +{self.magnitude:.0%} "
            f"for {self.duration} steps"
        )

        if insurance_market:
            ins_ids = list(getattr(insurance_market, "insurers", {}).keys())
            if self.target != "all" and self.target in ins_ids:
                logs.append(f"  🎯 Targeting insurer: {self.target}")
            else:
                logs.append(f"  🎯 Affecting all insurers ({', '.join(ins_ids)})")
        else:
            logs.append(f"  🎯 Affecting: {self.target} (no insurance market found)")
        return logs

    def get_modifiers(self, current_step: int) -> dict[str, float]:
        r = self.residual(current_step)
        if r == 0.0:
            return {}
        return {"claim_freq_multiplier": 1.0 + r}


# ════════════════════════════════════════════════════════════════════════
#  Event Manager
# ════════════════════════════════════════════════════════════════════════


class EventManager:
    """Holds the event schedule and coordinates firing + modifier aggregation.

    Usage in runner::

        em = EventManager(events=[...])
        for step in range(1, STEPS + 1):
            logs = em.fire_events(context, step)
            for msg in logs:
                print(msg)
            mods = em.get_active_modifiers(step)
            if 'demand_multiplier' in mods:
                demand_factor *= mods['demand_multiplier']
    """

    def __init__(self, events: list[ShockEvent] | None = None):
        self.events: list[ShockEvent] = list(events) if events else []

    # ── Schedule management ──────────────────────────────────────

    def add(self, event: ShockEvent) -> None:
        """Add a single event to the schedule."""
        self.events.append(event)

    def schedule(self, events: list[ShockEvent]) -> None:
        """Replace the schedule with a new list of events."""
        self.events = list(events)

    # ── Runtime ──────────────────────────────────────────────────

    def fire_events(self, context: dict, current_step: int) -> list[str]:
        """Fire all events whose *trigger_step* matches *current_step*.

        *context* is augmented with ``current_step`` and passed to
        each event's *apply()*.  Returns a combined list of log
        messages.
        """
        context["current_step"] = current_step
        all_logs: list[str] = []
        for event in self.events:
            if event.trigger_step == current_step and not event._fired:
                logs = event.apply(context)
                all_logs.extend(logs)
        return all_logs

    def get_active_modifiers(self, current_step: int) -> dict[str, float]:
        """Aggregate ongoing modifiers from all fired events.

        When multiple events affect the same modifier (e.g. two events
        both set ``claim_freq_multiplier``), the **maximum** value wins.
        """
        modifiers: dict[str, float] = {}
        for event in self.events:
            if event._fired:
                em = event.get_modifiers(current_step)
                for k, v in em.items():
                    if k not in modifiers or v > modifiers[k]:
                        modifiers[k] = v
        return modifiers

    # ── Introspection ─────────────────────────────────────────────

    @property
    def active_events(self) -> list[ShockEvent]:
        """Events that have fired and may still have ongoing effects."""
        return [e for e in self.events if e._fired]

    @property
    def pending_events(self) -> list[ShockEvent]:
        """Events that haven't fired yet."""
        return [e for e in self.events if not e._fired]

    def summary(self) -> list[dict]:
        """Return a human-readable summary of the full schedule."""
        return [
            {
                "name": e.name,
                "type": type(e).__name__,
                "trigger_step": e.trigger_step,
                "magnitude": e.magnitude,
                "duration": e.duration,
                "target": e.target,
                "fired": e._fired,
            }
            for e in self.events
        ]


# ════════════════════════════════════════════════════════════════════════
#  Default Event Schedule & Builder
# ════════════════════════════════════════════════════════════════════════

DEFAULT_EVENT_SCHEDULE: list[ShockEvent] = [
    NaturalDisaster(
        name="Hurricane_Alpha",
        trigger_step=50,
        magnitude=0.40,
        duration=10,
        target="compact_alpha",
    ),
    InsuranceMarketStress(
        name="Insurer_Crisis",
        trigger_step=60,
        magnitude=0.50,
        duration=15,
        target="all",
    ),
    MassTort(
        name="ClassAction_Wave",
        trigger_step=80,
        magnitude=6.0,
        duration=0,
        target="all",
    ),
    Recession(
        name="Economic_Recession",
        trigger_step=100,
        magnitude=0.30,
        duration=20,
        target="all",
    ),
]


def build_schedule(config: dict | None = None) -> EventManager:
    """Build an EventManager from a config dict or return defaults.

    The *config* dict should have the form::

        {
            "events": [
                {
                    "type": "NaturalDisaster",
                    "name": "MyDisaster",
                    "trigger_step": 50,
                    "magnitude": 0.40,
                    "duration": 10,
                    "target": "compact_alpha",
                },
                ...
            ]
        }
    """
    if config and "events" in config:
        type_map = {
            "naturaldisaster": NaturalDisaster,
            "natural_disaster": NaturalDisaster,
            "masstort": MassTort,
            "mass_tort": MassTort,
            "recession": Recession,
            "insurancemarketstress": InsuranceMarketStress,
            "insurance_market_stress": InsuranceMarketStress,
        }
        events: list[ShockEvent] = []
        for ec in config["events"]:
            raw_type = ec.pop("type", "naturaldisaster")
            cls = type_map.get(raw_type.lower())
            if cls is None:
                raise ValueError(
                    f"Unknown event type: {raw_type}. "
                    f"Valid: {list(type_map.keys())}"
                )
            events.append(cls(**ec))
        return EventManager(events)

    return EventManager(DEFAULT_EVENT_SCHEDULE)
