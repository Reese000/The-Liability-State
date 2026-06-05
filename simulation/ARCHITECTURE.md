# Simulation — Architecture Specification

## 1. Rule Enforcement: Simulating the Liability State's Actual Enforcement

**Critical principle: The simulation must NOT have a central "law enforcement" agent that detects and punishes all violations.** The LS has no police, no regulators, no compliance inspectors. Enforcement happens through the same mechanisms available to real agents: detection, litigation, and market consequences.

### How Enforcement Works in the LS (and in the Simulation)

| Violation | Who detects it | How they detect it | Consequence |
|-----------|---------------|-------------------|-------------|
| **Insurance fraud** (fake claim) | Insurer | Claims investigation (probabilistic detection) | Claim denied + policy cancelled + blacklisted from other insurers |
| **Premium evasion** (under-reporting risk) | Insurer or competitor | Actuarial audit, statistical outlier detection | Back premiums owed + penalty + premium increase |
| **Harberger under-declaration** | Any buyer | Anyone can buy at declared price (self-enforcing) | Loss of property |
| **Contract breach** | Counterparty | They know they were harmed | File a court case |
| **Pollution / externalized harm** | Victim or their insurer | Victim experiences harm, insurer investigates cause | Court case → damages awarded |
| **Guild certification fraud** | Guild or customers | Shoddy work detected by buyer or guild audit | Guild expulsion, liability for damages |
| **Court corruption** | Other courts, litigants | Inconsistent rulings, suspicious pattern | Reputation loss, cases migrate to other courts |
| **Collusion / price fixing** | Competitors, customers | Above-market pricing detected | Court case under antitrust liability |
| **Glass Box violation** (hiding data) | Any citizen, competitor, Actuarial Commons | Missing or non-replicable data | Liability for obstruction, reputational damage |
| **Operating without insurance** | Insurers, courts, counterparties | Can't show proof of coverage when required | Personal liability for any harm, cannot operate |

### Detection Probability

Each violation has a **base detection probability** that depends on:

| Factor | Effect on detection |
|--------|-------------------|
| **Transaction visibility** | Glass Box transactions = high detection. Off-ledger deals = low detection |
| **Number of parties** | More parties = higher chance someone notices |
| **Magnitude** | Larger violations = more visible |
| **Sophistication** | Complex schemes = harder to detect |
| **Insurer auditing frequency** | Regular audits = higher detection of insurance-related violations |

Detection probability is modified by agent investment in concealment (e.g., off-ledger payments, shell companies, complex contract structures).

### The Enforcement Flow

```
Agent commits violation
        │
        ▼
Detection roll (based on violation type + concealment)
        │
    ┌───┴───┐
    │       │
   Miss    Hit
    │       │
    ▼       ▼
No         Counterparty identified
consequence   │
              ├─ Can they sue? (legal standing, evidence, cost vs expected award)
              │     │
              │     ▼
              │  Yes → File court case
              │     │
              │     ▼
              │  Court evaluates:
              │    • Was there harm? (causation)
              │    • Was defendant liable? (standard of care, foreseeability)
              │    • Damages calculation
              │    • Did defendant have insurance? (insurer pays)
              │
              ├─ Market consequence (reputation, premium adjustment)
              │
              └─ Regulatory consequence (Glass Box: automatic for some violations)
```

**The simulation does not enforce rules. The simulation models detection, litigation, and consequence. Agents only face consequences if someone detects and acts.**

---

## 2. Objective Metrics Recording

### The Ledger System

Every economic entity (agent, company, court, insurance pool, guild, Alliance, compact) has a **double-entry ledger**. Every step:

1. All inflows and outflows are recorded
2. Ending balances are computed
3. The **zero-sum invariant** is checked: total money in the system before step = total money after step (unless money is explicitly created or destroyed by a mechanic)

### Ledger Entry Schema

```
step: int              # Which step
entity_id: str         # Who
counterparty_id: str   # Who they transacted with
mechanism: str         # What caused the flow (lvt, dividend, premium, claim, etc.)
amount: float          # How much
balance_before: float  # Entity's balance before
balance_after: float   # Entity's balance after
description: str       # Human-readable
```

### Flow Matrix

A 2D array where `flow[A][B]` = total dollars moved from entity A to entity B this step.

