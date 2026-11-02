# Host test: 5-second idle/wave/blink/talk clip of the rigged host character.
# Usage: blender -b host.blend -P host_test.py -- OUTDIR HDRI START END [inspect]
import bpy, sys, math, os, re
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, HDRI, START, END = argv[0], argv[1], int(argv[2]), int(argv[3])
INSPECT = len(argv) > 4
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene

# ---------- inspect ----------
arm = None
for o in bpy.data.objects:
    if o.type == 'ARMATURE' and len(o.data.bones) > 50 and not o.name.lower().startswith('faceit'):
        if arm is None or len(o.data.bones) > len(arm.data.bones):
            arm = o
print("ARMATURE:", arm and arm.name, arm and len(arm.data.bones))
for o in bpy.data.objects:
    sk = o.data.shape_keys.key_blocks.keys() if o.type == 'MESH' and o.data.shape_keys else []
    print("OBJ", o.type, repr(o.name), "hide_render=", o.hide_render, "verts=", len(o.data.vertices) if o.type == 'MESH' else '', "sk=", len(sk), list(sk)[:60])
if arm:
    names = [b.name for b in arm.pose.bones]
    print("BONES", [n for n in names if not n.startswith(('ORG', 'DEF', 'MCH'))][:400])
    for pb in arm.pose.bones:
        if 'IK_FK' in pb.keys():
            print("IKFK", pb.name, pb['IK_FK'])
for im in bpy.data.images:
    print("IMG", im.name, tuple(im.size))

# hide helper rigs and widget objects
for o in bpy.data.objects:
    if o.name.lower().startswith(('faceit', 'wgt')):
        o.hide_render = True

# ---------- textures: cap at 2048 ----------
for im in bpy.data.images:
    try:
        w, h = im.size
        if max(w, h) > 2048:
            s = 2048 / max(w, h)
            im.scale(max(1, int(w * s)), max(1, int(h * s)))
    except Exception as e:
        print("scale fail", im.name, e)

# ---------- helpers ----------
def pb(*cands):
    if not arm: return None
    for c in cands:
        if c in arm.pose.bones: return arm.pose.bones[c]
    return None

def key_rot(bone, frame, euler):
    if not bone: return
    bone.rotation_mode = 'XYZ'
    bone.rotation_euler = euler
    bone.keyframe_insert('rotation_euler', frame=frame)

MODE = os.environ.get('MODE', 'wave')
SECS = int(os.environ.get('SECS', '5'))
FPS = 15
sc.render.fps = FPS
F0, F1 = 1, SECS * FPS
if MODE == 'full':
    for o in bpy.data.objects:
        if o.name in ('hat', 'Corset', 'top'):
            o.hide_render = True; o.hide_viewport = True
sc.frame_start, sc.frame_end = F0, F1

