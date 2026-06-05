# Phase 4 Architecture — Honest Dynamics Simulator

## Design Principles
1. **Emergence over parameters** — corruption, monopolization, bloat emerge from rules, not scalars
2. **Modular layers** — each layer has clear interfaces, testable in isolation
3. **Empirical grounding** — all parameters from published data (IRS, NIT, WJP, TI)
4. **Config-driven systems** — all 10+ systems as configs, no hardcoded logic
5. **Traceable outputs** — every causal path can be decomposed

## 6-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 6: SOCIAL — Demographics, inheritance, norms         │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: MONITORING — Detection, enforcement, audits       │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: INSTITUTIONS — Tax, courts, regulation, banking   │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: MARKETS — Labor, goods, credit, insurance         │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: AGENTS — Workers, businesses, bankers, govt       │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: CORE — Ledger, time, random state                 │
└─────────────────────────────────────────────────────────────┘
```

## Dynamics to Model

| Dynamic | Layer | Mechanism | Parameter Source |
|---------|-------|-----------|-----------------|
| Corruption | 4+5 | Bribery channel → detection prob → penalty | WJP Rule of Law Index |
| Complacency | 2 | Income effect on labor from transfers | NIT experiments (0.05-0.15) |
| Bureaucratic Bloat | 4 | Admin cost = f(tax complexity, system size) | IRS cost studies |
| Monopolization | 3+2 | Economies of scale → market share → markup | Industry concentration data |
| Banking/Credit | 4 | Fractional reserve → loans → interest | Federal Reserve data |
| Demographics | 6 | Birth/death → inheritance → dynastic wealth | Census/OLG models |
| Enforcement | 5 | Detection prob = f(system type, investment) | TI Corruption Index |
