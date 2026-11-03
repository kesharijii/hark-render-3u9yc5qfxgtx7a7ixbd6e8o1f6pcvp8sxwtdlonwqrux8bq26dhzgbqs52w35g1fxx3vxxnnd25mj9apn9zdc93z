"""Facial animation for the witch host.

The mesh still carries Rigify face weights (DEF-lid.*, DEF-brow.*, DEF-lip.*,
DEF-chin.*, DEF-cheek.*...), but those bones were deleted from the armature;
only DEF-jaw, teeth and tongue survive. We rebuild a bone for every orphaned
DEF- face group at its weighted centroid, so the existing skin weights drive
the face again, then key those bones for speech, blinks and expressions.
"""
import math, wave, struct
import bpy
from mathutils import Vector

FACE_PREFIX = ('DEF-lid', 'DEF-brow', 'DEF-lip', 'DEF-chin', 'DEF-cheek', 'DEF-jaw', 'DEF-nose',
               'DEF-forehead', 'DEF-temple', 'DEF-ear', 'DEF-teeth', 'DEF-tongue')
LOWER = ('DEF-lip.B', 'DEF-chin', 'DEF-jaw.', 'DEF-teeth.B', 'DEF-tongue')
FACE_MESHES = ('chubby_body', 'eyes_brow', 'eyes_lashes', 'teeth_down', 'teeth_up', 'tongue', 'eyes_L', 'eyes_R')


def is_face(name):
    return name.startswith(FACE_PREFIX)


def side_of(name):
    if name.endswith('.L') or '.L.' in name: return 'L'
    if name.endswith('.R') or '.R.' in name: return 'R'
    return None


class Face:
    def __init__(self, arm, report=print):
        self.arm, self.report = arm, report
        self.centroids = self._centroids()
        self._rebuild()
        self.pb = arm.pose.bones
        self.bones = {n: self.pb[n] for n in self.pb.keys() if is_face(n)}
        jaw = self.bones.get('DEF-jaw')
        self.L = (self._c('DEF-jaw') - self._c('DEF-forehead.L', self._c('DEF-jaw') + Vector((0, 0, .1)))).length or 0.1
        lt = self._avg('DEF-lid.T'); lb = self._avg('DEF-lid.B')
        self.eye_gap = abs(lt.z - lb.z) if lt and lb else 0.01
        report('FACE rebuilt', len(self.bones), 'bones; scale', round(self.L, 4), 'eye_gap', round(self.eye_gap, 4))

    # --- setup ------------------------------------------------------------
    def _centroids(self):
        """Weighted centroid (armature space) of every face vertex group across face meshes."""
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

    def _c(self, name, default=None):
        return self.centroids.get(name, default)

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
            if b.name.startswith(LOWER) and jaw:
                b.use_connect = False; b.parent = jaw
            elif b.name in made:
                b.parent = anchor
        bpy.ops.object.mode_set(mode='POSE')
        for n in ['DEF-jaw'] + made:
            pb = arm.pose.bones.get(n)
            if not pb: continue
            for c in list(pb.constraints): pb.constraints.remove(c)
            pb.rotation_mode = 'XYZ'
        self.report('FACE made', len(made), sorted(made))

    # --- primitives -------------------------------------------------------
    def _sel(self, prefix, side=None):
        return [b for n, b in self.bones.items() if n.startswith(prefix) and (side is None or side_of(n) == side)]

    def _move(self, bones, f, v):
        """v in armature space (absolute units)."""
        for b in bones:
            vv = Vector(v)
            if side_of(b.name) == 'R': vv.x = -vv.x
            b.location = b.bone.matrix_local.to_3x3().inverted() @ vv
            b.keyframe_insert('location', frame=f)

    def jaw(self, f, amount, max_deg=14):
        b = self.bones.get('DEF-jaw')
        if not b: return
        b.rotation_euler = (math.radians(max_deg * amount), 0, 0)
        b.keyframe_insert('rotation_euler', frame=f)

    def lids(self, f, close, side=None):
        d = self.eye_gap
        self._move(self._sel('DEF-lid.T', side), f, (0, 0, -1.7 * d * close))
        self._move(self._sel('DEF-lid.B', side), f, (0, 0, 0.3 * d * close))

    def smirk(self, f, amount, side='L'):
        lips = [b for n, b in self.bones.items() if n.startswith('DEF-lip')]
        if not lips: return
        xmax = max(abs(self._c(b.name, Vector()).x) for b in lips)
        c = [b for b in lips if side_of(b.name) == side and abs(self._c(b.name, Vector()).x) > 0.7 * xmax]
        s = self.eye_gap
        self._move(c, f, (0.35 * s * amount, -0.1 * s * amount, 0.9 * s * amount))
        cheek = self._sel('DEF-cheek.B', side)
        self._move(cheek, f, (0, 0, 0.4 * s * amount))

    def pucker(self, f, amount):
        """Rounded lips for OO/W sounds."""
        lips = [b for n, b in self.bones.items() if n.startswith('DEF-lip')]
        s = self.eye_gap
        for b in lips:
            x = self._c(b.name, Vector()).x
            self._move([b], f, (-0.25 * s * amount * (1 if x > 0 else -1) * (1 if side_of(b.name) != 'R' else -1), -0.15 * s * amount, 0))

    def brows(self, f, inner_down=0.0, outer_up=0.0, side=None):
        bs = self._sel('DEF-brow', side)
        if not bs: return
        xs = [abs(self._c(b.name, Vector()).x) for b in bs]; mid = (min(xs) + max(xs)) / 2
        s = self.eye_gap
        for b in bs:
            inner = abs(self._c(b.name, Vector()).x) < mid
            dz = -1.0 * s * inner_down if inner else 1.0 * s * outer_up
            self._move([b], f, (0, 0, dz))

    def neutral(self, f):
        self.jaw(f, 0); self.lids(f, 0); self.smirk(f, 0, 'L'); self.smirk(f, 0, 'R'); self.brows(f, 0, 0)

    # --- speech -----------------------------------------------------------
    def lipsync(self, wav_path, f0, fps, gain=1.15, floor=0.1):
        env = envelope(wav_path, fps)
        peak = sorted(env)[int(len(env) * 0.95)] or 1.0
        prev = 0.0
        for i, e in enumerate(env):
            a = min(1.0, max(0.0, (e / peak - floor) / (1 - floor)) * gain)
            a = 0.6 * a + 0.4 * prev; prev = a
            self.jaw(f0 + i, a)
        self.jaw(f0 + len(env) + 1, 0.0)
        return len(env)

    def blinks(self, f_start, f_end, fps, every_s=3.2, base=0.0, seed=3):
        import random
        r = random.Random(seed)
        t = f_start + int(fps * r.uniform(0.8, 1.6))
        while t < f_end - 4:
            self.lids(t - 1, base); self.lids(t + 1, 1.0); self.lids(t + 3, base)
            t += int(fps * r.uniform(every_s * 0.7, every_s * 1.3))


def envelope(path, fps):
    w = wave.open(path)
    sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
    data = struct.unpack('<%d%s' % (n * ch, {2: 'h', 4: 'i'}[sw]), w.readframes(n))[::ch]
    hop = int(sr / fps)
    return [math.sqrt(sum(s * s for s in data[i:i + hop]) / hop) for i in range(0, len(data) - hop, hop)]