| From \ To | Citizens | Trust | Alliance | Insurers | Courts | Guilds | Total Out |
|-----------|----------|-------|----------|----------|--------|--------|-----------|
| **Citizens** | — | LVT | — | Premiums | Fees | Dues | ... |
| **National Trust** | Dividend | — | Skim | — | — | — | ... |
| **Alliance** | Refund | — | — | War bonds | — | — | ... |
| **Insurers** | Claims | — | — | — | — | — | ... |
| **Courts** | Awards | — | — | — | — | — | ... |
| **Guilds** | Benefits | — | — | — | — | — | ... |
| **Total In** | ... | ... | ... | ... | ... | ... | Σ = 0 ✓ |

### Balance Sheet (per agent)

```
cash: float                    # Liquid currency
land_value: float              # Current assessed value of owned land
property_count: int            # Number of parcels owned
insurance_policies: list       # Active insurance contracts
guild_memberships: list        # Active guild memberships
outstanding_liability: float   # Total unpaid court judgments against agent
outstanding_claims: float      # Total unpaid claims agent is owed
expected_premium: float        # Premium due next period
lvt_due: float                 # LVT due next period
```

### Aggregate Metrics (computed from ledgers each step)

| Metric | Formula |
|--------|---------|
| **Total LVT collected** | Σ all LVT payments this step |
| **Total Dividend paid** | Σ all Dividend payments this step |
| **Total Premiums** | Σ all premium payments this step |
| **Total Claims paid** | Σ all claim payments this step |
| **Insurance pool solvency** | (Total reserves) / (Expected future claims) |
| **Gini coefficient** | Standard calculation from wealth distribution |
| **Litigation rate** | Cases filed / total agents |
| **Court backlog** | Pending cases / number of judges |
| **Premium-to-claim ratio** | Total premiums / total claims (rolling window) |
| **Harberger valuation gap** | Median(declared value / estimated true value) |
| **Evasion rate** | Estimated violations / total transactions |
| **Bankruptcy rate** | Agents with negative net worth / total agents |
| **Compact migration rate** | Agents who switched compacts / total agents |
| **Market concentration (insurance)** | Herfindahl index of premium market share |
| **Market concentration (land)** | % of land owned by top 10% of landowners |
| **Dividend as % of median income** | Dividend amount / median labor income |
| **Agent satisfaction** | Composite wellbeing score (see below) |

### Agent Wellbeing Score (per step)

```
wellbeing = 0.3 × wealth_score
          + 0.2 × security_score    # Insurance coverage, liability exposure
          + 0.15 × freedom_score    # Ability to act without permission
          + 0.15 × community_score  # Guild membership, trust network size
          + 0.10 × purpose_score    # Has meaningful work, advancing
          + 0.10 × stability_score  # Low volatility in income/expenses
```

Each sub-score is normalized 0-1.

---

## 3. Event System

### Event Definition

```
Event:
  name: str
  type: enum(EXTERNAL, INTERNAL)
  trigger:
    type: enum(TIMED, PROBABILISTIC, CONDITIONAL)
    step: int | None          # For TIMED: which step to fire
    probability: float | None # For PROBABILISTIC: per-step chance
    condition: str | None     # For CONDITIONAL: function reference
  effects:
    - target: str             # What system/agent type to affect
      mechanic: str           # What to change
      magnitude: float        # How much
      duration: int           # How many steps it lasts
      recovery: str           # How the system heals
  description: str
```

### Event Types

| Event | Type | Trigger | Effect |
|-------|------|---------|--------|
| **Natural disaster** | EXTERNAL | Conditional (seismic zone) or timed | Reduces land values in affected compacts by X%. Generates health claims. Damages infrastructure. |
| **Foreign invasion** | EXTERNAL | Conditional (border compact) or timed | Triggers war bond mechanism. Damages property. Generates casualty claims. |
| **Mass tort** | INTERNAL | Probabilistic (increases with unsafe activity) | Batch of related liability claims filed simultaneously. Tests court capacity and insurer solvency. |
| **Technology disruption** | EXTERNAL | Timed | Reduces demand for specific occupations. Triggers Harberger IP revaluation. |
| **Insurance market failure** | INTERNAL | Conditional (when pool solvency < threshold) | Major insurer fails. Claims go unpaid. Remaining insurers raise premiums. |
| **Guild scandal** | INTERNAL | Probabilistic (increases with unmonitored guild power) | Guild certification discredited. Members face liability for substandard work. |
| **Compact secession** | INTERNAL | Conditional (when compact dissatisfaction > threshold) | Compact attempts to leave. Triggers STO enforcement. Trade disruption. |
| **Pandemic** | EXTERNAL | Timed | Universal health claims. Reduced labor capacity. Business closures. |
| **Population shock** | EXTERNAL | Timed | Sudden immigration/emigration. LVT base expands/contracts. |
| **Class action** | INTERNAL | Conditional (when similar harms affect many agents) | Large coordinated lawsuit against a single defendant or industry. |

