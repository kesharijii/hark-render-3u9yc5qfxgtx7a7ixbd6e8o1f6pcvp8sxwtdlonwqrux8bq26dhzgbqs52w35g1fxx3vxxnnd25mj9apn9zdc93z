"""Mai rig test: decimate the static sculpt, give her a skeleton with proximity weights, render test poses.

blender -b any.blend -P render/shorts/mai_rig.py -- OUTDIR ASSETDIR START END   (DRY=comma frames)
Frames: 1 rest | 10 head turn + chest twist | 20 right arm wave | 30 hip shift + knee bend | 40 hand-on-hip lean
"""
import math, os, sys, urllib.request
import bpy, numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
OUT, AD, START, END = a[0], a[1], int(a[2]), int(a[3])
SPP = int(os.environ.get('SPP', '16'))
MID = os.environ.get('MODEL_ID', '1JNeHus64mfC2aKMwj3s_WwZZBBnmi17Z')
os.makedirs(OUT, exist_ok=True)
glb = os.path.join(AD, f'model_{MID}.glb'); hdr = os.path.join(AD, 'studio_small_09_2k.hdr')
if not os.path.exists(glb): urllib.request.urlretrieve(f'https://drive.usercontent.google.com/download?id={MID}&export=download&confirm=t', glb)
if not os.path.exists(hdr): urllib.request.urlretrieve('https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/studio_small_09_2k.hdr', hdr)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=glb)
body = [o for o in sc.objects if o.type == 'MESH'][0]
# bake all transforms into the mesh, then fit: feet on floor, 1.7 m tall
for o in list(sc.objects):
    if o is not body and o.type == 'EMPTY': pass
mw = body.matrix_world.copy(); body.parent = None; body.matrix_world = mw
bpy.context.view_layer.objects.active = body; body.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(sc.objects):
    if o is not body: bpy.data.objects.remove(o)
V = np.empty(len(body.data.vertices) * 3); body.data.vertices.foreach_get('co', V); V = V.reshape(-1, 3)
s = 1.7 / (V[:, 2].max() - V[:, 2].min()); V[:, 2] -= V[:, 2].min(); V *= s
body.data.vertices.foreach_set('co', V.ravel()); body.data.update()
dec = body.modifiers.new('Dec', 'DECIMATE'); dec.ratio = float(os.environ.get('DEC', '.15'))
bpy.ops.object.modifier_apply(modifier='Dec')
body.data.shade_smooth()
print('MODEL verts after decimate', len(body.data.vertices))

# ------------------------------------------------ skeleton (joints measured from horizontal slices of the sculpt)
J = {
    'hips': ((-.08, -.04, .90), (-.08, -.04, 1.04)),
    'spine': ((-.08, -.04, 1.04), (-.075, -.04, 1.20)),
    'chest': ((-.075, -.04, 1.20), (-.07, -.03, 1.36)),
    'neck': ((-.07, -.03, 1.36), (-.05, -.03, 1.46)),
    'head': ((-.05, -.03, 1.46), (-.04, -.03, 1.70)),
    'shoulder.R': ((-.10, -.03, 1.33), (-.20, -.03, 1.31)),
    'upper_arm.R': ((-.20, -.03, 1.31), (-.195, -.02, 1.04)),
    'forearm.R': ((-.195, -.02, 1.04), (-.17, -.04, .86)),
    'hand.R': ((-.17, -.04, .86), (-.16, -.05, .78)),
    'shoulder.L': ((-.04, -.03, 1.33), (.06, -.03, 1.31)),
    'upper_arm.L': ((.06, -.03, 1.31), (.17, -.02, 1.04)),
    'forearm.L': ((.17, -.02, 1.04), (.15, -.03, .84)),
    'hand.L': ((.15, -.03, .84), (.14, -.04, .76)),
    'thigh.R': ((-.20, -.05, .88), (-.22, -.07, .47)),
    'shin.R': ((-.22, -.07, .47), (-.276, -.07, .10)),
    'foot.R': ((-.276, -.07, .10), (-.29, -.17, .02)),
    'thigh.L': ((.03, -.05, .88), (.11, -.07, .47)),
    'shin.L': ((.11, -.07, .47), (.088, -.07, .10)),
    'foot.L': ((.088, -.07, .10), (.09, -.17, .02)),
}
PARENT = {'spine': 'hips', 'chest': 'spine', 'neck': 'chest', 'head': 'neck',
          'shoulder.R': 'chest', 'upper_arm.R': 'shoulder.R', 'forearm.R': 'upper_arm.R', 'hand.R': 'forearm.R',
          'shoulder.L': 'chest', 'upper_arm.L': 'shoulder.L', 'forearm.L': 'upper_arm.L', 'hand.L': 'forearm.L',
          'thigh.R': 'hips', 'shin.R': 'thigh.R', 'foot.R': 'shin.R', 'thigh.L': 'hips', 'shin.L': 'thigh.L', 'foot.L': 'shin.L'}
