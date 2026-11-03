"""Facial animation for the witch host.

The model's mesh is weighted to Rigify face DEF bones, but the control layer
was stripped. We free those DEF bones from their constraints and key them
directly: jaw for speech, lids for blinks and sultry half-lids, lip corners
for smirks, brows for attitude.
"""
import math, wave, struct
from mathutils import Vector, Matrix

FACE_KEYS = ('jaw', 'lip', 'lid', 'brow', 'chin', 'cheek', 'teeth', 'tongue', 'nose', 'forehead', 'ear')


class Face:
    def __init__(self, arm, report=print):
        self.arm = arm
        self.pb = arm.pose.bones
        self.bones = [b for b in self.pb if b.name.startswith('DEF-') and any(k in b.name.lower() for k in FACE_KEYS)]
        head = self.pb['DEF-spine.006'] if 'DEF-spine.006' in self.pb else self.pb['head']
        self.L = head.bone.length
        for b in self.bones:
            report('FACEBONE', b.name, 'parent', b.parent and b.parent.name, 'cons', [c.type for c in b.constraints],
                   'head', tuple(round(v, 4) for v in b.bone.head_local))
        self._free()

    def _free(self):
        """Drop constraints so keys drive the bones; hang the lower face off the jaw."""
        jaw = self.pb.get('DEF-jaw')
        for b in self.bones:
            for c in list(b.constraints):
                b.constraints.remove(c)
            b.rotation_mode = 'XYZ'
        if jaw is None:
            return
        ed = self.arm.data
        lower = [b.name for b in self.bones if any(k in b.name for k in ('lip.B', 'chin', 'teeth.B', 'tongue'))]
        import bpy
        bpy.context.view_layer.objects.active = self.arm
        bpy.ops.object.mode_set(mode='EDIT')
        for n in lower:
            eb = ed.edit_bones.get(n)
            if eb and n != 'DEF-jaw':
                eb.use_connect = False
                eb.parent = ed.edit_bones['DEF-jaw']
        bpy.ops.object.mode_set(mode='POSE')
        self.pb = self.arm.pose.bones
        self.bones = [self.pb[b.name] for b in self.bones]

    # --- groups -----------------------------------------------------------
    def group(self, *keys):
        return [b for b in self.bones if all(k in b.name for k in keys)]

    def corners(self):
        lips = [b for b in self.bones if 'lip' in b.name]
        if not lips:
            return []
        xmax = max(abs(b.bone.head_local.x) for b in lips)
        return [b for b in lips if abs(b.bone.head_local.x) > xmax * 0.8]

    # --- primitive keys ---------------------------------------------------
    def jaw(self, f, amount, axis=0, max_deg=16):
        b = self.pb.get('DEF-jaw')
        if not b: return
        e = [0, 0, 0]; e[axis] = math.radians(max_deg * amount)
        b.rotation_euler = e; b.keyframe_insert('rotation_euler', frame=f)

    def _move(self, bones, f, vec_world_fraction):
        """Translate bones by a vector given as a fraction of head length, in armature space."""
        for b in bones:
            v = Vector(vec_world_fraction) * self.L
            if b.name.endswith('.R') or '.R.' in b.name:
                v.x = -v.x
            local = b.bone.matrix_local.to_3x3().inverted() @ v
            b.location = local
            b.keyframe_insert('location', frame=f)

    def lids(self, f, close, side=None):
        """close 0 open .. 1 shut. Upper lids move down, lower lids up a little."""
        sel = lambda g: [b for b in g if side is None or b.name.endswith('.' + side) or f'.{side}.' in b.name]
        self._move(sel(self.group('lid.T')), f, (0, 0, -0.045 * close))
        self._move(sel(self.group('lid.B')), f, (0, 0, 0.012 * close))

    def smirk(self, f, amount, side='L'):
        c = [b for b in self.corners() if b.name.endswith('.' + side) or f'.{side}.' in b.name]
        self._move(c, f, (0.01 * amount, 0.0, 0.025 * amount))

    def brows(self, f, inner_down=0.0, outer_up=0.0, side=None):
        for b in self.group('brow'):
            if side and not (b.name.endswith('.' + side) or f'.{side}.' in b.name):
                continue
            inner = abs(b.bone.head_local.x) < 0.035 * self.L / 0.267 * 1.0
            dz = (-0.03 * inner_down) if inner else (0.03 * outer_up)
            self._move([b], f, (0, 0, dz))

    # --- speech -----------------------------------------------------------
    def lipsync(self, wav_path, f0, fps, gain=1.0, floor=0.08):
        """Drive the jaw from the loudness envelope of a wav, starting at frame f0."""
        env = envelope(wav_path, fps)
        peak = max(env) or 1.0
        prev = 0.0
        for i, e in enumerate(env):
            a = min(1.0, max(0.0, (e / peak - floor) / (1 - floor)) * gain)
            a = 0.55 * a + 0.45 * prev  # soften, avoid chatter
            prev = a
            self.jaw(f0 + i, a)
        self.jaw(f0 + len(env) + 1, 0.0)
        return len(env)

    def blinks(self, f_start, f_end, fps, every_s=3.2, seed=3):
        import random
        r = random.Random(seed)
        t = f_start + int(fps * r.uniform(0.8, 1.6))
        while t < f_end - 4:
            self.lids(t - 1, 0.0); self.lids(t + 1, 1.0); self.lids(t + 3, 0.0)
            t += int(fps * r.uniform(every_s * 0.7, every_s * 1.3))


def envelope(path, fps):
    w = wave.open(path)
    sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
    raw = w.readframes(n)
    fmt = {2: 'h', 4: 'i'}[sw]
    data = struct.unpack('<%d%s' % (n * ch, fmt), raw)[::ch]
    hop = int(sr / fps)
    out = []
    for i in range(0, len(data) - hop, hop):
        seg = data[i:i + hop]
        out.append(math.sqrt(sum(s * s for s in seg) / len(seg)))
    return out