### Event Recovery

After an event, the system heals according to specified recovery rules:

| Recovery type | How it works |
|---------------|-------------|
| **Linear** | Effect magnitude decreases by X% per step until zero |
| **Exponential** | Effect decays at rate λ: magnitude(t) = magnitude₀ × e^(-λt) |
| **Market-driven** | Recovery speed depends on how much agents invest in rebuilding |
| **Permanent** | Some effects (e.g., compact secession) are structural changes, not temporary shocks |

---

## 4. Agent Interaction Model

### Interaction Types

All agent interactions happen through **markets** and **contracts**. There is no direct agent-to-agent action outside these channels.

#### Market: Labor

```
Worker                             Business
  │                                    │
  │  Offers labor at reservation wage  │
  │ ─────────────────────────────────> │
  │                                    │
  │           Hires at offered wage     │
  │ <───────────────────────────────── │
  │                                    │
  │  Works (productivity depends on    │
  │  skill, guild certification)       │
  │ ─────────────────────────────────> │
  │                                    │
  │           Paid wage                │
  │ <───────────────────────────────── │
```

#### Market: Insurance

```
Agent                              Insurer
  │                                    │
  │  Requests quote (declares risk     │
  │  profile, may under-report)        │
  │ ─────────────────────────────────> │
  │                                    │
  │           Offers premium based on   │
  │           declared risk + audit    │
  │ <───────────────────────────────── │
  │                                    │
  │  Accepts, pays premium             │
  │ ─────────────────────────────────> │
  │                                    │
  │           Coverage active          │
  │           (or detects fraud if     │
  │           declared vs actual risk  │
  │           mismatch detected)       │
```

#### Market: Property (Harberger)

```
Buyer                              Seller
  │                                    │
  │  Sees declared price of parcel     │
  │                                    │
  │  Posts bond at declared price      │
  │ ─────────────────────────────────> │
  │                                    │
  │  ┌─ 14-day free refusal window     │
  │  │  Seller may refuse at no cost   │
  │  │  (tax basis still rises)        │
  │  │                                 │
  │  ├─ Day 15-90: penalty phase       │
  │  │  Seller refuses → pays 15%     │
  │  │  Seller accepts → sale proceeds │
  │  └─────────────────────────────────│
```

#### Interaction: Court Case

```
Plaintiff                          Court                          Defendant
  │                                    │                               │
  │  Files claim (pays filing fee)     │                               │
  │ ─────────────────────────────────> │                               │
  │                                    │                               │
  │                                    │  Sends summons               │
  │                                    │ ────────────────────────────> │
  │                                    │                               │
  │                                    │  Responds (or defaults)      │
  │                                    │ <──────────────────────────── │
  │                                    │                               │
  │  ┌─ Court evaluates:               │                               │
  │  │  • Harm (did it occur?)         │                               │
  │  │  • Causation (was defendant     │                               │
  │  │    the cause?)                  │                               │
  │  │  • Liability (did defendant      │                               │
  │  │    breach standard of care?)    │                               │
  │  │  • Damages (what is owed?)      │                               │
  │  └─────────────────────────────────│                               │
  │                                    │                               │
  │  Award (or dismissal)              │                               │
  │ <─────────────────────────────────│                               │
  │                                    │                               │
  │                                    │  Pays award (or insurer pays)│
  │                                    │ <──────────────────────────── │
```

#### Interaction: Guild

