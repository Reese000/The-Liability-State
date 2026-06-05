"""
adversarial/controller.py — Strategy Controller for Phase 3 adversarial behavior.

Evaluates each agent's available strategies each step and returns the best one
(honest or exploit) based on expected value with honesty discount θ.

Spec reference:
  - ADVERSARIAL_STRATEGIES.md (full strategy library of 81 strategies)
  - AGENT_MODEL.md §5 (honesty parameter θ and strategy switching logic)
"""

from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════════
#  Data containers
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class StrategyEvaluation:
    """Result of evaluating a single strategy for one agent."""

    strategy_name: str
    is_honest: bool
    expected_value: float
    detection_probability: float
    reward: float
    penalty: float
    prerequisites_met: bool
    details: str = ""


@dataclass
class AgentContext:
    """
    Normalised view of an agent's state for strategy evaluation.

    Extracts the common attributes from WorkerAgent, BusinessAgent,
    GuildAgent, etc. so strategies are agent-type-agnostic.
    """

    agent_id: str
    agent_type: str  # 'worker', 'business', 'guild'

    # ── Behavioural parameters ───────────────────────────────────
    honesty: float = 0.5       # θ ∈ [0, 1]
    inertia: float = 0.3       # λ ∈ [0, 1]
    concealment: float = 0.0   # concealment investment ∈ [0, 1]

    # ── Economic state ───────────────────────────────────────────
    cash: float = 0.0
    land_value: float = 0.0
    property_count: int = 0
    revenue: float = 0.0
    income: float = 0.0
    outstanding_liability: float = 0.0

    # ── Insurance state ──────────────────────────────────────────
    has_insurance: bool = False
    insurance_coverage: float = 0.0
    insurance_premium: float = 0.0
    risk_profile: float = 0.05  # True risk ∈ [0,1]

    # ── Guild / Business specifics ───────────────────────────────
    member_count: int = 0
    worker_count: int = 0
    guild_ids: list[str] = field(default_factory=list)

    # ── Market / system context (set by controller) ──────────────
    step: int = 0
    compact_id: str = ""

    # ── Extra fields for strategy-specific logic ─────────────────
    extra: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
#  Abstract base for all adversarial strategies
# ═══════════════════════════════════════════════════════════════════════


class AdversarialStrategy(ABC):
    """Base class for all adversarial / exploitative strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy identifier."""
        ...

    @property
    def is_honest(self) -> bool:
        """False for all adversarial strategies (overridden by HonestBaseline)."""
        return False

    @abstractmethod
    def check_prerequisites(self, agent: AgentContext) -> bool:
        """Return True if the agent can attempt this strategy."""
        ...

    @abstractmethod
    def reward(self, agent: AgentContext) -> float:
        """Gross reward if the strategy succeeds undetected."""
        ...

    @abstractmethod
    def penalty(self, agent: AgentContext) -> float:
        """Penalty if the strategy is detected / fails."""
        ...

    @abstractmethod
    def _detection_probability_raw(self, agent: AgentContext) -> float:
        """Base detection probability before any modifiers."""
        ...

    def detection_probability(self, agent: AgentContext) -> float:
        """
        Full detection probability including concealment modifiers.

        P_detect = max(0, min(1, P_raw * (1 - concealment) - concealment_bonus))
        """
        p_raw = self._detection_probability_raw(agent)
        # Concealment investment reduces detection
        p_mod = p_raw * (1.0 - agent.concealment * 0.5) - agent.concealment * 0.05
        return max(0.0, min(1.0, p_mod))

    def expected_value(self, agent: AgentContext) -> float:
        """
        Expected value calculation:

            eV = P(success) × reward + P(detection) × penalty

        Where P(success) = 1 - P_detect.
        Penalty is negative (so it reduces expected value).
        """
        p_detect = self.detection_probability(agent)
        p_success = 1.0 - p_detect
        r = self.reward(agent)
        pnl = self.penalty(agent)  # should be negative (cost)

        ev = p_success * r + p_detect * pnl
        return ev

    def evaluate(self, agent: AgentContext) -> StrategyEvaluation:
        """Full evaluation including prerequisites check."""
        prereqs = self.check_prerequisites(agent)
        if not prereqs:
            return StrategyEvaluation(
                strategy_name=self.name,
                is_honest=self.is_honest,
                expected_value=0.0,
                detection_probability=0.0,
                reward=0.0,
                penalty=0.0,
                prerequisites_met=False,
                details=f"Prerequisites not met: {self._prereq_failure_reason(agent)}",
            )
        p_detect = self.detection_probability(agent)
        r = self.reward(agent)
        pnl = self.penalty(agent)
        ev = self.expected_value(agent)
        return StrategyEvaluation(
            strategy_name=self.name,
            is_honest=self.is_honest,
            expected_value=ev,
            detection_probability=p_detect,
            reward=r,
            penalty=pnl,
            prerequisites_met=True,
            details=self._evaluation_details(agent, ev, p_detect, r, pnl),
        )

    def _prereq_failure_reason(self, agent: AgentContext) -> str:
        """Override to provide a human-readable failure reason."""
        return "Conditions not satisfied"

    def _evaluation_details(
        self,
        agent: AgentContext,
        ev: float,
        p_detect: float,
        reward: float,
        penalty: float,
    ) -> str:
        """Override for strategy-specific detail strings."""
        return (
            f"eV={ev:.2f} = P(success)={1-p_detect:.2f}×${reward:.2f} + "
            f"P(detect)={p_detect:.2f}×${penalty:.2f}"
        )


# ═══════════════════════════════════════════════════════════════════════
#  Honest Baseline Strategy
# ═══════════════════════════════════════════════════════════════════════


