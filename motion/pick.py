import sys
"""Pick the best MoMask sample per prompt with simple physical heuristics and copy it to motion/out/<name>.npy.

MoMask joints: (T,22,3), y-up, 20 fps. Heuristics (no human review in CI):
  * reject sitting/crouching takes: pelvis must stay near standing height,
  * locomotion prompts (walk/carry/tiptoe) must actually travel; standing prompts must not drift,
  * hand prompts reward the expected hand height (pet: right wrist high; shock: both wrists near head).
"""
import glob, json, os, shutil, sys
import numpy as np

gen, out = sys.argv[1], sys.argv[2]
names = [l.strip() for l in open(sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(__file__), 'names.txt')) if l.strip()]
os.makedirs(out, exist_ok=True)
LOCO = {'walk', 'carry', 'tiptoe'}
report = {}
for k, name in enumerate(names):
    fs = sorted(glob.glob(os.path.join(gen, 'joints', str(k), '*_ik.npy')))
    best = None
    for f in fs:
        P = np.load(f)
        pel = P[:, 0, 1]; head = P[:, 15, 1]
        stand_h = np.percentile(pel, 90)
        sit_pen = max(0.0, 0.8 - pel.min() / max(stand_h, 1e-3)) * 10 + max(0.0, 0.85 - stand_h) * 10
        travel = float(np.linalg.norm(P[-1, 0, [0, 2]] - P[0, 0, [0, 2]]))
        if name in LOCO:
            mot = -min(travel, 4.0) + (3.0 if travel < 1.2 else 0.0)
        else:
            mot = max(0.0, travel - 0.6) * 3
        hand = 0.0
        if name == 'pet':
            hand = -float(P[:, 21, 1].max() - head.max()) * 2   # right wrist up near/above head
        if name == 'shock':
            d = np.minimum(np.linalg.norm(P[:, 20] - P[:, 15], axis=1), np.linalg.norm(P[:, 21] - P[:, 15], axis=1))
            hand = float(d.min()) * 3
        if name == 'facepalm':
            hand = float(np.linalg.norm(P[:, 21] - P[:, 15], axis=1).min()) * 3
        if name == 'nose':
            hand = float(np.linalg.norm(P[:, 21] - P[:, 15], axis=1).min()) * 3
        score = sit_pen + mot + hand
        report.setdefault(name, []).append(dict(file=os.path.basename(f), score=round(score, 3), travel=round(travel, 2),
                                                pelvis_min=round(float(pel.min()), 2), stand_h=round(float(stand_h), 2)))
        if best is None or score < best[0]:
            best = (score, f)
    if best:
        shutil.copy(best[1], os.path.join(out, name + '.npy'))
        report[name + '_chosen'] = os.path.basename(best[1])
    else:
        report[name + '_chosen'] = None
json.dump(report, open(os.path.join(out, 'pick_report.json'), 'w'), indent=1)
print(json.dumps(report, indent=1))
