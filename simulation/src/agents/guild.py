"""
agents/guild.py — Guild Agent

Each Guild sets certification standards (affects member worker productivity),
collects dues from members, manages a mutual insurance pool, and can restrict
membership. All financial interactions are recorded through the LedgerEngine.

SPEC REFERENCES
  - AGENT_MODEL.md §2.4 (Guild attributes)
  - AGENT_MODEL.md §3.5 (Guild utility)
  - AGENT_MODEL.md §9.4 (Guild decision variables)
  - AGENT_MODEL.md §11.4 (Worker ↔ Guild interaction)
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from ..core.ledger import LedgerEngine, EntityType
except ImportError:
    from core.ledger import LedgerEngine, EntityType


# ══════════════════════════════════════════════════════════════════════
#  Guild Member Record
# ══════════════════════════════════════════════════════════════════════


@dataclass
class GuildMemberRecord:
    """Tracks a worker's membership in a guild."""

    member_id: str
    guild_id: str
    skill_at_join: float              # Worker's skill level when they joined
    current_skill: float              # Updated by certification effects
    productivity_multiplier: float    # From certification (≥ 1.0)
    dues_paid_total: float = 0.0
    benefits_received: float = 0.0    # Mutual pool payouts received
    step_joined: int = 0
    is_active: bool = True

    @property
    def net_contribution(self) -> float:
        """Dues paid minus benefits received (positive = net contributor)."""
        return self.dues_paid_total - self.benefits_received

    def to_dict(self) -> dict:
        return {
            'member_id': self.member_id,
            'guild_id': self.guild_id,
            'skill_at_join': round(self.skill_at_join, 4),
            'current_skill': round(self.current_skill, 4),
            'productivity_multiplier': round(self.productivity_multiplier, 4),
            'dues_paid_total': round(self.dues_paid_total, 4),
            'benefits_received': round(self.benefits_received, 4),
            'net_contribution': round(self.net_contribution, 4),
            'step_joined': self.step_joined,
            'is_active': self.is_active,
        }


# ══════════════════════════════════════════════════════════════════════
#  Certification Standards
# ══════════════════════════════════════════════════════════════════════


@dataclass
class CertificationStandards:
    """
    Certification requirements set by the guild.

    Attributes
    ----------
    min_skill : float ∈ [0, 1]
        Minimum worker skill level required for membership.
    productivity_boost : float ≥ 1.0
        Multiplier applied to member skill productivity (e.g. 1.10 = +10%).
        Represents training, quality signalling, and best-practice sharing.
    recertification_interval : int
        Steps between mandatory skill re-assessments (0 = no re-cert).
    testing_fee : float
        Fee charged to members for certification testing/renewal.
    """

    min_skill: float = 0.3
    productivity_boost: float = 1.10
    recertification_interval: int = 0       # 0 = no recert required
    testing_fee: float = 10.0

    def to_dict(self) -> dict:
        return {
            'min_skill': round(self.min_skill, 4),
            'productivity_boost': round(self.productivity_boost, 4),
            'recertification_interval': self.recertification_interval,
            'testing_fee': round(self.testing_fee, 4),
        }


# ══════════════════════════════════════════════════════════════════════
#  Guild Mutual Pool
# ══════════════════════════════════════════════════════════════════════


