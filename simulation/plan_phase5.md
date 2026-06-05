# Phase 5 Integration Plan — Harberger + Property Tests + Quick Wins

## Build Order (sequential, each validated before next)

### Step 1: Property-Based Invariant Tests (safety net first)
Create `test_invariants.py` that verifies across all 10 configs:
- Money conservation (total wealth constant within a run)
- Non-negative balances for all entities
- Gini in [0,1]
- Min ≤ Mean ≤ Max wealth

### Step 2: Wire Harberger into comparison
- Add `use_harberger` config toggle to comparison_phase5.py
- In simulation loop: create HarbergerMarket, register parcels, call advance_day(), 
  replace manual LVT with Harberger's assess_lvt()
- Handle Harberger LVT flowing into Dividend (same as manual LVT)
- Add random bidder agent (buyer) to trigger forced sales
- Run all 10 systems with and without Harberger, compare results

### Step 3: Quick-Win Configs
- `agricultural_lvt_rate` (default: same as LVT, separate rate for farmland parcels)
- `minimum_wage` (default: 0, wage floor for workers)
- `foreign_ownership_allowed` (default: True, when False non-citizen can't own land)

### Step 4: Full Validation Run
- Run 10 systems × 5 seeds × 480 steps with Harberger + all new configs
- Run invariant tests
- Compare results to Phase 4 baseline

## Quality Guards
- Each step must pass invariant tests before next step begins
- All changes are additive (new config keys, no existing code modified)
- Full regression: Phase 4 baseline results must still be reproducible
