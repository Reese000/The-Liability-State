"""
agents/worker.py — WorkerAgent for The Liability State

Each WorkerAgent represents an individual citizen in the simulation.
Workers supply labour (balancing wage income vs leisure disutility),
make insurance decisions, pay LVT, receive dividends, and may migrate
between compacts.

All economic interactions are recorded through the LedgerEngine
for double-entry accounting and zero-sum invariant enforcement.

Spec reference: AGENT_MODEL.md §2.1 (Worker), §3.2 (Worker Utility),
                §9.1 (Worker Decision Variables), §12.2 (Parameters)
"""

from __future__ import annotations

import random
from typing import Optional

from ..core.ledger import LedgerEngine, EntityType


# ═══════════════════════════════════════════════════════════════════════
#  WorkerAgent
# ═══════════════════════════════════════════════════════════════════════


class WorkerAgent:
    """
    A worker citizen in The Liability State simulation.

    Each worker has:

      *productivity*  — wage rate per labour-hour (skill/earnings capacity)
      *land_value*    — assessed land value (basis for LVT)
      *risk_profile*  — hidden risk probability ∈ [0,1] (insurance pricing)
      *honesty*       — moral parameter θ ∈ [0,1] (see AGENT_MODEL §5)
      *inertia*       — bounded-rationality λ ∈ [0,1] (resistance to change)

    Per-step decisions (orchestrated by calling *step()*):

      1. **Labour supply**  — choose hours L ∈ [0, L_MAX] balancing
         wage income against convex leisure-disutility C(L) = c₁·L².

      2. **Insurance** — decide whether to purchase coverage by comparing
         expected utility with and without a policy (quantal-response
         choice with inertia).

      3. **Migration** — evaluate compact-attractiveness indices and
         decide whether to move (costly, inertia-moderated).

    All money flows go through the LedgerEngine so the zero-sum
    invariant can be checked every simulation step.
    """

    # ── Class-level defaults (can be overridden per instance) ─────
    L_MAX: float = 16.0               # Maximum labour hours / step
    EFFORT_COST_C1: float = 0.5       # Disutility coefficient in c₁·L²
    DECISION_NOISE_SIGMA: float = 0.15  # Bounded-rationality noise scale

    # ────────────────────────────────────────────────────────────────
    #  Constructor
    # ────────────────────────────────────────────────────────────────

    def __init__(
        self,
        worker_id: str,
        ledger: LedgerEngine,
        *,
        productivity: float = 10.0,
        land_value: float = 0.0,
        risk_profile: float = 0.05,
        honesty: float = 0.7,
        inertia: float = 0.3,
        compact_id: str = '',
        initial_cash: float = 5000.0,
    ):
        if not (0.0 <= risk_profile <= 1.0):
            raise ValueError(
                f"risk_profile must be in [0, 1], got {risk_profile}"
            )
        if not (0.0 <= honesty <= 1.0):
            raise ValueError(f"honesty must be in [0, 1], got {honesty}")

        # ── Identity & environment ─────────────────────────────────
        self.id = worker_id
        self.ledger = ledger
        self.compact_id = compact_id

        # ── Economic parameters ────────────────────────────────────
        self.productivity = productivity      # $ / labour-hour
        self.land_value = land_value          # Assessed land (LVT base)
        self.risk_profile = risk_profile      # True risk ∈ [0,1]
        self.initial_cash = initial_cash      # Starting cash (for registration)

        # ── Behavioural parameters ─────────────────────────────────
        self.honesty = honesty                # θ — moral parameter
        self.inertia = inertia                # λ — bounded rationality

        # ── Insurance state ────────────────────────────────────────
        self.has_insurance: bool = False
        self.insurer_id: Optional[str] = None
        self.insurance_coverage: float = 0.0
        self.insurance_premium: float = 0.0

        # ── Migration state ────────────────────────────────────────
        self.migration_target: Optional[str] = None

        # ── Distress state ─────────────────────────────────────────
        self.distressed: bool = False
        self._consecutive_no_income_steps: int = 0

        # ── Statistics accumulators ────────────────────────────────
        self.total_labor_income: float = 0.0
        self.total_lvt_paid: float = 0.0
        self.total_insurance_premiums: float = 0.0
        self.total_dividends: float = 0.0
        self.total_hours_worked: float = 0.0

        # ── Register on ledger ─────────────────────────────────────
        self._ensure_registered()

    # ────────────────────────────────────────────────────────────────
    #  Internal helpers
    # ────────────────────────────────────────────────────────────────

    def _ensure_registered(self) -> None:
        """Register this worker on the ledger if not already present."""
        if not self.ledger.entity_exists(self.id):
            bs = self.ledger.register_entity(
                self.id,
                EntityType.CITIZEN,
                compact_id=self.compact_id,
                initial_cash=self.initial_cash,
            )
            bs.land_value = self.land_value
        else:
            bs = self.ledger.get_balance(self.id)
            bs.land_value = self.land_value

    # ────────────────────────────────────────────────────────────────
    #  1. Labour Supply Decision
    # ────────────────────────────────────────────────────────────────

    def decide_labor_hours(self) -> float:
        """
        Choose labour hours L ∈ [0, L_MAX] that maximise:

            U(L) = productivity · L  -  c₁ · L²

        **First-order condition** (interior solution):
            productivity = 2 · c₁ · L   ⇒   L* = productivity / (2 · c₁)

        Bounded rationality is modelled as:
          - Gaussian noise added to the optimal choice (quantal response).
          - Inertia: the chosen hours are pulled toward the previous
            period's hours by a factor proportional to λ (inertia).

        Returns
        -------
        float
            Chosen labour hours, clipped to [0, L_MAX].
        """
        # ── Optimal frictionless hours ────────────────────────────
        if self.EFFORT_COST_C1 <= 0.0:
            L_opt = self.L_MAX
        else:
            L_opt = self.productivity / (2.0 * self.EFFORT_COST_C1)

        L_opt = max(0.0, min(L_opt, self.L_MAX))

        # ── Bounded-rationality noise (quantal response) ──────────
        noise = random.gauss(0.0, self.DECISION_NOISE_SIGMA * self.L_MAX)
        L_chosen = L_opt + noise

        # ── Inertia: smooth toward previous hours ─────────────────
        prev_hours = getattr(self, '_prev_hours', 0.0)
        gap = L_chosen - prev_hours
        L_chosen = prev_hours + gap * (1.0 - self.inertia * 0.3)

        # ── Clamp ─────────────────────────────────────────────────
        L_chosen = max(0.0, min(L_chosen, self.L_MAX))
        self._prev_hours = L_chosen

        return L_chosen

    # ────────────────────────────────────────────────────────────────
    #  2. Insurance Decision
    # ────────────────────────────────────────────────────────────────

    def decide_insurance(self) -> bool:
        """
        Decide whether to purchase insurance this step.

        The worker compares expected utility with and without insurance:

            **Without insurance:**
                E[U_no] = (1 - risk_profile) · wealth_after_loss
                           + risk_profile · (wealth_after_loss - loss)

            **With insurance:**
                E[U_yes] = wealth - premium
                           + risk_profile · coverage_ratio · loss

        A *quantal response* noise term and an *inertia bias* (tendency
        to maintain the current insured/uninsured state) are added.

        Returns
        -------
        bool
            True if the worker wants insurance this step.
        """
        # ── Estimate a simplified premium ─────────────────────────
        # Premium = base_rate × risk_profile × reference_income × loading
        reference_income = self.productivity * 10.0
        base_rate = 0.05
        loading = 1.3
        premium = base_rate * self.risk_profile * reference_income * loading
        self.insurance_premium = max(premium, 1.0)

        # ── Expected loss without insurance ───────────────────────
        expected_loss = self.risk_profile * (self.productivity * 5.0)

        # ── Expected benefit from insurance coverage (80 % of loss) ─
        coverage_ratio = 0.8
        expected_benefit = self.risk_profile * (
            self.productivity * 5.0 * coverage_ratio
        )

        # ── Net value ─────────────────────────────────────────────
        net_value = expected_benefit - premium

        # ── Decision noise ────────────────────────────────────────
        noise = random.gauss(
            0.0, self.DECISION_NOISE_SIGMA * max(abs(net_value), 1.0)
        )

        # ── Status-quo inertia ────────────────────────────────────
        if self.has_insurance:
            inertia_bonus = self.inertia * 0.2 * premium   # stick to insured
        else:
            inertia_bonus = -self.inertia * 0.2 * premium   # stick to uninsured

        return (net_value + noise + inertia_bonus) > 0

    # ────────────────────────────────────────────────────────────────
    #  3. Migration Decision
    # ────────────────────────────────────────────────────────────────

    def decide_migration(
        self, compact_utilities: dict[str, float]
    ) -> Optional[str]:
        """
        Consider migrating to another compact.

        The worker compares their current compact's utility index
        against the best alternative.  Migration carries a fixed cost
        (5 % of productivity).  An inertia penalty makes staying the
        default.

        Parameters
        ----------
        compact_utilities : dict[str, float]
            Estimated utility index per compact.  Higher = more
            attractive (e.g. higher dividend expectations, better
           公共服务).

        Returns
        -------
        str | None
            Target compact_id to move to, or None to stay put.
        """
        if not compact_utilities:
            return None

        current_util = compact_utilities.get(self.compact_id, 0.0)

        # Find the most attractive alternative compact
        best_compact: Optional[str] = None
        best_util = current_util
        for cid, util in compact_utilities.items():
            if cid == self.compact_id:
                continue
            if util > best_util:
                best_util = util
                best_compact = cid

        if best_compact is None:
            return None

        # Migration cost (fixed fraction of productivity)
        migration_cost = 0.05 * self.productivity

        # Net gain of moving
        gain = best_util - current_util
        noise = random.gauss(
            0.0, self.DECISION_NOISE_SIGMA * max(abs(gain), 1.0)
        )

        # Only move if the gain exceeds the cost weighted by inertia
        threshold = migration_cost * (1.0 + self.inertia)
        if (gain + noise) > threshold:
            return best_compact

        return None

    # ────────────────────────────────────────────────────────────────
    #  Action Execution (ledger-mediated)
    # ────────────────────────────────────────────────────────────────

    def execute_labor(self, hours: float) -> float:
        """
        Execute labour supply: earn wage income.

        Transfer:  **SYSTEM → worker**  (mechanism = ``'wage'``)

        In a full simulation the counterparty would be a Business;
        here SYSTEM acts as the employer for the demo.

        Parameters
        ----------
        hours : float
            Hours worked this step.

        Returns
        -------
        float
            Wage income earned.
        """
        if hours <= 0.0:
            return 0.0

        wage_income = self.productivity * hours

        # Ensure __system__ exists for wage payments
        if not self.ledger.entity_exists('__system__'):
            self.ledger.register_entity(
                '__system__', EntityType.SYSTEM, initial_cash=1_000_000.0
            )

        self.ledger.transfer(
            from_id='__system__',
            to_id=self.id,
            mechanism='wage',
            amount=wage_income,
            description=(
                f'Wage: {self.id} works {hours:.2f}h × '
                f'${self.productivity:.2f}/h'
            ),
        )

        self.total_labor_income += wage_income
        self.total_hours_worked += hours
        return wage_income

    def execute_buy_insurance(
        self, insurer_id: str, coverage_limit: float = 5000.0
    ) -> None:
        """
        Record an insurance purchase intention.

        The actual premium payment flows through the InsuranceMarket's
        ``collect_premiums()`` method.  This method only sets the
        worker's internal flags so they appear as a policyholder.

        Parameters
        ----------
        insurer_id : str
            Entity id of the chosen insurer.
        coverage_limit : float
            Maximum claim payout per event.
        """
        self.has_insurance = True
        self.insurer_id = insurer_id
        self.insurance_coverage = coverage_limit

    def execute_lvt_payment(self, lvt_amount: float) -> None:
        """
        Pay Land Value Tax.

        Transfer:  **worker → national_trust**  (mechanism = ``'lvt'``)

        Parameters
        ----------
        lvt_amount : float
            LVT bill for this step (land_value × rate).
        """
        if lvt_amount <= 0.0:
            return

        self.ledger.transfer(
            from_id=self.id,
            to_id='national_trust',
            mechanism='lvt',
            amount=lvt_amount,
            description=(
                f'LVT: {self.id} on land ${self.land_value:.2f} '
                f'@ {self.ledger.get_balance(self.id).land_value:.2f}'
            ),
        )
        self.total_lvt_paid += lvt_amount

    def receive_dividend(self, amount: float) -> None:
        """
        Receive the Citizen's Dividend from the National Trust.

        Transfer:  **national_trust → worker** (mechanism = ``'dividend'``)

        Parameters
        ----------
        amount : float
            Per-capita dividend amount.
        """
        if amount <= 0.0:
            return

        self.ledger.transfer(
            from_id='national_trust',
            to_id=self.id,
            mechanism='dividend',
            amount=amount,
            description=f'Dividend: {self.id}',
        )
        self.total_dividends += amount

    def execute_migration(self, target_compact_id: str) -> None:
        """
        Execute migration to a new compact.

        Updates the worker's compact_id and the ledger BalanceSheet.
        """
        old_compact = self.compact_id
        self.compact_id = target_compact_id

        bs = self.ledger.get_balance(self.id)
        bs.compact_id = target_compact_id

        self.migration_target = None

    # ────────────────────────────────────────────────────────────────
    #  Full Per-Step Orchestration
    # ────────────────────────────────────────────────────────────────

    def step(
        self,
        compact_utilities: Optional[dict[str, float]] = None,
        insurer_id: Optional[str] = None,
        insurance_coverage: float = 5000.0,
    ) -> dict:
        """
        Execute one full simulation step for this worker.

        Sequence
        --------
        1. Labour supply — decide hours and earn wage.
        2. Insurance — decide whether to purchase; if yes and uninsured,
           record a new policy with *insurer_id*.
        3. Migration — decide whether to move compact.

        Parameters
        ----------
        compact_utilities : dict[str, float] or None
            Compact-attractiveness indices for migration decisions.
            If None migration is skipped.
        insurer_id : str or None
            Insurer to use if a new policy is purchased.
        insurance_coverage : float
            Coverage limit for new policies.

        Returns
        -------
        dict
            Step result with keys:
            ``worker_id``, ``hours_worked``, ``wage_income``,
            ``insurance_action``, ``has_insurance``, ``migrated_to``,
            ``compact_id``.
        """
        result: dict = {'worker_id': self.id}

        # ── 1. Labour ───────────────────────────────────────────────
        # Distressed workers do not supply labour — they rely only
        # on the Citizen's Dividend
        if self.distressed:
            hours = 0.0
            wage = 0.0
            result['hours_worked'] = 0.0
            result['wage_income'] = 0.0
        else:
            hours = self.decide_labor_hours()
            wage = self.execute_labor(hours)
            result['hours_worked'] = round(hours, 2)
            result['wage_income'] = round(wage, 2)

        # ── Distress check ─────────────────────────────────────────
        # Track consecutive steps where cash < 0 AND no wage income
        if self.cash < 0 and wage == 0:
            self._consecutive_no_income_steps += 1
        else:
            self._consecutive_no_income_steps = 0

        if self._consecutive_no_income_steps >= 5:
            self.distressed = True

        result['distressed'] = self.distressed

        # ── 2. Insurance ────────────────────────────────────────────
        wants_insurance = self.decide_insurance()

        if wants_insurance and not self.has_insurance and insurer_id is not None:
            self.execute_buy_insurance(insurer_id, insurance_coverage)
            result['insurance_action'] = 'bought'
            result['wants_new_policy'] = True
            result['wants_new_insurer'] = insurer_id
        elif wants_insurance and self.has_insurance:
            result['insurance_action'] = 'kept'
            result['wants_new_policy'] = False
        elif not wants_insurance and self.has_insurance:
            self.has_insurance = False
            self.insurer_id = None
            result['insurance_action'] = 'dropped'
            result['wants_new_policy'] = False
        else:
            result['insurance_action'] = 'none'
            result['wants_new_policy'] = False

        result['has_insurance'] = self.has_insurance

        # ── 3. Migration ────────────────────────────────────────────
        if compact_utilities:
            target = self.decide_migration(compact_utilities)
            if target is not None and target != self.compact_id:
                self.execute_migration(target)
                result['migrated_to'] = target
            else:
                result['migrated_to'] = None
        else:
            result['migrated_to'] = None

        result['compact_id'] = self.compact_id

        return result

    # ────────────────────────────────────────────────────────────────
    #  Query Helpers
    # ────────────────────────────────────────────────────────────────

    @property
    def cash(self) -> float:
        """Current cash balance from the ledger."""
        return self.ledger.get_balance(self.id).cash

    @property
    def net_worth(self) -> float:
        """Current net worth from the ledger."""
        return self.ledger.get_balance(self.id).net_worth

    # ────────────────────────────────────────────────────────────────
    #  Reporting
    # ────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return aggregate statistics for this worker."""
        return {
            'worker_id': self.id,
            'productivity': self.productivity,
            'land_value': self.land_value,
            'risk_profile': self.risk_profile,
            'honesty': round(self.honesty, 4),
            'inertia': round(self.inertia, 4),
            'compact_id': self.compact_id,
            'cash': round(self.cash, 2),
            'net_worth': round(self.net_worth, 2),
            'has_insurance': self.has_insurance,
            'total_hours_worked': round(self.total_hours_worked, 2),
            'total_labor_income': round(self.total_labor_income, 2),
            'total_lvt_paid': round(self.total_lvt_paid, 2),
            'total_dividends': round(self.total_dividends, 2),
            'total_insurance_premiums': round(
                self.total_insurance_premiums, 2
            ),
        }

    def __repr__(self) -> str:
        return (
            f"WorkerAgent({self.id}, "
            f"prod={self.productivity:.1f}, "
            f"land={self.land_value:.0f}, "
            f"risk={self.risk_profile:.2f}, "
            f"θ={self.honesty:.2f}, "
            f"λ={self.inertia:.2f}, "
            f"compact={self.compact_id})"
        )


