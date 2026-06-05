#!/usr/bin/env python3
"""Complete cross-country decomposition for Japan, India, China, South Korea.

Runs 4 additional countries and produces a full cross-country comparison table.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from comparison_phase8 import run_phase8, gen_population

SEED = 42

# Load configs from validate scripts
sys.path.insert(0, os.path.dirname(__file__))
from validate_japan_backtest import PERIODS as JP_CONFIGS
from validate_india_backtest import PERIODS as IN_CONFIGS
from validate_china_backtest import PERIODS as CN_CONFIGS
from validate_sk_backtest import PERIODS as SK_CONFIGS

COUNTRIES = {
    'Japan': (JP_CONFIGS[1960], JP_CONFIGS[2020]),
    'India': (IN_CONFIGS[1970], IN_CONFIGS[2020]),
    'China': (CN_CONFIGS[1980], CN_CONFIGS[2020]),
    'South_Korea': (SK_CONFIGS[1980], SK_CONFIGS[2020]),
}

# Mechanisms to test
MECHANISMS = [
    ('skill_premium_growth', 'SBTC'),
    ('union_coverage', 'Union Coverage'),
    ('capital_income_share', 'Financialization'),
    ('import_competition', 'Import Competition'),
    ('import_displacement_rate', 'Import Displacement'),
    ('use_progressive_tax', 'Progressive Tax'),
    ('elite_capture_intensity', 'Elite Capture'),
    ('informal_share', 'Informal Sector'),
]

def make_config(base, toggle_off=None):
    cfg = dict(base)
    if toggle_off:
        if toggle_off == 'use_progressive_tax':
            cfg[toggle_off] = False
        elif toggle_off in ('skill_premium_growth', 'union_coverage', 'capital_income_share',
                            'import_competition', 'import_displacement_rate',
                            'elite_capture_intensity', 'informal_share'):
            cfg[toggle_off] = 0.0
    return cfg

def run_decomposition(name, cfg_early, cfg_late):
    w1, r1, b1 = gen_population(SEED)
    res_late = run_phase8(w1, r1, b1, SEED, cfg_late)
    w0, r0, b0 = gen_population(SEED)
    res_early = run_phase8(w0, r0, b0, SEED, cfg_early)
    g_early = res_early['gini']
    g_late = res_late['gini']
    delta_full = g_late - g_early
    
    print(f'\n{name}: {g_early:.4f} -> {g_late:.4f}  delta={delta_full:+.4f}')
    
    contribs = {}
    for key, label in MECHANISMS:
        c_early = make_config(cfg_early, key)
        c_late = make_config(cfg_late, key)
        w, r, b = gen_population(SEED)
        r_e = run_phase8(w, r, b, SEED, c_early)
        w2, r2, b2 = gen_population(SEED)
        r_l = run_phase8(w2, r2, b2, SEED, c_late)
        delta = r_l['gini'] - r_e['gini']
        contribs[key] = delta_full - delta
    
    ranked = sorted(contribs.items(), key=lambda x: -abs(x[1]))
    for i, (key, contrib) in enumerate(ranked, 1):
        pct = abs(contrib) / max(abs(delta_full), 0.001) * 100
        print(f'  {i}. {dict(MECHANISMS)[key]:<25} {contrib:+.4f} ({pct:.0f}%)')
    
    return {'full_delta': delta_full, 'contribs': contribs}

all_results = {}
for name, (cfg_early, cfg_late) in COUNTRIES.items():
    all_results[name] = run_decomposition(name, cfg_early, cfg_late)

# Final cross-country table
print(f'\n{"="*80}')
print('COMPLETE CROSS-COUNTRY COMPARISON')
print(f'{"="*80}')
print(f'{"Country":<14} {"Delta":>8} {"Top Driver 1":<30} {"Top Driver 2":<30} {"Top Driver 3":<30}')
print('-' * 112)

# Include US, UK, France, Brazil from previous results
previous = {
    'US': {'delta': 0.1081, 'drivers': ['ImportComp (24%)', 'ImportDisp (24%)', 'SBTC (20%)']},
    'UK': {'delta': 0.1761, 'drivers': ['ImportComp (15%)', 'ImportDisp (15%)', 'SBTC (6%)']},
    'France': {'delta': -0.0394, 'drivers': ['ProgTax (179%)', 'SBTC (46%)', 'ImportComp (36%)']},
    'Brazil': {'delta': -0.0456, 'drivers': ['Patrimonial (237%)', 'SBTC (18%)', 'ProgTax (16%)']},
}

all_countries = {**previous}
for name, res in all_results.items():
    ranked = sorted(res['contribs'].items(), key=lambda x: -abs(x[1]))[:3]
    drivers = []
    for key, contrib in ranked:
        if abs(res['full_delta']) > 0.01:
            pct = abs(contrib) / abs(res['full_delta']) * 100
            drivers.append(f'{dict(MECHANISMS)[key]} ({pct:.0f}%)')
        else:
            drivers.append(f'{dict(MECHANISMS)[key]} ({contrib:+.4f})')
    all_countries[name] = {'delta': res['full_delta'], 'drivers': drivers}

for name in ['US', 'UK', 'France', 'Brazil', 'Japan', 'India', 'China', 'South_Korea']:
    if name in all_countries:
        d = all_countries[name]
        dr = d['drivers'] + [''] * (3 - len(d['drivers']))
        print(f'{name:<14} {d["delta"]:>+8.4f} {dr[0]:<30} {dr[1]:<30} {dr[2]:<30}')

print('-' * 112)
with open('output/full_cross_country.json', 'w') as f:
    json.dump({k: {'delta': v['delta'], 'drivers': v['drivers']} for k, v in all_countries.items()}, f, indent=2)
print('Saved: output/full_cross_country.json')
