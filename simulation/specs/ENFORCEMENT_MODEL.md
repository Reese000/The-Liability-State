# Enforcement & Detection Model Specification

## Design Philosophy

The Liability State has **no police, no regulators, no compliance inspectors**. Violations are only detected through the self-interested actions of:

- **Counterparties** — harmed by a breach, have direct knowledge and incentive
- **Victims** — experienced harm, may investigate cause
- **Insurers** — financial interest in preventing fraud and misrepresentation
- **Auditors** — hired by insurers, courts, or guilds to verify compliance
- **Whistleblowers** — insiders or bystanders with private knowledge
- **Competitors** — harmed by unfair advantage from violations

This specification defines a **Detection Probability Model** (Section 1), a **Litigation Pipeline** (Section 2), **Consequences** (Section 3), and **Per-Violation Enforcement Flows** (Section 4). The system provides **channels** (court system, reputation market, blacklist registries) and **baseline probabilities**; it does not prescribe detection effort. Each actor independently decides whether to investigate based on expected value.

---

## 1. Detection Probability Model

### 1.1 Core Principle

Every violation has a **base detection probability** (`P_base`) — the chance per step that at least one eligible observer notices the violation **if they choose to look**. The actual detection probability for a specific actor depends on:

1. **Their role** relative to the violation (victim, counterparty, insurer, auditor, whistleblower)
2. **Their investment** in detection (auditing frequency, forensic tools, monitoring)
3. **The violation's characteristics** (visibility, magnitude, concealment, sophistication)
4. **The transaction context** (on-ledger vs off-ledger, number of parties, jurisdiction)

### 1.2 Base Detection Probability Table

Each violation type has a base probability per step that it is detected by **someone** (assuming at least one eligible observer exists and chooses to look):

| Violation Type | `P_base` | Primary Detector(s) | Justification |
|---|---|---|---|
| Insurance fraud (fake claim) | 0.35 | Insurer | Claims investigation is standard; insurers have strong incentive |
| Premium evasion (under-reporting risk) | 0.20 | Insurer, Actuarial Commons | Requires statistical analysis; hard to spot per-transaction |
| Harberger under-declaration | 0.50 | Any buyer | Self-enforcing — anyone can force a sale at declared price |
| Contract breach | 0.80 | Counterparty | Counterparty knows immediately they didn't receive what was promised |
| Pollution / externalized harm | 0.40 | Victim, victim's insurer | Victim experiences harm; may not immediately know cause |
| Guild certification fraud | 0.30 | Guild, customers | Shoddy work eventually noticed; guild may audit |
| Court corruption | 0.10 | Litigants, other courts | Hard to detect; requires pattern analysis across many cases |
| Collusion / price fixing | 0.15 | Competitors, customers | Above-market pricing visible but hard to prove collusion |
| Glass Box violation (hiding data) | 0.25 | Any citizen, Actuarial Commons | Missing data can be noticed by anyone who tries to replicate |
| Operating without insurance | 0.40 | Insurers, courts, counterparties | Proof of coverage is standard; non-compliance quickly visible |
| Insider trading (compact-level) | 0.15 | Competitors, whistleblowers | Hard to detect without insider leak |
| Double-pledging collateral | 0.30 | Insurers, creditors | Audits of collateral registries reveal conflicts |
| Fraudulent guild certification | 0.25 | Guild, customers, other guilds | Shoddy work or test cheating eventually surfaces |
| Evasion of court judgment | 0.35 | Plaintiff, court registry | Non-payment is directly observable by the owed party |
| Breach of fiduciary duty | 0.20 | Beneficiaries, co-fiduciaries | Requires audit of agent's decisions |
| Market manipulation | 0.15 | Competitors, exchange monitor | Suspicious patterns visible but hard to attribute |
| Harberger gaming (coordinated under-declaration) | 0.35 | Any buyer, tax authority | Side deals leave traces; forced-sale right creates natural check |
| Court flooding (frivolous suits) | 0.20 | Court, defendants, insurers | Pattern of filings visible to court administration; defendants can petition for sanctions |
| Guild rent-seeking (membership restriction) | 0.25 | Non-member workers, competing guilds, customers | Restricted supply → higher prices → visible market signal |
| LVT evasion (under-declare, compact arbitrage) | 0.20 | National Trust, compact tax authority, Harberger buyers | Under-declaration self-enforcing via forced sale; arbitrage leaves migration trail |
| Asset flight (hiding assets from judgments) | 0.15 | Judgment creditors, court registries, insurers | Requires cross-jurisdictional tracking; hard to detect but large targets get scrutiny |

### 1.3 Modifier Factors

`P_effective = clamp(P_base × factor_visibility × factor_magnitude × factor_concealment × factor_parties × factor_auditing × factor_jurisdiction, 0.0, 1.0)`

#### Factor: Transaction Visibility (`0.2x – 1.5x`)

| Level | Description | Multiplier |
|---|---|---|
| **Fully transparent** | On-ledger, Glass Box compliant, public record | 1.5× |
| **Standard** | Normal market transaction, some records exist | 1.0× |
| **Opaque** | Off-ledger, private contract, no public record | 0.5× |
| **Hidden** | Shell companies, encrypted channels, cut-out intermediaries | 0.2× |

#### Factor: Violation Magnitude (`0.5x – 2.0x`)

| Level | Description | Multiplier |
|---|---|---|
| **Massive** | Threatens solvency of counterparty or system-wide | 2.0× |
| **Large** | >10× typical transaction size | 1.5× |
| **Medium** | 2× – 10× typical | 1.0× |
| **Small** | Normal transaction range | 0.75× |
| **Micro** | Below typical floor | 0.5× |

#### Factor: Concealment Investment (`0.1x – 1.0x`)

Agent expenditure on concealment reduces detection. Each dollar spent (one-time per violation) applies:

| Investment Level | Cost (relative to gain) | Multiplier |
|---|---|---|
| **None** | — | 1.0× |
| **Basic** | 5% of expected gain | 0.7× |
| **Moderate** | 15% of expected gain | 0.4× |
| **Sophisticated** | 30% of expected gain | 0.2× |
| **Extreme** | 50%+ of expected gain | 0.1× |

Concealment methods include: off-ledger payments, shell company chains, encrypted communications, fake identities, complex contract structures, bribery of auditors.

#### Factor: Number of Parties Aware (`0.6x – 1.8x`)

| Parties with knowledge | Multiplier |
|---|---|
| 1 (only violator) | 0.6× |
| 2 (violator + 1 counterparty) | 1.0× |
| 3–5 | 1.2× |
| 6–10 | 1.5× |
| 10+ | 1.8× |

#### Factor: Auditing Frequency (`0.5x – 3.0x`)

Depends on whether the relevant oversight body (insurer, guild, court, compact) performs regular audits:

| Auditing Regime | Multiplier |
|---|---|
| Continuous real-time audit | 3.0× |
| Regular (monthly/quarterly) | 2.0× |
| Annual audit | 1.5× |
| Random / sporadic | 1.0× |
| No auditing | 0.5× |

#### Factor: Jurisdiction Enforcement Quality (`0.3x – 1.5x`)

Compacts may have different record-keeping, court quality, or social norms:

| Compact Enforcement Level | Multiplier |
|---|---|
| High (strong Glass Box norms, efficient courts) | 1.5× |
| Standard | 1.0× |
| Weak (limited auditing, corrupt courts) | 0.6× |
| Failed (no functioning enforcement channels) | 0.3× |

### 1.4 Actor-Specific Detection Rolls

When a violation occurs, each **eligible observer** (based on role) makes an independent detection roll each step. The model:

1. Determine which actor types could detect this violation type (see Section 1.2)
2. For each eligible actor, calculate `P_effective` using their specific modifiers
3. Roll independently per actor
4. If multiple actors detect, the **first successful detector** gets priority in litigation (but others may still be witnesses)

Actors may **choose not to look** (invest zero in detection) for a given violation if the expected return doesn't justify the cost. Detection only occurs if the actor:

- **Is directly affected** (victim, counterparty): automatic visibility of the harm
- **Has a monitoring contract** (insurer auditing a policyholder, guild auditing a member): checks at defined intervals
- **Invests in general surveillance** (whistleblower, competitor intelligence): optional, costs resources each step
- **Stumbles upon evidence** (bystander, journalist): low base probability, can be increased by investment

