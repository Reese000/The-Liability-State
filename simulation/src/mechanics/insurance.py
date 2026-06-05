"""
mechanics/insurance.py — Insurance Market System

Implements:
  - InsurancePool: Collects premiums, pays claims, tracks solvency.
  - InsuranceMarket: Matches agents to insurers, handles risk pricing,
    detects premium evasion via statistical outliers.

Supports multiple competing insurers.
Agents have hidden risk profiles; insurers price based on declared risk plus audit.

References:
  - SPEC: MECHANICS_INVENTORY.md §8 (Insurance System)
  - SPEC: ENFORCEMENT_MODEL.md §4.1–4.2 (insurance fraud, premium evasion)
  - AGENT_MODEL.md §2.3 (Insurer attributes)
"""

from __future__ import annotations

import math
import random
import statistics
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from ..core.ledger import LedgerEngine, EntityType
except ImportError:
    from core.ledger import LedgerEngine, EntityType


# ══════════════════════════════════════════════════════════════════════
#  Insurance Pool
# ══════════════════════════════════════════════════════════════════════

@dataclass
class InsurancePool:
    """
    A risk pool managed by an insurer.

    Collects premiums from policyholders, pays claims, and tracks solvency.
    Each insurer may operate multiple pools (e.g. different risk tiers).

    Solvency is tracked as the ratio of reserves to estimated future liability.
    """

    pool_id: str
    insurer_id: str
    reserves: float = 0.0
    premiums_collected: float = 0.0
    claims_paid: float = 0.0
    policy_count: int = 0

    # Solvency thresholds
    solvency_target: float = 1.2     # Desired reserve ratio
    min_solvency_ratio: float = 0.1  # Below this = insolvent

    # ── Solvency ─────────────────────────────────────────────────

    @property
    def solvency_ratio(self) -> float:
        """Ratio of reserves to estimated expected liability."""
        expected = self._estimate_liability()
        if expected <= 0.0:
            return float('inf') if self.reserves > 0.0 else 0.0
        return self.reserves / expected

    @property
    def is_solvent(self) -> bool:
        """Pool can cover expected claims."""
        return self.solvency_ratio >= self.min_solvency_ratio

    def _estimate_liability(self) -> float:
        """
        Estimate expected outstanding claims liability.

        Uses a blended approach:
          – If there is claims history, uses the empirical loss ratio.
          – Otherwise conservatively estimates 10 % of reserves.
        """
        if self.premiums_collected > 0.0 and self.policy_count > 0:
            loss_ratio = self.claims_paid / self.premiums_collected
            # Expected future claims based on current reserves and loss ratio
            return loss_ratio * self.reserves * 0.5 + self.reserves * 0.05
        return self.reserves * 0.10

    # ── Operations ───────────────────────────────────────────────

    def collect_premium(self, amount: float) -> float:
        """Record a premium collection. Returns new reserve balance."""
        if amount < 0:
            raise ValueError(f"Negative premium: {amount}")
        self.premiums_collected += amount
        self.reserves += amount
        return self.reserves

    def pay_claim(self, amount: float) -> tuple[bool, float]:
        """
        Pay a claim from pool reserves.

        Returns
        -------
        (paid_in_full, amount_paid)
            If reserves are insufficient, pays what is available (partial).
        """
        if amount < 0:
            raise ValueError(f"Negative claim amount: {amount}")
        paid = min(amount, self.reserves)
        self.reserves -= paid
        self.claims_paid += paid
        return paid >= amount, paid

    # ── Reporting ────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            'pool_id': self.pool_id,
            'insurer_id': self.insurer_id,
            'reserves': round(self.reserves, 4),
            'premiums_collected': round(self.premiums_collected, 4),
            'claims_paid': round(self.claims_paid, 4),
            'policy_count': self.policy_count,
            'solvency_ratio': round(self.solvency_ratio, 4),
            'is_solvent': self.is_solvent,
        }

    def to_dict(self) -> dict:
        return self.get_status()


# ══════════════════════════════════════════════════════════════════════
#  Agent Insurance Record
# ══════════════════════════════════════════════════════════════════════

@dataclass
class AgentInsuranceRecord:
    """
    Tracks an agent's insurance relationship with an insurer.

    Attributes
    ----------
    true_risk : float
        The agent's actual risk probability (hidden from insurer).
    declared_risk : float
        What the agent declared to the insurer (may be understated).
    assessed_risk : float
        The risk the insurer uses for pricing (updated after audit).
    premium : float
        Current premium amount charged per step.
    coverage_limit : float
        Maximum claim payout per event.
    evasion_flagged : bool
        Set True by statistical outlier detection.
    """

    agent_id: str
    insurer_id: str
    pool_id: str
    true_risk: float
    declared_risk: float
    assessed_risk: float
    premium: float
    coverage_limit: float

    premiums_paid: float = 0.0
    claims_filed: int = 0
    claims_paid_amount: float = 0.0
    is_active: bool = True
    evasion_flagged: bool = False
    step_purchased: int = 0

    @property
    def loss_ratio(self) -> float:
        """Ratio of claims paid to premiums paid."""
        if self.premiums_paid <= 0.0:
            return 0.0
        return self.claims_paid_amount / self.premiums_paid

    def to_dict(self) -> dict:
        return {
            'agent_id': self.agent_id,
            'insurer_id': self.insurer_id,
            'pool_id': self.pool_id,
            'true_risk': self.true_risk,
            'declared_risk': self.declared_risk,
            'assessed_risk': self.assessed_risk,
            'premium': round(self.premium, 4),
            'coverage_limit': self.coverage_limit,
            'premiums_paid': round(self.premiums_paid, 4),
            'claims_filed': self.claims_filed,
            'claims_paid_amount': round(self.claims_paid_amount, 4),
            'loss_ratio': round(self.loss_ratio, 4),
            'is_active': self.is_active,
            'evasion_flagged': self.evasion_flagged,
            'step_purchased': self.step_purchased,
        }


