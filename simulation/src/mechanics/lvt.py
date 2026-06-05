"""
mechanics/lvt.py — LVT, National Trust, Citizen's Dividend & Alliance Skim

Implements the full LVT → Dividend → Skim loop:

  1. LVTEngine  — collects Land Value Tax from citizens based on land holdings
  2. TrustEngine — receives LVT revenue, skims 10 % to the Alliance,
                   distributes the remainder as a per-capita Citizen's Dividend
  3. AllianceSkim — tracks the Alliance budget and refunds unspent funds
                    proportional to each compact's contribution

All monetary transfers go through the LedgerEngine interface.
"""

from __future__ import annotations
from typing import Optional
from ..core.ledger import LedgerEngine, EntityType


# ═══════════════════════════════════════════════════════════════════════
# 1 — LVT Engine
# ═══════════════════════════════════════════════════════════════════════

class LVTEngine:
    """
    Collects Land Value Tax from citizens based on their declared
    land holdings (recorded on each citizen's BalanceSheet as land_value).

    LVT_Bill_i = LVT_Rate × Declared_Land_Value_i

    Money flows: citizen → national_trust  (mechanism='lvt')
    """

    def __init__(self, ledger: LedgerEngine,
                 trust_id: str = 'national_trust',
                 rate: float = 0.05):
        """
        Parameters
        ----------
        ledger    : LedgerEngine  — the simulation accounting engine
        trust_id  : str           — entity id of the National Trust
        rate      : float         — LVT rate (default 5 %; typical range 3–6 %)
        """
        self.ledger = ledger
        self.trust_id = trust_id
        self.rate = rate

    # ── Public API ─────────────────────────────────────────────────

    def collect(self, citizen_ids: list[str]) -> dict[str, float]:
        """
        Assess and collect LVT from every citizen in *citizen_ids*.

        Returns a dict mapping each citizen_id to the amount collected
        (0.0 for citizens with no land holdings).

        Precondition: the caller has called ledger.begin_step().
        """
        results: dict[str, float] = {}
        for cid in citizen_ids:
            bs = self.ledger.get_balance(cid)
            bill = bs.land_value * self.rate
            if bill > 0:
                self.ledger.transfer(
                    from_id=cid,
                    to_id=self.trust_id,
                    mechanism='lvt',
                    amount=bill,
                    description=f'LVT on land value {bs.land_value:.2f} @ {self.rate*100:.2f}%',
                )
            results[cid] = bill
        return results

    @property
    def total_collected(self) -> float:
        """Total LVT ever collected (across all steps)."""
        return self.ledger.get_total_flow('lvt')

    def total_collected_this_step(self) -> float:
        """Total LVT collected during the current step only."""
        return self.ledger.get_total_flow('lvt', step=self.ledger.step)


# ═══════════════════════════════════════════════════════════════════════
# 2 — Trust Engine  (National Trust → Dividend)
# ═══════════════════════════════════════════════════════════════════════

