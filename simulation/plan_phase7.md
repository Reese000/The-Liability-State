# Phase 7 Implementation Plan — Validation

## Components
1. **Global Sensitivity Analysis** (2 hrs compute)
   - Vary every Phase 6 parameter ±50% independently
   - Run 10 systems × 3 seeds × 10 parameters × 3 levels (low/mid/high) = 900 runs
   - Report: which pairwise rankings are robust (never flip) vs fragile (flip under some perturbation)

2. **Historical Backtesting** (requires data)
   - Calibrate US_Style to 1960 parameters (income tax ~20%, corp tax ~50%, welfare ~5%)
   - Run 60 steps/year × 60 years = 3600 steps
   - Compare GDP/capita and Gini trajectory to real US data (FRED/World Bank)
   - Report: trajectory fit (direction, magnitude, turning points)

3. **Monte Carlo Uncertainty** (100+ samples)
   - Draw all parameters from uniform distributions ±50%
   - Run 100 samples of LS_Full and US_Style
   - Report: confidence intervals on wealth ratio and Gini

## Implementation Order
1. validate_sensitivity.py — GSA script
2. validate_backtest.py — Historical backtesting
3. validate_montecarlo.py — MC uncertainty

## Quality Criteria
- All scripts produce text-only output (no plots)
- Raw stdout/stderr captured for critic
- Results saved to output/ as JSON