# ══════════════════════════════════════════════════════════════════════
#  Insurance Market
# ══════════════════════════════════════════════════════════════════════

_RISK_BANDS = [
    ('very_low',   0.0,   0.02),
    ('low',        0.02,  0.05),
    ('medium',     0.05,  0.10),
    ('high',       0.10,  0.20),
    ('very_high',  0.20,  1.01),
]


def _risk_band(risk: float) -> str:
    """Categorise a risk value into a named band for statistics."""
    for name, lo, hi in _RISK_BANDS:
        if lo <= risk < hi:
            return name
    return 'very_high'


class InsuranceMarket:
    """
    Central insurance marketplace.

    Manages multiple competing insurers, matches agents to insurers,
    handles risk pricing, and detects premium evasion via statistical
    outlier analysis.

    Key design points
    -----------------
    - Agents have a **hidden** `true_risk` and a **declared** risk.
    - Insurers price policies based on declared risk, but may audit
      a policy (with configurable probability) to discover the true risk.
    - Premium evasion is detected by comparing an agent's loss ratio
      against others in the same declared-risk band using Z-scores.
    - All financial flows go through the LedgerEngine for double-entry
      accounting and zero-sum enforcement.
    """

    def __init__(
        self,
        ledger: LedgerEngine,
        *,
        audit_probability: float = 0.10,
        base_rate: float = 0.05,
        loading_factor: float = 1.30,
        evasion_z_threshold: float = 2.0,
        # Dynamic pricing & bankruptcy parameters
        premium_raise_factor: float = 1.25,
        premium_lower_factor: float = 1.20,
        solvency_raise_threshold: float = 0.1,
        solvency_lower_threshold: float = 0.5,
        consecutive_negative_max: int = 3,
    ):
        """
        Parameters
        ----------
        ledger : LedgerEngine
            Core double-entry accounting engine.
        audit_probability : float
            Probability per step that a policy is audited (0.0 – 1.0).
        base_rate : float
            Base premium rate applied to assessed risk.
        loading_factor : float
            Multiplier over the actuarially fair premium (covers expenses,
            profit margin).
        evasion_z_threshold : float
            Z-score threshold for flagging premium evasion.
        premium_raise_factor : float
            Multiplier applied to an insurer's premium when loss ratio > 1.0
            or solvency ratio below raise threshold.
        premium_lower_factor : float
            Divisor applied to an insurer's premium when overcapitalised
            (solvency ratio above lower threshold).
        solvency_raise_threshold : float
            Pool-level solvency ratio below which premiums are raised.
        solvency_lower_threshold : float
            Pool-level solvency ratio above which premiums are lowered.
        consecutive_negative_max : int
            Consecutive steps with negative total reserves before an insurer
            is declared bankrupt and its policies are redistributed.
        """
        self.ledger = ledger
        self.audit_probability = audit_probability
        self.base_rate = base_rate
        self.loading_factor = loading_factor
        self.evasion_z_threshold = evasion_z_threshold

        # Dynamic pricing & bankruptcy config
        self.premium_raise_factor = premium_raise_factor
        self.premium_lower_factor = premium_lower_factor
        self.solvency_raise_threshold = solvency_raise_threshold
        self.solvency_lower_threshold = solvency_lower_threshold
        self.consecutive_negative_max = consecutive_negative_max

        # Pools indexed by pool_id
        self.pools: dict[str, InsurancePool] = {}

        # Insurer metadata
        self.insurers: dict[str, dict[str, Any]] = {}

        # Active policies indexed by agent_id
        self.policies: dict[str, AgentInsuranceRecord] = {}

        # Agent risk profiles (private information)
        self.agents: dict[str, dict[str, float]] = {}

        # ── Dynamic pricing per-insurer premium multiplier ───────
        self.premium_multipliers: dict[str, float] = {}

        # ── Bankruptcy tracking ──────────────────────────────────
        # Consecutive steps with total reserves < 0 per insurer
        self._negative_steps: dict[str, int] = {}
        self._failed_insurers: set[str] = set()

    # ── Registration ─────────────────────────────────────────────

    def register_insurer(
        self,
        insurer_id: str,
        initial_capital: float = 10_000.0,
        num_pools: int = 1,
    ) -> str:
        """Register an insurer and create its risk pools."""
        if insurer_id in self.insurers:
            raise ValueError(f"Insurer {insurer_id!r} already registered")

        # Ensure the ledger has an entity for this insurer
        if not self.ledger.entity_exists(insurer_id):
            self.ledger.register_entity(
                insurer_id, EntityType.INSURER, initial_cash=initial_capital,
            )

        pool_ids: list[str] = []
        for i in range(num_pools):
            pool_id = f"{insurer_id}_pool_{i}"
            pool = InsurancePool(
                pool_id=pool_id,
                insurer_id=insurer_id,
                reserves=initial_capital * 0.30,  # seed reserves
            )
            self.pools[pool_id] = pool
            pool_ids.append(pool_id)

        self.insurers[insurer_id] = {
            'capital': initial_capital,
            'pool_ids': pool_ids,
        }

        # Initialise per-insurer premium multiplier (1.0 = no adjustment)
        self.premium_multipliers[insurer_id] = 1.0

        return insurer_id

    def register_agent(
        self,
        agent_id: str,
        true_risk: float,
        declared_risk: float | None = None,
        initial_cash: float = 1000.0,
    ) -> str:
        """
        Register an agent with a risk profile.

        Parameters
        ----------
        agent_id : str
        true_risk : float in [0, 1]
            The agent's actual risk probability (hidden from insurers).
        declared_risk : float or None
            What the agent declares.  Defaults to *true_risk* (honest agent).
            Evaders pass a lower value.
        initial_cash : float
            Starting cash for the ledger entity.
        """
        if agent_id in self.agents:
            raise ValueError(f"Agent {agent_id!r} already registered")
        if not (0.0 <= true_risk <= 1.0):
            raise ValueError(f"true_risk must be in [0, 1], got {true_risk}")

        if declared_risk is None:
            declared_risk = true_risk
        if not (0.0 <= declared_risk <= 1.0):
            raise ValueError(f"declared_risk must be in [0, 1], got {declared_risk}")

        self.agents[agent_id] = {
            'true_risk': true_risk,
            'declared_risk': declared_risk,
        }

        if not self.ledger.entity_exists(agent_id):
            self.ledger.register_entity(
                agent_id, EntityType.CITIZEN, initial_cash=initial_cash,
            )
        return agent_id

    # ── Pricing ──────────────────────────────────────────────────

    def price_policy(
        self,
        insurer_id: str,
        agent_id: str,
        coverage_limit: float = 10_000.0,
    ) -> float:
        """
        Calculate the premium for insuring an agent.

        Formula
        -------
        premium = base_rate * assessed_risk * coverage_limit * loading_factor
                 * premium_multiplier(insurer_id)

        The *assessed_risk* is the agent's declared risk unless an audit
        has revealed a higher true risk.

        The *premium_multiplier* is a per-insurer factor adjusted dynamically
        each step based on solvency and loss ratio.
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id!r} not registered")
        if insurer_id not in self.insurers:
            raise ValueError(f"Insurer {insurer_id!r} not registered")

        # Use assessed risk if we already have a policy (post-audit)
        if agent_id in self.policies:
            assessed = self.policies[agent_id].assessed_risk
        else:
            assessed = self.agents[agent_id]['declared_risk']

        # Apply per-insurer dynamic pricing multiplier
        multiplier = self.premium_multipliers.get(insurer_id, 1.0)

        premium = (
            self.base_rate
            * assessed
            * coverage_limit
            * self.loading_factor
            * multiplier
        )
        return max(premium, 1.0)  # floor of $1

    # ── Policy Purchase ──────────────────────────────────────────

    def purchase_policy(
        self,
        agent_id: str,
        insurer_id: str,
        coverage_limit: float = 10_000.0,
    ) -> AgentInsuranceRecord:
        """
        An agent purchases a policy from an insurer.

        The agent is assigned to the insurer's pool with the fewest
        current policies (load balancing).

        Returns the resulting AgentInsuranceRecord.
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id!r} not registered")
        if insurer_id not in self.insurers:
            raise ValueError(f"Insurer {insurer_id!r} not registered")
        if insurer_id in self._failed_insurers:
            raise ValueError(
                f"Insurer {insurer_id!r} has failed and cannot underwrite "
                f"new policies"
            )

        # Deactivate any existing policy
        if agent_id in self.policies:
            self.policies[agent_id].is_active = False

        # Load-balance: pick pool with fewest policies
        pool_ids = self.insurers[insurer_id]['pool_ids']
        pool_id = min(pool_ids, key=lambda pid: self.pools[pid].policy_count)
        pool = self.pools[pool_id]

        agent_data = self.agents[agent_id]
        premium = self.price_policy(insurer_id, agent_id, coverage_limit)
        assessed = agent_data['declared_risk']

        record = AgentInsuranceRecord(
            agent_id=agent_id,
            insurer_id=insurer_id,
            pool_id=pool_id,
            true_risk=agent_data['true_risk'],
            declared_risk=agent_data['declared_risk'],
            assessed_risk=assessed,
            premium=premium,
            coverage_limit=coverage_limit,
            step_purchased=self.ledger.step,
        )
        self.policies[agent_id] = record
        pool.policy_count += 1
        return record

    # ── Premium Collection ───────────────────────────────────────

    def collect_premiums(self) -> list[dict]:
        """
        Collect premiums from all active policyholders.

        Transfers are recorded on the ledger.  If an agent cannot afford
        their premium the policy lapses automatically.

        Returns a list of result dicts per agent.
        """
        results: list[dict] = []
        for agent_id, record in list(self.policies.items()):
            if not record.is_active:
                continue
            if not self.ledger.entity_exists(agent_id):
                continue

            # Check affordability
            agent_bs = self.ledger.get_balance(agent_id)
            if agent_bs.cash < record.premium:
                record.is_active = False
                pool = self.pools[record.pool_id]
                pool.policy_count = max(0, pool.policy_count - 1)
                results.append({
                    'agent_id': agent_id,
                    'status': 'lapsed',
                    'reason': 'insufficient_funds',
                })
                continue

            # Execute ledger transfer
            try:
                self.ledger.transfer(
                    from_id=agent_id,
                    to_id=record.insurer_id,
                    mechanism='premium',
                    amount=record.premium,
                    description=(
                        f'Insurance premium: {agent_id} → {record.insurer_id}'
                    ),
                )
            except Exception as exc:
                results.append({
                    'agent_id': agent_id,
                    'status': 'failed',
                    'reason': str(exc),
                })
                continue

            # Update pool & record
            pool = self.pools[record.pool_id]
            pool.collect_premium(record.premium)
            record.premiums_paid += record.premium

            results.append({
                'agent_id': agent_id,
                'insurer_id': record.insurer_id,
                'premium': record.premium,
                'status': 'paid',
            })

        return results

    # ── Claim Processing ─────────────────────────────────────────

    def file_claim(self, agent_id: str, claim_amount: float) -> dict:
        """
        File and process an insurance claim.

        Returns
        -------
        dict with keys: status, amount_paid, reason, etc.
        """
        if agent_id not in self.policies:
            return {'status': 'denied', 'reason': 'no_policy', 'amount_paid': 0.0}

        record = self.policies[agent_id]
        if not record.is_active:
            return {'status': 'denied', 'reason': 'policy_lapsed', 'amount_paid': 0.0}

        # Apply coverage limit
        payout = min(claim_amount, record.coverage_limit)

        pool = self.pools[record.pool_id]
        paid_in_full, amount_paid = pool.pay_claim(payout)

        if amount_paid <= 0.0:
            return {
                'status': 'denied',
                'reason': 'insufficient_reserves',
                'amount_paid': 0.0,
            }

        # Transfer from insurer to agent via ledger
        try:
            self.ledger.transfer(
                from_id=record.insurer_id,
                to_id=agent_id,
                mechanism='claim',
                amount=amount_paid,
                description=f'Claim payment: {record.insurer_id} → {agent_id}',
            )
        except Exception as exc:
            # Rollback pool state
            pool.reserves += amount_paid
            pool.claims_paid -= amount_paid
            return {'status': 'failed', 'reason': str(exc), 'amount_paid': 0.0}

        record.claims_filed += 1
        record.claims_paid_amount += amount_paid

        return {
            'status': 'paid_in_full' if paid_in_full else 'partial_payment',
            'amount_paid': amount_paid,
            'claim_amount': claim_amount,
            'coverage_limit': record.coverage_limit,
            'pool_reserves_remaining': pool.reserves,
        }

    # ── Auditing ─────────────────────────────────────────────────

    def run_audits(self) -> list[dict]:
        """
        Randomly audit policies.

        If an audit reveals declared_risk < true_risk, the assessed risk
        is updated and the premium is recalculated.

        Returns a list of audit result dicts.
        """
        results: list[dict] = []
        for agent_id, record in list(self.policies.items()):
            if not record.is_active:
                continue
            if random.random() >= self.audit_probability:
                continue

            agent = self.agents[agent_id]
            true_r = agent['true_risk']
            declared_r = agent['declared_risk']

            if true_r > declared_r:
                # Under-reporting detected
                record.assessed_risk = true_r
                old_premium = record.premium
                record.premium = self.price_policy(
                    record.insurer_id, agent_id, record.coverage_limit,
                )
                results.append({
                    'agent_id': agent_id,
                    'audit_found': True,
                    'declared_risk': declared_r,
                    'true_risk': true_r,
                    'old_premium': old_premium,
                    'new_premium': record.premium,
                })
            else:
                results.append({
                    'agent_id': agent_id,
                    'audit_found': False,
                    'declared_risk': declared_r,
                    'true_risk': true_r,
                })
        return results

    # ── Premium Evasion Detection ────────────────────────────────

    def detect_premium_evasion(self) -> list[dict]:
        """
        Statistical outlier detection for premium evasion.

        Groups active policies by declared-risk band, computes the mean
        and standard deviation of loss ratios within each band, and flags
        agents whose loss ratio exceeds the band mean by more than
        ``evasion_z_threshold`` standard deviations.

        Returns a list of flagged-agent evidence dicts.
        """
        # Group by risk band
        bands: dict[str, list[AgentInsuranceRecord]] = {}
        for record in self.policies.values():
            if not record.is_active:
                continue
            band = _risk_band(record.declared_risk)
            bands.setdefault(band, []).append(record)

        flagged: list[dict] = []

        for band, records in bands.items():
            if len(records) < 3:
                continue  # statistically insignificant

            loss_ratios = [r.loss_ratio for r in records]
            mean_lr = statistics.mean(loss_ratios)
            stdev_lr = (
                statistics.stdev(loss_ratios) if len(loss_ratios) > 1 else 0.0
            )

            if stdev_lr <= 0.0:
                continue

            for record in records:
                z = (record.loss_ratio - mean_lr) / stdev_lr
                if z > self.evasion_z_threshold:
                    record.evasion_flagged = True
                    flagged.append({
                        'agent_id': record.agent_id,
                        'insurer_id': record.insurer_id,
                        'band': band,
                        'declared_risk': record.declared_risk,
                        'true_risk': record.true_risk,
                        'loss_ratio': round(record.loss_ratio, 4),
                        'band_mean_loss_ratio': round(mean_lr, 4),
                        'z_score': round(z, 2),
                        'premiums_paid': round(record.premiums_paid, 4),
                        'claims_paid': round(record.claims_paid_amount, 4),
                    })

        return flagged

    # ── Solvency ─────────────────────────────────────────────────

    def check_solvency(self) -> list[dict]:
        """Check solvency of all pools. Returns status dict per pool."""
        return [pool.get_status() for pool in self.pools.values()]

    # ── Dynamic Pricing ─────────────────────────────────────────

    def _insurer_aggregates(self, insurer_id: str) -> dict[str, float]:
        """Aggregate pool-level financials for a given insurer."""
        pools = [
            self.pools[pid]
            for pid in self.insurers.get(insurer_id, {}).get('pool_ids', [])
        ]
        return {
            'total_reserves': sum(p.reserves for p in pools),
            'total_premiums': sum(p.premiums_collected for p in pools),
            'total_claims': sum(p.claims_paid for p in pools),
            'total_policies': sum(p.policy_count for p in pools),
        }

    def adjust_pricing(self) -> list[dict]:
        """
        Adjust each solvent insurer's premium multiplier based on its
        aggregate solvency ratio and cumulative loss ratio.

        Rules
        -----
        - If total reserves are negative OR the cumulative loss ratio
          exceeds 1.0, the premium_multiplier is multiplied by
          ``premium_raise_factor`` (raise prices).
        - Otherwise, if the average pool solvency ratio exceeds the
          ``solvency_lower_threshold`` (overcapitalised), the
          premium_multiplier is divided by ``premium_lower_factor``
          (lower prices to attract customers).
        - The multiplier is clamped to [0.5, 3.0] to prevent extreme
          swings.

        Returns a list of adjustment result dicts.
        """
        results: list[dict] = []
        for ins_id in list(self.insurers.keys()):
            if ins_id in self._failed_insurers:
                continue

            agg = self._insurer_aggregates(ins_id)
            total_reserves = agg['total_reserves']
            total_premiums = agg['total_premiums']
            total_claims = agg['total_claims']
            total_policies = agg['total_policies']

            if total_policies == 0:
                continue

            loss_ratio = total_claims / max(1.0, total_premiums)
            old_mult = self.premium_multipliers.get(ins_id, 1.0)
            multiplier = old_mult

            # ── Raise premiums ───────────────────────────────────
            # Trigger: negative reserves or loss ratio > 1.0
            if total_reserves < 0.0 or loss_ratio > 1.0:
                multiplier *= self.premium_raise_factor
                reason = 'losses'

            # ── Lower premiums (overcapitalised) ─────────────────
            else:
                pool_ratios = [
                    self.pools[pid].solvency_ratio
                    for pid in self.insurers[ins_id]['pool_ids']
                ]
                avg_solvency = (
                    sum(pool_ratios) / len(pool_ratios)
                    if pool_ratios else 0.0
                )
                if avg_solvency > self.solvency_lower_threshold:
                    multiplier /= self.premium_lower_factor
                    multiplier = max(multiplier, 0.5)  # floor
                    reason = 'overcapitalised'
                else:
                    reason = 'stable'

            # Clamp to safe bounds
            multiplier = max(0.5, min(3.0, multiplier))
            self.premium_multipliers[ins_id] = multiplier

            if abs(multiplier - old_mult) > 0.001:
                results.append({
                    'insurer_id': ins_id,
                    'old_multiplier': round(old_mult, 4),
                    'new_multiplier': round(multiplier, 4),
                    'reason': reason,
                    'total_reserves': round(total_reserves, 2),
                    'loss_ratio': round(loss_ratio, 4),
                })

        return results

    # ── Bankruptcy ──────────────────────────────────────────────

    def check_bankruptcy(self) -> list[dict]:
        """
        Check each insurer for bankruptcy.

        An insurer is declared bankrupt if its total reserves (summed
        across all pools) have been negative for ``consecutive_negative_max``
        consecutive steps.

        Returns a list of bankruptcy event dicts for newly failed insurers.
        """
        results: list[dict] = []
        for ins_id in list(self.insurers.keys()):
            if ins_id in self._failed_insurers:
                continue

            agg = self._insurer_aggregates(ins_id)
            total_reserves = agg['total_reserves']

            if total_reserves < 0:
                self._negative_steps[ins_id] = (
                    self._negative_steps.get(ins_id, 0) + 1
                )
            else:
                self._negative_steps[ins_id] = 0

            if self._negative_steps.get(ins_id, 0) >= self.consecutive_negative_max:
                self._failed_insurers.add(ins_id)
                results.append({
                    'insurer_id': ins_id,
                    'status': 'failed',
                    'reason': (
                        f'negative reserves for '
                        f'{self.consecutive_negative_max} consecutive steps'
                    ),
                    'total_reserves': round(total_reserves, 2),
                    'consecutive_negative_steps': self.consecutive_negative_max,
                })

        return results

    def transfer_policies_from_failed(self) -> list[dict]:
        """
        Reassign all active policies from failed insurers to surviving
        insurers (load-balanced by policy count).

        If no surviving insurers remain, policies are lapsed instead.

        Returns a list of transfer result dicts.
        """
        results: list[dict] = []
        surviving = [
            iid for iid in self.insurers
            if iid not in self._failed_insurers
        ]

        if not surviving:
            # No surviving insurers — all policies from failed lapse
            for agent_id, record in list(self.policies.items()):
                if not record.is_active:
                    continue
                if record.insurer_id in self._failed_insurers:
                    record.is_active = False
                    pool = self.pools.get(record.pool_id)
                    if pool:
                        pool.policy_count = max(0, pool.policy_count - 1)
                    results.append({
                        'agent_id': agent_id,
                        'from_insurer': record.insurer_id,
                        'status': 'lapsed_no_survivors',
                    })
            return results

        for agent_id, record in list(self.policies.items()):
            if not record.is_active:
                continue
            if record.insurer_id not in self._failed_insurers:
                continue

            old_insurer = record.insurer_id
            old_pool_id = record.pool_id

            # Decrement old pool policy count
            old_pool = self.pools.get(old_pool_id)
            if old_pool:
                old_pool.policy_count = max(0, old_pool.policy_count - 1)

            # Pick surviving insurer with fewest total policies
            new_insurer = min(
                surviving,
                key=lambda iid: sum(
                    self.pools[pid].policy_count
                    for pid in self.insurers[iid]['pool_ids']
                ),
            )

            # Assign to least-loaded pool of the new insurer
            new_pool_ids = self.insurers[new_insurer]['pool_ids']
            new_pool_id = min(
                new_pool_ids,
                key=lambda pid: self.pools[pid].policy_count,
            )
            new_pool = self.pools[new_pool_id]
            new_pool.policy_count += 1

            # Update the record
            record.insurer_id = new_insurer
            record.pool_id = new_pool_id

            results.append({
                'agent_id': agent_id,
                'from_insurer': old_insurer,
                'to_insurer': new_insurer,
                'pool_id': new_pool_id,
                'status': 'transferred',
            })

        return results

    def is_insurer_failed(self, insurer_id: str) -> bool:
        """Return True if the insurer has been declared bankrupt."""
        return insurer_id in self._failed_insurers

    # ── Simulation Step ──────────────────────────────────────────

    def run_step(self) -> dict:
        """
        Execute one simulation step:

        1. Run audits
        2. Collect premiums
        3. Detect premium evasion
        4. Check solvency
        5. Adjust insurer pricing (dynamic premiums)
        6. Check for bankruptcies (3+ consecutive negative-reserve steps)
        7. Transfer policies from any newly failed insurers

        Returns a summary dict.
        """
        audits = self.run_audits()
        premiums = self.collect_premiums()
        evasion = self.detect_premium_evasion()
        solvency = self.check_solvency()

        # ── Dynamic pricing adjustment ───────────────────────────
        pricing_adjustments = self.adjust_pricing()

        # ── Bankruptcy check ─────────────────────────────────────
        bankruptcies = self.check_bankruptcy()

        # ── Policy transfers ─────────────────────────────────────
        transfers: list[dict] = []
        if bankruptcies:
            transfers = self.transfer_policies_from_failed()

        return {
            'step': self.ledger.step,
            'audits': audits,
            'premiums': premiums,
            'evasion_flagged': evasion,
            'solvency': solvency,
            'pricing_adjustments': pricing_adjustments,
            'bankruptcies': bankruptcies,
            'policy_transfers': transfers,
        }

    # ── Market Statistics ────────────────────────────────────────

    def get_market_stats(self) -> dict:
        """Return aggregate market statistics."""
        total_premiums = sum(p.premiums_collected for p in self.pools.values())
        total_claims = sum(p.claims_paid for p in self.pools.values())
        total_reserves = sum(p.reserves for p in self.pools.values())
        total_active = sum(1 for r in self.policies.values() if r.is_active)

        per_insurer: dict[str, dict] = {}
        for ins_id, info in self.insurers.items():
            ins_pools = [self.pools[pid] for pid in info['pool_ids']]
            per_insurer[ins_id] = {
                'pool_count': len(ins_pools),
                'premiums_collected': round(sum(p.premiums_collected for p in ins_pools), 4),
                'claims_paid': round(sum(p.claims_paid for p in ins_pools), 4),
                'reserves': round(sum(p.reserves for p in ins_pools), 4),
                'policy_count': sum(p.policy_count for p in ins_pools),
            }

        total_evasion_flagged = sum(
            1 for r in self.policies.values() if r.evasion_flagged
        )

        return {
            'insurer_count': len(self.insurers),
            'failed_insurer_count': len(self._failed_insurers),
            'failed_insurers': list(self._failed_insurers),
            'pool_count': len(self.pools),
            'active_policies': total_active,
            'total_premiums_collected': round(total_premiums, 4),
            'total_claims_paid': round(total_claims, 4),
            'total_reserves': round(total_reserves, 4),
            'total_evasion_flagged': total_evasion_flagged,
            'insurers': per_insurer,
            'premium_multipliers': {
                k: round(v, 4) for k, v in self.premium_multipliers.items()
            },
        }