class HonestBaseline(AdversarialStrategy):
    """
    The 'honest' baseline — no exploitation, just normal economic activity.

    Always has prerequisites met. Its expected value represents the utility
    of playing by the rules.
    """

    @property
    def name(self) -> str:
        return "honest"

    @property
    def is_honest(self) -> bool:
        return True

    def check_prerequisites(self, agent: AgentContext) -> bool:
        return True

    def reward(self, agent: AgentContext) -> float:
        # Normal economic output — use a fraction to represent
        # net surplus/profit from honest activity (not gross revenue)
        base = max(agent.income, agent.revenue, agent.cash * 0.01, 0.0)
        return base * 0.15  # ~15% net return

    def penalty(self, agent: AgentContext) -> float:
        # No penalty for being honest; just baseline costs
        return max(agent.outstanding_liability, 0.0) * -0.1

    def _detection_probability_raw(self, agent: AgentContext) -> float:
        return 0.0  # Nothing to detect

    def expected_value(self, agent: AgentContext) -> float:
        # Honest baseline isn't discounted by θ
        r = self.reward(agent)
        pnl = self.penalty(agent)
        return r + pnl

    def evaluate(self, agent: AgentContext) -> StrategyEvaluation:
        ev = self.expected_value(agent)
        return StrategyEvaluation(
            strategy_name=self.name,
            is_honest=True,
            expected_value=ev,
            detection_probability=0.0,
            reward=self.reward(agent),
            penalty=self.penalty(agent),
            prerequisites_met=True,
            details=f"Honest baseline eV = ${ev:.2f}",
        )


# ═══════════════════════════════════════════════════════════════════════
#  1. Premium Evasion
# ═══════════════════════════════════════════════════════════════════════


class PremiumEvasion(AdversarialStrategy):
    """
    Risk under-reporting to reduce insurance premiums.
    (ADVERSARIAL_STRATEGIES.md §1.1)
    """

    @property
    def name(self) -> str:
        return "premium_evasion"

    def check_prerequisites(self, agent: AgentContext) -> bool:
        return (
            agent.has_insurance
            and agent.insurance_premium > 0.0
            and agent.risk_profile > 0.02
        )

    def reward(self, agent: AgentContext) -> float:
        """Premium savings from under-declaring risk over several steps."""
        savings_per_step = agent.insurance_premium * agent.risk_profile * 0.6
        steps = max(3.0, 8.0 * (1.0 + agent.concealment))
        return savings_per_step * steps

    def penalty(self, agent: AgentContext) -> float:
        """Back premiums owed + fine."""
        gain = agent.insurance_premium * agent.risk_profile * 0.6 * 6.0
        return -gain * 1.8

    def _detection_probability_raw(self, agent: AgentContext) -> float:
        base = 0.15 + 0.15 * agent.risk_profile * 10.0
        return max(0.05, min(0.65, base - agent.concealment * 0.15))


# ═══════════════════════════════════════════════════════════════════════
#  2. Insurance Fraud
# ═══════════════════════════════════════════════════════════════════════


class InsuranceFraud(AdversarialStrategy):
    """
    Fabricated claim — filing a claim for a loss that never occurred.
    (ADVERSARIAL_STRATEGIES.md §2.1)
    """

    @property
    def name(self) -> str:
        return "insurance_fraud"

    def check_prerequisites(self, agent: AgentContext) -> bool:
        return agent.has_insurance and agent.insurance_coverage > 0.0

    def reward(self, agent: AgentContext) -> float:
        """
        Claim payout if approved.
        Higher coverage → bigger potential payout.
        """
        claim_payout = agent.insurance_coverage * 0.35
        p_approval = 0.55 + agent.concealment * 0.25
        return claim_payout * p_approval

    def penalty(self, agent: AgentContext) -> float:
        """Legal penalties if caught (severe but not ruinous)."""
        claim_payout = agent.insurance_coverage * 0.35
        return -claim_payout * 1.5

    def _detection_probability_raw(self, agent: AgentContext) -> float:
        base = 0.20 + 0.15 * min(1.0, agent.insurance_coverage / 200000.0)
        return max(0.10, min(0.70, base - agent.concealment * 0.15))


# ═══════════════════════════════════════════════════════════════════════
#  3. Harberger Gaming
# ═══════════════════════════════════════════════════════════════════════


class HarbergerGaming(AdversarialStrategy):
    """
    Land value under-declaration to reduce LVT.
    (ADVERSARIAL_STRATEGIES.md §3.1)
    """

    @property
    def name(self) -> str:
        return "harberger_gaming"

    def check_prerequisites(self, agent: AgentContext) -> bool:
        return agent.land_value > 10000.0 and agent.property_count > 0

    def reward(self, agent: AgentContext) -> float:
        """
        LVT savings from under-declaring land value over expected holding period.
        """
        lvt_rate = 0.02
        under_declare_frac = 0.15 + agent.concealment * 0.20  # 15-35% under-declaration
        savings_per_step = agent.land_value * under_declare_frac * lvt_rate
        p_sale = self._forced_sale_probability(agent)
        expected_steps = max(3.0, 12.0 * (1.0 - p_sale))
        return savings_per_step * expected_steps

    def penalty(self, agent: AgentContext) -> float:
        """Loss if forced sale occurs at the low declared price."""
        p_sale = self._forced_sale_probability(agent)
        under_declare_frac = 0.15 + agent.concealment * 0.20
        loss = agent.land_value * under_declare_frac
        return -loss * p_sale

    def _forced_sale_probability(self, agent: AgentContext) -> float:
        """Probability that someone buys the land at declared price."""
        return min(0.50, 0.05 + (0.15 + agent.concealment * 0.20) * 0.4)

    def _detection_probability_raw(self, agent: AgentContext) -> float:
        return self._forced_sale_probability(agent)


# ═══════════════════════════════════════════════════════════════════════
#  4. Court Flooding
# ═══════════════════════════════════════════════════════════════════════