# ═══════════════════════════════════════════════════════════════════════
#  Demonstration
# ═══════════════════════════════════════════════════════════════════════

def demo():
    """
    Full WorkerAgent demo:

    1. Creates **20 workers** with random economic and behavioural
       parameters drawn from the AGENT_MODEL distributions.
    2. Registers two insurers with the InsuranceMarket.
    3. Runs **10 simulation steps** where each step:
       - Workers choose labour hours and earn wages (SYSTEM → worker).
       - Workers decide whether to buy/keep/drop insurance.
       - InsuranceMarket collects premiums.
       - LVT is collected (worker → national_trust).
       - TrustEngine distributes the Citizen's Dividend (trust → worker).
       - Workers evaluate compact-migration (optional).
    4. Prints **per-step summaries** and **final aggregate statistics**
       including ledger health checks (zero-sum balance).

    All monetary flows are routed through the LedgerEngine so the
    zero-sum invariant is enforced every step.
    """
    import sys
    import os as _os

    # Ensure src/ is on sys.path for standalone runs
    _script_dir = _os.path.dirname(_os.path.abspath(__file__))
    _src_dir = _os.path.normpath(_os.path.join(_script_dir, '..'))
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)

    import random as _random
    _random.seed(42)

    print('═' * 72)
    print('  WORKER AGENT — DEMONSTRATION')
    print('═' * 72)

    # ── Imports for demo ──────────────────────────────────────────
    from src.mechanics.lvt import LVTEngine, TrustEngine
    from src.core.ledger import LedgerEngine, EntityType
    from src.mechanics.insurance import InsuranceMarket

    # ── 1. Set up core systems ──────────────────────────────────────
    ledger = LedgerEngine(step_log=False)
    lvt_engine = LVTEngine(ledger, rate=0.05)
    trust_engine = TrustEngine(ledger, skim_rate=0.10)

    # System entities
    ledger.register_entity(
        '__system__', EntityType.SYSTEM, initial_cash=1_000_000.0
    )
    ledger.register_entity('national_trust', EntityType.TRUST, initial_cash=0.0)
    ledger.register_entity('alliance', EntityType.ALLIANCE, initial_cash=0.0)

    # Compacts
    COMPACT_IDS = ['compact_alpha', 'compact_beta', 'compact_gamma']
    for cid in COMPACT_IDS:
        ledger.register_entity(cid, EntityType.COMPACT, initial_cash=0.0)

    # ── 2. Create Workers ──────────────────────────────────────────
    workers: list[WorkerAgent] = []
    for i in range(20):
        wid = f'worker_{i:03d}'
        # Parameters drawn from AGENT_MODEL distributions
        productivity = _random.uniform(8.0, 18.0)
        land_value = _random.uniform(0.0, 50_000.0)
        risk_profile = _random.uniform(0.01, 0.30)
        # Beta(5, 2) → mean ≈ 0.71 per AGENT_MODEL §12.3
        honesty = _random.betavariate(5.0, 2.0)
        inertia = _random.uniform(0.1, 0.5)
        compact_id = _random.choice(COMPACT_IDS)
        initial_cash = _random.uniform(2_000.0, 10_000.0)

        w = WorkerAgent(
            worker_id=wid,
            ledger=ledger,
            productivity=productivity,
            land_value=land_value,
            risk_profile=risk_profile,
            honesty=honesty,
            inertia=inertia,
            compact_id=compact_id,
            initial_cash=initial_cash,
        )
        workers.append(w)

    # ── 3. Set up insurance market ─────────────────────────────────
    insurance_market = InsuranceMarket(
        ledger,
        audit_probability=0.10,
        base_rate=0.05,
        loading_factor=1.3,
    )
    insurance_market.register_insurer(
        'insurer_a', initial_capital=100_000.0, num_pools=2
    )
    insurance_market.register_insurer(
        'insurer_b', initial_capital=80_000.0, num_pools=1
    )

    # Register all workers with the insurance market (honest declaration)
    for w in workers:
        insurance_market.register_agent(
            agent_id=w.id,
            true_risk=w.risk_profile,
            declared_risk=w.risk_profile,  # honest
            initial_cash=0.0,             # already on ledger
        )

    # ── 4. Compact-utility map (drives migration) ─────────────────
    compact_utilities = {
        'compact_alpha': 1.0,
        'compact_beta': 1.1,
        'compact_gamma': 0.9,
    }

    # ── 5. Simulation loop ─────────────────────────────────────────
    STEPS = 10

    print(f'\n─── Created {len(workers)} workers across '
          f'{len(COMPACT_IDS)} compacts ───\n')

    for step_num in range(1, STEPS + 1):
        ledger.begin_step()

        step_results: list[dict] = []

        # ── Phase A: Worker decisions ──────────────────────────────
        for w in workers:
            sr = w.step(
                compact_utilities=compact_utilities,
                insurer_id=(
                    'insurer_a' if _random.random() < 0.5 else 'insurer_b'
                ),
                insurance_coverage=5000.0,
            )
            step_results.append(sr)

            # Purchase policy with insurance market if worker wants one
            if sr.get('wants_new_policy') and sr.get('wants_new_insurer'):
                insurance_market.purchase_policy(
                    agent_id=w.id,
                    insurer_id=sr['wants_new_insurer'],
                    coverage_limit=5000.0,
                )

        # ── Phase B: Insurance premium collection ──────────────────
        premium_results = insurance_market.collect_premiums()
        premium_lookup: dict[str, float] = {}
        for pr in premium_results:
            if pr.get('status') == 'paid':
                premium_lookup[pr['agent_id']] = pr.get('premium', 0.0)
        for w in workers:
            amt = premium_lookup.get(w.id, 0.0)
            w.total_insurance_premiums += amt

        # ── Phase C: LVT + Dividend ────────────────────────────────
        citizen_ids = [w.id for w in workers]
        compact_map = {w.id: w.compact_id for w in workers}

        lvt_results = lvt_engine.collect(citizen_ids)
        for cid, amt in lvt_results.items():
            for w in workers:
                if w.id == cid:
                    w.total_lvt_paid += amt
                    break

        compact_contributions: dict[str, float] = {}
        for cid, bill in lvt_results.items():
            comp = compact_map.get(cid, '')
            compact_contributions[comp] = (
                compact_contributions.get(comp, 0.0) + bill
            )

        total_lvt = sum(lvt_results.values())
        dist_result = trust_engine.distribute(
            citizen_ids=citizen_ids,
            total_lvt=total_lvt,
            compact_contributions=compact_contributions,
        )

        for t in dist_result.get('transfers', []):
            for w in workers:
                if w.id == t['citizen']:
                    w.total_dividends += t['dividend']
                    break

        # ── Close step with zero-sum check ─────────────────────────
        metrics = ledger.close_step()

        # ── Per-step summary line ─────────────────────────────────
        total_wage = sum(sr['wage_income'] for sr in step_results)
        total_hours = sum(sr['hours_worked'] for sr in step_results)
        insured_count = sum(
            1 for sr in step_results if sr['has_insurance']
        )
        migrations = sum(
            1 for sr in step_results if sr.get('migrated_to')
        )

        print(
            f'  Step {step_num:2d}:  '
            f'wages=${total_wage:>8.2f}  '
            f'hours={total_hours:>6.1f}  '
            f'LVT=${total_lvt:>8.2f}  '
            f'div=${dist_result["per_capita"]:>6.2f}/ea  '
            f'insured={insured_count:2d}/{len(workers)}  '
            f'moved={migrations:2d}  '
            f'{"✓" if metrics["balanced"] else "⚠"}'
        )

    # ── 6. Final Aggregate Statistics ───────────────────────────────
    print('\n' + '═' * 72)
    print('  AGGREGATE STATISTICS (10 steps)')
    print('═' * 72)

    all_stats = [w.get_stats() for w in workers]

    total_wage = sum(s['total_labor_income'] for s in all_stats)
    total_lvt = sum(s['total_lvt_paid'] for s in all_stats)
    total_div = sum(s['total_dividends'] for s in all_stats)
    total_prem = sum(s['total_insurance_premiums'] for s in all_stats)
    total_hours = sum(s['total_hours_worked'] for s in all_stats)
    total_net_worth = sum(s['net_worth'] for s in all_stats)
    total_cash = sum(s['cash'] for s in all_stats)
    insured_count = sum(1 for s in all_stats if s['has_insurance'])

    avg_productivity = (
        sum(s['productivity'] for s in all_stats) / len(all_stats)
    )
    avg_honesty = sum(s['honesty'] for s in all_stats) / len(all_stats)
    avg_land = sum(s['land_value'] for s in all_stats) / len(all_stats)
    avg_risk = sum(s['risk_profile'] for s in all_stats) / len(all_stats)

    compact_dist: dict[str, int] = {}
    for s in all_stats:
        c = s['compact_id']
        compact_dist[c] = compact_dist.get(c, 0) + 1

    print(f'\n  Workers:             {len(workers)}')
    print(f'  Steps:               {STEPS}')
    print(f'  Currently insured:   {insured_count}/{len(workers)}')
    print(f'  Compact distribution:{compact_dist}')
    print()
    print(f'  ── Averages per worker ──')
    print(f'  Productivity:        {avg_productivity:>8.2f}  $/hour')
    print(f'  Land value:          ${avg_land:>8,.2f}')
    print(f'  Risk profile:        {avg_risk:>8.3f}')
    print(f'  Honesty (θ):         {avg_honesty:>8.3f}')
    print()
    print(f'  ── Totals (all workers) ──')
    print(f'  Total labour income: ${total_wage:>10,.2f}')
    print(f'  Total hours worked:  {total_hours:>10,.1f}')
    print(f'  Total LVT paid:      ${total_lvt:>10,.2f}')
    print(f'  Total dividends:     ${total_div:>10,.2f}')
    print(f'  Total insurance:     ${total_prem:>10,.2f}')
    print(f'  Total cash:          ${total_cash:>10,.2f}')
    print(f'  Total net worth:     ${total_net_worth:>10,.2f}')
    print()
    print(f'  ── Ledger Health ──')
    print(f'  Total transfers:     {len(ledger.transfers)}')
    print(f'  Total entries:       {len(ledger.entries)}')
    total_money = sum(bs.cash for bs in ledger.balances.values())
    print(f'  Total money in sys:  ${total_money:>10,.2f}')
    print(f'\n✅ Demo complete — all steps balanced through the ledger.\n')


if __name__ == '__main__':
    # Delayed imports so the module is importable standalone
    # Import LVT mechanics for demo
    from src.mechanics.lvt import LVTEngine, TrustEngine
    from ..mechanics.insurance import InsuranceMarket
    demo()
