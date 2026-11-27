#!/usr/bin/env python3
"""Check documented numeric examples/invariants, not Unity runtime behaviour."""
import json
import math
from fractions import Fraction

checks = []
def check(label, ok):
    if not ok:
        raise AssertionError(label)
    checks.append(label)

# Block compression: round every level separately, never round bpp alone.
def astc(w, h, block):
    return math.ceil(w/block) * math.ceil(h/block) * 16
base6, base4 = astc(1024, 1024, 6), astc(1024, 1024, 4)
check('ASTC 6x6 base = 467856 bytes; saving rounds to 55.38%',
      base6 == 467856 and base4 == 1048576 and round((1-base6/base4)*100, 2) == 55.38)
full6 = sum(astc(max(1,1024 >> mip), max(1,1024 >> mip), 6) for mip in range(11))
check('ASTC mip rounding differs from blindly multiplying by 4/3',
      full6 == 626288 and full6 != base6 * Fraction(4,3))
check('1080p RGBA8 ~7.91 MiB; 2048 R8 =4 MiB',
      round(1920*1080*4/2**20, 2) == 7.91 and 2048**2/2**20 == 4)
check('200m/2048 ~9.77cm; circle/square ~78.54%',
      round(200/2048*100, 2) == 9.77 and round(math.pi/4*100,2) == 78.54)
check('0.75 render scale means 56.25% pixels; 60fps budget ~16.67ms',
      .75**2 == .5625 and round(1000/60,2) == 16.67)
check('Terrain example: 32x32 patches, 8m each; 513 height points ->0.5m',
      1024//32 == 32 and 256/(1024/32) == 8 and 256/(513-1) == .5)
flat = [2,8,15,8,21]
rows = [(0,3),(3,2)]
sets = [set(flat[start:start+count]) for start,count in rows]
check('CSR slices support non-contiguous IDs and one shared building',
      sets[0] == {2,8,15} and sets[1] == {8,21} and len(set.union(*sets)) == 4)
check('Negative coordinates require floor, not truncation',
      math.floor(-1/32) == -1 and int(-1/32) == 0)
# Coverage union counterexample, preserving sub-sample identity.
left, right = 0b0011, 0b1100
check('Max scalar coverage is not area union',
      max(left.bit_count()/4, right.bit_count()/4) == .5 and (left|right).bit_count()/4 == 1)
check('Non-square UV has unequal metric scale for equal world distances',
      not math.isclose(1/200,1/100))
# Four timestamps: server and client intentionally have different epochs.
def measure(up, down, processing, offset=5000):
    t0 = 10
    t1 = t0 + up + offset
    t2 = t1 + processing
    t3 = t0 + up + processing + down
    return ((t1-t0)+(t2-t3))/2, (t3-t0)-(t2-t1)
a,rtt = measure(.05,.05,.03)
b,_ = measure(.02,.08,.03)
check('NTP symmetric offset and processing-time subtraction',
      math.isclose(a,5000) and math.isclose(rtt,.1))
check('NTP asymmetric error = (uplink-downlink)/2',
      math.isclose(b-5000,-.03,abs_tol=1e-9))
# Fully covered screen footprint; a background hole must prevent culling.
def hidden_normal(nearest, depth_samples):
    return nearest > max(depth_samples)
def hidden_reversed(nearest, depth_samples):
    return nearest < min(depth_samples)
check('Hi-Z max/min equivalence and conservative background hole',
      hidden_normal(.8,[.2,.4]) and not hidden_normal(.8,[.2,1.0]) and
      hidden_reversed(.2,[.8,.6]) and not hidden_reversed(.2,[.8,0.0]))
print(json.dumps({'checks': len(checks), 'passed': checks,
                  'limits': 'Arithmetic/model checks only; no GPU, engine, driver or network runtime measurements.'},
                 ensure_ascii=False, indent=2))