class CourtFlooding(AdversarialStrategy):
    """
    Frivolous mass litigation — filing many low-merit lawsuits
    hoping for nuisance settlements. (ADVERSARIAL_STRATEGIES.md §4.1)
    """

    @property
    def name(self) -> str:
        return "court_flooding"

    def check_prerequisites(self, agent: AgentContext) -> bool:
        return agent.cash > 5000.0  # Need at least some capital

    def reward(self, agent: AgentContext) -> float:
        """
        Expected settlement revenue from nuisance suits.
        Scales with agent's cash (ability to fund litigation).
        """
        num_cases = max(1.0, min(6.0, agent.cash / 15000.0))
        settlement_per_case = 3000.0
        p_settlement = 0.30 + agent.concealment * 0.15
        return num_cases * settlement_per_case * p_settlement

    def penalty(self, agent: AgentContext) -> float:
        """
        Costs from lost cases under English Rule.
        """
        num_cases = max(1.0, min(6.0, agent.cash / 15000.0))
        expected_losses = num_cases * 0.3 * 5000.0  # 30% lose, $5K each
        return -expected_losses

    def _detection_probability_raw(self, agent: AgentContext) -> float:
        num_cases = max(1.0, min(6.0, agent.cash / 15000.0))
        return 0.25 + 0.06 * num_cases


# ═══════════════════════════════════════════════════════════════════════
#  5. Guild Rent-Seeking
# ═══════════════════════════════════════════════════════════════════════


class GuildRentSeeking(AdversarialStrategy):
    """
    Closed shop / membership restriction — guild restricts membership
    to raise wages for existing members. (ADVERSARIAL_STRATEGIES.md §5.1)
    """

    @property
    def name(self) -> str:
        return "guild_rent_seeking"

    def check_prerequisites(self, agent: AgentContext) -> bool:
        return agent.member_count > 2 and agent.agent_type in ("guild", "unknown")

    def reward(self, agent: AgentContext) -> float:
        """Wage premium from artificial scarcity over period."""
        premium_per_member = 400.0
        return premium_per_member * agent.member_count * 2.0

    def penalty(self, agent: AgentContext) -> float:
        """Antitrust penalty + reputation loss."""
        gain = 400.0 * agent.member_count * 2.0
        return -gain * 1.2

    def _detection_probability_raw(self, agent: AgentContext) -> float:
        visibility = min(1.0, agent.member_count / 30.0)
        return 0.20 + visibility * 0.30


# ═══════════════════════════════════════════════════════════════════════
#  6. Collusion
# ═══════════════════════════════════════════════════════════════════════


class Collusion(AdversarialStrategy):
    """
    Price-fixing cartel — businesses agree to fix prices above
    competitive levels. (ADVERSARIAL_STRATEGIES.md §6.1)
    """

    @property
    def name(self) -> str:
        return "collusion"

    def check_prerequisites(self, agent: AgentContext) -> bool:
        return agent.revenue > 5000.0 and agent.agent_type in ("business", "unknown")

    def reward(self, agent: AgentContext) -> float:
        """Cartel profit: extra markup on revenue over several steps."""
        markup = 0.15  # 15% price increase
        return agent.revenue * markup * 3.0  # 3 steps

    def penalty(self, agent: AgentContext) -> float:
        """Antitrust penalties if caught."""
        gain = agent.revenue * 0.15 * 3.0
        return -gain * 1.5

    def _detection_probability_raw(self, agent: AgentContext) -> float:
        visibility = min(1.0, agent.revenue / 80000.0)
        return 0.15 + visibility * 0.25


# ═══════════════════════════════════════════════════════════════════════
#  7. Contract Breach
# ═══════════════════════════════════════════════════════════════════════


class ContractBreach(AdversarialStrategy):
    """
    Efficient breach — breaching a contract and paying damages
    is more profitable than performing. (ADVERSARIAL_STRATEGIES.md §8.1)
    """

    @property
    def name(self) -> str:
        return "contract_breach"

    def check_prerequisites(self, agent: AgentContext) -> bool:
        return (agent.income > 0.0 or agent.revenue > 0.0) and agent.cash > 100.0

    def reward(self, agent: AgentContext) -> float:
        """Cost saved by not performing the contract."""
        return max(agent.income, agent.revenue) * 0.20

    def penalty(self, agent: AgentContext) -> float:
        """P(sued) × damages (expectation damages + costs)."""
        contract_value = max(agent.income, agent.revenue) * 0.20
        p_sued = 0.5
        return -p_sued * contract_value * 1.3

    def _detection_probability_raw(self, agent: AgentContext) -> float:
        """Detection certain (counterparty knows). P(sued) scales with wealth."""
        wealth_factor = min(1.0, agent.cash / 100000.0)
        return 0.30 + wealth_factor * 0.35


# ═══════════════════════════════════════════════════════════════════════
#  8. LVT Evasion
# ═══════════════════════════════════════════════════════════════════════


class LvtEvasion(AdversarialStrategy):
    """
    Strategic land fragmentation — subdividing land to fall below
    LVT thresholds. (ADVERSARIAL_STRATEGIES.md §11.1)
    """

    @property
    def name(self) -> str:
        return "lvt_evasion"

    def check_prerequisites(self, agent: AgentContext) -> bool:
        return agent.land_value > 0.0 and agent.property_count > 1

    def reward(self, agent: AgentContext) -> float:
        """LVT savings from fragmentation over several steps."""
        lvt_rate = 0.02
        savings_fraction = 0.15 + agent.concealment * 0.20  # 15-35% reduction
        return agent.land_value * lvt_rate * savings_fraction * 10.0

    def penalty(self, agent: AgentContext) -> float:
        """Back taxes + penalties if caught."""
        lvt_rate = 0.02
        savings_fraction = 0.15 + agent.concealment * 0.20
        gain = agent.land_value * lvt_rate * savings_fraction * 10.0
        return -gain * 1.5

    def _detection_probability_raw(self, agent: AgentContext) -> float:
        density = min(1.0, agent.property_count / 8.0)
        return 0.20 + density * 0.25


