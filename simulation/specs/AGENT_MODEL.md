# Agent Model Specification — The Liability State

> **Version:** 1.0  
> **Scope:** Defines all agent types, utility functions, decision processes, behavioral parameters, memory architecture, learning mechanisms, and the strategy controller for the Liability State simulation.  
> **Design Principle:** Agents are utility-maximizers with **bounded rationality**, operating under incomplete information and cognitive constraints. The honesty parameter tunes the moral cost of exploitative behavior.

---

## Table of Contents

1. [Core Architecture](#1-core-architecture)
2. [Agent Types](#2-agent-types)
3. [Utility Functions](#3-utility-functions)
4. [Decision-Making Process](#4-decision-making-process)
5. [Honesty Parameter](#5-honesty-parameter)
6. [Memory Model](#6-memory-model)
7. [Learning & Adaptation](#7-learning--adaptation)
8. [Strategy Controller](#8-strategy-controller)
9. [Decision Variables per Agent Type](#9-decision-variables-per-agent-type)
10. [Agent Lifecycle](#10-agent-lifecycle)
11. [Interaction Protocols](#11-interaction-protocols)
12. [Parameter Tables & Defaults](#12-parameter-tables--defaults)

---

## 1. Core Architecture

### 1.1 Agent Definition

Every agent in the simulation is an instance of a base `Agent` class with the following invariant properties:

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `UUID` | Globally unique identifier |
| `type` | `Enum(AgentType)` | One of: WORKER, BUSINESS, INSURER, GUILD, COURT |
| `tick_created` | `int` | Simulation step when agent was created |
| `alive` | `bool` | Whether agent is active (insolvent agents may be terminated) |
| `wealth` | `float` | Current liquid wealth |
| `assets` | `dict` | Non-liquid holdings (capital, inventory, reserves) |
| `location` | `(x, y)` | Position in the simulated spatial economy |
| `θ` (theta) | `float ∈ [0,1]` | **Honesty parameter** — base moral position |
| `θ_effective` | `float ∈ [0,1]` | Honesty after strategy-controller modulation |
| `λ` (lambda) | `float ∈ [0,1]` | **Inertia coefficient** — resistance to changing behavior |
| `memory` | `dict` | Structured memory store (see §6) |
| `strategy` | `Enum(Strategy)` | Current behavioral mode: HONEST or EXPLOITATIVE |

### 1.2 Bounded Rationality Constraints

All agents operate under bounded rationality, modeled as:

1. **Information Asymmetry:** Agents observe only local/market signals, not the full state.
2. **Finite Horizon:** Decision horizon `H` (steps into future considered) is capped per agent type.
3. **Discounting:** Future utility is discounted by `γ ∈ (0,1]`.
4. **Noise:** Decisions include a stochastic perturbation `ε ~ N(0, σ²)` to model irrational noise.
5. **Satisficing:** When search costs exceed benefit, agents satisfice rather than optimize.

---

## 2. Agent Types

### 2.1 Worker

**Role:** Supplies labor, earns wages, purchases goods, may file claims.

**Key Attributes:**
- `skill_level ∈ [0,1]` — productivity in labor market
- `wage_expectation` — reservation wage (minimum acceptable)
- `employer_id` — currently contracted business (if any)
- `claims_filed` — list of liability claims the worker has initiated
- `risk_tolerance ∈ [0,1]` — willingness to accept variance in income
- `network ∈ [Guild | None]` — optional guild membership

**Lifecycle States:** Unemployed → Job-seeking → Employed → (possible) Claim-filing → Unemployed (repeat)

### 2.2 Business

**Role:** Produces goods/services, hires workers, carries liability risk, purchases insurance.

**Key Attributes:**
- `production_capacity` — max output per tick
- `capital_stock` — accumulated productive assets
- `liability_exposure` — risk level inherent in operations
- `safety_investment ∈ [0,1]` — fraction of revenue spent on loss prevention
- `pricing_model` — pricing strategy (cost-plus, market-rate, predatory)
- `insurance_policy` — current insurer contract (if any)
- `workforce` — list of employed worker IDs

**Lifecycle States:** Starting → Operating → (possible) Liability event → Claim dispute → (possible) Insolvency → Exit

### 2.3 Insurer

**Role:** Underwrites liability policies, collects premiums, manages claims payouts, invests reserves.

**Key Attributes:**
- `premium_schedule` — pricing function based on risk assessment
- `reserves` — funds set aside for expected claims
- `risk_pool_size` — number of policies underwritten (diversification)
- `claim_approval_rate ∈ [0,1]` — probability of approving a valid claim
- `investigation_capacity` — ability to verify claim validity
- `solvency_ratio` — reserves / expected liabilities

**Lifecycle States:** Underwriting → Premium collection → Claim processing → Payout/Denial → Rebalancing

### 2.4 Guild

**Role:** Mutual insurance / collective bargaining body for workers. Provides solidarity, reputation tracking, and pooled risk.

**Key Attributes:**
- `membership` — set of member worker IDs
- `mutual_fund` — pooled contribution reserves
- `reputation_scores` — map of business IDs to historical trust ratings
- `bargaining_power ∈ [0,1]` — ability to negotiate collective contracts
- `dues_structure` — contribution formula for members
- `solidarity_threshold` — minimum member count to remain viable

**Lifecycle States:** Forming → Operating → (possible) Fund depletion → Restructuring / Dissolution

### 2.5 Court

**Role:** Adjudicates disputes, sets legal precedent, imposes liability judgments.

**Key Attributes:**
- `workload` — pending case queue
- `backlog_delay` — ticks required to process a case
- `judicial_bias ∈ [-1, 1]` — tendency favoring plaintiffs (+) or defendants (-)
- `damages_multiplier` — how awarded damages relate to proven harm
- `precedent_weight ∈ [0,1]` — how strongly past rulings constrain current decisions
- `evidence_standard` — threshold of proof required (preponderance, clear-and-convincing, beyond-reasonable-doubt)

**Lifecycle States:** Idle → Case received → Deliberation → Ruling issued (Precedent updated)

---

## 3. Utility Functions

### 3.1 General Utility Structure

Each agent maximizes **expected discounted utility** over horizon `H`:

```
U_total = E[ Σ_{t=0}^{H} γ^t · (u_consumption(t) + u_social(t) + u_risk(t) + u_moral(t)) ]
```

Where:
- `u_consumption`: Material payoff (wealth, income, consumption)
- `u_social`: Relational utility (reputation, network, trust)
- `u_risk`: Risk penalty (variance aversion)
- `u_moral`: Moral utility (honesty-alignment cost of exploitative actions)

### 3.2 Worker Utility

```
U_worker = w · L - C_effort(L) + E[claims_payout] - litigation_cost + u_moral
          - α_var · Var(income) + β_guild · guild_support
```

| Term | Description |
|------|-------------|
| `w · L` | Wage income (wage rate × labor supplied) |
| `C_effort(L)` | Convex disutility of labor: `c₁ · L²` |
| `E[claims_payout]` | Expected value of liability claims filed |
| `litigation_cost` | Fixed cost of pursuing a claim |
| `u_moral` | Moral utility from honesty (see §3.7) |
| `α_var · Var(income)` | Risk penalty (variance aversion) |
| `β_guild · guild_support` | Utility boost from guild solidarity |

### 3.3 Business Utility

```
U_business = π + (1 - θ_eff) · E[exploitative_gain] - E[liability_cost] - C_safety
             - premium_cost + u_moral - α_rep · reputation_penalty
```

| Term | Description |
|------|-------------|
| `π` | Operating profit (revenue - wages - materials) |
| `(1 - θ_eff) · E[exploitative_gain]` | Discounted gain from exploitative behavior (wage theft, safety neglect) |
| `E[liability_cost]` | Expected cost of liability judgments against the business |
| `C_safety` | Investment in safety/loss prevention |
| `premium_cost` | Insurance premiums paid |
| `u_moral` | Moral utility (see §3.7) |
| `α_rep · reputation_penalty` | Market reputation damage from exploitative behavior |

### 3.4 Insurer Utility

```
U_insurer = Σ premiums - E[claims_payouts] - C_operations - C_investigation
            + (r · reserves) - ρ · solvency_risk_penalty + u_moral
```

| Term | Description |
|------|-------------|
| `Σ premiums` | Total premium income from policies |
| `E[claims_payouts]` | Expected payout on valid claims |
| `C_operations` | Administrative overhead |
| `C_investigation` | Cost of verifying claims |
| `r · reserves` | Return on invested reserves |
| `ρ · solvency_risk_penalty` | Penalty for under-reserving (regulatory + risk) |
| `u_moral` | Moral utility (see §3.7) |

### 3.5 Guild Utility

```
U_guild = Σ member_surplus + δ_reputation · avg_reputation - C_administration
          - solidarity_risk + u_moral
```

| Term | Description |
|------|-------------|
| `Σ member_surplus` | Aggregate welfare improvement of members vs. no guild |
| `δ_reputation · avg_reputation` | Value of accumulated reputation capital |
| `C_administration` | Operational costs |
| `solidarity_risk` | Risk of fund depletion from correlated claims |
| `u_moral` | Moral utility (see §3.7) |

### 3.6 Court Utility (Social Welfare Objective)

```
U_court = -|damages_awarded - optimal_damages| - C_deliberation
          + ω_precedent · precedent_consistency - backlog_penalty(workload)
          + u_moral
```

| Term | Description |
|------|-------------|
| `-|damages_awarded - optimal_damages|` | Deviation from socially optimal damages |
| `C_deliberation` | Cognitive cost of deciding |
| `ω_precedent · precedent_consistency` | Utility from consistent rulings |
| `backlog_penalty(workload)` | Disutility from case queue |
| `u_moral` | Moral utility (see §3.7) |

**Note:** The Court is a **social planner surrogate** — it does not maximize private utility but rather a social welfare function that balances justice, efficiency, and consistency.

### 3.7 Moral Utility (Honesty-Alignment Term)

The `u_moral` term is common across all agent types and captures the psychic cost of dishonest behavior:

```
u_moral = θ_eff · (baseline_moral_utility) - (1 - θ_eff) · guilt_penalty(exploitation)
```

Where:
- `baseline_moral_utility = M₀` (constant, default 1.0)
- `guilt_penalty(exploitation) = g₀ · exploitation_amount²` (convex guilt cost)

**Key property:** An agent with `θ_eff = 1` receives full moral utility and zero guilt. An agent with `θ_eff = 0` receives no moral utility and pays the full guilt penalty. This creates an internal cost to exploitation that scales with the magnitude of exploitation.

---

## 4. Decision-Making Process

### 4.1 Expected Value with Bounded Rationality

Agents evaluate decisions using a **quantal response** model rather than perfect utility maximization:

```
P(choose action a) = exp(β · V(a)) / Σ_{a' ∈ A} exp(β · V(a'))
```

Where:
- `V(a) = E[U(a)] + ε_a` is the perceived (noisy) value of action `a`
- `β ≥ 0` is the **rationality parameter** (inverse temperature)
  - `β → ∞`: Perfect rational choice (always picks max)
  - `β → 0`: Uniform random choice
  - Default: `β ∈ [1, 10]` depending on agent type
- `ε_a ~ Logistic(0, s)` is decision noise

### 4.2 Belief Updating

Agents maintain beliefs about unknown parameters (e.g., counterparty honesty, claim success probability) and update via **Bayesian reinforcement learning**:

```
P(θ_c) ∝ P(data | θ_c) · P(θ_c)
```

With a computational shortcut using **exponential recency-weighted averaging**:

```
belief_{t+1} = (1 - η) · belief_t + η · observation_t
```

Where `η ∈ (0,1)` is the learning rate (see §7).

### 4.3 Decision Horizon & Discounting

| Agent Type | Horizon `H` | Discount `γ` | Rationality `β` |
|------------|-------------|--------------|------------------|
| Worker | 12-24 months | 0.92-0.97 | 2-5 |
| Business | 24-60 months | 0.90-0.95 | 3-8 |
| Insurer | 36-120 months | 0.85-0.93 | 5-10 |
| Guild | 12-36 months | 0.90-0.95 | 3-6 |
| Court | 1 case (no discounting) | 1.0 | 8-10 |

### 4.4 Satisficing Rule

When the number of possible actions `|A| > S_max` (search capacity threshold), agents:
1. Sample a subset of actions of size `min(S_max, |A|)`
2. Set an aspiration level `A_spire = current_utility · (1 + δ_sat)`
3. Choose the first action that meets or exceeds the aspiration level
4. If none does, increase search or choose best found so far

### 4.5 Cognitive Cost

Each unit of computation (evaluated alternative, considered scenario) carries cost `c_cog`:

```
V_net(a) = V(a) - c_cog · search_effort
```

This naturally limits exhaustive optimization.

---

## 5. Honesty Parameter

### 5.1 Definition

The **honesty parameter** `θ ∈ [0,1]` represents an agent's intrinsic moral position:

| θ | Interpretation |
|---|----------------|
| 1.0 | **Saint** — never exploits, high guilt from dishonesty |
| 0.8-0.99 | **Principled** — exploits only under extreme duress |
| 0.5-0.79 | **Conditionally honest** — exploits when profitable enough |
| 0.2-0.49 | **Opportunistic** — defaults to exploitation unless monitored |
| 0.01-0.19 | **Predatory** — exploits aggressively |
| 0.0 | **Sociopath** — no moral constraint |

### 5.2 Effective Honesty (`θ_eff`)

The effective honesty used in decisions is **not** the base `θ` but a modulated version controlled by the Strategy Controller (§8):

```
θ_eff = M(θ, strategy, stress_level)
```

Where `M` is the strategy modulation function:

```
θ_eff = θ + Δ_strategy · (1 - θ)      if strategy == HONEST
θ_eff = θ - Δ_strategy · θ            if strategy == EXPLOITATIVE
```

With `Δ_strategy ∈ [0, 0.3]` representing the amplitude of strategic modulation.

### 5.3 Effects of θ on Behavior

- **Exploitative gain discounting:** Net exploitative gain = `(1 - θ_eff) · gross_gain`
- **Claim-filing threshold:** Workers with higher `θ` require stronger evidence of harm before filing
- **Premium fairness:** Insurers with higher `θ` price closer to actuarially fair rates
- **Judgment leniency:** Courts with higher `θ` penalize dishonest plaintiffs more
- **Safety investment:** Businesses with higher `θ` invest more in safety even when unobserved

### 5.4 Inheritance & Initialization

- Agent `θ` is drawn from a beta distribution `Beta(a, b)` at creation
- Default: `Beta(4, 2)` → right-skewed toward honesty (mean ≈ 0.67)
- Configurable per agent type to model different baseline moral distributions
- `θ` can shift over time through learning (§7) and strategy switching (§8)

---

## 6. Memory Model

### 6.1 Memory Architecture

Each agent maintains a **structured episodic memory** with four stores:

```
┌─────────────────────────────────────────────────────┐
│                   AGENT MEMORY                       │
├─────────────┬──────────────┬───────────┬─────────────┤
│  Episodic    │  Semantic    │  Working   │  Social     │
│  (events)    │  (beliefs)   │  (scratch) │  (relations)│
├─────────────┼──────────────┼───────────┼─────────────┤
│ - up to M_E │ - parameter  │ - current │ - reputation │
│   events    │   estimates  │   context │   scores     │
│ - timestamp │ - learned    │ - active  │ - trust      │
│ - decayed   │   patterns   │   goals   │   matrix     │
│   by τ_E    │ - causal     │ - pending │ - network    │
│             │   models     │   actions │   graph      │
└─────────────┴──────────────┴───────────┴─────────────┘
```

### 6.2 Memory Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `M_E` | 100 | 10-1000 | Max episodic events retained |
| `τ_E` | 50 ticks | 10-500 | Episodic decay half-life |
| `M_S` | N/A | — | Semantic memory (no limit) |
| `M_W` | 7 ± 2 chunks | — | Working memory capacity |
| `η_recall` | 0.85 | 0.5-1.0 | Recall fidelity (recent/important events more retrievable) |

### 6.3 Episodic Memory

Stores individual interaction records:

```python
{
    "event_id": UUID,
    "timestamp": tick,
    "type": "contract_signed" | "claim_filed" | "payout_received" |
            "judgment_issued" | "inspection" | "premium_paid",
    "counterparty_id": UUID,
    "outcome": float,            # utility impact
    "details": dict,             # type-specific data
    "salience": float ∈ [0,1],  # importance weight
    "decayed_weight": float     # current retrievability
}
```

**Decay function:** `decayed_weight = salience · exp(-(current_tick - timestamp) / τ_E)`

### 6.4 Semantic Memory

Learned abstractions from experience:

```python
{
    "counterparty_trust": {UUID: float},       # running trust scores
    "success_rate_by_action": {action: float}, # empirical success rates
    "market_conditions": {                      # macro beliefs
        "avg_wage": float,
        "claim_success_rate": float,
        "insolvency_probability": float
    },
    "causal_beliefs": [                         # learned correlations
        ("safety_investment", "claim_rate", -0.7)
    ]
}
```

### 6.5 Social Memory (Reputation)

Each agent maintains a **trust matrix** of counterparties:

```
T_{i,j} = running trust score of agent i about agent j
```

Updated via:
```
T_{i,j}^{(t+1)} = T_{i,j}^{(t)} + η_trust · (observed_behavior - T_{i,j}^{(t)})
```

Where `observed_behavior ∈ {+1, 0, -1}` for positive, neutral, negative interaction.

**Guild-shared reputation:** Guilds maintain a collective reputation DB accessible to all members (reducing individual information asymmetry).

### 6.6 Memory Retrieval

Memory retrieval is cue-dependent with interference:

```
P(retrieve event e | cue c) = σ(α_cue · similarity(c, e_features) - β_int · interference)
```

Where:
- `α_cue` = cue sensitivity
- `β_int` = interference penalty from similar events
- `σ` = sigmoid function

---

## 7. Learning & Adaptation

### 7.1 Learning Mechanisms

Agents learn through four parallel processes:

| Mechanism | Update Target | Frequency |
|-----------|--------------|-----------|
| **Bayesian belief updating** | Semantic memory parameters | Every interaction |
| **Reinforcement learning** | Action values (Q-learning) | After each outcome |
| **Social learning** | Trust scores, reputation | After observed interactions |
| **Strategy learning** | When to switch strategies | Periodic (every K ticks) |

### 7.2 Reinforcement Learning (Q-Learning)

Agents learn action values via SARSA with eligibility traces:

```
Q(s, a) ← Q(s, a) + α · [r + γ · Q(s', a') - Q(s, a)]
```

Where:
- `α ∈ [0.01, 0.3]` = learning rate (varies by agent type)
- `γ` = discount factor (§4.3)
- `r` = received reward
- `s, a` = current state and action
- `s', a'` = next state and chosen action

**Eligibility traces (λ):** `λ = 0.6` for all agents, enabling credit assignment over multiple steps.

### 7.3 Learning Rate Schedule

Learning rates decay over agent lifetime to model **convergence of beliefs**:

```
α(t) = α₀ · exp(-t / τ_α)
```

| Agent Type | α₀ | τ_α (ticks) |
|------------|----|-------------|
| Worker | 0.25 | 200 |
| Business | 0.15 | 500 |
| Insurer | 0.10 | 1000 |
| Guild | 0.20 | 300 |
| Court | 0.05 | 2000 |

### 7.4 Belief Updating Functions

**Claim success probability belief (worker):**
```
P(win_next_claim) = (wins + prior_α) / (total_claims + prior_α + prior_β)
```
Uses Beta-Binomial conjugacy with prior `Beta(α=2, β=5)` (pessimistic prior).

**Counterparty honesty belief:**
```
P(θ_c > 0.5) = updated via Beta-Bernoulli on observed honest/dishonest acts
```

**Market condition belief:**
```
E[wage_{t+1}] = η · observed_wage_t + (1 - η) · E[wage_t]
```

### 7.5 Social Learning & Imitation

Agents can observe and imitate the strategies of successful peers:

```
P(switch to strategy of peer j) = σ(β_imitate · (U_j - U_i))
```

Where `σ` is the sigmoid function and `β_imitate` controls imitation propensity.

**Conditions for imitation:**
1. Agent must have observed peer j (directly or via guild reputation)
2. Peer j must have outperformed agent i over recent window `W_impute`
3. Agent must have sufficient cognitive capacity to evaluate the strategy

### 7.6 Adaptation Triggers

Agents reassess their strategy when **prediction error** exceeds threshold:

```
prediction_error = |actual_outcome - expected_utility| > η_predict
```

Or when **wealth stress** crosses a threshold:

```
stress_level = 1 - (current_wealth / reference_wealth)
```

Trigger values:
| Condition | Threshold | Effect |
|-----------|-----------|--------|
| Prediction error > threshold | `η_predict = 0.3 · avg_utility` | Triggers belief revision |
| Stress level > 0.7 | — | Triggers strategy re-evaluation (§8) |
| Consecutive losses (3+) | — | Triggers exploration boost (α increases) |

---

## 8. Strategy Controller

### 8.1 Overview

The **Strategy Controller** is the mechanism that decides when agents switch between HONEST and EXPLOITATIVE behavioral modes. It acts as a meta-cognitive layer evaluating the performance of the current strategy against alternatives.

### 8.2 Strategy States

```
                    ┌─────────────┐
                    │   HONEST    │
                    └──────┬──────┘
                           │
                ┌──────────┴──────────┐
                │                     │
        Performance Review     Performance Review
        every K ticks          every K ticks
                │                     │
                ▼                     ▼
        ┌──────────────┐    ┌──────────────────┐
        │ Stay HONEST   │    │ Switch to        │
        │ (θ_eff ↑)     │    │ EXPLOITATIVE     │
        └──────────────┘    │ (θ_eff ↓)         │
                            └────────┬─────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │   EXPLOITATIVE   │
                            └────────┬─────────┘
                                     │
                            Performance Review
                            every K ticks
                                     │
                            ┌────────┴────────┐
                            │                 │
                            ▼                 ▼
                    ┌──────────────┐  ┌────────────────┐
                    │ Stay EXP.    │  │ Switch to      │
                    │ (θ_eff ↓)    │  │ HONEST (θ_eff ↑)│
                    └──────────────┘  └────────────────┘
```

### 8.3 Performance Review Function

Every `K` ticks (default: `K=12`), agents evaluate their current strategy:

```
ΔU = U_current_strategy - U_counterfactual

where U_counterfactual = estimated utility if the other strategy were used
```

The **switch probability** is:

```
P(switch) = σ(β_switch · (ΔU + θ_inertia_bias + ε))
```

Where:
- `β_switch` = switching sensitivity (inverse temperature for strategy switching)
- `θ_inertia_bias = λ · (1 - 2 · strategy)` — inertia pushes toward current strategy
  - If HONEST: bias = +λ (harder to leave honesty)
  - If EXPLOITATIVE: bias = -λ (harder to leave exploitation)
- `ε ~ Logistic(0, s_switch)` = switching noise

### 8.4 Stress-Based Triggering

Strategy review is **accelerated** when agents are under stress:

```
K_effective = max(1, K · (1 - stress_level))

Under normal conditions: review every 12 ticks
Under severe stress (stress=0.9): review every 1-2 ticks
```

This models the observation that moral behavior degrades under economic pressure.

### 8.5 Counterfactual Estimation

To estimate `U_counterfactual`, agents simulate a short forward horizon under the alternate strategy:

```
U_counterfactual = E[U(alternate_strategy) | current_beliefs, last_N_outcomes]
```

Implementation:
- Agent replays last `N = 5` interactions through the alternate decision function
- Computes what utility would have been realized
- This is computationally bounded — only 5-step rollouts, not full planning

### 8.6 Inertia Mechanism

The **inertia coefficient** `λ ∈ [0,1]` models the stickiness of behavior:

| λ | Interpretation |
|---|----------------|
| 0.0 | **Mercurial** — switches freely based on short-term incentives |
| 0.3 | **Typical** — moderate resistance to change |
| 0.5 | **Stubborn** — requires significant evidence to switch |
| 0.7+ | **Dogmatic** — nearly fixed behavior |
| 1.0 | **Absolute** — never switches (fixed type) |

**Inertia update:** `λ` can itself evolve:
```
λ_{t+1} = λ_t + η_λ · (switching_cost - baseline_cost)
```
If switching frequently proves costly, `λ` increases (agent becomes more stubborn).

### 8.7 Strategy Modulation of θ

When switching strategy, `θ_eff` is modulated as defined in §5.2:

```
Switch to HONEST:       θ_eff = θ + Δ · (1 - θ)    [θ_eff ≥ θ]
Switch to EXPLOITATIVE: θ_eff = θ - Δ · θ          [θ_eff ≤ θ]
```

Where `Δ` is the agent's **strategic flexibility** parameter. Higher Δ means larger swings in effective honesty when switching strategy.

### 8.8 Strategy Controller Algorithm

```
Algorithm: StrategyController.evaluate(agent, tick)

Input: Agent with current strategy, beliefs, memory
Output: Updated strategy, updated θ_eff

1. If tick % K_effective(agent.stress) != 0: return  # skip if not review time

2. Compute U_current  = simulate_future(agent.strategy, H=5)
3. Compute U_alt      = simulate_future(alternate(agent.strategy), H=5)
4. Compute ΔU         = U_current - U_alt

5. Compute inertia_bias:
   if agent.strategy == HONEST:       bias = +agent.λ
   else if agent.strategy == EXPLOIT: bias = -agent.λ

6. Compute switch_prob = sigmoid(β_switch · (ΔU + bias + noise))

7. Draw r ~ Uniform(0, 1)
8. If r < switch_prob:
     agent.strategy ← alternate(agent.strategy)
     agent.θ_eff ← modulate(agent.θ, agent.strategy, agent.Δ)
     Log strategy_switch event to episodic memory

9. Return
```

---

## 9. Decision Variables per Agent Type

### 9.1 Worker Decision Variables

| Variable | Symbol | Domain | Description |
|----------|--------|--------|-------------|
| **Labor supply** | `L` | `[0, L_max]` | Hours/effort to supply this period |
| **Reservation wage** | `w_res` | `[w_min, w_max]` | Minimum wage to accept a job |
| **Job search intensity** | `s_job` | `[0, 1]` | Fraction of effort spent searching |
| **Claim filing** | `c_file` | `{0, 1}` | Whether to file a liability claim |
| **Claim settlement threshold** | `c_settle` | `[0, 1]` | Minimum payout to accept settlement |
| **Guild membership** | `g_join` | `{0, 1}` | Whether to join/remain in guild |
| **Savings rate** | `s_rate` | `[0, 0.5]` | Fraction of income saved |
| **Quit decision** | `q` | `{0, 1}` | Whether to quit current employment |
| **Report violation** | `r_viol` | `{0, 1}` | Whether to report safety/wage violation |
| **Training investment** | `t_inv` | `[0, 1]` | Fraction of time invested in skill upgrading |

### 9.2 Business Decision Variables

| Variable | Symbol | Domain | Description |
|----------|--------|--------|-------------|
| **Output quantity** | `Q` | `[0, Q_max]` | Production volume |
| **Wage offered** | `w_offer` | `[w_min, w_max]` | Wage rate for workers |
| **Hiring** | `h` | `ℕ` | Number of workers to hire |
| **Safety investment** | `s_inv` | `[0, 1]` | Fraction of revenue on safety |
| **Wage compliance** | `w_comp` | `{0, 1}` | Whether to pay legally required wages |
| **Safety compliance** | `s_comp` | `{0, 1}` | Whether to meet safety regulations |
| **Insurance purchase** | `i_buy` | `{0, 1}` | Whether to buy liability insurance |
| **Coverage level** | `c_lev` | `[0, c_max]` | Insurance coverage amount |
| **Price setting** | `p` | `[0, p_max]` | Product/service price |
| **Contract type** | `c_type` | `{standard, gig, temp}` | Employment contract formality |
| **Lobbying effort** | `lobby` | `[0, 1]` | Resources spent on regulatory influence |
| **Legal defense spend** | `defense` | `[0, 1]` | Resources for legal defense against claims |

### 9.3 Insurer Decision Variables

| Variable | Symbol | Domain | Description |
|----------|--------|--------|-------------|
| **Premium price** | `p_prem` | `[0, p_prem_max]` | Per-policy premium amount |
| **Risk assessment accuracy** | `assess` | `[0, 1]` | Accuracy of risk classification |
| **Policy coverage** | `cov` | `[0, cov_max]` | Policy coverage cap |
| **Claim verification effort** | `verify` | `[0, 1]` | Resources per claim for verification |
| **Claim approval probability** | `p_approve` | `[0, 1]` | Fraction of valid claims approved |
| **Reserve ratio** | `r_res` | `[0, 1]` | Reserves / Premium income target |
| **Reinsurance** | `reins` | `[0, 1]` | Fraction of risk ceded to reinsurance |
| **Market entry/exit** | `mkt_entry` | `{0, 1}` | Whether to enter/exit a market segment |
| **Underwriting stringency** | `u_string` | `[0, 1]` | Strictness of underwriting criteria |
| **Investment allocation** | `inv_all` | `[0, 1]` | Risky vs. safe asset allocation for reserves |

### 9.4 Guild Decision Variables

| Variable | Symbol | Domain | Description |
|----------|--------|--------|-------------|
| **Dues rate** | `d` | `[0, d_max]` | Membership dues as fraction of wage |
| **Mutual fund payout** | `payout` | `[0, fund_balance]` | Support to members in distress |
| **Member admission** | `admit` | `{0, 1}` | Whether to admit a new member |
| **Member expulsion** | `expel` | `{0, 1}` | Whether to expel a member |
| **Strike call** | `strike` | `{0, 1}` | Whether to call collective action |
| **Strike threshold** | `strike_thresh` | `[0, 1]` | Member support required for strike |
| **Reputation sharing** | `rep_share` | `[0, 1]` | How much reputation data to share externally |
| **Negotiation aggressiveness** | `bargain` | `[0, 1]` | Bargaining stance (0=conciliatory, 1=aggressive) |
| **Legal fund allocation** | `legal_fund` | `[0, 1]` | Resources for member legal support |
| **Organizing effort** | `organize` | `[0, 1]` | Resources for recruitment and organizing |

### 9.5 Court Decision Variables

| Variable | Symbol | Domain | Description |
|----------|--------|--------|-------------|
| **Liability finding** | `liability` | `{0, 1}` | Whether defendant is found liable |
| **Damages awarded** | `damages` | `[0, damages_max]` | Monetary judgment amount |
| **Punitive multiplier** | `punit_mult` | `[1, punit_max]` | Punitive damages multiplier |
| **Evidence threshold** | `ev_thresh` | `[0, 1]` | Standard of proof applied (case-specific) |
| **Case priority** | `priority` | `[0, 1]` | Where in queue to place this case |
| **Precedent override** | `override` | `{0, 1}` | Whether to depart from precedent |
| **Sanctions** | `sanctions` | `[0, 1]` | Penalty for frivolous claims |
| **Mediation referral** | `mediate` | `{0, 1}` | Whether to order mediation before trial |

---

## 10. Agent Lifecycle

### 10.1 Birth / Creation

```
Agent is spawned with:
- Initial θ drawn from Beta(a_type, b_type)
- Initial wealth: BaseEndowment + N(μ_wealth, σ²_wealth)
- Random strategy assignment (bias toward HONEST at t=0)
- Empty memory, prior beliefs initialized
- Type-specific initial conditions (skill, capacity, etc.)
```

### 10.2 Per-Tick Update Loop

```
For each alive agent at tick t:

1. PERCEPTION:
   - Observe market signals (prices, wages, rumors)
   - Retrieve relevant episodic memories
   - Update semantic beliefs from observations

2. STRATEGY REVIEW (if t % K == 0):
   - Run StrategyController.evaluate()
   - Possibly switch strategy and modulate θ_eff

3. DECISION MAKING:
   - Evaluate available actions (bounded rational search)
   - Compute Q-values or use learned policy
   - Select action via quantal response (§4.1)
   - Execute action

4. INTERACTION:
   - Engage with counterparties as per action
   - Exchange payments, file claims, issue rulings
   - Record interaction outcome

5. LEARNING:
   - Compute prediction error
   - Update Q-values (SARSA update: §7.2)
   - Update beliefs (§7.4)
   - Update trust scores (§6.5)
   - Update learning rate (§7.3)

6. ECONOMIC UPDATE:
   - Update wealth (income - expenses ± transfers)
   - Update assets
   - Check solvency (if wealth < 0: trigger insolvency protocol)

7. MEMORY MAINTENANCE:
   - Encode new episodic memories
   - Decay old memories (§6.3)
   - Consolidate frequent patterns to semantic memory
```

### 10.3 Death / Termination

Agents are removed under these conditions:

| Condition | Trigger | Notes |
|-----------|---------|-------|
| **Insolvency** | `wealth < -debt_limit` | Business: bankruptcy; Worker: destitution; Agent may be replaced |
| **Liquidation** | Court-ordered dissolution | Applicable to businesses and guilds |
| **Exit** | Voluntary market exit | Businesses close, workers leave simulation |
| **Aging out** | After `agent_lifespan` ticks | Default lifespan: 600-3600 ticks (~5-30 years) |

---

## 11. Interaction Protocols

### 11.1 Worker ↔ Business (Employment)

```
1. Matching: Worker applies; Business screens
2. Contract: Wage, hours, safety conditions negotiated
3. Production: Worker supplies L; Business pays w
4. Monitoring: Business may exploit (wage theft, unsafe conditions)
5. Worker response: Accept, Quit, Report, File claim
6. Resolution: Guild may intervene, Court may adjudicate
```

**Decision sequence:**
- Business offers `(w_offer, s_inv_visible)` — may differ from actual safety
- Worker accepts if `w_offer ≥ w_res` and `E[safety] ≥ safety_threshold`
- During employment: Business chooses actual `w_paid` (may ≠ `w_offer`) and actual `s_actual` (may ≠ `s_inv_visible`)
- Worker detects discrepancy with probability `P_detect = f(monitoring_effort, guild_support)`
- Worker decides: quit, report, file claim, or accept

### 11.2 Worker ↔ Court (Claim Filing)

```
1. Worker files claim (cost: litigation_cost)
2. Court evaluates: case strength, evidence, precedent, workload
3. Court issues ruling: liability found? damages awarded?
4. Payout transferred: Business (or Insurer) pays damages
5. Precedent recorded: influences future similar cases
```

### 11.3 Business ↔ Insurer (Insurance)

```
1. Business applies for policy
2. Insurer assesses risk (may be inaccurate)
3. Premium set based on risk assessment + mark-up
4. If claim occurs: Insurer investigates, approves or denies
5. Payout: If approved, insurer covers damages up to coverage cap
6. Moral hazard: Insured business may reduce safety investment
```

### 11.4 Worker ↔ Guild (Membership)

```
1. Worker applies / Guild recruits
2. Guild assesses: worker risk profile, alignment
3. Membership approved (or rejected)
4. Ongoing: Worker pays dues; Guild provides support, reputation data
5. Guild may call collective action (strike, negotiation)
```

### 11.5 Guild ↔ Business (Collective Bargaining)

```
1. Guild represents workers in wage/safety negotiation
2. Bargaining power determined by: guild size, fund reserves, strike credibility
3. Contract negotiated; may include guild-enforced safety monitoring
4. If negotiation fails: Guild may call strike (costly for both sides)
```

### 11.6 Court ↔ All (Precedent System)

```
1. Court ruling sets precedent for similar future cases
2. Precedent_vector = f(liability_facts, damages_awarded, industry_context)
3. Future courts weigh precedent: similarity_scalar · precedent_weight
4. Agents learn precedent distribution and adjust behavior
```

---

## 12. Parameter Tables & Defaults

### 12.1 Global Agent Parameters

| Parameter | Symbol | Default | Range | Description |
|-----------|--------|---------|-------|-------------|
| Learning rate (initial) | α₀ | 0.2 | [0.01, 0.5] | Initial learning rate |
| Learning rate decay | τ_α | 500 | [100, 5000] | Decay half-life (ticks) |
| Discount factor | γ | 0.92 | [0.80, 0.99] | Future utility discount |
| Horizon | H | 24 | [1, 120] | Planning horizon (ticks) |
| Rationality | β | 5 | [1, 10] | Inverse temperature (QRE) |
| Decision noise scale | s | 0.15 | [0.01, 1.0] | Logistic noise scale |
| Search capacity | S_max | 15 | [3, 50] | Max actions evaluated |
| Cognitive cost | c_cog | 0.01 | [0, 0.1] | Per-evaluation cost |
| Inertia coefficient | λ | 0.3 | [0, 1] | Strategy switching resistance |
| Strategic flexibility | Δ | 0.15 | [0, 0.3] | θ modulation amplitude |
| Switch sensitivity | β_switch | 3.0 | [0.5, 10] | Temp. for strategy switching |
| Review period | K | 12 | [1, 52] | Ticks between strategy reviews |
| Memory capacity | M_E | 100 | [10, 1000] | Max episodic events |
| Memory decay | τ_E | 50 | [10, 500] | Episodic half-life |
| Trust learning rate | η_trust | 0.2 | [0.05, 0.5] | Trust update speed |
| Moral utility baseline | M₀ | 1.0 | [0, 5] | Base moral utility |
| Guilt scaling | g₀ | 2.0 | [0.5, 10] | Guilt penalty multiplier |

### 12.2 Type-Specific Parameter Defaults

| Parameter | Worker | Business | Insurer | Guild | Court |
|-----------|--------|----------|---------|-------|-------|
| `β` (rationality) | 3 | 5 | 7 | 4 | 9 |
| `γ` (discount) | 0.95 | 0.92 | 0.90 | 0.93 | 1.0 |
| `H` (horizon) | 18 | 36 | 60 | 24 | 1 |
| `α₀` (learning rate) | 0.25 | 0.15 | 0.10 | 0.20 | 0.05 |
| `λ` (inertia) | 0.25 | 0.35 | 0.40 | 0.30 | 0.50 |
| `S_max` (search cap) | 10 | 15 | 20 | 12 | 25 |
| `M_E` (memory cap) | 50 | 100 | 200 | 150 | 500 |
| `θ` distribution | Beta(5,2) | Beta(3,3) | Beta(4,3) | Beta(6,2) | Beta(8,2) |

### 12.3 Honesty Distribution Shapes

```python
HONESTY_DISTRIBUTIONS = {
    "Worker":   {"a": 5, "b": 2, "mean": 0.71, "description": "Moderately honest, some variance"},
    "Business": {"a": 3, "b": 3, "mean": 0.50, "description": "Uniform spread, equal dishonesty/honesty"},
    "Insurer":  {"a": 4, "b": 3, "mean": 0.57, "description": "Slightly honest-skewed, professional norms"},
    "Guild":    {"a": 6, "b": 2, "mean": 0.75, "description": "Honest-skewed, solidarity norms"},
    "Court":    {"a": 8, "b": 2, "mean": 0.80, "description": "Highly honest, institutional integrity"},
}
```

### 12.4 Exploitative Behaviors by Agent Type

| Agent Type | Exploitative Behavior | Detection Mechanism | Sanction |
|------------|----------------------|---------------------|----------|
| **Worker** | Fraudulent claim filing | Court investigation, Insurer verification | Claim denied, sanctions, reputation damage |
| **Business** | Wage theft, safety neglect, false advertising | Worker reporting, Guild monitoring, Regulatory inspection | Liability judgment, fines, reputation loss, insolvency |
| **Insurer** | Wrongful claim denial, premium overcharging | Regulatory audit, Court appeal, Guild legal action | Restitution, fines, license revocation |
| **Guild** | Embezzlement of mutual fund, favoritism | Member audit, democratic oversight | Dissolution, leader sanctions |
| **Court** | Biased rulings, bribery | Appeal system, Judicial oversight | Precedent reversal, removal |

### 12.5 Equilibrium Monitoring Variables

These aggregate metrics should be tracked to identify emergent regimes:

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| `Honesty ratio` | Mean(θ_eff) across all agents | Overall moral climate |
| `Exploitation rate` | Fraction of interactions involving exploitation | Prevalence of dishonesty |
| `Claim rate` | Claims filed / potential claims | Litigiousness |
| `Claim success rate` | Worker claims won / total filed | Access to justice |
| `Insurance density` | Insured businesses / total businesses | Risk transfer depth |
| `Guild density` | Guild members / total workers | Collective bargaining penetration |
| `Precedent consistency` | Variance in damages for similar cases | Rule of law stability |
| `Wealth Gini` | Gini coefficient of agent wealth | Inequality trajectory |
| `Insolvency rate` | Agents exiting due to insolvency / total | System stability |
| `Strategy switch rate` | Strategy switches per agent per tick | Behavioral volatility |

---

## Appendix A: Mathematical Summary

### Core Optimization Problem

Each agent `i` solves:

```
max_{a ∈ A_i}  V_i(a) = E[U_i(a) | B_i] + ε_i(a) - c_cog · search_effort
```

Subject to:
- Bounded rationality: `|A_sampled| ≤ S_max`
- Information set: `B_i` (beliefs from memory)
- Resource constraint: `wealth_i(t) + income_i(t) ≥ expenditures_i(t)`
- Legal constraint: actions must respect institutional rules (with possible violation)

### Key Equations

| Equation | Formula |
|----------|---------|
| Quantal response | `P(a) = exp(β · V(a)) / Σ exp(β · V(a'))` |
| Honesty modulation | `θ_eff = θ ± Δ · (min(θ, 1-θ))` depending on strategy |
| Switch probability | `P(switch) = σ(β_switch · (ΔU + λ · bias + ε))` |
| Q-learning update | `Q(s,a) ← Q(s,a) + α · [r + γ · Q(s',a') - Q(s,a)]` |
| Belief update | `belief ← (1-η)·belief + η·observation` |
| Memory decay | `weight = salience · exp(-Δt/τ_E)` |
| Stress | `stress = 1 - (wealth / reference_wealth)` |
| Prediction error | `PE = |outcome - expected_value|` |

---

## Appendix B: Implementation Interface (Python Pseudo-Code)

```python
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import numpy as np

class AgentType(Enum):
    WORKER = auto()
    BUSINESS = auto()
    INSURER = auto()
    GUILD = auto()
    COURT = auto()

class Strategy(Enum):
    HONEST = auto()
    EXPLOITATIVE = auto()

@dataclass
class Agent:
    id: UUID = field(default_factory=uuid4)
    type: AgentType = None
    tick_created: int = 0
    alive: bool = True
    wealth: float = 0.0
    assets: dict = field(default_factory=dict)
    location: Tuple[float, float] = (0.0, 0.0)
    
    # Honesty
    theta: float = 0.7          # Base honesty parameter
    theta_effective: float = 0.7 # Modulated honesty
    lambda_inertia: float = 0.3  # Inertia coefficient
    
    # Decision parameters
    learning_rate: float = 0.2
    discount: float = 0.92
    horizon: int = 24
    rationality: float = 5.0
    search_capacity: int = 15
    
    # Learning
    q_table: Dict = field(default_factory=dict)
    beliefs: Dict = field(default_factory=dict)
    memory: Dict = field(default_factory=lambda: {
        "episodic": [],
        "semantic": {},
        "working": [],
        "social": {}
    })
    
    # Strategy
    strategy: Strategy = Strategy.HONEST
    strategy_flexibility: float = 0.15
    switch_sensitivity: float = 3.0
    review_period: int = 12
    ticks_since_review: int = 0
    
    # Type-specific data
    type_data: Dict = field(default_factory=dict)
    
    def get_perceived_value(self, action: str, state: Dict) -> float:
        """Compute bounded-rational value of an action."""
        expected_u = self.estimate_utility(action, state)
        noise = np.random.logistic(0, 0.15)
        cognitive_cost = self.cognitive_cost(len(self.get_available_actions(state)))
        return expected_u + noise - cognitive_cost
    
    def choose_action(self, state: Dict) -> str:
        """Quantal response action selection."""
        actions = self.get_available_actions(state)
        values = [self.get_perceived_value(a, state) for a in actions]
        exp_values = np.exp(self.rationality * np.array(values))
        probs = exp_values / exp_values.sum()
        return np.random.choice(actions, p=probs)
    
    def update_q(self, state, action, reward, next_state, next_action):
        """SARSA Q-learning update."""
        alpha = self.learning_rate
        current_q = self.q_table.get((state, action), 0.0)
        next_q = self.q_table.get((next_state, next_action), 0.0)
        td_target = reward + self.discount * next_q
        self.q_table[(state, action)] = current_q + alpha * (td_target - current_q)
    
    def evaluate_strategy(self, tick: int):
        """Strategy controller: decide whether to switch behavioral mode."""
        stress = 1.0 - (self.wealth / max(self.wealth, 1.0))
        effective_k = max(1, int(self.review_period * (1.0 - stress)))
        
        if self.ticks_since_review < effective_k:
            self.ticks_since_review += 1
            return
        
        # Counterfactual evaluation
        u_current = self.simulate_strategy(self.strategy, horizon=5)
        u_alternate = self.simulate_strategy(
            Strategy.EXPLOITATIVE if self.strategy == Strategy.HONEST 
            else Strategy.HONEST,
            horizon=5
        )
        
        delta_u = u_current - u_alternate
        inertia_bias = self.lambda_inertia if self.strategy == Strategy.HONEST else -self.lambda_inertia
        
        switch_prob = 1.0 / (1.0 + np.exp(-self.switch_sensitivity * (delta_u + inertia_bias + np.random.logistic(0, 0.1))))
        
        if np.random.random() < switch_prob:
            self.strategy = Strategy.EXPLOITATIVE if self.strategy == Strategy.HONEST else Strategy.HONEST
            self.theta_effective = self.modulate_theta(self.theta, self.strategy)
        
        self.ticks_since_review = 0
    
    def modulate_theta(self, theta: float, strategy: Strategy) -> float:
        """Modulate base honesty by current strategy."""
        if strategy == Strategy.HONEST:
            return theta + self.strategy_flexibility * (1.0 - theta)
        else:
            return theta - self.strategy_flexibility * theta
```

---

*End of Agent Model Specification*  
*Next spec: Market & Institutional Model*
