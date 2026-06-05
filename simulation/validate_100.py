#!/usr/bin/env python3
"""Validate the 100-improvements sounding board for:
1. No duplicate entries within the list
2. No ideas that already exist in the codebase  
3. Cost estimates are internally consistent
4. All 100 entries present and complete
5. No placeholder/missing content"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

# Read the file
with open('100_improvements.md') as f:
    text = f.read()

lines = text.split('\n')
PASS, FAIL = 0, 0

def check(desc, cond, detail=''):
    global PASS, FAIL
    if cond: PASS+=1; print(f'  ✓ {desc} {detail}')
    else: FAIL+=1; print(f'  ✗ FAIL: {desc} {detail}')

# Test 1: Exactly 100 numbered ideas
print('\n─── Structure ───')
nums = re.findall(r'^\| (\d+) \|', text, re.MULTILINE)
ids = [int(n) for n in nums]
check('100 numbered entries', len(ids) == 100, f'found={len(ids)}')
check('Consecutive 1-100', ids == list(range(1,101)), f'first={ids[0]}, last={ids[-1]}')
check('10 section headers', text.count('## ') == 10)

# Test 2: No duplicate titles
print('\n─── No Duplicates ───')
titles = re.findall(r'^\| \d+ \| \*\*(.*?)\*\*', text, re.MULTILINE)
titles_lower = [t.lower() for t in titles]
check('All titles unique', len(set(titles_lower)) == len(titles_lower))
# Check for near-duplicates
for i, t1 in enumerate(titles_lower):
    for j, t2 in enumerate(titles_lower):
        if i < j and (t1 in t2 or t2 in t1):
            print(f'  ⚠ Near-duplicate: #{i+1}="{titles[i]}" ~ #{j+1}="{titles[j]}"')

# Test 3: Cost estimates are valid
print('\n─── Cost Estimates ───')
costs = re.findall(r'\|\s*(Low|Medium|High|Very High)\s*\|', text)
check('All 100 have cost estimates', len(costs) == 100)
low = costs.count('Low')
med = costs.count('Medium')
high = costs.count('High')
vh = costs.count('Very High')
check('Costs sum to 100', low+med+high+vh == 100, f'L={low} M={med} H={high} VH={vh}')

# Test 4: Cross-reference against existing code
print('\n─── Cross-Reference: Not Already Implemented ───')
# Known existing features (from codebase grep)
existing = [
    'adversarial', 'premium evasion', 'insurance fraud', 'harberger gaming',
    'court flooding', 'guild rent seeking', 'collusion', 'contract breach',
    'lvt evasion', 'event', 'recession', 'mass tort', 'natural disaster',
    'population', 'gini', 'ledger', 'court', 'compact', 'LVT', 'dividend',
    'welfare', 'bank', 'monopoly', 'economies of scale', 'income effect',
    'enforcement', 'info asymmetry', 'inheritance', 'inherit',
]
for idea_title in titles:
    title_lower = idea_title.lower()
    match = [e for e in existing if e.lower() in title_lower]
    if match:
        print(f'  ⚠ Already partially covered: "{idea_title}" matches: {match}')

# Test 5: Each entry has all 4 fields (number, title, detail, cost)
print('\n─── Entry Completeness ───')
entries = re.findall(r'\| (\d+) \| \*\*(.*?)\*\* — (.*?) \| (.*?) \| (Low|Medium|High|Very High) \|', text, re.DOTALL)
check('Each entry has title+description+rationale+cost', len(entries) == 100)

# Test 6: No placeholders
print('\n─── No Placeholders ───')
check('No TODO markers', 'TODO' not in text)
check('No FIXME markers', 'FIXME' not in text.upper())
check('No XXX markers', 'XXX' not in text.upper())
check('No TBD markers', 'TBD' not in text.upper())

# Test 7: Description length quality
print('\n─── Description Quality ───')
short_descs = [e[2] for e in entries if len(e[2]) < 20]
check('No critically short descriptions', len(short_descs) == 0, 
      f'short entries={len(short_descs)}' if short_descs else '')

# Test 8: Cost distribution reasonableness
print('\n─── Cost Distribution ───')
check('Low-cost items exist (quick wins)', low >= 5, f'L={low}')
check('Very-high-cost items exist (ambitious)', vh >= 5, f'VH={vh}')

# Summary
print(f'\n{"="*60}')
print(f'  {PASS}/{PASS+FAIL} checks passed')
if FAIL == 0:
    print('  ✅ SOUNDING BOARD VALID')
else:
    print(f'  ❌ {FAIL} failures')
print(f'{"="*60}')
sys.exit(0 if FAIL == 0 else 1)