# ═══════════════════════════════════════════════════════════════════════
#  Strategy Registry
# ═══════════════════════════════════════════════════════════════════════

# All built-in strategies (the 8 required + honest baseline)
BUILTIN_STRATEGIES: list[AdversarialStrategy] = [
    HonestBaseline(),
    PremiumEvasion(),
    InsuranceFraud(),
    HarbergerGaming(),
    CourtFlooding(),
    GuildRentSeeking(),
    Collusion(),
    ContractBreach(),
    LvtEvasion(),
]


# ═══════════════════════════════════════════════════════════════════════
#  Strategy Controller
# ═══════════════════════════════════════════════════════════════════════


class StrategyController:
    """
    Evaluates each agent's available strategies each step and returns
    the best one (honest or exploit) based on expected value with
    honesty discount θ.

    Selection logic (from ADVERSARIAL_STRATEGIES.md § "Strategy Selection"):

        For each strategy S that meets prerequisites:
            eV(S) = P(success) × reward(S) + P(detection) × penalty(S)

            Apply honesty discount:
                eV_adjusted(S) = eV(S) * agent.honesty    if S != 'honest'

            If eV_adjusted(S) > eV(honest) × (1 + agent.inertia):
                agent switches to strategy S

    Parameters
    ----------
    strategies : list of AdversarialStrategy
        The pool of strategies to evaluate (default: BUILTIN_STRATEGIES).
    register_strategies : list of AdversarialStrategy, optional
        Additional custom strategies to register at construction.
    """

    def __init__(
        self,
        strategies: Optional[list[AdversarialStrategy]] = None,
        register_strategies: Optional[list[AdversarialStrategy]] = None,
    ):
        self.strategies: list[AdversarialStrategy] = (
            list(strategies) if strategies is not None else list(BUILTIN_STRATEGIES)
        )
        if register_strategies:
            self.strategies.extend(register_strategies)

        # Index strategies by name for fast lookup
        self._strategy_map: dict[str, AdversarialStrategy] = {
            s.name: s for s in self.strategies
        }

    # ── Strategy management ──────────────────────────────────────

    def register_strategy(self, strategy: AdversarialStrategy) -> None:
        """Add a single custom strategy to the controller."""
        self.strategies.append(strategy)
        self._strategy_map[strategy.name] = strategy

    def get_strategy(self, name: str) -> Optional[AdversarialStrategy]:
        """Look up a strategy by name."""
        return self._strategy_map.get(name)

    def list_strategies(self) -> list[str]:
        """Return names of all registered strategies."""
        return [s.name for s in self.strategies]

    # ── Agent adaptation ─────────────────────────────────────────

    @staticmethod
    def adapt_agent(agent: Any) -> AgentContext:
        """
        Adapt any agent type (WorkerAgent, BusinessAgent, GuildAgent,
        or dict) into a normalised AgentContext.

        This method introspects the agent's attributes / dict keys, so
        it works with any class that follows the conventions of the
        simulation or plain dict representations.
        """

        def _get(attr: str, default: Any = None) -> Any:
            """Read from dict key or object attribute."""
            if isinstance(agent, dict):
                return agent.get(attr, default)
            return getattr(agent, attr, default)

        agent_id = str(
            _get("id", _get("agent_id", str(agent)))
        )

        # Determine agent type
        agent_type: str = "unknown"
        if isinstance(agent, dict):
            agent_type = str(_get("type", _get("agent_type", "unknown")))
        else:
            class_name = type(agent).__name__.lower()
            if "worker" in class_name:
                agent_type = "worker"
            elif "business" in class_name:
                agent_type = "business"
            elif "guild" in class_name:
                agent_type = "guild"
            else:
                agent_type = class_name

        # ── Economic state ───────────────────────────────────────
        cash: float = 0.0
        try:
            _cash = _get("cash", 0.0)
            if callable(_cash):
                _cash = _cash()
            cash = float(_cash)
        except Exception:
            cash = 0.0

        land_value: float = 0.0
        try:
            land_value = float(_get("land_value", 0.0))
        except Exception:
            land_value = 0.0

        revenue: float = 0.0
        try:
            revenue = float(_get("revenue", _get("current_revenue", 0.0)))
        except Exception:
            revenue = 0.0

        income: float = 0.0
        try:
            income = float(_get("income", _get("total_labor_income", 0.0)))
        except Exception:
            income = 0.0

        property_count: int = 0
        try:
            property_count = int(_get("property_count", 0))
        except Exception:
            property_count = 0

        outstanding_liability: float = 0.0
        try:
            outstanding_liability = float(_get("outstanding_liability", 0.0))
        except Exception:
            outstanding_liability = 0.0

        # Try ledger if available
        ledger = _get("ledger", None)
        if ledger is not None and hasattr(ledger, "get_balance"):
            try:
                bs = ledger.get_balance(agent_id)
                property_count = getattr(bs, "property_count", property_count)
                outstanding_liability = getattr(
                    bs, "outstanding_liability", outstanding_liability
                )
            except Exception:
                pass

        # ── Behavioural parameters ───────────────────────────────
        try:
            honesty = float(_get("honesty", 0.5))
        except Exception:
            honesty = 0.5

        try:
            inertia = float(_get("inertia", 0.3))
        except Exception:
            inertia = 0.3

        # ── Insurance state ──────────────────────────────────────
        has_insurance = bool(_get("has_insurance", False))

        insurance_coverage: float = 0.0
        try:
            insurance_coverage = float(_get("insurance_coverage", 0.0))
        except Exception:
            insurance_coverage = 0.0

        insurance_premium: float = 0.0
        try:
            insurance_premium = float(_get("insurance_premium", 0.0))
        except Exception:
            insurance_premium = 0.0

        risk_profile: float = 0.05
        try:
            risk_profile = float(_get("risk_profile", 0.05))
        except Exception:
            risk_profile = 0.05

        # ── Guild / Business specifics ───────────────────────────
        def _count(attr: str) -> int:
            v = _get(attr, 0)
            if callable(v):
                v = v()
            try:
                return int(v)
            except (ValueError, TypeError):
                return 0

        member_count = _count("member_count")
        worker_count = _count("labor_count")

        # ── Concealment investment ───────────────────────────────
        concealment: float = 0.0
        try:
            concealment = float(_get("concealment", max(0.0, 0.3 - honesty * 0.4)))
        except Exception:
            concealment = max(0.0, 0.3 - honesty * 0.4)

        # ── Compact & guild IDs ──────────────────────────────────
        compact_id = str(_get("compact_id", ""))

        _guild_ids = _get("guild_ids", [])
        if not isinstance(_guild_ids, list):
            try:
                _guild_ids = list(_guild_ids)
            except TypeError:
                _guild_ids = []
        guild_ids: list[str] = [str(g) for g in _guild_ids]

        _guild_id = _get("guild_id", None)
        if _guild_id and str(_guild_id) not in guild_ids:
            guild_ids.append(str(_guild_id))

        return AgentContext(
            agent_id=agent_id,
            agent_type=agent_type,
            honesty=honesty,
            inertia=inertia,
            concealment=concealment,
            cash=cash,
            land_value=land_value,
            property_count=property_count,
            revenue=revenue,
            income=income,
            outstanding_liability=outstanding_liability,
            has_insurance=has_insurance,
            insurance_coverage=insurance_coverage,
            insurance_premium=insurance_premium,
            risk_profile=risk_profile,
            member_count=member_count,
            worker_count=worker_count,
            guild_ids=guild_ids,
            compact_id=compact_id,
        )

    # ── Core evaluation ──────────────────────────────────────────

    def evaluate(
        self,
        agent: Any,
        context: Optional[AgentContext] = None,
    ) -> list[StrategyEvaluation]:
        """
        Evaluate all strategies for a given agent.

        Returns a list of StrategyEvaluation objects sorted by
        adjusted expected value (descending).

        Parameters
        ----------
        agent : Any
            The agent to evaluate (any type with compatible attributes).
        context : AgentContext, optional
            Pre-computed agent context. If None, it is auto-adapted.

        Returns
        -------
        list[StrategyEvaluation]
            All strategy evaluations, sorted by adjusted eV descending.
        """
        if context is None:
            ctx = self.adapt_agent(agent)
        else:
            ctx = context

        results: list[StrategyEvaluation] = []
        for strategy in self.strategies:
            evaluation = strategy.evaluate(ctx)
            results.append(evaluation)

        # Sort by adjusted expected value descending
        # (honesty discount applied to non-honest strategies)
        results.sort(key=lambda r: self._adjusted_ev(r, ctx), reverse=True)
        return results

    def best_strategy(
        self,
        agent: Any,
        context: Optional[AgentContext] = None,
    ) -> StrategyEvaluation:
        """
        Return the single best strategy for this agent.

        The best strategy is the one with the highest adjusted expected
        value after applying the honesty discount.
        """
        evaluations = self.evaluate(agent, context)
        return evaluations[0] if evaluations else self._empty_evaluation()

    def decide_switch(
        self,
        agent: Any,
        context: Optional[AgentContext] = None,
    ) -> Optional[str]:
        """
        Decide whether the agent should switch strategies.

        Returns the strategy name to switch to, or None to stay on
        current (honest) strategy.

        Logic:
            1. Find best adversarial strategy (highest eV after θ discount).
            2. Compare with honest baseline eV × (1 + inertia).
            3. Only switch if adversarial eV exceeds the inertia-adjusted
               honest baseline.
        """
        if context is None:
            ctx = self.adapt_agent(agent)
        else:
            ctx = context

        evaluations = self.evaluate(agent, ctx)

        # Find honest baseline evaluation
        honest_ev = 0.0
        best_adversarial: Optional[StrategyEvaluation] = None

        for ev in evaluations:
            if ev.is_honest and ev.prerequisites_met:
                honest_ev = ev.expected_value
            elif not ev.is_honest and ev.prerequisites_met:
                # Apply honesty discount to adversarial eV
                adj_ev = ev.expected_value * (1.0 - ctx.honesty)
                if best_adversarial is None or adj_ev > best_adversarial.expected_value * (1.0 - ctx.honesty):
                    best_adversarial = ev

        if best_adversarial is None:
            return None  # No viable adversarial strategy

        # Apply inertia threshold: adversarial must exceed honest baseline × (1 + inertia)
        threshold = honest_ev * (1.0 + ctx.inertia)

        adj_best_ev = best_adversarial.expected_value * (1.0 - ctx.honesty)

        if adj_best_ev > threshold:
            return best_adversarial.strategy_name

        return None  # Stay honest

    def step(
        self,
        agents: list[Any],
    ) -> dict[str, Any]:
        """
        Run the controller over a list of agents for one simulation step.

        For each agent:
          1. Adapt to AgentContext.
          2. Evaluate all strategies.
          3. Decide whether to switch.

        Parameters
        ----------
        agents : list[Any]
            List of agent objects to evaluate.

        Returns
        -------
        dict
            Step result with:
              - 'switches': list of dicts {agent_id, from_strategy, to_strategy, reason}
              - 'evaluations': dict[agent_id, list[StrategyEvaluation]]
              - 'summary': dict with counts
        """
        switches: list[dict] = []
        all_evaluations: dict[str, list[StrategyEvaluation]] = {}
        strategy_counts: dict[str, int] = {}

        for agent in agents:
            ctx = self.adapt_agent(agent)
            evals = self.evaluate(agent, ctx)
            all_evaluations[ctx.agent_id] = evals

            # Find current vs best
            current = "honest"
            switch_to = self.decide_switch(agent, ctx)

            if switch_to is not None and switch_to != current:
                switches.append({
                    "agent_id": ctx.agent_id,
                    "agent_type": ctx.agent_type,
                    "honesty": round(ctx.honesty, 3),
                    "inertia": round(ctx.inertia, 3),
                    "from_strategy": current,
                    "to_strategy": switch_to,
                    "reason": "Adversarial EV exceeds honest baseline × (1+inertia)",
                })

            chosen = switch_to or "honest"
            strategy_counts[chosen] = strategy_counts.get(chosen, 0) + 1

        return {
            "switches": switches,
            "evaluations": all_evaluations,
            "summary": {
                "total_agents": len(agents),
                "switched_count": len(switches),
                "strategy_distribution": strategy_counts,
            },
        }

    # ── Internal helpers ─────────────────────────────────────────

    @staticmethod
    def _adjusted_ev(
        evaluation: StrategyEvaluation,
        context: AgentContext,
    ) -> float:
        """
        Apply honesty discount θ to adversarial strategies.

        The honesty parameter θ ∈ [0,1] represents the agent's moral
        constraint.  A fully honest agent (θ ≈ 1) heavily discounts
        exploitative actions; a fully amoral agent (θ ≈ 0) applies
        no discount.

        Adjusted EV = eV * (1 - θ)   if S != 'honest'
        """
        if evaluation.is_honest or not evaluation.prerequisites_met:
            return evaluation.expected_value
        # Higher honesty → larger discount (adversarial less attractive)
        return evaluation.expected_value * (1.0 - context.honesty)

    @staticmethod
    def _empty_evaluation() -> StrategyEvaluation:
        return StrategyEvaluation(
            strategy_name="none",
            is_honest=True,
            expected_value=0.0,
            detection_probability=0.0,
            reward=0.0,
            penalty=0.0,
            prerequisites_met=False,
            details="No strategies available",
        )


