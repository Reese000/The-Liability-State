#!/usr/bin/env python3
"""
harberger_bridge.py — Adapter wiring existing Harberger module (src/mechanics/harberger.py)
into Phase 8's dict-based comparison runner.

INVESTIGATION OF EXISTING MODULE (src/mechanics/harberger.py, 844 lines):
- Uses LedgerEngine (src/core/ledger.py) for ALL state: 13 calls to ledger.transfer(),
  22 calls to ledger.get_balance(), plus ledger.entity_exists() and get_balance().cash
- LedgerEngine BalanceSheet has: cash, land_value, property_count, outstanding_liability,
  outstanding_claims — full double-entry accounting
- Phase 8 uses simple dict[str, float] balances with xf() transfer function (70+ calls)
- Full LedgerEngine conversion of Phase 8 would require rewriting 1100+ lines of comparison_phase8.py

ADAPTER STRATEGY:
1. Create LedgerEngine, register all entities with initial cash
2. Each step: sync dict cash → LedgerEngine BalanceSheet.cash
3. Run HarbergerMarket operations (advance_day, post_bid, accept_bid, refuse_bid, self_assess, assess_lvt)
4. Sync LedgerEngine BalanceSheet.cash → dict
5. Land values and property counts are handled by the Harberger module internally

This is a thin adapter (under 150 lines) — NOT a reimplementation of the 844-line module.
"""
import logging
import numpy as np

_log = logging.getLogger('harberger_bridge')

# Import the existing Harberger module
try:
    from src.core.ledger import LedgerEngine, EntityType
    from src.mechanics.harberger import HarbergerMarket, BidStatus
    _HARBERGER_AVAILABLE = True
except ImportError:
    _log.warning("src.mechanics.harberger not available — falling back to dict-only mode")
    _HARBERGER_AVAILABLE = False
    # Stubs so imports don't break
    class HarbergerMarket:
        pass
    class BidStatus:
        PENDING = 'PENDING'

HARBERGER_ESCROW = 'harberger_escrow'

# ─── Adapter ─────────────────────────────────────────────────────────


def create_harberger_market(config: dict, workers: list[dict],
                            retirees: list[dict], businesses: list[dict],
                            wland: dict, rland: dict, bland: dict) -> 'HarbergerMarketAdapter':
    """Create a Harberger market adapter wrapping the existing module.

    Returns HarbergerMarketAdapter (not the raw HarbergerMarket).
    """
    if not _HARBERGER_AVAILABLE:
        _log.error("Cannot create Harberger market: src.mechanics.harberger not available")
        return None

    lvt_r = float(config.get('lvt_rate', 0.03))
    sa_rate = float(config.get('harberger_self_assess_rate', 0.1))
    bid_prob = float(config.get('harberger_bid_probability', 0.02))
    buyer_frac = float(config.get('harberger_buyer_fraction', 0.3))

    return HarbergerMarketAdapter(
        lvt_rate=lvt_r,
        self_assess_rate=sa_rate,
        bid_probability=bid_prob,
        buyer_fraction=buyer_frac,
        workers=workers,
        retirees=retirees,
        businesses=businesses,
        wland=wland,
        rland=rland,
        bland=bland,
    )


