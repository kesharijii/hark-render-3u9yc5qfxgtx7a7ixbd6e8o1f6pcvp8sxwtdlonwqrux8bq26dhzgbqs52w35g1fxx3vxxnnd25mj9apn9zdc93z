# Face probe: what can drive lip sync / expressions on the host?
# blender -b host.blend -P face_probe.py -- OUTDIR HDRI
import bpy, sys, os, math
from mathutils import Vector
OUT, HDRI = sys.argv[sys.argv.index('--') + 1:][:2]
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
ARM = bpy.data.objects['magic girl  pbr_Rigify']
head = ARM.pose.bones['head']
hz = ARM.matrix_world @ head.head; ht = ARM.matrix_world @ head.tail
print('HEAD', tuple(round(v, 3) for v in hz), tuple(round(v, 3) for v in ht))

print('BONES_ALL', len(ARM.data.bones))
print('FACEBONES', [b.name for b in ARM.data.bones if any(k in b.name.lower() for k in
      ('jaw', 'eye', 'lid', 'lip', 'mouth', 'brow', 'teeth', 'tongue', 'face', 'chin', 'cheek', 'nose', 'ear'))])
print('HEADKIDS', [b.name for b in ARM.data.bones['head'].children_recursive][:60] if 'head' in ARM.data.bones else None)

r = (ht - hz).length * 1.3
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    sk = [k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else []
    mw = o.matrix_world
    near = sum(1 for v in o.data.vertices if ((mw @ v.co) - (hz + ht) / 2).length < r)
    vgs = [g.name for g in o.vertex_groups]
    hv = [g for g in vgs if any(k in g.lower() for k in ('head', 'jaw', 'eye', 'lid', 'lip', 'mouth', 'brow'))]
    print('MESH', repr(o.name), 'verts', len(o.data.vertices), 'nearHead', near, 'hide_r', o.hide_render,
          'mats', [m.name for m in o.data.materials if m], 'sk', sk[:40], 'headVG', hv)
for m in bpy.data.materials:
    if m.use_nodes:
        ims = [n.image.name + f' {n.image.size[0]}x{n.image.size[1]}' for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
        print('MAT', repr(m.name), ims)
print('DRIVERS', [(o.name, len(o.animation_data.drivers)) for o in bpy.data.objects if o.animation_data and o.animation_data.drivers])

# close-ups
for o in bpy.data.objects:
    if o.type in ('CAMERA', 'LIGHT') or o.name.lower().startswith(('wgt', 'faceit')): o.hide_render = True
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(HDRI)
bg = nt.nodes.new('ShaderNodeBackground'); o_ = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(env.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], o_.inputs['Surface'])
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 768
sc.view_settings.view_transform = 'AgX'
c = (hz + ht) / 2
cd = bpy.data.cameras.new('C'); cd.lens = 85; cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
L = (ht - hz).length
# figure out which way she faces: Rigify faces -Y
for name, off in (('front', Vector((0, -1, 0.05))), ('three_q', Vector((0.6, -0.8, 0.1))), ('side', Vector((1, 0, 0.05)))):
    cam.location = c + off.normalized() * L * 6
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, f'face_{name}.png'); bpy.ops.render.render(write_still=True)
print('DONE')
