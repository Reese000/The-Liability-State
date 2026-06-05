# Plan: Fix All 10 Critiqued Modules — Hybrid Execution

## Phase 1 (Gate): Adversarial + Insurance Pooling (HIGHEST IMPACT)
1. Wire StrategyController into comparison_batch.py — agents can switch to exploit strategies based on expected value
2. Add community-rated insurance pooling (cross-subsidization) alongside risk-based pricing
3. Validate Phase 1 output before proceeding

## Phase 2 (Parallel Wave): Shocks, Compacts, TFP, Horizon, Demographics
4. Wire EventManager — inject MassTort and Recession events at step 120
5. Split workers/businesses into 2 compacts with different court biases
6. Add TFP response to tax burden
7. Extend horizon to 480 steps
8. Add dependency ratio stress test
9. Parameter sweeps for LVT rate (1-10%)

## File Layout
- All core logic in existing `src/adversarial/`, `src/events/`, `src/core/ledger.py`
- New integration layer: `comparison_phase3.py` — a Phase 3 version of the batch runner
