#!/usr/bin/env python3
"""18 tests for Harberger bridge adapter (wraps existing src/mechanics/harberger.py)."""
import sys, os, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np

from harberger_bridge import create_harberger_market, HARBERGER_ESCROW
from src.core.ledger import LedgerEngine, EntityType
from src.mechanics.harberger import HarbergerMarket as CanonicalMarket
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS

PASS, FAIL = 0, 0
def check(desc, ok):
    global PASS, FAIL
    if ok: PASS += 1; print(f'  ✅ {desc}')
    else: FAIL += 1; print(f'  ❌ {desc}')

# ─── Test 1: Market initialization ──────────────────────────────────

print('=== 1. Market Initialization ===')
w, r, b = gen_population(42)
wland = {ww['id']: ww['land'] for ww in w}
rland = {rr['id']: rr['land'] for rr in r}
bland = {bb['id']: np.random.RandomState(42).uniform(50000, 200000) for bb in b}
config = {'lvt_rate': 0.03}
adapter = create_harberger_market(config, w, r, b, wland, rland, bland)
check('Adapter created', adapter is not None)
check(f'{len(adapter.parcels)} parcels registered', len(adapter.parcels) == len(w) + len(r) + len(b))
check('Parcel IDs correct', 'land_w000' in adapter.parcels)

# ─── Test 2: Self-assessment via underlying module ─────────────────

print('\n=== 2. Self-Assessment ===')
# Use the canonical module directly
ledger = LedgerEngine(step_log=False)
ledger.register_entity('owner', EntityType.CITIZEN, initial_cash=500000)
ledger.register_entity(HARBERGER_ESCROW, EntityType.SYSTEM, initial_cash=0)
market = CanonicalMarket(ledger, lvt_rate=0.03/12, escrow_account=HARBERGER_ESCROW)
market.register_parcel('p1', 'owner', 50000)
before = market.get_parcel('p1').declared_value
market.self_assess('p1', 75000)
after = market.get_parcel('p1').declared_value
check('Self-assessment updates value', after == 75000)
check('Assessed for LVT also updated', market.get_parcel('p1').assessed_for_lvt == 75000)

# ─── Test 3: Bidding ───────────────────────────────────────────────

print('\n=== 3. Bidding ===')
ledger2 = LedgerEngine(step_log=False)
ledger2.register_entity('owner', EntityType.CITIZEN, initial_cash=500000)
ledger2.register_entity('bidder', EntityType.CITIZEN, initial_cash=500000)
ledger2.register_entity(HARBERGER_ESCROW, EntityType.SYSTEM, initial_cash=0)
m2 = CanonicalMarket(ledger2, lvt_rate=0.03/12, escrow_account=HARBERGER_ESCROW, bond_fraction=0.1)
m2.register_parcel('p2', 'owner', 100000)
m2.advance_day()
bid = m2.post_bid('p2', 'bidder')
check('Bid posted at declared value', bid.bid_price == 100000)
check('Bond locked', ledger2.get_balance('bidder').cash < 500000)

# ─── Test 4: Forced Sale ───────────────────────────────────────────

print('\n=== 4. Forced Sale ===')
sale = m2.accept_bid('p2', bid.bid_id)
check('Ownership transferred', m2.get_parcel('p2').owner == 'bidder')
check('Declared value updated to sale price', m2.get_parcel('p2').declared_value == 100000)

# ─── Test 5: Option Premium (free refusal) ─────────────────────────

print('\n=== 5. Option Premium ===')
ledger3 = LedgerEngine(step_log=False)
ledger3.register_entity('owner', EntityType.CITIZEN, initial_cash=500000)
ledger3.register_entity('bidder', EntityType.CITIZEN, initial_cash=500000)
ledger3.register_entity(HARBERGER_ESCROW, EntityType.SYSTEM, initial_cash=0)
m3 = CanonicalMarket(ledger3, lvt_rate=0.03/12, escrow_account=HARBERGER_ESCROW)
m3.register_parcel('p3', 'owner', 50000)
bid3 = m3.post_bid('p3', 'bidder', bid_price=60000)
m3.advance_day()  # Within free window (14 days)
refusal = m3.refuse_bid('p3', bid3.bid_id)
check('Free refusal within 14 days', refusal['refusal_type'] == 'free')
check('Assessed LVT bumped to bid price', m3.get_parcel('p3').assessed_for_lvt >= 60000)

# ─── Test 6: LVT Collection ────────────────────────────────────────

print('\n=== 6. LVT Collection ===')
ledger4 = LedgerEngine(step_log=False)
ledger4.register_entity('owner', EntityType.CITIZEN, initial_cash=1000000)
ledger4.register_entity('trust', EntityType.TRUST, initial_cash=0)
ledger4.register_entity(HARBERGER_ESCROW, EntityType.SYSTEM, initial_cash=0)
m4 = CanonicalMarket(ledger4, lvt_rate=0.03/12, escrow_account=HARBERGER_ESCROW)
m4.register_parcel('p4', 'owner', 100000)
result = m4.assess_lvt(collector='trust')
# LVT = 0.03/12 * 100000 = 250
check('LVT collected correctly', abs(result['total_lvt'] - 250) < 1)
check('Collector receives funds', ledger4.get_balance('trust').cash > 0)

# ─── Test 7: Phase 8 Integration ───────────────────────────────────

print('\n=== 7. Phase 8 Integration ===')
cfg = PHASE8_CONFIGS['Pure_Georgist'].copy()
cfg['use_harberger'] = True
try:
    w7, r7, b7 = gen_population(42)
    res = run_phase8([dict(d) for d in w7], [dict(d) for d in r7], [dict(d) for d in b7], 42, cfg)
    check('480 steps completed', res['steps'] == 480)
    check('Valid gini', 0 <= res['gini'] <= 1)
except Exception as e:
    check(f'Phase 8 integration: {e}', False)

# ─── Test 8: Aggregate Effect ──────────────────────────────────────

print('\n=== 8. Aggregate Effect ===')
cfg_off = PHASE8_CONFIGS['Laissez_Faire'].copy()
cfg_on = copy.deepcopy(cfg_off)
cfg_on['use_harberger'] = True
w8, r8, b8 = gen_population(1)
res_off = run_phase8(w8, r8, b8, 1, cfg_off)
w8b, r8b, b8b = gen_population(1)
res_on = run_phase8([dict(d) for d in w8b], [dict(d) for d in r8b], [dict(d) for d in b8b], 1, cfg_on)
diff = abs(res_on['w_mean'] - res_off['w_mean'])
check(f'Harberger changes mean wealth (diff=\${diff:>,.0f})', diff > 100)
check('Both complete 480 steps', res_on['steps'] == 480 and res_off['steps'] == 480)

# ─── Summary ────────────────────────────────────────────────────────

total = PASS + FAIL
print(f'\nRESULTS: {PASS} passed, {FAIL} failed out of {total}')
sys.exit(0 if FAIL == 0 else 1)