### 1.5 Detection Delay

Detection is not instantaneous. The step at which detection occurs depends on:

| Detection Path | Typical Delay (steps) |
|---|---|
| Counterparty (direct harm) | 0 (same step) |
| Victim experiences harm | 0–1 |
| Insurer claims investigation | 1–3 |
| Auditor (scheduled) | Next audit cycle |
| Whistleblower comes forward | 1–5 |
| Statistical outlier detection | 2–10 |
| Pattern analysis (collusion, corruption) | 5–20 |

Delay is modeled as: `P_detect_this_step = P_effective × γ^delay_factor` where `γ = 0.7` (probability drops each step the violation remains undetected, as the trail goes cold — but some violations become *more* detectable over time as patterns accumulate, in which case `γ > 1.0` for pattern-based detection).

---

## 2. Litigation Pipeline

Once a violation is detected, the detecting actor must **choose to act**. Litigation is voluntary, costly, and uncertain.

```
Detection
    │
    ▼
[Gate 1: Decision to Act]
    ├─ File court case (pays filing fee)
    ├─ Report to insurer / guild (internal action)
    ├─ Public accusation (reputation attack)
    ├─ Negotiate private settlement
    └─ Do nothing (too costly, fear of retaliation, etc.)
    │
    ▼ (if court case filed)
[Gate 2: Standing & Jurisdiction]
    ├─ Does plaintiff have legal standing?
    ├─ Is this the correct court?
    ├─ Is the case within statute of limitations?
    └─ Court accepts or dismisses
    │
    ▼ (if accepted)
[Gate 3: Evidence Evaluation]
    ├─ Plaintiff presents evidence (strength = combined detection factors)
    ├─ Defendant presents counter-evidence (denial, justification, alibi)
    ├─ Court appoints expert auditor (optional, costs both parties)
    └─ Evidence score computed: 0.0 (none) to 1.0 (conclusive)
    │
    ▼ (if evidence threshold met)
[Gate 4: Adjudication]
    ├─ Was there harm? (yes/no)
    ├─ Was defendant liable? (standard of care, foreseeability, causation)
    ├─ Comparative negligence? (plaintiff contributed to harm?)
    └─ Verdict: Dismissal | Defendant liable | Plaintiff liable (counter-suit)
    │
    ▼ (if liability found)
[Gate 5: Damages Calculation]
    ├─ Compensatory damages (actual harm)
    ├─ Punitive damages (if willful, malicious, or reckless)
    ├─ Legal costs (loser pays or each pays own, per contract)
    └─ Insurance applies? (insurer pays up to coverage limit)
    │
    ▼ (if damages awarded)
[Gate 6: Enforcement]
    ├─ Defendant pays voluntarily
    ├─ Court seizes assets (bank account, property via Harberger forced sale)
    ├─ Insurer pays on defendant's behalf
    ├─ Payment plan ordered (if cannot pay immediately)
    └─ Default → reputation blacklisting, further penalties
    │
    ▼ (optional)
[Gate 7: Appeals]
    ├─ Appeal to higher court (if exists)
    ├─ Grounds: procedural error, new evidence, bias
    ├─ Higher court reviews (lower probability of reversal unless clear error)
    └─ Final judgment
```

### 2.1 Decision to Act (Gate 1)

The detector calculates expected value of litigation:

```
EV_lawsuit = P_win × award - P_lose × (defendant_costs + reputation_damage)
             - filing_fee - evidence_cost - time_cost
```

They file suit only if `EV_lawsuit > 0` **and** `EV_lawsuit > EV_private_settlement`.

Factors that influence the decision:

| Factor | Effect |
|---|---|
| **Evidence strength** | Higher strength → higher `P_win` → more likely to sue |
| **Defendant's wealth** | Deeper pockets → higher potential award → more likely to sue |
| **Plaintiff's wealth** | Rich plaintiff can afford litigation costs; poor may not |
| **Insurance coverage** (plaintiff) | Legal expense insurance → more likely to sue (costs covered) |
| **Insurance coverage** (defendant) | Insured defendant → higher chance of actual payout → more likely to sue |
| **Court reputation** | Fair, fast court → more likely to file; biased, slow court → less likely |
| **Relationship** | Ongoing business relationship → prefer settlement over adversarial litigation |
| **Retaliation risk** | Fear of counter-suit or violence → less likely to sue |
| **Reputation effect** | Being seen as litigious → less likely for small claims; being seen as weak → more likely to defend rights |

### 2.2 Standing & Jurisdiction (Gate 2)

**Standing** requires:
1. The plaintiff suffered **actual harm** (or represents someone who did)
2. The harm is **traceable** to the defendant's action
3. The court can **redress** the harm through a judgment

**Jurisdiction** depends on:
- Where the violation occurred
- Where the defendant resides/operates
- Where the contract was formed
- Where the harm was suffered

Courts may compete for cases (forum shopping is allowed), but a case cannot be filed in multiple courts simultaneously.

**Statute of limitations:**
- Contract breach: 10 steps
- Tort / externalized harm: 20 steps
- Fraud: 30 steps (or discovery + 5 steps)
- Property claims: no limit (land title is perpetual)
- No statute for systematic concealment (clock starts when discovered)

### 2.3 Evidence Evaluation (Gate 3)

Evidence strength is computed from:

```
evidence_strength = clamp(
    0.3 × detection_factors_combined     # How the violation was detected
    + 0.3 × documentation_quality         # Records, contracts, ledgers
    + 0.2 × witness_credibility           # Number and reliability of witnesses
    + 0.2 × forensic_investment,          # Expert reports, audits, data analysis
    0.0, 1.0
)
```

**Detection factors combined** = the `P_effective` from Section 1.3, normalized: if the violation was detected with high probability factors, the evidence is stronger.

**Documentation quality** depends on:
- Glass Box compliance (automated records = high quality)
- Contract written vs. verbal (written = stronger)
- Ledger entries, emails, messages, logs

**Witness credibility** depends on:
- Number of independent witnesses
- Their reputation (credible actors = higher weight)
- Conflicts of interest (reduces credibility)

**Forensic investment** depends on:
- Whether plaintiff hired an auditor or expert
- Quality/independence of the forensic examiner
- Time elapsed since violation (older = weaker forensics)

**Evidence threshold**: `evidence_strength >= 0.2` to proceed. Below this, the case is dismissed for lack of evidence. The plaintiff may withdraw before judgment to avoid adverse costs.

### 2.4 Adjudication (Gate 4)

The court determines liability using a **reasonableness standard**:

```
P_liable = clamp(
    0.4 × evidence_strength
    + 0.3 × (1 - defendant_due_care)     # Did defendant take reasonable precautions?
    + 0.2 × foreseeability                # Could defendant have foreseen harm?
    + 0.1 × precedent_weight              # How similar cases were decided
    - 0.2 × comparative_negligence,       # Was plaintiff partly at fault?
    0.0, 1.0
)
```

**Defendant due care** (0-1): Did the defendant invest in precautions proportional to the risk? Higher = less liable.

**Foreseeability** (0-1): Was the harm a foreseeable consequence of the action? Higher = more liable.

**Precedent weight** (0-1): Have similar cases resulted in liability? Depends on court's respect for precedent.

**Comparative negligence** (0-1): Was the plaintiff contributorily negligent? Higher = reduces defendant's liability proportionally.

**Court bias** (configurable per court): Some courts may be pro-plaintiff (+0.1 to `P_liable`) or pro-defendant (-0.1). Courts that are too biased lose reputation as litigants migrate away.

Verdict is determined by comparing `P_liable` against a threshold:
- `P_liable < 0.3` → Defendant wins (dismissal)
- `0.3 <= P_liable < 0.6` → Split/compromise verdict (court may award partial damages)
- `P_liable >= 0.6` → Plaintiff wins

### 2.5 Damages Calculation (Gate 5)

**Compensatory damages** = `actual_harm + consequential_losses - plaintiff_mitigation_effort`

