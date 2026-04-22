#!/usr/bin/env python3
import random, sys
sys.path.insert(0, ".")
from markov_rhythm import (
    build_global_chain_from_folder, generate_sequence, RATIO_LABEL, mirror_ratio
)

CHAIN, _, _ = build_global_chain_from_folder("Flows desde Muiñeira de Monterrei")

random.seed(42)
seq_n, nf_n = generate_sequence(CHAIN, (1.0, 0.5), 12, mirror=False)

random.seed(42)
seq_m, nf_m = generate_sequence(CHAIN, (1.0, 0.5), 12, mirror=True)

print("idx | Normal              | Espello             | ruído_n | ruído_m")
for i in range(max(len(seq_n), len(seq_m))):
    rn = RATIO_LABEL.get(seq_n[i], str(seq_n[i])) if i < len(seq_n) else "-"
    rm = RATIO_LABEL.get(seq_m[i], str(seq_m[i])) if i < len(seq_m) else "-"
    vn = seq_n[i] if i < len(seq_n) else None
    vm = seq_m[i] if i < len(seq_m) else None
    nn = str(nf_n[i]) if i < len(nf_n) else "-"
    nm = str(nf_m[i]) if i < len(nf_m) else "-"
    flag = " ***" if rn != rm else ""
    print(f"{i:3d} | {rn:>5s} ({str(vn):>5s}) | {rm:>5s} ({str(vm):>5s}) | {nn:>6s} | {nm:>6s}{flag}")
