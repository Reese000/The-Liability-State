#!/usr/bin/env python3
"""Seed-level variance for China and India."""
import sys, os, copy
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))
import logging
logging.basicConfig(level=logging.WARNING)
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS

for name in ['China', 'India']:
    cfg = copy.deepcopy(PHASE8_CONFIGS[name])
    ginis, wealths = [], []
    for s in range(1, 6):
        w, r, b = gen_population(s)
        res = run_phase8(w, r, b, s, cfg)
        ginis.append(res['gini'])
        wealths.append(res['w_mean'])
    print('{:<6}: Gini={:.4f} +/- {:.4f}  Wealth=${:,.0f} +/- ${:,.0f}'.format(
        name, np.mean(ginis), np.std(ginis), np.mean(wealths), np.std(wealths)))
    print('  Seeds: {}'.format(['{:.4f}'.format(g) for g in ginis]))