# ═══════════════════════════════════════════════════════════════════════
#  Demo / Test Harness
# ═══════════════════════════════════════════════════════════════════════


def run_demo():
    """
    Demo that creates 20 agents with varying honesty (0.2-0.95) and
    shows which agents switch to which adversarial strategies.

    The demo simulates a standalone run of the StrategyController
    without needing the full simulation engine. Agents are represented
    as simple dict-like objects for the purpose of this demo.
    """
    print("=" * 72)
    print("  STRATEGY CONTROLLER DEMO")
    print("  Phase 3 Adversarial Behavior — Honesty Variation")
    print("=" * 72)

    # ── Create controller ────────────────────────────────────────
    controller = StrategyController()

    print(f"\nRegistered strategies ({len(controller.strategies)}):")
    for s in controller.strategies:
        print(f"  • {s.name:25s} {'(honest)' if s.is_honest else '(adversarial)'}")
    print()

    # ── Create 20 demo agents with varying honesty ───────────────
    agents = _create_demo_agents(count=20)
    print(f"Created {len(agents)} demo agents:\n")
    print(f"  {'Agent':<12s} {'Type':<10s} {'Honesty(θ)':<12s} {'Inertia(λ)':<12s} {'Cash':<10s} {'Insurance':<10s}")
    print(f"  {'-'*12} {'-'*10} {'-'*12} {'-'*12} {'-'*10} {'-'*10}")
    for a in agents:
        print(
            f"  {a['id']:<12s} {a['type']:<10s} {a['honesty']:<12.3f} "
            f"{a['inertia']:<12.3f} ${a['cash']:<8,.0f} {str(a['has_insurance']):<10s}"
        )

    # ── Run controller step ──────────────────────────────────────
    print("\n" + "-" * 72)
    print("  Running Strategy Controller step()...")
    print("-" * 72)

    result = controller.step(agents)

    # ── Print results ────────────────────────────────────────────
    print(f"\n  Total agents evaluated: {result['summary']['total_agents']}")
    print(f"  Agents that switched:  {result['summary']['switched_count']}")
    print()

    if result["switches"]:
        # Group by strategy
        by_strategy: dict[str, list[dict]] = {}
        for sw in result["switches"]:
            strat = sw["to_strategy"]
            by_strategy.setdefault(strat, []).append(sw)

        print(f"  {'Agent':<12s} {'Type':<10s} {'θ':<6s} {'λ':<6s} {'Strategy':<20s}")
        print(f"  {'-'*12} {'-'*10} {'-'*6} {'-'*6} {'-'*20}")
        for sw in sorted(result["switches"], key=lambda x: x["honesty"]):
            print(
                f"  {sw['agent_id']:<12s} {sw['agent_type']:<10s} "
                f"{sw['honesty']:<6.3f} {sw['inertia']:<6.3f} "
                f"{sw['to_strategy']:<20s}"
            )

        print(f"\n  Per-strategy breakdown:")
        for strat, agents_list in sorted(by_strategy.items()):
            avg_honesty = sum(a["honesty"] for a in agents_list) / len(agents_list)
            avg_inertia = sum(a["inertia"] for a in agents_list) / len(agents_list)
            print(
                f"    {strat:<20s}: {len(agents_list):>2d} agents "
                f"(avg θ={avg_honesty:.3f}, avg λ={avg_inertia:.3f})"
            )
    else:
        print("  No agents switched to adversarial strategies this step.")
        print("  (Honest baseline expected value exceeds all adversarial options)")

    # ── Strategy distribution ────────────────────────────────────
    print(f"\n  Strategy distribution:")
    for strat, count in sorted(
        result["summary"]["strategy_distribution"].items(),
        key=lambda x: -x[1],
    ):
        pct = count / result["summary"]["total_agents"] * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"    {strat:<20s}: {count:>2d}/{result['summary']['total_agents']} ({pct:5.1f}%) {bar}")

    # ── Per-agent detailed breakdown for a few interesting cases ──
    print("\n" + "-" * 72)
    print("  Detailed evaluations for selected agents")
    print("-" * 72)

    # Pick agents with low, medium, and high honesty
    sorted_agents = sorted(agents, key=lambda a: a["honesty"])
    selected = [sorted_agents[0], sorted_agents[len(sorted_agents)//2], sorted_agents[-1]]

    for agent_data in selected:
        ctx = controller.adapt_agent(agent_data)
        evals = controller.evaluate(agent_data, ctx)

        print(f"\n  Agent: {ctx.agent_id} ({ctx.agent_type})  θ={ctx.honesty:.3f}  λ={ctx.inertia:.3f}")
        print(f"  {'Strategy':<22s} {'Prereqs':<8s} {'eV':<10s} {'P(detect)':<10s} {'Adj eV':<10s}")
        print(f"  {'-'*22} {'-'*8} {'-'*10} {'-'*10} {'-'*10}")

        for ev in evals:
            adj_ev = controller._adjusted_ev(ev, ctx)
            prereq_str = "✓" if ev.prerequisites_met else "✗"
            print(
                f"  {ev.strategy_name:<22s} {prereq_str:<8s} "
                f"${ev.expected_value:<8.2f} {ev.detection_probability:<10.3f} "
                f"${adj_ev:<8.2f}"
            )

        best = controller.best_strategy(agent_data, ctx)
        switch_to = controller.decide_switch(agent_data, ctx)
        print(f"  → Best strategy: {best.strategy_name} (eV={best.expected_value:.2f})")
        print(f"  → Would switch to: {switch_to or 'honest (stay)'}")

    # ── Summary analysis ─────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  KEY INSIGHTS")
    print("=" * 72)

    switches = result["switches"]
    if switches:
        avg_honesty_switchers = sum(sw["honesty"] for sw in switches) / len(switches)
        print(f"  • Average honesty of agents that switched: {avg_honesty_switchers:.3f}")
        print(f"  • Lower-honesty agents are more likely to switch to adversarial strategies.")

        low_honest = [s for s in switches if s["honesty"] < 0.4]
        mid_honest = [s for s in switches if 0.4 <= s["honesty"] < 0.7]
        high_honest = [s for s in switches if s["honesty"] >= 0.7]
        print(f"  • Low-honesty (<0.4) switches:   {len(low_honest)}")
        print(f"  • Mid-honesty (0.4-0.7) switches: {len(mid_honest)}")
        print(f"  • High-honesty (≥0.7) switches:   {len(high_honest)}")

        if low_honest and not high_honest:
            print(f"  ✓ Honesty parameter θ effectively suppresses adversarial switching")
            print(f"    for agents with high moral standards.")
    else:
        print(f"  • No agents switched this step. This may be because:")
        print(f"    - The honest baseline provides sufficient expected value.")
        print(f"    - Detection penalties are high enough to offset rewards.")
        print(f"    - Some strategies may need agents with specific attributes")
        print(f"      (e.g., guild membership, insurance, high land value).")

    print("\n  Demo complete.\n")


def _create_demo_agents(count: int = 20) -> list[dict]:
    """
    Create a diverse set of demo agents with varying honesty,
    economic profiles, and insurance status.
    """
    random.seed(42)  # Reproducible

    agents: list[dict] = []

    for i in range(count):
        # Distribute honesty evenly from 0.2 to 0.95
        honesty = 0.20 + (i / max(count - 1, 1)) * 0.75

        # Inertia inversely correlated with honesty (dishonest agents are
        # more willing to change strategies)
        inertia = 0.1 + (1.0 - honesty) * 0.5 + random.uniform(-0.05, 0.05)
        inertia = max(0.05, min(0.95, inertia))

        # Assign diverse agent types and profiles so different strategies
        # become viable for different agents
        profile_bucket = i % 8  # 8 different strategy-oriented profiles

        if profile_bucket == 0:
            # Premium evasion profile: insured, high risk, LOW land (no harberger)
            agent = {
                "id": f"agent_{i:03d}", "type": "worker",
                "honesty": round(honesty, 3), "inertia": round(inertia, 3),
                "cash": round(random.uniform(5000, 30000), 2),
                "land_value": round(random.uniform(0, 5000), 2),  # Low land
                "property_count": random.randint(0, 1),
                "risk_profile": round(random.uniform(0.20, 0.40), 3),
                "revenue": round(random.uniform(5000, 20000), 2),
                "income": round(random.uniform(2000, 15000), 2),
                "has_insurance": True,
                "insurance_coverage": round(random.uniform(50000, 150000), 2),
                "insurance_premium": round(random.uniform(1000, 5000), 2),
                "outstanding_liability": 0.0,
                "member_count": 0, "labor_count": 0,
                "compact_id": f"compact_{random.choice(['A','B','C'])}",
            }
        elif profile_bucket == 1:
            # Insurance fraud profile: insured, high coverage, low cash, LOW land
            agent = {
                "id": f"agent_{i:03d}", "type": "worker",
                "honesty": round(honesty, 3), "inertia": round(inertia, 3),
                "cash": round(random.uniform(2000, 10000), 2),
                "land_value": round(random.uniform(0, 2000), 2),  # Very low land
                "property_count": random.randint(0, 1),
                "risk_profile": round(random.uniform(0.10, 0.25), 3),
                "revenue": round(random.uniform(2000, 10000), 2),
                "income": round(random.uniform(1000, 5000), 2),
                "has_insurance": True,
                "insurance_coverage": round(random.uniform(100000, 250000), 2),
                "insurance_premium": round(random.uniform(500, 2000), 2),
                "outstanding_liability": 0.0,
                "member_count": 0, "labor_count": 0,
                "compact_id": f"compact_{random.choice(['A','B','C'])}",
            }
        elif profile_bucket == 2:
            # Harberger gaming profile: high land value, many properties
            # (this is the only profile that SHOULD have high land)
            agent = {
                "id": f"agent_{i:03d}", "type": "business",
                "honesty": round(honesty, 3), "inertia": round(inertia, 3),
                "cash": round(random.uniform(20000, 100000), 2),
                "land_value": round(random.uniform(200000, 500000), 2),
                "property_count": random.randint(3, 8),
                "risk_profile": round(random.uniform(0.05, 0.15), 3),
                "revenue": round(random.uniform(20000, 60000), 2),
                "income": round(random.uniform(5000, 20000), 2),
                "has_insurance": random.random() < 0.5,
                "insurance_coverage": round(random.uniform(50000, 200000), 2) if random.random() < 0.5 else 0.0,
                "insurance_premium": round(random.uniform(500, 3000), 2) if random.random() < 0.5 else 0.0,
                "outstanding_liability": 0.0,
                "member_count": 0,
                "labor_count": random.randint(5, 30),
                "compact_id": f"compact_{random.choice(['A','B','C'])}",
            }
        elif profile_bucket == 3:
            # Court flooding profile: high cash, LOW land
            agent = {
                "id": f"agent_{i:03d}", "type": "business",
                "honesty": round(honesty, 3), "inertia": round(inertia, 3),
                "cash": round(random.uniform(80000, 200000), 2),
                "land_value": round(random.uniform(0, 5000), 2),  # Low land
                "property_count": random.randint(0, 1),
                "risk_profile": round(random.uniform(0.05, 0.10), 3),
                "revenue": round(random.uniform(10000, 50000), 2),
                "income": round(random.uniform(3000, 15000), 2),
                "has_insurance": random.random() < 0.6,
                "insurance_coverage": round(random.uniform(50000, 100000), 2) if random.random() < 0.6 else 0.0,
                "insurance_premium": round(random.uniform(500, 2000), 2) if random.random() < 0.6 else 0.0,
                "outstanding_liability": 0.0,
                "member_count": 0,
                "labor_count": random.randint(5, 20),
                "compact_id": f"compact_{random.choice(['A','B','C'])}",
            }
        elif profile_bucket == 4:
            # Guild rent-seeking profile: guild with many members, LOW land
            agent = {
                "id": f"agent_{i:03d}", "type": "guild",
                "honesty": round(honesty, 3), "inertia": round(inertia, 3),
                "cash": round(random.uniform(10000, 80000), 2),
                "land_value": round(random.uniform(0, 10000), 2),  # Low land
                "property_count": random.randint(0, 1),
                "risk_profile": round(random.uniform(0.05, 0.15), 3),
                "revenue": round(random.uniform(5000, 30000), 2),
                "income": round(random.uniform(2000, 10000), 2),
                "has_insurance": True,
                "insurance_coverage": round(random.uniform(50000, 100000), 2),
                "insurance_premium": round(random.uniform(500, 1500), 2),
                "outstanding_liability": 0.0,
                "member_count": random.randint(10, 60),
                "labor_count": 0,
                "compact_id": f"compact_{random.choice(['A','B','C'])}",
            }
        elif profile_bucket == 5:
            # Collusion profile: high-revenue business, LOW land
            agent = {
                "id": f"agent_{i:03d}", "type": "business",
                "honesty": round(honesty, 3), "inertia": round(inertia, 3),
                "cash": round(random.uniform(30000, 150000), 2),
                "land_value": round(random.uniform(0, 10000), 2),  # Low land
                "property_count": random.randint(0, 1),
                "risk_profile": round(random.uniform(0.05, 0.10), 3),
                "revenue": round(random.uniform(40000, 80000), 2),
                "income": round(random.uniform(10000, 30000), 2),
                "has_insurance": True,
                "insurance_coverage": round(random.uniform(100000, 200000), 2),
                "insurance_premium": round(random.uniform(1000, 3000), 2),
                "outstanding_liability": 0.0,
                "member_count": 0,
                "labor_count": random.randint(10, 30),
                "compact_id": f"compact_{random.choice(['A','B','C'])}",
            }
        elif profile_bucket == 6:
            # Contract breach profile: high income/contract value, LOW land
            agent = {
                "id": f"agent_{i:03d}", "type": "worker",
                "honesty": round(honesty, 3), "inertia": round(inertia, 3),
                "cash": round(random.uniform(10000, 60000), 2),
                "land_value": round(random.uniform(0, 5000), 2),  # Low land
                "property_count": random.randint(0, 1),
                "risk_profile": round(random.uniform(0.05, 0.15), 3),
                "revenue": round(random.uniform(20000, 50000), 2),
                "income": round(random.uniform(15000, 30000), 2),
                "has_insurance": True,
                "insurance_coverage": round(random.uniform(50000, 100000), 2),
                "insurance_premium": round(random.uniform(500, 2000), 2),
                "outstanding_liability": 0.0,
                "member_count": 0, "labor_count": 0,
                "compact_id": f"compact_{random.choice(['A','B','C'])}",
            }
        else:  # bucket 7
            # LVT evasion profile: high land, many properties
            agent = {
                "id": f"agent_{i:03d}", "type": "worker",
                "honesty": round(honesty, 3), "inertia": round(inertia, 3),
                "cash": round(random.uniform(10000, 50000), 2),
                "land_value": round(random.uniform(300000, 600000), 2),
                "property_count": random.randint(5, 10),
                "risk_profile": round(random.uniform(0.05, 0.15), 3),
                "revenue": round(random.uniform(5000, 20000), 2),
                "income": round(random.uniform(2000, 10000), 2),
                "has_insurance": True,
                "insurance_coverage": round(random.uniform(50000, 100000), 2),
                "insurance_premium": round(random.uniform(500, 1500), 2),
                "outstanding_liability": 0.0,
                "member_count": 0, "labor_count": 0,
                "compact_id": f"compact_{random.choice(['A','B','C'])}",
            }

        agents.append(agent)

    return agents


# ═══════════════════════════════════════════════════════════════════════
#  Main entry point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    run_demo()