Where:
- `actual_harm` = verifiable financial loss
- `consequential_losses` = downstream effects (lost business, medical costs, repair costs)
- `plaintiff_mitigation_effort` = plaintiff's duty to minimize damages (if plaintiff could have prevented further harm but didn't, damages reduced)

**Punitive damages** (only if violation was willful or reckless):
- Multiplier on compensatory: `1×` (standard) to `3×` (willful)
- Multiplier higher for concealment, fraud, repeat offenses

**Legal costs**: Default = each party pays own costs. Contract may specify "loser pays." If loser pays and plaintiff loses, plaintiff pays defendant's costs.

**Insurance application**:
- If defendant has liability insurance, insurer pays up to coverage limit
- If damages exceed coverage, defendant pays remainder
- If defendant is judgment-proof (cannot pay), plaintiff may recover nothing
- If defendant is uninsured in a domain where insurance is mandatory, defendant bears full personal liability and may face additional penalties

### 2.6 Enforcement (Gate 6)

If defendant does not pay voluntarily:

| Enforcement Mechanism | How it works | Success probability |
|---|---|---|
| **Voluntary payment** | Defendant pays within grace period (3 steps) | Higher for reputable actors, insured defendants |
| **Asset seizure** | Court orders bank/locker to transfer funds | 0.8 if defendant has liquid assets |
| **Harberger forced sale** | Court seizes land, sells at declared value | 0.9 if land held, value may be below damages |
| **Wage garnishment** | Percentage of labor income diverted | 0.6, limited to % of income |
| **Garnishment of insurance payouts** | Claims owed to defendant diverted | 0.7, if claim exists |
| **Payment plan** | Structured payments over time | 0.5 completion rate |
| **Default → blacklist** | Added to public non-payment registry | 0.0 financial recovery, but reputational penalty |

**Priority of claims**: If multiple creditors, court claims are senior. Then secured creditors, then unsecured.

### 2.7 Appeals (Gate 7)

**Grounds for appeal:**
1. Procedural error (court made a legal mistake)
2. New material evidence discovered
3. Bias or corruption of the judge
4. Damages calculation error

**Appeal procedure:**
- Must be filed within 5 steps of judgment
- Higher court reviews the record (no new trial unless new evidence)
- `P_reversal` = 0.2 to 0.4 depending on grounds
- Filing an appeal may require posting a bond (to prevent frivolous appeals)
- If appeal fails, appellant pays appellee's costs

**Supreme / Constitutional court** (if one exists for the compact):
- Only hears cases on important legal questions
- Lower `P_reversal` (0.1–0.2) but rulings set precedent

---

## 3. Consequences

### 3.1 Financial Consequences

| Consequence | Mechanism | Magnitude |
|---|---|---|
| **Compensatory damages** | Court award | Actual harm (variable) |
| **Punitive damages** | Court award | 1×–3× compensatory |
| **Legal costs** | If loser pays | Filing fee + evidence costs + lawyer costs |
| **Back premiums** | Insurer recalculates | Premium difference × duration under-reported |
| **Penalty for evasion** | Insurer or court | 20%–100% of back premiums |
| **Filing fee** | Paid to court | Fixed (configurable, typically 1%–5% of claim) |
| **Pre-judgment interest** | Court adds | Interest on damages from violation date |
| **Post-judgment interest** | Court adds | Interest on unpaid damages from judgment date |

### 3.2 Insurance Consequences

| Consequence | Mechanism | Persistence |
|---|---|---|
| **Premium increase** | Insurer recalculates risk profile | Next policy period or longer |
| **Deductible increase** | Insurer adjusts policy terms | Next policy period |
| **Coverage reduction** | Insurer excludes certain risks | Future policies |
| **Policy cancellation** | Insurer terminates coverage | Immediate; may be contested |
| **Blacklisting** | Added to shared insurer blacklist | 20–100 steps (configurable) |
| **Refusal to insure** | No insurer will offer policy | Until blacklist expires or conditions met |
| **Higher collateral requirements** | Insurer demands surety bond | Ongoing while unrated |

**Premium adjustment formula:**

```
new_premium = base_premium × (1 + violation_penalty_multiplier × severity)
```

Where `violation_penalty_multiplier` is per violation type:
- Insurance fraud: 2.0 (premium doubles)
- Premium evasion: 1.5
- Contract breach: 1.2
- Pollution/externalized harm: 1.4
- Court judgment unpaid: 1.8
- Operating without insurance: 2.5

And `severity` is 0.0–1.0 (damages relative to agent net worth).

### 3.3 Reputation Consequences

| Consequence | Mechanism | Effect |
|---|---|---|
| **Reputation score decrease** | Public record of violations and judgments | Affects all future interactions |
| **Trust penalty** | Counterparties less willing to contract | Higher collateral demands, shorter contract terms |
| **Social exclusion** | Guilds may expel, community may ostracize | Loss of guild benefits, mutual aid |
| **Shaming** | Public registry of bad actors | Psychological cost (modeled as disutility) |
| **Loss of standing** | Cannot serve on juries, hold certain positions | Reduced civic participation |

**Reputation score formula:**

```
reputation_score = base_reputation
    - Σ (violation_severity_i × violation_reputation_penalty_i)
    + positive_actions (timely payments, community service, etc.)
```

Range: 0.0 (pariah) to 1.0 (saint). Default: 0.5 (average).

**Effect on interactions:**

| Reputation Band | Effect |
|---|---|
| 0.0–0.2 (Pariah) | Cannot get insurance, no contracts without full prepayment, guilds expel, courts view unfavorably |
| 0.2–0.4 (Poor) | Premiums +50%, must post collateral for contracts, limited guild options |
| 0.4–0.6 (Average) | Standard terms |
| 0.6–0.8 (Good) | Premiums -10%, preferred contracting terms |
| 0.8–1.0 (Excellent) | Premiums -20%, automatic trust, expedited court processing |

### 3.4 Blacklisting

**Types of blacklists:**

| Blacklist | Maintained by | Purpose | Duration |
|---|---|---|---|
| **Insurance Blacklist** | Shared among insurers (via Actuarial Commons) | Track fraudsters, evaders, and high-risk actors | 20–100 steps |
| **Court Judgment Blacklist** | Court registries (shared between compacts) | Track non-paying judgment debtors | Until debt paid + 10 steps |
| **Guild Expulsion Registry** | Guilds (shared if cross-guild agreement) | Track expelled members, certification fraud | 50–200 steps |
| **Compact Blacklist** | Compact government | Track those who evade LVT, commit treason | Permanent (or compact decision) |

**Adding to blacklist:**
- Requires a court judgment (for court/debt blacklists)
- Requires insurer finding (for insurance blacklist, with evidence)
- Can be contested in court (wrongful blacklisting is a tort)

**Effects of blacklisting:**
- Insurance: no policy offered by any participating insurer
- Court: cannot file new cases until debt resolved
- Guild: cannot join or be certified by any participating guild
- Compact: may be excluded from certain benefits, subject to higher LVT

**Removal from blacklist:**
- Pay the debt in full (court blacklist)
- Wait out the duration (insurance blacklist)
- Successful appeal proving wrongful listing
- Expungement by the maintaining body (rare, requires supermajority)

---

## 4. Per-Violation Enforcement Flows

### 4.1 Insurance Fraud (Fake Claim)

**Who detects:** Insurer (claims adjuster)

**Detection mechanics:**
1. Claim filed
2. Insurer compares claim to policyholder's declared risk profile
3. `P_detect` = 0.35 × visibility_modifier (claim is documented) × magnitude_modifier × concealment_modifier × auditing_modifier
4. If detected → fraud investigation (may involve auditor or forensic accountant)
5. Evidence collected: claim documents, policy history, interview records

**Litigation flow (if insurer chooses to act):**
1. Insurer denies the claim
2. Insurer may file a court case against policyholder for fraud
3. If insurer wins → damages = claim amount + investigation costs + punitive
4. If policyholder wins → insurer must pay claim + costs

**Consequences:**
- Claim denied (immediate)
- Policy cancelled
- Insurance blacklist (50 steps)
- Reputation decrease: -0.3
- Court judgment for damages (if litigated)
- Future premiums: 2× base

**Notes:**
- Policyholder may also face criminal-style penalties in some compacts (treated as additional damages in LS)
- Small frauds (< threshold) may be handled internally without court
- Repeat fraud → higher `P_detect` (insurer flags account)

