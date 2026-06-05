# Phase 8 Plan — Fix Core Biases + Sectoral Extensions

## Phase 8a: Fix Core Biases
1. **Consumption channel**: Replace cash welfare with CRRA utility U(c)=c^(1-γ)/(1-γ). 
   Workers consume 80% of after-tax income; utility discounted at β=0.96 annually.
   Welfare = Σ β^t * U(c_t). This changes comparison from "who has most cash" to "who has highest utility."

2. **TFP_TAX_ELASTICITY**: Apply in business revenue:
   `revenue *= (1 + TFP_TAX_ELASTICITY * effective_tax_rate)`
   Effective tax rate = income_tax_rate for income systems, lvt_rate * land_income_ratio for LVT systems.

3. **Labor elasticity sensitivity**: Run comparison at 0.2 and 0.3.
   
4. **Open banking**: Add `money_creation_rate` — banks create new money at fraction of deposits.

## Phase 8b: Sectoral Extensions
5. **Healthcare**: Each system has `healthcare_gdp_share` (US=0.18, Nordic=0.10, Singapore=0.04, LS=0.05).
   Higher share reduces disposable income but improves health outcomes (productivity modifier).

6. **Education**: Each system has `education_gdp_share` (Nordic=0.06, US=0.05, Singapore=0.03, LS=0.02).
   Investment grows human capital (worker productivity) at 8% return (Psacharopoulos).

7. **Environment**: Each system has `carbon_tax_rate` (Nordic=0.03, US=0.0, LS=0.01).
   Revenue from carbon tax, cost to businesses.

8. **Elite capture**: High-wealth agents can influence policy.
   Wealthiest 10% get a `capture_bonus` — reduces their effective tax rate.

## Build Order
1. comparison_phase8.py — single file, ~600 lines
2. Validate against phase7 invariant tests
3. Run batch comparison
4. Critic review