@dataclass
class GuildMutualPool:
    """
    Mutual insurance pool managed by the guild.
    Collects a portion of dues and pays benefits to members in distress.

    Attributes
    ----------
    total_reserves : float
        Current cash held in the pool.
    total_dues_allocated : float
        Cumulative dues allocated to the pool.
    total_benefits_paid : float
        Cumulative benefits paid out.
    solvency_target : float
        Desired reserve-to-obligation ratio.
    benefit_rate : float ∈ [0, 1]
        Fraction of pool reserves paid per eligible member per distress event.
    """

    total_reserves: float = 0.0
    total_dues_allocated: float = 0.0
    total_benefits_paid: float = 0.0
    solvency_target: float = 1.5
    benefit_rate: float = 0.05    # Pay 5 % of reserves per distressed member

    @property
    def solvency_ratio(self) -> float:
        """Simple solvency: ratio of reserves to total benefits paid out so far."""
        if self.total_benefits_paid <= 0:
            return float('inf') if self.total_reserves > 0 else 0.0
        return self.total_reserves / max(self.total_benefits_paid, 1.0)

    @property
    def is_solvent(self) -> bool:
        return self.solvency_ratio >= 0.3  # Hard floor

    def allocate_dues(self, amount: float) -> float:
        """Allocate a portion of dues to the mutual pool. Returns new reserves."""
        if amount < 0:
            raise ValueError(f"Negative dues allocation: {amount}")
        self.total_reserves += amount
        self.total_dues_allocated += amount
        return self.total_reserves

    def pay_benefit(self, amount: float) -> tuple[bool, float]:
        """
        Pay a benefit from the pool.

        Returns
        -------
        (paid_in_full, amount_paid)
            If reserves are insufficient, pays what is available.
        """
        if amount < 0:
            raise ValueError(f"Negative benefit amount: {amount}")
        paid = min(amount, self.total_reserves)
        self.total_reserves -= paid
        self.total_benefits_paid += paid
        return paid >= amount, paid

    def get_status(self) -> dict:
        return {
            'total_reserves': round(self.total_reserves, 4),
            'total_dues_allocated': round(self.total_dues_allocated, 4),
            'total_benefits_paid': round(self.total_benefits_paid, 4),
            'solvency_ratio': round(self.solvency_ratio, 4),
            'is_solvent': self.is_solvent,
        }

    def to_dict(self) -> dict:
        return self.get_status()


# ══════════════════════════════════════════════════════════════════════
#  Guild Agent
# ══════════════════════════════════════════════════════════════════════


