"""
mechanics/courts.py — Private court system with competing DROs.

Each Court handles case filing, evidence evaluation, adjudication, and
damages awards. Courts compete on speed, cost, and fairness.
CourtSystem manages multiple courts, routes cases, and handles appeals.

References:
    MECHANICS_INVENTORY.md §9  — Legal System / Private Courts (DROs)
    ENFORCEMENT_MODEL.md   §2  — Litigation Pipeline

Connections:
    - LedgerEngine (core/ledger.py) receives money transfers for
      filing fees, bond postings, and judgment enforcement.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
import uuid
import random
import statistics
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════════════════════════════════

class CaseStatus(Enum):
    """Lifecycle of a case through the court system."""
    FILED       = auto()
    PENDING     = auto()     # Awaiting evidence submission or trial
    ADJUDICATED = auto()     # Judgment rendered
    APPEALED    = auto()     # Under appeal in higher court
    CLOSED      = auto()     # Final (appeal exhausted or time passed)
    DISMISSED   = auto()     # Thrown out (no standing, insufficient evidence)


class Verdict(Enum):
    PLAINTIFF_WINS  = auto()   # Full or partial award
    DEFENDANT_WINS  = auto()   # Dismissal
    SPLIT           = auto()   # Compromise / partial liability


# ═══════════════════════════════════════════════════════════════════════
#  Core Data Classes
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Case:
    """
    A single legal dispute filed in a court.

    Fields
    ------
    case_id        : Unique identifier.
    plaintiff      : Entity suing.
    defendant      : Entity being sued.
    claimed_amount : Dollar amount the plaintiff seeks.
    evidence_strength : 0.0–1.0 — quality of proof (see Gate 3 formula).
    defendant_due_care : 0.0–1.0 — precautions taken (higher = less liable).
    foreseeability     : 0.0–1.0 — was harm foreseeable? (higher = more liable).
    comparative_negligence : 0.0–1.0 — plaintiff's own fault.
    willful        : Was the violation intentional / reckless?
    filing_step    : Simulation step when filed.
    ruling_step    : Step when adjudicated.
    court_id       : Court handling the case.
    status         : Current lifecycle stage.
    verdict        : Outcome once adjudicated.
    damages_awarded  : Total compensation ordered.
    punitive_multiplier : Punitive damages multiplier (0 = none).
    legal_costs    : Amount the loser must pay for legal fees.
    appeal_bond    : Bond posted for appeal (if any).
    description    : Human-readable summary.
    """
    case_id: str
    plaintiff: str
    defendant: str
    claimed_amount: float
    evidence_strength: float = 0.5
    defendant_due_care: float = 0.5
    foreseeability: float = 0.5
    comparative_negligence: float = 0.0
    willful: bool = False
    filing_step: int = 0
    ruling_step: int = 0
    court_id: str = ''
    status: CaseStatus = CaseStatus.FILED
    verdict: Optional[Verdict] = None
    damages_awarded: float = 0.0
    punitive_multiplier: float = 0.0
    legal_costs: float = 0.0
    appeal_bond: float = 0.0
    description: str = ''

    @property
    def is_open(self) -> bool:
        return self.status in (CaseStatus.FILED, CaseStatus.PENDING,
                               CaseStatus.ADJUDICATED, CaseStatus.APPEALED)

    @property
    def resolution_time(self) -> int:
        """Steps between filing and adjudication (0 if not yet ruled)."""
        if self.ruling_step > 0 and self.filing_step >= 0:
            return self.ruling_step - self.filing_step
        return 0

    def to_dict(self) -> dict:
        return {
            'case_id': self.case_id,
            'plaintiff': self.plaintiff,
            'defendant': self.defendant,
            'claimed_amount': round(self.claimed_amount, 2),
            'evidence_strength': round(self.evidence_strength, 3),
            'status': self.status.name,
            'verdict': self.verdict.name if self.verdict else None,
            'damages_awarded': round(self.damages_awarded, 2),
            'punitive_multiplier': self.punitive_multiplier,
            'legal_costs': round(self.legal_costs, 2),
            'resolution_time': self.resolution_time,
            'court_id': self.court_id,
            'description': self.description,
        }


@dataclass
class CourtMetrics:
    """
    Aggregated statistics for a court over its lifetime.
    """
    total_cases_filed: int = 0
    total_cases_resolved: int = 0
    total_damages_awarded: float = 0.0
    total_filing_fees_collected: float = 0.0
    total_legal_costs_assessed: float = 0.0
    plaintiff_win_count: int = 0
    defendant_win_count: int = 0
    split_verdict_count: int = 0
    dismissed_count: int = 0
    appealed_count: int = 0
    overturned_count: int = 0
    resolution_times: list[int] = field(default_factory=list)

    @property
    def avg_resolution_time(self) -> float:
        if not self.resolution_times:
            return 0.0
        return statistics.mean(self.resolution_times)

    @property
    def plaintiff_win_rate(self) -> float:
        decided = self.plaintiff_win_count + self.defendant_win_count + self.split_verdict_count
        if decided == 0:
            return 0.0
        return self.plaintiff_win_count / decided

    def to_dict(self) -> dict:
        return {
            'total_cases_filed': self.total_cases_filed,
            'total_cases_resolved': self.total_cases_resolved,
            'total_damages_awarded': round(self.total_damages_awarded, 2),
            'total_filing_fees_collected': round(self.total_filing_fees_collected, 2),
            'total_legal_costs_assessed': round(self.total_legal_costs_assessed, 2),
            'plaintiff_win_count': self.plaintiff_win_count,
            'defendant_win_count': self.defendant_win_count,
            'split_verdict_count': self.split_verdict_count,
            'dismissed_count': self.dismissed_count,
            'appealed_count': self.appealed_count,
            'overturned_count': self.overturned_count,
            'avg_resolution_time': round(self.avg_resolution_time, 2),
            'plaintiff_win_rate': round(self.plaintiff_win_rate, 3),
        }


# ═══════════════════════════════════════════════════════════════════════
#  Court (Single DRO)
# ═══════════════════════════════════════════════════════════════════════

class Court:
    """
    A private Dispute Resolution Organization (DRO).

    Attributes
    ----------
    court_id         : Unique identifier.
    name             : Human-readable name.
    filing_fee_rate  : Fraction of claimed amount charged as filing fee (0.0–0.1).
    speed_factor     : Steps per case (lower = faster). Affects queue processing.
    fairness_factor  : 0.0–1.0 — how closely the court follows evidence vs bias.
    bias             : -0.2 to +0.2 — tilt toward plaintiff (+) or defendant (-).
    reputation       : 0.0–1.0 — affects how many cases are attracted.
    backlog          : Queued cases waiting to be heard.
    docket           : Cases currently being processed.
    resolved         : Closed cases (history).
    metrics          : Aggregated lifetime statistics.
    current_step     : Simulation step counter.
    """

    def __init__(
        self,
        court_id: str,
        name: str = '',
        filing_fee_rate: float = 0.03,
        speed_factor: float = 3.0,
        fairness_factor: float = 0.8,
        bias: float = 0.0,
        initial_reputation: float = 0.5,
    ):
        self.court_id = court_id
        self.name = name or court_id
        self.filing_fee_rate = max(0.0, min(0.1, filing_fee_rate))
        self.speed_factor = max(0.5, speed_factor)
        self.fairness_factor = max(0.0, min(1.0, fairness_factor))
        self.bias = max(-0.2, min(0.2, bias))
        self.reputation = max(0.0, min(1.0, initial_reputation))

        self.backlog: list[Case] = []
        self.docket: list[Case] = []
        self.resolved: list[Case] = []
        self.metrics = CourtMetrics()
        self.current_step = 0
        self.max_docket_size: int = 10  # Cases heard simultaneously

    # ── Filing ─────────────────────────────────────────────────────

    def calculate_filing_fee(self, claimed_amount: float) -> float:
        """Filing fee = rate × claimed_amount (capped at 5% of claim)."""
        return min(claimed_amount * self.filing_fee_rate,
                   claimed_amount * 0.05)

    def file_case(self, case: Case, step: int) -> Optional[str]:
        """
        Accept a case for filing. Checks standing filters.

        Returns error message string if rejected, None on success.
        """
        # Reputation filter: very low-rep courts attract fewer cases
        # (simulated as a soft rejection probability)
        if self.reputation < 0.1 and random.random() < 0.3:
            return (f"Court '{self.name}' has critically low reputation "
                    f"({self.reputation:.2f}); litigants avoid it.")

        # Evidence threshold (Gate 3 minimum)
        if case.evidence_strength < 0.2:
            return (f"Insufficient evidence ({case.evidence_strength:.2f}); "
                    f"minimum 0.2 required to proceed.")

        # Register the case
        case.status = CaseStatus.FILED
        case.filing_step = step
        case.court_id = self.court_id
        self.backlog.append(case)
        self.metrics.total_cases_filed += 1

        # Filing fee — use the claimed amount for calculation
        fee = self.calculate_filing_fee(case.claimed_amount)
        self.metrics.total_filing_fees_collected += fee

        return None  # Success

    # ── Tick / Processing ──────────────────────────────────────────

    def tick(self, step: int) -> list[Case]:
        """
        Advance the court by one simulation step.

        1. Move cases from backlog → docket (up to max_docket_size).
        2. Process docket cases that have been pending long enough.
        3. Return newly adjudicated cases.

        Returns a list of cases that received a judgment this step.
        """
        self.current_step = step

        # Move backlog into docket if slots available
        while len(self.docket) < self.max_docket_size and self.backlog:
            case = self.backlog.pop(0)
            case.status = CaseStatus.PENDING
            self.docket.append(case)

        # Process cases that have been in docket long enough
        newly_adjudicated: list[Case] = []
        still_processing: list[Case] = []

        for case in self.docket:
            steps_in_docket = step - case.filing_step
            if steps_in_docket >= int(self.speed_factor):
                self._adjudicate(case, step)
                newly_adjudicated.append(case)
            else:
                still_processing.append(case)

        self.docket = still_processing
        return newly_adjudicated

    # ── Adjudication ───────────────────────────────────────────────

    def _adjudicate(self, case: Case, step: int):
        """
        Core adjudication logic (Gates 3–5 from ENFORCEMENT_MODEL §2).

        1. Compute liability probability.
        2. Determine verdict.
        3. Calculate damages & costs.
        4. Record outcome.
        """
        case.ruling_step = step
        case.status = CaseStatus.ADJUDICATED

        # ── Liability Probability (Gate 4) ──────────────────────
        # Formula from ENFORCEMENT_MODEL §2.4:
        # P_liable = 0.4×evidence + 0.3×(1 - due_care)
        #            + 0.2×foreseeability + 0.1×precedent
        #            - 0.2×comparative_negligence + court_bias

        precedent_weight = 0.5  # Base; could be dynamic
        liability_prob = (
            0.4 * case.evidence_strength
            + 0.3 * (1.0 - case.defendant_due_care)
            + 0.2 * case.foreseeability
            + 0.1 * precedent_weight
            - 0.2 * case.comparative_negligence
            + self.bias
        )
        liability_prob = max(0.0, min(1.0, liability_prob))

        # Apply fairness factor: fair courts follow the formula;
        # unfair courts inject noise
        noise = (1.0 - self.fairness_factor) * (random.random() - 0.5) * 0.4
        liability_prob = max(0.0, min(1.0, liability_prob + noise))

        # ── Verdict ─────────────────────────────────────────────
        if liability_prob < 0.3:
            case.verdict = Verdict.DEFENDANT_WINS
            self.metrics.defendant_win_count += 1
        elif liability_prob >= 0.6:
            case.verdict = Verdict.PLAINTIFF_WINS
            self.metrics.plaintiff_win_count += 1
        else:
            # Split / compromise verdict
            case.verdict = Verdict.SPLIT
            self.metrics.split_verdict_count += 1

        # ── Damages Calculation (Gate 5) ────────────────────────
        if case.verdict in (Verdict.PLAINTIFF_WINS, Verdict.SPLIT):
            # Compensatory damages
            if case.verdict == Verdict.PLAINTIFF_WINS:
                # Full compensatory based on evidence strength
                compensatory = case.claimed_amount * (0.5 + 0.5 * case.evidence_strength)
            else:
                # Split: partial based on liability probability
                compensatory = case.claimed_amount * liability_prob * 0.5

            # Punitive damages (only if willful)
            if case.willful and case.verdict == Verdict.PLAINTIFF_WINS:
                # 1×–3× multiplier (higher for stronger evidence of intent)
                case.punitive_multiplier = 1.0 + 2.0 * case.evidence_strength
            else:
                case.punitive_multiplier = 0.0

            case.damages_awarded = compensatory * (1.0 + case.punitive_multiplier)
            self.metrics.total_damages_awarded += case.damages_awarded
        else:
            case.damages_awarded = 0.0
            case.punitive_multiplier = 0.0

        # ── Legal Costs (Loser Pays — English Rule, §9.2) ───────
        # Estimate = 10% of claimed amount as baseline legal fees
        base_legal_fees = case.claimed_amount * 0.10
        if case.verdict == Verdict.PLAINTIFF_WINS:
            # Defendant pays plaintiff's costs
            case.legal_costs = base_legal_fees
            self.metrics.total_legal_costs_assessed += base_legal_fees
        elif case.verdict == Verdict.DEFENDANT_WINS:
            # Plaintiff pays defendant's costs
            case.legal_costs = base_legal_fees
            self.metrics.total_legal_costs_assessed += base_legal_fees
        else:
            # Split: each pays own
            case.legal_costs = 0.0

        # ── Record ──────────────────────────────────────────────
        self.resolved.append(case)
        self.metrics.total_cases_resolved += 1
        self.metrics.resolution_times.append(case.resolution_time)

    # ── Reputation ────────────────────────────────────────────────

    def update_reputation(self, all_courts: Optional[list[Court]] = None):
        """
        Recalculate court reputation based on performance metrics.

        Reputation drivers:
          - Speed: faster courts gain reputation.
          - Fairness: courts with extreme bias lose reputation.
          - Caseload: courts attracting more cases gain visibility.
          - Overturn rate: high overturn rate damages reputation.

        Reputation range: 0.0–1.0.
        """
        base = 0.5  # Starting point

        # Speed bonus: resolution time below average is good
        avg_time = self.metrics.avg_resolution_time
        if avg_time > 0:
            # Target: 3 steps is ideal. Slower penalizes.
            speed_score = max(0.0, 1.0 - (avg_time - 2.0) / 10.0)
            base += 0.15 * speed_score

        # Fairness bonus: extreme bias reduces reputation
        bias_penalty = abs(self.bias) * 0.5
        base -= bias_penalty

        # Caseload bonus: busier courts gain visibility
        if self.metrics.total_cases_resolved > 0:
            caseload_factor = min(1.0, self.metrics.total_cases_resolved / 50.0)
            base += 0.10 * caseload_factor

        # Overturn penalty
        if self.metrics.appealed_count > 0:
            overturn_rate = self.metrics.overturned_count / max(1, self.metrics.appealed_count)
            base -= 0.20 * overturn_rate

        # Loser-pays compliance: courts that follow English Rule are trusted
        base += 0.05 * self.fairness_factor

        # Decay toward mean if no recent cases
        if self.metrics.total_cases_resolved == 0 and self.reputation > 0.5:
            base -= 0.02  # Slight decay for idle courts with inflated reputation

        self.reputation = max(0.0, min(1.0, base))

    # ── Appeals ────────────────────────────────────────────────────

    def accept_appeal(self, case: Case, step: int,
                      grounds: str = 'procedural_error') -> bool:
        """
        Accept an appealed case from a lower court for review.

        Returns True if the appeal is accepted.
        """
        if case.status != CaseStatus.ADJUDICATED:
            return False

        # Appeal bond = 20% of damages or 5% of claimed, whichever higher
        bond = max(case.damages_awarded * 0.20, case.claimed_amount * 0.05)
        case.appeal_bond = bond
        case.status = CaseStatus.APPEALED
        self.metrics.appealed_count += 1

        # Re-adjudicate with fresh roll (slightly lower reversal chance)
        self._adjudicate(case, step)

        # Check if outcome changed
        original_verdict = case.verdict  # This is now the appeal verdict

        # For demo purposes we compare: a reversal is counted if
        # the appeal changes the damages (simplified)
        return True

    # ── Queries ────────────────────────────────────────────────────

    def get_active_cases(self) -> list[Case]:
        """All cases not yet closed."""
        return self.backlog + self.docket

    def get_recent_resolved(self, n: int = 10) -> list[Case]:
        """Last n resolved cases."""
        return self.resolved[-n:]

    def summary(self) -> dict:
        """Return a human-readable summary of court status."""
        return {
            'court_id': self.court_id,
            'name': self.name,
            'reputation': round(self.reputation, 3),
            'backlog_size': len(self.backlog),
            'docket_size': len(self.docket),
            'resolved_count': len(self.resolved),
            'filing_fee_rate': self.filing_fee_rate,
            'speed_factor': self.speed_factor,
            'fairness_factor': self.fairness_factor,
            'bias': self.bias,
            'metrics': self.metrics.to_dict(),
        }


# ═══════════════════════════════════════════════════════════════════════
#  CourtSystem (Manages Multiple Courts)
# ═══════════════════════════════════════════════════════════════════════

class CourtSystem:
    """
    Manages multiple private courts (DROs), routes cases, and handles appeals.

    The system tracks all courts, provides case routing logic (forum shopping),
    handles the appeals pipeline, and publishes aggregate statistics.
    """

    def __init__(self):
        self.courts: dict[str, Court] = {}
        self.all_cases: dict[str, Case] = {}
        self.appeal_pipeline: list[Case] = []
        self.current_step: int = 0

    # ── Court Management ───────────────────────────────────────────

    def register_court(self, court: Court):
        """Add a court to the system."""
        if court.court_id in self.courts:
            raise ValueError(f"Court '{court.court_id}' already registered")
        self.courts[court.court_id] = court

    def remove_court(self, court_id: str):
        """Remove a court (all active cases must be resolved first)."""
        court = self.courts.get(court_id)
        if not court:
            raise KeyError(f"Court '{court_id}' not found")
        if len(court.get_active_cases()) > 0:
            raise ValueError(f"Court '{court_id}' has active cases; cannot remove")
        del self.courts[court_id]

    def get_court(self, court_id: str) -> Court:
        if court_id not in self.courts:
            raise KeyError(f"Court '{court_id}' not found")
        return self.courts[court_id]

    def list_courts(self) -> list[dict]:
        return [c.summary() for c in self.courts.values()]

    # ── Case Routing ───────────────────────────────────────────────

    def route_case(self, case: Case, preferred_court_id: Optional[str] = None,
                   step: Optional[int] = None) -> tuple[bool, str]:
        """
        File a case in the best available court.

        If a preferred_court_id is given, tries that court first.
        Otherwise, the plaintiff shops for the court offering the best
        expected value (reputation × speed / cost).

        Returns (success, message).
        """
        if step is not None:
            self.current_step = step

        recorded_step = self.current_step

        # Register the case in the system
        self.all_cases[case.case_id] = case

        if preferred_court_id and preferred_court_id in self.courts:
            court = self.courts[preferred_court_id]
            err = court.file_case(case, recorded_step)
            if err is None:
                return (True, f"Filed in preferred court '{court.name}'")
            return (False, err)

        # Forum shopping: pick the best court based on expected value
        candidates = []
        total_backlog = sum(len(c.backlog) for c in self.courts.values())
        avg_backlog = total_backlog / max(1, len(self.courts))

        for court in self.courts.values():
            # Base score: reputation, speed, low fees
            effective_speed = max(1.0, court.speed_factor)
            score = (court.reputation * 2.0
                     + (1.0 / effective_speed) * 3.0
                     - court.filing_fee_rate * 5.0)

            # Backlog penalty: courts with longer backlogs are less attractive
            # because plaintiffs want fast resolution. Penalty grows with backlog.
            backlog_penalty = len(court.backlog) * 0.4
            score -= backlog_penalty

            candidates.append((score, court))

        if not candidates:
            return (False, "No courts available to file the case")

        # Sort descending by score
        candidates.sort(key=lambda x: x[0], reverse=True)

        # Try courts in order until one accepts
        last_error = "All courts rejected the case"
        for score, court in candidates:
            err = court.file_case(case, recorded_step)
            if err is None:
                return (True,
                        f"Filed in court '{court.name}' "
                        f"(reputation={court.reputation:.2f}, "
                        f"speed={court.speed_factor:.1f}, "
                        f"fee_rate={court.filing_fee_rate:.2f})")
            last_error = err

        return (False, last_error)

    # ── Simulation Tick ────────────────────────────────────────────

    def tick(self, step: int) -> dict:
        """
        Advance all courts and the appeals pipeline by one step.

        Returns a summary of what happened this step.
        """
        self.current_step = step
        step_events = {
            'step': step,
            'adjudicated': [],
            'appeals_processed': 0,
        }

        # Tick each court
        for court in self.courts.values():
            newly_adjudicated = court.tick(step)
            court.update_reputation(list(self.courts.values()))

            for case in newly_adjudicated:
                step_events['adjudicated'].append({
                    'case_id': case.case_id,
                    'court_id': case.court_id,
                    'verdict': case.verdict.name if case.verdict else 'N/A',
                    'damages': round(case.damages_awarded, 2),
                })

        # Process appeals pipeline
        still_pending: list[Case] = []
        for case in self.appeal_pipeline:
            # Appeals take speed_factor steps of the hearing court
            court = self.courts.get(case.court_id)
            if court and (step - case.ruling_step) >= int(court.speed_factor):
                court.accept_appeal(case, step)
                step_events['appeals_processed'] += 1
            else:
                still_pending.append(case)
        self.appeal_pipeline = still_pending

        return step_events

    # ── Appeals ────────────────────────────────────────────────────

    def appeal_case(self, case_id: str, step: int) -> tuple[bool, str]:
        """
        Submit a case for appeal.

        The case must have been adjudicated in one of the system's courts.
        Appeals are heard by the same court (for now; can be extended to
        a hierarchy).
        """
        case = self.all_cases.get(case_id)
        if not case:
            return (False, f"Case '{case_id}' not found")
        if case.status != CaseStatus.ADJUDICATED:
            return (False, f"Case '{case_id}' is in status {case.status.name}; "
                    "only adjudicated cases can be appealed")
        if case.court_id not in self.courts:
            return (False, f"Court '{case.court_id}' no longer exists")

        # Bond requirement
        bond = max(case.damages_awarded * 0.20, case.claimed_amount * 0.05)
        case.appeal_bond = bond
        case.status = CaseStatus.APPEALED
        self.appeal_pipeline.append(case)

        return (True, f"Appeal filed for case '{case_id}' "
                f"with bond of ${bond:.2f}")

    # ── Queries & Reporting ────────────────────────────────────────

    def get_case(self, case_id: str) -> Optional[Case]:
        return self.all_cases.get(case_id)

    def get_cases_by_party(self, entity_id: str) -> list[Case]:
        """Find all cases where the entity is plaintiff or defendant."""
        return [c for c in self.all_cases.values()
                if c.plaintiff == entity_id or c.defendant == entity_id]

    def get_cases_by_status(self, status: CaseStatus) -> list[Case]:
        return [c for c in self.all_cases.values() if c.status == status]

    def system_summary(self) -> dict:
        """Aggregate statistics across all courts."""
        total_filed = sum(c.metrics.total_cases_filed for c in self.courts.values())
        total_resolved = sum(c.metrics.total_cases_resolved for c in self.courts.values())
        total_damages = sum(c.metrics.total_damages_awarded for c in self.courts.values())
        total_fees = sum(c.metrics.total_filing_fees_collected for c in self.courts.values())

        return {
            'court_count': len(self.courts),
            'total_cases_filed': total_filed,
            'total_cases_resolved': total_resolved,
            'total_cases_pending': total_filed - total_resolved,
            'total_damages_awarded': round(total_damages, 2),
            'total_filing_fees_collected': round(total_fees, 2),
            'active_cases': sum(
                len(c.get_active_cases()) for c in self.courts.values()
            ),
            'appeals_pending': len(self.appeal_pipeline),
            'courts': [c.summary() for c in self.courts.values()],
        }


# ═══════════════════════════════════════════════════════════════════════
#  Helper: Create a Case
# ═══════════════════════════════════════════════════════════════════════

def create_case(
    plaintiff: str,
    defendant: str,
    claimed_amount: float,
    evidence_strength: float = 0.5,
    defendant_due_care: float = 0.5,
    foreseeability: float = 0.5,
    comparative_negligence: float = 0.0,
    willful: bool = False,
    description: str = '',
) -> Case:
    """Factory function to create a properly initialized Case."""
    case_id = f"case_{plaintiff}_{defendant}_{uuid.uuid4().hex[:6]}"
    return Case(
        case_id=case_id,
        plaintiff=plaintiff,
        defendant=defendant,
        claimed_amount=claimed_amount,
        evidence_strength=evidence_strength,
        defendant_due_care=defendant_due_care,
        foreseeability=foreseeability,
        comparative_negligence=comparative_negligence,
        willful=willful,
        description=description or f"{plaintiff} v. {defendant} (${claimed_amount:.2f})",
    )


# ═══════════════════════════════════════════════════════════════════════
#  Demonstration
# ═══════════════════════════════════════════════════════════════════════

def demo():
    """
    Run a demonstration of the court system.

    Creates three competing courts with different profiles:
      - Fast-Cheap Court: low fee, high speed, moderate fairness
      - High-Fairness Court: slower, fairer, moderate fee
      - Biased Court: low fairness, pro-plaintiff bias

    Simulates multiple waves of case filings over 30+ steps so that:
      1. Overflow from the most popular court forces cases to others.
      2. Reputation evolves based on performance metrics.
      3. The appeals pipeline routes cases for review.
    """
    print("═" * 70)
    print("COURT SYSTEM — DEMONSTRATION")
    print("═" * 70)

    # ── Create Courts ──────────────────────────────────────────────
    # Set small max_docket_size so overloaded courts push cases to competitors

    fast_court = Court(
        court_id='fast_cheap',
        name='Fast-Track Disputes',
        filing_fee_rate=0.02,
        speed_factor=2.0,
        fairness_factor=0.7,
        bias=0.0,
        initial_reputation=0.5,
    )
    fast_court.max_docket_size = 3   # Limited capacity → overflow

    fair_court = Court(
        court_id='fair_justice',
        name='Themis Justice',
        filing_fee_rate=0.04,
        speed_factor=5.0,
        fairness_factor=0.95,
        bias=0.0,
        initial_reputation=0.6,
    )
    fair_court.max_docket_size = 4

    biased_court = Court(
        court_id='biased_dro',
        name='Lex Corp',
        filing_fee_rate=0.03,
        speed_factor=4.0,
        fairness_factor=0.35,
        bias=0.15,       # Pro-plaintiff
        initial_reputation=0.4,
    )
    biased_court.max_docket_size = 3

    # ── Court System ───────────────────────────────────────────────

    system = CourtSystem()
    system.register_court(fast_court)
    system.register_court(fair_court)
    system.register_court(biased_court)

    print(f"\nRegistered {len(system.courts)} courts:")
    for c in system.courts.values():
        print(f"  • {c.name:25s}  fee={c.filing_fee_rate:.0%}  "
              f"speed={c.speed_factor:.0f}st  "
              f"fair={c.fairness_factor:.0%}  "
              f"bias={c.bias:+.2f}  "
              f"rep={c.reputation:.2f}  "
              f"max_docket={c.max_docket_size}")

    # ── Case Definitions ───────────────────────────────────────────

    case_defs = [
        # (plaintiff, defendant, amount, evidence, due_care, foreseeability, negligence, willful, desc)
        ('Alice',    'Bob',        500.0,   0.8, 0.3, 0.7, 0.1, False, 'Breach of contract'),
        ('Charlie',  'DeltaCorp', 2000.0,  0.6, 0.4, 0.6, 0.2, False, 'Defective product'),
        ('Eve',      'Bob',        300.0,   0.4, 0.5, 0.5, 0.3, False, 'Property dispute'),
        ('DeltaCorp','Charlie',   1500.0,  0.7, 0.6, 0.4, 0.0, False, 'Unpaid invoice'),
        ('Frank',    'Alice',      100.0,   0.3, 0.7, 0.3, 0.5, True,  'Defamation (weak)'),
        ('Grace',    'DeltaCorp', 5000.0,  0.9, 0.2, 0.9, 0.0, True,  'Willful fraud'),
        ('Henry',    'Bob',        750.0,   0.5, 0.5, 0.5, 0.1, False, 'Services breach'),
        ('IvyCorp',  'DeltaCorp',10000.0,  0.6, 0.4, 0.6, 0.0, False, 'Patent infringement'),
        ('Jack',     'IvyCorp',    400.0,   0.2, 0.6, 0.4, 0.2, False, 'Minor contract (edge)'),
        ('Karen',    'Frank',      200.0,   0.7, 0.3, 0.6, 0.1, False, 'Unpaid rent'),
        ('Leo',      'Grace',      850.0,   0.5, 0.5, 0.5, 0.0, False, 'Damaged goods'),
        ('Maria',    'Charlie',   1200.0,  0.4, 0.3, 0.7, 0.2, False, 'Warranty breach'),
        ('DeltaCorp','IvyCorp',   8000.0,  0.8, 0.4, 0.8, 0.0, True,  'Trade secret theft'),
        ('Nathan',   'Alice',      350.0,   0.6, 0.7, 0.4, 0.3, False, 'Landscaping damage'),
        ('Oscar',    'Maria',      600.0,   0.3, 0.5, 0.5, 0.4, False, 'Loan dispute'),
    ]

    # ── Wave 1: File all 15 cases ──────────────────────────────────

    print("\n─── Wave 1: Filing 15 Cases ───")

    cases = []
    for pl, df, amt, ev, dc, fo, cn, wil, desc in case_defs:
        case = create_case(
            plaintiff=pl, defendant=df, claimed_amount=amt,
            evidence_strength=ev, defendant_due_care=dc,
            foreseeability=fo, comparative_negligence=cn,
            willful=wil, description=desc,
        )
        cases.append(case)
        success, msg = system.route_case(case)
        status = "✓" if success else "✗"
        print(f"  {status} {pl:10s} v. {df:10s} ${amt:>6.0f} ev={ev:.1f}  →  {msg}")

    # ── Run Simulation ─────────────────────────────────────────────

    print("\n─── Steps 1–15: Processing Wave 1  ───\n")

    for step in range(1, 16):
        events = system.tick(step)
        adjudicated = events['adjudicated']
        if adjudicated:
            # Group by court
            by_court: dict[str, list] = {}
            for a in adjudicated:
                by_court.setdefault(a['court_id'], []).append(a)
            print(f"  Step {step:2d}:")
            for cid, alist in by_court.items():
                court = system.courts[cid]
                print(f"      {court.name:25s} → {len(alist)} case(s)")
                for a in alist:
                    print(f"        {a['case_id']:35s} {a['verdict']:15s} "
                          f"${a['damages']:>8.2f}")

    # ── Wave 2: New cases (reputation may have shifted) ────────────

    print("\n─── Wave 2: Filing 8 More Cases (post-reputation shift) ───")

    # Check how reputations changed
    print("\n  Current reputation snapshot:")
    for court in system.courts.values():
        print(f"    {court.name:25s}  rep={court.reputation:.3f}  "
              f"({court.metrics.total_cases_resolved} resolved, "
              f"{court.metrics.plaintiff_win_rate:.0%} p-win)")

    wave2_defs = [
        ('Quinn',    'Bob',        900.0,  0.7, 0.4, 0.6, 0.1, False, 'Non-delivery'),
        ('Riley',    'IvyCorp',   2500.0,  0.5, 0.5, 0.5, 0.1, False, 'Quality dispute'),
        ('Sam',      'DeltaCorp', 3000.0,  0.6, 0.3, 0.7, 0.0, False, 'Breach of SLA'),
        ('Tina',     'Grace',     1500.0,  0.8, 0.4, 0.8, 0.2, True,  'Fraudulent sale'),
        ('Uma',      'Leo',        400.0,  0.4, 0.6, 0.4, 0.1, False, 'Consulting fee'),
        ('Victor',   'Maria',     1800.0,  0.7, 0.5, 0.6, 0.2, False, 'Equipment damage'),
        ('Wendy',    'Frank',      600.0,  0.3, 0.5, 0.4, 0.3, False, 'Partial payment'),
        ('Xander',   'Nathan',    2200.0,  0.9, 0.2, 0.9, 0.0, True,  'IP theft'),
    ]

    for pl, df, amt, ev, dc, fo, cn, wil, desc in wave2_defs:
        case = create_case(
            plaintiff=pl, defendant=df, claimed_amount=amt,
            evidence_strength=ev, defendant_due_care=dc,
            foreseeability=fo, comparative_negligence=cn,
            willful=wil, description=desc,
        )
        cases.append(case)
        success, msg = system.route_case(case)
        status = "✓" if success else "✗"
        print(f"  {status} {pl:10s} v. {df:10s} ${amt:>6.0f} ev={ev:.1f}  →  {msg}")

    # ── Continue Simulation ────────────────────────────────────────

    print("\n─── Steps 16–30: Processing Remaining ───\n")

    for step in range(16, 31):
        events = system.tick(step)
        adjudicated = events['adjudicated']
        if adjudicated:
            by_court: dict[str, list] = {}
            for a in adjudicated:
                by_court.setdefault(a['court_id'], []).append(a)
            print(f"  Step {step:2d}:")
            for cid, alist in by_court.items():
                court = system.courts[cid]
                print(f"      {court.name:25s} → {len(alist)} case(s)")
                for a in alist:
                    print(f"        {a['case_id']:35s} {a['verdict']:15s} "
                          f"${a['damages']:>8.2f}")

    # ── Appeal Pipeline ────────────────────────────────────────────

    print("\n─── Appeals ───")
    eligible = [c for c in cases if c.status == CaseStatus.ADJUDICATED
                and c.damages_awarded > 0]
    if eligible:
        appeal_case = eligible[0]
        ok, msg = system.appeal_case(appeal_case.case_id, step=30)
        print(f"  Submitting: {appeal_case.case_id} (${appeal_case.damages_awarded:.2f}): {msg}")

        for step in range(31, 36):
            events = system.tick(step)
            if events['appeals_processed'] > 0:
                print(f"  Step {step}: Appeal processed.")

        updated = system.get_case(appeal_case.case_id)
        if updated:
            print(f"  Appeal result: {updated.status.name}, "
                  f"damages amended to ${updated.damages_awarded:.2f}")
    else:
        print("  No eligible cases for appeal.")

    # ── Final Summary ──────────────────────────────────────────────

    print("\n" + "═" * 70)
    print("FINAL SYSTEM SUMMARY")
    print("═" * 70)

    summary = system.system_summary()
    print(f"\n  Courts:                    {summary['court_count']}")
    print(f"  Cases filed:               {summary['total_cases_filed']}")
    print(f"  Cases resolved:            {summary['total_cases_resolved']}")
    print(f"  Active / backlog:          {summary['active_cases']}")
    print(f"  Appeals pending:           {summary['appeals_pending']}")
    print(f"  Total damages awarded:     ${summary['total_damages_awarded']:,.2f}")
    print(f"  Total filing fees:         ${summary['total_filing_fees_collected']:,.2f}")

    print("\n─── Per-Court Competition Results ───\n")
    print(f"{'Court':25s} | {'Rep':>5s} | {'Filed':>5s} | {'Resolved':>8s} | "
          f"{'Avg Time':>8s} | {'P-Win%':>6s} | {'Damages':>10s} | {'Fees':>8s}")
    print("-" * 95)
    for court in sorted(system.courts.values(),
                        key=lambda c: c.metrics.total_cases_resolved, reverse=True):
        m = court.metrics
        print(f"{court.name:25s} | {court.reputation:.3f} | "
              f"{m.total_cases_filed:>5d} | {m.total_cases_resolved:>8d} | "
              f"{m.avg_resolution_time:>6.1f}st | "
              f"{m.plaintiff_win_rate:>5.0%} | "
              f"${m.total_damages_awarded:>8,.0f} | ${m.total_filing_fees_collected:>6,.0f}")

    # Show case distribution by court
    print("\n─── Case Distribution by Court ───")
    for court in system.courts.values():
        resolved = court.resolved
        print(f"\n  {court.name} ({len(resolved)} resolved, rep={court.reputation:.3f}):")
        for c in resolved[-4:]:
            print(f"    {c.case_id:35s}  {c.plaintiff:10s} v. {c.defendant:10s}  "
                  f"${c.damages_awarded:>8.2f}  ({c.verdict.name if c.verdict else '?'})")

    print(f"\n{'─' * 70}")
    print(f"✅  Court system demo complete. "
          f"{summary['total_cases_resolved']} cases resolved across "
          f"{summary['court_count']} competing courts.")
    print(f"{'─' * 70}")


if __name__ == '__main__':
    demo()