if arm:
    # put arms in FK so we can pose them directly
    for side in ('L', 'R'):
        p = pb(f'upper_arm_parent.{side}')
        if p and 'IK_FK' in p.keys():
            p['IK_FK'] = 1.0
            p.keyframe_insert('["IK_FK"]', frame=F0)
    # clear any existing action so only our motion plays
    if arm.animation_data: arm.animation_data.action = None

    head = pb('head'); neck = pb('neck'); chest = pb('chest'); torso = pb('torso')
    ua = pb('upper_arm_fk.R'); fa = pb('forearm_fk.R'); hand = pb('hand_fk.R')
    ual = pb('upper_arm_fk.L'); fal = pb('forearm_fk.L')
    # relaxed arms down from A-pose
    for f in (F0, F1):
        key_rot(ual, f, (0, 0, math.radians(-25)))
        key_rot(fal, f, (math.radians(15), 0, 0))
    # head: look, tilt, look at camera
    for f, e in ((F0, (0, 0, 0)), (20, (0, math.radians(12), math.radians(5))), (45, (math.radians(-4), math.radians(-6), math.radians(-4))), (F1, (0, 0, 0))):
        key_rot(head, f, e)
    for f, e in ((F0, (0, 0, 0)), (38, (math.radians(2), math.radians(4), 0)), (F1, (0, 0, 0))):
        key_rot(chest, f, e)
    if MODE == 'full':
        for f in (F0, F1):
            key_rot(ua, f, (0, 0, math.radians(25)))
            key_rot(fa, f, (math.radians(15), 0, 0))
        # slow weight shift / sway
        for f in range(F0, F1 + 1, 45):
            key_rot(torso, f, (0, math.radians(3 if (f // 45) % 2 else -3), 0))
    else:
        up = (math.radians(-10), 0, math.radians(70))
        for f, e in ((F0, (0, 0, math.radians(25))), (14, up), (F1 - 8, up), (F1, (0, 0, math.radians(25)))):
            key_rot(ua, f, e)
        for f in range(F0, F1 + 1, 5):
            waving = 14 <= f <= F1 - 8
            key_rot(fa, f, (math.radians(-90 if waving else -15), 0, math.radians((25 if (f // 5) % 2 else -10) if waving else 0)))
    # breathing
    if torso:
        for f in range(F0, F1 + 1, 15):
            torso.scale = (1, 1.0 + (0.004 if (f // 15) % 2 else 0), 1)
            torso.keyframe_insert('scale', frame=f)

# shape keys: blink + talk
def sk_find(keys, *pats):
    for k in keys:
        if any(re.search(p, k.name, re.I) for p in pats):
            yield k

for o in bpy.data.objects:
    if o.type != 'MESH' or not o.data.shape_keys: continue
    kb = o.data.shape_keys.key_blocks
    for k in sk_find(kb, r'blink', r'eyes?_?close'):
        for f, v in ((F0, 0), (17, 0), (19, 1), (21, 0), (52, 0), (54, 1), (56, 0), (F1, 0)):
            k.value = v; k.keyframe_insert('value', frame=f)
    for k in sk_find(kb, r'^jawopen$', r'mouth_?open', r'^jaw_open'):
        for f in range(F0, F1 + 1, 2):
            talking = 24 <= f <= 60
            k.value = (0.35 if (f // 2) % 2 else 0.08) if talking else 0
            k.keyframe_insert('value', frame=f)
    for k in sk_find(kb, r'smile'):
        for f, v in ((F0, 0.2), (12, 0.6), (F1, 0.5)):
            k.value = v; k.keyframe_insert('value', frame=f)


# ---------- outfit swap: fit an external bikini onto the body ----------
BIKINI = os.environ.get('BIKINI', '')
if BIKINI and os.path.exists(BIKINI) and arm:
    for o in bpy.data.objects:
        if o.name in ('hat', 'Corset', 'top', 'skirt') or (o.name == 'bra' and os.environ.get('BIKINI_PARTS', 'all') == 'all'):
            o.hide_render = True; o.hide_viewport = True
    body = bpy.data.objects['chubby_body']
    with bpy.data.libraries.load(BIKINI, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n == os.environ.get('BIKINI_OBJ', 'Classic_Halter_Neck_Bikini_Set')]
    bk = dst.objects[0]; sc.collection.objects.link(bk)
    bk.parent = None; bk.hide_render = False; bk.hide_viewport = False
    for m in list(bk.modifiers): bk.modifiers.remove(m)
    arm.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    mw = bk.matrix_world.copy()
    for v in bk.data.vertices: v.co = mw @ v.co
    bk.matrix_world = Matrix.Identity(4)
    # split loose parts into top / bottom by height
    import bmesh
    bm = bmesh.new(); bm.from_mesh(bk.data); bm.verts.ensure_lookup_table()
    seen = set(); parts = []
    for v in bm.verts:
        if v.index in seen: continue
        stack = [v]; comp = []; seen.add(v.index)
        while stack:
            x = stack.pop(); comp.append(x.index)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen: seen.add(y.index); stack.append(y)
        parts.append(comp)
    zs = [v.co.z for v in bm.verts]; zmid = (min(zs) + max(zs)) / 2
    def cen(ids): 
        c = Vector(); 
        for i in ids: c += bm.verts[i].co
        return c / len(ids)
    top_ids = [i for p in parts if cen(p).z > zmid for i in p]
    bot_ids = [i for p in parts if cen(p).z <= zmid for i in p]
    print('BIKINI parts', len(parts), 'top verts', len(top_ids), 'bottom verts', len(bot_ids))
    def bone(n, tail=False):
        b = arm.data.bones.get(n)
        return (arm.matrix_world @ (b.tail_local if tail else b.head_local)) if b else None
    # breast centre = between head (chest wall) and tail (tip) of each breast bone
    bL = (bone('ORG-breast.L') + bone('ORG-breast.L', True)) / 2
    bR = (bone('ORG-breast.R') + bone('ORG-breast.R', True)) / 2
    chest = (bL + bR) / 2
    hip = (bone('ORG-thigh.L') + bone('ORG-thigh.R')) / 2
    hip.z += 0.02 * (bone('ORG-spine.003') - hip).length if bone('ORG-spine.003') else 0
    top_parts = sorted([p for p in parts if cen(p).z > zmid], key=len, reverse=True)
    cups = top_parts[:2]
    c1, c2 = cen(cups[0]), cen(cups[1])
    cup_mid = (c1 + c2) / 2
    s_top = ((bL - bR).length / max(1e-4, (c1 - c2).length)) * 1.18
    tc, bc = cen(top_ids), cen(bot_ids)
    s_bot = (chest.z - hip.z) / max(1e-4, (tc.z - bc.z)) * 1.06
    print('FIT chest', chest, 'hip', hip, 's_top', s_top, 's_bot', s_bot)
    for i in top_ids:
        co = (bm.verts[i].co - cup_mid) * s_top
        co.x *= 1.08; co.y *= 1.15
        bm.verts[i].co = chest + co
    for i in bot_ids:
        co = (bm.verts[i].co - bc) * s_bot
        co.x *= 1.1; co.y *= 1.1
        bm.verts[i].co = hip + co
    s_ = max(s_top, s_bot)
    if os.environ.get('BIKINI_PARTS', 'all') == 'bottom':
        bmesh.ops.delete(bm, geom=[bm.verts[i] for i in top_ids], context='VERTS')
    bm.to_mesh(bk.data); bm.free()
    def apply(mod):
        with bpy.context.temp_override(object=bk, active_object=bk, selected_objects=[bk], selected_editable_objects=[bk]):
            bpy.ops.object.modifier_apply(modifier=mod.name)
    sw = bk.modifiers.new('SW', 'SHRINKWRAP'); sw.target = body; sw.wrap_method = 'NEAREST_SURFACEPOINT'
    sw.wrap_mode = 'OUTSIDE_SURFACE'; sw.offset = 0.004 * max(1.0, s_)
    apply(sw)
    sm = bk.modifiers.new('SM', 'CORRECTIVE_SMOOTH'); sm.iterations = 4; apply(sm)
    sw = bk.modifiers.new('SW2', 'SHRINKWRAP'); sw.target = body; sw.wrap_method = 'NEAREST_SURFACEPOINT'
    sw.wrap_mode = 'OUTSIDE'; sw.offset = 0.003 * max(1.0, s_); apply(sw)
    sol = bk.modifiers.new('SOL', 'SOLIDIFY'); sol.thickness = 0.002; sol.offset = 1
    dt = bk.modifiers.new('DT', 'DATA_TRANSFER'); dt.object = body
    dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'POLYINTERP_NEAREST'
    with bpy.context.temp_override(object=bk, active_object=bk, selected_objects=[bk], selected_editable_objects=[bk]):
        bpy.ops.object.datalayout_transfer(modifier='DT')
    apply(dt)
    am = bk.modifiers.new('ARM', 'ARMATURE'); am.object = arm
    arm.data.pose_position = 'POSE'
    print('BIKINI fitted, vgroups', len(bk.vertex_groups))

# ---------- ground ----------
_low = 1e9
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type == 'MESH' and not o.hide_render and not o.name.startswith('WGT'):
        e = o.evaluated_get(dg)
        for c in e.bound_box: _low = min(_low, (o.matrix_world @ Vector(c)).z)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, _low))
deck = bpy.context.active_object; deck.name = 'Deck'; deck.scale = (3, 30, 1)
dm = bpy.data.materials.new('DeckWood'); dm.use_nodes = True
bsdf = dm.node_tree.nodes['Principled BSDF']
wave = dm.node_tree.nodes.new('ShaderNodeTexWave'); wave.wave_type = 'BANDS'; wave.inputs['Scale'].default_value = 6; wave.inputs['Distortion'].default_value = 3
ramp = dm.node_tree.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.18, 0.11, 0.06, 1); ramp.color_ramp.elements[1].color = (0.38, 0.25, 0.14, 1)
dm.node_tree.links.new(wave.outputs['Fac'], ramp.inputs['Fac']); dm.node_tree.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
bsdf.inputs['Roughness'].default_value = 0.7
deck.data.materials.append(dm)
print('GROUND at', _low)

# ---------- camera ----------
target = None
if arm and pb('head'):
    target = arm.matrix_world @ pb('head').head
else:
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render]
    top = max((o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box)
    target = Vector((0, 0, top * 0.88))
print("HEAD AT", target)
height = max(target.z, 0.5)
cam_data = bpy.data.cameras.new('HostCam'); cam_data.lens = 50
cam_data.dof.use_dof = True; cam_data.dof.aperture_fstop = 2.8
cam = bpy.data.objects.new('HostCam', cam_data); sc.collection.objects.link(cam)
look = target - Vector((0, 0, height * 0.22))  # head to waist framing
dist = height * 1.15
# figure out which way she faces: Rigify/most models face -Y
cam.location = look + Vector((dist * 0.25, -dist, height * 0.03))
cam.rotation_euler = (look - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam_data.dof.focus_distance = (target - cam.location).length
cam.keyframe_insert('location', frame=F0)
cam.location += Vector((0, dist * 0.06, 0)); cam.keyframe_insert('location', frame=F1)  # slow push-in
sc.camera = cam
if MODE == 'full':
    cam.animation_data_clear()
    cam_data.lens = 40
    piv = bpy.data.objects.new('Orbit', None); sc.collection.objects.link(piv)
    mid = Vector((target.x, target.y, height * 0.5))
    piv.location = mid
    d = height * 1.9
    cam.parent = piv
    cam.location = Vector((0, -d, height * 0.02))
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam_data.dof.focus_distance = d
    cam_data.dof.aperture_fstop = 4.0
    piv.rotation_euler = (0, 0, 0); piv.keyframe_insert('rotation_euler', frame=F0)
    piv.rotation_euler = (0, 0, math.radians(360)); piv.keyframe_insert('rotation_euler', frame=F1 + 1)
    for fc in piv.animation_data.action.fcurves:
        for k in fc.keyframe_points: k.interpolation = 'LINEAR'

# ---------- light: golden-hour HDRI + warm key + rim ----------
w = bpy.data.worlds.new('Golden'); sc.world = w; w.use_nodes = True
nt = w.node_tree; nt.nodes.clear()
env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(HDRI)
mp = nt.nodes.new('ShaderNodeMapping'); tc = nt.nodes.new('ShaderNodeTexCoord')
mp.inputs['Rotation'].default_value = (0, 0, math.radians(200))
bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 1.0
out = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
nt.links.new(env.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
def area(name, loc, energy, color, size):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.color = color; l.size = size
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (target - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
area('Key', target + Vector((-height * 0.9, -height * 0.9, height * 0.35)), 250 * height, (1.0, 0.82, 0.62), height * 0.6)
area('Rim', target + Vector((height * 0.8, height * 0.9, height * 0.4)), 300 * height, (1.0, 0.7, 0.45), height * 0.4)
area('Fill', target + Vector((height * 1.0, -height * 0.8, 0)), 60 * height, (0.75, 0.85, 1.0), height * 0.8)
if MODE == 'full':
    piv = bpy.data.objects['Orbit']
    for n in ('Key', 'Rim', 'Fill'):
        L = bpy.data.objects[n]; L.parent = piv; L.matrix_parent_inverse = piv.matrix_world.inverted()

# ---------- render settings ----------
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get('SPP', '32'))
sc.cycles.use_denoising = True
sc.cycles.denoiser = 'OPENIMAGEDENOISE'
sc.cycles.max_bounces = 6
sc.render.resolution_x, sc.render.resolution_y = 540, 960
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Medium High Contrast'
sc.render.film_transparent = False
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = os.path.join(OUT, 'f_')

if INSPECT:
    sc.frame_set(30)
    sc.render.filepath = os.path.join(OUT, 'still.png')
    bpy.ops.render.render(write_still=True)
else:
    sc.frame_start, sc.frame_end = max(F0, START), min(F1, END)
    bpy.ops.render.render(animation=True)
