"""Reusable stage pieces for witch shorts: host loading, world, lights, cameras, props, particles.

Every helper is frame-keyed so a shot file only describes *what happens when*.
Coordinates: the witch stands at the origin facing -Y, ~1.55 m to the base of the head.
"""
import math, os
import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

R = math.radians
HOST = 'magic girl  pbr_Rigify'


# ------------------------------------------------------------------ keys
def key(owner, path, f, value):
    setattr(owner, path, value); owner.keyframe_insert(path, frame=f)


def key_socket(sock, f, value):
    sock.default_value = value
    sock.keyframe_insert('default_value', frame=f)


def set_interp(owner, interp, path=None):
    ad = getattr(owner, 'animation_data', None)
    if not ad or not ad.action: return
    for fc in ad.action.fcurves:
        if path is None or fc.data_path == path:
            for k in fc.keyframe_points: k.interpolation = interp


def show(obj, f_on, f_off=None):
    """Render-visible only in [f_on, f_off)."""
    for f, hidden in ((1, True), (f_on, False)) + (((f_off, True),) if f_off else ()):
        obj.hide_render = hidden; obj.keyframe_insert('hide_render', frame=f)
        obj.hide_viewport = hidden; obj.keyframe_insert('hide_viewport', frame=f)


# ------------------------------------------------------------------ materials
def mat(name, col, rough=0.5, emit=None, strength=0.0, metal=0.0, transmission=0.0, ior=1.45, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Transmission Weight'].default_value = transmission
    b.inputs['IOR'].default_value = ior
    b.inputs['Alpha'].default_value = alpha
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = strength
    return m


def emission_socket(m):
    return m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']


def prim(kind, name, material=None, **kw):
    getattr(bpy.ops.mesh, f'primitive_{kind}_add')(**kw)
    o = bpy.context.active_object; o.name = name
    if material: o.data.materials.append(material)
    return o


# ------------------------------------------------------------------ host
class Witch:
    """The witch host: hides helper objects, shrinks textures, normalises scale, gives pose helpers."""

    POSE = {  # (upper_arm_fk, forearm_fk) local eulers for the R side; L mirrors Y/Z
        'relax': ((0, 0, 35), (15, 0, 0)),
        'raise': ((25, 0, -95), (40, 0, 0)),
        'flick': ((20, 0, -72), (-5, 0, 0)),
        'point': ((75, 0, 5), (5, 0, 0)),
        'up': ((10, 0, -125), (20, 0, 0)),
        'shock': ((40, 0, -40), (90, 0, 0)),
    }

    def __init__(self, sc, tex_max=1024):
        self.sc = sc
        self.arm = bpy.data.objects[HOST]
        for o in bpy.data.objects:
            if o.name.lower().startswith(('wgt', 'faceit')) or o.type in ('CAMERA', 'LIGHT'): o.hide_render = True
        for im in bpy.data.images:
            try:
                w, h = im.size
                if max(w, h) > tex_max: s = tex_max / max(w, h); im.scale(max(1, int(w * s)), max(1, int(h * s)))
            except Exception as e: print('scale fail', im.name, e)
        if self.arm.animation_data: self.arm.animation_data.action = None
        self.pb = self.arm.pose.bones
        for sd in ('L', 'R'):
            p = self.pb[f'upper_arm_parent.{sd}']; p['IK_FK'] = 1.0; p.keyframe_insert('["IK_FK"]', frame=1)
        bpy.context.view_layer.update()
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render and
                  (o.parent == self.arm or any(m.type == 'ARMATURE' and m.object == self.arm for m in o.modifiers))]
        dg = bpy.context.evaluated_depsgraph_get()
        low = min((o.matrix_world @ Vector(c)).z for o in meshes for c in o.evaluated_get(dg).bound_box)
        self.root = bpy.data.objects.new('WitchRoot', None); sc.collection.objects.link(self.root)
        self.arm.location.z -= low
        bpy.context.view_layer.update()
        mw = self.arm.matrix_world.copy(); self.arm.parent = self.root; self.arm.matrix_world = mw
        head_z = (self.arm.matrix_world @ self.pb['head'].head).z
        self.scale = 1.55 / head_z
        self.root.scale = (self.scale,) * 3
        bpy.context.view_layer.update()
        print('WITCH scale', round(self.scale, 4))

    def point(self, bone, at=0.0):
        """World position along a bone (0 = head, 1 = tail)."""
        b = self.pb[bone]; M = self.arm.matrix_world
        return (M @ b.head).lerp(M @ b.tail, at)

    def _rot(self, bone, f, deg):
        b = self.pb[bone]; b.rotation_mode = 'XYZ'
        b.rotation_euler = tuple(R(v) for v in deg); b.keyframe_insert('rotation_euler', frame=f)

    def arm_pose(self, f, side, name, wobble=None):
        ua, fa = self.POSE[name]
        if wobble: ua = tuple(a + b for a, b in zip(ua, wobble))
        if side == 'L': ua = (ua[0], -ua[1], -ua[2]); fa = (fa[0], -fa[1], -fa[2])
        self._rot(f'upper_arm_fk.{side}', f, ua); self._rot(f'forearm_fk.{side}', f, fa)

    def breathe(self, f0, f1, period=30):
        t = self.pb['torso']
        for f in range(f0, f1 + 1, period // 2):
            t.scale = (1, 1 + (0.005 if (f // (period // 2)) % 2 else 0), 1); t.keyframe_insert('scale', frame=f)

    def alive(self, f0, f1, seed=1, amount=1.0):
        """Weight shift, chest sway and arm drift layered on top of the keyed poses (F-curve noise)."""
        def base(bone):
            b = self.pb[bone]
            if b.rotation_mode != 'XYZ': b.rotation_mode = 'XYZ'
            if not (self.arm.animation_data and self.arm.animation_data.action and
                    self.arm.animation_data.action.fcurves.find(f'pose.bones["{bone}"].rotation_euler')):
                b.rotation_euler = (0, 0, 0); b.keyframe_insert('rotation_euler', frame=f0)
            b.keyframe_insert('location', frame=f0)
        spec = {  # bone: (rotation strength rad, location strength, noise scale frames)
            'torso': (.035, .012 / self.scale, 40), 'chest': (.05, 0, 28), 'hips': (.04, 0, 34),
            'upper_arm_fk.L': (.08, 0, 22), 'upper_arm_fk.R': (.06, 0, 24),
            'forearm_fk.L': (.1, 0, 18), 'forearm_fk.R': (.08, 0, 20),
        }
        for bone in spec:
            if bone in self.pb: base(bone)
        act = self.arm.animation_data.action
        for i, (bone, (rs, ls, sc_)) in enumerate(spec.items()):
            for path, st in (('rotation_euler', rs), ('location', ls)):
                if not st: continue
                for ax in range(3):
                    fc = act.fcurves.find(f'pose.bones["{bone}"].{path}', index=ax)
                    if not fc: continue
                    m = fc.modifiers.new('NOISE'); m.scale = sc_; m.strength = st * amount * (1 if ax != 1 or path == 'location' else .5)
                    m.phase = seed * 31.7 + i * 7.3 + ax * 3.1; m.blend_type = 'ADD'
                    m.use_restricted_range = True; m.frame_start = f0; m.frame_end = f1; m.blend_in = 5; m.blend_out = 5

    def gesture(self, f, side='L', size=1.0):
        """A quick beat gesture: forearm lifts and settles back over ~10 frames."""
        fa = f'forearm_fk.{side}'
        b = self.pb[fa]; act = self.arm.animation_data.action
        fc = [act.fcurves.find(f'pose.bones["{fa}"].rotation_euler', index=i) for i in range(3)]
        cur = tuple(c.evaluate(f) if c else 0 for c in fc)
        for df, k in ((0, 0), (3, 1), (6, .6), (10, 0)):
            b.rotation_euler = (cur[0] + math.radians(28 * size * k), cur[1], cur[2]); b.keyframe_insert('rotation_euler', frame=f + df)

    def wand(self, glow_mat):
        wood = mat('WandWood', (0.09, 0.05, 0.03), 0.45)
        w = prim('cylinder', 'Wand', wood, radius=0.011, depth=0.42, vertices=12)
        tip = prim('ico_sphere', 'WandTip', glow_mat, radius=0.022, subdivisions=2, location=(0, 0, 0.215))
        tip.parent = w
        bone = 'DEF-hand.R' if 'DEF-hand.R' in self.arm.data.bones else 'hand_fk.R'
        w.parent = self.arm; w.parent_type = 'BONE'; w.parent_bone = bone
        w.matrix_parent_inverse = Matrix.Identity(4)
        s = self.scale
        w.location = (0.0, -0.03 / s, 0.02 / s); w.rotation_euler = (R(-90), 0, 0); w.scale = (1 / s,) * 3
        return w, tip


# ------------------------------------------------------------------ world
class World:
    """Several HDRIs chained through mix shaders; `go(f, name)` crossfades to one."""

    def __init__(self, sc, hdri_dir, looks):
        """looks: [(name, file, strength, saturation, rotation_deg)] in chain order."""
        w = bpy.data.worlds.new('Stage'); sc.world = w; w.use_nodes = True
        nt = w.node_tree; nt.nodes.clear(); self.nt = nt
        out = nt.nodes.new('ShaderNodeOutputWorld')
        tc = nt.nodes.new('ShaderNodeTexCoord')
        self.fac, self.order, prev = {}, [], None
        for i, (name, fname, strength, sat, rot) in enumerate(looks):
            mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, R(rot))
            env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(os.path.join(hdri_dir, fname))
            hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = sat
            bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = strength
            nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
            nt.links.new(env.outputs['Color'], hs.inputs['Color']); nt.links.new(hs.outputs['Color'], bg.inputs['Color'])
            if prev is None: prev = bg.outputs['Background']
            else:
                mix = nt.nodes.new('ShaderNodeMixShader'); mix.inputs['Fac'].default_value = 0
                nt.links.new(prev, mix.inputs[1]); nt.links.new(bg.outputs['Background'], mix.inputs[2])
                self.fac[name] = mix.inputs['Fac']; prev = mix.outputs['Shader']
            self.order.append(name)
        nt.links.new(prev, out.inputs['Surface'])
        self.state = {n: 0.0 for n in self.fac}

    def go(self, f, name, ramp=6):
        """Crossfade so `name` fully shows from frame f (starting at f - ramp)."""
        k = self.order.index(name)
        target = {n: (1.0 if n == name else (0.0 if self.order.index(n) > k else self.state[n])) for n in self.fac}
        for n, sock in self.fac.items():
            key_socket(sock, max(1, f - ramp), self.state[n]); key_socket(sock, f, target[n])
        self.state = target


# ------------------------------------------------------------------ lights & cameras
def area(name, loc, target, energy, color=(1, 1, 1), size=1.0):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.color = color; l.size = size
    o = bpy.data.objects.new(name, l); bpy.context.scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


def point_light(name, loc, energy, color=(1, 1, 1), radius=0.05):
    l = bpy.data.lights.new(name, 'POINT'); l.energy = energy; l.color = color; l.shadow_soft_size = radius
    o = bpy.data.objects.new(name, l); bpy.context.scene.collection.objects.link(o); o.location = loc
    return o


def light_key(light_obj, f, energy=None, color=None):
    d = light_obj.data
    if energy is not None: d.energy = energy; d.keyframe_insert('energy', frame=f)
    if color is not None: d.color = color; d.keyframe_insert('color', frame=f)


class Cameras:
    """One camera per shot, switched with timeline markers (hard cuts)."""

    def __init__(self, sc):
        self.sc, self.cams = sc, {}

    def shot(self, name, f0, lens=50):
        cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24
        cd.clip_start = 0.05; cd.clip_end = 500
        cam = bpy.data.objects.new(name, cd); self.sc.collection.objects.link(cam)
        m = self.sc.timeline_markers.new(name, frame=f0); m.camera = cam
        if f0 == 1 or self.sc.camera is None: self.sc.camera = cam
        self.cams[name] = cam
        return cam

    @staticmethod
    def move(cam, f, loc, look, lens=None, roll=0.0):
        cam.location = loc
        q = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y')
        cam.rotation_euler = (q @ Quaternion((0, 0, 1), R(roll))).to_euler()
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
        if lens: cam.data.lens = lens; cam.data.keyframe_insert('lens', frame=f)

    @staticmethod
    def shake(cam, f0, f1, strength=0.01, seed=0):
        ad = cam.animation_data
        if not ad or not ad.action: return
        for fc in ad.action.fcurves:
            if fc.data_path not in ('location', 'rotation_euler'): continue
            m = fc.modifiers.new('NOISE'); m.scale = 1.5; m.phase = seed * 13.7 + fc.array_index * 5
            m.strength = strength if fc.data_path == 'location' else strength * 0.08
            m.use_restricted_range = True; m.frame_start = f0; m.frame_end = f1; m.blend_in = 2; m.blend_out = 2


# ------------------------------------------------------------------ particles
def particles(name, emitter, f0, f1, count, inst, lifetime, vel=(0, 0, 0), gravity=1.0, size=1.0,
              size_random=0.5, align_velocity=False):
    """Instance `inst` from `emitter` (whose own render is turned off)."""
    ps_mod = emitter.modifiers.new(name, 'PARTICLE_SYSTEM'); ps = ps_mod.particle_system.settings
    ps.count = count; ps.frame_start = f0; ps.frame_end = f1; ps.lifetime = lifetime; ps.lifetime_random = 0.2
    ps.emit_from = 'VOLUME' if emitter.type == 'MESH' and len(emitter.data.polygons) > 6 else 'FACE'
    ps.normal_factor = 0.0; ps.object_align_factor = vel; ps.factor_random = 0.05
    ps.effector_weights.gravity = gravity
    ps.render_type = 'OBJECT'; ps.instance_object = inst; ps.particle_size = size; ps.size_random = size_random
    ps.use_rotations = bool(align_velocity)
    if align_velocity: ps.rotation_mode = 'VEL'; ps.angular_velocity_mode = 'NONE'
    emitter.show_instancer_for_render = False; emitter.show_instancer_for_viewport = False
    pc = ps_mod.particle_system.point_cache; pc.frame_start = min(f0, 1) - 1; pc.frame_end = max(f1 + lifetime, 1)
    inst.location = (0, 0, -1000)
    return ps


def bake_particles(f0, f1):
    """Simulate every particle system once so any chunk of frames renders identically."""
    for o in bpy.data.objects:
        for psys in getattr(o, 'particle_systems', []):
            pc = psys.point_cache; pc.frame_start = min(pc.frame_start, f0); pc.frame_end = max(pc.frame_end, f1)
    ctx = bpy.context.copy()
    with bpy.context.temp_override(**ctx):
        bpy.ops.ptcache.bake_all(bake=True)


def render_setup(sc, out, res=(540, 960), spp=16, fps=15):
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.samples = spp; sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 6; sc.cycles.transmission_bounces = 6; sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.fps = fps
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = os.path.join(out, 'f_')
    sc.render.use_persistent_data = True
