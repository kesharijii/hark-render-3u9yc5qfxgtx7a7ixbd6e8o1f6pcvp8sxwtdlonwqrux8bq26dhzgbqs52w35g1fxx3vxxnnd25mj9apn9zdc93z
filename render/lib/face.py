"""Facial performance for the witch host (v3).

The mesh still carries Rigify face weights (DEF-lid.*, DEF-brow.*, DEF-lip.*,
DEF-cheek.*, DEF-nose.*...), but those bones were deleted from the armature;
only DEF-jaw, teeth and tongue survive. `Face` rebuilds a bone for every
orphaned DEF- face group at its weighted centroid, so the existing skin
weights drive the face again.

Animation is additive and baked per frame:
  * SHAPES  - small, named bone-offset sets (smile_L, squint_R, brow_down...)
  * EXPR    - emotions as weighted mixes of shapes (smug, menace, delight...)
  * speech  - jaw + three lip shapes (wide / round / press) read from the audio
  * life    - blinks, head nods on stressed syllables, slow head sway
Everything is summed per frame in `bake()`, so speech rides on top of the
emotion instead of overwriting it.

Usage:
    face = Face(armature)
    face.express(1, 'smug'); face.express(40, 'menace')
    face.speak('line.wav', start_frame=8, fps=15)
    face.blinks(1, 120, 15)
    face.bake(1, 120)
"""
import bisect, math, random, wave
import bpy
import numpy as np
from mathutils import Euler, Vector

FACE_PREFIX = ('DEF-lid', 'DEF-brow', 'DEF-lip', 'DEF-chin', 'DEF-cheek', 'DEF-jaw', 'DEF-nose',
               'DEF-forehead', 'DEF-temple', 'DEF-ear', 'DEF-teeth', 'DEF-tongue')
LOWER = ('DEF-lip.B', 'DEF-chin', 'DEF-jaw.', 'DEF-teeth.B', 'DEF-tongue')
FACE_MESHES = ('chubby_body', 'eyes_brow', 'eyes_lashes', 'teeth_down', 'teeth_up', 'tongue', 'eyes_L', 'eyes_R')
SIDES = ('L', 'R')


def is_face(name):
    return name.startswith(FACE_PREFIX)


def side_of(name):
    if name.endswith('.L') or '.L.' in name: return 'L'
    if name.endswith('.R') or '.R.' in name: return 'R'
    return None


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


class Curve:
    """Keyed scalar (or tuple) with smoothstep easing between keys."""

    def __init__(self, default=0.0):
        self.f, self.v, self.default = [], [], default

    def key(self, f, v):
        i = bisect.bisect_left(self.f, f)
        if i < len(self.f) and self.f[i] == f: self.v[i] = v
        else: self.f.insert(i, f); self.v.insert(i, v)

    def __call__(self, f):
        if not self.f: return self.default
        i = bisect.bisect_right(self.f, f)
        if i == 0: return self.v[0]
        if i == len(self.f): return self.v[-1]
        f0, f1, v0, v1 = self.f[i - 1], self.f[i], self.v[i - 1], self.v[i]
        t = smooth((f - f0) / (f1 - f0))
        if isinstance(v0, tuple): return tuple(a + (b - a) * t for a, b in zip(v0, v1))
        return v0 + (v1 - v0) * t


# Emotions as shape mixes. Values are shape weights (1.0 = full shape).
EXPR = {
    'neutral':  {},
    'smug':     {'smile_L': .8, 'smile_R': .25, 'squint_L': .3, 'squint_R': .3, 'brow_up_L': .55},
    'sultry':   {'lids_L': .35, 'lids_R': .35, 'smile_L': .5, 'brow_up_L': .15, 'brow_up_R': .15},
    'menace':   {'brow_down': .9, 'squint_L': .5, 'squint_R': .5, 'smile_L': .35, 'sneer_L': .3},
    'delight':  {'smile_L': 1, 'smile_R': 1, 'squint_L': .45, 'squint_R': .45, 'brow_up_L': .35, 'brow_up_R': .35},
    'surprise': {'brow_up_L': 1, 'brow_up_R': 1, 'wide_eyes': 1, 'jaw': .25},
    'annoyed':  {'frown': .6, 'brow_down': .5, 'squint_L': .3, 'squint_R': .3, 'sneer_R': .25},
    'pout':     {'frown': .5, 'brow_sad': .6, 'lids_L': .15, 'lids_R': .15},
    'tease':    {'smile_L': .7, 'smile_R': .4, 'brow_up_R': .65, 'squint_L': .35},
}


