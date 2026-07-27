# The Liability State

> **A Comprehensive Documentation Library for an Audited Society**  
> **Status:** Active research and simulation project

A governance model that replaces ex-ante regulation with ex-post strict liability enforced through private courts and mandatory insurance. Revenue from Land Value Tax (LVT); no income tax. Citizens receive a Universal Dividend. Corporate liability shields are eliminated.

---

## Contents

| Directory | Description |
|-----------|-------------|
| `1_Ideology/` | Philosophical foundation — goals, principles, constitutional framework, 2008 case study |
| `2_Laws_and_Functions/` | Complete operational mechanics — economics, finance, legal system, defense, infrastructure, taxation, monetary system (12 chapters) |
| `3_Implementation/` | Transition pathway from current US system — Regency Period, institutional reform, pilot programs |
| `4_Critiques_and_Risks/` | Self-assessed vulnerabilities — fiscal gap, capital formation, insurance cartel risk, justice access, military risks (16 chapters with mitigations) |
| `5_Future_Ideas/` | Forward-looking concepts — AI auditors, post-scarcity, space frontier, Harberger patents |
| `simulation/` | Full economic agent-based simulation (Python) — validates the model against historical data across 10+ countries |
| `Audiobook/` | Text-to-speech narrations of the complete document set |
| `scripts/` | Validation and integrity-checking utilities |

---

## Simulation

The `simulation/` directory is the most active development area. It contains a custom Python ABM (not Mesa) with:

- **Double-entry accounting engine** — every dollar tracked, zero-balance invariant
- **Agent types** — workers, businesses, insurers, guilds, courts
- **Mechanics** — LVT, insurance pooling, Harberger property, tort liability, guild certification
- **Validation** — 4 canonical micro-tests (adverse selection, LVT efficiency, tort deterrence, Harberger)
- **Adversarial layer** — agents can switch to exploitative strategies (fraud, collusion, forum shopping)
- **Cross-country backtesting** — US, UK, France, Germany, Japan, Brazil, India, China, South Korea
- **50+ experiment outputs** — comparison results, sensitivity analyses, Pareto fronts

### Tech Stack

- Python 3.11+, NumPy, Pandas, Matplotlib, networkx
- YAML configuration
- SQLite for per-run storage

## Honest Status

**The written document is mature** — 5 sections covering ideology, law, implementation, critiques, and future ideas, plus an audiobook narration. The **simulation is actively under development** with over 50 experiment runs completed and cross-country calibration ongoing. The simulation has identified several failure modes (adverse selection, court gridlock) and is being refined iteratively. Not yet ready for peer review but structurally complete.

---

## Related Repositories

- **[Business Plan](https://github.com/Reese000/Business-Plan)** — Practical CNC shop launch planning (operates at the personal business level, not the system governance level)
- **[Costs](https://github.com/Reese000/Costs)** — Business financial records (independent project; no direct overlap)

> **Note:** The word "costs" appears throughout this document in the economic/theoretical sense (transaction costs, cost of regulation, cost of insurance). This is **not** a reference to the separate `Costs` repository.
