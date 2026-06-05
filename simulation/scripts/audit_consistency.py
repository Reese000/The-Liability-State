#!/usr/bin/env python3
"""
Cross-reference audit: verify the 7 simulation specs are internally consistent.
Checks key interfaces between specs for naming mismatches, type conflicts, and gaps.
"""
import os
import sys
import re

SPEC_DIR = "/mnt/c/Users/reese/OneDrive/Desktop/AI/The Liability State/simulation/specs"
PASS = 0
FAIL = 0

def check(desc, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {desc}")
    else:
        FAIL += 1
        print(f"  ❌ {desc} — {detail}" if detail else f"  ❌ {desc}")

def load(name):
    path = os.path.join(SPEC_DIR, name)
    with open(path, 'r') as f:
        return f.read()

# ─── Load all specs ────────────────────────────────────────────────
specs = {}
for f in os.listdir(SPEC_DIR):
    if f.endswith(".md"):
        specs[f] = load(f)

print("=" * 65)
print("SIMULATION ARCHITECTURE — CROSS-REFERENCE AUDIT")
print("=" * 65)

# ─── 1. Core spec coverage ─────────────────────────────────────────
print("\n━━━ 1. REQUIRED SPECS EXIST ━━━\n")
required = [
    "MECHANICS_INVENTORY.md",
    "AGENT_MODEL.md",
    "ENFORCEMENT_MODEL.md",
    "EVENT_MODEL.md",
    "ADVERSARIAL_STRATEGIES.md",
    "VALIDATION_FRAMEWORK.md",
    "CORE_LEDGER.md",
]
for name in required:
    check(f"{name} exists", name in specs, f"Missing: {name}")

# ─── 2. Agent types mentioned in all specs ─────────────────────────
print("\n━━━ 2. AGENT TYPE CONSISTENCY ━━━\n")

agent_types = ["worker", "business", "insurer", "guild", "court"]
source_unsorted = specs.get("MECHANICS_INVENTORY.md", "")
agent_model = specs.get("AGENT_MODEL.md", "")
enforcement = specs.get("ENFORCEMENT_MODEL.md", "")
adv_strat = specs.get("ADVERSARIAL_STRATEGIES.md", "")

for atype in agent_types:
    in_mech = atype in source_unsorted.lower()
    in_agent = atype in agent_model.lower()
    in_enforce = atype in enforcement.lower()
    in_adv = atype in adv_strat.lower()
    msg = f"Agent '{atype}' in Mechanics={in_mech}, Agent={in_agent}, Enforce={in_enforce}, Adv={in_adv}"
    check(msg, in_mech and in_agent)

# ─── 3. Key LS mechanic names appear in both mechanics inventory AND ledger ─
print("\n━━━ 3. MECHANIC ↔ LEDGER CONSISTENCY ━━━\n")

mechanics = specs.get("MECHANICS_INVENTORY.md", "").lower()
ledger = specs.get("CORE_LEDGER.md", "").lower()

key_terms = [
    "land value tax", "lvt",
    "citizen's dividend", "dividend",
    "harberger", "forced sale",
    "insurance premium", "premium",
    "insurance claim", "claim",
    "court fee", "filing fee",
    "court award", "judgment",
    "guild dues", "guild",
    "war bond", "victory bond",
    "alliance skim",
    "glass box",
    "reinsurance",
]

for term in key_terms:
    in_mech = term in mechanics
    in_ledger = term in ledger
    check(f"Term '{term}' in Mechanics={in_mech}, Ledger={in_ledger}",
          in_mech)

# ─── 4. Violation types in enforcement match adversarial strategies ─
print("\n━━━ 4. ENFORCEMENT ↔ ADVERSARIAL CONSISTENCY ━━━\n")

violation_keywords = [
    "premium evasion", "insurance fraud", "harberger gaming",
    "court flooding", "forum shopping", "contract breach",
    "collusion", "guild rent-seeking", "glass box",
    "lvt evasion", "asset flight",
]
for v in violation_keywords:
    in_enforce = v in enforcement.lower()
    in_adv = v in adv_strat.lower()
    check(f"Violation '{v}' in Enforcement={in_enforce}, Adversarial={in_adv}",
          in_enforce and in_adv,
          f"Missing from {'Adversarial' if not in_adv else 'Enforcement'}")

# ─── 5. Event types in event model ─────────────────────────────────
print("\n━━━ 5. EVENT MODEL COVERAGE ━━━\n")

events = load("EVENT_MODEL.md").lower() if "EVENT_MODEL.md" in specs else ""
event_types = [
    "natural disaster", "foreign invasion", "mass tort",
    "technology disruption", "insurance market failure",
    "guild scandal", "compact secession", "pandemic",
    "population shock", "class action", "financial crisis",
]
for e in event_types:
    check(f"Event '{e}' defined", e in events)

# ─── 6. Validation stages exist ────────────────────────────────────
print("\n━━━ 6. VALIDATION STAGES ━━━\n")

validation = load("VALIDATION_FRAMEWORK.md").lower() if "VALIDATION_FRAMEWORK.md" in specs else ""
val_stages = ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9"]
for vs in val_stages:
    check(f"Validation stage '{vs}' defined",
          f"{vs} " in validation or f"## {vs}" in validation or f"stage {vs}" in validation)

# ─── 7. Check for major gaps ───────────────────────────────────────
print("\n━━━ 7. MAJOR GAP DETECTION ─━━\n")

# Check if money flows track the full citizen experience
citizen_flows = ["wage", "salary", "income", "labor", "dividend", "premium", "claim", "lvt", "harberger"]
for flow in citizen_flows:
    check(f"Ledger tracks '{flow}'", flow in ledger)

# Check that every mechanic has an adversarial strategy
adv_text = adv_strat.lower()
major_mechanics_for_attack = ["lvt", "harberger", "insurance", "court", "guild", "glass box", "contract", "dividend"]
for mm in major_mechanics_for_attack:
    check(f"Adversarial strategies target '{mm}'", mm in adv_text)

# ─── 8. Summary ────────────────────────────────────────────────────
print(f"\n{'=' * 65}")
print(f"AUDIT COMPLETE: {PASS} PASSED, {FAIL} FAILED")
print(f"{'=' * 65}")
sys.exit(0 if FAIL == 0 else 1)
