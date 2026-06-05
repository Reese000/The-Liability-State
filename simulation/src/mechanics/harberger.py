"""
harberger.py — Harberger Property Market mechanic

Implements the Harberger self-assessment property system with:
  - HarbergerParcel: land parcel with owner, declared value, assessed LVT value, bids
  - Bid: an offer to purchase a parcel at a given price
  - HarbergerMarket: orchestrates self-assessment, forced-sale process,
    Option Premium 14-day free refusal window, penalty phase at 15%,
    and Land Value Tax assessment.

Spec reference: MECHANICS_INVENTORY.md §1 (LVT & Harberger Self-Assessment)
                 and §2 (Option Premium / Harberger Transfer Protocol)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import uuid

from ..core.ledger import LedgerEngine, EntityType


# ─── Bid Status ──────────────────────────────────────────────────────


class BidStatus(Enum):
    """Lifecycle states for a purchase bid."""
    PENDING         = auto()   # Active, awaiting owner response
    ACCEPTED        = auto()   # Seller accepted → forced sale executed
    REFUSED_FREE    = auto()   # Refused during free window (no penalty)
    REFUSED_PENALTY = auto()   # Refused during penalty phase (15 % penalty)
    EXPIRED         = auto()   # Max duration reached without resolution


# ─── Option Premium Constants ────────────────────────────────────────

FREE_WINDOW_DAYS  = 14    # Days 1–14: owner may refuse with zero cash penalty
PENALTY_PHASE_DAYS = 90   # Days 15–90: owner may refuse by paying 15 % of bid
MAX_BID_DURATION  = 104   # Total days before automatic expiry
PENALTY_RATE      = 0.15  # 15 % penalty for refusal after free window


# ─── Bid Data ────────────────────────────────────────────────────────


@dataclass
class Bid:
    """A purchase offer on a Harberger parcel.

    A bid references the declared value at the time of posting.  The buyer
    has a bond (a fraction of the bid price) locked in the market escrow
    account for the duration of the bid's lifecycle.
    """

    bid_id: str
    parcel_id: str
    bidder_id: str
    bid_price: float
    step_posted: int
    status: BidStatus = BidStatus.PENDING

    def to_dict(self) -> dict:
        return {
            'bid_id': self.bid_id,
            'parcel_id': self.parcel_id,
            'bidder_id': self.bidder_id,
            'bid_price': round(self.bid_price, 4),
            'step_posted': self.step_posted,
            'status': self.status.name,
        }


# ─── Harberger Parcel ────────────────────────────────────────────────


@dataclass
class HarbergerParcel:
    """A land parcel managed under the Harberger property system.

    Attributes:
        parcel_id:       Unique identifier.
        owner:           Entity ID of the current owner.
        declared_value:  Owner's self-assessed value (the standing buyout price).
        assessed_for_lvt: Current value used for LVT calculation (may differ
                          from declared_value after a free-window refusal).
        bids:            All bids ever placed on this parcel (active + history).
    """
    parcel_id: str
    owner: str
    declared_value: float
    assessed_for_lvt: float
    bids: list[Bid] = field(default_factory=list)

    # ── computed properties ──────────────────────────────────────

    @property
    def active_bids(self) -> list[Bid]:
        """Return only bids that are still pending."""
        return [b for b in self.bids if b.status == BidStatus.PENDING]

    @property
    def has_pending_bid(self) -> bool:
        return len(self.active_bids) > 0

    def to_dict(self) -> dict:
        return {
            'parcel_id': self.parcel_id,
            'owner': self.owner,
            'declared_value': round(self.declared_value, 4),
            'assessed_for_lvt': round(self.assessed_for_lvt, 4),
            'active_bids': [b.to_dict() for b in self.active_bids],
            'total_bids_placed': len(self.bids),
        }


# ─── Harberger Market Orchestrator ───────────────────────────────────


class HarbergerMarket:
    """Orchestrates the Harberger property market.

    Key mechanics:
      * Self-assessment   — Owners declare their own land value at any time.
      * LVT assessment    — Tax collected on every parcel's assessed value.
      * Bidding           — Any agent may post a bid (≥ declared value) to buy.
      * Forced sale       — Owner accepts a bid → parcel transfers at bid price.
      * Option Premium    — Free refusal window (14 d), then penalty phase (15 %).
      * Escrow            — Buyer's bond is locked in a dedicated escrow account.

    Time is tracked as an integer day counter (``current_day``) that advances
    independently from the ledger's step counter, allowing bid aging to be
    controlled by the caller via ``advance_day()``.
    """

    def __init__(
        self,
        ledger: LedgerEngine,
        lvt_rate: float = 0.05,
        escrow_account: str = 'harberger_escrow',
        bond_fraction: float = 1.0,
    ):
        self.ledger = ledger
        self.lvt_rate = lvt_rate
        self.escrow_account = escrow_account
        self.bond_fraction = bond_fraction   # fraction of bid price locked
        self.parcels: dict[str, HarbergerParcel] = {}
        self.current_day: int = 0

        # Ensure the escrow account exists in the ledger
        if not ledger.entity_exists(escrow_account):
            ledger.register_entity(escrow_account, EntityType.SYSTEM, initial_cash=0.0)

    # ── helpers ──────────────────────────────────────────────────

    def _find_bid(self, parcel: HarbergerParcel, bid_id: str) -> Bid:
        for b in parcel.bids:
            if b.bid_id == bid_id:
                return b
        raise KeyError(
            f"Bid '{bid_id}' not found on parcel '{parcel.parcel_id}'"
        )

    def _bond_amount(self, bid_price: float) -> float:
        return bid_price * self.bond_fraction

    # ── Parcel Management ────────────────────────────────────────

    def register_parcel(
        self,
        parcel_id: str,
        owner: str,
        declared_value: float,
    ) -> HarbergerParcel:
        """Register a new Harberger parcel.

        Args:
            parcel_id:       Unique identifier for the parcel.
            owner:           Entity ID of the initial owner.
            declared_value:  Owner's initial Harberger self-assessment.

        Returns:
            The newly created HarbergerParcel.

        Raises:
            ValueError: If the parcel already exists, the value is negative,
                        or the owner is not a registered entity.
        """
        if parcel_id in self.parcels:
            raise ValueError(f"Parcel '{parcel_id}' already registered")
        if declared_value < 0:
            raise ValueError(
                f"Declared value cannot be negative: {declared_value}"
            )
        if not self.ledger.entity_exists(owner):
            raise ValueError(f"Owner '{owner}' is not a registered entity")

        parcel = HarbergerParcel(
            parcel_id=parcel_id,
            owner=owner,
            declared_value=declared_value,
            assessed_for_lvt=declared_value,
        )
        self.parcels[parcel_id] = parcel

        # Update owner's balance-sheet land value
        bs = self.ledger.get_balance(owner)
        bs.land_value += declared_value
        bs.property_count += 1

        return parcel

    def get_parcel(self, parcel_id: str) -> HarbergerParcel:
        """Look up a parcel by ID.

        Raises:
            KeyError: If the parcel does not exist.
        """
        if parcel_id not in self.parcels:
            raise KeyError(f"Parcel '{parcel_id}' not found")
        return self.parcels[parcel_id]

    # ── Self-Assessment ──────────────────────────────────────────

    def self_assess(self, parcel_id: str, new_value: float) -> HarbergerParcel:
        """Owner updates the declared (self-assessed) value of a parcel.

        Both ``declared_value`` and ``assessed_for_lvt`` are updated to the
        new value.  The owner's balance-sheet land value is adjusted.

        Args:
            parcel_id:  The parcel being re-assessed.
            new_value:  New Harberger declared value.

        Raises:
            ValueError: If the new value is negative.
        """
        if new_value < 0:
            raise ValueError(
                f"Declared value cannot be negative: {new_value}"
            )

        parcel = self.get_parcel(parcel_id)
        old_value = parcel.declared_value
        delta = new_value - old_value

        parcel.declared_value = new_value
        parcel.assessed_for_lvt = new_value

        # Adjust owner's balance sheet
        bs = self.ledger.get_balance(parcel.owner)
        bs.land_value += delta

        return parcel

    # ── Bidding ───────────────────────────────────────────────────

    def post_bid(self, parcel_id: str, bidder_id: str,
                 bid_price: Optional[float] = None) -> Bid:
        """Post a bid to purchase a parcel.

        The bid price defaults to the parcel's current declared value but may
        be set higher (minimum = declared value).  The buyer's bond (a fraction
        of the bid price) is immediately transferred to the market escrow
        account.

        Args:
            parcel_id:  The parcel to bid on.
            bidder_id:  Entity ID of the prospective buyer.
            bid_price:  Offered price (must be ≥ declared value).
                        Defaults to the parcel's current declared value.

        Returns:
            The newly created Bid.

        Raises:
            ValueError: If the bidder is the owner, the bid price is below
                        the declared value, or the bidder lacks funds for
                        the bond.
        """
        parcel = self.get_parcel(parcel_id)

        if bidder_id == parcel.owner:
            raise ValueError("Owner cannot bid on their own parcel")
        if not self.ledger.entity_exists(bidder_id):
            raise ValueError(f"Bidder '{bidder_id}' is not registered")

        if bid_price is None:
            bid_price = parcel.declared_value
        if bid_price < parcel.declared_value:
            raise ValueError(
                f"Bid price ({bid_price}) must be ≥ declared value "
                f"({parcel.declared_value})"
            )

        bond = self._bond_amount(bid_price)

        # Verify buyer can afford the bond
        buyer_bs = self.ledger.get_balance(bidder_id)
        if buyer_bs.cash < bond:
            raise ValueError(
                f"Bidder '{bidder_id}' has insufficient cash "
                f"({buyer_bs.cash:.2f}) for bond ({bond:.2f})"
            )

        # Create the bid record
        bid = Bid(
            bid_id=str(uuid.uuid4())[:12],
            parcel_id=parcel_id,
            bidder_id=bidder_id,
            bid_price=bid_price,
            step_posted=self.current_day,
        )
        parcel.bids.append(bid)

        # Lock bond in escrow
        self.ledger.transfer(
            from_id=bidder_id,
            to_id=self.escrow_account,
            mechanism='harberger_bond',
            amount=bond,
            description=f"Bond for bid '{bid.bid_id}' on parcel '{parcel_id}'",
        )

        return bid

    def accept_bid(self, parcel_id: str, bid_id: str) -> dict:
        """Owner accepts a bid → forced sale.

        The bond held in escrow is released to the seller as the sale
        proceeds.  Ownership, balance-sheet land values, and the parcel's
        declared value are updated accordingly.

        Args:
            parcel_id:  The parcel being sold.
            bid_id:     The ID of the bid being accepted.

        Returns:
            A summary dict with keys: parcel_id, buyer, seller,
            sale_price, bid_id.

        Raises:
            ValueError: If the bid is not in PENDING status.
        """
        parcel = self.get_parcel(parcel_id)
        bid = self._find_bid(parcel, bid_id)

        if bid.status != BidStatus.PENDING:
            raise ValueError(
                f"Bid '{bid_id}' is not pending (status: {bid.status.name})"
            )

        old_owner = parcel.owner
        buyer = bid.bidder_id
        sale_price = bid.bid_price
        bond = self._bond_amount(sale_price)

        # Mark accepted
        bid.status = BidStatus.ACCEPTED

        # --- Ledger transfers ---

        # 1. Bond from escrow → seller (sale proceeds)
        self.ledger.transfer(
            from_id=self.escrow_account,
            to_id=old_owner,
            mechanism='harberger_sale',
            amount=bond,
            description=f"Forced sale: parcel '{parcel_id}' → '{buyer}'",
        )

        # --- Balance-sheet updates ---
        old_bs = self.ledger.get_balance(old_owner)
        old_bs.land_value -= parcel.declared_value
        old_bs.property_count -= 1

        new_bs = self.ledger.get_balance(buyer)
        new_bs.land_value += sale_price
        new_bs.property_count += 1

        # --- Ownership transfer ---
        parcel.owner = buyer
        parcel.declared_value = sale_price
        parcel.assessed_for_lvt = sale_price

        return {
            'parcel_id': parcel_id,
            'bid_id': bid_id,
            'buyer': buyer,
            'seller': old_owner,
            'sale_price': sale_price,
        }

    def refuse_bid(self, parcel_id: str, bid_id: str) -> dict:
        """Owner refuses a pending bid.

        Two phases (Option Premium):
          * Free window  (≤14 days) — No penalty.  Bond returned to buyer.
            Tax basis (assessed_for_lvt) increases to the bid price.
          * Penalty phase (>14 days) — Owner pays 15 % of the bid price to
            the buyer.  Bond returned to buyer.

        Args:
            parcel_id:  The parcel the bid is on.
            bid_id:     The bid being refused.

        Returns:
            A summary dict with keys: parcel_id, bidder, refusal_type,
            days_elapsed, penalty.

        Raises:
            ValueError: If the bid is not PENDING, or the owner cannot
                        afford the penalty (phase 2).
        """
        parcel = self.get_parcel(parcel_id)
        bid = self._find_bid(parcel, bid_id)

        if bid.status != BidStatus.PENDING:
            raise ValueError(
                f"Bid '{bid_id}' is not pending (status: {bid.status.name})"
            )

        days_elapsed = self.current_day - bid.step_posted
        bond = self._bond_amount(bid.bid_price)
        in_penalty_phase = days_elapsed > FREE_WINDOW_DAYS

        # Always return the bond
        self.ledger.transfer(
            from_id=self.escrow_account,
            to_id=bid.bidder_id,
            mechanism='harberger_bond_refund',
            amount=bond,
            description=f"Bond returned for refused bid '{bid_id}'",
        )

        if in_penalty_phase:
            # --- Phase 2: Penalty refusal ---
            penalty = bid.bid_price * PENALTY_RATE

            seller_bs = self.ledger.get_balance(parcel.owner)
            if seller_bs.cash < penalty:
                raise ValueError(
                    f"Owner '{parcel.owner}' has insufficient cash "
                    f"({seller_bs.cash:.2f}) for penalty ({penalty:.2f})"
                )

            self.ledger.transfer(
                from_id=parcel.owner,
                to_id=bid.bidder_id,
                mechanism='harberger_refusal_penalty',
                amount=penalty,
                description=f"Refusal penalty (15 %) on bid '{bid_id}'",
            )

            bid.status = BidStatus.REFUSED_PENALTY
            result = {
                'parcel_id': parcel_id,
                'bid_id': bid_id,
                'bidder': bid.bidder_id,
                'refusal_type': 'penalty',
                'days_elapsed': days_elapsed,
                'penalty': penalty,
            }
        else:
            # --- Phase 1: Free refusal ---
            # Tax basis increases to the bid price (deters under-assessment)
            parcel.assessed_for_lvt = max(parcel.assessed_for_lvt, bid.bid_price)

            bid.status = BidStatus.REFUSED_FREE
            result = {
                'parcel_id': parcel_id,
                'bid_id': bid_id,
                'bidder': bid.bidder_id,
                'refusal_type': 'free',
                'days_elapsed': days_elapsed,
                'penalty': 0.0,
            }

        return result

    # ── Time Advancement ──────────────────────────────────────────

    def advance_day(self) -> list[dict]:
        """Advance the simulation clock by one day.

        Processes bid aging — any bid exceeding MAX_BID_DURATION is
        automatically expired and its bond returned to the bidder.

        Returns:
            A list of expiry-event dicts for any bids that were auto-expired.
        """
        self.current_day += 1
        expired: list[dict] = []

        for parcel in self.parcels.values():
            for bid in list(parcel.active_bids):
                age = self.current_day - bid.step_posted
                if age > MAX_BID_DURATION:
                    bid.status = BidStatus.EXPIRED
                    bond = self._bond_amount(bid.bid_price)

                    self.ledger.transfer(
                        from_id=self.escrow_account,
                        to_id=bid.bidder_id,
                        mechanism='harberger_bond_refund',
                        amount=bond,
                        description=f"Bond returned for expired bid "
                                    f"'{bid.bid_id}' on '{parcel.parcel_id}'",
                    )

                    expired.append({
                        'type': 'expired',
                        'parcel_id': parcel.parcel_id,
                        'bid_id': bid.bid_id,
                        'bidder': bid.bidder_id,
                        'bid_price': bid.bid_price,
                    })

        return expired

    # ── LVT Assessment ────────────────────────────────────────────

    def assess_lvt(self, collector: str = 'national_trust') -> dict:
        """Assess and collect Land Value Tax on all parcels.

        For each parcel the owner is charged::
            LVT due = lvt_rate × assessed_for_lvt

        If the owner has insufficient cash, the shortfall is recorded as
        ``outstanding_liability`` on their balance sheet.

        Args:
            collector:  Entity ID that receives the LVT payments.
                        Defaults to ``'national_trust'``.

        Returns:
            A summary dict with keys:
              * total_lvt       — total LVT collected this round
              * total_due       — total LVT billed
              * total_shortfall — aggregate unpaid LVT
              * parcels         — per-parcel assessment details
        """
        # Ensure the collector exists; fall back to escrow account
        if not self.ledger.entity_exists(collector):
            collector = self.escrow_account

        total_lvt = 0.0
        total_due = 0.0
        total_shortfall = 0.0
        parcels_assessed: list[dict] = []

        for parcel_id, parcel in self.parcels.items():
            due = self.lvt_rate * parcel.assessed_for_lvt
            total_due += due

            if due <= 0:
                parcels_assessed.append({
                    'parcel_id': parcel_id,
                    'owner': parcel.owner,
                    'assessed_value': parcel.assessed_for_lvt,
                    'lvt_due': 0.0,
                    'lvt_paid': 0.0,
                    'shortfall': 0.0,
                })
                continue

            owner_bs = self.ledger.get_balance(parcel.owner)
            paid = min(due, max(0.0, owner_bs.cash))
            shortfall = due - paid

            if paid > 0:
                self.ledger.transfer(
                    from_id=parcel.owner,
                    to_id=collector,
                    mechanism='lvt',
                    amount=paid,
                    description=f"LVT on parcel '{parcel_id}' "
                                f"(rate={self.lvt_rate})",
                )

            if shortfall > 0:
                owner_bs.outstanding_liability += shortfall
                total_shortfall += shortfall

            total_lvt += paid

            parcels_assessed.append({
                'parcel_id': parcel_id,
                'owner': parcel.owner,
                'assessed_value': parcel.assessed_for_lvt,
                'lvt_due': round(due, 4),
                'lvt_paid': round(paid, 4),
                'shortfall': round(shortfall, 4),
            })

        return {
            'total_lvt': round(total_lvt, 4),
            'total_due': round(total_due, 4),
            'total_shortfall': round(total_shortfall, 4),
            'parcels': parcels_assessed,
        }

    # ── State ─────────────────────────────────────────────────────

    def summary(self) -> dict:
        """Return a human-readable snapshot of the entire market."""
        return {
            'current_day': self.current_day,
            'lvt_rate': self.lvt_rate,
            'escrow_balance': round(
                self.ledger.get_balance(self.escrow_account).cash, 4
            ),
            'parcel_count': len(self.parcels),
            'parcels': {pid: p.to_dict() for pid, p in self.parcels.items()},
        }


# ═══════════════════════════════════════════════════════════════════════
#  Demonstration
# ═══════════════════════════════════════════════════════════════════════

def demo():
    """Run a complete walk-through of the Harberger property market.

    Demonstrates:
      1. Ledger setup & entity registration
      2. Parcel creation with Harberger self-assessment
      3. Self-assessment (owner changes declared value)
      4. Bid posting & forced purchase (acceptance)
      5. Bid posting & Option Premium refusal (free window + penalty phase)
      6. LVT assessment across all parcels
      7. Comprehensive state snapshot
    """
    print("═" * 72)
    print("HARBERGER PROPERTY MARKET — DEMONSTRATION")
    print("═" * 72)

    # ─── 1. Setup ─────────────────────────────────────────────────
    print("\n─── 1. Setup: Ledger & Entities ───────────────────────\n")

    ledger = LedgerEngine(step_log=False)

    ledger.register_entity('alice', EntityType.CITIZEN,
                           compact_id='alpha', initial_cash=200_000.0)
    ledger.register_entity('bob', EntityType.CITIZEN,
                           compact_id='alpha', initial_cash=150_000.0)
    ledger.register_entity('carol', EntityType.CITIZEN,
                           compact_id='alpha', initial_cash=100_000.0)
    ledger.register_entity('national_trust', EntityType.TRUST, initial_cash=0.0)

    print("  ✓ Alice   (citizen)    $200,000")
    print("  ✓ Bob     (citizen)    $150,000")
    print("  ✓ Carol   (citizen)    $100,000")
    print("  ✓ National Trust")

    # ─── 2. Create Market & Parcels ──────────────────────────────
    print("\n─── 2. Parcel Registration ─────────────────────────────\n")

    market = HarbergerMarket(ledger, lvt_rate=0.05, bond_fraction=1.0)

    parcel_a = market.register_parcel('parcel_a', 'alice', 50_000.0)
    parcel_b = market.register_parcel('parcel_b', 'bob', 30_000.0)
    parcel_c = market.register_parcel('parcel_c', 'carol', 20_000.0)

    print(f"  Parcel A — Alice   declares $50,000")
    print(f"  Parcel B — Bob     declares $30,000")
    print(f"  Parcel C — Carol   declares $20,000")

    alice_bs = ledger.get_balance('alice')
    print(f"  Alice land holdings: ${alice_bs.land_value:.2f} "
          f"({alice_bs.property_count} parcel(s))")

    # ─── 3. Self-Assessment ──────────────────────────────────────
    print("\n─── 3. Self-Assessment ────────────────────────────────\n")

    market.self_assess('parcel_a', 60_000.0)
    pa = market.get_parcel('parcel_a')
    print(f"  Alice re-assesses Parcel A: $50,000 → ${pa.declared_value:,.0f}")
    print(f"  Alice land value now: ${ledger.get_balance('alice').land_value:,.0f}")
    assert pa.declared_value == 60_000.0
    assert pa.assessed_for_lvt == 60_000.0
    print("  ✓ Declared value and LVT basis both updated")

    # ─── 4. Forced Purchase (Accept Bid) ─────────────────────────
    print("\n─── 4. Forced Purchase: Bid & Accept ───────────────────\n")

    ledger.begin_step()
    print(f"  Step {ledger.step}: Bob bids on Parcel A (declared: ${pa.declared_value:,.0f})")
    bid1 = market.post_bid('parcel_a', 'bob')
    print(f"    Bid '{bid1.bid_id}' posted: ${bid1.bid_price:,.0f}")
    print(f"    Bond locked: ${ledger.get_balance('bob').cash:,.2f} "
          f"(was $8,000)")
    print(f"    Escrow holds: ${ledger.get_balance('harberger_escrow').cash:,.2f}")

    # Advance time past free window to show penalty isn't needed on accept
    market.advance_day()  # day 1
    print(f"  Day {market.current_day}: Alice accepts the bid")

    sale = market.accept_bid('parcel_a', bid1.bid_id)
    print(f"    ✓ Forced sale: {sale['seller']} → {sale['buyer']}")
    print(f"      Price: ${sale['sale_price']:,.2f}")
    print(f"    Alice cash: ${ledger.get_balance('alice').cash:,.2f} "
          f"(+${sale['sale_price']:,.2f})")
    print(f"    Bob   cash: ${ledger.get_balance('bob').cash:,.2f}")
    print(f"    Parcel A owner: {market.get_parcel('parcel_a').owner}")
    print(f"    Escrow: ${ledger.get_balance('harberger_escrow').cash:,.2f}")

    ledger.close_step()

    # ─── 5. Option Premium: Free Refusal ─────────────────────────
    print("\n─── 5. Option Premium — Free Refusal (≤14 days) ─────────\n")

    # Carol now owns Parcel C. Bob bids on it. Carol refuses in free window.
    pa_c = market.get_parcel('parcel_c')
    print(f"  Parcel C owner: {pa_c.owner}, declared: ${pa_c.declared_value:,.0f}")

    ledger.begin_step()
    bid2 = market.post_bid('parcel_c', 'bob', bid_price=25_000.0)
    print(f"  Bob bids $25,000 on Parcel C (declared: ${pa_c.declared_value:,.0f})")
    print(f"  Bob cash after bond: ${ledger.get_balance('bob').cash:,.2f}")

    # Advance a few days (still within free window)
    for _ in range(5):
        market.advance_day()
    print(f"  Day {market.current_day}: Carol refuses (days elapsed = "
          f"{market.current_day - bid2.step_posted})")

    refusal1 = market.refuse_bid('parcel_c', bid2.bid_id)
    print(f"    Refusal type: {refusal1['refusal_type']}")
    print(f"    Penalty: ${refusal1['penalty']:,.2f}")
    # Check tax basis increased to bid price
    pc_after = market.get_parcel('parcel_c')
    print(f"    Parcel C assessed_for_lvt: ${pc_after.assessed_for_lvt:,.0f} "
          f"(was ${pc_after.declared_value:,.0f})")
    print(f"    Bob's cash after bond refund: "
          f"${ledger.get_balance('bob').cash:,.2f}")
    ledger.close_step()

    # ─── 6. Option Premium: Penalty Refusal ──────────────────────
    print("\n─── 6. Option Premium — Penalty Refusal (>14 days) ──────\n")

    # Carol re-declares at her new basis
    market.self_assess('parcel_c', pc_after.assessed_for_lvt)
    print(f"  Carol updates Parcel C to assessed value: "
          f"${pc_after.assessed_for_lvt:,.0f}")

    ledger.begin_step()
    bid3 = market.post_bid('parcel_c', 'alice')
    print(f"  Alice bids ${bid3.bid_price:,.0f} on Parcel C")
    print(f"  Alice cash after bond: ${ledger.get_balance('alice').cash:,.2f}")

    # Advance past the free window
    for _ in range(15):
        market.advance_day()
    print(f"  Day {market.current_day}: Carol refuses (days elapsed = "
          f"{market.current_day - bid3.step_posted})")

    refusal2 = market.refuse_bid('parcel_c', bid3.bid_id)
    print(f"    Refusal type: {refusal2['refusal_type']}")
    print(f"    Penalty: ${refusal2['penalty']:,.2f} (15 % of ${bid3.bid_price:,.0f})")
    print(f"    Carol  cash after penalty: "
          f"${ledger.get_balance('carol').cash:,.2f}")
    print(f"    Alice  cash after bond + penalty: "
          f"${ledger.get_balance('alice').cash:,.2f}")
    ledger.close_step()

    # ─── 7. LVT Assessment ─────────────────────────────────────
    print("\n─── 7. Land Value Tax Assessment ───────────────────────\n")

    # Advance time to the next "year" (just a clean step for LVT)
    ledger.begin_step()
    lvt_result = market.assess_lvt(collector='national_trust')
    print(f"  LVT rate: {market.lvt_rate * 100:.1f} %")
    print(f"  Total LVT billed:  ${lvt_result['total_due']:,.2f}")
    print(f"  Total LVT paid:    ${lvt_result['total_lvt']:,.2f}")
    print(f"  Total shortfall:   ${lvt_result['total_shortfall']:,.2f}")

    for p in lvt_result['parcels']:
        print(f"    {p['parcel_id']:10s} | "
              f"assessed ${p['assessed_value']:>8,.0f} | "
              f"due ${p['lvt_due']:>7,.2f} | "
              f"paid ${p['lvt_paid']:>7,.2f} | "
              f"short ${p['shortfall']:>7,.2f}")

    ledger.close_step()
    print(f"\n  National Trust balance: "
          f"${ledger.get_balance('national_trust').cash:,.2f}")

    # ─── 8. Summary ──────────────────────────────────────────────
    print("\n─── 8. Market Summary ──────────────────────────────────\n")

    summary = market.summary()
    print(f"  Simulation day: {summary['current_day']}")
    print(f"  Parcels:        {summary['parcel_count']}")
    print(f"  Escrow balance: ${summary['escrow_balance']:,.2f}")
    print()

    for pid, pdata in summary['parcels'].items():
        print(f"  {pid}:")
        print(f"    Owner:     {pdata['owner']}")
        print(f"    Declared:  ${pdata['declared_value']:>8,.2f}")
        print(f"    LVT basis: ${pdata['assessed_for_lvt']:>8,.2f}")
        if pdata['active_bids']:
            for b in pdata['active_bids']:
                print(f"    Active bid: {b['bidder_id']} @ ${b['bid_price']:,.2f}")
        print()

    # Final state
    print("─" * 72)
    print("ENTITY BALANCE SHEETS")
    print("─" * 72)
    for eid, bs in ledger.balances.items():
        if eid == 'harberger_escrow':
            continue
        print(f"  {eid:20s} | cash ${bs.cash:>8,.2f} | "
              f"land ${bs.land_value:>8,.2f} | "
              f"props {bs.property_count} | "
              f"net ${bs.net_worth:>9,.2f}")

    # Verify zero-sum for every step
    print("\n─" * 72)
    print("STEP INTEGRITY CHECK")
    print("─" * 72)
    all_ok = True
    for m in ledger.step_metrics:
        ok = m['balanced']
        all_ok = all_ok and ok
        print(f"  Step {m['step']:2d}: "
              f"{'✓ BALANCED' if ok else '✗ IMBALANCE!'} "
              f"(imbalance={m['imbalance']:.6f}, "
              f"transfers={m['transfer_count']})")
    print(f"\n  {'✅ All steps balanced.' if all_ok else '❌ Imbalance detected!'}")
    print(f"  Total transfers: {len(ledger.transfers)}")
    print(f"  Total entries:   {len(ledger.entries)}")
    print(f"\n{'═' * 72}")
    print("DEMO COMPLETE")
    print(f"{'═' * 72}")


# ─── Run ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    demo()