### 4.2 Premium Evasion (Under-Reporting Risk)

**Who detects:** Insurer, Actuarial Commons (statistical outlier), competitor

**Detection mechanics:**
1. Policyholder declares risk profile (e.g., low-risk occupation, safe neighborhood)
2. Insurer pools all policyholders' declared vs actual claims experience
3. `P_detect` per step = 0.20 × visibility_modifier (declared risk is on record) × magnitude_modifier × concealment_modifier × auditing_modifier
4. Detection trigger: policyholder's claims significantly exceed actuarial prediction for declared risk
5. Actuarial Commons may flag agent if aggregated data shows anomalous claims across insurers

**Litigation flow:**
1. Insurer audits policyholder (may send auditor, request documents)
2. If evasion confirmed → recalculate premiums for entire policy period
3. Demand back premiums + penalty
4. If policyholder refuses → court case for breach of insurance contract

**Consequences:**
- Back premiums owed (full amount evaded)
- Penalty: 50% of back premiums
- Premium increase: 1.5× base for next period
- If intentional fraud (not just error) → insurance blacklist (30 steps)
- Reputation decrease: -0.15
- Liability: losses caused by under-insurance not covered

**Notes:**
- Honest mistake vs intentional fraud: insurer determines based on pattern
- Self-reporting (correcting declaration before detection) reduces penalty to 10%
- Companies evading premium on behalf of employees face higher penalties

### 4.3 Harberger Under-Declaration

**Who detects:** Any buyer

**Detection mechanics:**
1. Owner declares land value V
2. Any buyer can post a bond for V and force a purchase
3. Self-enforcing: no detection roll needed if buyer exists
4. `P_detect` per step = 0.50 (any buyer may notice undervaluation)

**Litigation flow:**
1. Buyer posts bond equal to declared value
2. 14-day free refusal window: owner can refuse at no cost (but tax basis rises)
3. Day 15–90: owner may still refuse but pays 15% penalty
4. If owner accepts → sale proceeds at declared value
5. If owner refuses and pays penalty → property retained, tax basis adjusted
6. Collusion between owner and buyer (side payment + forced sale to true value) is separately detectable

**Consequences:**
- If forced sale: property lost at below-market price
- If refusal: 15% penalty + tax basis increases
- Collusion detected: both parties liable for Harberger manipulation (see separate flow)

**Notes:**
- Under-declaration is the most self-correcting violation in the LS
- The mechanism incentivizes owners to declare at or near true value
- Collusion is hard but possible (requires side payment in opaque channel)

### 4.4 Contract Breach

**Who detects:** Counterparty

**Detection mechanics:**
1. Counterparty expected delivery/payment/performance
2. Did not receive it → immediate knowledge
3. `P_detect` = 0.80 (counterparty knows instantly)
4. No concealment possible (counterparty directly experiences non-performance)

**Litigation flow:**
1. Counterparty calculates: is breach material enough to sue?
2. If yes → file at court with jurisdiction (per contract)
3. Evidence: the contract itself + proof of non-delivery
4. Court determines: was there a valid contract? Was it breached? Were there force majeure or other defenses?
5. Damages: expectation damages (what counterparty would have received) or reliance damages (costs incurred), whichever is greater

**Consequences:**
- Court award: expectation damages
- Legal costs (may be awarded to winner if contract specifies)
- Reputation decrease: -0.1 to -0.3 (depends on severity)
- If intentional breach (opportunistic): punitive damages up to 2×
- If breach due to insolvency: treated as bankruptcy, not fraud

**Notes:**
- Minor breaches may be handled by renegotiation or arbitration
- Liquidated damages clause in contract sets pre-agreed amount
- Force majeure defense available for events outside defendant's control
- Breach due to concealment (deliberate signing with no intent to perform) is fraud, not simple breach

### 4.5 Pollution / Externalized Harm

**Who detects:** Victim, victim's insurer, bystander, community

**Detection mechanics:**
1. Victim experiences harm (illness, property damage, nuisance)
2. Victim may not immediately know cause → investigation step
3. `P_detect` = 0.40 × visibility_modifier (visible pollution = high, invisible toxins = low) × magnitude_modifier × concealment_modifier
4. Victim's insurer may investigate on behalf of victim
5. Community monitoring (neighbors, environmental groups) may detect pattern

**Litigation flow:**
1. Victim identifies likely source (defendant)
2. Files court case for nuisance / trespass / negligence / strict liability
3. Evidence: medical records, property damage assessment, expert reports on causation
4. Court determines: was there harm? Is defendant the cause? Did defendant exercise reasonable care?
5. Strict liability applies to ultrahazardous activities (no due care defense)
6. Comparative negligence: was victim aware of risk and continued anyway?

**Consequences:**
- Compensatory damages (medical costs, property repair, lost income)
- If willful or reckless → punitive damages (2×–3×)
- Injunction (court orders pollution to stop) — enforced by contempt penalties
- Premium increase: 1.4×
- Reputation decrease: -0.25 (if egregious)
- Cleanup costs (may be ordered in addition to damages)

**Notes:**
- Class actions possible if many victims affected similarly
- Victim's health insurance subrogates (insurer pays, then sues polluter)
- Businesses may purchase pollution liability insurance (covers cleanup and defense)
- Some compacts may have no-fault pollution compensation funds

### 4.6 Guild Certification Fraud

**Who detects:** Guild (quality audit), customers (defective work), other guilds

**Detection mechanics:**
1. Certified member produces substandard work
2. Customer detects: product fails, service is poor
3. `P_detect` = 0.30 (detection through normal use) × visibility_modifier (obvious vs latent defect) × magnitude_modifier × concealment_modifier
4. Guild auditor may discover during random quality checks
5. Competing guild may expose fraud to damage rival's reputation

**Litigation flow (customer):**
1. Customer sues guild member for defective work
2. Evidence: the defective product/service, expert testimony
3. If member acted within guild standards → guild may have vicarious liability
4. If member acted outside standards → individual liability, guild may revoke certification

**Litigation flow (guild):**
1. Guild conducts internal hearing
2. If fraud confirmed: certification revoked, guild expelled
3. Guild may compensate customer from mutual pool (if applicable)
4. Guild reports to certification registry

**Consequences:**
- Individual: liability for damages, guild expulsion, reputation -0.3, cannot practice trade without certification
- Guild (if lax oversight): reputation damage, members face higher premiums, may lose accreditation
- Certification revoked: must re-qualify to practice (costly)
- Legal liability for damages caused by substandard work
- If fraud was systematic (guild complicit): guild dissolved, members individually liable

**Notes:**
- Some guilds have mutual insurance that covers member liability
- Guild has incentive to self-police: if they don't, market may abandon guild certification
- Customers may demand guild certification as condition of contract
- Multiple guilds per trade allow competition on certification standards

### 4.7 Court Corruption

**Who detects:** Litigants (adverse ruling with suspicious pattern), other courts, journalists, whistleblowers

**Detection mechanics:**
1. Judge consistently rules in favor of certain parties
2. `P_detect` = 0.10 per case (low — requires pattern across multiple cases)
3. Detection requires: statistical analysis of rulings + circumstantial evidence
4. Whistleblower (court clerk, bribed party) may come forward
5. Other courts may notice if cases consistently migrate to a corrupt court for favorable verdicts

**Litigation flow:**
1. Accuser files case against judge or court in a higher court (if exists) or in a different compact's court
2. Evidence: pattern analysis (ruling statistics), financial records (unexplained wealth), witness testimony
3. Court evaluates: is there evidence of bribery, bias, or extortion?
4. If proven → judge removed, verdicts in questioned cases may be vacated

**Consequences:**
- Judge removed from bench
- All cases tainted by corruption may be retried
- Judge liable for damages caused by corrupt rulings
- Reputation: -0.5 (severe)
- Court loses jurisdiction (other compacts refuse to enforce its judgments)
- Insurance for judicial liability (if exists) may cover damages (but not for intentional corruption)

**Notes:**
- Hard to detect and hard to prove — corruption may persist long
- Market correction: litigants migrate away from corrupt courts
- Courts compete on reputation; corruption is a losing strategy long-term
- Recusal norms (judge steps aside when conflicted) reduce opportunities