ad = bpy.data.armatures.new('MaiRig'); arm = bpy.data.objects.new('MaiRig', ad); sc.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
for n, (h, t) in J.items():
    e = ad.edit_bones.new(n); e.head, e.tail = h, t
for n, p in PARENT.items():
    ad.edit_bones[n].parent = ad.edit_bones[p]; ad.edit_bones[n].use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')

# proximity weights: distance to each bone segment, sharp falloff, only bones close to the nearest one
V = np.empty(len(body.data.vertices) * 3); body.data.vertices.foreach_get('co', V); V = V.reshape(-1, 3)
names = list(J); D = np.empty((len(V), len(names)))
for i, n in enumerate(names):
    h, t = np.array(J[n][0]), np.array(J[n][1]); d = t - h
    u = np.clip(((V - h) @ d) / (d @ d), 0, 1)
    D[:, i] = np.linalg.norm(V - (h + u[:, None] * d), axis=1)
dmin = D.min(1, keepdims=True)
Wt = np.where(D <= dmin * 1.35 + .012, (1.0 / (D + .01)) ** 4, 0.0)
# the head bone owns the hair above the neck; the hips own the skirt core
Wt /= Wt.sum(1, keepdims=True)
for i, n in enumerate(names):
    g = body.vertex_groups.new(name=n)
    idx = np.nonzero(Wt[:, i] > .01)[0]
    for k in idx: g.add([int(k)], float(Wt[k, i]), 'REPLACE')
mod = body.modifiers.new('Arm', 'ARMATURE'); mod.object = arm; body.parent = arm
print('MODEL rigged bones', len(names))

# smooth the weights a little so joints bend instead of crease
bpy.context.view_layer.objects.active = body
for g in body.vertex_groups:
    body.vertex_groups.active_index = g.index
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT'); bpy.ops.object.vertex_group_smooth(group_select_mode='ACTIVE', factor=.5, repeat=3); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.vertex_group_normalize_all(lock_active=False)

# ------------------------------------------------ test poses
pb = arm.pose.bones
for b in pb: b.rotation_mode = 'XYZ'
def pose(f, rots):
    for b in pb:
        r = rots.get(b.name, (0, 0, 0)); b.rotation_euler = tuple(math.radians(x) for x in r); b.keyframe_insert('rotation_euler', frame=f)
    arm.location = rots.get('_loc', (0, 0, 0)); arm.keyframe_insert('location', frame=f)
pose(1, {})
pose(10, {'head': (0, 0, 25), 'neck': (0, 0, 10), 'chest': (0, 0, 12)})
pose(20, {'upper_arm.R': (0, 0, -95), 'forearm.R': (0, 0, -40), 'head': (0, 0, -10)})
pose(30, {'hips': (0, 4, 0), 'thigh.L': (-25, 0, 0), 'shin.L': (40, 0, 0), 'chest': (0, -3, 0), '_loc': (0, 0, -.02)})
pose(40, {'chest': (6, 8, -10), 'head': (-8, 10, 12), 'upper_arm.L': (0, 0, 30), 'forearm.L': (0, 0, 30)})

# ------------------------------------------------ studio (same look as the turntable)
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
nt = w.node_tree; bg = nt.nodes['Background']
env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(hdr)
nt.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = .35
lp = nt.nodes.new('ShaderNodeLightPath'); mix = nt.nodes.new('ShaderNodeMixShader'); dark = nt.nodes.new('ShaderNodeBackground')
dark.inputs['Color'].default_value = (.012, .01, .016, 1)
nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0]); nt.links.new(bg.outputs[0], mix.inputs[1]); nt.links.new(dark.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], nt.nodes['World Output'].inputs['Surface'])
def area(name, loc, energy, color, size):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = energy; d.color = color; d.size = size
    o = bpy.data.objects.new(name, d); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 1.1)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
area('Key', (-1.8, -2.4, 2.6), 380, (1, .93, .88), 1.6); area('Fill', (2.2, -1.8, 1.2), 90, (.8, .86, 1), 2.0)
area('RimL', (-1.6, 2.0, 2.2), 320, (1, .45, .35), .8); area('RimR', (1.7, 2.0, 2.0), 260, (.6, .7, 1), .8)
cam_d = bpy.data.cameras.new('Cam'); cam_d.lens = 50
cam = bpy.data.objects.new('Cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (-.08, -3.3, 1.1); cam.rotation_euler = (math.radians(89), 0, 0)
r = sc.render; r.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SPP; sc.cycles.use_denoising = True
r.resolution_x, r.resolution_y = 540, 960; r.image_settings.file_format = 'PNG'; r.filepath = os.path.join(OUT, 'f_####')
sc.view_settings.view_transform = 'AgX'
sc.frame_start, sc.frame_end = START, END
if os.environ.get('DRY'):
    r.resolution_x, r.resolution_y = 360, 640; sc.cycles.samples = 12
    for fr in [int(x) for x in os.environ['DRY'].split(',')]:
        sc.frame_set(fr); r.filepath = os.path.join(OUT, f'dry_{fr:04d}.png'); bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
print('DONE')
