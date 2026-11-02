# Witch + giant cat episode renderer.
# blender -b witch.blend -P episode.py -- OUTDIR ASSETDIR SHOT START END
# ASSETDIR holds cat.blend and the HDRIs. Frames are global (15 fps); output f_####.png.
import bpy, sys, os, math, random
from mathutils import Vector, Euler, Matrix, Quaternion

a = sys.argv[sys.argv.index('--') + 1:]
OUT, AD, SHOT, START, END = a[0], a[1], a[2], int(a[3]), int(a[4])
SPP = int(os.environ.get('SPP', '16'))
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
sc.render.fps = 15
R = math.radians
random.seed(7)

SHOTS = {  # name: (first, last, hdri, world strength)
    'S1': (1, 52, 'small_harbour_sunset', 1.0),
    'S2': (53, 150, 'small_harbour_sunset', 1.0),
    'S3': (151, 270, 'small_harbour_sunset', 1.0),
    'S4a': (271, 345, 'golden_bay', 1.6),
    'S4b': (346, 420, 'victoria_sunset', 1.0),
    'S5': (421, 570, 'small_harbour_sunset', 1.0),
    'S6': (571, 720, 'victoria_sunset', 1.0),
    'S7': (721, 810, 'small_harbour_sunset', 1.0),
}
F0, F1, HDRI, WSTR = SHOTS[SHOT]

# ---------------- witch ----------------
W = bpy.data.objects['magic girl  pbr_Rigify']
for o in bpy.data.objects:
    if o.name.lower().startswith(('wgt', 'faceit')): o.hide_render = True
    if o.type == 'CAMERA' or o.type == 'LIGHT': o.hide_render = True
for im in bpy.data.images:
    try:
        w, h = im.size
        if max(w, h) > 1024:
            s = 1024 / max(w, h); im.scale(max(1, int(w * s)), max(1, int(h * s)))
    except Exception as e: print('scale fail', im.name, e)
if W.animation_data: W.animation_data.action = None
WP = W.pose.bones
for sd in ('L', 'R'):
    WP[f'upper_arm_parent.{sd}']['IK_FK'] = 1.0
    WP[f'upper_arm_parent.{sd}'].keyframe_insert('["IK_FK"]', frame=1)
bpy.context.view_layer.update()

def low_z(objs):
    dg = bpy.context.evaluated_depsgraph_get(); lo = 1e9
    for o in objs:
        e = o.evaluated_get(dg)
        for c in e.bound_box: lo = min(lo, (o.matrix_world @ Vector(c)).z)
    return lo
wmesh = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render and (o.parent == W or any(m.type == 'ARMATURE' and m.object == W for m in o.modifiers))]
wl = low_z(wmesh)
WR = bpy.data.objects.new('WitchRoot', None); sc.collection.objects.link(WR)
W.location.z -= wl
bpy.context.view_layer.update()
mw = W.matrix_world.copy(); W.parent = WR; W.matrix_world = mw
HEADZ = (W.matrix_world @ WP['head'].head).z
WS = 1.55 / HEADZ
WR.scale = (WS, WS, WS)
print('WITCH low', wl, 'head z', HEADZ, 'scale', WS)

def wkey(bone, f, deg):
    b = WP[bone]; b.rotation_mode = 'XYZ'; b.rotation_euler = tuple(R(v) for v in deg)
    b.keyframe_insert('rotation_euler', frame=f)

def armspace_q(pbone, deg):
    q = Euler(tuple(R(v) for v in deg), 'XYZ').to_quaternion()
    B = pbone.bone.matrix_local.to_quaternion()
    return B.inverted() @ q @ B

def key_arm_rot(pbone, f, deg):
    ql = armspace_q(pbone, deg)
    if pbone.rotation_mode == 'QUATERNION':
        pbone.rotation_quaternion = ql; pbone.keyframe_insert('rotation_quaternion', frame=f)
    elif pbone.rotation_mode == 'AXIS_ANGLE':
        pbone.rotation_mode = 'QUATERNION'; pbone.rotation_quaternion = ql; pbone.keyframe_insert('rotation_quaternion', frame=f)
    else:
        pbone.rotation_euler = ql.to_euler(pbone.rotation_mode); pbone.keyframe_insert('rotation_euler', frame=f)

