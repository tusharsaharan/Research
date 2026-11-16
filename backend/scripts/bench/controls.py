"""Question-independent negative controls under a measured context budget."""
from __future__ import annotations

import hashlib
import math
import random

from gateway.modules.m2_compressor.qwen_evidence import source_units


def shuffled_context(passage, item_id, target, count, seed=20261116):
    if not math.isfinite(target) or not 0 < target <= 1:
        raise ValueError('target must be in (0,1]')
    budget=max(1,math.floor(count(passage)*target)) if passage else 0
    units=source_units(passage)
    order=list(range(len(units)))
    rng=random.Random(int(hashlib.sha256(f'{seed}|{item_id}'.encode()).hexdigest(),16))
    rng.shuffle(order)
    chosen=[]
    for index in order:
        if count('\n'.join(units[i] for i in [*chosen,index]))<=budget:
            chosen.append(index)
    text='\n'.join(units[i] for i in chosen)
    return dict(text=text,original_tokens=count(passage),actual_tokens=count(text),target_tokens=budget,
                budget_met=count(text)<=budget,selected_ids=chosen,shuffle_order=order,
                note='Shuffled complete-span subset under the same cap; achieved token counts need not match candidate exactly.')
