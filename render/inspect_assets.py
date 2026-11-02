# Asset inspection: cat rig/actions/fur still, and witch arm-axis test stills.
# blender -b FILE -P inspect_assets.py -- OUTDIR HDRI cat|witch
import bpy, sys, os, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
OUT, HDRI, WHAT = a[0], a[1], a[2]
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene

def world(strength=1.0):
    w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(HDRI)
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = strength
    o = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], o.inputs['Surface'])

def setup(res=(540, 960), spp=16):
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = spp
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'AgX'
    sc.render.image_settings.file_format = 'PNG'

def cam_at(target, dist, height, lens=50, side=0.3):
    cd = bpy.data.cameras.new('C'); cd.lens = lens
    c = bpy.data.objects.new('C', cd); sc.collection.objects.link(c)
    c.location = target + Vector((dist * side, -dist, height))
    c.rotation_euler = (target - c.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = c
    return c

def bbox_all(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi

if WHAT == 'cat':
    print('SCENE fps', sc.render.fps, 'frames', sc.frame_start, sc.frame_end, 'engine', sc.render.engine)
    for o in bpy.data.objects:
        ps = [(p.name, p.settings.type, p.settings.count, p.settings.hair_length, p.settings.render_type) for p in getattr(o, 'particle_systems', [])] if o.type == 'MESH' else []
        mods = [(m.type, m.name) for m in o.modifiers] if hasattr(o, 'modifiers') else []
        print('OBJ', o.type, repr(o.name), 'parent=', o.parent and o.parent.name, 'hide_r=', o.hide_render, 'dim=', tuple(round(x, 3) for x in o.dimensions), 'loc=', tuple(round(x, 3) for x in o.location), 'mods=', mods, 'ps=', ps,
              'action=', o.animation_data.action.name if o.animation_data and o.animation_data.action else None)
    for ac in bpy.data.actions:
        print('ACTION', repr(ac.name), 'range', tuple(ac.frame_range), 'users', ac.users, 'fcurves', len(ac.fcurves))
    for ob in bpy.data.objects:
        if ob.type == 'ARMATURE':
            print('BONES', ob.name, [(b.name, b.parent.name if b.parent else None) for b in ob.data.bones])
            if ob.animation_data:
                print('NLA', [(t.name, [s.name for s in t.strips]) for t in ob.animation_data.nla_tracks])
    for m in bpy.data.materials:
        print('MAT', m.name, 'nodes' if m.use_nodes else 'no-nodes', [n.type for n in m.node_tree.nodes] if m.use_nodes else '')
    world(1.0)
    setup(spp=24)
    for n in ('Plane', 'Empty'):
        if n in bpy.data.objects: bpy.data.objects[n].hide_render = True
    catm = bpy.data.objects['Cat']
    for p in catm.particle_systems:
        st = p.settings
        print('PSET', p.name, 'child', st.child_type, st.rendered_child_count, 'steps', st.render_step, 'mat', st.material_slot, 'shape', st.root_radius if hasattr(st,'root_radius') else '')
    lo, hi = bbox_all([catm])
    c = (lo + hi) / 2; size = max(hi - lo)
    print('CAT bbox', lo, hi)
    arm = bpy.data.objects['Armature']
    cam_at(c, size * 1.3, size * 0.1, lens=50, side=0.9)
    for act, f in (('Walk', 1), ('Walk', 14), ('run', 8)):
        arm.animation_data.action = bpy.data.actions[act]
        sc.frame_set(f)
        sc.render.filepath = os.path.join(OUT, f'cat_{act}_{f}.png')
        bpy.ops.render.render(write_still=True)
    # head turn test
    arm.animation_data.action = None
    pb = arm.pose.bones
    for b in pb: b.rotation_mode = 'XYZ'
    for name, bn, rot in (('head_x30', 'Head', (30,0,0)), ('head_z30', 'Head', (0,0,30)), ('ear_x40', 'Ear', (40,0,0))):
        for b in pb: b.rotation_euler = (0,0,0)
        pb[bn].rotation_euler = tuple(math.radians(v) for v in rot)
        if bn == 'Ear': pb['Ear.006'].rotation_euler = tuple(math.radians(v) for v in rot)
        sc.frame_set(1)
        sc.render.filepath = os.path.join(OUT, f'cat_{name}.png')
        bpy.ops.render.render(write_still=True)

if WHAT == 'witch':
    arm = bpy.data.objects['magic girl  pbr_Rigify']
    for o in bpy.data.objects:
        if o.name.lower().startswith(('wgt', 'faceit')): o.hide_render = True
    for im in bpy.data.images:
        w, h = im.size
        if max(w, h) > 1024:
            s = 1024 / max(w, h); im.scale(max(1, int(w * s)), max(1, int(h * s)))
    pb = arm.pose.bones
    for sd in ('L', 'R'):
        pb[f'upper_arm_parent.{sd}']['IK_FK'] = 1.0
    world(1.0); setup(res=(360, 640), spp=8)
    head = arm.matrix_world @ pb['head'].head
    mid = Vector((head.x, head.y, head.z * 0.62))
    cam_at(mid, head.z * 1.5, 0, lens=40, side=0.0)
    tests = [('rest', None, None),
             ('ua_x+70', 'upper_arm_fk.R', (70, 0, 0)), ('ua_x-70', 'upper_arm_fk.R', (-70, 0, 0)),
             ('ua_y+70', 'upper_arm_fk.R', (0, 70, 0)), ('ua_z+70', 'upper_arm_fk.R', (0, 0, 70)), ('ua_z-70', 'upper_arm_fk.R', (0, 0, -70)),
             ('fa_x+80', 'forearm_fk.R', (80, 0, 0)), ('fa_x-80', 'forearm_fk.R', (-80, 0, 0)), ('fa_z+80', 'forearm_fk.R', (0, 0, 80))]
    for name, bn, rot in tests:
        for b in ('upper_arm_fk.R', 'forearm_fk.R'):
            pb[b].rotation_mode = 'XYZ'; pb[b].rotation_euler = (0, 0, 0)
        if bn:
            pb[bn].rotation_euler = tuple(math.radians(v) for v in rot)
        bpy.context.view_layer.update()
        hand = arm.matrix_world @ pb['hand_fk.R'].head
        print('TEST', name, 'hand_R at', tuple(round(v, 3) for v in hand))
        sc.render.filepath = os.path.join(OUT, f'witch_{name}.png')
        bpy.ops.render.render(write_still=True)