### 4.8 Collusion / Price Fixing

**Who detects:** Competitors (harmed by cartel), customers (pay higher prices), whistleblowers (insider)

**Detection mechanics:**
1. Multiple firms in same market charge suspiciously similar prices above competitive level
2. `P_detect` = 0.15 per step × visibility_modifier (prices are public) × magnitude_modifier (excess profits) × concealment_modifier
3. Requires pattern analysis: price correlation across firms, parallel behavior
4. Whistleblower: employee of cartel member provides evidence (often for reward)
5. Customer: notices all providers charge same high price

**Litigation flow:**
1. Plaintiff (competitor, customer, or compact government) files antitrust case
2. Evidence: price data, communication records (if on-ledger), witness testimony
3. Court determines: was there an agreement to fix prices? Or was pricing parallel but independent?
4. If collusion proven → damages = overcharge × volume, trebled (3×) in many compacts

**Consequences:**
- Treble damages (antitrust multiplier)
- Contracts at collusive prices voidable
- Reputation: -0.3
- Premiums: 1.3× base
- If ringleader: additional penalties, potential dissolution of company
- Whistleblower reward: 15–30% of recovered damages

**Notes:**
- Tacit collusion (price matching without explicit agreement) is harder to prove
- Some compacts have leniency programs: first whistleblower gets immunity
- Cartel stability decreases with more members and higher transparency
- Industry associations may facilitate collusion — discoverable through association records

### 4.9 Glass Box Violation (Hiding Data)

**Who detects:** Any citizen, competitor, Actuarial Commons, researcher, journalist