class GuildAgent:
    """
    Guild agent managing a worker collective.

    Each guild:
      1. Sets / updates certification standards (min_skill, productivity_boost).
      2. Collects dues from members (via ledger transfers).
      3. Manages a mutual insurance pool (allocates dues, pays benefits).
      4. Admits / rejects applicants (enforces certification requirements).
      5. Can expel members (restrict membership).

    All financial flows pass through the LedgerEngine for double-entry
    accounting and zero-sum enforcement.
    """

    def __init__(
        self,
        guild_id: str,
        ledger: LedgerEngine,
        *,
        # Dues
        dues_rate: float = 0.02,       # Fraction of member cash per step
        mutual_allocation_frac: float = 0.50,  # Fraction of dues → mutual pool
        # Certification
        min_skill: float = 0.3,
        productivity_boost: float = 1.10,
        recertification_interval: int = 0,
        testing_fee: float = 10.0,
        # Pool
        solvency_target: float = 1.5,
        benefit_rate: float = 0.05,
        # Membership
        max_members: int = 100,
        # Financial
        initial_cash: float = 1000.0,
    ):
        self.guild_id = guild_id
        self.ledger = ledger

        # ── Parameters ──────────────────────────────────────────
        self.dues_rate = dues_rate
        self.mutual_allocation_frac = mutual_allocation_frac
        self.max_members = max_members

        # ── Certification ───────────────────────────────────────
        self.certification = CertificationStandards(
            min_skill=min_skill,
            productivity_boost=productivity_boost,
            recertification_interval=recertification_interval,
            testing_fee=testing_fee,
        )

        # ── Mutual Pool ─────────────────────────────────────────
        self.mutual_pool = GuildMutualPool(
            solvency_target=solvency_target,
            benefit_rate=benefit_rate,
        )

        # ── Members ────────────────────────────────────────────
        self.members: dict[str, GuildMemberRecord] = {}

        # ── Applicant queue ────────────────────────────────────
        self.applicants: dict[str, dict[str, Any]] = {}

        # ── Step tracking ──────────────────────────────────────
        self.step_metrics: list[dict] = []

        # ── Register ledger entity ─────────────────────────────
        if not self.ledger.entity_exists(guild_id):
            self.ledger.register_entity(
                guild_id,
                EntityType.GUILD,
                initial_cash=initial_cash,
            )

    # ══════════════════════════════════════════════════════════════════
    #  Properties
    # ══════════════════════════════════════════════════════════════════

    @property
    def member_count(self) -> int:
        return len(self.members)

    @property
    def active_member_count(self) -> int:
        return sum(1 for m in self.members.values() if m.is_active)

    @property
    def balance_sheet(self):
        return self.ledger.get_balance(self.guild_id)

    @property
    def cash(self) -> float:
        return self.balance_sheet.cash

    # ══════════════════════════════════════════════════════════════════
    #  1. Certification Management
    # ══════════════════════════════════════════════════════════════════

    def set_certification_standards(
        self,
        *,
        min_skill: Optional[float] = None,
        productivity_boost: Optional[float] = None,
        recertification_interval: Optional[int] = None,
        testing_fee: Optional[float] = None,
    ) -> dict:
        """
        Update the guild's certification standards.

        Parameters
        ----------
        min_skill : float or None
            Minimum worker skill for membership (0–1).
        productivity_boost : float or None
            Productivity multiplier for certified members (≥ 1.0).
        recertification_interval : int or None
            Steps between re-certification (0 = none).
        testing_fee : float or None
            Fee for certification testing.

        Returns the updated standards dict.
        """
        if min_skill is not None:
            if not (0.0 <= min_skill <= 1.0):
                raise ValueError(f"min_skill must be in [0, 1], got {min_skill}")
            self.certification.min_skill = min_skill

        if productivity_boost is not None:
            if productivity_boost < 1.0:
                raise ValueError(
                    f"productivity_boost must be ≥ 1.0, got {productivity_boost}"
                )
            self.certification.productivity_boost = productivity_boost

        if recertification_interval is not None:
            if recertification_interval < 0:
                raise ValueError(
                    f"recertification_interval must be ≥ 0, "
                    f"got {recertification_interval}"
                )
            self.certification.recertification_interval = recertification_interval

        if testing_fee is not None:
            if testing_fee < 0:
                raise ValueError(f"testing_fee must be ≥ 0, got {testing_fee}")
            self.certification.testing_fee = testing_fee

        # Update productivity multipliers for existing members
        step = self.ledger.step
        for member in self.members.values():
            if member.is_active:
                member.productivity_multiplier = self.certification.productivity_boost

        return self.certification.to_dict()

    def get_certification_status(self) -> dict:
        """Return current certification standards plus member stats."""
        return {
            'standards': self.certification.to_dict(),
            'certified_members': self.active_member_count,
            'total_members': self.member_count,
        }

    # ══════════════════════════════════════════════════════════════════
    #  2. Membership Management
    # ══════════════════════════════════════════════════════════════════

    def can_join(self, agent_id: str, skill: float) -> tuple[bool, str]:
        """
        Check if a worker meets guild membership requirements.

        Returns (can_join, reason).
        """
        if agent_id in self.members:
            return False, "Already a member"

        if self.active_member_count >= self.max_members:
            return False, "Guild at maximum capacity"

        if skill < self.certification.min_skill:
            return (
                False,
                f"Skill {skill:.3f} below minimum {self.certification.min_skill:.3f}",
            )

        if not self.ledger.entity_exists(agent_id):
            return False, "Agent not registered in ledger"

        return True, "Meets requirements"

    def admit_member(
        self,
        agent_id: str,
        skill: float,
        **kwargs,
    ) -> GuildMemberRecord:
        """
        Admit a new member to the guild.

        Parameters
        ----------
        agent_id : str
            The worker's entity ID.
        skill : float
            The worker's skill level (0–1).
        **kwargs
            Additional fields passed to GuildMemberRecord.

        Returns the GuildMemberRecord.
        """
        can_join, reason = self.can_join(agent_id, skill)
        if not can_join:
            raise ValueError(f"Cannot admit {agent_id}: {reason}")

        # Collect any testing / certification fee first
        if self.certification.testing_fee > 0:
            try:
                self.ledger.transfer(
                    from_id=agent_id,
                    to_id=self.guild_id,
                    mechanism='guild_testing_fee',
                    amount=self.certification.testing_fee,
                    description=(
                        f"Certification fee: {agent_id} → {self.guild_id}"
                    ),
                )
            except Exception as exc:
                raise ValueError(
                    f"Failed to collect testing fee from {agent_id}: {exc}"
                ) from exc

        record = GuildMemberRecord(
            member_id=agent_id,
            guild_id=self.guild_id,
            skill_at_join=skill,
            current_skill=skill,
            productivity_multiplier=self.certification.productivity_boost,
            step_joined=self.ledger.step,
            **kwargs,
        )
        self.members[agent_id] = record

        # Remove from applicant queue if present
        self.applicants.pop(agent_id, None)

        return record

    def apply_for_membership(self, agent_id: str, skill: float) -> dict:
        """
        Register a worker's application. Returns the application result.

        If the worker meets certification requirements, they are immediately
        admitted.  Otherwise they are placed in the applicant queue for
        manual review.
        """
        if agent_id in self.members:
            return {'status': 'already_member', 'agent_id': agent_id}

        if agent_id in self.applicants:
            return {'status': 'already_applied', 'agent_id': agent_id}

        meets_requirements, reason = self.can_join(agent_id, skill)

        if meets_requirements:
            record = self.admit_member(agent_id, skill)
            return {
                'status': 'admitted',
                'agent_id': agent_id,
                'record': record.to_dict(),
            }

        # Queue for manual review
        self.applicants[agent_id] = {
            'agent_id': agent_id,
            'skill': skill,
            'step_applied': self.ledger.step,
            'reason': reason,
        }
        return {
            'status': 'pending',
            'agent_id': agent_id,
            'reason': reason,
        }

    def reject_applicant(self, agent_id: str) -> dict:
        """Reject a pending applicant."""
        if agent_id not in self.applicants:
            raise ValueError(f"No pending application from {agent_id}")
        app = self.applicants.pop(agent_id)
        return {
            'status': 'rejected',
            'agent_id': agent_id,
            'reason': 'Rejected by guild',
        }

    def expel_member(self, agent_id: str, reason: str = '') -> dict:
        """
        Expel a member from the guild (membership restriction).

        Returns a dict with the outcome.
        """
        if agent_id not in self.members:
            raise ValueError(f"{agent_id} is not a member")
        self.members[agent_id].is_active = False
        return {
            'status': 'expelled',
            'agent_id': agent_id,
            'guild_id': self.guild_id,
            'reason': reason or 'Expelled by guild',
        }

    # ══════════════════════════════════════════════════════════════════
    #  3. Dues Collection
    # ══════════════════════════════════════════════════════════════════

    def collect_dues(self) -> list[dict]:
        """
        Collect membership dues from all active members.

        Dues are a flat percentage of the member's current cash balance.
        A portion of each due is allocated to the mutual pool.

        All transfers are recorded on the ledger.

        Returns a list of result dicts per member.
        """
        results: list[dict] = []
        for member_id, record in list(self.members.items()):
            if not record.is_active:
                continue
            if not self.ledger.entity_exists(member_id):
                # Member's entity has been removed; mark inactive
                record.is_active = False
                results.append({
                    'member_id': member_id,
                    'status': 'lapsed',
                    'reason': 'entity_removed',
                })
                continue

            member_bs = self.ledger.get_balance(member_id)
            due_amount = member_bs.cash * self.dues_rate

            if due_amount <= 0.001:
                results.append({
                    'member_id': member_id,
                    'status': 'skipped',
                    'reason': 'no_cash',
                    'due': 0.0,
                })
                continue

            # Execute ledger transfer (member → guild)
            try:
                self.ledger.transfer(
                    from_id=member_id,
                    to_id=self.guild_id,
                    mechanism='guild_dues',
                    amount=due_amount,
                    description=f"Guild dues: {member_id} → {self.guild_id}",
                )
            except Exception as exc:
                results.append({
                    'member_id': member_id,
                    'status': 'failed',
                    'reason': str(exc),
                })
                continue

            # Allocate portion to mutual pool
            pool_allocation = due_amount * self.mutual_allocation_frac
            guild_allocation = due_amount - pool_allocation

            # The guild's cash already increased; we now move the pool portion
            # conceptually.  Since the mutual pool is a sub-account tracked by
            # the guild itself (not a separate ledger entity), we do an internal
            # accounting transfer on the ledger for transparency.
            if pool_allocation > 0:
                self.ledger.transfer(
                    from_id=self.guild_id,
                    to_id=self.guild_id,
                    mechanism='guild_pool_allocation',
                    amount=pool_allocation,
                    description=(
                        f"Mutual pool allocation from {member_id}'s dues"
                    ),
                )
                self.mutual_pool.allocate_dues(pool_allocation)

            # Update member record
            record.dues_paid_total += due_amount

            results.append({
                'member_id': member_id,
                'status': 'paid',
                'due': round(due_amount, 4),
                'pool_allocation': round(pool_allocation, 4),
                'guild_allocation': round(guild_allocation, 4),
            })

        return results

    # ══════════════════════════════════════════════════════════════════
    #  4. Mutual Pool Management
    # ══════════════════════════════════════════════════════════════════

    def distribute_benefits(self, distressed_members: list[str]) -> list[dict]:
        """
        Distribute mutual pool benefits to members facing financial distress.

        Each distressed member receives a share of the mutual pool based on
        the configured benefit_rate.

        Parameters
        ----------
        distressed_members : list of str
            Member IDs who are in financial distress (e.g. low cash, insolvent).

        Returns a list of result dicts per member.
        """
        results: list[dict] = []
        if not distressed_members:
            return results

        # Only pay benefits to active members
        eligible = [
            m_id for m_id in distressed_members
            if m_id in self.members and self.members[m_id].is_active
        ]

        if not eligible:
            return results

        # Per-member benefit amount
        per_member_benefit = (
            self.mutual_pool.total_reserves * self.mutual_pool.benefit_rate
            / len(eligible)
        )

        for member_id in eligible:
            if per_member_benefit <= 0.001:
                break

            paid_in_full, amount_paid = self.mutual_pool.pay_benefit(
                per_member_benefit
            )

            if amount_paid <= 0:
                continue

            # Ledger transfer (guild → member)
            try:
                self.ledger.transfer(
                    from_id=self.guild_id,
                    to_id=member_id,
                    mechanism='guild_benefit',
                    amount=amount_paid,
                    description=(
                        f"Mutual pool benefit: {self.guild_id} → {member_id}"
                    ),
                )
            except Exception as exc:
                results.append({
                    'member_id': member_id,
                    'status': 'failed',
                    'reason': str(exc),
                })
                continue

            # Update member record
            self.members[member_id].benefits_received += amount_paid

            results.append({
                'member_id': member_id,
                'amount': round(amount_paid, 4),
                'paid_in_full': paid_in_full,
                'status': 'paid',
            })

        return results

    def get_pool_status(self) -> dict:
        """Return the current status of the mutual pool."""
        return self.mutual_pool.get_status()

    # ══════════════════════════════════════════════════════════════════
    #  5. Per-Step Agent Loop
    # ══════════════════════════════════════════════════════════════════

    def step(
        self,
        *,
        new_cert_standards: Optional[dict] = None,
        applicants_to_admit: Optional[list[str]] = None,
        applicants_to_reject: Optional[list[str]] = None,
        members_to_expel: Optional[list[tuple[str, str]]] = None,
        distressed_members: Optional[list[str]] = None,
    ) -> dict:
        """
        Execute one simulation step for this guild.

        Step actions (in order):
          1. Optionally update certification standards.
          2. Collect dues from all active members.
          3. Manage mutual pool (distribute benefits to distressed members).
          4. Process membership applications (admit / reject) and expulsions.

        Parameters
        ----------
        new_cert_standards : dict or None
            New certification parameters to apply before collecting dues.
        applicants_to_admit : list of str or None
            List of applicant agent IDs to admit (manual override).
        applicants_to_reject : list of str or None
            List of applicant agent IDs to reject.
        members_to_expel : list of (member_id, reason) or None
            Members to expel.
        distressed_members : list of str or None
            Members facing financial distress who should receive benefits.

        Returns a summary dict for this step.
        """
        step_summary = {
            'guild_id': self.guild_id,
            'step': self.ledger.step,
            'actions': {},
        }

        # ── 1. Update certification standards ──────────────────────
        if new_cert_standards:
            updated = self.set_certification_standards(**new_cert_standards)
            step_summary['actions']['certification_updated'] = updated

        # ── 2. Collect dues ────────────────────────────────────────
        dues_results = self.collect_dues()
        total_dues = sum(
            r.get('due', 0.0) for r in dues_results if r['status'] == 'paid'
        )
        step_summary['actions']['dues_collected'] = {
            'total_dues': round(total_dues, 4),
            'member_count': self.active_member_count,
            'results': dues_results,
        }

        # ── 3. Manage mutual pool ──────────────────────────────────
        if distressed_members:
            benefit_results = self.distribute_benefits(distressed_members)
            total_benefits = sum(
                r.get('amount', 0.0) for r in benefit_results
                if r['status'] == 'paid'
            )
            step_summary['actions']['benefits_distributed'] = {
                'total_benefits': round(total_benefits, 4),
                'pool_status': self.mutual_pool.get_status(),
                'results': benefit_results,
            }

        # ── 4. Process membership changes ──────────────────────────
        membership_changes = []

        # Admit applicants (auto-admit those who meet requirements)
        for app_id, app_data in list(self.applicants.items()):
            if applicants_to_admit and app_id in applicants_to_admit:
                try:
                    record = self.admit_member(
                        app_id, app_data['skill'],
                    )
                    membership_changes.append({
                        'action': 'admitted',
                        'agent_id': app_id,
                        'by': 'manual_override',
                    })
                except ValueError as e:
                    membership_changes.append({
                        'action': 'admit_failed',
                        'agent_id': app_id,
                        'reason': str(e),
                    })

        # Reject applicants
        if applicants_to_reject:
            for app_id in applicants_to_reject:
                if app_id in self.applicants:
                    self.reject_applicant(app_id)
                    membership_changes.append({
                        'action': 'rejected',
                        'agent_id': app_id,
                    })

        # Expel members
        if members_to_expel:
            for m_id, reason in members_to_expel:
                try:
                    self.expel_member(m_id, reason)
                    membership_changes.append({
                        'action': 'expelled',
                        'agent_id': m_id,
                        'reason': reason,
                    })
                except ValueError as e:
                    membership_changes.append({
                        'action': 'expel_failed',
                        'agent_id': m_id,
                        'reason': str(e),
                    })

        if membership_changes:
            step_summary['actions']['membership_changes'] = membership_changes

        # ── Record step metrics ────────────────────────────────────
        guild_bs = self.balance_sheet
        metrics = {
            'step': self.ledger.step,
            'cash': round(guild_bs.cash, 4),
            'active_members': self.active_member_count,
            'total_members': self.member_count,
            'pending_applicants': len(self.applicants),
            'mutual_pool': self.mutual_pool.get_status(),
            'certification': self.certification.to_dict(),
        }
        self.step_metrics.append(metrics)
        step_summary['metrics'] = metrics

        return step_summary

    # ══════════════════════════════════════════════════════════════════
    #  Utility & Reporting
    # ══════════════════════════════════════════════════════════════════

    def get_member_summary(self) -> list[dict]:
        """Return a list of all member record dicts."""
        return [m.to_dict() for m in self.members.values()]

    def get_applicant_summary(self) -> list[dict]:
        """Return a list of pending applicants."""
        return list(self.applicants.values())

    def get_status(self) -> dict:
        """Full status report for this guild."""
        return {
            'guild_id': self.guild_id,
            'cash': round(self.cash, 4),
            'active_members': self.active_member_count,
            'total_members': self.member_count,
            'max_members': self.max_members,
            'dues_rate': self.dues_rate,
            'mutual_allocation_frac': self.mutual_allocation_frac,
            'certification': self.certification.to_dict(),
            'mutual_pool': self.mutual_pool.get_status(),
            'pending_applicants': len(self.applicants),
        }

    def to_dict(self) -> dict:
        return self.get_status()