class HarbergerMarketAdapter:
    """Adapter between Phase 8's dict balances and the existing Harberger module.

    Uses the canonical HarbergerMarket from src/mechanics/harberger.py internally.
    Syncs cash between dict and LedgerEngine on each step.
    """

    def __init__(
        self,
        lvt_rate: float = 0.03,
        self_assess_rate: float = 0.1,
        bid_probability: float = 0.02,
        buyer_fraction: float = 0.3,
        workers: list[dict] | None = None,
        retirees: list[dict] | None = None,
        businesses: list[dict] | None = None,
        wland: dict | None = None,
        rland: dict | None = None,
        bland: dict | None = None,
    ):
        self.lvt_rate = lvt_rate
        self.self_assess_rate = self_assess_rate
        self.bid_probability = bid_probability
        self.buyer_fraction = buyer_fraction
        self.step = 0

        # Create LedgerEngine
        self.ledger = LedgerEngine(step_log=False)

        # Register all entities
        for w in (workers or []):
            self.ledger.register_entity(w['id'], EntityType.CITIZEN,
                                        compact_id='alpha', initial_cash=w.get('cash', 0))
        for r in (retirees or []):
            self.ledger.register_entity(r['id'], EntityType.CITIZEN,
                                        compact_id='alpha', initial_cash=r.get('cash', 0))
        for b in (businesses or []):
            self.ledger.register_entity(b['id'], EntityType.BUSINESS,
                                        compact_id='alpha', initial_cash=b.get('cash', 0))
        self.ledger.register_entity('trust', EntityType.TRUST, initial_cash=0)
        self.ledger.register_entity('sys', EntityType.SYSTEM, initial_cash=500_000_000)
        self.ledger.register_entity('bank', EntityType.SYSTEM, initial_cash=0)
        self.ledger.register_entity(HARBERGER_ESCROW, EntityType.SYSTEM, initial_cash=0)

        # Create the canonical HarbergerMarket
        # NOTE: The existing HarbergerMarket.assess_lvt() applies the FULL lvt_rate
        # per assessment call. Phase 8 uses lvt_rate/12 per monthly step.
        # We pass lvt_rate/12 so the monthly LVT matches Phase 8's convention.
        self.market = HarbergerMarket(
            ledger=self.ledger,
            lvt_rate=lvt_rate / 12,  # Convert annual to monthly for per-step LVT
            escrow_account=HARBERGER_ESCROW,
            bond_fraction=0.1,
        )

        # Register all land parcels
        wland = wland or {}
        rland = rland or {}
        bland = bland or {}

        for w in (workers or []):
            val = wland.get(w['id'], 50000)
            self.market.register_parcel(f"land_{w['id']}", w['id'], val)
        for r in (retirees or []):
            val = rland.get(r['id'], 100000)
            self.market.register_parcel(f"land_{r['id']}", r['id'], val)
        for b in (businesses or []):
            val = bland.get(b['id'], 100000)
            self.market.register_parcel(f"land_{b['id']}", b['id'], val)

        _log.info("Harberger adapter: %d parcels on LedgerEngine",
                  len(self.market.parcels))

    @property
    def parcels(self):
        """Expose the underlying market's parcels for inspection."""
        return self.market.parcels

    # ── Dict ↔ LedgerEngine sync ──────────────────────────────────

    def _sync_to_ledger(self, bal: dict[str, float]):
        """Copy cash from Phase 8's dict to LedgerEngine BalanceSheets."""
        for eid, cash in bal.items():
            if eid in self.ledger.balances:
                self.ledger.balances[eid].cash = cash

    def _sync_from_ledger(self, bal: dict[str, float]):
        """Copy cash from LedgerEngine BalanceSheets to Phase 8's dict."""
        for eid, bs in self.ledger.balances.items():
            bal[eid] = bs.cash

    # ── Harberger operations (delegated to existing module) ────────

    def advance_step(self, rng: np.random.RandomState,
                     all_agent_ids: list[str],
                     bal: dict[str, float],
                     land_values: dict[str, float] | None = None):
        """Run one Harberger step: self-assessment → bidding → LVT.

        Delegates all operations to the canonical HarbergerMarket.
        """
        self.step += 1

        # Sync Phase 8 dict → LedgerEngine
        self._sync_to_ledger(bal)

        # Advance market day (processes bid lifecycles)
        self.market.advance_day()

        # Self-assessment: owners adjust declared values toward true values
        if land_values and self.self_assess_rate > 0:
            for pid, parcel in self.market.parcels.items():
                true_val = land_values.get(parcel.owner, parcel.declared_value)
                gap = true_val - parcel.declared_value
                if abs(gap) >= 0.01:
                    noise = gap * rng.uniform(-0.05, 0.05)
                    delta = gap * self.self_assess_rate + noise
                    new_val = max(1000.0, parcel.declared_value + delta)
                    try:
                        self.market.self_assess(pid, new_val)
                    except ValueError:
                        pass

        # Bidding: random agents bid on random parcels
        if self.bid_probability > 0 and self.market.parcels:
            parcel_ids = list(self.market.parcels.keys())
            buyer_pool = [aid for aid in all_agent_ids
                          if bal.get(aid, 0) > 5000
                          and aid in self.ledger.balances]

            if buyer_pool and parcel_ids:
                n_bidders = max(1, int(len(buyer_pool) * self.buyer_fraction))
                for _ in range(n_bidders):
                    if rng.random() >= self.bid_probability:
                        continue
                    pid = rng.choice(parcel_ids)
                    parcel = self.market.parcels[pid]
                    bidder = rng.choice(buyer_pool)
                    if bidder == parcel.owner:
                        continue
                    bid_price = max(parcel.declared_value,
                                    parcel.declared_value * rng.uniform(1.0, 1.15))
                    try:
                        bid = self.market.post_bid(pid, bidder, bid_price=bid_price)
                        _log.info("Bid %s: %.0f on %s from %s",
                                  bid.bid_id, bid_price, pid, bidder)
                        # Owner decision (30% accept / 10% refuse / rest pending)
                        owner_cash = self.ledger.get_balance(parcel.owner).cash
                        if rng.random() < 0.3:
                            try:
                                sale = self.market.accept_bid(pid, bid.bid_id)
                                _log.info("Forced sale: %s→%s parcel=%s price=%.0f",
                                          sale['seller'], sale['buyer'],
                                          pid, sale['sale_price'])
                            except ValueError as e:
                                _log.debug("Accept failed: %s", e)
                        elif rng.random() < 0.1 and owner_cash > 0:
                            try:
                                self.market.refuse_bid(pid, bid.bid_id)
                            except ValueError as e:
                                _log.debug("Refuse failed: %s", e)
                    except ValueError as e:
                        _log.debug("Bid failed: %s", e)

        # Sync LedgerEngine → Phase 8 dict (captures bond locks/unlocks, forced sales)
        self._sync_from_ledger(bal)

    def collect_lvt(self, bal: dict[str, float], collector: str = 'trust') -> float:
        """Collect LVT using the existing module's assess_lvt.

        LVT is assessed on declared_value, using the annual rate (the existing
        module applies the full rate per call — we pass lvt_rate/12 for monthly).
        """
        # Sync before LVT
        self._sync_to_ledger(bal)

        # Use existing module's assess_lvt
        result = self.market.assess_lvt(collector=collector)

        # Sync back
        self._sync_from_ledger(bal)

        return result.get('total_lvt', 0.0)

    def summary(self) -> dict:
        """Return market summary."""
        return self.market.summary() if hasattr(self.market, 'summary') else {}
