# Mechanics Inventory — The Liability State

> **Formal specification of every computable mechanic in the Liability State economic simulation.**
> Extracted from all documents in `/2_Laws_and_Functions/` (files 00–12).
> Each mechanic includes: formal definition, inputs, outputs, preconditions, parameters, edge cases, and inter-mechanic connections.

---

## Table of Contents

1. [Land Value Tax (LVT) & Harberger Self-Assessment](#1-lvt--harberger-self-assessment)
2. [Option Premium (Anti-Griefing)](#2-option-premium)
3. [Citizen's Dividend](#3-citizens-dividend)
4. [National Trust & Three-Source Mandate](#4-national-trust--three-source-mandate)
5. [Monetary System & Land Value Index](#5-monetary-system--land-value-index)
6. [Financial System: Bonds, Royalties, Partnerships](#6-financial-system)
7. [Investment Engine: Bounties, Sandboxes, Patents](#7-investment-engine)
8. [Insurance System](#8-insurance-system)
9. [Legal System: Private Courts & DROs](#9-legal-system)
10. [Fraud Prevention Stack](#10-fraud-prevention-stack)
11. [Glass Box Mandate & Transparency](#11-glass-box-mandate)
12. [Private Civil Servants (PCS)](#12-private-civil-servants)
13. [Whistleblower Protections](#13-whistleblower-protections)
14. [Political Structure: Strategist, House of Repeal, Oversight Panel](#14-political-structure)
15. [Regional Compacts](#15-regional-compacts)
16. [Defense & War Machine](#16-defense--war-machine)
17. [Infrastructure & Property Rights](#17-infrastructure--property-rights)
18. [Social Services & Welfare](#18-social-services--welfare)
19. [Taxation Suite (Non-LVT)](#19-taxation-suite)
20. [Immigration & Border System](#20-immigration--border-system)
21. [Guild System](#21-guild-system)
22. [AI as Legal Actor](#22-ai-as-legal-actor)
23. [Cross-Border Enforcement](#23-cross-border-enforcement)
24. [Catastrophic Event & Solvency Mechanisms](#24-catastrophic-event--solvency)
25. [System Evolution Loops](#25-system-evolution-loops)

---

# 1. LVT & Harberger Self-Assessment

## 1.1 Land Value Tax — Budget-First Cap

### Formal Definition
```
LVT_Rate = (Defense_Costs + Court_Costs + Subsistence_Floor * Population) / Total_LVT_Asset_Value

Annual_LVT_Bill_i = LVT_Rate * Declared_Value_i
```

### Source
01_economic_architecture.md, 10_taxation.md

### Inputs
| Input | Type | Source |
|-------|------|--------|
| Defense_Costs | Float (LS$/yr) | Alliance budget |
| Court_Costs | Float (LS$/yr) | Alliance + compact court operations |
| Subsistence_Floor | Float (LS$/person/yr) | Calculated from cheapest habitable area |
| Population | Integer | Total citizens across all compacts |
| Declared_Value_i | Float (LS$) | Owner's Harberger self-assessment for parcel i |
| Total_LVT_Asset_Value | Float (LS$) | Sum of all Declared_Values across all LVT-taxable assets |

### Outputs
| Output | Type | Destination |
|--------|------|-------------|
| LVT_Rate | Float (0.0–1.0) | All LVT calculations |
| Annual_LVT_Bill_i | Float (LS$) | Parcel owner's tax obligation |
| Aggregate_LVT_Revenue | Float (LS$/yr) | National Trust (10% skim → Alliance; 90% → compact dividend pool) |

### Preconditions
- Every LVT-taxable asset has a valid Harberger self-assessment
- Subsistence Floor has been recalculated within the last 5 years
- LVT_Rate is constitutionally locked (75% supermajority required to change formula)

### Parameters
| Parameter | Value / Range | Notes |
|-----------|--------------|-------|
| LVT Rate | Formula-driven (typically 3–6%) | Budget-first cap: only essential costs |
| Physical land weight in LVI | ≥60% constitutional floor | Prevents currency volatility |
| Alliance skim | 10% of compact-level LVT revenue | Automatic lockbox transfer |

### Edge Cases
1. **Recession**: LVT revenue falls (land values drop) but fixed costs remain → LVT_Rate rises automatically (counter-cyclical pressure)
2. **Territorial expansion**: New territory phased into LVT base over 10 years (monetary system)
3. **No bidders for distressed assets**: Assigned Risk Pool covers minimum tax liability
4. **Zero declared value**: Minimum declaration = documented R&D cost or flat minimum (whichever higher) — prevents instant transfer abuse

### Connections
- → **Citizen's Dividend**: LVT Revenue - Government Costs = Dividend Pool
- → **Monetary System**: LVI = Total LVT Value / Currency Units
- → **National Trust**: 10% skim funds Alliance functions
- → **Harberger Self-Assessment**: Declared value determines tax bill AND buyout price

---

## 1.2 Harberger Self-Assessment

### Formal Definition
```
Owner declares value V_i for asset i.
Annual tax = LVT_Rate × V_i.
Any third party may purchase asset i at price V_i (subject to Option Premium process).
```

### Source
10_taxation.md, 03_investment_engine.md (for patents)

### Inputs
| Input | Type | Source |
|-------|------|--------|
| V_i | Float (LS$) | Owner's declared value |
| LVT_Rate | Float | From Budget-First Cap calculation |

### Outputs
| Output | Type | Destination |
|--------|------|-------------|
| Annual_Tax_i | Float (LS$) | Tax authority |
| Purchase_Price | Float (LS$) | Standing offer to any buyer |

### Incentive Structure
- **Under-declare**: Lower tax but risk forced sale at low price
- **Over-declare**: Higher tax but deter buyers
- **Honest declare**: Optimal — market price reflects true value

### Scope: "Land" Definition (Expanded)
| Component | Examples | Notes |
|-----------|----------|-------|
| Physical land | Residential, commercial, agricultural, undeveloped | ≥60% of LVI weight floor |
| Electromagnetic spectrum | Frequency bands, broadcast licenses | Treated as Harberger asset |
| Orbital slots | Geostationary positions, orbital paths | On Mercantile Registry |
| Intellectual property | Harberger-patented inventions | Tier 1 (Exclusive) value taxed |
| Extraction rights | Mineral, oil, gas, water permits | Treated as Harberger asset |

### No-Owner Homesteading
Resources are not granted by the state — any person can homestead by:
1. Declaring a Harberger price
2. Paying the 3% (standard) LVT
3. State acts only as Notary of Exclusive Use

---

# 2. Option Premium

## 2.1 Harberger Transfer Protocol

### Formal Definition
```
Phase 1 (Free Window): Days 1–14 after bid posted.
  - Owner may refuse with zero cash penalty.
  - Owner's tax basis increases to bid price.

Phase 2 (Penalty Phase): Days 15–90.
  - Owner may refuse by paying buyer 15% of bid price.
  - Buyer's capital locked in escrow entire duration (104 days max).

Acceptance: Sale proceeds at declared price. Bond returned to buyer.
```

### Source
10_taxation.md §The Option Premium Model (Anti-Griefing)

### Inputs
| Input | Type | Source |
|-------|------|--------|
| Bid_Price | Float (LS$) | Buyer's offer at or above declared value |
| Declared_Value | Float (LS$) | Current owner's Harberger assessment |
| Phase_Day | Integer (1–104) | Days elapsed since bid posted |
| Free_Window | Integer (14) | Constitutional parameter |
| Penalty_Rate | Float (0.15) | Constitutional parameter |
| Bond_Lockup_Max | Integer (90) | Max days buyer's capital locked after free window |

### Outputs
| Output | Type | Destination |
|--------|------|-------------|
| Owner_Can_Refuse_For_Free | Boolean | True if day ≤ 14 |
| Owner_Refusal_Penalty | Float (LS$) | 15% of Bid_Price if day > 14 |
| Tax_Basis_Adjustment | Float (LS$) | Declared_Value updated to Bid_Price if refused in Free Window |
| Sale_Proceeds | Float (LS$) | To seller on acceptance |

### Edge Cases
1. **Griefing by wealthy bidder**: 15% penalty + 104-day capital lockup deters
2. **Sentimental owner**: Pays "Pride Tax" (penalty) to keep property → funds community dividend
3. **Liquidity shock**: 14-day free window prevents immediate forced-sale crisis
4. **Multiple simultaneous bids**: First valid bid processed; subsequent bids queued
5. **Declared value changes during bidding**: New bids reference current declared value

### Connections
- → **LVT**: Tax basis increases on refused offers
- → **Harberger Patents**: Same mechanism applies to IP Tier 1 buyout
- → **Citizen's Dividend**: "Pride Tax" penalty revenue flows to dividend pool

---

## 2.2 LVT Revenue Futures

### Formal Definition
```
Treasury sells rights to next fiscal year's LVT revenue stream to global investors.
= LVT_Futures_Price × Expected_Revenue × (1 - Risk_Discount)
```

### Source
10_taxation.md §Revenue Futures

### Purpose
Offload LVT revenue volatility to capital markets. Boom: investors pay premium. Bust: investors absorb loss.

### Inputs
| Input | Type |
|-------|------|
| Expected_Revenue | Float (LS$) |
| Risk_Discount | Float (0.0–1.0) |
| Market_Demand | Float (LS$) |

### Output
| Output | Destination |
|--------|-------------|
| Upfront_Cash | Treasury (stable regardless of actual revenue) |

---

# 3. Citizen's Dividend

## 3.1 Dividend Calculation

### Formal Definition
```
Total_Dividend_Pool = Total_LVT_Revenue + Pollution_Fees + Fines - Alliance_Skim - Essential_State_Costs

Per_Capita_Dividend = Total_Dividend_Pool / Citizen_Count

Dividend_Floor = Subsistence_Cost(cheapest_habitable_area)
  where Subsistence_Cost = 2,000 kcal/day + basic shelter in cheapest habitable compact
```

### Source
01_economic_architecture.md, 09_social_services.md

### Inputs
| Input | Type | Source |
|-------|------|--------|
| Total_LVT_Revenue | Float (LS$/yr) | Sum of all compact-level LVT |
| Pollution_Fees | Float (LS$/yr) | Environmental extraction fees |
| Fines | Float (LS$/yr) | Legal system fines |
| Alliance_Skim | Float (LS$/yr) | 10% of compact-level LVT |
| Essential_State_Costs | Float (LS$/yr) | Defense auditing, courts, minimal admin |
| Citizen_Count | Integer | All registered citizens |
| Cheapest_Area_Subsistence | Float (LS$/yr) | Recalculated every 5 years |

### Outputs
| Output | Type | Destination |
|--------|------|-------------|
| Per_Capita_Dividend | Float (LS$/yr) | Every citizen's individual payment |
| Dividend_Floor | Float (LS$/yr) | Constitutional minimum per citizen |

### Parameters
| Parameter | Value | Notes |
|-----------|-------|-------|
| Recalculation period | 5 years | Pegged to cheapest habitable area |
| Dividend floor type | National (fixed) | Same amount everywhere |
| Compact supplementation | Permitted (add only) | Cannot reduce below national floor |

### The Blind Trust Lockbox (Child Dividend)
- Children receive full dividend from birth
- **0%** goes to parents
- Money accumulates in trust, earning interest
- Unlocks at age 18 (or trade school completion)
- Every 18-year-old enters workforce with capital stake

### Edge Cases
1. **Population boom**: Dilutes per-capita dividend until LVT revenue catches up
2. **Recession**: Dividend falls with LVT → automatic contractionary pressure
3. **Compact supplementation**: Rich compacts can add local dividend on top
4. **Deflation offset**: Rising dividend in growth phase offsets mild deflation from appreciating currency

### Connections
- → **Monetary System**: Dividend is the supply anchor (puts currency in citizens' hands)
- → **LVT**: Revenue source drives dividend pool
- → **Immigration**: Citizens receive dividend; non-citizens do not
- → **Social Safety Net**: Dividend IS the subsistence floor — replaces welfare
- → **Geographic Arbitrage**: Non-workers move to cheap areas → organic population distribution

---

## 3.2 Zero-Sum Budget Formula

### Formal Definition
```
Tax_Revenue - Government_Costs = Citizen_Dividend
```

Every cent of government waste is a cent removed from every citizen's pocket. This creates universal incentive for efficient government.

### Source
06_political_structure.md

### Constitutional Protections
| Element | Change Required |
|---------|-----------------|
| LVT rate formula | 75% supermajority |
| Dividend distribution formula | 75% supermajority |
| Core rights definitions | 75% supermajority |

---

# 4. National Trust & Three-Source Mandate

## 4.1 National Trust Structure

### Formal Definition
```
National_Trust_Balance = Σ(Compact_LVT_Revenue × 0.10) + LVT_Futures_Proceeds + War_Escrow_10%

Allocation:
  - Inter-Compact Dispute Resolution (STO)
  - Border Defense (PMC contracts)
  - Currency & LVI administration
  - Citizen's Dividend Floor auditing
```

### Source
06_political_structure.md §The National Alliance

### Inputs
| Input | Type | Source |
|-------|------|--------|
| Compact_LVT_Revenue | Float (LS$/yr) | Each compact's aggregate LVT collection |
| LVT_Futures_Proceeds | Float (LS$) | Sale of future LVT revenue |
| War_Escrow_10% | Float (LS$) | 10% of War Escrow payout pool |

### Outputs
| Output | Type | Destination |
|--------|------|-------------|
| Unspent_Balance | Float (LS$) | Refunded proportional to compact contribution |
| Function_Budgets | Float[4] | Four Alliance functions |

### Key Rules
- **No discretion**: Trust disburses to four functions by formula
- **No income/sales/VAT/corporate tax**: Constitutionally banned
- **No standing army**: All military is private PMC
- **No debt issuance**: Alliance cannot bind compacts to debt
- **Unspent funds refunded** proportional to each compact's contribution (not per capita)

### Sunset Mechanism
- Each Alliance function has a 10-year charter
- Year 8: STO performance review
- Year 10: Each compact votes on each function separately
- Function dies if majority of compacts do not re-authorize

---

## 4.2 Three-Source Mandate

### Rule
No single pool holds concentrated exposure. Risk is distributed across:
1. Guild Mutuals (small pools of 500–5,000 members)
2. Private insurers
3. Global reinsurance / secondary claims market

### Source
07_defense_military.md §Catastrophic Event Solvency

---

# 5. Monetary System & Land Value Index

## 5.1 Definitional Peg

### Formal Definition
```
1 LS_Dollar ≡ 1/1,000,000 of the Land Value Index (LVI)

LVI = Σ(LVT_assessed_value_of_all_assets) / Currency_units_in_circulation
```

### Source
12_monetary_system.md

### Inputs
| Input | Type | Source |
|-------|------|--------|
| LVT_Assessed_Values | Map[AssetID → Float] | Harberger self-assessments across all compacts |
| Currency_Units | Integer | Total LS Dollars in circulation |
| Physical_Land_Weight | Float (0.6) | Constitutional floor ≥60% |
| Component_Weights | Float[5] | 5-year trailing average LVT revenue per component class |

### Outputs
| Output | Type | Destination |
|--------|------|-------------|
| LVI | Float (LS$/unit) | Daily published index; monetary anchor |
| Real_Currency_Value | Float (LS$) | Implicit purchasing power vs. land base |

### Components of LVI
| Component | Weight Floor | Examples |
|-----------|:-----------:|----------|
| Physical land | ≥60% | Residential, commercial, agricultural |
| Electromagnetic spectrum | Variable | Frequency bands, broadcast licenses |
| Orbital slots | Variable | Geostationary positions |
| Intellectual property | Variable | Harberger patents, copyright terms |
| Extraction rights | Variable | Mineral, oil, gas, water permits |

### Stress Test Results
| Scenario | Residual Backing | Action |
|----------|:----------------:|--------|
| Baseline | 100% | Peg holds |
| IP crash -90% (dot-com) | 64% | Court review triggered (<90%) |
| Land crash -30% (Japan) | 82% | Court review triggered |
| Combined -30% land + -50% IP | 62% | Court review triggered |
| Tail -20% land + -90% IP | 52% | Constitutional intervention required |
| GFC 2008 (-25% land, -40% IP) | 69% | Borderline — court review |

### Enforcement (No Central Bank)
| Force | Direction | Mechanism |
|-------|-----------|-----------|
| Demand anchor | People need currency | LVT collected in LS Dollars only |
| Supply anchor | People receive currency | Dividend paid in LS Dollars only |
| Stability | Natural equilibrium | Revenue and expense in same unit = closed loop |
| Constitutional liability | Government dilution | Courts enforce peg; violators face liability |

### Edge Cases
1. **Government tries to print**: Dilutes LVI → citizens sue; courts enforce constitutional peg
2. **Territorial expansion**: New territory phased in over 10 years to prevent supply shock
3. **LVI below 90% threshold**: Courts may authorize one-time rebasing or temporary LVT surcharge
4. **Private credit creation**: Allowed but disincentivized by unlimited liability and Glass Box transparency

---

## 5.2 Counter-Cyclical Dynamics

### Growth Phase
```
Land values ↑ → LVT ↑ → Dividend ↑ → Mild deflation (1-3%/yr)
  Dividend rise offsets deflationary pressure
```

### Contraction Phase
```
Land values ↓ → LVT ↓ → Dividend ↓ → Mild inflation (1-3%/yr)
  Dividend fall prevents over-stimulation
```

### Key Insight
The LS Dollar is slightly deflationary in booms, slightly inflationary in busts — automatically counter-cyclical without any policy decision.

---

# 6. Financial System

## 6.1 Corporate Bonds (Debt)

### Formal Definition
```
Investor lends Principal P at Interest_Rate r for Term T.
Bond_Maturity: Pay P × (1 + r)^T at date D.
Risk: Default only — no shareholder liability.
```

### Source
02_financial_system.md

### Inputs
| Input | Type |
|-------|------|
| Principal | Float (LS$) |
| Interest_Rate | Float (APR) |
| Term | Integer (years) |
| Issuer_Credit_Rating | Float |

### Outputs
| Output | Destination |
|--------|-------------|
| Periodic_Interest | Investor |
| Principal_Repayment | Investor at maturity |

---

## 6.2 Revenue-Based Financing (Royalties)

### Formal Definition
```
Investor provides Principal P.
Company pays r% of top-line revenue per period until Cumulative_Payment reaches Cap (e.g., 2P).

Cumulative_Payment = Σ(r × Revenue_t) for t = 1..T such that Cumulative_Payment ≤ Cap
```

### Source
02_financial_system.md

### Key Rules
- No voting rights (investor not liable)
- Contract ends when cap reached (self-limiting)
- Returns tied to actual sales, not stock price

---

## 6.3 Limited Partnerships

### Governance
| Role | Liability | Control |
|------|-----------|---------|
| Active Investors (Board/Management) | Unlimited | Full |
| Limited Partners (Public) | Limited to investment | None |

### The Firewall Rule
If a limited partner sends even one instruction to the CEO, they pierce the veil → become fully liable.

### Source
02_financial_system.md

---

## 6.4 Mutualism & Credit Unions

### Stakeholder Finance Model
- Guild Banks: Credit unions owned by trade members, serving that trade
- Customer Funding: Pre-paid credits fund construction (not speculation)
- Pension Funds: Workers collectively invest in own industries

---

## 6.5 Tobin Tax (Financial Transaction)

```
Tax = 0.1% × Transaction_Value
```

### Source
10_taxation.md

### Effect
| Investor Type | Impact |
|--------------|--------|
| Long-term (10-year hold) | Negligible (0.1% one-time) |
| HFT algorithm (1000 trades/sec) | Profit margin destroyed |

---

# 7. Investment Engine

## 7.1 National Bounties (Pull Financing)

### Formal Definition
```
State posts binding contract prize P for achieving Goal G.
Bounty_Active: Yes/No (until claimed or expired)
First entity to verifiably meet Goal G receives P (tax-free).

Bounty Types:
- Energy: First sustainable fusion reactor
- Medicine: Cure for Alzheimer's
- Space: First self-sustaining Mars colony
- Infrastructure: Hyperloop at specified cost/mile
- Defense: Hypersonic interception system
```

### Source
03_investment_engine.md

### Inputs
| Input | Type | Source |
|-------|------|--------|
| Goal_G | String + Verification_Criteria | Strategist proposal / referendum |
| Prize_P | Float (LS$) | Funded from National Trust or War Escrow |
| Verification_Oracle | Boolean | Truth Oracle (Schelling Point prediction market) |

### Outputs
| Output | Destination |
|--------|-------------|
| Prize_P | First verified winner |
| Economic_Boom_Effect | → Increased land values → higher LVT |

### Key Rules
- Prize only paid if goal achieved (no vaporware)
- "First to achieve" creates competitive pressure
- Verification via Truth Oracle (prediction market)

---

## 7.2 Sandbox Zones (Innovation Enclaves)

### Formal Definition
```
Designated physical area A where limited liability is restored for experimental testing.
  Inside_A: Limited liability, experimental freedom
  Outside_A: Strict liability, full damages for any leakage

If experiment leaks outside zone:
  Strict_Liability_Applies = True
  Operator faces full unlimited liability
```

### Source
03_investment_engine.md

### Locations
- Desert testing ranges
- Orbital stations
- Isolated islands
- Underground facilities

---

## 7.3 Harberger Patent Licensing

### Formal Definition
```
Inventor registers patent with:
  Tier_1_Value = Exclusive buyout price (taxed at LVT rate)
  Tier_2_Fee = Per-unit licensing rate (income, not double-taxed)

Any party may:
  (a) Purchase patent outright at Tier_1_Value (via Option Premium process)
  (b) License use at Tier_2_Fee per unit (no negotiation needed)
```

### Source
03_investment_engine.md

### Inputs
| Input | Type |
|-------|------|
| Tier_1_Value | Float (LS$) |
| Tier_2_Fee | Float (LS$/unit) |
| R&D_Cost | Float (LS$) | Minimum declaration |

### Outputs
| Output | Destination |
|--------|-------------|
| Annual_Patent_Tax | LVT pool (Tier_1 × LVT_Rate) |
| Licensing_Revenue | Patent holder (taxed as regular income) |

### Anti-Stagnation Mechanics
| Abuse | Countermeasure |
|-------|---------------|
| Patent trolling | High Tier 1 → high tax; low Tier 2 → low licensing income |
| Sitting on patents | Rival bids up Tier 1 → forced sale or higher tax |
| Complex valuation | Market clears through declared prices |
| Hostile takeover (griefing) | Option Premium (15% penalty) protects genuine inventors |

---

## 7.4 Insurance-Led R&D

Insurers fund safety technology R&D because they bear liability costs:
- AI monitoring systems
- Self-healing pipes
- Early warning sensors

Logic: Insurer pays claims → insurer funds prevention → prevention is cheaper than claims.

---

## 7.5 Golden Ticket Visa

### Formal Definition
```
Immediate citizenship + business grant for:
  (a) Foreigners passing rigorous Founder's Test, OR
  (b) Bringing a verified high-tech patent
```

### Purpose
Import risk-taking entrepreneurs when domestic population becomes too comfortable.

---

# 8. Insurance System

## 8.1 Mandatory Liability Insurance

### Rule
To operate any business in the Liability State, an entity must carry comprehensive liability insurance from a certified insurer.

### Source
04_legal_system.md

### Flow
```
Business wants to operate
  → Must purchase liability insurance
  → Insurer inspects facilities
  → Premium priced proportional to risk
  → Unsafe businesses face unaffordable premiums → exit via market forces
```

### The Insurance Ceiling (Anti-Monopoly)
```
Small company → small potential lawsuit → low insurance cost
Large company → massive potential lawsuit → high insurance cost
Monopoly → catastrophic potential lawsuit → UNINSURABLE
  → Natural break-up into smaller insurable units
```

---

## 8.2 Systemic Risk Multiplier

### Rule
Courts apply scaled damages based on market share:

| Market Share | Damages |
|:-----------:|---------|
| 5% | Cleanup costs only |
| 80% | Cleanup + Systemic Risk Multiplier |

### Source
01_economic_architecture.md

---

## 8.3 Insurer Whitelist for Courts

### Rule
Each insurer publishes a list of approved Dispute Resolution Organizations (DROs).
- Policyholders must use whitelisted courts
- If contract specifies non-whitelist court, insurer won't cover disputes
- Market pressure: companies using corrupt courts become uninsurable

### Source
04_legal_system.md

---

## 8.4 Guild Mutuals (Self-Insurance)

### Structure
- Groups of 500–5,000 members can self-insure
- Guild mutuals as exit option from private insurers
- Provides fraternal benefits for members

### Source
07_defense_military.md, 09_social_services.md

---

## 8.5 Actuarial Nexus Doctrine

### Rule
Insurers can price **risk**, not **values**:
- ✅ Charge more for fast drivers
- ❌ Charge more for voting wrong
- If no direct causal link between behavior and claims → clause void

### Source
07_defense_military.md

---

## 8.6 Assigned Risk Pool

### Rule
If denied coverage by 3 insurers for exercising a constitutional right:
1. Enter Assigned Risk Pool
2. Every insurer must take a share
3. Premiums capped at 300% of standard rate

### Source
07_defense_military.md

---

# 9. Legal System

## 9.1 Private Judiciary (DROs)

### Structure
```
Dispute Resolution Organizations (DROs) — private courts competing on:
  - Speed (faster → more clients)
  - Cost (cheaper → more clients)
  - Fairness (reputation → more clients)

Government role: Auditor only — certifies due process (like ISO certification)
```

### Source
04_legal_system.md

### Certification and Enforcement
1. DROs must be certified by government auditor
2. Businesses agree to specific DROs in contracts
3. Rulings are legally binding
4. **Published Statistics**: Win rates by party type (45-55% or flagged)
5. **Audit Rotation**: Government randomly audits 20% of rulings annually
6. **Whistleblower Bounties**: 10% of damages to anyone proving bias

---

## 9.2 Loser Pays (English Rule)

### Formal Definition
```
If Plaintiff loses lawsuit:
  Plaintiff pays 100% of Defendant's legal fees

If Plaintiff wins:
  Defendant pays 100% of Plaintiff's legal fees
```

### Source
04_legal_system.md, 05_fraud_prevention.md

### Effect
| Case Type | Plaintiff Incentive |
|-----------|-------------------|
| Strong case | Proceed confidently |
| Frivolous case | Financially suicidal |
| Settlement extortion | Eliminated |

---

## 9.3 Litigation Bonds

### Formal Definition
```
Before case proceeds:
  Plaintiff posts Bond_Amount (LS$) or obtains Legal_Insurance

If case is fraudulent:
  No insurer will back it → bond not posted → case rejected

If plaintiff cannot afford bond:
  Trust Broker / Litigation Financier backs legitimate claims in exchange for % of payout
```

### Source
05_fraud_prevention.md

---

## 9.4 Contempt & Non-Compliance

| Sanction | Mechanism |
|----------|-----------|
| Asset Liens | Court places lien on property, bank accounts |
| Insurance Revocation | Insurer drops non-compliant client |
| Guild Expulsion | Professional blacklisting |
| Ultimate Sanction | No one will do business with judgment-evader |

### Source
04_legal_system.md

---

## 9.5 Rehabilitation Contracts (Criminal Law)

### Formal Definition
```
Court convicts person of crime.
Court issues Rehabilitation Contract:
  - Duration D (set by court)
  - Minimum living conditions M (set by court)
  - Restitution obligations R (set by court)

Contract auction: Private rehabilitation firms bid to house/supervise convict.
  - Convict is NOT property — contract is for services
  - If contractor abuses convict → sued for damages
  - If convict re-offends under supervision → contractor sued for damages
  - Funding: Convict's assets first; insurance covers remainder
```

### Source
04_legal_system.md

### Prisoner's Contract Ladder
| Level | Conditions | Who Bids |
|-------|-----------|----------|
| Default | Basic housing, monitored movement, no work | Cheapest meeting minimum |
| Level 2 | Semi-private, supervised work | Mid-tier firms |
| Level 3 | Unmonitored movement, full employment (wages garnished) | High-trust contractors |
| Reintegration | Early release under guild sponsorship | Guild vouches, liable if re-offend |

### Guardrails
| Risk | Mitigation |
|------|-----------|
| Lowest-bidder warehouses | Default contract must meet court-set minimum standards |
| No bidders for dangerous convicts | Regional Compact provides minimum-security option funded by convict's insurance |
| Abuse by contractors | Full liability — contractor sued for guard's actions |
| Escape | Contractor pays forfeiture bond; bounty issued for recapture |

---

## 9.6 Public Ledger of Judgments

Every private court maintains a digital Book of Judgments accessible to anyone:
- Builds case law precedent
- Exposes patterns (which companies get sued often?)
- Creates reputation consequences

---

# 10. Fraud Prevention Stack

## 10.1 Six-Layer Deterrent Stack

### Source
05_fraud_prevention.md

| Layer | Mechanism | Risk to Scammer |
|:-----:|-----------|-----------------|
| 1 | Loser Pays | Pay defendant's legal fees |
| 2 | Litigation Bond | Lose deposit |
| 3 | Reputation Database | Future claims flagged |
| 4 | Forensic Evidence | Case demolished by data |
| 5 | Counter-Suit | Criminal fraud charges |
| 6 | Attorney Gatekeeping | Can't find lawyer |

---

## 10.2 Reputation Database (Plaintiff Tracking)

### Data
Shared database across private courts and insurers:
- Number of suits filed per individual
- Win/loss record
- Types of claims
- Payout history

### Effect
Serial plaintiffs get a "Credibility Score" — on the Nth claim, the burden of proof shifts.

---

## 10.3 Comparative Negligence

### Rule
Courts assess **relative fault** between plaintiff and defendant.
- Plaintiff contributed 80% → payout reduced by 80%
- Can rule 50/50 split liability

### Source
05_fraud_prevention.md

---

## 10.4 Forensic Surveillance Standard

Businesses maintain:
- High-resolution cameras with timestamps
- Floor sensors (spills, cleanups)
- Environmental monitors
- Activity logs

These are standard defensive provisions in a liability-based world.

---

## 10.5 Attorney Gatekeeping

### Rule
Attorneys are personally liable for frivolous suits:
- Must certify cases have merit
- False certification = malpractice
- Insurance companies monitor attorney track records

---

# 11. Glass Box Mandate

## 11.1 Corporate Transparency Requirements

### Source
01_economic_architecture.md, 06_political_structure.md

### Requirements
All corporations must operate as Glass Boxes:
1. **Real-Time Logbook**: Safety audits, emission levels, liability-linked financial reserves — all public
2. **Auditable Actuarial Models**: Internal risk models used for insurance negotiations must be auditable by any affected citizen
3. **Asset Visibility**: Concealing ownership or assets to evade liability is "Strategic Sabotage" (criminal act)

---

## 11.2 Glass Box State Mandate

### Requirements for Alliance and Compacts
1. **Real-Time Treasury Log**: Every cent leaving the state treasury visible within 60 seconds
2. **Model Transparency**: LVT and Dividend formulas must be open-source and auditable
3. **External Audit Access**: Any individual/group can trigger an "Adversarial Audit" of a state function
   - If audit discovers waste/fraud → auditor paid bounty from recovered funds (Incentivized Vigilance)

### Temporal Transparency (Vault Model)
- Military/diplomatic secrets kept secret in real-time
- Automatically unlock after 2–5 years
- Politicians cannot block "unsealing"
- Zero-knowledge auditing: prove statements without revealing data

---

# 12. Private Civil Servants (PCS)

## 12.1 Deep-Access Auditor Model

### Source
04_legal_system.md

### Structure
| Feature | Description |
|---------|-------------|
| Status | Voluntary — individuals sign up |
| Access | With court warrant, can demand any data/facility |
| Liability | Personal ruin for any abuse, leakage, corruption |
| Bonding | Backed by 5+ personal sureties, each posting significant assets |
| Confidentiality | Lifetime NDA; leakage = total disgorgement of all future income |
| Monitoring | Sureties monitor PCS activity continuously (their assets at stake) |

### Warrant Process
1. **Probable cause**: Whistleblower/insurer/Actuarial Commons presents evidence
2. **Court review**: Private court reviews ex parte → warrant if probable cause
3. **PCS execution**: 2-3 PCSs from different bond networks execute simultaneously
4. **Inspection**: Examine secret data, systems, facilities
5. **Attestation**: Public "verified clean" or detailed findings — no proprietary data revealed
6. **Sanction**: Violations found → company faces liability; PCS attestation is admissible evidence

### Minimum Standards
| Standard | Requirement |
|----------|-------------|
| Bond-to-examination ratio | ≥10× the economic stake of what they inspect |
| Multi-PCS requirement | 2-3 PCSs from independent bond networks |
| Lifetime disgorgement | Leak → forfeit all income from all sources for life |
| Surety reporting | Must report known violations within 30 days or lose bond status permanently |

---

# 13. Whistleblower Protections

## 13.1 Statutory Exemption

### Source
04_legal_system.md

### Rule
NDA clauses that would prevent disclosure of fraud/public safety violations/systemic harm are **void as against public policy**.

### Conditions for Protection
| Element | Rule |
|---------|------|
| Void provisions | Contract clause preventing disclosure of defined wrongdoing = unenforceable |
| Designated channels | Must report to: Actuarial Commons, private court, guild mutual auditor, or public registry |
| Reasonable basis | Whistleblower must have reasonable belief wrongdoing occurred |
| Good faith | No personal gain, competitor relationship, extortion attempt, or prior demand for payment |

### Legal Effect
1. NDA void as applied → court dismisses breach of contract claim
2. No liability for disclosure
3. Permanent protection — cannot be retroactively enforced

### Enhanced Remedies for Retaliation
| Firm Action | Whistleblower Remedy |
|-------------|---------------------|
| Wrongful termination | Treble back pay + damages for career harm |
| Suit to enforce void NDA | Treble damages + full legal costs |
| Blacklisting/defamation | Punitive damages |

### Guild Mutual Liability
Guild bears secondary liability if it knew/should have known about suppression through void contract provisions.

---

## 13.2 Pardon Power

### Source
06_political_structure.md

### Mechanism
- **Power**: Executive Oversight Panel (unanimous 3/3 vote)
- **Purpose**: Last resort for cases where statutory protections don't apply but public interest requires relief
- **Threshold**: High — requires unanimous agreement among three randomly selected citizens

---

# 14. Political Structure

## 14.1 The Strategist (Executive)

### Source
06_political_structure.md

| Has | Does Not Have |
|-----|---------------|
| Power of the Pulpit (speeches, vision) | Legislative power (cannot write laws) |
| Power to Propose National Missions | Command of police (private) |
| Cultural leadership | Treasury control |
| Diplomatic representation | Ability to seize money |

### National Missions Process
1. Strategist proposes mission (e.g., "Go to Mars — $1T")
2. Cannot take money — must initiate National Referendum
3. Citizens vote
4. Private courts unlock specific funds for that mission only

---

## 14.2 Bonded Executive (Emergency Powers)

### Formal Definition
```
Trigger: Strategist declares "Imminent Threat"
Bond: Posts personal assets (home, savings, pension) as collateral
Powers: Temporary authority to mobilize defense, bypass referendum
Duration: 90 days maximum (renewable once)
Audit: Post-crisis — Private Courts audit decisions

If justified: Bond returned, leader honored.
If abuse/error: Bond forfeited to victims. Strategist personally liable.
```

### Edge Cases
- **Fake crisis**: Strategist loses house → deters fabrication
- **Real crisis**: Instant response enabled
- **No "fog of war" immunity**: Every dollar justified post-hoc

---

## 14.3 Executive Oversight Panel (Sortition Panel of 3)

### Source
06_political_structure.md

### Selection Criteria
| Requirement | Rationale |
|-------------|-----------|
| Active dues-paying guild member, employed in trade | Live skin in the game |
| Not receiving guild retirement/pension | Verifiable proxy for non-retired status |
| 5+ years active guild membership in last 7 | Continuous economic engagement |
| No guild executive/board leadership in last 5 years | Not governance insider |
| Clean liability record (10 years) | No outstanding judgments |
| Pass civic literacy assessment | Three-Source Mandate, Option Premium, guild mutual mechanics |
| No elected office ever held | No career politicians |

### Term and Staggering
- 6-month term, no reappointment, permanently ineligible after service
- Staggered: one member drawn every 2 months
- Confirmed draw: 6 names drawn; 3 serve after 2-week confirmation window

### Powers (Constitutional Veto — 2/3 supermajority)
| Executive Action | Abuse Blocked |
|-----------------|---------------|
| Emergency declaration | Expands power indefinitely |
| Guild mutual de-certification | Political revenge |
| Treaty/foreign commitment | Sells out liability protections |
| Snap referendum call | Exploits temporary crisis |
| Harberger estate forced sale | Expropriates opposition land |

### Deliberately Withheld Powers
| Rejected Power | Reason |
|----------------|--------|
| Calling audits/investigations | No expertise; would reintroduce single-point-of-pressure bottleneck |
| Initiating legislation/policy | Check on executive, not legislature |
| Appointing/removing officials | Cannot hire or fire anyone |

---

## 14.4 House of Repeal (Sortition Legislature)

### Source
06_political_structure.md

### Selection
Random lottery (like jury duty) from all eligible citizens.

### Powers (Negative Only)
Can only:
- **Repeal** existing regulations
- **Fire** corrupt Auditors
- Trigger **Vote of No Confidence** on executives

Cannot pass new laws.

### Voting Thresholds
| Action | Threshold |
|--------|:---------:|
| Repeal law | Simple majority |
| Change Dividend formula | 75% supermajority |
| Change basic rights | 75% supermajority |
| Change LVT rate formula | 75% supermajority |
| Constitutional amendment | 75% HoR + majority of Compacts |

---

## 14.5 Recall Switch

### Rule
House of Repeal can trigger immediate "Vote of No Confidence."
Strategist has no army or treasury → losing means simply fired.

---

# 15. Regional Compacts

## 15.1 Compact Structure

### Source
06_political_structure.md

### What Compacts Are
Instead of traditional states with legislative power, Compacts are **Standardized Legal Frameworks**:
- Invoice member Cities (not tax individuals)
- Maintain "flavor" of existing law (don't write new laws)
- Can be dissolved by member Cities
- Cultural custodians, not political rulers

### Five Differentiation Axes
| Axis | What Varies | Example |
|------|-------------|---------|
| Damage valuation | Non-economic damages caps | Kansas: $500K; Coastal: $5M |
| Environmental harm definition | Pollution, depletion | Mountain: groundwater as strict liability; Gulf: resource extraction pricing |
| Guild authority | Certification autonomy | Texas: guild-only licensing; Vermont: dual compact-guild |
| Court preference | Default court selection | Mandatory random rotation vs. contractual choice |
| Risk tolerance | Permitted activities + coverage minimums | Nevada: high-risk finance; New England: lower ceilings |

### Constitutional Floor (All Compacts)
- No ex-ante licensing for most activities
- Recognition of private court judgments across compacts
- Free movement of citizens and capital
- Three-Source Mandate compliance

### Force Prohibition
No compact may raise a military, police force, or armed militia for use against other compacts or residents.

---

## 15.2 Compact Boundaries (Ideology Permitted)

| Ideology | Permitted? | Limitation |
|----------|:----------:|------------|
| Minarchist/market-dominant | ✅ Yes | Default setting |
| Social democratic | ⚠️ Partial | No income tax (constitutional); can add local taxes on LVT or municipal subscriptions |
| Communist (state-owned) | ⚠️ Partial | Must carry insurance, face liability, operate as Glass Boxes |
| Theocratic (religious law) | ⚠️ Partial | Religious courts alongside liability courts; liability judgments prevail |
| Authoritarian | ❌ No | Courts must be independent; insurers must challenge government |
| Hyper-bureaucratic (ex-ante licensing) | ❌ No | Constitutional commitment to ex-post liability |

---

## 15.3 Commons Stewardship

### Rule
Shared resources (fisheries, watersheds, airsheds, aquifers) managed at **Compact level only**.

- Federal level has NO regulatory power over commons
- Each compact defines "reasonable use" of regional shared resources
- Enforcement through liability system
- Inter-compact commons (rivers, migratory fisheries, atmospheric pollution): mutual agreements → private courts → STO enforcement
- Competitive pressure: mismanaging compacts lose residents/businesses

---

## 15.4 Compact Accountability

- Funded by invoices to member Cities
- Cities can vote to Dissolve and Reform a compact
- Leadership must stay efficient or lose "customers"

---

## 15.5 Supreme Trust Oracle (STO)

### Role
Backstop enforcement layer for inter-compact disputes.

### Jurisdiction
- Adjudicates disputes between compacts
- Enforces cross-compact judgments
- Issues Freedom of Exit Determinations (conquest doctrine)
- Dissolves rogue compacts
- Triggers Trust Blockade (invalidates rogue compact's land titles across all compacts)

---

# 16. Defense & War Machine

## 16.1 War IPO Architecture

### Formal Definition
```
War_Escrow (Iron Vault): Smart contract liquidity pool.
  - Cryptographically locked — no political release
  - Oracle-triggered: only Truth Oracle can unlock
  - Funding: Insurance Cartel (defensive) + Global Investors (offensive)

Victory Bonds: Tokenized claims on Escrow.
  - Face Value: $1.00 (paid only on victory)
  - Market Price: Floating (probability of victory)
  - Tradeable 24/7 on Victory Curve (AMM)

Victory Curve: Automated Market Maker pricing bonds.
  Price = f(Total_Capital_Invested)
```

### Source
07_defense_military.md

### The 90/10 Split
- 90% → Victory Payout Pool (backs bonds)
- 10% → National Trust (government profit)

---

## 16.2 Victory Bond Lifecycle

1. Issuance: Government mints bonds = Escrow funds
2. Allocation: Sold to insurers/investors to fill Escrow
3. Payment: PMCs paid in bonds (skin in game)
4. Resupply: PMCs sell bonds on secondary market for cash
5. Maturity: Victory → $1.00 payout per bond

### Feedback Loop
```
PMC wins battle → Bond price rises (e.g., $0.20 → $0.40)
PMC sells bonds → 100% profit on paper gains
Cash reinvested → More ammo, more victories
Success breeds funding → Momentum accelerates
```

---

## 16.3 Truth Oracle (Schelling Point)

### Formal Definition
```
Question: "Has Win Condition for Bounty #892 been met?"
Betting: Thousands of independent actors bet YES/NO
Consensus: When YES trades at ~99.9% for sustained period
Trigger: Smart contract signs cryptographic key
Payout: Escrow unlocks automatically

Adversarial Audit: Even the enemy can participate — if PMCs lie, enemy bets NO with proof.
```

---

## 16.4 PMC Control Stack

| Mechanism | Lever | How It Works |
|-----------|-------|--------------|
| Traitor's Bounty | Greed | Rogue PMC's bond becomes kill bounty for competitors |
| Individual Liability | Fear | Soldiers lose personal assets for illegal orders |
| Guardian Shares | Patriotism | 20-year vesting; treason burns pension |
| Logistics Firewall | Structure | Combat/Logistics PMCs legally separated |

### Traitor's Bounty
If PMC moves toward Capital without authorization:
1. Geofence triggers → Oracle flags as Rogue
2. Surety bond confiscated → posted as kill bounty
3. Every competitor notified: "Liquidate Rogue Alpha: $5B reward"

### Logistics Firewall
- Combat PMCs: Own weapons, hire soldiers; CANNOT own logistics
- Logistics PMCs: Own fuel depots, ammo factories; CANNOT own combat units
- Result: Coup force runs out of fuel in 72 hours

### 3-Day Leash
- Training stock: Regular exercises
- Ready load: 3 days high-intensity combat
- War reserve: Held by Logistics, released during active bounties

### Guardian Shares
Soldiers paid partly in National Equity vesting over 20 years:
- State prospers → Dividend grows
- Honorable retirement → Wealthy for life
- Treason conviction → Unvested equity burned

---

## 16.5 Defensive Mobilization

### Total Liability Call
```
On invasion detection:
  1. Calculate: "If we do nothing, damages = $5T"
  2. Therefore: "Spend $1T now to stop invasion"
  3. Insurers buy Defense Bonds within minutes
  4. PMCs receive unlimited funding immediately
```

### Market Veto
```
1. Leader posts metric-based Win Condition
2. Market evaluates — investors/insurers decide worth
3. If bids < cost → War cancelled (Market Veto)
4. If bids > cost → War proceeds with guaranteed funding
```

---

## 16.6 Offensive Operations (Conquest Rights Auction)

### Formal Definition
```
Government auctions titles to enemy assets:
  Class A: Ports, oil fields, factories
  Class B: Future tax revenue (20-year streams)

Investors bid to own these assets IF PMCs can secure them.
```

### Zero Taxpayer Cost
| Entity | Role | Risk |
|--------|------|:----:|
| Government | Escrow Administrator | Zero |
| Insurers | Defensive Capital | High |
| Investors | Offensive Capital | High |
| PMCs | Execution | High (operational) |
| Taxpayer | Receives Dividend | Zero |

---

## 16.7 Peaceful Accession Principle

### Formal Definition
```
The Liability State shall not extend jurisdiction by armed force over any territory
whose inhabitants had the option of peaceful immigration at the time of action.

Peaceful immigration = any person physically present may voluntarily enter LS territory
and claim citizenship without penalty/retaliation/restriction.

Exception: Territories whose government forcibly prevents emigration.
  Requirements for armed action:
    1. Operation insured and actuarially priced by private insurer
    2. All inhabitants receive full citizenship + Dividend from date of occupation
    3. All harm to non-combatants compensated under strict liability
```

### Freedom of Exit Determination (STO)
1. Compact petitions STO for determination
2. STO reviews evidence (published laws, border practices, traveler accounts, human rights assessments)
3. Target government may participate
4. STO issues ruling: **Open, Restricted, or Closed**
5. Open → Conquest constitutionally prohibited
6. Restricted → Must wait 2 years, petition again
7. Closed → Conquest constitutionally permitted

### Conquered Population Rights
| Right | Automatic From Occupation |
|-------|:-------------------------:|
| Citizen's Dividend | ✅ |
| Access to private courts | ✅ |
| Insurance coverage | ✅ |
| Free movement | ✅ |
| Harberger property rights | ✅ |
| Second-class status | ❌ (prohibited) |

---

## 16.8 Asymmetric Threats

### Prevention Chain
1. Attack destroys factory → Insurer pays damages
2. Loss spikes premiums for region/asset class
3. Infrastructure owners face higher costs
4. Owners collectively fund security through mutual pool
5. Market finds cost-effective countermeasure

### Border Failure Liability Chain
| Party | Liability |
|-------|-----------|
| Attacker | Primary (but typically no assets) |
| Enablers (transport, logistics) | Secondary — insurers pay, premiums rise |
| Compact border authority | Upstream — liable for negligent administration |
| Alliance border authority | Ultimate upstream — liable for inadequate screening |

---

## 16.9 Catastrophic Event Solvency

### Coverage Limits
Every insurance policy has coverage limits. Unlimited coverage has no price.

### Loss Dispersion
When total claims exceed industry reserves, every policy pays proportional fraction of face value.

### Dividend as Shock Absorber
Economic contraction → LVT ↓ → Dividend ↓ → every citizen shares small reduction.

### Structural Mitigations
1. Three-Source Mandate
2. Guild Mutual structure (small pools: 500–5,000)
3. Total Liability Call
4. Global reinsurance
5. Secondary claims market

---

# 17. Infrastructure & Property Rights

## 17.1 Roads as Subscription Services

### Source
08_infrastructure.md

| Type | Owner |
|------|-------|
| Highways | Large Logistics Guilds |
| Local Streets | Neighborhood Trusts (residents) |
| Bridges | Construction/Maintenance Guilds |

### Pothole Guarantee
If a pothole damages a vehicle, the road owner is **strictly liable**.
→ Road owners maintain obsessively to avoid claims.

### Easement of Necessity
- Every property has inherent "Right of Way"
- Road owner must permit passage for reasonable fee
- Cannot legally barricade residents

---

## 17.2 Grid & Utilities

### Micro-Grids (Natural Decentralization)
- Neighborhoods run own solar/generators
- Factories maintain backup power
- Main grid connection = backup only
- Liability for massive blackouts is astronomical → grid fragments

### Water Systems
- Local water trusts own treatment/distribution
- Competition on quality and reliability
- Liability for contamination drives safety investment

---

## 17.3 Property Rights

### Quiet Enjoyment Standard
| Violation | Response |
|-----------|----------|
| Neighbor blasts music at 2 AM | Bill for "Loss of Quiet Enjoyment" |
| Factory emits foul smell | Sue for property damage |
| Construction creates dust | Compensation for cleaning/health |
| Refusal to pay | Private court places lien on property |

### Visual Covenants (Contract-Based Zoning)
- Deed covenants when buying property
- Example: "I agree not to paint house neon pink"
- Voluntary contract, not government mandate
- Breach = breach of contract → lawsuit from neighbors

### Good Samaritan Exception (Emergency Privilege)
| Scenario | Ruling |
|----------|--------|
| Trespassing to escape fire | Not liable (life > property) |
| Broke fence while escaping | Still owe for fence repair |

---

## 17.4 Public Spaces as Trust-Managed Commons

### Structure
- Parks, squares, wildlands owned by **Private Trusts**
- Trustees have fiduciary duty to maintain
- "Public" = anyone can use
- "Private" = trustees can exclude troublemakers
- If park becomes dangerous → trustees face lawsuits

### Environmental Protection
- Rivers placed in environmental trusts
- Trustees have fiduciary duty to water quality
- Company dumps waste → Trust sues for property damage
- Replaces "environmental fines" with specific claims

---

## 17.5 Contract Culture (Private Jurisdictions)

### Municipal Subscription Model
| Traditional City | Municipal Corporation |
|-----------------|----------------------|
| Subject to laws | "Subscribe" to services |
| Taxes mandatory | Fees for services used |
| No exit option | Can move to different provider |

### Digital Identity Contract Negotiation
- Walk into mall → entering private jurisdiction
- Sign: "By entering, you agree to arbitration for disputes"
- Digital identity auto-negotiates terms
- "I only agree to ISO-Certified arbiters" → "We only use Certified Arbiters" → phone pings "Agreement Signed"

---

# 18. Social Services & Welfare

## 18.1 Citizen's Dividend as Safety Net

See [§3.1](#31-dividend-calculation). The dividend IS the welfare system. No separate welfare bureaucracy.

---

## 18.2 Disability Care — Genetic Lottery Pool

### Source
09_social_services.md

### Accident-Caused Disability
- Insurance pays immediately
- Tort settlement covers lifetime care + lost wages
- Courts enforce full compensation

### Congenital/No-Fault Disability
| Step | Mechanism |
|:----:|-----------|
| 1 | Fixed % of LVT revenue → High-Risk Reinsurance Pool |
| 2 | Three independent, randomly-selected physicians diagnose |
| 3 | If all 3 concur on diagnosis code → coverage activates automatically |
| 4 | Fraud check: colluding doctors face fraud liability + license revocation |

### Coverage Includes
- Medical care (market-rate for diagnosis)
- Support equipment (patient chooses provider)
- Living assistance (based on independence level)

---

## 18.3 Unemployment Insurance

### Rule
Mandatory (like car insurance):
- Lose job → private insurer pays
- Chronically unemployed due to laziness → premiums spike
- Eventually dropped → must rely on (smaller) Dividend
- Incentive to stay employable

---

## 18.4 Guild Safety Nets (Fraternal Benefits)

As a guild member:
- Pay dues
- If sick/injured, guild covers you
- Not state welfare — fraternal benefit
- Local, personal, efficient

### Fraud Prevention vs Bureaucracy
| Government Bureaucrat | Guild Brothers |
|----------------------|---------------|
| Distant, impersonal | Know you personally |
| Easy to fool | Know if you're faking |
| No stake in outcome | Their dues fund your claim |

---

## 18.5 Education System

### Source
09_social_services.md

### Education Wallet
- Every child receives dedicated Dividend portion
- Can **only** be spent on education
- Follows the child, not the school

### Micro-Schools
| Traditional | Micro-School |
|-------------|--------------|
| 2,000 students | 15 students in workshop |
| Standardized curriculum | Specialized learning |
| One-size-fits-all | Physics taught through rebuilding engines |

### Early Apprenticeship
Around age 12-14, children can bid their Education Wallet to join a Guild.

### Masterpiece Graduation
| Traditional | Liability State |
|-------------|----------------|
| Pass scantron test | Produce a Masterpiece |
| Credential = attendance | Credential = demonstrated skill |
| Easy to fake | Judged by Guild Elders |

Examples: Build a functional robot, write a novel, machine a precision turbine.

---

## 18.6 Child Protection — Abuse Bounty

### Source
09_social_services.md

### Mechanism
| Step | Description |
|:----:|-------------|
| 1 | Mandatory reporter or Trust Broker-endorsed claimant files suit |
| 2 | Private court investigates with expedited timeline |
| 3 | If abuse substantiated → court orders parents' assets/insurer to pay |
| 4 | Bounty portion to claimant (court discretion, published precedent) |
| 5 | Restitution for child relocation, therapy, housing |
| 6 | Court determines placement (family, guild, or private care) |

### Anti-Fraud Protections
| Risk | Mitigation |
|------|-----------|
| False reports for bounty | Loser Pays + lowered litigation bond; cap bounty at ~$50K |
| Wealthy parent targets | Court discretion on bounty percentage |
| Cultural variation | Regional Compacts define abuse standards |
| Gaming by parents | Child Dividend locked in trust (no profit motive) |

---

# 19. Taxation Suite

## 19.1 LVT (Primary Revenue)

See [§1.1](#11-land-value-tax--budget-first-cap).

---

## 19.2 Inheritance Tax — The Merit Razor

### Formal Definition
```
Rate: 50%+
Payment: Can be paid in non-voting equity (not just cash)

If heir cannot pay cash:
  Government/Trust takes 50% of shares
  Heir keeps control, runs business
  50% of future dividends go to public
```

### Source
10_taxation.md

### The Liquidity Problem Fixed
| Problem | Solution |
|---------|----------|
| Heir can't pay cash | Pay in equity |
| Forces sale of productive business | Heir keeps control |
| Destroys family enterprise | Business survives; unearned wealth flows to citizens |

---

## 19.3 Vacancy Tax

### Formal Definition
```
If property unoccupied ≥6 months/year:
  Tax_Rate = 3 × Standard_LVT_Rate
Else:
  Tax_Rate = Standard_LVT_Rate
```

### Source
10_taxation.md

---

## 19.4 Severance Tax (Raw Material)

### Rule
Tax resources at **Point of Extraction**:
- New materials become expensive → recycling is profitable
- Circular economy emerges (scrap is tax-free)
- Conservation incentivized without bans

---

## 19.5 Sin Taxes (Actuarial, Not Moral)

### Rule
Tax cigarettes to fund **Cancer Treatment Risk Pool**, not general government.
- Smoker pays extra fee → High-Risk Health Insurance pool
- Pre-paying their own future medical costs
- Pure actuarial pricing, not moral judgment

---

## 19.6 Automation Ratio Shift

### Formal Definition
```
Human_to_Revenue_Ratio = Employees / Revenue

If high (employing people) → Discount on LVT rate
If low (fully automated) → Full LVT rate
```

### Source
10_taxation.md

---

## 19.7 Full Expensing (CapEx Incentive)

### Rule
```
Profit = $1M
If spent $1M on equipment → Taxable_Income = $0
If kept $1M as cash → Taxable_Income = $1M (taxed fully)
```

Forces companies to reinvest profits. Makes cash hoarding expensive.

---

## 19.8 Feebate Model (Revenue Neutral)

### Source
10_taxation.md

### Example: Vehicles
| Action | Effect |
|--------|--------|
| Buy gas guzzler (15 MPG) | Pay $2,000 fee |
| Buy efficient car (45 MPG) | Receive $2,000 rebate |

### Properties
- Self-funding: fee funds the rebate (no treasury drain)
- Dynamic: if everyone buys efficient → fees dry up, rebates dry up
- Self-terminating: system turns off when goal achieved

---

# 20. Immigration & Border System

## 20.1 Citizenship Bond

### Source
11_immigration.md

### Formal Definition
```
To become a citizen, a foreigner must pay a Citizenship_Bond:
  Fee = Variable (adjusted to maintain target immigration flow)
  Financing: Guild sponsorship as collateral
  Insurance_Sponsorship: Endorsed by certified domestic insurer
  Children: Enter Child Trust system automatically upon parent's citizenship
```

---

## 20.2 Insurance Sponsorship Requirement

### Process
1. Insurer vets immigrant (background check, financial standing)
2. If approved, insurer posts **Surety Bond** covering immigrant's liability for 5 years
3. If immigrant causes uncompensated harm → insurer pays
4. If insurer fails to vet → absorbs full cost

### Effect
Insurers become border guards — financial incentive to admit low-risk, exclude high-risk.

---

## 20.3 Temporary Visitation

### Formal Definition
```
Per_daily_pass_cost = Liability_Insurance_Coverage / Duration_Days + Underwriting_Fee
Duration: Fixed term (e.g., 90 days), renewable from outside country
Overstay: Automatically uninsured → cannot rent, work, or engage in commerce
Conversion: Can convert to citizenship by paying remaining bond difference
```

---

## 20.4 Illegal Immigration Liability Gap

### Rule
```
It is illegal to do business with an uninsured person.
```

| Violation | Consequence |
|-----------|-------------|
| Renting to uninsured tenant | Landlord fully liable for all tenant damages |
| Employing uninsured worker | Employer fully liable for all worker actions |
| Selling to uninsured buyer | Seller liable for downstream harm |

### Net Effect
Market excludes illegals more efficiently than any border patrol — cannot rent, work, buy car, sign phone contract.

---

## 20.5 Guild Sponsorship Loop

1. Guild needs more workers (shortage)
2. Guild sponsors foreigner: pays Citizenship Bond + provides insurance
3. Immigrant gets citizenship + job
4. Immigrant repays guild through wage garnishment or service contract
5. If immigrant reneges, guild is insured against loss

Self-balancing: If genuine labor shortage → guild pays premium to import. If domestic workers available → importing is more expensive.

---

## 20.6 Asylum & Humanitarian Cases

| Case | Mechanism |
|------|-----------|
| Refugee | Humanitarian Sponsor Bond: guild/Trust Broker sponsors liability for 5 years |
| Stateless person | Assigned Risk Pool covers liability at standard rates; Compacts rotate responsibility |

---

# 21. Guild System

## 21.1 Guild Structure

### Source
09_social_services.md, 07_defense_military.md

### Functions
1. **Certification**: Guild seals for quality assurance (Trust Brokers)
2. **Mutual Insurance**: Guild mutuals (500–5,000 members) as self-insurance pools
3. **Safety Nets**: Fraternal benefits for sick/injured members
4. **Apprenticeship**: Education wallet funding for trade training
5. **Sponsorship**: Guild-driven immigration for labor shortages
6. **Masterpiece Graduation**: Guild Elders judge skill demonstrations
7. **Liability**: Guild mutuals bear secondary liability for member firms' employment practices

### Guild Bank (Credit Union)
- Owned by trade members
- Serves that trade's financial needs

---

## 21.2 Guild Mutual Liability

### Rule
If guild knew/should have known a member firm was suppressing evidence through void contract provisions → guild faces liability adjustments from Actuarial Commons.

### Source
04_legal_system.md

---

# 22. AI as Legal Actor

## 22.1 Default Liability Rule

### Source
04_legal_system.md

### Formal Definition
```
AI has no moral agency and no wallet.
Liability falls on the natural or legal persons who:
  - Deployed, designed, funded, or benefited from the AI's actions.

This is product liability extended to software.
```

---

## 22.2 Specific Scenarios

| Scenario | Liable Party | Mechanism |
|----------|-------------|-----------|
| Autonomous vehicle kills pedestrian | Owner/operator (strict) + manufacturer (product defect) | Standard liability chain |
| LLM hallucination causes financial loss | Deployer (inadequate safeguards) + manufacturer (defect) | Professional/product liability |
| AI trading bot causes flash crash | Operator (inadequate fail-safes) + developer (code defect) | Market liability |
| Autonomous drone damages property | Operator (strict) + manufacturer (defect) | Standard + product liability |
| AI generates harmful content | Deployer (inadequate filtering) + training data curator | Foreseeable misuse |
| AGI causes systemic harm | Deployer (failed control systems) | Systemic liability |

---

## 22.3 Beneficiary Liability Principle

### Rule
If immediate deployer cannot be identified/pay, liability falls on **beneficiaries** — those who received value from AI's actions.

| Scenario | Liable |
|----------|--------|
| Autonomous agent raises capital, causes harm | Investors who accepted returns |
| AI agent defaults on contracts | Counterparties who accepted AI's performance |
| AI swarm coordinated without clear owner | Proportional liability by funding share |

### Analogy
Structurally identical to partnership law. AI agent = algorithmic general partner. Limited partners accepting returns = vicariously liable.

---

# 23. Cross-Border Enforcement

## 23.1 Insurance Chain Enforcement

### Source
04_legal_system.md

### Process
1. Foreign corporation causes harm within LS
2. Local insurer pays judgment to victim
3. Insurer holds right of subrogation → pursues foreign corporation for reimbursement
4. Insurer has capital, legal teams, global standing
5. Pursuit is private contract enforcement, not state action

### Comparison
| Mechanism | Limitation |
|-----------|------------|
| State asset recovery | Requires diplomatic pressure, treaties |
| Victim lawsuit | Individual lacks capital for cross-border |
| Insurance chain | Private contract action, globally recognized |

---

## 23.2 Foreign Insurer Bonding

### Requirements
| Requirement | Purpose |
|-------------|---------|
| Post surety bond within LS jurisdiction | Recoverable capital if exit |
| Use Actuarial Commons published models | Prevents data-moat arbitrage |
| Glass Box transparency for all LS operations | Prevents hiding liabilities |
| Bond forfeiture on violation | Penalty for cheating |

### Market Exit Penalty
- Primary deterrent: loss of ALL LS customers
- Decertified insurer → every LS policyholder must obtain new coverage
- Double penalty: bond forfeiture + market exit

---

# 24. Catastrophic Event & Solvency

## 24.1 Coverage Limits

Every policy has explicit limits. Unlimited coverage cannot be priced.

## 24.2 Loss Dispersion

```
If Total_Claims > Industry_Reserves:
  Payout_Ratio = Industry_Reserves / Total_Claims
  Each claimant receives: Claim_Amount × Payout_Ratio
```

## 24.3 Dividend Shock Absorption

```
Economic Contraction → LVT_Revenue ↓ → Dividend ↓ → All citizens share reduction
```

This is embedded social insurance without explicit mechanism.

## 24.4 Structural Mitigations

1. **Three-Source Mandate**: No single pool holds concentrated exposure
2. **Guild Mutuals**: Small pools (500–5,000) cannot be simultaneously destroyed
3. **Total Liability Call**: Insurers fund relief → cheaper than paying claims
4. **Global Reinsurance**: Foreign reinsurers diversify risk
5. **Secondary Claims Market**: Claimants sell unpaid judgments for immediate partial liquidity

---

# 25. System Evolution Loops

## 25.1 Safety Loop

```
Harm → Insurer pays victim → Premiums rise → Safety investment → Lower premiums
```

Actors: Insurer ↔ Business

## 25.2 Justice Loop

```
Harm → Victim files suit (with litigation bond) → Private court adjudicates
  → Loser pays all legal fees → Precedent set
```

Actors: Victim ↔ Court ↔ Defendant

## 25.3 Evolution Loop (Primary Adaptation Mechanism)

### Source
04_legal_system.md, 00_overview.md

### Process
1. **Knowledge advances**: Scientific discovery reveals new harm
2. **Standard of care shifts**: After knowledge available, continuing behavior falls below reasonable care
3. **Liability attaches**: Courts find liability for failure to adapt to known risk
4. **Insurers price the shift**: Premiums rise industry-wide
5. **Behavior changes**: Harmful practice becomes more expensive than alternative

### Why Faster Than Legislation
- No regulatory lag — standard shifts the moment knowledge is published
- Insurers update premiums immediately (financial interest aligns)
- Self-sunsetting: when risk recedes, liability recedes — no law to repeal

---

## 25.4 Long-Latency Harm

### Mechanism
If company dumps substance KNOWN to cause harm (even if 30-year latency):
- Harm is foreseeable
- Lawsuit can be brought NOW (before symptoms)
- Damages based on: actuarial probability × expected severity × population exposed
- Insurer pays immediately; premiums rise; behavior stops

### If Harm Was NOT Known
- Genuine accident — insurance covers it
- No liability for past (standard of care was met)
- Premiums may rise for future once knowledge available

---

## 25.5 Pure Novelty & Emerging Technologies

### Process
1. **Insurer demands court guidance**: No insurer will underwrite novel high-risk activity without court defining liability exposure
2. **Court sets standard**: Hears experts, examines tech, issues ruling establishing standard of care
3. **Insurer calibrates**: Premium reflects gap between court standard and operator's practices
4. **Bad standards self-correct**: If court set too lax → catastrophic liability → court loses credibility
5. **Precedent grows**: Courts publish reasoned rulings; insurers build actuarial models

---

## 25.6 Court-Sues-Court Mechanism

### Source
04_legal_system.md

DROs (private courts) carry liability insurance for adjudicative negligence.

| Scenario | Mechanism | Outcome |
|----------|-----------|---------|
| Unsound ruling | Losing party appeals or sues for adjudicative negligence | First court pays damages, premiums rise |
| Systematic bias | Actuarial Commons flags pattern; insurer raises premiums | Court cannot operate without insurance |
| Captured by repeat litigant | Insurers whitelist competing courts, blacklist captured | Business flows away |

### Result
Only courts producing sound, evidence-grounded, fair rulings survive. Unreasonable courts become uninsurable.

---

## 25.7 Trust Loop (Private Civil Servants)

### Source
00_overview.md

1. Probable cause → whistleblower/insurer presents evidence to private court
2. Warrant issued → court reviews ex parte
3. Deep audit → 2-3 PCSs from independent networks inspect secret data
4. Attestation → public verification without revealing secrets
5. Consequence → if violation found, company faces liability

---

## 25.8 Enforcement Cascade (Inter-Compact)

1. Dispute arises between compacts
2. Private court — compacts agree on neutral venue; court issues resolution
3. Compliance — 95%+ comply voluntarily (or Good Faith Bond covers judgment)
4. Escalation — if compact refuses, dispute escalates to Supreme Trust Oracle
5. STO enforcement — Trust Blockade invalidates rogue compact's land titles, or Good Faith Bond liquidated

---

# Parameter Summary Table

| Parameter | Default/Source | Applies To |
|-----------|---------------|------------|
| LVT Rate | Budget-First Cap formula | All LVT |
| Physical Land LVI Weight | ≥60% constitutional floor | Currency backing |
| Alliance Skim | 10% of compact LVT | National Trust |
| Free Window | 14 days | Option Premium |
| Penalty Rate | 15% of offer | Option Premium |
| Bond Lockup | 90 days max | Option Premium |
| Dividend Floor | Subsistence in cheapest area | Citizen's Dividend |
| Dividend Recalc | Every 5 years | Citizen's Dividend |
| Emergency Powers Duration | 90 days (renewable once) | Bonded Executive |
| Oversight Panel Term | 6 months | Executive Oversight |
| Panel Stagger | Every 2 months | Executive Oversight |
| House of Repeal Supermajority | 75% | Constitutional changes |
| Victory Bond Face | $1.00 | War Escrow |
| Escrow Split | 90/10 (Victory/National Trust) | War Escrow |
| Citizenship Bond | Variable (market-adjusted) | Immigration |
| Insurance Sponsorship Term | 5 years | Immigration |
| Visitor Pass Duration | 90 days (renewable from outside) | Immigration |
| Vacancy Tax Multiplier | 3× LVT | Vacancy Tax |
| Inheritance Tax | 50%+ | Inheritance Tax |
| Tobin Tax | 0.1% per transaction | Financial Transactions |
| Child Trust Unlock | Age 18 or trade school | Blind Trust Lockbox |
| Bounty Cap (Child Abuse) | ~$50K | Child Protection |
| PCS Bond Multiplier | 10× economic stake inspected | Private Civil Servants |
| PCS Minimum | 2-3 per inspection | Private Civil Servants |
| Assigned Risk Pool Cap | 300% of standard rate | Insurance |
| Court Audit Rotation | 20% annually | Legal System |
| Alliance Charter | 10-year sunset | National Alliance |
| Good Faith Bond | Legal system default | Inter-Compact disputes |
| Military Temporal Secret | 2-5 year unlock | Glass Box State |
| LVT Future Term | Next fiscal year | LVT Revenue Futures |
| War Bond Threshold | Market Veto (bids < cost) | Defense |
| Class B Concession Term | 20-year tax stream | Offensive War |
| New Territory Phase-In | 10 years | Monetary System |
| LVI Recalculation | Daily | Monetary System |
| LVI Component Weighting | 5-year trailing average | Monetary System |
| LVI Stress Threshold | 90% residual backing | Monetary System Intervention |

---

*End of Mechanics Inventory*

Generated from all 13 files in `/2_Laws_and_Functions/`:
00_overview.md, 01_economic_architecture.md, 02_financial_system.md, 03_investment_engine.md, 04_legal_system.md, 05_fraud_prevention.md, 06_political_structure.md, 07_defense_military.md, 08_infrastructure.md, 09_social_services.md, 10_taxation.md, 11_immigration.md, 12_monetary_system.md