```
Worker                              Guild
  │                                    │
  │  Applies for membership            │
  │  (pays certification fee)          │
  │ ─────────────────────────────────> │
  │                                    │
  │  ┌─ Evaluates:                     │
  │  │  • Skill test (or certification)│
  │  │  • Background check             │
  │  │  • Capacity (if closed shop)    │
  │  └─────────────────────────────────│
  │                                    │
  │           Accepted/rejected        │
  │ <───────────────────────────────── │
  │                                    │
  │  Pays ongoing dues                 │
  │ ─────────────────────────────────> │
  │                                    │
  │           Receives guild benefits  │
  │           (mutual insurance,       │
  │           certification, network)  │
```

### Agent Decision Making

Each step, agents evaluate their options using **expected value** with **bounded rationality**:

```
For each possible action A:
  expected_value(A) = P(success) × reward(A) + P(failure) × penalty(A)
                     + P(detection) × detection_penalty(A)
                     + non_monetary_factor(A)  # wellbeing, risk tolerance, honesty
  
  If expected_value(A) > expected_value(current_behavior) * (1 + inertia_threshold):
    switch to A
```

The **inertia threshold** represents the effort of changing behavior — agents don't instantly optimize every step.

The **honesty parameter** (0-1) is a multiplier on expected value from exploitative actions:
- honesty = 0.8: the agent feels bad about cheating, effectively discounts exploitative gains by 20%
- honesty = 0.2: the agent is mostly amoral

This prevents every agent from becoming a perfect sociopath while still allowing exploitation when the rewards are high enough.

### Agent Types

| Type | Primary goal | Interactions | Decision variables |
|------|--------------|--------------|-------------------|
| **Worker** | Maximize income + security | Labor market (sell labor), insurance market (buy), property market (rent/buy), guild (join) | Hours worked, occupation, which compact to live in, risk to insure, honesty level |
| **Business** | Maximize profit | Labor market (hire), insurance market (buy), property market (buy/lease), goods market (sell), court (sue/be sued) | Price of goods, wages offered, care level (safety investment), expansion/contraction |
| **Insurer** | Maximize underwriting profit | Insurance market (sell policies), investment market (invest reserves) | Premium pricing, risk assessment accuracy, claims payout speed, reserve allocation |
| **Guild** | Maximize member welfare | Guild market (certify), mutual pool (collect dues/pay benefits) | Certification standards, dues level, membership cap, lobbying effort |
| **Court** | Maximize reputation + revenue | Court market (sell adjudication services) | Fee level, judgment bias, speed of rulings |

---

## 5. Simulation Flow

```
for each step in range(total_steps):
    # 1. Events
    for each event:
        if event.should_fire(step):
            event.apply(environment)
    
    # 2. Revenue collection (compulsory)
    for each agent:
        collect_lvt(agent)        # Based on land holdings
        collect_insurance_premiums(agent)  # Based on active policies
    
    # 3. Economic activity (interactions)
    for each market:
        market.step()  # Labor, goods, property, etc.
    
    # 4. Insurance claims
    for each accident that occurred:
        process_insurance_claim(accident)
    
    # 5. Court system
    for each pending case:
        court.adjudicate(case)
        enforce_judgment(case)   # Transfer money, update ledgers
    
    # 6. Dividend distribution
    total_lvt = sum(all_lvt_collected)
    alliance_skim = total_lvt × 0.10
    dividend_pool = total_lvt × 0.90
    refund_pool = alliance_skim - alliance_spending
    distribute_dividend(dividend_pool / agent_count)
    distribute_refund(refund_pool proportional to compact contribution)
    
    # 7. Agent planning
    for each agent:
        agent.evaluate_options()
        agent.take_action()
    
    # 8. Recording
    ledger.close_step()
    flow_tracker.update()
    metrics.compute()
    wellbeing.update()
    structures.detect()
    failures.check()
```

---

## 6. Key Data Structures