def whead(f, deg): key_arm_rot(WP['head'], f, deg)

POSE = {  # (upper_arm_fk, forearm_fk) local eulers, R side; L mirrors Z/Y
    'relax': ((0, 0, 35), (15, 0, 0)),
    'raise': ((25, 0, -95), (40, 0, 0)),
    'flick': ((20, 0, -72), (-5, 0, 0)),
    'point': ((75, 0, 5), (5, 0, 0)),
    'up': ((10, 0, -125), (20, 0, 0)),
    'shock': ((40, 0, -40), (90, 0, 0)),
}
def warm(f, side, name):
    ua, fa = POSE[name]
    if side == 'L': ua = (ua[0], -ua[1], -ua[2]); fa = (fa[0], -fa[1], -fa[2])
    wkey(f'upper_arm_fk.{side}', f, ua); wkey(f'forearm_fk.{side}', f, fa)
def wboth(f, name): warm(f, 'R', name); warm(f, 'L', name)
def breathe(f0, f1):
    t = WP['torso']
    for f in range(f0, f1 + 1, 15):
        t.scale = (1, 1 + (0.004 if (f // 15) % 2 else 0), 1); t.keyframe_insert('scale', frame=f)

# wand in right hand
def mat(name, col, rough=0.5, emit=None, strength=0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = strength
    return m
wood = mat('WandWood', (0.09, 0.05, 0.03), 0.45)
glow = mat('Glow', (1, 0.8, 0.4), 0.3, (1.0, 0.75, 0.35), 25)
def make_wand(name):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.011, depth=0.42, vertices=12)
    wd = bpy.context.active_object; wd.name = name; wd.data.materials.append(wood)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.022, subdivisions=2, location=(0, 0, 0.215))
    tip = bpy.context.active_object; tip.name = name + 'Tip'; tip.data.materials.append(glow)
    tip.parent = wd
    return wd, tip
wand, wtip = make_wand('Wand')
wand.parent = W; wand.parent_type = 'BONE'; wand.parent_bone = 'DEF-hand.R' if 'DEF-hand.R' in W.data.bones else 'hand_fk.R'
wand.matrix_parent_inverse = Matrix.Identity(4)
wand.location = (0.0, -0.03 / WS, 0.02 / WS); wand.rotation_euler = (R(-90), 0, 0); wand.scale = (1 / WS,) * 3

def sparkle(parent, f0, f1, count, size, vel, life=18, loc=(0, 0, 0)):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=size, subdivisions=1)
    star = bpy.context.active_object; star.name = 'Star'; star.data.materials.append(glow)
    star.location = (0, 0, -500); star.hide_render = False
    bpy.ops.mesh.primitive_ico_sphere_add(radius=max(size * 4, 0.02), subdivisions=1)
    em = bpy.context.active_object; em.name = 'Emitter'; em.parent = parent; em.location = loc
    em.hide_render = True
    ps = em.modifiers.new('P', 'PARTICLE_SYSTEM').particle_system.settings
    ps.count = count; ps.frame_start = f0; ps.frame_end = f1; ps.lifetime = life; ps.lifetime_random = 0.6
    ps.normal_factor = vel; ps.factor_random = vel * 0.8; ps.effector_weights.gravity = 0.05
    ps.render_type = 'OBJECT'; ps.instance_object = star; ps.particle_size = 1.0; ps.size_random = 0.7
    em.show_instancer_for_render = False
    return em

# ---------------- cat ----------------
with bpy.data.libraries.load(os.path.join(AD, 'cat.blend'), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n in ('Armature', 'Cat', 'Sphere', 'Sphere.001')]
    dst.actions = [n for n in src.actions if n in ('Walk', 'run')]
cat_objs = {o.name.split('.0')[0] if o.name.startswith('Armature') else o.name: o for o in dst.objects}
CA = next(o for o in dst.objects if o.type == 'ARMATURE')
CM = next(o for o in dst.objects if o.type == 'MESH' and o.particle_systems)
for o in dst.objects: sc.collection.objects.link(o)
WALK = next(x for x in dst.actions if x.name.startswith('Walk'))
CR = bpy.data.objects.new('CatRoot', None); sc.collection.objects.link(CR)
bpy.context.view_layer.update()
mw = CA.matrix_world.copy(); CA.parent = CR; CA.matrix_world = mw
CP = CA.pose.bones
CAT_FOOT = 2.886  # model units from origin to paw bottom
CAT_LEN = 10.0

def hold_action(srcact, f, name):
    act = bpy.data.actions.new(name)
    for fc in srcact.fcurves:
        n = act.fcurves.new(fc.data_path, index=fc.array_index)
        n.keyframe_points.insert(1, fc.evaluate(f))
    return act
HOLD = hold_action(WALK, 1, 'CatHold')
ad = CA.animation_data or CA.animation_data_create()
for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
ad.action = None

def cat_base(kind, f0, f1, speed=1.0):
    tr = ad.nla_tracks.new()
    if kind == 'walk':
        st = tr.strips.new('walk', f0 - 30, WALK)
        st.scale = 0.625 * speed
        cyc = (WALK.frame_range[1] - WALK.frame_range[0]) * st.scale
        st.repeat = max(1.0, (f1 - f0 + 60) / max(cyc, 1))
    else:
        st = tr.strips.new('hold', f0 - 30, HOLD)
        st.action_frame_start, st.action_frame_end = 1, 2
        st.scale = 1; st.repeat = max(1.0, (f1 - f0 + 60))
    st.extrapolation = 'HOLD'
    return st

def cat_extras():
    ad.action_blend_type = 'COMBINE'

def ckey(bone, f, deg):
    key_arm_rot(CP[bone], f, deg); ad.action_blend_type = 'COMBINE'

def ckey_loc(bone, f, delta_arm):
    pb = CP[bone]
    B = pb.bone.matrix_local.to_3x3()
    pb.location = B.inverted() @ Vector(delta_arm)
    pb.keyframe_insert('location', frame=f); ad.action_blend_type = 'COMBINE'

def cat_place(f, x, y, s, yaw, sink=0.0):
    CR.location = (x, y, (CAT_FOOT - sink) * s); CR.scale = (s, s, s); CR.rotation_euler = (0, 0, R(yaw))
    for p in ('location', 'scale', 'rotation_euler'): CR.keyframe_insert(p, frame=f)

def wplace(f, x, y, yaw=0, z=0):
    WR.location = (x, y, z); WR.rotation_euler = (0, 0, R(yaw))
    WR.keyframe_insert('location', frame=f); WR.keyframe_insert('rotation_euler', frame=f)

# ---------------- world / camera / lights ----------------
import numpy as np
wd_ = bpy.data.worlds.new('Sky'); sc.world = wd_; wd_.use_nodes = True
nt = wd_.node_tree; nt.nodes.clear()
env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(os.path.join(AD, HDRI + '.hdr'))
mp = nt.nodes.new('ShaderNodeMapping'); tc = nt.nodes.new('ShaderNodeTexCoord')
bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = WSTR
wo = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
nt.links.new(env.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], wo.inputs['Surface'])