class Face:
    def __init__(self, arm, report=print, seed=3, gain=1.5):
        self.arm, self.report, self.gain = arm, report, gain
        self.rng = random.Random(seed)
        self.centroids = self._centroids()
        self._rebuild()
        self.pb = arm.pose.bones
        self.bones = {n: self.pb[n] for n in self.pb.keys() if is_face(n)}
        lt, lb = self._avg('DEF-lid.T'), self._avg('DEF-lid.B')
        self.s = abs(lt.z - lb.z) if lt and lb else 0.01   # eye opening: the face's unit of motion
        self.shapes = self._shapes()
        self.w = {}                       # shape -> Curve (sparse, eased)
        self.events = []                  # (frame, expression, amount)
        self.jaw_c, self.head_c = Curve(), Curve((0.0, 0.0, 0.0))
        self.dense = {}                   # channel -> {frame: value} (speech, blinks, nods)
        self.phase = {k: self.rng.uniform(0, 6.28) for k in ('brow_up_L', 'brow_up_R', 'smile_L', 'smile_R', 'squint_L', 'squint_R')}
        self.head = self.pb.get('head')
        self.eyes = self._eye_rig()
        report('FACE', len(self.bones), 'bones; unit', round(self.s, 4), 'shapes', sorted(self.shapes))

    # ---------------------------------------------------------------- rebuild
    def _centroids(self):
        """Weighted centroid (armature space) of every face vertex group across the face meshes."""
        inv = self.arm.matrix_world.inverted()
        acc = {}
        for mn in FACE_MESHES:
            o = bpy.data.objects.get(mn)
            if not o: continue
            names = {g.index: g.name for g in o.vertex_groups if is_face(g.name)}
            M = inv @ o.matrix_world
            for v in o.data.vertices:
                p = None
                for g in v.groups:
                    n = names.get(g.group)
                    if n and g.weight > 0.05:
                        p = p or (M @ v.co)
                        s = acc.setdefault(n, [Vector(), 0.0]); s[0] += p * g.weight; s[1] += g.weight
        return {n: s[0] / s[1] for n, s in acc.items() if s[1] > 0}

    def _c(self, name):
        return self.centroids.get(name, Vector())

    def _avg(self, prefix):
        pts = [c for n, c in self.centroids.items() if n.startswith(prefix)]
        return sum(pts, Vector()) / len(pts) if pts else None

    def _rebuild(self):
        arm = self.arm
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode='EDIT')
        eb = arm.data.edit_bones
        anchor = eb.get('ORG-face') or eb.get('DEF-spine.006') or eb['head']
        jaw = eb.get('DEF-jaw')
        made = []
        for n, c in sorted(self.centroids.items()):
            if n in eb: continue
            b = eb.new(n); b.head = c; b.tail = c + Vector((0, -0.01, 0)); b.roll = 0
            b.use_deform = True
            made.append(n)
        for b in eb:
            if not is_face(b.name) or b.name == 'DEF-jaw': continue
            if b.name.startswith(LOWER) and jaw: b.use_connect = False; b.parent = jaw
            elif b.name in made: b.parent = anchor
        bpy.ops.object.mode_set(mode='POSE')
        for n in ['DEF-jaw'] + made:
            pb = arm.pose.bones.get(n)
            if not pb: continue
            for c in list(pb.constraints): pb.constraints.remove(c)
            pb.rotation_mode = 'XYZ'
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report('FACE made', len(made))

    # ---------------------------------------------------------------- shapes
    def _sel(self, prefix, side=None):
        return [n for n in self.bones if n.startswith(prefix) and (side is None or side_of(n) == side)]

    def _split_x(self, names):
        """(inner, outer) halves of a bone set by distance from the face midline."""
        if not names: return [], []
        xs = {n: abs(self._c(n).x) for n in names}
        mid = (min(xs.values()) + max(xs.values())) / 2
        return [n for n in names if xs[n] < mid], [n for n in names if xs[n] >= mid]

    def _shapes(self):
        """Named offsets, written for the character's left side (+x outward, -y forward, +z up),
        in eye-opening units; right-side bones get x mirrored when baked."""
        lips = self._sel('DEF-lip')
        xmax = max((abs(self._c(n).x) for n in lips), default=1)
        corner = {sd: [n for n in lips if side_of(n) == sd and abs(self._c(n).x) > .7 * xmax] for sd in SIDES}
        mid_t = [n for n in lips if n.startswith('DEF-lip.T') and n not in corner['L'] + corner['R']]
        mid_b = [n for n in lips if n.startswith('DEF-lip.B') and n not in corner['L'] + corner['R']]
        brow = {sd: self._split_x(self._sel('DEF-brow', sd)) for sd in SIDES}
        nostril = {sd: self._sel('DEF-nose.' + sd, sd) for sd in SIDES}
        S = {}

        def add(shape, names, v):
            d = S.setdefault(shape, {})
            for n in names: d[n] = d.get(n, Vector()) + Vector(v)

        for sd in SIDES:
            add(f'lids_{sd}', self._sel('DEF-lid.T', sd), (0, 0, -1.7))
            add(f'lids_{sd}', self._sel('DEF-lid.B', sd), (0, 0, .3))
            add(f'squint_{sd}', self._sel('DEF-lid.B', sd), (0, 0, .45))
            add(f'squint_{sd}', self._sel('DEF-lid.T', sd), (0, 0, -.35))
            add(f'squint_{sd}', self._sel('DEF-cheek.T', sd), (0, 0, .35))
            add(f'smile_{sd}', corner[sd], (.5, .2, 1.4))
            add(f'smile_{sd}', self._sel('DEF-cheek.B', sd), (.1, 0, .8))
            add(f'smile_{sd}', self._sel('DEF-cheek.T', sd), (0, 0, .45))
            add(f'smile_{sd}', self._sel('DEF-lid.B', sd), (0, 0, .2))
            add(f'smile_{sd}', nostril[sd], (.05, 0, .12))
            add(f'brow_up_{sd}', brow[sd][0], (0, 0, 1.2))
            add(f'brow_up_{sd}', brow[sd][1], (0, 0, 1.3))
            add(f'brow_up_{sd}', self._sel('DEF-forehead', sd), (0, 0, .3))
            add(f'sneer_{sd}', nostril[sd], (0, 0, .6))
            add(f'sneer_{sd}', [n for n in mid_t if side_of(n) == sd], (0, 0, .35))
            add(f'sneer_{sd}', self._sel('DEF-cheek.B', sd), (0, 0, .2))
            add('wide_eyes', self._sel('DEF-lid.T', sd), (0, 0, .35))
            add('wide_eyes', self._sel('DEF-lid.B', sd), (0, 0, -.15))
            add('frown', corner[sd], (-.05, 0, -1.0))
            add('brow_down', brow[sd][0], (-.35, 0, -1.3))
            add('brow_down', brow[sd][1], (0, 0, -.2))
            add('brow_sad', brow[sd][0], (0, 0, 1.0))
            add('brow_sad', brow[sd][1], (0, 0, -.3))
            add('vis_wide', corner[sd], (.5, .15, .1))
            add('vis_round', corner[sd], (-.5, -.3, 0))
        add('frown', mid_b, (0, 0, .12))
        add('frown', self._sel('DEF-chin'), (0, 0, .25))
        add('vis_round', mid_t, (0, -.35, -.05))
        add('vis_round', mid_b, (0, -.35, .08))
        add('vis_press', mid_t, (0, 0, -.3))
        add('vis_press', mid_b, (0, 0, .35))
        return S

    def _eye_rig(self):
        """Bones that turn the eyeballs: whatever the eye meshes are weighted or parented to."""
        found = {}
        for sd in SIDES:
            o = bpy.data.objects.get(f'eyes_{sd}')
            cands = []
            if o:
                if o.parent_type == 'BONE' and o.parent_bone: cands.append(o.parent_bone)
                cands += [g.name for g in o.vertex_groups if 'eye' in g.name.lower()]
            cands += [n for n in (f'DEF-eye.{sd}', f'ORG-eye.{sd}', f'MCH-eye.{sd}', f'eye.{sd}') if n in self.pb]
            for n in cands:
                if n in self.pb: found[sd] = self.pb[n]; break
        self.report('FACE eyes', {k: v.name for k, v in found.items()},
                    'eye groups', [g.name for g in getattr(bpy.data.objects.get('eyes_L'), 'vertex_groups', [])][:8])
        for b in found.values():
            for c in list(b.constraints): c.mute = True
            b.rotation_mode = 'XYZ'
        return found

    def gaze(self, f0, f1, fps, at_camera=.7):
        """Saccades: quick eye jumps, held 0.6-2.2 s, mostly back to the lens."""
        t = f0
        while t < f1:
            if self.rng.random() < at_camera: yaw, pitch = self.rng.uniform(-2, 2), self.rng.uniform(-1, 1)
            else: yaw, pitch = self.rng.choice((-1, 1)) * self.rng.uniform(6, 12), self.rng.uniform(-5, 4)
            for k in range(int(fps * self.rng.uniform(.6, 2.2))):
                self._dense('gaze_yaw', t + k, yaw, 'set'); self._dense('gaze_pitch', t + k, pitch, 'set')
            t += int(fps * self.rng.uniform(.6, 2.2))

    def look(self, f0, f1, yaw, pitch):
        for f in range(f0, f1 + 1):
            self._dense('gaze_yaw', f, yaw, 'set'); self._dense('gaze_pitch', f, pitch, 'set')

    # ---------------------------------------------------------------- authoring
    def express(self, f, name, amount=1.0):
        """Hold expression `name` from frame f until the next express() call."""
        assert name in EXPR, name
        self.events.append((f, name, amount))

    def head_pose(self, f, pitch=0.0, yaw=0.0, roll=0.0):
        """Base head angle in degrees (armature space), eased between keys."""
        self.head_c.key(f, (float(pitch), float(yaw), float(roll)))

    def _dense(self, ch, f, v, mode='max'):
        d = self.dense.setdefault(ch, {})
        d[f] = v if mode == 'set' else (max(d.get(f, 0.0), v) if mode == 'max' else d.get(f, 0.0) + v)

    def speak(self, wav_path, start_frame, fps, gain=1.15, nods=True):
        """Jaw + wide/round/press lip shapes from loudness and brightness of the voice."""
        env, cen = load_analysis(wav_path) if wav_path.endswith('.json') else analyse(wav_path, fps)
        if not len(env): return 0
        peak = np.percentile(env, 95) or 1.0
        a = np.clip((env / peak - .1) / .9 * gain, 0, 1)
        lo, md, hi = np.percentile(cen[a > .3], [15, 50, 85]) if (a > .3).sum() > 3 else (1, 2, 3)
        prev = 0.0
        for i in range(len(a)):
            x = a[i]
            x = .7 * x + .3 * prev if x > prev else .45 * x + .55 * prev   # quick attack, softer release
            prev = x
            f = start_frame + i
            wide = smooth((cen[i] - md) / max(hi - md, 1e-6)) * x
            rnd = smooth((md - cen[i]) / max(md - lo, 1e-6)) * x * .9
            self._dense('jaw', f, x)
            self._dense('vis_wide', f, wide)
            self._dense('vis_round', f, rnd)
            # lips meet in short dips between loud frames (m / b / p)
            win = a[max(0, i - 3): i + 4]
            if a[i] < .15 and len(win) and win.max() > .4: self._dense('vis_press', f, 1.0)
        n = len(a)
        self._dense('jaw', start_frame + n + 1, 0.0)
        for i in range(n):   # cheeks and lower lids ride on the jaw, like a real face
            self._dense('squint_L', start_frame + i, .18 * a[i], 'add'); self._dense('squint_R', start_frame + i, .18 * a[i], 'add')
        if nods:   # stressed syllables: nod, brow pop (sometimes one brow), a little head tilt
            last = -99
            for i in range(1, n - 1):
                if a[i] > .7 and a[i] >= a[i - 1] and a[i] >= a[i + 1] and i - last > 6:
                    f = start_frame + i
                    one = self.rng.random() < .35
                    sd = self.rng.choice(SIDES)
                    tdir = self.rng.choice((-1, 1))
                    for k, v in enumerate((.4, 1.0, .8, .55, .3, .12)):
                        self._dense('nod', f + k, v)
                        if one: self._dense(f'brow_up_{sd}', f + k, .7 * v, 'add')
                        else: self._dense('brow_up_L', f + k, .45 * v, 'add'); self._dense('brow_up_R', f + k, .45 * v, 'add')
                        self._dense('tilt', f + k, v * tdir, 'add')
                    last = i
        return n

    def blinks(self, f_start, f_end, fps, every_s=3.0):
        t = f_start + int(fps * self.rng.uniform(.6, 1.4))
        while t < f_end - 4:
            for k, v in enumerate((.5, 1.0, .8, .3)):
                self._dense('blink', t + k, v)
            t += int(fps * self.rng.uniform(every_s * .6, every_s * 1.3))

    def blink(self, f):
        for k, v in enumerate((.5, 1.0, .8, .3)): self._dense('blink', f + k, v)

    # ---------------------------------------------------------------- bake
    def _expr_curves(self, ramp=4):
        curves = {}
        ev = sorted(self.events)
        names = {k for _, n, _ in ev for k in EXPR[n]}
        for i, (f, n, amt) in enumerate(ev):
            hold = (ev[i + 1][0] - ramp) if i + 1 < len(ev) else None
            for k in names:
                v = EXPR[n].get(k, 0.0) * amt
                c = curves.setdefault(k, Curve())
                c.key(f, v)
                if hold and hold > f: c.key(hold, v)
        return curves

    def weights(self, f, curves):
        w = {k: c(f) for k, c in curves.items()}
        for ch, d in self.dense.items():
            w[ch] = w.get(ch, 0.0) + d.get(f, 0.0)
        # micro-motion: a living face never holds perfectly still
        for k, amp, fr in (('brow_up_L', .12, .11), ('brow_up_R', .12, .13), ('smile_L', .1, .07),
                           ('smile_R', .08, .09), ('squint_L', .08, .17), ('squint_R', .08, .19)):
            w[k] = w.get(k, 0.0) + amp * (.5 + .5 * math.sin(f * fr + self.phase[k]))
        b = w.pop('blink', 0.0)
        for sd in SIDES:                      # a blink closes from wherever the lids are
            base = w.get(f'lids_{sd}', 0.0)
            w[f'lids_{sd}'] = base + (1.0 - base) * min(1.0, b)
        if w.get('vis_press'): w['jaw'] = w.get('jaw', 0.0) * (1 - w['vis_press'])
        return w

    def bake(self, f0, f1, sway=True):
        curves = self._expr_curves()
        mats = {n: b.bone.matrix_local.to_3x3().inverted() for n, b in self.bones.items()}
        used = {n for d in self.shapes.values() for n in d}
        jaw = self.bones.get('DEF-jaw')
        hq = self.head.bone.matrix_local.to_quaternion() if self.head else None
        if self.head: self.head.rotation_mode = 'QUATERNION'
        ph = self.rng.uniform(0, 6.28)
        for f in range(f0, f1 + 1):
            w = self.weights(f, curves)
            off = {n: Vector() for n in used}
            for k, wt in w.items():
                if not wt or k not in self.shapes: continue
                for n, v in self.shapes[k].items(): off[n] += v * wt
            for n in used:
                v = off[n] * self.s * self.gain
                if side_of(n) == 'R': v.x = -v.x
                b = self.bones[n]; b.location = mats[n] @ v
                b.keyframe_insert('location', frame=f)
            if jaw:
                jaw.rotation_euler = (math.radians(14 * min(1.2, w.get('jaw', 0.0))), 0, 0)
                jaw.keyframe_insert('rotation_euler', frame=f)
            if self.head:
                p, y, r = self.head_c(f)
                p += 5.0 * w.get('nod', 0.0)
                r += 3.0 * w.get('tilt', 0.0)
                if sway:
                    y += 4.0 * math.sin(f * .07 + ph) + 1.5 * math.sin(f * .19 + ph * .3)
                    r += 3.0 * math.sin(f * .045 + ph * 1.7)
                    p += 1.5 * math.sin(f * .061 + ph * 2.3)
                q = Euler((math.radians(p), math.radians(y), math.radians(r)), 'XYZ').to_quaternion()
                self.head.rotation_quaternion = hq.inverted() @ q @ hq
                self.head.keyframe_insert('rotation_quaternion', frame=f)
            for sd, b in self.eyes.items():
                b.rotation_euler = (math.radians(w.get('gaze_pitch', 0.0)), 0, math.radians(-w.get('gaze_yaw', 0.0)))
                b.keyframe_insert('rotation_euler', frame=f)
        self.report('FACE baked', f0, f1)