**Detection mechanics:**
1. Required data (transaction records, risk disclosures, environmental reports) is missing or non-replicable
2. `P_detect` = 0.25 per step (anyone trying to access the data notices it's missing)
3. Detection increases if data was previously available and disappears
4. Actuarial Commons may have automated checks for missing submissions
5. Replication failures (someone tries to reproduce a claim and cannot) trigger investigation

**Litigation flow:**
1. Accuser files case for obstruction / Glass Box violation
2. Evidence: record of data request, proof of non-compliance
3. Court evaluates: was data required to be public? Was there a legitimate reason for non-disclosure? (trade secrets may be exempt)
4. If violation proven → order to disclose + penalties

**Consequences:**
- Mandatory disclosure order (with daily fines for continued non-compliance)
- Liability for any harm caused by missing data (e.g., mispriced risk, undetected fraud)
- Reputation: -0.2
- Premiums: 1.3× base
- If systematic: court may appoint a monitor at violator's expense
- Administrative penalty (per-day fine until compliance)

**Notes:**
- Glass Box requirements vary by compact and data type
- Trade secrets and personal privacy are legitimate exemptions
- Violation can be technical (poor record-keeping) vs intentional (destroying evidence)
- Actuarial Commons may impose its own penalties on non-compliant members

### 4.10 Operating Without Insurance

**Who detects:** Insurers (checking proof of coverage), courts (verifying at hearing), counterparties (demanding proof)

**Detection mechanics:**
1. Agent required to carry insurance (for their profession, assets, or activities)
2. Counterparty or court asks for proof of coverage
3. `P_detect` = 0.40 per interaction requiring proof
4. Insurers can check registry of policyholders vs required coverage
5. Court will verify coverage before hearing a case (if required by compact rules)

**Litigation flow:**
1. Accuser (insurer, court, counterparty, compact official) files case
2. Court verifies: does this agent/activity require insurance? Did agent have it?
3. If uninsured → personal liability for any harm caused during period without coverage
4. Agent may be ordered to obtain coverage immediately

**Consequences:**
- Personal liability for ALL harm caused while uninsured (no liability cap)
- If harm occurred: agent pays 100% of damages out of pocket
- If no harm yet: court orders coverage obtained, with penalty
- Cannot operate legally until insured (may face additional penalties for operating while uninsured)
- Reputation: -0.15
- Cannot file certain court cases (some courts require parties to be insured)
- Coverage may be retroactively purchased but at high premium + penalty
- If agent is judgment-proof (cannot pay damages), victim may have no recourse (illustrates why insurance matters)

**Notes:**
- This is one of the most serious violations because it removes the liability system's protection
- Some compacts have automatic enrollment in a basic insurance pool for uninsured agents
- Proof of insurance may be checked at: court filing, guild membership, property registration, business license
- Insurers compete to offer coverage to previously uninsured (it's a new market)

### 4.11 Insider Trading (Compact-Level Securities)

**Who detects:** Competitors, whistleblowers, exchange monitors, Actuarial Commons (pattern)

**Detection mechanics:**
1. Agent trades on material non-public information about compact bonds, land values, or investment contracts
2. `P_detect` = 0.15 per step × visibility_modifier (trades on exchange = visible) × magnitude_modifier × concealment_modifier
3. Exchange monitors for unusual trading patterns before material public announcements
4. Whistleblower: insider or observer reports suspicious trading
5. Counterparty to trade may suspect informational asymmetry

**Litigation flow:**
1. Accuser (compact, exchange, or affected party) files case
2. Evidence: trading records, timing correlation with material information, communication trails
3. Court determines: was information material and non-public? Did defendant know? Did they trade on it?
4. If proven → disgorgement of profits + penalty

**Consequences:**
- Disgorgement: all profits from insider trades returned
- Penalty: up to 3× disgorged profits
- Reputation: -0.25
- Blacklisting from financial markets (cannot trade on exchange)
- Directors/officers: barred from management positions (10–50 steps)
- Premiums: 1.5× base

**Notes:**
- Only relevant if compact has securities or bond markets
- Legal insider trading (based on public information) is permitted
- Tipping (passing information to others who trade) is equivalent to trading
- Some compacts have no insider trading restrictions (let caveat emptor rule)

### 4.12 Double-Pledging Collateral

**Who detects:** Insurers (who rely on collateral for coverage), creditors, collateral registries

**Detection mechanics:**
1. Agent pledges the same asset as collateral for multiple obligations
2. `P_detect` = 0.30 per audit cycle × auditing_modifier (registry checks) × magnitude_modifier
3. Collateral registry detects conflict when second lien is registered
4. First lien holder discovers when they try to enforce and find asset already claimed

**Litigation flow:**
1. Damaged creditor or insurer files case
2. Evidence: collateral registry records, loan documents, insurance policy terms
3. Court determines: was asset double-pledged? Were registries checked?
4. If proven → priority determined by registration order, fraud damages for excess

**Consequences:**
- First-registered lien has priority
- Defrauded creditor recovers damages from agent's other assets
- Reputation: -0.25
- Premiums: 1.4× base
- Insurance blacklist: 30 steps
- Criminal-style penalty (in some compacts): additional damages
- Registration is the key defense — unregistered liens lose priority

**Notes:**
- Central collateral registry prevents most double-pledging
- Cross-compact collateral is harder to track (multiple registries)
- Some assets (land) cannot be double-pledged due to Harberger title system
- Insurers may require collateral for high-risk policies (reinsurance, surety bonds)

### 4.13 Fraudulent Guild Certification

**Who detects:** Guild (internal audit), customers (defective work), other guilds (competition), whistleblowers

**Detection mechanics:**
1. Guild issues certification to unqualified member (bribery, favoritism, test fraud)
2. `P_detect` = 0.25 per step × auditing_modifier (guild quality audits) × magnitude_modifier (number of unqualified certs) × concealment_modifier
3. Customer discovers certified member lacks basic competence
4. Other guild audits reveal inflated certs
5. Whistleblower (disgruntled member, test proctor) exposes scheme

**Litigation flow:**
1. Accuser (customer, other guild, compact) sues guild and/or certified member
2. Evidence: test scores, certification records, work samples, whistleblower testimony
3. Court determines: was certification improperly granted? Was guild complicit?
4. If proven → certification voided, guild liable for damages caused by unqualified members

**Consequences:**
- Guild: liability for all damages caused by fraudulently certified members (potentially massive)
- Guild: reputation -0.4, members face certification challenges, guild may lose accreditation
- Guild officers: personal liability if complicit
- Certified member: certification revoked, reputation -0.3, may be expelled
- Customers: entitled to damages from guild or member
- If systematic: guild dissolved, assets distributed to victims
- Insurance for guild errors & omissions (if held) may cover — but intentional fraud is excluded

**Notes:**
- Different from individual certification fraud (Section 4.6): this is institutional fraud
- Guild has strong incentive to self-police: one bad certification risks entire guild's reputation
- Competing guilds benefit from exposing corruption in rival guilds
- Some guilds use third-party testing to prevent this

### 4.14 Evasion of Court Judgment

**Who detects:** Plaintiff (waiting for payment), court registry (monitoring compliance)

**Detection mechanics:**
1. Defendant ordered to pay damages
2. Payment not received within grace period (3 steps after judgment)
3. `P_detect` = 0.35 (plaintiff knows they weren't paid)
4. Court registry tracks all judgments and payment status

**Litigation flow:**
1. Plaintiff petitions court for enforcement
2. Court issues enforcement order (asset seizure, wage garnishment, etc.)
3. Defendant may contest on grounds of inability to pay (but must disclose assets)
4. If defendant concealed assets → additional penalty for concealment
5. If defendant fled compact → cross-compact enforcement (if agreements exist)

**Consequences:**
- Asset seizure (see Section 2.6)
- Post-judgment interest accrues
- Court judgment blacklist: until debt paid + 10 steps
- Reputation: -0.2 ongoing
- Cannot file new cases in any court until judgment satisfied
- If intentional evasion (asset hiding, flight): punitive damages equal to original award
- Insurer (if defendant had liability insurance) must pay — insurer then subrogates against defendant for non-compliance

**Notes:**
- Most common enforcement problem in real legal systems
- Cross-compact enforcement depends on treaties between compacts
- Some compacts have debtors' prison equivalent (may be treated as additional liability, not incarceration — LS principle)
- Judgment-proof defendants may declare insolvency; garnishment ends

### 4.15 Breach of Fiduciary Duty

**Who detects:** Beneficiaries, co-fiduciaries, auditors, courts (during oversight)

**Detection mechanics:**
1. Agent managing assets for another (trustee, executor, fund manager) acts in self-interest
2. `P_detect` = 0.20 per step × auditing_modifier (regular accounting) × magnitude_modifier (diversion size) × concealment_modifier
3. Beneficiary reviews statements and notices irregularities
4. Co-fiduciary may notice improper decisions
5. Court reviewing estate or trust accounts flags issues

**Litigation flow:**
1. Beneficiary (or co-fiduciary, or compact on behalf of vulnerable) files case
2. Evidence: accounting records, investment statements, communications
3. Court determines: did fiduciary act in beneficiary's best interest? Were there conflicts of interest? Was there self-dealing?
4. If proven → surcharge (fiduciary must restore losses + disgorge profits)

**Consequences:**
- Restitution: restore all losses caused by breach
- Disgorgement: any profits fiduciary made from breach
- Removal as fiduciary
- Reputation: -0.35 (severe — fiduciary duty is a position of trust)
- Premiums: 1.5× base
- Barred from serving as fiduciary (10–50 steps)
- If intentional self-dealing: punitive damages 2×
- Insurance (fiduciary liability) may cover if policy exists (not for intentional breach)

**Notes:**
- Standard of care is higher than ordinary negligence
- Prudent investor rule: fiduciary must invest as a prudent person would
- Self-dealing is per se breach (no defense)
- Full disclosure to beneficiary and consent can cure conflict of interest
- Trusts, estates, corporate directors, fund managers all owe fiduciary duties

### 4.16 Market Manipulation

**Who detects:** Competitors, exchange monitors, Actuarial Commons (statistical), other traders

**Detection mechanics:**
1. Agent places large orders, spreads false information, or corners a market to manipulate prices
2. `P_detect` = 0.15 per step × visibility_modifier (exchange trades are visible) × magnitude_modifier (price impact) × concealment_modifier (layering, spoofing)
3. Exchange monitors unusual order patterns
4. Actuarial Commons flags abnormal price movements inconsistent with fundamentals
5. Competitors observe manipulation and report

**Litigation flow:**
1. Accuser (exchange, affected trader, compact) files case
2. Evidence: trading records, order book data, communications (if conspiratorial)
3. Court determines: was there manipulative intent? Was market price affected?
4. If proven → disgorgement + penalty + restitution to affected traders

**Consequences:**
- Disgorgement: profits from manipulation
- Penalty: 1×–3× disgorged profits
- Restitution: compensate injured traders
- Reputation: -0.25
- Market blacklist: cannot trade on participating exchanges (20–100 steps)
- Premiums: 1.4× base
- If exchange complicit: exchange loses license (rare)

**Notes:**
- Difficult to distinguish from legitimate trading strategies (fundamental analysis, hedging)
- Information-based manipulation (false rumors) requires proving intent
- Cornering a market (buying all supply) is easier to detect
- Exchanges may have their own penalties (trading suspension, account freeze) independent of courts
- Some compacts have no market manipulation restrictions (caveat emptor exchange)

---

### 4.17 Harberger Gaming (Coordinated Under-Declaration)

**Who detects:** Any buyer, compact tax authority, competitor

**Detection mechanics:**
1. Agent under-declares land value to reduce LVT
2. Buyer observes low declared price on a valuable parcel
3. `P_detect` = 0.35 × visibility (declared price is public) × magnitude (LVT savings) × concealment × auditing
4. Detection via: buyer attempts to force purchase at declared price, tax authority spots valuation gap, or competitor notices anomalous pricing

**Litigation flow:**
1. Buyer posts bond at declared price → triggers forced-sale process
2. Seller may refuse (free window or penalty phase) → Option Premium paid
3. If coordinated gaming suspected (side deal between buyer and seller), tax authority or other citizens may file suit
4. Court examines: was the declared price genuinely below market? Was there a side payment?

**Consequences:**
- Forced sale at declared price (immediate, if buyer exercises option)
- Option Premium paid to buyer if seller refuses
- LVT reassessment to market value + back taxes if gaming found
- Reputation decrease: -0.2
- Collusion penalty (if side deal proven): 2× tax savings

**Notes:**
- The Harberger forced-sale mechanism is self-enforcing — under-declaration invites purchase
- Coordinated gaming requires side payments, which are hard to hide in Glass Box systems
- High-value parcels attract more scrutiny

### 4.18 Court Flooding (Frivolous Suits)

**Who detects:** Court administration, defendant's insurer, opposing counsel

**Detection mechanics:**
1. Agent files many small claims or nuisance suits
2. `P_detect` = 0.20 × visibility (court filings are public) × magnitude (total filing fees vs settlements) × concealment
3. Detection: pattern of similar claims from same plaintiff, high rate of dismissed cases, defendants petitioning for sanctions

**Litigation flow:**
1. Defendant (or their insurer) notices pattern and petitions court for abuse of process
2. Court reviews plaintiff's filing history and case outcomes
3. If pattern of frivolous filings found → sanctions imposed
4. Defendant may countersue for malicious prosecution

**Consequences:**
- Dismissal of current case (if frivolous)
- Court sanctions: fine up to 3× filing fees of all related cases
- Barred from filing new cases for X steps (escalating: 30, 90, 180, permanent)
- Reputation decrease: -0.4
- Malicious prosecution damages if victims countersue

**Notes:**
- Small claims courts may have higher tolerance for marginal cases
- Court flooding is most effective when defendant's cost to defend > settlement amount
- Repeated offenders face escalating penalties (see Section 6.2)

### 4.19 Guild Rent-Seeking (Membership Restriction)

**Who detects:** Non-member workers, competing guilds, customers, compact authorities

**Detection mechanics:**
1. Guild restricts membership below market demand (caps, long apprenticeships, high fees)
2. `P_detect` = 0.25 × visibility (membership criteria are public) × magnitude (wage premium) × concealment
3. Detection: wage premium above competitive levels, documented complaints from excluded workers, customer complaints about limited supply

**Litigation flow:**
1. Excluded workers or customers may file a court case alleging anti-competitive practices
2. Court examines: is the restriction justified by quality/safety concerns, or is it solely to raise wages?
3. Burden of proof on guild to demonstrate legitimate purpose
4. If found unjustified → guild must revise membership criteria

**Consequences:**
- Guild ordered to revise membership criteria (open reasonable path to membership)
- Damages to excluded workers (lost wages × steps excluded)
- Guild mutual pool may be used to pay damages
- If guild refuses → dissolution petition to compact authority
- Reputation decrease: -0.3

**Notes:**
- Some restriction is legitimate (skill certification protects public safety)
- The line between quality control and rent-seeking is determined by courts
- Compacts with stronger anti-monopoly norms will attract workers from restrictive guilds

### 4.20 LVT Evasion (Under-Declaration and Compact Arbitrage)

**Who detects:** National Trust, compact tax authority, Harberger buyers, neighboring compacts

**Detection mechanics:**
1. Agent under-declares land value to reduce LVT, or shifts declared residence/asset location to lower-LVT compact
2. `P_detect` = 0.20 × visibility (declared values are public) × magnitude (tax savings) × concealment × auditing
3. Detection of under-declaration: Harberger forced-sale mechanism (anyone can buy at declared price)
4. Detection of compact arbitrage: migration trail, inconsistent residency patterns, land use vs declaration mismatch

**Litigation flow:**
1. For under-declaration: same as Harberger Gaming (Section 4.17)
2. For compact arbitrage: tax authority investigates whether relocation is genuine or nominal
3. Court examines: actual residency, business operations in declared compact, time spent in each jurisdiction
4. If evasion found → back taxes owed to correct compact

**Consequences:**
- Forced sale if under-declared (self-enforcing via Harberger)
- Back LVT owed + interest (10% annualized)
- Penalty: 50% of evaded tax
- Reputation decrease: -0.2
- For repeat offenders: audit flag (automatic higher detection in future)
- Genuine relocation protected; only sham transactions penalized

**Notes:**
- Compact arbitrage is a feature of competitive federalism, not always evasion
- Genuine migration is protected by free movement
- The line between tax planning and tax evasion is determined by court precedent

### 4.21 Asset Flight (Hiding Assets from Judgments)

**Who detects:** Judgment creditors, court registries, insurers, compact authorities

**Detection mechanics:**
1. Agent facing or anticipating a judgment moves assets beyond LS jurisdiction or into untraceable forms
2. `P_detect` = 0.15 × visibility (large transfers are harder to hide) × magnitude (judgment size) × concealment
3. Detection: large transfers coinciding with litigation, shell company formation in foreign jurisdictions, sudden change in declared asset holdings

**Litigation flow:**
1. Creditor discovers suspicious asset movements and petitions court for asset freeze
2. Court issues temporary restraining order on suspect transfers
3. Full hearing: did the agent knowingly transfer assets to evade a foreseeable judgment?
4. If proven → transfers reversed + sanctions
5. If assets beyond LS jurisdiction → STO may coordinate with foreign courts or trigger Trust Blockade

**Consequences:**
- Asset freeze (pending hearing)
- Transfer reversal (if timing proves evasion)
- Sanctions: 30% of concealed amount as penalty
- Reputation decrease: -0.5 (severe — indicates bad faith)
- Insurance blacklist (50 steps) — uninsurable risk
- Potential expulsion from guild

**Notes:**
- Asset flight is hard to detect and harder to reverse across jurisdictions
- The LS has no automatic international treaty enforcement; relies on STO and market pressure
- High-net-worth agents face more scrutiny, making flight more detectable for them

---

## 5. Whistleblower System

### 5.1 Whistleblower Incentives

Whistleblowers are a critical detection channel for violations that are otherwise hard to detect (collusion, corruption, insider trading, fraud).

| Violation Type | Whistleblower Reward | Source of Reward |
|---|---|---|
| Insurance fraud | 20% of recovered amount | Insurer |
| Collusion (antitrust) | 15–30% of recovered damages | Court award |
| Court corruption | Fixed bounty (10,000) | Compact |
| Insider trading | 15% of disgorged profits | Compact/exchange |
| Fraudulent certification | 10% of damages recovered | Guild or victims |
| Environmental violation | 5% of cleanup cost savings | Compact |

### 5.2 Whistleblower Protection

Whistleblowers may face retaliation. Protections include:

| Protection | Mechanism |
|---|---|
| **Anonymity** | Can file report without revealing identity (through intermediary or encrypted channel) |
| **Anti-retaliation** | Retaliation against whistleblower is a separate tort with punitive damages |
| **Identity protection** | Court may seal identity in proceedings |
| **Immunity** | Whistleblower immune from liability for disclosures made in good faith |
| **Witness protection** | Compact may relocate whistleblower in extreme cases |

**Whistleblower decision process:**

```
P_report = clamp(
    0.5 × reward_amount / (reward_amount + base_salary)
    + 0.3 × protection_level
    - 0.2 × retaliation_risk
    - 0.1 × loyalty_to_violator,
    0.0, 1.0
)
```

The whistleblower comes forward if `random() < P_report`.

### 5.3 False Reporting Penalties

To prevent malicious false reports:
- Knowingly false report → liable for defendant's legal costs + damages for reputational harm
- Negligent false report (should have known) → liable for costs but not punitive
- Retraction before investigation → no penalty (encourages correction)

---

## 6. Cross-Violation Dynamics

### 6.1 Compound Violations

A single act may constitute multiple violations (e.g., insurance fraud + Glass Box violation = hiding the fraud evidence). Enforcement treats each separately but courts may consolidate.

### 6.2 Repeat Offender Escalation

| Prior Violations (in N steps) | Detection Multiplier | Penalty Multiplier | Blacklist Duration |
|---|---|---|---|
| 0 | 1.0× | 1.0× | Standard |
| 1 | 1.3× | 1.5× | 1.5× standard |
| 2 | 1.6× | 2.0× | 2× standard |
| 3+ | 2.0× | 3.0× | 3× standard (or permanent) |

### 6.3 Insurance Interaction

- If the defendant has liability insurance: the insurer pays covered damages and may subrogate against the defendant for fraud or intentional acts (which are typically excluded)
- If the plaintiff has legal expense insurance: more likely to file suit
- If either party is uninsured in a domain requiring insurance: additional penalty

### 6.4 Reputation Market Interaction

- All court judgments are public (Glass Box) → feed into reputation score
- Settlements may be confidential → no reputation penalty (incentivizes settlement)
- Unfounded accusations (cases dismissed with prejudice) → reputation penalty for accuser
- Reputation score is an input to future litigation (credibility of parties, likelihood of perjury)

### 6.5 Compact Migration

- Agents may flee a compact to avoid enforcement (judgment evasion)
- Cross-compact enforcement treaties determine whether the judgment follows them
- If no treaty: the violation follows the agent's reputation (reputation is portable — recorded in shared Actuarial Commons)
- The fleeing compact may have its own penalties for aiding fugitives from justice

---

## 7. Configuration Parameters

The following parameters should be configurable in `config.yaml`:

```yaml
enforcement:
  detection:
    base_probabilities:
      insurance_fraud: 0.35
      premium_evasion: 0.20
      harberger_under_declaration: 0.50
      contract_breach: 0.80
      pollution: 0.40
      guild_certification_fraud: 0.30
      court_corruption: 0.10
      collusion: 0.15
      glass_box_violation: 0.25
      operating_without_insurance: 0.40
      insider_trading: 0.15
      double_pledging: 0.30
      fraudulent_guild_certification: 0.25
      judgment_evasion: 0.35
      fiduciary_breach: 0.20
      market_manipulation: 0.15

    modifiers:
      visibility:
        fully_transparent: 1.5
        standard: 1.0
        opaque: 0.5
        hidden: 0.2
      magnitude:
        massive: 2.0
        large: 1.5
        medium: 1.0
        small: 0.75
        micro: 0.5
      concealment:
        none: 1.0
        basic: 0.7
        moderate: 0.4
        sophisticated: 0.2
        extreme: 0.1
      parties:
        one: 0.6
        two: 1.0
        three_to_five: 1.2
        six_to_ten: 1.5
        more_than_ten: 1.8
      auditing:
        continuous: 3.0
        regular: 2.0
        annual: 1.5
        random: 1.0
        none: 0.5
      jurisdiction:
        high: 1.5
        standard: 1.0
        weak: 0.6
        failed: 0.3

    detection_decay_gamma: 0.7  # Per-step decay for non-pattern violations
    pattern_detection_gamma: 1.05  # Per-step increase for pattern-based detection

  litigation:
    evidence_threshold: 0.2
    liability_low_threshold: 0.3
    liability_high_threshold: 0.6
    max_punitive_multiplier: 3.0
    statute_of_limitations:
      contract: 10
      tort: 20
      fraud: 30
      property: 999999  # perpetual
    filing_fee_fraction: 0.02  # 2% of claim amount
    appeal_bond_fraction: 0.05  # 5% of judgment for appeal bond

  consequences:
    reputation:
      default: 0.5
      insurance_fraud_penalty: 0.3
      premium_evasion_penalty: 0.15
      contract_breach_penalty: 0.2
      pollution_penalty: 0.25
      guild_fraud_penalty: 0.3
      court_corruption_penalty: 0.5
      collusion_penalty: 0.3
      glass_box_penalty: 0.2
      uninsured_penalty: 0.15
      insider_trading_penalty: 0.25
      double_pledging_penalty: 0.25
      fiduciary_breach_penalty: 0.35
      market_manipulation_penalty: 0.25
      judgment_evasion_penalty: 0.2

    premium_multipliers:
      insurance_fraud: 2.0
      premium_evasion: 1.5
      contract_breach: 1.2
      pollution: 1.4
      judgment_evasion: 1.8
      uninsured: 2.5
      other: 1.3  # default for unspecified

    blacklist_durations:
      insurance_fraud: 50
      premium_evasion_intentional: 30
      collusion: 40
      insider_trading: 30
      double_pledging: 30
      judgment_evasion: "until_debt_paid_plus_10"
      market_manipulation: 60

  whistleblower:
    rewards:
      insurance_fraud: 0.20
      collusion: 0.25
      court_corruption: "fixed_10000"
      insider_trading: 0.15
      fraudulent_certification: 0.10
      environmental: 0.05
    protection_level: 0.7  # 0-1, affects P_report
```

---

## 8. Detection & Enforcement Algorithm (Pseudocode)

```python
def process_enforcement(simulation_step):
    """
    Called once per simulation step.
    Does not actively enforce. Rolls detection for each active violation
    and processes litigation pipeline for filed cases.
    """

    # === PHASE 1: DETECTION ===
    for violation in active_violations:
        for detector in find_eligible_detectors(violation):
            if not detector.chooses_to_monitor(violation):
                continue

            # Calculate effective detection probability
            p_base = config.base_probabilities[violation.type]
            mod_vis = config.modifiers.visibility[violation.declared_visibility]
            mod_mag = config.modifiers.magnitude[violation.magnitude_level]
            mod_conc = config.modifiers.concealment[violation.concealment_level]
            mod_parties = config.modifiers.parties[violation.parties_aware]
            mod_audit = get_auditing_modifier(detector, violation)
            mod_jur = config.modifiers.jurisdiction[detector.compact.enforcement_level]

            p_effective = clamp(
                p_base * mod_vis * mod_mag * mod_conc * mod_parties * mod_audit * mod_jur,
                0.0, 1.0
            )

            # Apply delay decay
            steps_since_violation = simulation_step - violation.occurred_step
            if violation.detection_mode == "pattern":
                gamma = config.pattern_detection_gamma
            else:
                gamma = config.detection_decay_gamma
            p_this_step = p_effective * (gamma ** steps_since_violation)

            # Roll for detection
            if random.random() < p_this_step:
                violation.detected_by = detector.id
                violation.detected_at_step = simulation_step
                violation.evidence_strength = compute_evidence_strength(
                    detection_factors=(mod_vis, mod_mag, mod_conc, mod_parties, mod_audit, mod_jur),
                    documentation_quality=violation.documentation_quality,
                    witnesses=find_witnesses(violation),
                    forensic_investment=detector.forensic_capability
                )
                active_litigations.append(
                    LitigationCase(
                        violation=violation,
                        plaintiff=detector,
                        evidence_strength=violation.evidence_strength,
                        status="filed"
                    )
                )
                break  # Only first detector becomes plaintiff


    # === PHASE 2: LITIGATION PIPELINE ===
    for case in active_litigations:
        if case.status == "filed":
            case.status = gate_standing_and_jurisdiction(case)
        if case.status == "accepted":
            case.status = gate_evidence_evaluation(case)
        if case.status == "evidence_submitted":
            case.status = gate_adjudication(case)
        if case.status == "liable_found":
            case.status = gate_damages(case)
        if case.status == "judgment_entered":
            case.status = gate_enforcement(case)
        if case.status == "appealed":
            case.status = gate_appeal(case)


def find_eligible_detectors(violation):
    """Returns list of agents who could potentially detect this violation."""
    detectors = []

    # Directly affected parties always eligible
    if violation.type == "contract_breach":
        detectors.append(violation.counterparty)
    elif violation.type == "pollution":
        detectors.append(violation.victim)
        if violation.victim.has_insurance:
            detectors.append(violation.victim.insurer)
    # ... etc for each violation type

    # Insurers detect fraud/evasion for their policyholders
    if violation.type in ("insurance_fraud", "premium_evasion"):
        if violation.perpetrator.has_insurance:
            detectors.append(violation.perpetrator.insurer)

    # General detectors (whistleblowers, auditors, competitors)
    for agent in all_agents:
        if agent.role == "whistleblower" and agent.is_monitoring(violation.context):
            detectors.append(agent)
        if agent.role == "auditor" and agent.current_audit_target == violation.perpetrator:
            detectors.append(agent)
        if agent.role == "competitor" and agent.is_affected_by(violation):
            detectors.append(agent)

    return detectors
```

---

## Appendix A: Evidence Strength Computation Detail

```
evidence_strength = clamp(
    0.30 × normalized_detection_factors
    + 0.30 × documentation_quality
    + 0.20 × witness_credibility
    + 0.20 × forensic_investment,
    0.0, 1.0
)
```

**Normalized detection factors** = average of the modifier values used in detection:
- `(vis_mod + mag_mod + (1.0 - conceal_mod) + parties_mod + audit_mod + jur_mod) / 6.0`
- Higher concealment *reduces* this component (so sophisticated concealers have weaker evidence against them)

**Documentation quality** depends on:
- 0.0: no records (verbal agreement, off-ledger)
- 0.3: minimal records (single receipt, informal note)
- 0.5: standard records (contract, ledger entries, email trail)
- 0.7: Glass Box compliant (full transaction records, automated logging)
- 0.9: audited records (third-party verified, blockchain-style ledger)
- 1.0: forensic-grade (multiple independent verified sources)

**Witness credibility** = average of witness reputation scores, capped at number of witnesses:
- 1 witness: 0.5 × rep_score (one person's word)
- 2–3 witnesses: 0.7 × avg_rep_score (corroborating accounts)
- 4+ witnesses: 0.9 × avg_rep_score (strong corroboration)

**Forensic investment** depends on detector resources allocated:
- 0.0: no investment
- 0.3: standard review of available records
- 0.5: hired an auditor
- 0.7: hired forensic specialist
- 0.9: full independent investigation with expert testimony
- 1.0: court-appointed master or examiner

---

## Appendix B: Court Quality Metrics

Courts compete on reputation. Key metrics that litigants consider:

| Metric | Calculation | Effect on Litigant Decisions |
|---|---|---|
| **Correctness rate** | % of judgments not reversed on appeal | Higher → more cases filed (trust in outcome) |
| **Speed** | Average steps from filing to judgment | Faster → more cases (lower time cost) |
| **Cost** | Filing fee + typical evidence costs | Lower cost → more cases, especially small claims |
| **Fairness** | Variance-adjusted judgment consistency (are similar cases treated alike?) | Higher fairness → more cases, especially from out-of-compact litigants |
| **Enforcement rate** | % of judgments successfully enforced | Higher enforcement → more cases (judgment is meaningful) |
| **Judge integrity** | % of judges with no corruption findings | Higher integrity → more cases, lower forum shopping |

Courts with poor metrics lose market share. In extreme cases, a compact's court may be unable to attract any cases, effectively ending judicial revenue.

---

*End of Specification*