def sun_azimuth():
    im = env.image; w, h = im.size
    px = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(px)
    lum = px.reshape(h, w, 4)[:, :, :3].sum(axis=2)
    lum[: int(h * 0.48)] = 0
    v, u = np.unravel_index(np.argmax(lum), lum.shape)
    phi = (u / w - 0.5) * 2 * math.pi
    img = Vector((-math.cos(phi), math.sin(phi)))
    return math.atan2(img.y, img.x)
def set_sun(theta_deg):
    r = sun_azimuth() - R(theta_deg)
    mp.inputs['Rotation'].default_value = (0, 0, r)

bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
ground = bpy.context.active_object; ground.name = 'ShadowCatcher'; ground.is_shadow_catcher = True

cd = bpy.data.cameras.new('Cam'); cd.lens = 35; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24
cam = bpy.data.objects.new('Cam', cd); sc.collection.objects.link(cam); sc.camera = cam
cd.clip_end = 2000
def camkey(f, loc, look, lens=None):
    cam.location = loc
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
    if lens: cd.lens = lens; cd.keyframe_insert('lens', frame=f)

def shake(f0, f1, strength):
    if not cam.animation_data: return
    for fc in cam.animation_data.action.fcurves:
        if fc.data_path in ('location', 'rotation_euler'):
            m = fc.modifiers.new('NOISE'); m.scale = 1.5
            m.strength = strength if fc.data_path == 'location' else strength * 0.05
            m.phase = random.random() * 100
            m.use_restricted_range = True; m.frame_start = f0; m.frame_end = f1
            m.blend_in = 3; m.blend_out = 3

