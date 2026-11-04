"""Open a user .blend (from Drive), export GLB, render iso/top/side/front clay previews.
blender -b any.blend -P render/shorts/blend_preview.py -- OUTDIR ASSETDIR START END   (MODEL_ID env = Drive id)
"""
import math, os, sys, urllib.request
import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
OUT, AD = a[0], a[1]
MID = os.environ.get('MODEL_ID', '1dFQ9mb-L74zzdyLgHWkhnLQ_IgwlNXE5')
os.makedirs(OUT, exist_ok=True)
src = os.path.join(AD, f'user_{MID}.blend')
if not os.path.exists(src): urllib.request.urlretrieve(f'https://drive.usercontent.google.com/download?id={MID}&export=download&confirm=t', src)
bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
meshes = [o for o in sc.objects if o.type == 'MESH' and o.visible_get()]
print('MODEL objects', [(o.name, o.type, len(o.data.vertices) if o.type == 'MESH' else 0) for o in sc.objects])
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'model.glb'), export_format='GLB', use_selection=True, export_apply=True)
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
c = (lo + hi) / 2; R = (hi - lo).length / 2
print('MODEL bbox', tuple(round(v, 3) for v in lo), tuple(round(v, 3) for v in hi))
# clean studio
for o in list(sc.objects):
    if o.type in ('LIGHT', 'CAMERA'): bpy.data.objects.remove(o)
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (.03, .035, .045, 1)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 1
def sun(rot, e):
    d = bpy.data.lights.new('S', 'SUN'); d.energy = e; d.angle = .2
    o = bpy.data.objects.new('S', d); sc.collection.objects.link(o); o.rotation_euler = [math.radians(x) for x in rot]
sun((50, 0, 30), 3.5); sun((70, 0, 210), 1.2); sun((120, 0, 90), .8)
cd = bpy.data.cameras.new('C'); cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
r = sc.render; r.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 32; sc.cycles.use_denoising = True; r.resolution_x, r.resolution_y = 1280, 900
r.image_settings.file_format = 'PNG'; sc.view_settings.view_transform = 'AgX'
r.film_transparent = False
views = {'iso': Vector((1, -1.2, .8)), 'top': Vector((0, 0, 1)), 'side': Vector((1, 0, 0)), 'front': Vector((0, -1, 0))}
for name, d in views.items():
    d = d.normalized()
    if name == 'iso':
        cd.type = 'PERSP'; cd.lens = 50; cam.location = c + d * R * 3.2
    else:
        cd.type = 'ORTHO'; cd.ortho_scale = R * 2.15; cam.location = c + d * R * 4
    up = Vector((0, 1, 0)) if name == 'top' else Vector((0, 0, 1))
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y' if name != 'top' else 'Y').to_euler()
    if name == 'top': cam.rotation_euler = (0, 0, 0)
    cd.clip_end = R * 20
    r.filepath = os.path.join(OUT, f'view_{name}.png'); bpy.ops.render.render(write_still=True)
print('DONE')