# ══════════════════════════════════════════════════════════════════════
#  Demonstration
# ══════════════════════════════════════════════════════════════════════

def demo():
    """
    Run a comprehensive demonstration of the insurance market mechanic.

    Shows:
      - Multiple competing insurers
      - Agents with hidden risk profiles (some honest, some evading)
      - Premium collection through the ledger
      - Claim payment through the ledger
      - Audit uncovering misrepresentation
      - Statistical outlier detection of premium evasion (with 30+ agents)
      - Solvency tracking after claims
      - Zero-sum invariant enforcement
    """
    import sys
    import os
    import random as _random

    # Ensure src/ is on sys.path for standalone runs
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _src_dir = os.path.normpath(os.path.join(_script_dir, '..'))
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)

    # Use EntityType already imported at module level to avoid double-loading
    # the ledger module with a different fully-qualified name.

    print('═' * 70)
    print('INSURANCE MARKET — DEMONSTRATION')
    print('═' * 70)

    # ── 1. Set up ledger ──────────────────────────────────────────
    ledger = LedgerEngine(step_log=False)
    market = InsuranceMarket(
        ledger,
        audit_probability=0.12,
        base_rate=0.05,
        loading_factor=1.3,
        evasion_z_threshold=2.0,
    )

    # ── 2. Register insurers ──────────────────────────────────────
    print('\n─── Registering Insurers ───')
    market.register_insurer('safe_insure', initial_capital=50_000.0, num_pools=2)
    market.register_insurer('risk_accept', initial_capital=30_000.0, num_pools=1)

    for ins_id in ('safe_insure', 'risk_accept'):
        bs = ledger.get_balance(ins_id)
        print(f'  {ins_id}: cash=${bs.cash:.2f}, pools={len(market.insurers[ins_id]["pool_ids"])}')

    # ── 3. Register agents ────────────────────────────────────────
    print('\n─── Registering Agents ───')
    # 5 honest agents (declare their true risk)
    market.register_agent('alice', true_risk=0.02, declared_risk=0.02)
    market.register_agent('bob', true_risk=0.05, declared_risk=0.05)
    market.register_agent('carol', true_risk=0.10, declared_risk=0.10)
    market.register_agent('dan', true_risk=0.03, declared_risk=0.03)
    market.register_agent('ella', true_risk=0.08, declared_risk=0.08)

    # 2 evaders (under-declare their risk — land in the "low" band)
    market.register_agent('dave_evader', true_risk=0.25, declared_risk=0.04)
    market.register_agent('eve_evader', true_risk=0.18, declared_risk=0.04)

    for aid, data in sorted(market.agents.items()):
        print(f'  {aid:15s}  true_risk={data["true_risk"]:.2f}  declared={data["declared_risk"]:.2f}'
              f'  {"⚠ EVADING" if data["true_risk"] > data["declared_risk"] else "honest"}')

    # ── 4. Purchase policies ──────────────────────────────────────
    print('\n─── Purchasing Policies ───')

    agents_insurers = [
        ('alice',       'safe_insure'),
        ('bob',         'safe_insure'),
        ('carol',       'risk_accept'),
        ('dan',         'safe_insure'),
        ('ella',        'risk_accept'),
        ('dave_evader', 'safe_insure'),
        ('eve_evader',  'risk_accept'),
    ]

    for agent_id, ins_id in agents_insurers:
        record = market.purchase_policy(agent_id, ins_id, coverage_limit=5_000.0)
        print(f'  {agent_id:15s} → {ins_id:15s}  premium=${record.premium:.2f}  '
              f'assessed_risk={record.assessed_risk:.2f}')

    stats0 = market.get_market_stats()
    print(f'\n  Active policies: {stats0["active_policies"]}')

    # ── 5. Step 1 — Premium Collection ────────────────────────────
    print('\n' + '─' * 70)
    print('STEP 1 — Premium Collection')
    print('─' * 70)
    ledger.begin_step()
    result = market.run_step()
    n_paid = sum(1 for p in result["premiums"] if p["status"] == "paid")
    total_prem = sum(p.get("premium", 0) for p in result["premiums"])
    print(f'  Premiums collected: {n_paid}/{len(result["premiums"])}  (${total_prem:.2f})')
    for p in result['premiums']:
        status_extra = ''
        if p['status'] != 'paid':
            status_extra = f' ({p.get("reason", "")})'
        print(f'    {p["agent_id"]:15s}  ${p.get("premium", 0):.2f}  → {p["status"]}{status_extra}')
    # Show any audits that triggered during run_step (before premium collection)
    for ar in result.get('audits', []):
        if ar.get('audit_found'):
            print(f'    ⚠ (audit found: {ar["agent_id"]} risk {ar["declared_risk"]}→{ar["true_risk"]}, '
                  f'premium ${ar["old_premium"]:.2f}→${ar["new_premium"]:.2f})')
    ledger.close_step()

    # Show balances after premium collection
    for aid, _ in agents_insurers:
        bs = ledger.get_balance(aid)
        print(f'  {aid:15s} cash=${bs.cash:.2f}')

    # ── 6. Step 2 — Claims ─────────────────────────────────────────
    print('\n' + '─' * 70)
    print('STEP 2 — Claim Events')
    print('─' * 70)
    ledger.begin_step()

    claims = [
        ('alice',       500.0),
        ('bob',        3_000.0),
        ('dave_evader', 4_000.0),
        ('ella',        800.0),
    ]
    for agent_id, amount in claims:
        cr = market.file_claim(agent_id, amount)
        status_display = f'${amount:.0f} → {cr["status"]}, paid=${cr["amount_paid"]:.2f}'
        if cr['status'] != 'paid_in_full':
            status_display += f' (reason: {cr.get("reason", "n/a")})'
        print(f'  {agent_id:15s} claim: {status_display}')

    ledger.close_step()

    # Show insurer state after claims
    for ins_id in ('safe_insure', 'risk_accept'):
        bs = ledger.get_balance(ins_id)
        pool = market.pools[market.insurers[ins_id]['pool_ids'][0]]
        print(f'  {ins_id:15s} cash=${bs.cash:.2f}  pool_reserves=${pool.reserves:.2f}  '
              f'solvency={pool.solvency_ratio:.3f}')

    # ── 7. Step 3 — More claims + audit ───────────────────────────
    print('\n' + '─' * 70)
    print('STEP 3 — Additional Claims & Audit')
    print('─' * 70)
    ledger.begin_step()

    prem_result = market.collect_premiums()
    n_paid = sum(1 for p in prem_result if p["status"] == "paid")
    print(f'  Premiums collected: {n_paid}/{len(prem_result)}')

    # More claims
    for agent_id, amount in [('eve_evader', 2_000.0), ('carol', 1_500.0)]:
        cr = market.file_claim(agent_id, amount)
        print(f'  {agent_id:15s} claim: ${amount:.0f} → {cr["status"]}, paid=${cr["amount_paid"]:.2f}')

    # Run audits
    audit_results = market.run_audits()
    audits_found = [ar for ar in audit_results if ar['audit_found']]
    for ar in audits_found:
        print(f'  ⚠ AUDIT: {ar["agent_id"]} declared_risk={ar["declared_risk"]:.2f} '
              f'→ true_risk={ar["true_risk"]:.2f}  premium ${ar["old_premium"]:.2f}→${ar["new_premium"]:.2f}')
    if not audits_found:
        print(f'  No audits revealed misrepresentation this step')

    ledger.close_step()

    # ── 8. Statistical Evasion Detection Demo ──────────────────────
    print('\n' + '─' * 70)
    print('STEP 4 — Premium Evasion Detection (with 30+ agents)')
    print('─' * 70)

    # Create a separate market with enough agents for statistics
    ev_ledger = LedgerEngine(step_log=False)
    ev_market = InsuranceMarket(
        ev_ledger,
        audit_probability=0.0,   # no audits to let evasion persist
        base_rate=0.05,
        loading_factor=1.3,
        evasion_z_threshold=2.0,
    )
    ev_market.register_insurer('ev_insurer', initial_capital=200_000.0, num_pools=1)

    # 30 honest agents — true risk = declared risk
    _random.seed(42)
    for i in range(30):
        true_r = _random.uniform(0.02, 0.08)
        ev_market.register_agent(f'h_{i:03d}', true_risk=true_r, declared_risk=true_r)

    # 4 evaders — declared risk in "low" band but true risk is high
    ev_market.register_agent('e_evader_1', true_risk=0.30, declared_risk=0.04)
    ev_market.register_agent('e_evader_2', true_risk=0.28, declared_risk=0.04)
    ev_market.register_agent('e_evader_3', true_risk=0.22, declared_risk=0.04)
    ev_market.register_agent('e_evader_4', true_risk=0.35, declared_risk=0.04)

    # Purchase policies
    all_agents = [f'h_{i:03d}' for i in range(30)] + \
                 [f'e_evader_{i}' for i in range(1, 5)]
    for aid in all_agents:
        ev_market.purchase_policy(aid, 'ev_insurer', coverage_limit=2_000.0)

    # Simulate 6 steps: collect premiums, trigger claims
    for step_num in range(1, 7):
        ev_ledger.begin_step()
        ev_market.collect_premiums()

        # Honest agents: 1–2% file small claims
        for i in range(30):
            if _random.random() < 0.015:
                ev_market.file_claim(f'h_{i:03d}', _random.uniform(50, 300))

        # Evaders: file large claims frequently
        for i in range(1, 5):
            ev_market.file_claim(f'e_evader_{i}', _random.uniform(800, 2_000))

        ev_ledger.close_step()

    # Now detect
    ev_flags = ev_market.detect_premium_evasion()
    print(f'  Total agents: {len(all_agents)}')
    print(f'  Evaders in pool: 4 (true_risk 0.22–0.35, declared 0.04)')
    print(f'  Honest agents: 30 (risk 0.02–0.08)')
    print(f'  Simulated steps: 6')
    print(f'')
    print(f'  Agents flagged for premium evasion: {len(ev_flags)}')
    for ef in ev_flags:
        print(f'    ⚠ {ef["agent_id"]:12s}  band={ef["band"]:10s}  '
              f'loss_ratio={ef["loss_ratio"]:<8.2f}  '
              f'band_mean={ef["band_mean_loss_ratio"]:<8.2f}  '
              f'z_score={ef["z_score"]:>5.1f}  '
              f'declared={ef["declared_risk"]:.2f} true={ef["true_risk"]:.2f}')

    if not ev_flags:
        print('  (threshold not reached — try more steps or lower z threshold)')
    else:
        print(f'\n  ✓ Statistical outlier detection correctly identifies evaders '
              f'by their anomalous loss ratio within their declared-risk band.')

    ev_total = ev_ledger.get_total_flow('premium')
    ev_claims = ev_ledger.get_total_flow('claim')
    print(f'  Evasion-detect market: premiums=${ev_total:.2f} claims=${ev_claims:.2f}')

    # ── 9. Solvency Check ──────────────────────────────────────────
    print('\n' + '─' * 70)
    print('SOLVENCY TRACKING (main market)')
    print('─' * 70)
    solvency = market.check_solvency()
    for s in solvency:
        flag = ' ⚠ INSOLVENT' if not s['is_solvent'] else '  ✓ solvent'
        print(f'  {s["pool_id"]:25s}  reserves=${s["reserves"]:<8.2f}  '
              f'premiums=${s["premiums_collected"]:<8.2f}  '
              f'claims=${s["claims_paid"]:<8.2f}  '
              f'solvency={s["solvency_ratio"]:<8.3f}{flag}')

    # ── 10. Final Market Summary ───────────────────────────────────
    print('\n' + '─' * 70)
    print('FINAL MARKET SUMMARY')
    print('─' * 70)
    stats = market.get_market_stats()
    print(f'  Insurers:            {stats["insurer_count"]}')
    print(f'  Pools:               {stats["pool_count"]}')
    print(f'  Active policies:     {stats["active_policies"]}')
    print(f'  Total premiums:      ${stats["total_premiums_collected"]:.2f}')
    print(f'  Total claims paid:   ${stats["total_claims_paid"]:.2f}')
    print(f'  Total reserves:      ${stats["total_reserves"]:.2f}')
    print(f'  Evasion flags:       {stats["total_evasion_flagged"]}')
    for ins_id, istats in stats['insurers'].items():
        print(f'  ─ {ins_id:15s}  premiums=${istats["premiums_collected"]:<8.2f}  '
              f'claims=${istats["claims_paid"]:<8.2f}  '
              f'reserves=${istats["reserves"]:<8.2f}  '
              f'policies={istats["policy_count"]}')

    # ── 11. Ledger verification ────────────────────────────────────
    print('\n' + '─' * 70)
    print('LEDGER VERIFICATION')
    print('─' * 70)
    total_money = sum(bs.cash for bs in ledger.balances.values())
    print(f'  Total money in system: ${total_money:.2f}')
    print(f'  Total transfers:       {len(ledger.transfers)}')
    print(f'  Total ledger entries:  {len(ledger.entries)}')
    print(f'  Steps executed:        {ledger.step}')

    all_balanced = all(m['balanced'] for m in ledger.step_metrics)
    print(f'  All steps balanced:    {all_balanced}')
    if not all_balanced:
        for m in ledger.step_metrics:
            if not m['balanced']:
                print(f'    Step {m["step"]}: imbalance={m["imbalance"]:.6f}')

    premium_flow = ledger.get_total_flow('premium')
    claim_flow = ledger.get_total_flow('claim')
    print(f'  Total premium flow:    ${premium_flow:.2f}')
    print(f'  Total claim flow:      ${claim_flow:.2f}')

    print('\n' + '═' * 70)
    print('DEMONSTRATION COMPLETE')
    print('═' * 70)

    return market, ledger


# ══════════════════════════════════════════════════════════════════════
#  Runner
# ══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    demo()
