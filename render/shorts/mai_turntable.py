"""Studio turntable for a static (unrigged) model hosted on Drive.

blender -b any.blend -P render/shorts/mai_turntable.py -- OUTDIR ASSETDIR START END
MODEL_ID env = Drive file id of the .glb. 150 frames at 15 fps = one 360 spin in 10 s.
"""
import math, os, sys, urllib.request
import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
OUT, AD, START, END = a[0], a[1], int(a[2]), int(a[3])
SPP = int(os.environ.get('SPP', '16')); NFR = 150
MID = os.environ.get('MODEL_ID', '1JNeHus64mfC2aKMwj3s_WwZZBBnmi17Z')
os.makedirs(OUT, exist_ok=True)
glb = os.path.join(AD, f'model_{MID}.glb')
if not os.path.exists(glb):
    urllib.request.urlretrieve(f'https://drive.usercontent.google.com/download?id={MID}&export=download&confirm=t', glb)
hdr = os.path.join(AD, 'studio_small_09_2k.hdr')
if not os.path.exists(hdr):
    urllib.request.urlretrieve('https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/studio_small_09_2k.hdr', hdr)

# ------------------------------------------------ clean stage
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in sc.objects if o.type == 'MESH']
print('MODEL meshes', len(meshes), [len(o.data.vertices) for o in meshes])
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
print('MODEL bbox', tuple(round(v, 3) for v in lo), tuple(round(v, 3) for v in hi))
H = 1.7; s = H / (hi.z - lo.z)
spin = bpy.data.objects.new('Spin', None); sc.collection.objects.link(spin)
root = bpy.data.objects.new('Fit', None); sc.collection.objects.link(root)
root.parent = spin; root.scale = (s, s, s)
root.location = (-(lo.x + hi.x) / 2 * s, -(lo.y + hi.y) / 2 * s, -lo.z * s)
for o in sc.objects:
    if o.parent is None and o not in (spin, root): o.parent = root
for o in meshes:
    for m in o.data.materials:
        if m and m.use_nodes:
            b = m.node_tree.nodes.get('Principled BSDF')
            if b:
                b.inputs['Roughness'].default_value = .55
                b.inputs['Specular IOR Level'].default_value = .35
    o.data.shade_smooth() if hasattr(o.data, 'shade_smooth') else None
for f, ang in ((1, 0), (NFR + 1, 2 * math.pi)):
    spin.rotation_euler = (0, 0, ang); spin.keyframe_insert('rotation_euler', frame=f)
for fc in spin.animation_data.action.fcurves:
    for k in fc.keyframe_points: k.interpolation = 'LINEAR'

# ------------------------------------------------ studio
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
nt = w.node_tree; bg = nt.nodes['Background']
env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(hdr)
nt.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = .35
lp = nt.nodes.new('ShaderNodeLightPath'); mix = nt.nodes.new('ShaderNodeMixShader'); dark = nt.nodes.new('ShaderNodeBackground')
dark.inputs['Color'].default_value = (.012, .01, .016, 1)
out = nt.nodes['World Output']
nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0]); nt.links.new(bg.outputs[0], mix.inputs[1]); nt.links.new(dark.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], out.inputs['Surface'])

floor_m = bpy.data.materials.new('Floor'); floor_m.use_nodes = True
fb = floor_m.node_tree.nodes['Principled BSDF']; fb.inputs['Base Color'].default_value = (.006, .005, .007, 1); fb.inputs['Roughness'].default_value = .4
bpy.ops.mesh.primitive_cylinder_add(radius=.75, depth=.06, vertices=96, location=(0, 0, -.03)); bpy.context.object.data.materials.append(floor_m)
ring_m = bpy.data.materials.new('Ring'); ring_m.use_nodes = True
rb = ring_m.node_tree.nodes['Principled BSDF']; rb.inputs['Emission Color'].default_value = (1, .2, .15, 1); rb.inputs['Emission Strength'].default_value = 6
bpy.ops.mesh.primitive_torus_add(major_radius=.75, minor_radius=.008, location=(0, 0, 0)); bpy.context.object.data.materials.append(ring_m)

def area(name, loc, energy, color, size):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = energy; d.color = color; d.size = size
    o = bpy.data.objects.new(name, d); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 1.1)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
area('Key', (-1.8, -2.4, 2.6), 380, (1, .93, .88), 1.6)
area('Fill', (2.2, -1.8, 1.2), 90, (.8, .86, 1), 2.0)
area('RimL', (-1.6, 2.0, 2.2), 320, (1, .45, .35), .8)
area('RimR', (1.7, 2.0, 2.0), 260, (.6, .7, 1), .8)

cam_d = bpy.data.cameras.new('Cam'); cam_d.lens = 50; cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 4
cam = bpy.data.objects.new('Cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
tgt = bpy.data.objects.new('Tgt', None); sc.collection.objects.link(tgt)
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam_d.dof.focus_object = tgt
for f, loc, t in ((1, (0, -3.3, 1.15), (0, 0, .9)), (NFR, (0, -2.75, 1.2), (0, 0, .95))):   # slow push in while she spins
    cam.location = loc; cam.keyframe_insert('location', frame=f); tgt.location = t; tgt.keyframe_insert('location', frame=f)

r = sc.render; r.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SPP; sc.cycles.use_denoising = True
r.resolution_x, r.resolution_y, r.resolution_percentage = 540, 960, 100
r.image_settings.file_format = 'PNG'; r.filepath = os.path.join(OUT, 'f_####')
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.render.fps = 15
sc.frame_start, sc.frame_end = START, min(END, NFR)
print('RENDER', START, min(END, NFR))
if os.environ.get('DRY'):
    r.resolution_x, r.resolution_y = 270, 480; sc.cycles.samples = 8
    for fr in [int(x) for x in os.environ['DRY'].split(',')]:
        sc.frame_set(fr); r.filepath = os.path.join(OUT, f'dry_{fr:04d}.png'); bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
print('DONE')