def analyse(path, fps):
    """Per-frame RMS loudness and spectral centroid (Hz) of a mono/stereo 16-bit wav."""
    w = wave.open(path)
    sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
    x = np.frombuffer(w.readframes(n), dtype={2: np.int16, 4: np.int32}[sw]).astype(np.float32)
    x = x.reshape(-1, ch).mean(axis=1) / (2 ** (8 * sw - 1))
    hop = int(sr / fps)
    frames = [x[i:i + hop] for i in range(0, len(x) - hop, hop)]
    env = np.array([np.sqrt(np.mean(fr * fr)) for fr in frames])
    freqs = np.fft.rfftfreq(hop, 1 / sr)
    cen = []
    for fr in frames:
        m = np.abs(np.fft.rfft(fr * np.hanning(len(fr))))
        band = (freqs > 150) & (freqs < 5000)
        cen.append(float((freqs[band] * m[band]).sum() / (m[band].sum() + 1e-9)))
    return env, np.array(cen)


def load_analysis(path):
    """Precomputed {'fps', 'env', 'cen'} so a render needs no audio file."""
    import json
    d = json.load(open(path))
    return np.array(d['env'], dtype=float), np.array(d['cen'], dtype=float)


def envelope(path, fps):
    return list(analyse(path, fps)[0])