def area(name, loc, target, energy, color=(1.0, 0.8, 0.6), size=1.0):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.color = color; l.size = size
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o
def key_light(target, d, energy_k=70, side=-1, color=(1.0, 0.8, 0.6)):
    t = Vector(target)
    loc = t + Vector((side * d * 0.7, -d * 0.7, d * 0.35))
    return area('Key', loc, t, energy_k * d * d, color, d * 0.4)

def ease(fc_owner):
    if fc_owner.animation_data and fc_owner.animation_data.action:
        for fc in fc_owner.animation_data.action.fcurves:
            for k in fc.keyframe_points: k.interpolation = 'BEZIER'; k.easing = 'AUTO'

def lin(owner, path=None):
    if owner.animation_data and owner.animation_data.action:
        for fc in owner.animation_data.action.fcurves:
            if path is None or fc.data_path == path:
                for k in fc.keyframe_points: k.interpolation = 'LINEAR'

def bowl(x, y):
    m = mat('Bowl', (0.55, 0.12, 0.1), 0.35)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.09, depth=0.05, location=(x, y, 0.025))
    b = bpy.context.active_object; b.data.materials.append(m)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.09, minor_radius=0.012, location=(x, y, 0.05))
    bpy.context.active_object.data.materials.append(m)

H = 1.55
BIG = 1.2
S_SM = 0.06

# ---------------- shots ----------------
if SHOT == 'S1':
    set_sun(60)
    wplace(F0, 0, 0); wboth(F0, 'relax'); whead(F0, (0, 0, 0)); whead(40, (-6, 0, -8)); whead(F1, (-8, 0, -10))
    breathe(F0, F1)
    cat_base('hold', F0, F1); cat_place(F0, 2.6, 10, BIG, 20)
    ckey('Head', F0, (8, 0, 0)); ckey('Head', F1, (16, 0, -6))
    ckey('Tail', F0, (0, 0, 0)); ckey('Tail', 30, (0, 0, 12)); ckey('Tail', F1, (0, 0, -6))
    camkey(F0, (0.9, -4.8, 0.55), (0.2, 3, 3.0), 22); camkey(F1, (0.75, -4.1, 0.6), (0.2, 3, 3.3), 22)
    key_light((0, 0, H * 0.8), 3.0, side=-1)
    area('CatFill', (8, 0, 8), (2.6, 10, 6), 20000, (1.0, 0.75, 0.5), 6)

elif SHOT == 'S2':
    set_sun(60)
    wplace(F0, 0, 0); breathe(F0, F1)
    wboth(F0, 'relax'); warm(85, 'R', 'relax'); warm(100, 'R', 'raise'); warm(110, 'R', 'raise'); warm(115, 'R', 'flick'); warm(135, 'R', 'flick'); warm(F1, 'R', 'relax')
    whead(F0, (14, 0, -20)); whead(80, (18, 0, -28)); whead(105, (6, 0, -22)); whead(F1, (10, 0, -25))
    cat_base('hold', F0, F1); cat_place(F0, -0.62, -0.35, S_SM, 90)
    ckey('Head', F0, (-20, 0, 0)); ckey('Head', 75, (-28, 0, 8)); ckey('Head', 118, (-32, 0, -4)); ckey('Head', F1, (-25, 0, 0))
    ckey('Tail', F0, (0, 0, 0)); ckey('Tail', 90, (0, 0, 20)); ckey('Tail', F1, (0, 0, -15))
    ckey('Ear', F0, (0, 0, 0)); ckey('Ear', 112, (0, 0, 0)); ckey('Ear', 116, (-25, 0, 0)); ckey('Ear', 125, (0, 0, 0))
    bowl(-0.85, -0.6)
    sparkle(wtip, 112, 122, 260, 0.006, 0.6, life=16)
    camkey(F0, (-1.7, -3.7, 1.05), (-0.35, 0, 0.9), 28); camkey(F1, (-1.4, -3.2, 1.0), (-0.35, 0, 0.95), 28)
    key_light((-0.3, 0, H * 0.7), 2.6, side=-1)

