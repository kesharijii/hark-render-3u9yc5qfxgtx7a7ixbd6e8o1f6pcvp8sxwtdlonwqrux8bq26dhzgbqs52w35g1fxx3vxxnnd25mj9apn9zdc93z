# Face test: stills of each expression + a lip-synced close-up.
# blender -b host.blend -P face_test.py -- OUTDIR HDRI WAV MODE(stills|clip)
import bpy, sys, os, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.face import Face

OUT, HDRI, WAV, MODE = sys.argv[sys.argv.index('--') + 1:][:4]
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; FPS = 15; sc.render.fps = FPS
ARM = bpy.data.objects['magic girl  pbr_Rigify']
if ARM.animation_data: ARM.animation_data.action = None
for o in bpy.data.objects:
    if o.type in ('CAMERA', 'LIGHT') or o.name.lower().startswith(('wgt', 'faceit')): o.hide_render = True
for im in bpy.data.images:
    try:
        w, h = im.size
        if max(w, h) > 2048: s = 2048 / max(w, h); im.scale(int(w * s), int(h * s))
    except Exception: pass

face = Face(ARM)
pb = ARM.pose.bones
# tip the hat brim out of the eyes: tilt head up a touch
for n in ('neck', 'head'):
    if n in pb: pb[n].rotation_mode = 'XYZ'

w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(HDRI)
bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 0.8
o_ = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(env.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], o_.inputs['Surface'])
key = bpy.data.lights.new('K', 'AREA'); key.energy = 60; key.size = 0.6; key.color = (1, 0.85, 0.9)
kl = bpy.data.objects.new('K', key); sc.collection.objects.link(kl)
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = int(os.environ.get('SPP', '16')); sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 640
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'

bpy.context.view_layer.update()
H = ARM.matrix_world @ pb['head'].head; T = ARM.matrix_world @ pb['head'].tail
L = (T - H).length
mouth = H + (T - H) * 0.25 + Vector((0, -0.08 * L / 0.267, 0))
eyes = H + (T - H) * 0.55
target = mouth * 0.5 + eyes * 0.5
cd = bpy.data.cameras.new('C'); cd.lens = 70; cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = target + Vector((0.25, -1.0, -0.38)).normalized() * L * 5.2   # low: under the brim
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
kl.location = target + Vector((-0.8, -1.0, 0.1)) * L * 4
kl.rotation_euler = (target - kl.location).to_track_quat('-Z', 'Y').to_euler()

if MODE == 'stills':
    looks = ['neutral', 'smug', 'menace', 'delight', 'surprise', 'annoyed', 'sultry', 'pout', 'tease']
    for i, name in enumerate(looks): face.express(10 + i * 10, name)
    # visemes on top of neutral, after the expressions
    vf = 10 + len(looks) * 10
    face.express(vf - 5, 'neutral')
    for k, (ch, jaw) in enumerate((('vis_wide', .45), ('vis_round', .45), ('vis_press', 0))):
        face._dense(ch, vf + k * 10, 1.0); face._dense('jaw', vf + k * 10, jaw)
    face.bake(1, vf + 30, sway=False)
    shots = [(10 + i * 10, n) for i, n in enumerate(looks)] + [(vf + k * 10, n) for k, n in enumerate(('ee', 'oo', 'mm'))]
    for i, (f, name) in enumerate(shots):
        sc.frame_set(f)
        sc.render.filepath = os.path.join(OUT, f'{i:02d}_{name}.png'); bpy.ops.render.render(write_still=True)
else:
    face.express(1, 'sultry'); face.express(20, 'menace'); face.express(45, 'smug')
    n = face.speak(WAV, 8, FPS)
    face.express(n + 8, 'tease')
    face.blinks(1, n + 18, FPS)
    face.bake(1, n + 18)
    sc.frame_start, sc.frame_end = 1, n + 18
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = os.path.join(OUT, 'f_')
    bpy.ops.render.render(animation=True)
print('DONE')