class TrustEngine:
    """
    The National Trust receives LVT revenue, sends the Alliance skim
    (10 %) to the Alliance, then distributes the remainder as a flat
    per-capita Citizen's Dividend.

    Flow:
      LVT revenue (already in trust) →
        1. Alliance skim  (trust → alliance, mechanism='alliance_skim')
        2. Dividend        (trust → citizen, mechanism='dividend')
    """

    def __init__(self, ledger: LedgerEngine,
                 trust_id: str = 'national_trust',
                 alliance_id: str = 'alliance',
                 skim_rate: float = 0.10):
        """
        Parameters
        ----------
        ledger      : LedgerEngine
        trust_id    : str  — id of the National Trust entity
        alliance_id : str  — id of the Alliance entity
        skim_rate   : float  — fraction of LVT revenue taken by the Alliance
                               (constitutionally fixed at 0.10)
        """
        self.ledger = ledger
        self.trust_id = trust_id
        self.alliance_id = alliance_id
        self.skim_rate = skim_rate

    # ── Public API ─────────────────────────────────────────────────

    def distribute(self, citizen_ids: list[str],
                   total_lvt: float,
                   essential_costs: float = 0.0,
                   compact_contributions: Optional[dict[str, float]] = None
                   ) -> dict:
        """
        Execute the full dividend distribution for a single step.

        Parameters
        ----------
        citizen_ids           : list[str]  — all registered citizens
        total_lvt             : float      — gross LVT collected this step
        essential_costs       : float      — state costs deducted before dividend
                                             (default 0.0 for the simple loop)
        compact_contributions : dict[str, float] | None
            — mapping of compact_id → amount contributed in LVT this step.
              Used by AllianceSkim to track proportional refunds.
              If None the skim amount is passed without compact attribution.

        Returns a summary dict with keys:
            'gross_lvt', 'alliance_skim', 'dividend_pool',
            'per_capita', 'citizen_count', 'transfers'
        """
        if compact_contributions is None:
            compact_contributions = {}

        n = len(citizen_ids)
        if n == 0:
            return {
                'gross_lvt': total_lvt,
                'alliance_skim': 0.0,
                'dividend_pool': 0.0,
                'per_capita': 0.0,
                'citizen_count': 0,
                'transfers': [],
            }

        # --- 1. Alliance skim ---
        skim_amount = total_lvt * self.skim_rate

        self.ledger.transfer(
            from_id=self.trust_id,
            to_id=self.alliance_id,
            mechanism='alliance_skim',
            amount=skim_amount,
            description=f'Alliance skim ({self.skim_rate*100:.0f}% of {total_lvt:.2f} LVT)',
        )

        # --- 2. Deduct essential costs ---
        #    (these stay in the trust in a fuller model; for the basic loop
        #     we treat them as a deduction from the dividend pool)
        #    Costs are recorded as a transfer to SYSTEM for auditability.
        cost_paid = 0.0
        if essential_costs > 0:
            self.ledger.transfer(
                from_id=self.trust_id,
                to_id='__system__',
                mechanism='essential_cost',
                amount=essential_costs,
                description='Essential state costs',
            )
            cost_paid = essential_costs

        # --- 3. Dividend pool → per capita ---
        dividend_pool = total_lvt - skim_amount - cost_paid
        per_capita = dividend_pool / n

        transfers = []
        for cid in citizen_ids:
            self.ledger.transfer(
                from_id=self.trust_id,
                to_id=cid,
                mechanism='dividend',
                amount=per_capita,
                description=f'Citizen Dividend per capita ({per_capita:.4f})',
            )
            transfers.append({'citizen': cid, 'dividend': per_capita})

        return {
            'gross_lvt': total_lvt,
            'alliance_skim': skim_amount,
            'essential_costs': cost_paid,
            'dividend_pool': dividend_pool,
            'per_capita': per_capita,
            'citizen_count': n,
            'transfers': transfers,
        }


# ═══════════════════════════════════════════════════════════════════════
# 3 — Alliance Skim  (budget tracking & proportional refund)
# ═══════════════════════════════════════════════════════════════════════