elif SHOT == 'S3':
    set_sun(60)
    wplace(F0, 0, 0); breathe(F0, F1)
    wboth(F0, 'relax'); warm(F0, 'R', 'flick'); warm(200, 'R', 'flick'); warm(215, 'R', 'shock'); warm(215, 'L', 'shock'); warm(F1, 'R', 'shock'); warm(F1, 'L', 'shock')
    whead(F0, (10, 0, -25)); whead(190, (-10, 0, -20)); whead(240, (-32, 0, -12)); whead(F1, (-36, 0, -10))
    cat_base('hold', F0, F1)
    cat_place(F0, -0.62, -0.35, S_SM, 90); cat_place(160, -0.62, -0.35, S_SM, 90)
    cat_place(205, -2.0, 3.0, 0.5, 60); cat_place(245, -2.6, 7.5, BIG, 20); cat_place(F1, -2.6, 7.5, BIG, 20)
    ckey('Head', F0, (-25, 0, 0)); ckey('Head', 230, (-5, 0, 0)); ckey('Head', F1, (18, 0, 8))
    ckey('Tail', F0, (0, 0, 0)); ckey('Tail', 200, (0, 0, 25)); ckey('Tail', F1, (0, 0, -10))
    sparkle(CR, 156, 215, 600, 0.004, 3.0, life=20, loc=(0, 0, 2))
    camkey(F0, (-1.6, -2.9, 0.8), (-0.6, -0.3, 0.5), 30); camkey(175, (-1.6, -3.4, 0.9), (-0.8, 0, 0.9), 30)
    camkey(250, (1.8, -9.5, 1.1), (-1.6, 4, 4.4), 22); camkey(F1, (1.9, -10.0, 1.1), (-1.6, 4, 4.8), 22)
    key_light((0, 0, H * 0.7), 3.0, side=-1)
    area('CatFill', (6, -2, 9), (-2.6, 7.5, 6), 20000, (1.0, 0.75, 0.5), 6)

elif SHOT == 'S4a':
    set_sun(-120)
    cat_base('hold', F0, F1); cat_place(F0, 0, 5, BIG, -8, sink=1.6 * 1)
    for f in range(F0, F1 + 1, 12):
        ckey('Ear', f, (0, 0, 0)); ckey('Ear', f + 3, (-18, 0, 0)) if f + 3 <= F1 else None
    ckey('Head', F0, (5, 0, 0)); ckey('Head', F1, (12, 0, -10))
    wplace(F0, 1.9, -1.5, -25); wboth(F0, 'shock'); whead(F0, (-30, 0, 15)); whead(F1, (-34, 0, 10)); breathe(F0, F1)
    camkey(F0, (-0.6, -9.5, 1.0), (0.3, 3, 4.2), 26); camkey(F1, (-0.4, -8.6, 1.0), (0.3, 3, 4.5), 26)
    shake(F0 + 4, F1, 0.035)
    key_light((0.3, 3, 4), 9, side=-1, color=(1.0, 0.72, 0.45))
    area('Moon', (6, -4, 10), (0, 5, 4), 9000, (0.6, 0.7, 1.0), 6)

elif SHOT == 'S4b':
    set_sun(70)
    cat_base('hold', F0, F1); cat_place(F0, 0, 4, BIG, 90, sink=2.5)
    for f in range(F0, F1 + 1, 30):
        CR.scale = (BIG, BIG, BIG); CR.keyframe_insert('scale', frame=f)
        if f + 15 <= F1: CR.scale = (BIG, BIG, BIG * 1.025); CR.keyframe_insert('scale', frame=f + 15)
    ckey('Head', F0, (28, 0, 15)); ckey('Head', F1, (30, 0, 12))
    ckey('Tail', F0, (0, 0, 0)); ckey('Tail', 380, (0, 0, 18)); ckey('Tail', F1, (0, 0, 0))
    wplace(F0, 2.2, -3.6, -15); wboth(F0, 'relax'); warm(F0, 'R', 'point'); warm(375, 'R', 'point'); warm(390, 'R', 'relax')
    whead(F0, (-22, 0, 20)); whead(F1, (-18, 0, 10)); breathe(F0, F1)
    camkey(F0, (5.5, -14, 1.7), (0.5, 2, 2.4), 26); camkey(F1, (3.0, -13.2, 1.7), (0.3, 2, 2.4), 26)
    key_light((0.5, 3, 2.5), 10, side=-1)