```python
@dataclass
class LedgerEntry:
    step: int
    entity_id: str
    counterparty_id: str
    mechanism: str          # 'lvt', 'dividend', 'premium', 'claim', 'wage', etc.
    amount: float
    balance_before: float
    balance_after: float
    description: str

@dataclass
class Contract:
    id: str
    type: str               # 'employment', 'insurance', 'property', 'guild'
    party_a: str            # Agent ID
    party_b: str            # Agent ID
    terms: dict             # Price, duration, conditions
    start_step: int
    end_step: int | None
    disputes: list[str]     # Case IDs for any litigation

@dataclass
class CourtCase:
    id: str
    plaintiff: str
    defendant: str
    harm_description: str
    amount_claimed: float
    evidence_strength: float   # 0-1
    filed_step: int
    adjudicated_step: int | None
    outcome: str | None         # 'dismissed', 'plaintiff_win', 'defendant_win'
    award: float | None
    court_id: str

@dataclass
class InsurancePolicy:
    id: str
    policyholder: str
    insurer: str
    declared_risk: float
    actual_risk: float          # Hidden, known only to policyholder
    premium: float
    coverage_limit: float
    active: bool
    fraud_suspicion: float      # 0-1, builds as claims don't match declared risk

@dataclass
class HarbergerParcel:
    id: str
    owner_id: str
    declared_value: float
    assessed_for_lvt: float     # = declared_value
    bids: list                  # Pending purchase attempts
    last_sale_price: float      # Most recent transaction price
```

---

## 7. Adversarial Strategy Controller

```python
class StrategyController:
    """
    Decides whether an agent switches from honest to exploitative behavior.
    Called once per step per agent.
    """
    
    def evaluate(self, agent, environment):
        """
        Returns the strategy the agent will use this step.
        """
        best_strategy = 'honest'
        best_eV = self._honest_expected_value(agent)
        
        for strategy in self.available_strategies:
            if not self._meets_prerequisites(agent, strategy):
                continue
            
            eV = self._expected_value(agent, strategy, environment)
            
            # Apply honesty discount
            eV *= agent.honesty if strategy != 'honest' else 1.0
            
            if eV > best_eV * (1 + agent.inertia):
                best_strategy = strategy
                best_eV = eV
        
        return best_strategy
```

### Available Strategies

| Strategy | Prerequisites | Expected value calculation |
|----------|--------------|---------------------------|
| **Honest** | None | Normal economic activity |
| **Premium evasion** | Has insurance | (Premium savings) × (1 - P(detection)) - P(detection) × penalty |
| **Insurance fraud** | Has insurance | (Claim payout) × P(success) - P(failure) × penalty |
| **Harberger under-declare** | Owns land | (LVT savings) × P(no forced sale) - P(forced sale) × (property loss) |
| **Court flooding** | Has capital | P(setElement) × (expected settlement) - (filing fee + reputation cost) |
| **Guild rent-seeking** | Is guild member | (Wage increase due to restricted supply) - (lost dues from excluded workers) |
| **Collusion** | Has competitors | (Extra profit × P(success)) - P(detection) × antitrust penalty |
| **Forum shopping** | Has court case | (Higher award × P(success)) - (filing costs in favorable court) |
| **Contract breach** | Has contract | (Gain from breach) - P(sued) × (damages + legal costs) |
| **Pollution** | Has business | (Pollution cost savings) - P(detected) × (liability + cleanup costs) |

---

## 8. Structure Detection

Run each step to detect emergent patterns:

```python
def detect_structures(environment):
    structures = []
    
    # Market concentration
    for market in ['insurance', 'land', 'court']:
        hhi = herfindahl_index(market)
        if hhi > 2500:  # Highly concentrated
            structures.append(f"Concentrated {market} market (HHI={hhi:.0f})")
    
    # Guild power blocs
    for guild in environment.guilds:
        market_share = guild.certified_workers / total_workers
        if market_share > 0.3:
            structures.append(f"Dominant guild: {guild.name} ({market_share:.0%} of workforce)")
    
    # Court hierarchy
    top_court = max(environment.courts, key=lambda c: c.case_volume)
    if top_court.case_volume > 0.5 * total_cases:
        structures.append(f"Dominant court: {top_court.name} ({top_court.case_volume:.0%} of cases)")
    
    # Compact specialization
    for compact in environment.compacts:
        dominant_sector = compact.dominant_economic_sector()
        if dominant_sector and compact.sector_concentration() > 0.4:
            structures.append(f"Compact specialization: {compact.name} → {dominant_sector}")
    
    # Wealth stratification
    top_decile_share = wealth_share(top_frac=0.1)
    if top_decile_share > 0.7:
        structures.append(f"Wealth concentration: top 10% own {top_decile_share:.0%}")
    
    return structures
```