# ══════════════════════════════════════════════════════════════════════
#  Demonstration
# ══════════════════════════════════════════════════════════════════════


def demo():
    """Run a demonstration of the Guild agent lifecycle."""
    print("═" * 70)
    print("GUILD AGENT — DEMONSTRATION")
    print("═" * 70)

    # ── Setup ──────────────────────────────────────────────────────
    from ..core.ledger import LedgerEngine  # noqa: F811

    ledger = LedgerEngine()
    guild = GuildAgent(
        guild_id='guild_alpha',
        ledger=ledger,
        dues_rate=0.02,
        mutual_allocation_frac=0.50,
        min_skill=0.3,
        productivity_boost=1.15,
        testing_fee=5.0,
        benefit_rate=0.05,
        initial_cash=500.0,
    )

    # Register some workers on the ledger
    workers = {}
    worker_skills = [0.45, 0.60, 0.25, 0.80, 0.50, 0.35, 0.70]
    for i, skill in enumerate(worker_skills):
        worker_id = f"worker_{i}"
        ledger.register_entity(
            worker_id, EntityType.CITIZEN, initial_cash=1000.0 + i * 200,
        )
        workers[worker_id] = skill

    print(f"\n  Guild created: {guild.guild_id}")
    print(f"  Initial cash: ${guild.cash:.2f}")
    print(f"  Initial cert standards: {guild.certification.to_dict()}")
    print(f"  Workers registered: {len(workers)}")

    # ── Step 1: Admit members ──────────────────────────────────────
    print("\n─── Step 1: Membership Applications ───")
    ledger.begin_step()

    for w_id, skill in workers.items():
        result = guild.apply_for_membership(w_id, skill)
        status_icon = "✅" if result['status'] == 'admitted' else (
            "⏳" if result['status'] == 'pending' else "❌"
        )
        print(f"  {status_icon} {w_id} (skill={skill:.2f}): {result['status']}")

    metrics = ledger.close_step()
    print(f"\n  Members: {guild.active_member_count} active, "
          f"{guild.member_count} total")
    print(f"  Applicants pending: {len(guild.applicants)} (worker_2 has skill "
          f"{worker_skills[2]:.2f} < min {guild.certification.min_skill})")
    print(f"  Ledger balanced: {metrics['balanced']}")

    # ── Step 2: Manually admit the low-skill worker ────────────────
    # (The guild could choose to lower standards or reject them)
    print("\n─── Step 2: Manual Admission & Collect Dues ───")
    ledger.begin_step()

    # Admit worker_2 (low skill) by lowering standards then manually admitting
    guild.set_certification_standards(min_skill=0.2)
    record = guild.admit_member('worker_2', 0.25)
    print(f"  After lowering min_skill to 0.2: {record.member_id} admitted "
          f"(boost=×{record.productivity_multiplier})")

    # Collect dues
    dues_result = guild.collect_dues()
    total_dues = sum(r.get('due', 0.0) for r in dues_result
                     if r['status'] == 'paid')
    print(f"  Dues collected: ${total_dues:.2f} from "
          f"{sum(1 for r in dues_result if r['status'] == 'paid')} members")
    for r in dues_result:
        if r['status'] == 'paid':
            print(f"    {r['member_id']}: ${r['due']:.2f} "
                  f"(pool: ${r['pool_allocation']:.2f})")

    metrics = ledger.close_step()
    print(f"  Guild cash: ${guild.cash:.2f}")
    print(f"  Mutual pool reserves: ${guild.mutual_pool.total_reserves:.2f}")
    print(f"  Ledger balanced: {metrics['balanced']}")

    # ── Step 3: Certification Update + Benefits ────────────────────
    print("\n─── Step 3: Raise Standards & Distribute Benefits ───")
    ledger.begin_step()

    # Guild tightens certification standards
    guild.step(
        new_cert_standards={
            'min_skill': 0.35,
            'productivity_boost': 1.25,
        },
    )

    # Some members are in distress
    distressed = ['worker_0', 'worker_3']
    benefit_results = guild.distribute_benefits(distressed)

    print(f"  New cert: min_skill={guild.certification.min_skill}, "
          f"boost=×{guild.certification.productivity_boost}")
    print(f"  Benefits paid to distressed members:")
    for r in benefit_results:
        if r['status'] == 'paid':
            print(f"    {r['member_id']}: ${r['amount']:.2f}")

    metrics = ledger.close_step()
    print(f"  Guild cash: ${guild.cash:.2f}")
    print(f"  Mutual pool: ${guild.mutual_pool.total_reserves:.2f} "
          f"(solvency: {guild.mutual_pool.solvency_ratio:.2f})")
    print(f"  Ledger balanced: {metrics['balanced']}")

    # ── Step 4: Expel a member + reject applicant ──────────────────
    print("\n─── Step 4: Membership Restrictions ───")
    ledger.begin_step()

    # Expel a member
    guild.expel_member('worker_5', reason='Low productivity')
    print(f"  Expelled worker_5")

    # Reject a pending applicant
    if len(guild.applicants) > 0:
        app_id = list(guild.applicants.keys())[0]
        guild.reject_applicant(app_id)
        print(f"  Rejected applicant {app_id}")

    # Collect dues (skips expelled/lapsed members)
    guild.collect_dues()
    metrics = ledger.close_step()

    print(f"  Active members: {guild.active_member_count}")
    print(f"  Pending applicants: {len(guild.applicants)}")
    print(f"  Ledger balanced: {metrics['balanced']}")

    # ── Summary ────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("FINAL GUILD STATUS")
    print("─" * 70)
    status = guild.get_status()
    for k, v in status.items():
        print(f"  {k}: {v}")

    member_sheet = guild.get_member_summary()
    print(f"\n  Members ({len(member_sheet)}):")
    for m in member_sheet:
        print(f"    {m['member_id']}: skill={m['current_skill']:.2f}, "
              f"boost=×{m['productivity_multiplier']:.2f}, "
              f"dues=${m['dues_paid_total']:.2f}, "
              f"benefits=${m['benefits_received']:.2f}, "
              f"active={m['is_active']}")

    # Check zero-sum across all steps
    print(f"\n{'─' * 70}")
    print(f"LEDGER SUMMARY")
    print(f"{'─' * 70}")
    print(f"  Total transfers: {len(ledger.transfers)}")
    print(f"  Total entries:  {len(ledger.entries)}")
    print(f"  Steps simulated: {len(ledger.step_metrics)}")
    all_balanced = all(m['balanced'] for m in ledger.step_metrics)
    print(f"  All steps zero-sum: {'✅ YES' if all_balanced else '❌ NO'}")

    total_money = sum(bs.cash for bs in ledger.balances.values())
    print(f"  Total money in system: ${total_money:.2f}")

    # Guild-specific flow
    guild_flow = ledger.flow
    print(f"\n  Flow matrix (last step guild interactions):")
    guild_out = guild_flow.get(EntityType.GUILD, EntityType.CITIZEN)
    guild_in = guild_flow.get(EntityType.CITIZEN, EntityType.GUILD)
    print(f"    GUILD → CITIZEN: ${guild_out:.2f} (benefits)")
    print(f"    CITIZEN → GUILD: ${guild_in:.2f} (dues/fees)")

    print(f"\n{'═' * 70}")
    print("DEMONSTRATION COMPLETE")
    print(f"{'═' * 70}")


if __name__ == '__main__':
    demo()