elif SHOT == 'S5':
    set_sun(60)
    wplace(F0, 0, 0, 180); breathe(F0, F1)
    wboth(F0, 'relax'); warm(438, 'R', 'relax'); warm(458, 'R', 'point'); warm(495, 'R', 'point'); warm(512, 'R', 'shock'); warm(512, 'L', 'shock'); warm(F1, 'R', 'shock'); warm(F1, 'L', 'shock')
    whead(F0, (-25, 0, 0)); whead(500, (-30, 0, 0)); whead(530, (-10, 0, -35)); whead(F1, (-6, 0, -45))
    cat_base('hold', F0, F1); cat_place(F0, 1.2, 7.5, BIG, 15)
    ckey('Head', F0, (10, 0, 0)); ckey('Head', 455, (10, 0, 0)); ckey('Head', 485, (32, 0, 6)); ckey('Head', 505, (25, 0, 12))
    ckey('Head', 535, (10, 0, 40)); ckey('Head', F1, (8, 0, 48))
    ckey('Ear', F0, (0, 0, 0)); ckey('Ear', 480, (-20, 0, 0)); ckey('Ear', F1, (-15, 0, 0))
    paw = 'Foot_front_IK_R' if 'Foot_front_IK_R' in CP else None
    if paw:
        ckey_loc(paw, F0, (0, 0, 0)); ckey_loc(paw, 478, (0, 0, 0)); ckey_loc(paw, 492, (0.4, -2.5, 3.0))
        ckey_loc(paw, 500, (2.6, -2.8, 2.6)); ckey_loc(paw, 512, (1.0, -1.0, 1.2)); ckey_loc(paw, 526, (0, 0, 0))
    # wand flies off at 500
    sc.frame_set(500); bpy.context.view_layer.update()
    p0 = wand.matrix_world.translation.copy()
    wand.hide_render = False; wand.keyframe_insert('hide_render', frame=499); wand.hide_render = True; wand.keyframe_insert('hide_render', frame=500)
    wtip.hide_render = False; wtip.keyframe_insert('hide_render', frame=499); wtip.hide_render = True; wtip.keyframe_insert('hide_render', frame=500)
    fw, ft = make_wand('WandFly')
    fw.hide_render = True; fw.keyframe_insert('hide_render', frame=499); fw.hide_render = False; fw.keyframe_insert('hide_render', frame=500)
    ft.hide_render = True; ft.keyframe_insert('hide_render', frame=499); ft.hide_render = False; ft.keyframe_insert('hide_render', frame=500)
    end = Vector((-14, 22, -0.5))
    for i, f in enumerate(range(500, 546, 3)):
        t = i / 15
        pos = p0.lerp(end, t); pos.z = p0.z + 9 * t - 9.5 * t * t
        fw.location = pos; fw.rotation_euler = (R(720 * t), R(300 * t), 0)
        fw.keyframe_insert('location', frame=f); fw.keyframe_insert('rotation_euler', frame=f)
    sparkle(ft, 500, 540, 200, 0.005, 0.2, life=10)
    camkey(F0, (3.6, -4.2, 1.3), (0.4, 4, 3.0), 22); camkey(500, (3.2, -3.6, 1.3), (0.4, 4, 3.2), 22)
    camkey(F1, (2.6, -3.4, 1.4), (-2.5, 6, 2.6), 22)
    key_light((0, 0, H * 0.8), 3.0, side=1)
    area('CatFill', (7, 1, 9), (1.2, 7.5, 6), 22000, (1.0, 0.75, 0.5), 6)

