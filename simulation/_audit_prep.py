#!/usr/bin/env python3
"""Audit script: evaluates each mechanism against theoretical/empirical justification.
Criterion: Is the mechanism justified by economic theory and real-world data,
or is it an arbitrary parameter chosen for convenience?

Reports: mechanism name, justification score (1-5), verdict, reasoning.
"""
import sys, os, json, re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load the phase8 source to extract mechanisms
with open('comparison_phase8.py') as f:
    source = f.read()

# Load the mechanism docs
with open('MECHANISMS.md') as f:
    docs = f.read()

# Extract all C('key', default) calls
config_calls = re.findall(r"C\('([^']+)'\s*,\s*([^)]+)\)", source)

# Build audit for each unique key
seen = set()
audits = []
for key, default in config_calls:
    key_clean = key.strip()
    if key_clean in seen:
        continue
    seen.add(key_clean)
    
    # Determine if default is OFF/0 (not biasing)
    default_clean = default.strip().rstrip(')')
    is_off = default_clean in ('0', '0.0', 'False', '1.0', '') or '0.0' in default_clean
    
    # Find the mechanism in docs
    doc_section = ""
    if key_clean in docs:
        idx = docs.find(f"`{key_clean}`")
        if idx >= 0:
            doc_section = docs[idx:idx+800].replace('\n', ' | ')
    
    justification = "NEEDS_AUDIT"
    
    # Pre-score based on known characteristics
    # These are pre-scores for the audit — each will be verified
    score_pre = 3  # default unknown
    
    audits.append({
        'key': key_clean,
        'default': default_clean,
        'default_off': is_off,
        'doc_snippet': doc_section[:300],
        'provisional_score': score_pre,
        'needs_audit': True
    })

print(json.dumps(audits, indent=2))