class AllianceSkim:
    """
    Tracks the Alliance's cumulative skim revenue, attribute it per
    compact, and handles proportional refund of unspent funds.

    Per the spec:
      "Unspent funds refunded proportional to each compact's contribution
       (not per capita)."

    The Alliance cannot carry unspent budget across fiscal periods unless
    explicitly authorized — the default is full refund.
    """

    def __init__(self, ledger: LedgerEngine,
                 alliance_id: str = 'alliance'):
        self.ledger = ledger
        self.alliance_id = alliance_id

        # Cumulative contributions per compact (across all steps)
        # compact_id → total LS$ contributed via skim
        self.compact_contributions: dict[str, float] = {}

        # Running budget pool available for spending
        self.budget: float = 0.0

        # Spending so far this period (step-by-step)
        self.spending: list[dict] = []

    # ── Public API ─────────────────────────────────────────────────

    def record_skim(self, amount: float,
                    compact_contributions: dict[str, float]) -> float:
        """
        Record the Alliance skim from a step's LVT.

        Parameters
        ----------
        amount               : float
            The total skim received this step (10 % of LVT).
        compact_contributions : dict[str, float]
            How much LVT each compact generated this step.
            Used to attribute the skim proportionally per compact.

        Returns the updated budget balance.
        """
        total_lvt = sum(compact_contributions.values()) or 1.0  # avoid div-by-zero

        for compact_id, lvt_contributed in compact_contributions.items():
            if lvt_contributed <= 0:
                continue
            share = lvt_contributed / total_lvt
            contribution = amount * share
            self.compact_contributions[compact_id] = \
                self.compact_contributions.get(compact_id, 0.0) + contribution

        self.budget += amount
        return self.budget

    def spend(self, amount: float, description: str, payee_id: str = '__system__') -> float:
        """
        Record Alliance spending (e.g., defense PMC, court admin).

        Parameters
        ----------
        amount      : float
        description : str
        payee_id    : str   — who receives the payment (default SYSTEM)

        Returns remaining budget.
        """
        if amount > self.budget:
            amount = self.budget  # soft cap — cannot spend more than available

        self.ledger.transfer(
            from_id=self.alliance_id,
            to_id=payee_id,
            mechanism='alliance_spend',
            amount=amount,
            description=description,
        )
        self.budget -= amount
        self.spending.append({'amount': amount, 'description': description})
        return self.budget

    def refund_unspent(self) -> dict[str, float]:
        """
        Refund the unspent Alliance budget to compacts proportionally.

        Returns a dict mapping compact_id → refund amount.
        """
        total_contrib = sum(self.compact_contributions.values())
        if total_contrib <= 0 or self.budget <= 0:
            unspent = self.budget
            self.budget = 0.0
            return {}

        refunds: dict[str, float] = {}
        remaining = self.budget

        for compact_id, contrib in sorted(self.compact_contributions.items()):
            share = contrib / total_contrib
            refund_amount = self.budget * share
            # Compact refund goes to the compact entity itself
            self.ledger.transfer(
                from_id=self.alliance_id,
                to_id=compact_id,
                mechanism='alliance_refund',
                amount=refund_amount,
                description=f'Proportional refund to compact {compact_id} '
                            f'({share*100:.1f}% of unspent {self.budget:.2f})',
            )
            refunds[compact_id] = refund_amount
            remaining -= refund_amount

        # Dust guard — send rounding residual to SYSTEM
        if remaining > 0.001:
            self.ledger.transfer(
                from_id=self.alliance_id,
                to_id='__system__',
                mechanism='alliance_refund_dust',
                amount=remaining,
                description=f'Rounding residual refund dust ({remaining:.6f})',
            )

        self.budget = 0.0
        return refunds

    def reset(self):
        """Clear all compact tracking and budget (start a new fiscal period)."""
        self.compact_contributions.clear()
        self.budget = 0.0
        self.spending.clear()


# ═══════════════════════════════════════════════════════════════════════
# 4 — Convenience: Full LVT → Dividend → Skim pipeline
# ═══════════════════════════════════════════════════════════════════════

def run_full_cycle(ledger: LedgerEngine,
                   lvt: LVTEngine,
                   trust: TrustEngine,
                   alliance: AllianceSkim,
                   citizen_ids: list[str],
                   compact_map: dict[str, str],
                   essential_costs: float = 0.0) -> dict:
    """
    Execute one complete simulation step covering:
      1. LVT collection (citizen → trust)
      2. Dividend distribution with skim (trust → alliance, trust → citizen)

    Returns a composite summary dict.
    """
    ledger.begin_step()

    # 1. LVT collection
    lvt_results = lvt.collect(citizen_ids)

    # Build compact contribution map
    compact_contributions: dict[str, float] = {}
    for cid, bill in lvt_results.items():
        comp = compact_map.get(cid, '')
        compact_contributions[comp] = compact_contributions.get(comp, 0.0) + bill

    total_lvt = sum(lvt_results.values())

    # 2. Dividend distribution (includes skim transfer)
    dist_result = trust.distribute(
        citizen_ids=citizen_ids,
        total_lvt=total_lvt,
        essential_costs=essential_costs,
        compact_contributions=compact_contributions,
    )

    # 3. Record skim in Alliance tracker
    alliance.record_skim(
        amount=dist_result['alliance_skim'],
        compact_contributions=compact_contributions,
    )

    metrics = ledger.close_step()

    return {
        'step': ledger.step,
        'lvt_collected': lvt_results,
        'total_lvt': total_lvt,
        'compact_contributions': compact_contributions,
        'distribution': dist_result,
        'alliance_budget': alliance.budget,
        'balanced': metrics['balanced'],
        'imbalance': metrics['imbalance'],
        'step_metrics': metrics,
    }