elif SHOT in ('S6', 'S7'):
    set_sun(60 if SHOT == 'S7' else 100)
    WR.location = (300, 300, 0)
    if SHOT == 'S6':
        x0, x1 = -22.0, 18.0
        cat_base('walk', F0, F1, speed=1.6)
        cat_place(F0, x0, 4, BIG, 90); cat_place(F1, x1, 4, BIG, 90); lin(CR)
    else:
        cat_base('hold', F0, F1); cat_place(F0, 0, 6, BIG, 0)
        ckey('Head', F0, (5, 0, 0)); ckey('Head', 745, (5, 0, 0)); ckey('Head', 765, (-6, 0, 42)); ckey('Head', F1, (-8, 0, 46))
        ckey('Ear', F0, (0, 0, 0)); ckey('Ear', 760, (0, 0, 0)); ckey('Ear', 768, (-28, 0, 0)); ckey('Ear', F1, (-30, 0, 0))
        ckey('Ear.006', F0, (0, 0, 0)); ckey('Ear.006', 760, (0, 0, 0)); ckey('Ear.006', 768, (-28, 0, 0)); ckey('Ear.006', F1, (-30, 0, 0))
        ckey('Tail', F0, (0, 0, 0)); ckey('Tail', 770, (-35, 0, 0)); ckey('Tail', 785, (-30, 0, 15)); ckey('Tail', F1, (-35, 0, -12))
    sc.frame_set(F0); bpy.context.view_layer.update()
    hb = CP['Head']; hm = CA.matrix_world
    hc = (hm @ hb.head + hm @ hb.tail) / 2
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, nrm, idx, ob, _m = sc.ray_cast(dg, hc + Vector((0, 0, 60)), Vector((0, 0, -1)))
    top = loc if hit else hc + Vector((0, 0, 0.8 * BIG))
    print('HEAD TOP', hit, ob and ob.name, top)
    WR.animation_data_clear()
    WR.parent = CA; WR.parent_type = 'BONE'; WR.parent_bone = 'Head'
    bpy.context.view_layer.update()
    WR.matrix_world = Matrix.Translation(top - Vector((0, 0, 0.03))) @ Euler((0, 0, R(-20 if SHOT == 'S6' else 10))).to_matrix().to_4x4() @ Matrix.Scale(WS, 4)
    breathe(F0, F1)
    if SHOT == 'S6':
        wboth(F0, 'relax'); wboth(590, 'up'); wboth(620, 'up'); wboth(640, 'relax'); warm(665, 'R', 'up'); warm(700, 'R', 'up'); warm(F1, 'R', 'relax')
        whead(F0, (-5, 0, 10)); whead(640, (-10, 0, -15)); whead(F1, (-8, 0, 20))
        camkey(F0, (x0 + 5.5, -13.5, 6.0), (x0 + 5.0, 2, 10.0), 30)
        camkey(F1, (x1 + 5.0, -12.0, 6.0), (x1 + 5.0, 2, 10.4), 30); lin(cam)
        kl = key_light((x0 + 5, 2, 10), 12, side=-1)
        sc.frame_set(F0); bpy.context.view_layer.update()
        kl.parent = cam; kl.matrix_parent_inverse = cam.matrix_world.inverted()
    else:
        wboth(F0, 'relax'); wboth(762, 'relax'); wboth(774, 'shock'); wboth(790, 'up'); wboth(F1, 'up')
        whead(F0, (-5, 0, 0)); whead(762, (0, 0, 30)); whead(F1, (-15, 0, 35))
        camkey(F0, (2.5, -9.0, 6.0), (0, 0, 9.5), 28); camkey(F1, (2.0, -7.6, 6.3), (0, 0, 9.8), 28)
        shake(785, F1, 0.02)
        key_light((0, 1, 9.5), 9, side=-1)

# ---------------- render ----------------
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = SPP; sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
sc.cycles.max_bounces = 6
sc.render.resolution_x, sc.render.resolution_y = 540, 960; sc.render.resolution_percentage = 100
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.render.film_transparent = False
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = os.path.join(OUT, 'f_')
sc.frame_start, sc.frame_end = max(F0, START), min(F1, END)
sc.render.use_persistent_data = True
print('RENDER', SHOT, sc.frame_start, sc.frame_end)
if os.environ.get('DRY'):
    sc.render.resolution_x, sc.render.resolution_y = 270, 480; sc.cycles.samples = 4
    for k, fr in enumerate(os.environ['DRY'].split(',')):
        fr = int(fr) if fr != 'mid' else (F0 + F1) // 2
        sc.frame_set(fr); sc.render.filepath = os.path.join(OUT, f'dry_{SHOT}_{fr:04d}.png')
        bpy.ops.render.render(write_still=True)
elif os.environ.get('STILL'):
    sc.frame_set(int(os.environ['STILL'])); sc.render.filepath = os.path.join(OUT, f'still_{SHOT}.png')
    bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
