# Core Ledger & Money Flow Specification

> **Version:** 1.0  
> **Domain:** Phase 0 — Economic Engine (Money Flow Core)  
> **Dependencies:** None (foundational component)  
> **Implements:** Task 0.1 (Money tracking system — ledger, flow tracker, zero-balance invariant)  
> **Design Principle:** Every dollar is traceable, every transfer is recorded, and the zero-sum invariant is checked at every granularity.

---

## Table of Contents

1. [Architecture & Design Rationale](#1-architecture--design-rationale)
2. [Ledger Entry Schema](#2-ledger-entry-schema)
3. [Agent Definitions & Entity Registry](#3-agent-definitions--entity-registry)
4. [Flow Matrix](#4-flow-matrix)
5. [Money Flow Definitions (Mechanism Catalogue)](#5-money-flow-definitions-mechanism-catalogue)
6. [Zero-Sum Invariant & Validation](#6-zero-sum-invariant--validation)
7. [Balance Sheet per Agent](#7-balance-sheet-per-agent)
8. [Aggregate Metric Computation](#8-aggregate-metric-computation)
9. [Per-Step Execution Order](#9-per-step-execution-order)
10. [SQLite Database Schema](#10-sqlite-database-schema)
11. [Error Handling & Edge Cases](#11-error-handling--edge-cases)
12. [Testing & Validation Strategy](#12-testing--validation-strategy)

---

## 1. Architecture & Design Rationale

### 1.1 Decision: Centralized Ledger Engine with Per-Agent Balance Views

The simulation uses a **single, authoritative LedgerEngine** that processes all transfers atomically. This design was chosen after a structured debate (see Decision Gate 1) balancing:

| Concern | Centralized Engine | Distributed Per-Agent Ledgers | Our Approach |
|---------|-------------------|------------------------------|--------------|
| Atomic invariant enforcement | ✅ Per-transaction | ⚠️ After reconciliation layer | Centralized engine enforces per-transaction |
| Auditability | Requires trust in engine | ✅ Independent verification | Per-agent views derived from engine + step-end reconciliation cross-check |
| Simplicity | ✅ One moving part | Many coordination parts | Central single engine |
| Bug resilience | Single point of failure | ✅ Multiple independent checks | + Defensive reconciliation pass at step end |
| Modeling flexibility | Step-bound | ✅ Event-driven possible | Step-based with frozen snapshots (best for deterministic replay) |

**Final Design:**
- A single `LedgerEngine` class holds the authoritative transaction log and all entity balances.
- Every financial transfer is processed through `LedgerEngine.transfer()`.
- Per-agent balance sheets are **derived views** — computed from the engine's state.
- A **defensive reconciliation pass** at step end re-derives the flow matrix from raw transactions and independently re-checks the zero-sum invariant, catching bugs in the engine itself.
- The flow matrix is a **materialized view** — aggregated from individual transactions each step.

### 1.2 Key Properties

| Property | Implementation |
|----------|---------------|
| **Deterministic** | Same seed + same agent decisions → identical ledger state |
| **Atomic** | Every transfer either completes fully or not at all |
| **Immutable** | Transactions are append-only; no updates or deletes |
| **Auditable** | Every dollar can be traced from source to sink |
| **Zero-sum** | Total money in system is conserved across transfers |

### 1.3 Money Conservation Principle

The simulation is a **closed system** with respect to money. No dollars are created or destroyed. The total money supply `M` is determined at initialization and remains constant:

```
M = sum(balance(entity) for all entities)  →  constant across steps
```

**Exception:** Certain mechanics may explicitly create or destroy money as part of their modeled behavior (e.g., a fine that removes money from circulation, or a subsidy that injects money). These exceptions must be:
1. Explicitly declared in the mechanism definition
2. Tracked in a `money_created` / `money_destroyed` accumulator per step
3. Verified so that `M_before + money_created - money_destroyed = M_after`

For Phase 0, there are **no money-creation or money-destruction mechanics**. The system is strictly zero-sum.

---

## 2. Ledger Entry Schema

### 2.1 Canonical Schema

Every financial event in the simulation produces a single ledger entry:

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `entry_id` | `UUID` | Unique identifier for this entry | Auto-generated, globally unique |
| `step` | `int` | Simulation step when this occurred | ≥ 0 |
| `timestamp` | `float` | Sub-step sequence number (for ordering within a step) | ≥ step, < step + 1 |
| `entity_id` | `str` | The entity whose balance changed | References valid entity |
| `counterparty_id` | `str` | The other side of the transaction | References valid entity (may be `"__system__"` for fees/destruction) |
| `mechanism` | `str` | What caused the flow | See Mechanism Catalogue (§5) |
| `category` | `str` | High-level classification | One of: `revenue`, `expense`, `transfer`, `fine`, `creation`, `destruction` |
| `amount` | `float` | Signed amount (positive = inflow, negative = outflow) | Non-zero |
| `balance_before` | `float` | Entity's cash balance before this entry | |
| `balance_after` | `float` | Entity's cash balance after this entry | `= balance_before + amount` |
| `description` | `str` | Human-readable explanation | |
| `reference_id` | `str | None` | ID of the associated contract, case, policy, or parcel | Nullable |

### 2.2 Schema Design Rationale

- **Why `timestamp` instead of just `step`?** Multiple transfers occur within a single step. `timestamp` provides within-step ordering, enabling replay and debugging. We use a float: `step.0001`, `step.0002`, etc.
- **Why `balance_before` and `balance_after`?** This makes balance reconstruction O(1) without summing all prior transactions for that entity. It also enables trivial invariant checks: `balance_after - balance_before == amount`.
- **Why `reference_id`?** This links the financial event back to its root cause (a specific insurance policy, court case, property parcel). This is essential for traceability and debugging.

### 2.3 Dual-Entry Representation

Although each transfer produces **two ledger entries** (one for the sender, one for the receiver), they share a common `transfer_id`:

| Field | Description |
|-------|-------------|
| `transfer_id` | UUID linking the two legs of a transfer |
| `from_entity_id` | Sender |
| `to_entity_id` | Receiver |
| `amount` | Positive amount transferred |
| `mechanism` | Same as ledger entry |
| `step` | When it happened |

The dual entries are:
- Entity A: `amount = -X`, `counterparty_id = B`
- Entity B: `amount = +X`, `counterparty_id = A`

The `transfer_id` links them, enabling the zero-sum assertion: `sum(amounts for both legs) == 0`.

### 2.4 Entry Indexing

The ledger is indexed on:
1. `(step, entity_id)` — for per-entity step-end balance computation
2. `(step, mechanism)` — for mechanism-level aggregate queries
3. `(step,)` — for step-level flow matrix aggregation
4. `transfer_id` — for pairing dual entries

---

## 3. Agent Definitions & Entity Registry

### 3.1 Entity Types

The simulation has these entity types, each with a unique `entity_id` prefix:

| Type | ID Prefix | Examples | Count | Roles in Money Flow |
|------|-----------|---------|-------|---------------------|
| **Citizen** | `CIT-` | `CIT-0001`, `CIT-0002` | N (configurable) | Pay LVT, premiums, court fees, guild dues. Receive dividend, wages, claims, court awards. |
| **National Trust** | `TRUST-` | `TRUST-0001` | 1 | Collect LVT. Distribute dividend. Pay Alliance skim. |
| **Alliance** | `ALLIANCE-` | `ALLIANCE-0001` | 1 | Receive skim from Trust. Spend on shared goods. Issue refunds to compacts. Issue war bonds. |
| **Insurer** | `INS-` | `INS-0001`, `INS-0002` | M (configurable) | Collect premiums. Pay claims. Earn/lose underwriting profit. Pay into reinsurance pools. |
| **Court** | `COURT-` | `COURT-0001`, `COURT-0002` | K (configurable) | Collect filing fees. Pay judge salaries. Transfer court awards. |
| **Guild** | `GUILD-` | `GUILD-0001`, `GUILD-0002` | G (configurable) | Collect membership dues. Pay member benefits. Manage mutual insurance pool. |
| **Compact** | `COMPACT-` | `COMPACT-0001` | C (configurable, ≥ 1) | Receive Alliance refunds. May levy supplemental taxes. Track aggregate compact-level metrics. |
| **System Account** | `__SYSTEM__` | `__SYSTEM__` | 1 | Money creation/destruction sink (Phase 0: no flows). |

### 3.2 Entity Registry

The `EntityRegistry` maintains the canonical list of all entities:

```python
@dataclass
class Entity:
    entity_id: str
    entity_type: str           # 'citizen' | 'trust' | 'alliance' | 'insurer' | 'court' | 'guild' | 'compact' | 'system'
    compact_id: str | None     # Which compact the entity belongs to (citizens, insurers, courts, guilds)
    is_active: bool            # False if entity has been removed from simulation
    created_at_step: int
    destroyed_at_step: int | None
    initial_balance: float     # Starting cash
```

### 3.3 Initialization

At simulation start (step 0):
- Each entity receives its `initial_balance`.
- The total money supply `M = sum(initial_balance for all entities)`.
- The `__SYSTEM__` account has balance 0.0 (it's a sink, not a source).
- Step 0 has a single initialization entry per entity: `mechanism = "init"`, `category = "creation"`.

---

## 4. Flow Matrix

### 4.1 Definition

The flow matrix is a **2D array** where `F[A][B]` = total dollars moved from entity type A to entity type B during a given step, aggregated across all individual transfers.

Rows are **sources** (money out), columns are **destinations** (money in).

### 4.2 Complete Flow Matrix

The full matrix encompasses all entity types. Each cell notes the mechanism(s) that cause the flow.

| From \ To | Citizens | National Trust | Alliance | Insurers | Courts | Guilds | Compacts | System | ∑ Out |
|-----------|----------|---------------|----------|----------|--------|--------|----------|--------|-------|
| **Citizens** | — | LVT | — | Premiums, Reins. premiums | Filing fees | Guild dues | Compact tax | Fines | ∑ |
| **National Trust** | Dividend | — | Skim | — | — | — | — | — | ∑ |
| **Alliance** | — | — | — | War bonds | — | — | Refund, Excess spend | — | ∑ |
| **Insurers** | Claims, Reins. payouts | — | — | Reins. premiums (B→A) | — | — | — | — | ∑ |
| **Courts** | Awards, Salary | — | — | — | — | — | — | — | ∑ |
| **Guilds** | Benefits, Mutual payouts | — | — | — | — | — | — | — | ∑ |
| **Compacts** | — | — | — | — | — | — | — | — | ∑ |
| **System** | — | — | — | — | — | — | — | — | ∑ |
| **∑ In** | ∑ | ∑ | ∑ | ∑ | ∑ | ∑ | ∑ | ∑ | **Σ = 0 ✓** |

### 4.3 Aggregation Rules

The flow matrix is **materialized each step** by:

```python
def build_flow_matrix(step_entries: list[LedgerEntry]) -> dict[tuple[str, str], float]:
    """
    Sum all transfer amounts grouped by (from_entity_type, to_entity_type).
    Uses the transfer_id to pair entries.
    """
    matrix = defaultdict(float)
    transfers = group_by_transfer_id(step_entries)
    
    for transfer in transfers:
        from_type = entity_registry[transfer.from_entity_id].entity_type
        to_type = entity_registry[transfer.to_entity_id].entity_type
        amount = abs(transfer.amount)
        matrix[(from_type, to_type)] += amount
    
    return matrix
```

**Important:** The matrix sums **absolute** transfer amounts (always positive). The zero-sum assertion applies to the net of all entries, not the matrix cells individually.

### 4.4 Drill-Down Matrix (per-Mechanism)

For debugging and analysis, a 3D flow cube `F[A][B][mechanism]` can be computed:

```python
def build_flow_cube(step_entries):
    """Mechanism-level breakdown of flows between entity types."""
    cube = defaultdict(lambda: defaultdict(float))
    for entry in step_entries:
        # Only count outflow entries (negative amounts for sender)
        if entry.amount < 0:
            from_type = entity_registry[entry.entity_id].entity_type
            to_type = entity_registry[entry.counterparty_id].entity_type
            cube[(from_type, to_type, entry.mechanism)] += abs(entry.amount)
    return cube
```

### 4.5 Per-Entity Flow Vector

Each entity also has a per-step flow vector — a breakdown of its inflows and outflows by counterparty and mechanism. This is the raw data for agent-level analysis (e.g., "how much did citizen 42 pay in LVT this step?").

---

## 5. Money Flow Definitions (Mechanism Catalogue)

This section defines **every money-moving mechanism** in the simulation. Each mechanism specifies: sender, receiver, triggering condition, amount formula, and validation rules.

### 5.1 Land Value Tax (LVT)

| Property | Value |
|----------|-------|
| **Mechanism** | `lvt` |
| **Category** | `revenue` (for Trust), `expense` (for citizen) |
| **From** | Citizen (landowner) |
| **To** | National Trust |
| **Trigger** | Each step, for every land parcel owned |
| **Amount** | `declared_value × lvt_rate / steps_per_year` |
| **Validation** | Citizen must have sufficient balance (if insufficient, triggers delinquency — see §11.2) |
| **Per-step** | One entry per parcel per step |

**Note:** LVT is computed from the **declared value** (Harberger self-assessment), not an appraised value. This is the mechanism that makes Harberger self-assessment self-enforcing.

### 5.2 Citizen's Dividend

| Property | Value |
|----------|-------|
| **Mechanism** | `dividend` |
| **Category** | `revenue` (for citizen), `expense` (for Trust) |
| **From** | National Trust |
| **To** | Every citizen (universal) |
| **Trigger** | Each step, after LVT collection and Alliance skim |
| **Amount** | `(total_lvt_this_step × (1 - alliance_skim_rate)) / citizen_count` |
| **Validation** | Trust must have sufficient balance (sum of dividend payouts ≤ Trust balance) |
| **Per-step** | One entry per citizen |

### 5.3 Alliance Skim

| Property | Value |
|----------|-------|
| **Mechanism** | `alliance_skim` |
| **Category** | `expense` (for Trust), `revenue` (for Alliance) |
| **From** | National Trust |
| **To** | Alliance |
| **Trigger** | Each step, after LVT collection, before dividend |
| **Amount** | `total_lvt_this_step × alliance_skim_rate` |
| **Validation** | skim_rate ∈ [0.0, 1.0]; default is 0.10 (10%) |

### 5.4 Alliance Refund to Compacts

| Property | Value |
|----------|-------|
| **Mechanism** | `alliance_refund` |
| **Category** | `expense` (for Alliance), `revenue` (for Compact) |
| **From** | Alliance |
| **To** | Compacts (distribution) |
| **Trigger** | Each step, after Alliance spending |
| **Amount** | `alliance_skim - alliance_spending`, distributed proportionally by compact LVT contribution |
| **Validation** | Sum of refunds ≤ Alliance balance |

### 5.5 Insurance Premium

| Property | Value |
|----------|-------|
| **Mechanism** | `premium` |
| **Category** | `expense` (for citizen), `revenue` (for insurer) |
| **From** | Citizen (policyholder) |
| **To** | Insurer |
| **Trigger** | Each step, for each active insurance policy |
| **Amount** | Per the insurance contract (based on declared risk, coverage, etc.) |
| **Validation** | Citizen must be able to pay (otherwise policy lapses — see §11.3) |

### 5.6 Insurance Claim Payout

| Property | Value |
|----------|-------|
| **Mechanism** | `claim` |
| **Category** | `expense` (for insurer), `revenue` (for citizen) |
| **From** | Insurer |
| **To** | Citizen (claimant) |
| **Trigger** | When a claim is filed, investigated, and approved |
| **Amount** | Per the insurance contract terms (≤ coverage limit) |
| **Validation** | Insurer must have sufficient reserves (otherwise triggers insolvency cascade — see §11.4) |

### 5.7 Court Filing Fee

| Property | Value |
|----------|-------|
| **Mechanism** | `court_fee` |
| **Category** | `expense` (for citizen), `revenue` (for court) |
| **From** | Plaintiff (citizen) |
| **To** | Court |
| **Trigger** | When a case is filed |
| **Amount** | Per the court's fee schedule (configurable) |
| **Validation** | Plaintiff must have sufficient balance to pay the fee |

### 5.8 Court Award

| Property | Value |
|----------|-------|
| **Mechanism** | `court_award` |
| **Category** | `expense` (for defendant), `revenue` (for plaintiff) |
| **From** | Defendant (citizen or business) |
| **To** | Plaintiff (citizen or business) |
| **Trigger** | When a case is adjudicated in favor of plaintiff |
| **Amount** | Determined by court's damages calculation (bounded by liability cap) |
| **Validation** | Defendant must pay (if insufficient, triggers bankruptcy/collection — see §11.5) |

### 5.9 Court Salary

| Property | Value |
|----------|-------|
| **Mechanism** | `court_salary` |
| **Category** | `expense` (for court), `revenue` (for citizen) |
| **From** | Court |
| **To** | Judge (citizen or dedicated court staff entity) |
| **Trigger** | Each step, per active judge |
| **Amount** | Per the court's budget allocation |
| **Validation** | Court must have sufficient balance |

### 5.10 Guild Membership Dues

| Property | Value |
|----------|-------|
| **Mechanism** | `guild_dues` |
| **Category** | `expense` (for citizen), `revenue` (for guild) |
| **From** | Citizen (guild member) |
| **To** | Guild |
| **Trigger** | Each step, for each active guild membership |
| **Amount** | Per the guild's dues schedule |
| **Validation** | Member must have sufficient balance (otherwise membership lapses) |

### 5.11 Guild Benefits

| Property | Value |
|----------|-------|
| **Mechanism** | `guild_benefit` |
| **Category** | `expense` (for guild), `revenue` (for citizen) |
| **From** | Guild |
| **To** | Citizen (guild member) |
| **Trigger** | Per guild's benefit schedule (mutual insurance, training stipends, etc.) |
| **Amount** | Per guild policy |
| **Validation** | Guild mutual pool must have sufficient balance |

### 5.12 War Bond (Premium)

| Property | Value |
|----------|-------|
| **Mechanism** | `war_bond_premium` |
| **Category** | `expense` (for Alliance), `revenue` (for insurer) |
| **From** | Alliance |
| **To** | Insurer (underwriting the bond) |
| **Trigger** | When war bonds are issued (during invasion event) |
| **Amount** | Per bond terms (principal × risk premium) |

### 5.13 War Bond (Redemption)

| Property | Value |
|----------|-------|
| **Mechanism** | `war_bond_redemption` |
| **Category** | `expense` (for Alliance), `revenue` (for insurer) |
| **From** | Alliance |
| **To** | Insurer (bondholder) |
| **Trigger** | When war bond matures or invasion ends |
| **Amount** | Principal + interest |

### 5.14 Compact Tax (Supplemental)

| Property | Value |
|----------|-------|
| **Mechanism** | `compact_tax` |
| **Category** | `expense` (for citizen), `revenue` (for compact) |
| **From** | Citizen within the compact |
| **To** | Compact treasury |
| **Trigger** | Optional per-compact configuration (e.g., supplemental LVT, sales tax) |
| **Amount** | Per compact's tax schedule |

### 5.15 Harberger Property Sale

| Property | Value |
|----------|-------|
| **Mechanism** | `harberger_sale` |
| **Category** | `transfer` |
| **From** | Buyer |
| **To** | Seller |
| **Trigger** | When a Harberger purchase completes (after free-refusal window) |
| **Amount** | Parcel's declared price |
| **Validation** | Buyer must have sufficient balance. If seller refuses during penalty phase, seller pays 15% penalty to buyer. |

### 5.16 Compact Sunset Payment (if applicable)

| Property | Value |
|----------|-------|
| **Mechanism** | `sunset_payment` |
| **Category** | `expense` (for Alliance), `revenue` (for compact) |
| **From** | Alliance |
| **To** | Compact |
| **Trigger** | When a compact exits the Alliance (per sunset terms) |
| **Amount** | Per Alliance charter terms |

### 5.17 Reinsurance Premium

| Property | Value |
|----------|-------|
| **Mechanism** | `reinsurance_premium` |
| **Category** | `expense` (for insurer), `revenue` (for insurer) |
| **From** | Insurer (ceding risk) |
| **To** | Insurer (reinsurer) |
| **Trigger** | Per reinsurance contract terms |
| **Amount** | Per contract schedule |

### 5.18 Reinsurance Claim Recovery

| Property | Value |
|----------|-------|
| **Mechanism** | `reinsurance_recovery` |
| **Category** | `expense` (for reinsurer), `revenue` (for ceding insurer) |
| **From** | Insurer (reinsurer) |
| **To** | Insurer (ceding insurer) |
| **Trigger** | When a ceded claim is approved by reinsurer |
| **Amount** | Per reinsurance contract (ceding percentage × claim amount) |

### 5.19 Fines & Penalties

| Property | Value |
|----------|-------|
| **Mechanism** | `fine` |
| **Category** | `expense` (for citizen), `revenue` (for System / court) |
| **From** | Citizen |
| **To** | System (money destroyed) or Court |
| **Trigger** | By court judgment or by automatic penalty (e.g., Harberger refusal penalty) |
| **Amount** | Per court ruling or per rule |

---

## 6. Zero-Sum Invariant & Validation

### 6.1 The Invariant

The fundamental invariant is:

```
For every step:
  sum(balance_before for all entities) = sum(balance_after for all entities)
  
For every individual transfer:
  amount(from) + amount(to) = 0  (i.e., money is neither created nor destroyed)
```

### 6.2 Validation Layers

We validate the invariant at **four granularities**:

#### Layer 1: Per-Transfer Validation (during execution)

Every call to `LedgerEngine.transfer()` immediately asserts:

```python
def transfer(self, from_id, to_id, amount, mechanism, reference_id=None):
    assert amount > 0, "Transfer amount must be positive"
    assert from_id != to_id, "Cannot transfer to self"
    assert from_id in self.entities, f"Unknown sender: {from_id}"
    assert to_id in self.entities, f"Unknown receiver: {to_id}"
    assert self.entities[from_id].balance >= amount, f"Insufficient balance for {from_id}"
    
    from_before = self.entities[from_id].balance
    to_before = self.entities[to_id].balance
    
    # Execute
    self.entities[from_id].balance -= amount
    self.entities[to_id].balance += amount
    
    # Per-transfer invariant
    net_change = (from_before - amount) + (to_before + amount) - (from_before + to_before)
    assert net_change == 0, f"Zero-sum violation on transfer {from_id} -> {to_id}: {amount}"
    
    # Record dual entries
    self._record_entry(from_id, to_id, -amount, mechanism, from_before, from_before - amount, reference_id)
    self._record_entry(to_id, from_id, +amount, mechanism, to_before, to_before + amount, reference_id)
```

#### Layer 2: Per-Step End-to-End Validation

At step end, verify that no money was created or destroyed across the entire step:

```python
def validate_step_invariant(self, step):
    total_before = sum(e.initial_balance for e in self.entities.values() 
                       if e.created_at_step <= step and (e.destroyed_at_step is None or e.destroyed_at_step > step))
    total_after = sum(e.balance for e in self.entities.values()
                      if e.created_at_step <= step and (e.destroyed_at_step is None or e.destroyed_at_step > step))
    
    # Account for entities created/destroyed this step
    creations = sum(e.initial_balance for e in self.entities.values() if e.created_at_step == step)
    destructions = sum(e.balance for e in self.entities.values() if e.destroyed_at_step == step)
    
    assert abs(total_after - (total_before + creations - destructions)) < 1e-9, \
        f"Step {step}: Zero-sum invariant violated! before={total_before}, after={total_after}, net={total_after - total_before}"
```

#### Layer 3: Flow Matrix Validation

After building the flow matrix, verify:

```python
def validate_flow_matrix(self, matrix, step_entries):
    # Row totals: total outflow per entity type
    row_totals = defaultdict(float)
    col_totals = defaultdict(float)
    for (from_type, to_type), amount in matrix.items():
        row_totals[from_type] += amount
        col_totals[to_type] += amount
    
    # Total inflows must equal total outflows
    total_out = sum(row_totals.values())
    total_in = sum(col_totals.values())
    assert abs(total_out - total_in) < 1e-9, \
        f"Flow matrix not balanced: out={total_out}, in={total_in}"
    
    # Net flow for each entity type should match entity-level balance changes
    for entity_type in entity_types:
        net_out = row_totals[entity_type]
        net_in = col_totals[entity_type]
        type_balance_change = compute_type_balance_change(entity_type, step_entries)
        assert abs((net_in - net_out) - type_balance_change) < 1e-9, \
            f"Entity type {entity_type}: flow matrix net ({net_in - net_out}) != balance change ({type_balance_change})"
```

#### Layer 4: Defensive Reconciliation Pass

As an independent cross-check (catches engine bugs), we re-derive the total money supply from raw transaction logs rather than from the engine's balance cache:

```python
def reconcile_from_transaction_log(self, step):
    """Rebuild total money supply from the transaction log alone."""
    balances = defaultdict(float)
    # Start from initial balances
    for entity in self.entities.values():
        balances[entity.entity_id] = entity.initial_balance
    
    # Apply all transactions up to this step
    for entry in self.get_entries_up_to(step):
        balances[entry.entity_id] += entry.amount
    
    # Check: sum of reconstructed balances should equal sum of engine balances
    engine_total = sum(e.balance for e in self.entities.values())
    log_total = sum(balances.values())
    assert abs(engine_total - log_total) < 1e-9, \
        f"Reconciliation failed: engine={engine_total}, log={log_total}"
```

### 6.3 Edge Cases

| Edge Case | Handling |
|-----------|----------|
| **Floating-point precision** | All comparisons use `abs(x - y) < 1e-9` tolerance. Use `Decimal` for production (Phase 0: `float` is acceptable for prototyping). |
| **Entity creation mid-step** | New entity starts at balance 0.0. Money flows out of existing entities to it. Net supply unchanged. |
| **Entity destruction mid-step** | Remaining balance must be transferred to a designated receiver (e.g., heirs, creditors) before destruction. |
| **Simultaneous transfers** | Within a single step, transfers are sequential (ordered by sub-step timestamp). No concurrent mutations. |
| **Round-off in dividend distribution** | If `total_dividend / citizen_count` doesn't divide evenly, the remainder stays in the Trust (recorded as `dividend_remainder`). |

### 6.4 Failure Response

If any invariant check fails:
1. **Hard failure (assertion):** Halt simulation immediately with a detailed error report including the step, entity, and offending transfer.
2. **Soft failure (logging):** Log the discrepancy, dump the current state to a debug file, and allow the simulation to continue (for debugging during development).
3. **Default mode for Phase 0:** Hard failure. The invariant is the core contract — violation means a bug.

---

## 7. Balance Sheet per Agent

### 7.1 Canonical Balance Sheet Schema

Every entity has a balance sheet computed at step boundaries. The canonical schema:

| Field | Type | Description | Computation |
|-------|------|-------------|-------------|
| `entity_id` | `str` | Entity identifier | From registry |
| `step` | `int` | Step this balance sheet applies to | |
| `cash` | `float` | Liquid currency | Current balance from ledger engine |
| `land_value` | `float` | Sum of declared values of owned parcels | Sum of `HarbergerParcel.declared_value` for parcels where `owner_id == entity_id` |
| `property_count` | `int` | Number of parcels owned | Count of owned parcels |
| `insurance_policies` | `int` | Number of active insurance policies | Count of policies where `policyholder == entity_id` and `active == True` |
| `total_premiums` | `float` | Total premium due for current step | Sum of `premium` for active policies |
| `guild_memberships` | `int` | Number of active guild memberships | Count of active guild memberships |
| `total_guild_dues` | `float` | Total dues due for current step | Sum of dues for active memberships |
| `outstanding_liability` | `float` | Total unpaid court judgments against agent | Sum of awards in `CourtCase` where `defendant == entity_id` and not yet paid |
| `outstanding_claims_owed` | `float` | Total unpaid claims agent is owed | Sum of approved but unpaid claims |
| `lvt_due` | `float` | LVT due next step | Sum of `declared_value × lvt_rate / steps_per_year` for owned parcels |
| `lvt_paid_this_step` | `float` | LVT actually paid current step | Sum of LVT entries this step for this entity |
| `net_worth` | `float` | Cash + land - outstanding liability | `cash + land_value - outstanding_liability` |
| `total_income_this_step` | `float` | Sum of all inflows this step | Sum of positive `amount` entries for this entity this step |
| `total_expenses_this_step` | `float` | Sum of all outflows this step | Sum of negative `amount` entries (abs value) for this entity this step |
| `is_bankrupt` | `bool` | Whether agent has negative net worth | `net_worth < 0` |

### 7.2 Entity-Type-Specific Balance Sheets

Some entity types have additional fields:

#### Insurer

| Field | Type | Description |
|-------|------|-------------|
| `premium_reserves` | `float` | Total unearned premium reserves |
| `loss_reserves` | `float` | Reserves for reported but unpaid claims |
| `reinsurance_ceded` | `float` | Amount of risk ceded to reinsurers |
| `reinsurance_recoverable` | `float` | Amount recoverable from reinsurers |
| `solvency_ratio` | `float` | `cash / (expected_future_claims + loss_reserves)` |
| `premiums_collected_this_step` | `float` | Total premium revenue this step |
| `claims_paid_this_step` | `float` | Total claims paid this step |
| `underwriting_profit_this_step` | `float` | `premiums_collected - claims_paid - expenses` |

#### Court

| Field | Type | Description |
|-------|------|-------------|
| `filing_fees_collected` | `float` | Total fees collected this step |
| `salaries_paid` | `float` | Total judge/staff salaries paid this step |
| `cases_adjudicated` | `int` | Number of cases resolved this step |
| `cases_pending` | `int` | Cases in backlog |
| `budget_surplus` | `float` | `filing_fees_collected - salaries_paid` |

#### Guild

| Field | Type | Description |
|-------|------|-------------|
| `member_count` | `int` | Active members |
| `mutual_pool_balance` | `float` | Balance of the mutual insurance pool |
| `dues_collected_this_step` | `float` | Total dues received |
| `benefits_paid_this_step` | `float` | Total benefits paid out |

#### National Trust

| Field | Type | Description |
|-------|------|-------------|
| `lvt_collected_this_step` | `float` | Total LVT received |
| `dividend_paid_this_step` | `float` | Total dividend distributed |
| `skim_paid_this_step` | `float` | Amount skimmed to Alliance |
| `surplus_this_step` | `float` | `lvt_collected - dividend_paid - skim_paid` |

#### Alliance

| Field | Type | Description |
|-------|------|-------------|
| `skim_received` | `float` | Skim received from Trust |
| `spending_this_step` | `float` | Total Alliance spending |
| `refund_paid_this_step` | `float` | Total refunds to compacts |
| `war_bonds_outstanding` | `float` | Value of outstanding war bonds |

### 7.3 Balance Sheet Computation

Balance sheets are computed **once per step** (at step end) by the `BalanceSheetEngine`:

```python
def compute_balance_sheets(self, step):
    sheets = {}
    for entity in self.entity_registry.all():
        sheet = EntityBalanceSheet(
            entity_id=entity.entity_id,
            step=step,
            cash=self.ledger.get_balance(entity.entity_id),
            land_value=self.land_registry.get_total_value(entity.entity_id),
            property_count=self.land_registry.get_parcel_count(entity.entity_id),
            insurance_policies=self.insurance_registry.active_policy_count(entity.entity_id),
            total_premiums=self.insurance_registry.total_premiums_due(entity.entity_id),
            guild_memberships=self.guild_registry.active_membership_count(entity.entity_id),
            total_guild_dues=self.guild_registry.total_dues_due(entity.entity_id),
            outstanding_liability=self.court_registry.total_judgments_against(entity.entity_id),
            outstanding_claims_owed=self.insurance_registry.total_unpaid_claims(entity.entity_id),
            lvt_due=self.lvt_engine.lvt_due(entity.entity_id),
            lvt_paid_this_step=self.ledger.sum_for_entity(entity.entity_id, step, 'lvt'),
            # Computed fields
            net_worth=cash + land_value - outstanding_liability,
            total_income_this_step=self.ledger.sum_inflows(entity.entity_id, step),
            total_expenses_this_step=self.ledger.sum_outflows(entity.entity_id, step),
            is_bankrupt=(cash + land_value - outstanding_liability) < 0,
        )
        sheets[entity.entity_id] = sheet
    return sheets
```

---

## 8. Aggregate Metric Computation

All aggregate metrics are computed at step end from the ledger, balance sheets, and flow matrix.

### 8.1 Metric Definitions

| # | Metric | Formula | Source Data | Frequency |
|---|--------|---------|------------|-----------|
| M1 | **Total LVT collected** | `sum(ledger_entries where mechanism='lvt' and step=N)` | Ledger (amount, positive) | Per step |
| M2 | **Total Dividend paid** | `sum(ledger_entries where mechanism='dividend' and step=N)` | Ledger (amount, positive) | Per step |
| M3 | **Total Premiums collected** | `sum(ledger_entries where mechanism='premium' and step=N)` | Ledger | Per step |
| M4 | **Total Claims paid** | `sum(ledger_entries where mechanism='claim' and step=N)` | Ledger | Per step |
| M5 | **Total Court fees collected** | `sum(ledger_entries where mechanism='court_fee' and step=N)` | Ledger | Per step |
| M6 | **Total Court awards paid** | `sum(ledger_entries where mechanism='court_award' and step=N)` | Ledger | Per step |
| M7 | **Total Guild dues collected** | `sum(ledger_entries where mechanism='guild_dues' and step=N)` | Ledger | Per step |
| M8 | **Total Guild benefits paid** | `sum(ledger_entries where mechanism='guild_benefit' and step=N)` | Ledger | Per step |
| M9 | **Total Alliance skim** | `sum(ledger_entries where mechanism='alliance_skim' and step=N)` | Ledger | Per step |
| M10 | **Total Alliance refund** | `sum(ledger_entries where mechanism='alliance_refund' and step=N)` | Ledger | Per step |
| M11 | **Total LVT base** | `sum(declared_value for all parcels)` | Land registry | Per step |
| M12 | **Average LVT rate** | `M1 / M11` (effective) | Computed | Per step |
| M13 | **Gini coefficient (wealth)** | Standard Gini over `net_worth` for all citizens | Balance sheets | Per step |
| M14 | **Gini coefficient (income)** | Standard Gini over `total_income_this_step` for all citizens | Balance sheets | Per step |
| M15 | **Litigation rate** | `cases_filed_this_step / total_citizens` | Court registry + entity registry | Per step |
| M16 | **Court backlog** | `pending_cases / active_courts` | Court registry | Per step |
| M17 | **Premium-to-claim ratio** | `M3 / M4` (rolling window of last S steps) | Ledger | Rolling window |
| M18 | **Insurance pool solvency** | `total_insurer_cash / total_expected_claims_next_step` | Balance sheets + actuarial | Per step |
| M19 | **Harberger valuation gap** | `median(declared_value / estimated_true_value for all parcels)` | Land registry | Per step |
| M20 | **Bankruptcy rate** | `count(agents where is_bankrupt=True) / total_agents` | Balance sheets | Per step |
| M21 | **Compact migration rate** | `agents_who_changed_compact_this_step / total_agents` | Entity registry | Per step |
| M22 | **Market concentration — insurance** | Herfindahl-Hirschman Index: `sum((premium_share_of_insurer_i)^2 for all insurers)` | Flow matrix / ledger | Per step |
| M23 | **Market concentration — land** | `sum(land_value for top_10_pct_owners) / total_land_value` | Land registry | Per step |
| M24 | **Dividend as % of median income** | `dividend_amount / median(total_income_this_step for citizens)` | Computed | Per step |
| M25 | **Flow matrix completeness** | `sum(matrix.values())` should equal `sum(abs(entry.amount) for all entries in step) / 2` | Flow matrix + ledger | Per step (validation) |
| M26 | **Money supply** | `sum(cash for all entities)` | Balance sheets | Per step |
| M27 | **Net money creation/destruction** | `M26(step) - M26(step-1)` | Balance sheets | Per step (should be 0) |
| M28 | **Evasion rate (est.)** | `estimated_violations / total_transactions` | Adversarial detection module | Per step (Phase 3+) |

### 8.2 Gini Coefficient Computation

```python
def compute_gini(values: list[float]) -> float:
    """
    Standard Gini coefficient.
    0 = perfect equality, 1 = perfect inequality.
    """
    sorted_values = sorted(values)
    n = len(sorted_values)
    if n == 0 or sum(sorted_values) == 0:
        return 0.0
    cumulative = 0.0
    for i, v in enumerate(sorted_values):
        cumulative += (i + 1) * v
    return (2 * cumulative) / (n * sum(sorted_values)) - (n + 1) / n
```

### 8.3 Herfindahl-Hirschman Index (HHI)

```python
def compute_hhi(shares: list[float]) -> float:
    """Sum of squared market shares. Range: 1/N to 1 (or 0 to 10,000 in percentage form)."""
    total = sum(shares)
    if total == 0:
        return 0.0
    return sum((s / total) ** 2 for s in shares)
```

### 8.4 Rolling Window Metrics

For metrics that use a rolling window (like M17 premium-to-claim ratio), the window size `S` is a configurable parameter (default: `S = 12` steps, representing ~1 year at monthly steps):

```python
def rolling_sum(mechanism: str, current_step: int, window: int) -> float:
    return sum(
        entry.amount for entry in ledger
        if entry.mechanism == mechanism
        and current_step - window < entry.step <= current_step
    )
```

### 8.5 Metrics Aggregation

Metrics are computed by the `MetricsEngine` and stored in a time-series table:

```python
@dataclass
class StepMetrics:
    step: int
    total_lvt: float
    total_dividend: float
    total_premiums: float
    total_claims: float
    total_court_fees: float
    total_court_awards: float
    total_guild_dues: float
    total_guild_benefits: float
    total_alliance_skim: float
    total_alliance_refund: float
    gini_wealth: float
    gini_income: float
    litigation_rate: float
    court_backlog: float
    premium_claim_ratio: float
    insurance_solvency: float
    harberger_gap: float
    bankruptcy_rate: float
    migration_rate: float
    insurance_hhi: float
    land_concentration: float
    dividend_income_ratio: float
    money_supply: float
    money_creation: float       # Should be 0
    zero_sum_verified: bool     # True if all invariants passed
```

---

## 9. Per-Step Execution Order

### 9.1 Simulation Step Sequence

Each simulation step follows this exact execution order. The ledger engine is integrated at every substep.

```
STEP N
│
├── 0. STEP INITIALIZATION
│   ├── Snapshot pre-step balances
│   ├── Reset per-step accumulators (flow matrix accumulators, per-mechanism totals)
│   └── Close out any pending cross-step operations
│
├── 1. EVENT CHECK
│   ├── Check if any events fire this step (disasters, invasions, etc.)
│   └── If yes, apply event effects (which may trigger transfers)
│
├── 2. COMPULSORY REVENUE COLLECTION (fixed-order per entity)
│   ├── 2a. COLLECT LVT
│   │   ├── For each citizen with land: compute LVT = declared_value × rate / steps_per_year
│   │   ├── Ledger: transfer(CIT, TRUST, amount, 'lvt')
│   │   └── Handle delinquency if insufficient balance
│   │
│   ├── 2b. COLLECT INSURANCE PREMIUMS
│   │   ├── For each active policy: compute premium due
│   │   ├── Ledger: transfer(CIT, INS, amount, 'premium')
│   │   └── Handle non-payment (policy lapse)
│   │
│   ├── 2c. COLLECT GUILD DUES
│   │   ├── For each active membership: compute dues due
│   │   ├── Ledger: transfer(CIT, GUILD, amount, 'guild_dues')
│   │   └── Handle non-payment (membership lapse)
│   │
│   ├── 2d. COLLECT COURT FILING FEES (for newly filed cases)
│   │   ├── For each case filed this step:
│   │   ├── Ledger: transfer(CIT, COURT, fee, 'court_fee')
│   │   └── Case enters docket if paid
│   │
│   └── 2e. COLLECT COMPACT TAX (if applicable)
│       ├── For each citizen in compact with supplemental tax:
│       ├── Ledger: transfer(CIT, COMPACT, amount, 'compact_tax')
│       └── Handle delinquency
│
├── 3. ECONOMIC ACTIVITY (markets)
│   ├── 3a. LABOR MARKET
│   │   ├── Workers offer labor, businesses hire
│   │   └── Ledger: transfer(BUSINESS, CIT, wage, 'wage')
│   │
│   ├── 3b. GOODS MARKET
│   │   ├── Businesses sell goods to citizens
│   │   └── Ledger: transfer(CIT, BUSINESS, price, 'goods_purchase')
│   │
│   ├── 3c. HARBERGER PROPERTY MARKET
│   │   ├── Process pending purchase attempts (free-refusal windows)
│   │   ├── Ledger: transfer(BUYER, SELLER, price, 'harberger_sale')
│   │   └── Handle refusals (penalty transfer if applicable)
│   │   ├── Update declared values (citizens may adjust self-assessments)
│   │   └── Ledger: no transfer for declaration change (affects future LVT)
│   │
│   └── 3d. OTHER MARKETS (investment, etc. — Phase 2+)
│
├── 4. INSURANCE CLAIMS
│   ├── Evaluate accidents, illnesses, and other loss events
│   ├── For each approved claim:
│   ├── Ledger: transfer(INS, CIT, amount, 'claim')
│   └── If insurer insufficient: partial payment + insolvency flag
│
├── 5. REINSURANCE SETTLEMENTS
│   ├── For ceded claims: ceding insurer recovers from reinsurer
│   └── Ledger: transfer(REINSURER, CEDING_INS, amount, 'reinsurance_recovery')
│
├── 6. COURT SYSTEM
│   ├── 6a. ADJUDICATE CASES
│   │   ├── For each case ready for judgment:
│   │   ├── Court determines liability and damages
│   │   └── Ledger: transfer(DEFENDANT, PLAINTIFF, award, 'court_award')
│   │       (If defendant has insurance: transfer(INS, DEFENDANT, award, 'claim') first)
│   │   └── Handle insufficient defendant funds (bankruptcy/collection)
│   │
│   ├── 6b. PAY COURT SALARIES
│   │   └── Ledger: transfer(COURT, JUDGE, salary, 'court_salary')
│   │
│   └── 6c. UPDATE COURT BACKLOG
│       ├── Remove adjudicated cases from pending queue
│       └── Add newly filed cases to pending queue
│
├── 7. TRUST DISTRIBUTION
│   ├── 7a. ALLIANCE SKIM
│   │   ├── Compute skim = total_lvt_this_step × skim_rate
│   │   └── Ledger: transfer(TRUST, ALLIANCE, skim, 'alliance_skim')
│   │
│   ├── 7b. ALLIANCE SPENDING + REFUND
│   │   ├── Alliance allocates spending (shared goods, defense, etc.)
│   │   └── Ledger: transfer(ALLIANCE, COMPACT, refund, 'alliance_refund')
│   │       (May also transfer directly to third parties for Alliance purchases)
│   │
│   └── 7c. CITIZEN'S DIVIDEND
│       ├── Compute dividend = (total_lvt_this_step - skim) / citizen_count
│       └── For each citizen:
│           └── Ledger: transfer(TRUST, CIT, dividend, 'dividend')
│
├── 8. GUILD BENEFITS
│   ├── Guilds distribute benefits to members
│   └── Ledger: transfer(GUILD, CIT, amount, 'guild_benefit')
│
├── 9. AGENT PLANNING & ACTION (Phase 2+)
│   ├── Each agent evaluates options based on current state
│   ├── Agents attempt to take actions (hire, fire, buy insurance, sue, etc.)
│   │   └── These actions flow back to substeps 2–8 in the *next* step
│   └── Note: No immediate financial transfers here; actions queue for next step's execution
│
└── 10. STEP CLOSE
    ├── Compute Balance Sheets for all entities
    ├── Build Flow Matrix for this step
    ├── Compute all Aggregate Metrics (§8)
    ├── Validate Zero-Sum Invariants (all 4 layers — §6.2)
    ├── Check for Failure Modes (bankruptcy cascade, insolvency, etc.)
    ├── Record step results to database
    └── Advance sub-step counter for next step
```

### 9.2 Execution Order Rationale

The order matters. Key design decisions:

| Decision | Rationale |
|----------|-----------|
| **LVT collected first** | LVT is the foundational revenue source. It must be collected before the Trust can distribute anything. |
| **Insurance premiums before claims** | Premiums fund claims. Collecting premiums first ensures the pool is funded for claims that occur this step. |
| **Court fees before adjudication** | Courts need revenue to operate. Fees are collected when cases are filed; cases are adjudicated later in the same step. |
| **Alliance distribution before agent planning** | Agents make decisions knowing their updated balance (post-dividend, post-refund). |
| **Guild benefits before agent planning** | Same rationale — agents need full income picture before planning. |
| **Agent actions queue for next step** | This prevents infinite loops within a single step (agent acts → transfer → agent reacts → transfer → ...). A step is a discrete settlement period. |

### 9.3 Sub-Step Timestamps

Each transfer within a step gets a sub-step timestamp for deterministic ordering:

```python
def make_timestamp(step: int, substep: int, sequence: int) -> float:
    """
    Returns a float timestamp like 42.0203 for step 42, substep 2, sequence 3.
    Substeps correspond to the numbered sections in §9.1.
    Sequence within a substep is a monotonically increasing counter.
    """
    return step + (substep / 100) + (sequence / 10000)
```

This ensures replayability: given the same sequence of agent decisions, the ledger is bit-for-bit identical.

### 9.4 Deterministic Batching

For performance, transfers within a substep can be batched. The batch guarantees:

```python
@dataclass
class TransferBatch:
    step: int
    substep: int           # 1-10, matching §9.1
    transfers: list[tuple[str, str, float, str]]  # (from, to, amount, mechanism)
    # The engine processes these in order and assigns sequences 1..N
    
    def execute(self, engine: LedgerEngine):
        for i, (from_id, to_id, amount, mechanism) in enumerate(self.transfers):
            engine.transfer(from_id, to_id, amount, mechanism, 
                          timestamp=make_timestamp(self.step, self.substep, i+1))
```

---

## 10. SQLite Database Schema

### 10.1 Schema Overview

The simulation uses SQLite for per-run storage. The schema is designed for efficient querying of balance sheets, flows, and metrics.

```sql
-- Entity Registry
CREATE TABLE entities (
    entity_id       TEXT PRIMARY KEY,
    entity_type     TEXT NOT NULL CHECK(entity_type IN (
                        'citizen', 'trust', 'alliance', 'insurer', 
                        'court', 'guild', 'compact', 'system'
                    )),
    compact_id      TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at_step INTEGER NOT NULL,
    destroyed_at_step INTEGER,
    initial_balance REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (compact_id) REFERENCES entities(entity_id)
);

-- Ledger (canonical transaction log)
CREATE TABLE ledger_entries (
    entry_id        TEXT PRIMARY KEY,          -- UUID
    transfer_id     TEXT NOT NULL,             -- UUID linking dual entries
    step            INTEGER NOT NULL,
    timestamp       REAL NOT NULL,
    entity_id       TEXT NOT NULL,
    counterparty_id TEXT NOT NULL,
    mechanism       TEXT NOT NULL,             -- See mechanism catalogue
    category        TEXT NOT NULL CHECK(category IN (
                        'revenue', 'expense', 'transfer', 'fine', 'creation', 'destruction'
                    )),
    amount          REAL NOT NULL,             -- Signed
    balance_before  REAL NOT NULL,
    balance_after   REAL NOT NULL,
    description     TEXT,
    reference_id    TEXT,                      -- Links to policy/case/parcel/etc.
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (counterparty_id) REFERENCES entities(entity_id)
);

CREATE INDEX idx_ledger_step ON ledger_entries(step);
CREATE INDEX idx_ledger_entity ON ledger_entries(entity_id);
CREATE INDEX idx_ledger_mechanism ON ledger_entries(step, mechanism);
CREATE INDEX idx_ledger_transfer ON ledger_entries(transfer_id);

-- Balance Sheets (snapshot per entity per step)
CREATE TABLE balance_sheets (
    entity_id        TEXT NOT NULL,
    step             INTEGER NOT NULL,
    cash             REAL NOT NULL,
    land_value       REAL NOT NULL DEFAULT 0.0,
    property_count   INTEGER NOT NULL DEFAULT 0,
    insurance_policies INTEGER NOT NULL DEFAULT 0,
    total_premiums   REAL NOT NULL DEFAULT 0.0,
    guild_memberships INTEGER NOT NULL DEFAULT 0,
    total_guild_dues REAL NOT NULL DEFAULT 0.0,
    outstanding_liability REAL NOT NULL DEFAULT 0.0,
    outstanding_claims_owed REAL NOT NULL DEFAULT 0.0,
    lvt_due          REAL NOT NULL DEFAULT 0.0,
    lvt_paid_this_step REAL NOT NULL DEFAULT 0.0,
    net_worth        REAL NOT NULL DEFAULT 0.0,
    total_income_this_step REAL NOT NULL DEFAULT 0.0,
    total_expenses_this_step REAL NOT NULL DEFAULT 0.0,
    is_bankrupt      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (entity_id, step),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

-- Flow Matrix (per step)
CREATE TABLE flow_matrix (
    step             INTEGER NOT NULL,
    from_entity_type TEXT NOT NULL,
    to_entity_type   TEXT NOT NULL,
    mechanism        TEXT,                     -- NULL for aggregated total
    amount           REAL NOT NULL,
    PRIMARY KEY (step, from_entity_type, to_entity_type, mechanism)
);

-- Step Metrics (aggregate)
CREATE TABLE step_metrics (
    step                INTEGER PRIMARY KEY,
    total_lvt           REAL NOT NULL,
    total_dividend      REAL NOT NULL,
    total_premiums      REAL NOT NULL,
    total_claims        REAL NOT NULL,
    total_court_fees    REAL NOT NULL,
    total_court_awards  REAL NOT NULL,
    total_guild_dues    REAL NOT NULL,
    total_guild_benefits REAL NOT NULL,
    total_alliance_skim REAL NOT NULL,
    total_alliance_refund REAL NOT NULL,
    gini_wealth         REAL,
    gini_income         REAL,
    litigation_rate     REAL,
    court_backlog       REAL,
    premium_claim_ratio REAL,
    insurance_solvency  REAL,
    harberger_gap       REAL,
    bankruptcy_rate     REAL,
    migration_rate      REAL,
    insurance_hhi       REAL,
    land_concentration  REAL,
    dividend_income_ratio REAL,
    money_supply        REAL NOT NULL,
    money_creation      REAL NOT NULL DEFAULT 0.0,
    zero_sum_verified   INTEGER NOT NULL DEFAULT 0
);

-- Zero-Sum Validation Log
CREATE TABLE zero_sum_checks (
    check_id            TEXT PRIMARY KEY,
    step                INTEGER NOT NULL,
    layer               INTEGER NOT NULL,       -- 1=per-transfer, 2=step-end, 3=flow matrix, 4=reconciliation
    passed              INTEGER NOT NULL,
    expected_total      REAL,
    actual_total        REAL,
    discrepancy         REAL,
    details             TEXT,
    checked_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 10.2 Query Patterns

**Get balance history for a single agent:**
```sql
SELECT step, cash, net_worth, total_income_this_step, total_expenses_this_step
FROM balance_sheets
WHERE entity_id = 'CIT-0042'
ORDER BY step;
```

**Get flow matrix for a step:**
```sql
SELECT from_entity_type, to_entity_type, amount
FROM flow_matrix
WHERE step = 100 AND mechanism IS NULL
ORDER BY from_entity_type, to_entity_type;
```

**Trace a specific dollar (follow a transfer through the system):**
```sql
SELECT * FROM ledger_entries
WHERE transfer_id = 'abc-123-def'
ORDER BY entity_id;
```

**Check total money supply over time:**
```sql
SELECT step, money_supply
FROM step_metrics
ORDER BY step;
```

---

## 11. Error Handling & Edge Cases

### 11.1 Insufficient Balance During Transfer

| Scenario | Handling |
|----------|----------|
| **LVT delinquency** | If citizen has insufficient cash for LVT: record delinquency. Land goes into arrears. After N steps of arrears, land is forfeited (transferred to Trust, sold at auction). |
| **Premium non-payment** | Insurance policy lapses. Citizen becomes uninsured. |
| **Court award payment failure** | Defendant's assets are attached (cash first, then land via forced Harberger sale). If still insufficient, bankruptcy declared. |
| **Dividend payment failure** | Should never happen if order is correct (Trust collects LVT first). If it does, the Trust has an implementation bug — hard fail. |
| **Alliance spending > skim** | Alliance cannot spend more than its balance. Excess spending is queued or rejected (configurable). |

### 11.2 LVT Delinquency Detail

```python
def handle_lvt_delinquency(citizen_id, parcel_id, amount_due, step):
    """Handle a citizen who cannot pay LVT."""
    parcel = land_registry.get(parcel_id)
    
    # Check if citizen can pay from other sources
    if citizen.balance >= amount_due:
        citizen.pay_lvt()  # Normal path
        return
    
    # Delinquency
    arrears = lvt_registry.record_delinquency(citizen_id, parcel_id, amount_due, step)
    
    if arrears.steps_since_first_delinquency >= MAX_LVT_ARREARS_STEPS:
        # Forfeit land
        land_registry.transfer_ownership(parcel_id, from_=citizen_id, to_='TRUST-0001')
        # Trust sells at auction (future step)
        auction_queue.add(parcel_id, step)
```

### 11.3 Insurance Policy Lapse

```python
def handle_premium_non_payment(policy_id, step):
    """Handle a policyholder who cannot pay their premium."""
    policy = insurance_registry.get(policy_id)
    policy.lapse(step)  # Coverage ends; no future claims honored
    # Record the lapse in agent's history
    agent_narrative.append(f"Insurance policy {policy_id} lapsed at step {step}")
```

### 11.4 Insurer Insolvency

```python
def handle_insurer_insolvency(insurer_id, step):
    """Handle an insurer that cannot pay approved claims."""
    # 1. Flag insurer as insolvent
    insurer.insolvent = True
    
    # 2. Unpaid claims go to claims guaranty fund (if exists) or remain unpaid
    for unpaid_claim in insurer.unpaid_claims:
        # If reinsurance exists, try reinsurer first
        if unpaid_claim.is_ceded:
            try_reinsurance_recovery(unpaid_claim)
        else:
            # Claim remains unpaid; policyholder absorbs loss
            agent_narrative.append(f"Insurer {insurer_id} failed; claim {unpaid_claim.id} unpaid")
    
    # 3. Trigger market response: remaining insurers raise premiums
    for other_insurer in active_insurers:
        other_insurer.adjust_premiums(insolvency_event=True)
```

### 11.5 Court Award Collection Failure

```python
def handle_award_collection(defendant_id, plaintiff_id, award_amount, case_id, step):
    """Attempt to collect a court award from the defendant."""
    if entity_registry.get(defendant_id).balance >= award_amount:
        # Normal path: direct payment
        ledger.transfer(defendant_id, plaintiff_id, award_amount, 'court_award', 
                       reference_id=case_id)
        return
    
    # Insufficient cash: attach assets
    # 1. Attach cash (all of it)
    available_cash = entity_registry.get(defendant_id).balance
    if available_cash > 0:
        ledger.transfer(defendant_id, plaintiff_id, available_cash, 'court_award_partial',
                       reference_id=case_id)
        award_amount -= available_cash
    
    # 2. Force Harberger sale of land parcels until award is covered
    for parcel in land_registry.parcels_owned_by(defendant_id):
        if award_amount <= 0:
            break
        sale_price = min(parcel.declared_value, award_amount)
        # Force sale (buyer = plaintiff, or auction)
        ledger.transfer(plaintiff_id, defendant_id, sale_price, 'harberger_forced_sale',
                       reference_id=parcel.id)
        land_registry.transfer_ownership(parcel.id, from_=defendant_id, to_=plaintiff_id)
        award_amount -= sale_price
    
    # 3. If still insufficient: declare bankruptcy
    if award_amount > 0:
        declare_bankruptcy(defendant_id, step)
        # Remaining amount is written off (recorded as bad debt)
        ledger.write_off(award_amount, mechanism='bad_debt_write_off')
```

### 11.6 Floating Point Precision

All monetary values are stored as `REAL` (float64). Comparisons use relative tolerance:

```python
EPSILON = 1e-9

def approx_equal(a, b):
    return abs(a - b) < EPSILON

def approx_zero(a):
    return abs(a) < EPSILON
```

For Phase 1+, consider migrating to `Decimal` with 2 decimal places for currency-level precision.

### 11.7 Race Conditions / Concurrent Transfers

Since the simulation is single-threaded and sequential within each step, there are no race conditions. The execution order in §9.1 guarantees deterministic ordering.

---

## 12. Testing & Validation Strategy

### 12.1 Unit Tests

| Test | What it verifies | Priority |
|------|-----------------|----------|
| `test_single_transfer()` | Transfer between two entities maintains zero-sum | P0 |
| `test_chain_transfers()` | A→B→C: net zero-sum preserved across chain | P0 |
| `test_round_trip()` | A→B→A: net zero | P0 |
| `test_insufficient_balance()` | Transfer raises error on insufficient funds | P0 |
| `test_lvt_collection()` | LVT moves from citizen to Trust, amounts correct | P0 |
| `test_dividend_distribution()` | Dividend distributed equally, total matches LVT - skim | P0 |
| `test_alliance_loop()` | LVT → Trust → skim → Alliance → refund → compact | P0 |
| `test_insurance_cycle()` | Premium → pool → claim payout; net zero-sum | P0 |
| `test_court_cycle()` | Filing fee → adjudication → award; net zero-sum | P0 |
| `test_guild_cycle()` | Dues → mutual pool → benefits; net zero-sum | P0 |
| `test_flow_matrix_aggregation()` | Flow matrix sums match ledger totals | P0 |
| `test_balance_sheet_consistency()` | Balance sheet `cash` field matches ledger balance | P0 |
| `test_gini_computation()` | Gini coefficient calculated correctly for known distributions | P1 |
| `test_lvt_delinquency()` | Delinquency → arrears → forfeiture flow works | P1 |
| `test_insurer_insolvency()` | Insolvency triggers proper claim handling | P1 |
| `test_bankruptcy_cascade()` | Multiple defaults handled correctly | P2 |

### 12.2 Integration Tests

| Test | What it verifies |
|------|-----------------|
| `test_full_step_execution()` | Run one complete step with all mechanics. Verify all invariants. |
| `test_multi_step_execution()` | Run 10 steps. Verify money supply constant across all steps. |
| `test_empty_step()` | Step with no events, no agents acting. Verify balances unchanged. |
| `test_fuzz_transfers()` | Random transfers between random entities. Verify zero-sum after each. |
| `test_deterministic_replay()` | Same seed + same agent decisions → identical ledger state. |

### 12.3 Invariant Test Harness

```python
def run_invariant_suite(engine: LedgerEngine, step: int):
    """Run all invariant checks and return pass/fail with details."""
    results = {}
    
    # Layer 1: Per-transfer (already checked during execution)
    # Layer 2: Step-end total
    try:
        engine.validate_step_invariant(step)
        results['layer_2_step_total'] = True
    except AssertionError as e:
        results['layer_2_step_total'] = False
        results['layer_2_error'] = str(e)
    
    # Layer 3: Flow matrix
    matrix = build_flow_matrix(engine.get_entries_for_step(step))
    try:
        validate_flow_matrix(matrix, engine.get_entries_for_step(step))
        results['layer_3_flow_matrix'] = True
    except AssertionError as e:
        results['layer_3_flow_matrix'] = False
        results['layer_3_error'] = str(e)
    
    # Layer 4: Reconciliation
    try:
        engine.reconcile_from_transaction_log(step)
        results['layer_4_reconciliation'] = True
    except AssertionError as e:
        results['layer_4_reconciliation'] = False
        results['layer_4_error'] = str(e)
    
    return results
```

### 12.4 Validation Scenarios (Phase 0)

Before moving to Phase 1, the following must all pass:

1. **Scenario A — Minimal:** 1 citizen, 1 Trust, 1 Alliance, 1 compact. 1 parcel. Run 5 steps. Verify: LVT collected → Trust skim → Alliance refund → Dividend → all balances correct → zero-sum holds every step.

2. **Scenario B — Insurance:** 10 citizens, 2 insurers, 1 Trust, 1 Alliance, 1 compact. Citizens buy insurance. Inject claims at known rate. Run 20 steps. Verify: Premiums in → claims out → insurer profit/loss → zero-sum holds.

3. **Scenario C — Court:** 5 citizens, 1 court, 1 Trust, 1 Alliance, 1 compact. File cases, adjudicate, enforce awards. Run 10 steps. Verify: Fees collected → adjudication → award transferred → zero-sum holds.

4. **Scenario D — Full:** 20 citizens, 2 insurers, 2 courts, 2 guilds, 1 Trust, 1 Alliance, 2 compacts. Run 50 steps. Verify ALL invariants at every step.

---

## Appendix A: Decision Gate Log

### Gate 1: Centralized vs. Distributed Ledger Architecture

**Context:** Foundational design choice for the money tracking system.

**Fork:**
- **Option A:** Centralized LedgerEngine — single authoritative source, per-transfer zero-sum enforcement.
- **Option B:** Distributed per-agent ledgers with global event ordering and reconciliation.

**Proposal:** Option A (Centralized LedgerEngine).

**Critic concerns:**
1. "Single point of failure for bug detection" — addressed by Layer 4 (reconciliation pass from raw logs).
2. "Less auditable without independent verification" — addressed by dual-entry with transfer_id linking.
3. "Step-based freezing is artificial" — accepted trade-off for deterministic replay; snapshots are principled for financial settlement modeling.

**Decision:** Option A, with defensive reconciliation pass (Layer 4) added as a concession.

### Gate 2: Flow Matrix vs. Individual Transfer Logs

**Context:** How to represent inter-component money flows.

**Fork:**
- **Option A:** Materialize flow matrix at step end from individual transfers.
- **Option B:** Maintain a running flow matrix accumulator, updated per transfer.

**Proposal:** Option A (materialize at step end).

**Rationale:** Option B adds complexity to every transfer call. Materialization from the transaction log is O(n) in transfers per step and provides a cleaner separation of concerns. The materialization can be optimized with caching if performance is an issue.

**Decision:** Option A, with caching of last-computed matrix for read queries.

### Gate 3: Balance Sheet Computation

**Context:** When and how to compute per-agent balance sheets.

**Fork:**
- **Option A:** Compute balance sheets live from the ledger engine on every query.
- **Option B:** Compute and cache balance sheets at step end.

**Proposal:** Option B (compute and cache at step end).

**Rationale:** Balance sheets are read far more often than they change (agents query their state each step, metrics need them). Computing at step end and caching for the duration of the step avoids redundant computation. Step-end computation also ensures consistency — all balance sheets reflect the same moment in time.

**Decision:** Option B, with a `get_latest_balance_sheet(entity_id)` that returns the most recent cached version.

---

## Appendix B: Deviation Log

| Date | Deviation | Reason | Author |
|------|-----------|--------|--------|
| — | — | — | — |

*(No deviations logged yet — this is the initial specification.)*

---

## Appendix C: Glossary

| Term | Definition |
|------|-----------|
| **Dual entry** | Each transfer produces two ledger entries (debit sender, credit receiver) linked by a `transfer_id`. |
| **Flow matrix** | 2D array of total dollars moved between entity types per step. |
| **Zero-sum invariant** | The property that total money in the system remains constant across all transfers. |
| **Balance sheet** | Snapshot of an entity's financial position at a point in time. |
| **Materialized view** | A derived data structure that is computed and cached, rather than queried live. |
| **Mechanism** | A named cause of a money flow (e.g., `lvt`, `premium`, `claim`). |
| **Sub-step** | A numbered phase within a simulation step (1–10), defining execution order. |
| **Reconciliation** | Independent re-derivation of total money supply from raw transaction logs to catch engine bugs. |
| **Delinquency** | Failure to pay LVT when due, leading to arrears and eventual forfeiture. |
| **Insolvency** | An insurer's inability to pay approved claims from available reserves. |
| **Bankruptcy** | An entity's net worth falling below zero (or inability to pay court-ordered awards). |
