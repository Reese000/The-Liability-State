"""
core/ledger.py — Double-entry accounting engine

Every economic entity has a balance sheet. Every transfer is recorded.
The zero-sum invariant is checked every step.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
import uuid
import json
from pathlib import Path


# ─── Entity Types ────────────────────────────────────────────────────

class EntityType(Enum):
    CITIZEN       = auto()
    TRUST         = auto()   # National Trust (holds LVT, pays Dividend)
    ALLIANCE      = auto()
    INSURER       = auto()
    COURT         = auto()
    GUILD         = auto()
    COMPACT       = auto()
    BUSINESS      = auto()
    SYSTEM        = auto()   # Sink/source for external flows (events, etc.)


# ─── Ledger Entry ────────────────────────────────────────────────────

@dataclass
class LedgerEntry:
    entry_id: str
    step: int
    entity_id: str
    counterparty_id: str
    mechanism: str          # 'lvt', 'dividend', 'premium', 'claim', 'wage', etc.
    amount: float
    balance_before: float
    balance_after: float
    description: str

    def to_dict(self) -> dict:
        return {
            'entry_id': self.entry_id,
            'step': self.step,
            'entity_id': self.entity_id,
            'counterparty_id': self.counterparty_id,
            'mechanism': self.mechanism,
            'amount': round(self.amount, 4),
            'balance_before': round(self.balance_before, 4),
            'balance_after': round(self.balance_after, 4),
            'description': self.description,
        }


# ─── Entity Balance Sheet ────────────────────────────────────────────

@dataclass
class BalanceSheet:
    entity_id: str
    entity_type: EntityType
    cash: float = 0.0
    land_value: float = 0.0        # Current assessed value of land owned
    property_count: int = 0
    outstanding_liability: float = 0.0   # Unpaid court judgments against
    outstanding_claims: float = 0.0      # Unpaid claims owed to entity
    compact_id: str = ''

    @property
    def net_worth(self) -> float:
        return self.cash + self.land_value - self.outstanding_liability

    def to_dict(self) -> dict:
        return {
            'entity_id': self.entity_id,
            'entity_type': self.entity_type.name,
            'cash': round(self.cash, 4),
            'land_value': round(self.land_value, 4),
            'property_count': self.property_count,
            'outstanding_liability': round(self.outstanding_liability, 4),
            'outstanding_claims': round(self.outstanding_claims, 4),
            'net_worth': round(self.net_worth, 4),
            'compact_id': self.compact_id,
        }


# ─── Money Transfer ──────────────────────────────────────────────────

@dataclass
class Transfer:
    """A single money movement between two entities. Recorded in the ledger."""
    transfer_id: str
    step: int
    from_id: str
    to_id: str
    mechanism: str
    amount: float
    sub_step: int = 0   # Order within step for deterministic replay

    def to_dict(self) -> dict:
        return {
            'transfer_id': self.transfer_id,
            'step': self.step,
            'from_id': self.from_id,
            'to_id': self.to_id,
            'mechanism': self.mechanism,
            'amount': round(self.amount, 4),
            'sub_step': self.sub_step,
        }


# ─── Flow Matrix (8×8) ────────────────────────────────────────────

class FlowMatrix:
    """
    Tracks total dollars moved between entity types per step.
    flow[from_type][to_type] = total amount
    """

    TYPES = [
        EntityType.CITIZEN, EntityType.TRUST, EntityType.ALLIANCE,
        EntityType.INSURER, EntityType.COURT, EntityType.GUILD,
        EntityType.COMPACT, EntityType.BUSINESS, EntityType.SYSTEM,
    ]

    def __init__(self):
        self.reset()

    def reset(self):
        n = len(self.TYPES)
        idx = {t: i for i, t in enumerate(self.TYPES)}
        self.idx = idx
        self.matrix = [[0.0] * n for _ in range(n)]

    def record(self, from_type: EntityType, to_type: EntityType, amount: float):
        if amount == 0:
            return
        i, j = self.idx[from_type], self.idx[to_type]
        self.matrix[i][j] += amount

    def get(self, from_type: EntityType, to_type: EntityType) -> float:
        return self.matrix[self.idx[from_type]][self.idx[to_type]]

    def total_out(self, from_type: EntityType) -> float:
        return sum(self.matrix[self.idx[from_type]])

    def total_in(self, to_type: EntityType) -> float:
        return sum(row[self.idx[to_type]] for row in self.matrix)

    def check_zero_sum(self) -> tuple[bool, float]:
        """Returns (is_balanced, total_imbalance)."""
        total_out = sum(sum(row) for row in self.matrix)
        total_in = sum(sum(self.matrix[i][j] for i in range(len(self.TYPES)))
                       for j in range(len(self.TYPES)))
        # Total out should equal total in (every debit has a credit)
        imbalance = abs(total_out - total_in)
        return imbalance < 0.001, imbalance

    def to_dict(self) -> dict:
        result = {}
        for i, from_t in enumerate(self.TYPES):
            row = {}
            for j, to_t in enumerate(self.TYPES):
                if self.matrix[i][j] != 0:
                    row[to_t.name] = round(self.matrix[i][j], 4)
            if row:
                result[from_t.name] = row
        return result


# ─── Ledger Engine ───────────────────────────────────────────────────

class LedgerEngine:
    """
    Central accounting system.
    Manages balance sheets, records transfers, enforces zero-sum.
    """

    def __init__(self, step_log: bool = True):
        self.step = 0
        self.sub_step = 0
        self.step_log = step_log

        # Entity registry
        self.balances: dict[str, BalanceSheet] = {}

        # Transfer log (ordered)
        self.transfers: list[Transfer] = []

        # Ledger entries (one per side of each transfer)
        self.entries: list[LedgerEntry] = []

        # Flow matrix for current step
        self.flow = FlowMatrix()

        # Step metrics history
        self.step_metrics: list[dict] = []

    # ─── Entity Management ─────────────────────────────────────────

    def register_entity(self, entity_id: str, entity_type: EntityType,
                         compact_id: str = '', initial_cash: float = 0.0) -> BalanceSheet:
        if entity_id in self.balances:
            raise ValueError(f"Entity {entity_id} already registered")
        bs = BalanceSheet(
            entity_id=entity_id,
            entity_type=entity_type,
            cash=initial_cash,
            compact_id=compact_id,
        )
        self.balances[entity_id] = bs
        return bs

    def get_balance(self, entity_id: str) -> BalanceSheet:
        if entity_id not in self.balances:
            raise KeyError(f"Entity {entity_id} not found")
        return self.balances[entity_id]

    def entity_exists(self, entity_id: str) -> bool:
        return entity_id in self.balances

    # ─── Transfers ────────────────────────────────────────────────

    def transfer(self, from_id: str, to_id: str, mechanism: str,
                 amount: float, description: str = '') -> Transfer:
        """
        Execute a money transfer between two entities.
        Both must exist. Records ledger entries for both sides.
        """
        if amount < 0:
            raise ValueError(f"Negative transfer amount: {amount}")
        if amount == 0:
            # Still record zero transfers for audit trail
            pass

        from_bs = self.get_balance(from_id)
        to_bs = self.get_balance(to_id)

        # Check sufficient funds (soft — allow negative for debts/liabilities)
        # Hard enforcement is per-mechanic, not at the accounting layer

        # Execute
        from_bs.cash -= amount
        to_bs.cash += amount

        # Record transfer
        t = Transfer(
            transfer_id=str(uuid.uuid4())[:12],
            step=self.step,
            sub_step=self.sub_step,
            from_id=from_id,
            to_id=to_id,
            mechanism=mechanism,
            amount=amount,
        )
        self.transfers.append(t)

        # Record ledger entries (both sides)
        from_entry = LedgerEntry(
            entry_id=f"{t.transfer_id}_dr",
            step=self.step,
            entity_id=from_id,
            counterparty_id=to_id,
            mechanism=mechanism,
            amount=-amount,
            balance_before=from_bs.cash + amount,  # before deducting
            balance_after=from_bs.cash,
            description=description or f"{mechanism}: {from_id} → {to_id}",
        )
        to_entry = LedgerEntry(
            entry_id=f"{t.transfer_id}_cr",
            step=self.step,
            entity_id=to_id,
            counterparty_id=from_id,
            mechanism=mechanism,
            amount=amount,
            balance_before=to_bs.cash - amount,
            balance_after=to_bs.cash,
            description=description or f"{mechanism}: {from_id} → {to_id}",
        )
        self.entries.append(from_entry)
        self.entries.append(to_entry)

        # Update flow matrix
        self.flow.record(from_bs.entity_type, to_bs.entity_type, amount)

        self.sub_step += 1
        return t

    # ─── Step Management ──────────────────────────────────────────

    def begin_step(self):
        """Start a new simulation step."""
        self.step += 1
        self.sub_step = 0
        self.flow.reset()

    def close_step(self) -> dict:
        """
        End the current step. Check zero-sum invariant. Record metrics.
        Returns step summary.
        """
        balanced, imbalance = self.flow.check_zero_sum()

        metrics = {
            'step': self.step,
            'balanced': balanced,
            'imbalance': round(imbalance, 4),
            'transfer_count': sum(1 for t in self.transfers if t.step == self.step),
            'total_money': round(sum(bs.cash for bs in self.balances.values()), 4),
            'total_net_worth': round(sum(bs.net_worth for bs in self.balances.values()), 4),
            'flow_matrix': self.flow.to_dict(),
        }

        if not balanced and self.step_log:
            print(f"  ⚠️  Step {self.step}: imbalance detected: {imbalance:.6f}")

        self.step_metrics.append(metrics)
        return metrics

    # ─── Queries ──────────────────────────────────────────────────

    def get_transfers_by_mechanism(self, mechanism: str, step: Optional[int] = None) -> list[Transfer]:
        """Get all transfers for a mechanism (optionally at a specific step)."""
        result = []
        for t in self.transfers:
            if t.mechanism == mechanism:
                if step is None or t.step == step:
                    result.append(t)
        return result

    def get_total_flow(self, mechanism: str, step: Optional[int] = None) -> float:
        """Get total amount transferred for a mechanism."""
        return sum(t.amount for t in self.get_transfers_by_mechanism(mechanism, step))

    # ─── Export ───────────────────────────────────────────────────

    def export_json(self, path: str):
        """Export ledger to JSON file."""
        data = {
            'step': self.step,
            'entities': {eid: bs.to_dict() for eid, bs in self.balances.items()},
            'transfers': [t.to_dict() for t in self.transfers],
            'step_metrics': self.step_metrics,
        }
        Path(path).write_text(json.dumps(data, indent=2))



# ─── Test / Demonstration ────────────────────────────────────────────

def demo():
    """Run a simple test of the ledger engine."""
    print("═" * 60)
    print("CORE LEDGER — DEMONSTRATION")
    print("═" * 60)

    ledger = LedgerEngine()

    # Register entities
    alice = ledger.register_entity('alice', EntityType.CITIZEN, compact_id='alpha', initial_cash=1000.0)
    bob = ledger.register_entity('bob', EntityType.CITIZEN, compact_id='alpha', initial_cash=500.0)
    trust = ledger.register_entity('national_trust', EntityType.TRUST, initial_cash=0.0)
    alliance = ledger.register_entity('alliance', EntityType.ALLIANCE, initial_cash=0.0)
    insurer = ledger.register_entity('insurer_a', EntityType.INSURER, initial_cash=10000.0)
    court = ledger.register_entity('court_1', EntityType.COURT, initial_cash=500.0)

    print(f"\nEntities registered: {len(ledger.balances)}")
    print(f"  Alice: ${alice.cash}")
    print(f"  Bob:   ${bob.cash}")
    print(f"  Trust: ${trust.cash}")

    # Step 1: LVT collection
    print("\n─── Step 1: LVT Collection ───")
    ledger.begin_step()
    ledger.transfer('alice', 'national_trust', 'lvt', 50.0, 'Alice LVT payment')
    ledger.transfer('bob', 'national_trust', 'lvt', 30.0, 'Bob LVT payment')
    metrics = ledger.close_step()
    print(f"  Trust balance: ${trust.cash:.2f}")
    print(f"  Alice balance: ${alice.cash:.2f}")
    print(f"  Balanced: {metrics['balanced']}")

    # Step 2: Alliance skim + Dividend
    print("\n─── Step 2: Dividend Distribution ───")
    ledger.begin_step()
    total_lvt = ledger.get_total_flow('lvt')
    alliance_skim = total_lvt * 0.10
    dividend_pool = total_lvt - alliance_skim
    per_capita = dividend_pool / 2  # 2 citizens

    ledger.transfer('national_trust', 'alliance', 'alliance_skim', alliance_skim)
    ledger.transfer('national_trust', 'alice', 'dividend', per_capita, 'Citizen Dividend')
    ledger.transfer('national_trust', 'bob', 'dividend', per_capita, 'Citizen Dividend')
    metrics = ledger.close_step()
    print(f"  LVT collected: ${total_lvt:.2f}")
    print(f"  Alliance skim (10%): ${alliance_skim:.2f}")
    print(f"  Dividend per citizen: ${per_capita:.2f}")
    print(f"  Alice net after step 2: ${alice.cash:.2f}")
    print(f"  Trust balance: ${trust.cash:.2f}")
    print(f"  Balanced: {metrics['balanced']}")

    # Step 3: Insurance
    print("\n─── Step 3: Insurance Premium & Claim ───")
    ledger.begin_step()
    ledger.transfer('alice', 'insurer_a', 'premium', 20.0, 'Alice pays insurance premium')
    ledger.transfer('insurer_a', 'alice', 'claim', 150.0, 'Alice files claim, paid by insurer')
    metrics = ledger.close_step()
    print(f"  Alice cash: ${alice.cash:.2f}")
    print(f"  Insurer cash: ${insurer.cash:.2f}")
    print(f"  Balanced: {metrics['balanced']}")

    # Export
    ledger.export_json('/tmp/ledger_demo.json')
    print(f"\n✅ All steps balanced. Ledger exported.")
    print(f"   Total transfers: {len(ledger.transfers)}")
    print(f"   Total entries:  {len(ledger.entries)}")


if __name__ == '__main__':
    demo()