# ═══════════════════════════════════════════════════════════════════════
# 5 — Test / Demonstration
# ═══════════════════════════════════════════════════════════════════════

def demo():
    """
    Full integration demo that exercises the LVT → Dividend → Skim loop
    with multiple citizens and compacts, showing all balance changes,
    the proportional refund mechanism, and zero-sum invariant checks.
    """
    print("═" * 72)
    print("  LVT → NATIONAL TRUST → CITIZEN'S DIVIDEND → ALLIANCE SKIM")
    print("═" * 72)

    # ── Setup ──────────────────────────────────────────────────────
    ledger = LedgerEngine(step_log=True)
    lvt_engine = LVTEngine(ledger, rate=0.05)
    trust_engine = TrustEngine(ledger, skim_rate=0.10)
    alliance_skim = AllianceSkim(ledger)

    # Register entities
    ledger.register_entity('national_trust', EntityType.TRUST, initial_cash=0.0)
    ledger.register_entity('alliance',       EntityType.ALLIANCE, initial_cash=0.0)
    ledger.register_entity('__system__',     EntityType.SYSTEM,   initial_cash=0.0)

    # Register compacts
    ledger.register_entity('compact_alpha', EntityType.COMPACT, initial_cash=0.0)
    ledger.register_entity('compact_beta',  EntityType.COMPACT, initial_cash=0.0)

    # Register citizens with land holdings and compact membership
    citizens = [
        ('alice',  'compact_alpha', 500_000.0, 10_000.0),
        ('bob',    'compact_alpha', 300_000.0, 8_000.0),
        ('carol',  'compact_beta',  800_000.0, 20_000.0),
        ('dave',   'compact_beta',  200_000.0, 5_000.0),
        ('eve',    'compact_alpha',   2_000.0, 0_000.0),   # no land, still gets dividend
    ]

    citizen_ids: list[str] = []
    compact_map: dict[str, str] = {}

    for name, comp, initial_cash, land_val in citizens:
        bs = ledger.register_entity(
            name, EntityType.CITIZEN,
            compact_id=comp,
            initial_cash=initial_cash,
        )
        bs.land_value = land_val
        bs.property_count = 1 if land_val > 0 else 0
        citizen_ids.append(name)
        compact_map[name] = comp

    # ── Helper ─────────────────────────────────────────────────────
    def print_state(label: str):
        print(f"\n─── {label} ───")
        for eid in ['alice', 'bob', 'carol', 'dave', 'eve',
                     'national_trust', 'alliance',
                     'compact_alpha', 'compact_beta']:
            bs = ledger.get_balance(eid)
            print(f"  {eid:20s}  cash={bs.cash:>10.2f}  land={bs.land_value:>10.2f}  "
                  f"net={bs.net_worth:>10.2f}")

    # ═══════════════════════════════════════════════════════════════
    # CYCLE 1 — Simple LVT → Dividend → Skim
    # ═══════════════════════════════════════════════════════════════
    print("\n\n▶  CYCLE 1: Basic LVT Collection + Dividend + Skim")

    result = run_full_cycle(
        ledger, lvt_engine, trust_engine, alliance_skim,
        citizen_ids, compact_map,
    )

    print(f"\n  Step {result['step']}:")
    print(f"    LVT collected:        ${result['total_lvt']:>10.2f}")
    for cid, amt in result['lvt_collected'].items():
        print(f"      {cid:12s}  ${amt:>8.2f}")
    print(f"    Alliance skim (10%):  ${result['distribution']['alliance_skim']:>10.2f}")
    print(f"    Dividend pool:        ${result['distribution']['dividend_pool']:>10.2f}")
    print(f"    Per capita dividend:  ${result['distribution']['per_capita']:>10.2f}")
    print(f"    Alliance budget:      ${result['alliance_budget']:>10.2f}")
    print(f"    Balanced:             {result['balanced']}  (imbalance: {result['imbalance']:.6f})")

    print_state("After Cycle 1")

    # ═══════════════════════════════════════════════════════════════
    # CYCLE 2 — Second year (accumulate more skim)
    # ═══════════════════════════════════════════════════════════════
    print("\n\n▶  CYCLE 2: Another Year — accumulate Alliance budget")

    result2 = run_full_cycle(
        ledger, lvt_engine, trust_engine, alliance_skim,
        citizen_ids, compact_map,
    )

    print(f"\n  Step {result2['step']}:")
    print(f"    LVT collected:        ${result2['total_lvt']:>10.2f}")
    print(f"    Alliance budget now:  ${alliance_skim.budget:>10.2f}")
    print(f"    Balanced:             {result2['balanced']}  (imbalance: {result2['imbalance']:.6f})")

    print_state("After Cycle 2")

    # ═══════════════════════════════════════════════════════════════
    # CYCLE 3 — Spend some Alliance budget, then refund unspent
    # ═══════════════════════════════════════════════════════════════
    print("\n\n▶  CYCLE 3: Alliance spends part of budget + proportional refund")

    ledger.begin_step()

    # Alliance spends 40% of its budget on defense
    spend_amount = alliance_skim.budget * 0.40
    remaining = alliance_skim.spend(
        amount=spend_amount,
        description='Border defense PMC contract',
        payee_id='__system__',
    )
    print(f"    Spent on defense:     ${spend_amount:>10.2f}")
    print(f"    Remaining budget:     ${remaining:>10.2f}")

    # Refund unspent proportionally
    refunds = alliance_skim.refund_unspent()
    print(f"\n    Proportional refunds:")
    for comp, amt in refunds.items():
        print(f"      {comp:20s}  ${amt:>8.2f}")
    total_refunded = sum(refunds.values())
    print(f"      Total refunded:     ${total_refunded:>8.2f}")
    print(f"      Alliance budget after: ${alliance_skim.budget:.2f}")

    metrics3 = ledger.close_step()
    print(f"    Balanced:             {metrics3['balanced']}  (imbalance: {metrics3['imbalance']:.6f})")

    print_state("After Cycle 3 (refund)")

    # ── Final verification ─────────────────────────────────────────
    print("\n\n═" * 72)
    print("  FINAL VERIFICATION")
    print("═" * 72)

    # Verify zero-sum across all steps
    all_balanced = all(m['balanced'] for m in ledger.step_metrics)
    total_money = sum(bs.cash for bs in ledger.balances.values())
    print(f"  All steps balanced:  {all_balanced}")
    print(f"  Total money in system: ${total_money:>10.2f}")
    print(f"  Total transfers recorded: {len(ledger.transfers)}")
    print(f"  Total ledger entries:     {len(ledger.entries)}")

    # Verify each citizen's net position
    print(f"\n  Citizen net worth check:")
    for cid in citizen_ids:
        bs = ledger.get_balance(cid)
        lvt_paid = sum(
            t.amount for t in ledger.transfers
            if t.from_id == cid and t.mechanism == 'lvt'
        )
        dividend_received = sum(
            t.amount for t in ledger.transfers
            if t.to_id == cid and t.mechanism == 'dividend'
        )
        net_transfer = dividend_received - lvt_paid
        print(f"    {cid:12s}  LVT paid={lvt_paid:>8.2f}  "
              f"Dividends={dividend_received:>8.2f}  Net={net_transfer:>+8.2f}  "
              f"Cash={bs.cash:>8.2f}")

    # Verify compact refunds
    print(f"\n  Compact balances:")
    for comp in ['compact_alpha', 'compact_beta']:
        bs = ledger.get_balance(comp)
        refund_received = sum(
            t.amount for t in ledger.transfers
            if t.to_id == comp and t.mechanism == 'alliance_refund'
        )
        print(f"    {comp:20s}  cash={bs.cash:>8.2f}  "
              f"refund_received={refund_received:>8.2f}")

    # Summary
    print(f"\n  ✅ Pipeline complete."
          f"  Zero-sum: {'PASS' if all_balanced else 'FAIL'}")
    if not all_balanced:
        print(f"  ⚠️  Imbalances found — check step metrics above.")

    return ledger


if __name__ == '__main__':
    demo()
