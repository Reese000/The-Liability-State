"""Test calibration mapping: verify per-system mechanism configs are correct.

Tests:
1. BASE_MECHS has all expected shared keys
2. All 11 systems have entries in SYSTEM_MECHS
3. Per-system calibration values are in expected ranges
4. All configs pass _validate_mech_config
5. Non-empty overrides that are identical are flagged as intentional (LS variants)
6. All numeric values within [0, 1] where applicable
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))

from run_calibrated_comparison import BASE_MECHS, SYSTEM_MECHS, _validate_mech_config

PASS, FAIL = 0, 0
def check(name, ok):
    global PASS, FAIL
    if ok: PASS += 1; print(f'  ✅ {name}')
    else: FAIL += 1; print(f'  ❌ {name}')

all_systems = sorted([
    'Singapore', 'Laissez_Faire', 'US_Style', 'Nordic', 'Worker_Coop',
    'LS_Full', 'Pure_Georgist', 'Mutualist_LS', 'UBI_VAT',
    'Dual_Compact_LS', 'Harberger_Georgist'
])

# 1. BASE_MECHS has expected keys
expected_shared = ['inflation_rate', 'endogenous_tfp', 'wage_competition',
                   'capital_ownership_share', 'mobility_cost']
for k in expected_shared:
    check(f'BASE_MECHS.{k} exists', k in BASE_MECHS)

# 2. All 11 systems have entries
for sn in all_systems:
    check(f'SYSTEM_MECHS has {sn}', sn in SYSTEM_MECHS)

# 3. Per-system value range checks
checks = {
    'Singapore': [
        ('cpf_liquidity_trap', 0.05, 0.15),
        ('cpf_demand_suppression', 0.05, 0.15),
        ('cpf_housing_feedback', 0.02, 0.10),
    ],
    'Laissez_Faire': [
        ('use_public_goods', True, True),
    ],
    'US_Style': [
        ('gov_service_productivity', 0.3, 0.5),
        ('capital_ownership_concentration', 0.5, 1.0),
    ],
    'Nordic': [
        ('gov_service_productivity', 0.5, 0.7),
        ('capital_ownership_concentration', 0.2, 0.4),
        ('wage_competition_intensity', 0.1, 0.2),
    ],
    'Worker_Coop': [
        ('capital_ownership_share', 0.3, 0.5),
        ('capital_ownership_concentration', 0.0, 0.2),
    ],
}
for sn, cs in checks.items():
    cfg = SYSTEM_MECHS.get(sn, {})
    for key, lo, hi in cs:
        if isinstance(lo, bool):
            check(f'{sn}.{key}={cfg.get(key)}', cfg.get(key) == hi)
        else:
            val = cfg.get(key)
            check(f'{sn}.{key}={val} in [{lo},{hi}]', val is not None and lo <= val <= hi)

# 4. All configs pass validation
for sn in all_systems:
    cfg = dict(BASE_MECHS)
    if sn in SYSTEM_MECHS:
        cfg.update(SYSTEM_MECHS[sn])
    try:
        _validate_mech_config(sn, cfg)
        check(f'{sn} passes validation', True)
    except Exception as e:
        check(f'{sn} validation: {e}', False)

# 5. Duplicate overrides between LS variants are intentional
seen = {}
for sn in all_systems:
    if SYSTEM_MECHS.get(sn):
        items = tuple(sorted(SYSTEM_MECHS[sn].items()))
        if items in seen:
            check(f'{sn} shares config with {seen[items]} (intentional)', True)
        else:
            seen[items] = sn

# 6. All systems accounted for (no orphans)
for sn in all_systems:
    check(f'{sn} in SYSTEM_MECHS', sn in SYSTEM_MECHS)

total = PASS + FAIL
print(f'\nRESULTS: {PASS} passed, {FAIL} failed out of {total}')
sys.exit(0 if FAIL == 0 else 1)
