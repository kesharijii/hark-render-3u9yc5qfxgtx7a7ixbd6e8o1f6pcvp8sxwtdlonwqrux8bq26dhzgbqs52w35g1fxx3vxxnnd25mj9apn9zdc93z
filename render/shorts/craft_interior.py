"""Interior + exterior engineering pass on the user's Tripo3D spacecraft_concept.glb.
blender -b any.blend -P render/shorts/craft_interior.py -- OUTDIR ASSETDIR START END
DRY (env) non-empty -> stills only. Otherwise renders frames f_####.png START..END of the walk-through.
World: Blender Z-up, nose +X. Hull scaled x40 (~39 m). Layout numbers are written in a x32 frame and multiplied by K.
"""
import math, os, sys, urllib.request
import bpy, bmesh
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
OUT, AD = a[0], a[1]; S0, S1 = int(a[2]), int(a[3])
os.makedirs(OUT, exist_ok=True)
SPP = int(os.environ.get('SPP', '48')); DRY = os.environ.get('DRY', '')
K = 1.25
def P(x, y, z): return Vector((x * K, y * K, z * K))

glb = os.path.join(AD, 'craft.glb')
if not os.path.exists(glb) or os.path.getsize(glb) < 1e6:
    urllib.request.urlretrieve('https://drive.usercontent.google.com/download?id=12-V8qH5l2mrH5hzdw8Sd-MFBViGcOEXZ&export=download&confirm=t', glb)
hdr = os.path.join(AD, 'small_harbour_sunset_2k.hdr')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.use_scripts_auto_execute = True
sc = bpy.context.scene; col = sc.collection
sc.frame_start, sc.frame_end = 1, 240; sc.render.fps = 24

# ------------------------------------------------------------------ hull
bpy.ops.import_scene.gltf(filepath=glb)
hull = [o for o in bpy.context.selected_objects if o.type == 'MESH'][0]
hull.name = 'Hull'
for o in bpy.context.selected_objects:
    if o.parent is None: o.scale = (40, 40, 40)
bpy.context.view_layer.update()
import numpy as np
me = hull.data; nv = len(me.vertices); co = np.empty(nv * 3, dtype=np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
mw = np.array(hull.matrix_world); W = (np.c_[co, np.ones(nv)] @ mw.T)[:, :3]
print('MODEL hull verts', nv, 'bounds', W.min(0).round(2), W.max(0).round(2))

# ------------------------------------------------------------------ materials
def pbsdf(name, base, metal=.5, rough=.4, emit=None, estr=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*base, 1); p.inputs['Metallic'].default_value = metal; p.inputs['Roughness'].default_value = rough
    if emit: p.inputs['Emission Color'].default_value = (*emit, 1); p.inputs['Emission Strength'].default_value = estr
    return m
M_FLOOR = pbsdf('Deck', (.07, .075, .085), .7, .35)
M_WALL = pbsdf('Wall', (.55, .57, .6), .3, .45)
M_RIB = pbsdf('Rib', (.12, .13, .15), .8, .3)
M_SEAT = pbsdf('Seat', (.05, .05, .06), .0, .6)
M_PIPE = pbsdf('Pipe', (.5, .35, .2), .9, .3)
M_CYAN = pbsdf('LightCyan', (.2, .8, 1), 0, .5, (.25, .85, 1), 12)
M_AMBER = pbsdf('LightAmber', (1, .6, .2), 0, .5, (1, .55, .15), 10)
M_RED = pbsdf('NavRed', (1, .05, .03), 0, .5, (1, .04, .02), 0)
M_GREEN = pbsdf('NavGreen', (.05, 1, .2), 0, .5, (.05, 1, .2), 0)
M_WHITE = pbsdf('Strobe', (1, 1, 1), 0, .5, (1, 1, 1), 0)
M_THR = pbsdf('Thruster', (.15, .15, .17), .9, .25)
M_GLOW = pbsdf('ExhaustGlow', (.3, .6, 1), 0, .5, (.35, .65, 1), 0)
M_CORE = pbsdf('ReactorCore', (.4, .8, 1), 0, .2, (.3, .8, 1), 0)

def screen_mat(name, tint):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); e = nt.nodes.new('ShaderNodeEmission')
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 6; wv.inputs['Distortion'].default_value = 4
    tc = nt.nodes.new('ShaderNodeTexCoord'); ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (tint[0] * .15, tint[1] * .15, tint[2] * .15, 1); ramp.color_ramp.elements[1].color = (*tint, 1)
    nt.links.new(tc.outputs['Object'], wv.inputs['Vector']); nt.links.new(wv.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], e.inputs['Color']); e.inputs['Strength'].default_value = 6
    nt.links.new(e.outputs['Emission'], o.inputs['Surface'])
    d = wv.inputs['Phase Offset'].driver_add('default_value'); d.driver.expression = 'frame*0.15'
    return m
M_SCR = screen_mat('ScreenCyan', (.2, .8, 1)); M_SCR2 = screen_mat('ScreenAmber', (1, .55, .15))

# ------------------------------------------------------------------ hull shader masks (cutaway / canopy window / ramp hole)
cut_ctl = None; ramp_ctl = None
for m in hull.data.materials:
    nt = m.node_tree; outn = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    src = outn.inputs['Surface'].links[0].from_socket
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sep.inputs[0])
    def cmp(sock, op, val):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op; nt.links.new(sock, n.inputs[0]); n.inputs[1].default_value = val; return n.outputs[0]
    def mul(*ss):
        cur = ss[0]
        for s in ss[1:]:
            n = nt.nodes.new('ShaderNodeMath'); n.operation = 'MULTIPLY'; nt.links.new(cur, n.inputs[0]); nt.links.new(s, n.inputs[1]); cur = n.outputs[0]
        return cur
    absy = nt.nodes.new('ShaderNodeMath'); absy.operation = 'ABSOLUTE'; nt.links.new(sep.outputs['Y'], absy.inputs[0])
    X, Y, Z = sep.outputs['X'], absy.outputs[0], sep.outputs['Z']
    cutv = nt.nodes.new('ShaderNodeValue'); cutv.name = 'CUT'; cutv.outputs[0].default_value = 0
    rampv = nt.nodes.new('ShaderNodeValue'); rampv.name = 'RAMP'; rampv.outputs[0].default_value = 0
    m_cut = mul(cmp(X, 'GREATER_THAN', -11.8 * K), cmp(X, 'LESS_THAN', 12.6 * K), cmp(Y, 'LESS_THAN', 3.7 * K), cmp(Z, 'GREATER_THAN', .55 * K), cutv.outputs[0])
    m_win = mul(cmp(X, 'GREATER_THAN', 9.6 * K), cmp(X, 'LESS_THAN', 12.8 * K), cmp(Y, 'LESS_THAN', 1.05 * K), cmp(Z, 'GREATER_THAN', .9 * K))
    m_ramp = mul(cmp(X, 'GREATER_THAN', -1.6 * K), cmp(X, 'LESS_THAN', 1.6 * K), cmp(Y, 'LESS_THAN', .85 * K), cmp(Z, 'LESS_THAN', -.85 * K), cmp(rampv.outputs[0], 'GREATER_THAN', .03))
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); gl = nt.nodes.new('ShaderNodeBsdfGlass'); gl.inputs['Color'].default_value = (.55, .75, .85, 1); gl.inputs['Roughness'].default_value = .02
    gm = nt.nodes.new('ShaderNodeMixShader'); nt.links.new(m_win, gm.inputs[0]); nt.links.new(src, gm.inputs[1]); nt.links.new(gl.outputs[0], gm.inputs[2])
    hole = nt.nodes.new('ShaderNodeMath'); hole.operation = 'MAXIMUM'; nt.links.new(m_cut, hole.inputs[0]); nt.links.new(m_ramp, hole.inputs[1])
    tm = nt.nodes.new('ShaderNodeMixShader'); nt.links.new(hole.outputs[0], tm.inputs[0]); nt.links.new(gm.outputs[0], tm.inputs[1]); nt.links.new(tr.outputs[0], tm.inputs[2])
    nt.links.new(tm.outputs[0], outn.inputs['Surface'])
    cut_ctl = cutv; ramp_ctl = rampv
def set_cut(v):
    for m in hull.data.materials: m.node_tree.nodes['CUT'].outputs[0].default_value = v
# ramp hole driven by the RAMP value keyframes
for m in hull.data.materials:
    s = m.node_tree.nodes['RAMP'].outputs[0]
    s.default_value = 0; s.keyframe_insert('default_value', frame=40); s.default_value = 1; s.keyframe_insert('default_value', frame=41)

# ------------------------------------------------------------------ geometry helpers (all coords in x32 frame -> P())
def box(name, c, size, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=P(*c), rotation=[math.radians(r) for r in rot])
    o = bpy.context.active_object; o.name = name; o.scale = (size[0] * K, size[1] * K, size[2] * K); o.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bv = o.modifiers.new('B', 'BEVEL'); bv.width = .015; bv.segments = 2; bv.limit_method = 'ANGLE'
    return o
def cyl(name, c, r, depth, mat, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r * K, depth=depth * K, location=P(*c), rotation=[math.radians(x) for x in rot])
    o = bpy.context.active_object; o.name = name; o.data.materials.append(mat); o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons)); return o
def torus(name, c, R, r, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R * K, minor_radius=r * K, location=P(*c), rotation=[math.radians(x) for x in rot], major_segments=48, minor_segments=12)
    o = bpy.context.active_object; o.name = name; o.data.materials.append(mat); o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons)); return o
def area(name, c, size, energy, color=(1, 1, 1), rot=(0, 0, 0)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size * K; ld.energy = energy; ld.color = color
    o = bpy.data.objects.new(name, ld); col.objects.link(o); o.location = P(*c); o.rotation_euler = [math.radians(x) for x in rot]; return o
def point(name, c, energy, color, r=.1):
    ld = bpy.data.lights.new(name, 'POINT'); ld.energy = energy; ld.color = color; ld.shadow_soft_size = r
    o = bpy.data.objects.new(name, ld); col.objects.link(o); o.location = P(*c); return o
def room(name, x0, x1, yw, zf, zc, ribs=True, light=M_CYAN, endwalls=(True, True)):
    L = x1 - x0; cx = (x0 + x1) / 2; H = zc - zf
    box(name + '_floor', (cx, 0, zf - .05), (L, 2 * yw, .1), M_FLOOR)
    box(name + '_ceil', (cx, 0, zc + .05), (L, 2 * yw, .1), M_WALL)
    for s in (-1, 1):
        box(name + f'_wall{s}', (cx, s * (yw + .05), (zf + zc) / 2), (L, .1, H), M_WALL)
        box(name + f'_strip{s}', (cx, s * (yw - .06), zf + .04), (L - .2, .05, .04), light)   # floor edge light
        box(name + f'_cstrip{s}', (cx, s * yw * .45, zc - .02), (L - .3, .06, .03), light)    # ceiling light
        if ribs:
            n = max(2, int(L / .8))
            for i in range(n + 1):
                x = x0 + .1 + i * (L - .2) / n
                box(name + f'_rib{s}_{i}', (x, s * (yw - .07), (zf + zc) / 2), (.12, .14, H), M_RIB)
    for e, x in zip(endwalls, (x0, x1)):
        if e: box(name + f'_end{x}', (x, 0, (zf + zc) / 2), (.1, 2 * yw, H), M_WALL)
def door(name, x, yw, zf, zc, t_open, t_close=None):
    """Two sliding leaves in a frame at station x; opens sideways at t_open."""
    H = zc - zf
    for s in (-1, 1):
        box(name + f'_frame{s}', (x, s * (yw + .1), (zf + zc) / 2), (.25, .2, H), M_RIB)
        lf = box(name + f'_leaf{s}', (x, s * yw / 2, (zf + zc) / 2), (.08, yw, H - .05), M_WALL)
        lf.keyframe_insert('location', frame=t_open); lf.location.y += s * yw * K * .95; lf.keyframe_insert('location', frame=t_open + 18)
        box(name + f'_lamp{s}', (x - .05, s * (yw + .1), zc - .15), (.05, .12, .08), M_AMBER)
    box(name + '_head', (x, 0, zc - .06), (.25, 2 * yw + .4, .14), M_RIB)

# ------------------------------------------------------------------ INTERIOR
# bridge (nose), corridor, cabins, engine room
ZF, ZC = -1.0, 1.5
room('Bridge', 6.2, 11.6, 1.45, -.85, 1.35, endwalls=(False, False))
box('Bridge_step', (6.1, 0, -.92), (.3, 1.8, .15), M_FLOOR)
room('Corridor', -4.2, 6.2, .9, ZF, ZC, endwalls=(False, False))
for s in (-1, 1):  # side cabins off the corridor
    room(f'Cabin{s}', -2.4, 3.6, .8, -.95, 1.35, light=M_AMBER)
    for o in [o for o in col.objects if o.name.startswith(f'Cabin{s}')]:
        o.location.y += s * 1.75 * K
room('Engine', -11.2, -4.2, 2.5, -.35, 1.9, endwalls=(True, False))
for i, z in enumerate((-.85, -.65, -.45)):  # steps up to the engine deck
    box(f'Step{i}', (-4.0 - i * .25, 0, z), (.25, 1.7, .1), M_FLOOR)
door('DoorBridge', 6.2, .85, ZF, 1.35, 70)
door('DoorEngine', -4.2, .85, -.35, 1.5, 95)

# bridge furniture: pilot + co-pilot seats, wraparound console, captain chair, holo table
def seat(name, x, y, z, yaw=0):
    box(name + '_base', (x, y, z + .2), (.25, .25, .4), M_RIB)
    box(name + '_seat', (x, y, z + .47), (.55, .5, .1), M_SEAT, rot=(0, -6, yaw))
    box(name + '_back', (x - .27, y, z + .85), (.1, .5, .75), M_SEAT, rot=(0, -12, yaw))
    for s in (-1, 1): box(name + f'_arm{s}', (x, y + s * .28, z + .65), (.45, .06, .06), M_RIB)
for s in (-1, 1):
    seat(f'Pilot{s}', 9.6, s * .6, -.85)
    box(f'Console{s}', (10.6, s * .6, -.45), (.7, .9, .8), M_RIB, rot=(0, 0, 0))
    box(f'ConsoleScr{s}', (10.42, s * .6, .02), (.5, .8, .02), M_SCR, rot=(0, -55, 0))
    box(f'SideScr{s}', (8.0, s * 1.36, .35), (1.4, .03, .55), M_SCR2)
    box(f'SideDesk{s}', (8.0, s * 1.2, -.2), (1.6, .35, .08), M_RIB)
seat('Captain', 7.2, 0, -.85)
cyl('HoloBase', (8.4, 0, -.65), .3, .4, M_RIB)
holo = cyl('HoloGlobe', (8.4, 0, -.05), .22, .45, M_CYAN, verts=32); holo.scale.z = .3
dr = holo.driver_add('rotation_euler', 2); dr.driver.expression = 'frame*0.05'
box('BridgeCeilPanel', (9.0, 0, 1.3), (2.0, 1.4, .05), M_SCR)
# corridor: wall panels with screens, grating stripes, overhead conduit
for i, x in enumerate((-2.6, -.2, 2.6, 4.8)):
    for s in (-1, 1):
        if -2.4 < x < 3.6 and abs(x - .6) < .5: continue
        box(f'CorrScr{i}{s}', (x, s * .8, .5), (.6, .02, .35), M_SCR if i % 2 else M_SCR2)
for i in range(13): box(f'Grate{i}', (-3.9 + i * .8, 0, ZF + .005), (.04, 1.5, .01), M_RIB)
cyl('Conduit', (1.0, .45, 1.38), .06, 10.2, M_PIPE, rot=(0, 90, 0))
# cabin doorways (gaps) + bunks, lockers, mess table
for s in (-1, 1):
    yo = s * 1.75
    box(f'Bunk{s}a', (-1.0, yo + s * .45, -.55), (2.0, .7, .12), M_SEAT); box(f'Bunk{s}b', (-1.0, yo + s * .45, .35), (2.0, .7, .12), M_SEAT)
    box(f'BunkFrame{s}', (-1.0, yo + s * .45, -.1), (2.1, .75, 1.7), M_RIB).display_type = 'WIRE'
    box(f'Locker{s}', (2.9, yo + s * .5, .15), (1.0, .5, 2.2), M_WALL)
    box(f'LockerLine{s}', (2.9, yo + s * .24, .15), (.02, .01, 2.0), M_AMBER)
    box(f'Table{s}', (1.0, yo, -.35), (1.0, .7, .06), M_RIB); cyl(f'TableLeg{s}', (1.0, yo, -.68), .05, .6, M_RIB)
    # doorway: punch a light frame in the corridor wall at x=.6
    box(f'CabinArch{s}', (.6, s * .95, .2), (1.0, .12, .05), M_AMBER)
# engine room: reactor with spinning rings, coolant pipes, consoles, catwalk rail
EX = -8.2
cyl('ReactorBase', (EX, 0, -.25), .9, .2, M_RIB, verts=48)
core = cyl('ReactorCore', (EX, 0, .75), .28, 1.9, M_CORE, verts=32)
cyl('ReactorCap', (EX, 0, 1.75), .7, .18, M_RIB, verts=48)
for i, (R, ax) in enumerate(((.75, 0), (.62, 1), (.5, 2))):
    t = torus(f'ReactorRing{i}', (EX, 0, .75), R, .045, M_PIPE if i != 1 else M_CYAN)
    d = t.driver_add('rotation_euler', ax); d.driver.expression = f'frame*{0.06 + i * 0.035:.3f}'
# reactor pulse: emission strength driven by frame
cs = M_CORE.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
d = cs.driver_add('default_value'); d.driver.expression = '18+10*sin(frame*0.25)'
point('ReactorLight', (EX, 0, .75), 900, (.35, .8, 1), .3)
for s in (-1, 1):
    for j, z in enumerate((.2, .55, 1.2)):
        cyl(f'Pipe{s}{j}', (-7.6, s * 2.3, z), .08 + .03 * (j == 1), 7.0, M_PIPE, rot=(0, 90, 0))
    box(f'EngConsole{s}', (-5.4, s * 1.8, .1), (.9, .5, .9), M_RIB)
    box(f'EngScr{s}', (-5.4, s * 1.53, .6), (.7, .02, .4), M_SCR2, rot=(-15 * s, 0, 0))
    box(f'Rail{s}', (EX, s * 1.25, .55), (2.6, .04, .04), M_AMBER)
    for k in range(3): cyl(f'Post{s}{k}', (EX - 1.2 + k * 1.2, s * 1.25, .1), .03, .9, M_RIB)
    box(f'Tank{s}', (-10.4, s * 1.7, .5), (1.0, .9, 1.7), M_THR)
# boarding ramp in the belly (hinged at the aft end, lowers at frame 40-100)
ramp_piv = bpy.data.objects.new('RampPivot', None); col.objects.link(ramp_piv); ramp_piv.location = P(-1.5, 0, -1.0)
rp = box('Ramp', (0, 0, -1.05), (3.0, 1.6, .12), M_FLOOR); rp.parent = ramp_piv; rp.matrix_parent_inverse = ramp_piv.matrix_world.inverted()
for i in range(6): r = box(f'RampTread{i}', (-1.2 + i * .5, 0, -.98), (.06, 1.5, .03), M_AMBER); r.parent = ramp_piv; r.matrix_parent_inverse = ramp_piv.matrix_world.inverted()
ramp_piv.keyframe_insert('rotation_euler', frame=40); ramp_piv.rotation_euler.y = math.radians(-24); ramp_piv.keyframe_insert('rotation_euler', frame=100)
box('RampWell', (0, 0, -.95), (3.2, 1.8, .02), M_CYAN).hide_render = True
area('RampSpill', (0, 0, -.6), 2.0, 300, (1, .75, .5), rot=(0, 0, 0))

# room lights
for x in (8.0, 10.2): area(f'BrL{x}', (x, 0, 1.25), 1.6, 120, (.75, .9, 1))
for x in (-2.5, .8, 4.2): area(f'CoL{x}', (x, 0, 1.4), 1.0, 90, (.8, .9, 1))
for s in (-1, 1): area(f'CaL{s}', (.6, s * 1.75, 1.25), 1.6, 110, (1, .8, .6))
for x in (-10.0, -6.2): area(f'EnL{x}', (x, 0, 1.8), 2.0, 160, (.7, .85, 1))

# ------------------------------------------------------------------ EXTERIOR engineering
xmin, xmax = W[:, 0].min(), W[:, 0].max()
aft = W[W[:, 0] < xmin + 1.2]
# thrusters: three nozzles (centre + pair) at the aft face, placed from the hull's actual aft geometry
def mid_z(yc):
    s = aft[np.abs(aft[:, 1] - yc) < 1.0]
    return float(s[:, 2].mean()) if len(s) else 0.5
for i, yc in enumerate((0.0, -4.5, 4.5)):
    x0 = float(xmin) + .6; z0 = mid_z(yc); r = 1.0 if i == 0 else .75
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=r, radius2=r * .78, depth=1.6, location=(x0 - .5, yc, z0), rotation=(0, math.radians(90), 0))
    n = bpy.context.active_object; n.name = f'Thruster{i}'; n.data.materials.append(M_THR)
    bpy.ops.mesh.primitive_circle_add(vertices=32, radius=r * .74, fill_type='NGON', location=(x0 - 1.32, yc, z0), rotation=(0, math.radians(90), 0))
    g = bpy.context.active_object; g.name = f'Exhaust{i}'; g.data.materials.append(M_GLOW)
eg = M_GLOW.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
eg.default_value = 3; eg.keyframe_insert('default_value', frame=1); eg.default_value = 3; eg.keyframe_insert('default_value', frame=150); eg.default_value = 40; eg.keyframe_insert('default_value', frame=200)
# nav lights at the real wingtips + dorsal strobe
iy0, iy1, iz1 = W[:, 1].argmin(), W[:, 1].argmax(), W[:, 2].argmax()
for nm, idx, mat_, off in (('NavPort', iy0, M_RED, (0, -.15, 0)), ('NavStbd', iy1, M_GREEN, (0, .15, 0)), ('Strobe', iz1, M_WHITE, (0, 0, .15))):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.12, location=Vector(W[idx]) + Vector(off)); l = bpy.context.active_object; l.name = nm; l.data.materials.append(mat_)
for m_, ex in ((M_RED, '12*(sin(frame*0.26)>0.3)'), (M_GREEN, '12*(sin(frame*0.26)>0.3)'), (M_WHITE, '60*(sin(frame*0.26)>0.97)')):
    d = m_.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].driver_add('default_value'); d.driver.expression = ex
# landing gear: 3 struts (nose + two mains) from the belly, retracted -> deployed 1..30
def belly_z(x, y):
    s = W[(np.abs(W[:, 0] - x) < .6) & (np.abs(W[:, 1] - y) < .6)]
    return float(s[:, 2].min()) if len(s) else -1.5
for i, (x, y) in enumerate(((9.0 * K, 0), (-6.0 * K, -3.0 * K), (-6.0 * K, 3.0 * K))):
    bz = belly_z(x, y); piv = bpy.data.objects.new(f'GearPiv{i}', None); col.objects.link(piv); piv.location = (x, y, bz + .2)
    for nm, (c, sz) in {'strut': ((0, 0, -1.0), (.22, .22, 2.0)), 'foot': ((0, 0, -2.05), (1.0, .7, .12))}.items():
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x + c[0], y + c[1], bz + .2 + c[2])); o = bpy.context.active_object
        o.name = f'Gear{i}_{nm}'; o.scale = sz; o.data.materials.append(M_THR); o.parent = piv; o.matrix_parent_inverse = piv.matrix_world.inverted()
    piv.rotation_euler.y = math.radians(85); piv.keyframe_insert('rotation_euler', frame=1); piv.rotation_euler.y = 0; piv.keyframe_insert('rotation_euler', frame=30)
for o in bpy.data.objects:
    if o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'

# ------------------------------------------------------------------ world, camera, render
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True; nt = w.node_tree; bg = nt.nodes['Background']
if os.path.exists(hdr):
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(hdr); nt.links.new(env.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = .9
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); col.objects.link(sun); sun.data.energy = 3; sun.data.color = (1, .87, .72)
sun.rotation_euler = (math.radians(50), 0, math.radians(135))
gp = bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, float(W[:, 2].min()) - 2.1)); ground = bpy.context.active_object; ground.name = 'Pad'
gm = pbsdf('Pad', (.1, .1, .11), .2, .6); ground.data.materials.append(gm)
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); col.objects.link(cam); sc.camera = cam
r = sc.render; r.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SPP; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6; sc.cycles.transparent_max_bounces = 16
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'craft_interior.blend'), compress=True)

def look(loc, tgt, lens=28):
    cam.location = Vector(loc); cam.data.lens = lens; cam.data.clip_start = .05
    cam.rotation_euler = (Vector(tgt) - cam.location).to_track_quat('-Z', 'Y').to_euler()
def shot(name, frame, loc, tgt, lens=28, cut=0, res=(1600, 900), pad=True):
    sc.frame_set(frame); set_cut(cut); ground.hide_render = not pad; look(loc, tgt, lens)
    r.resolution_x, r.resolution_y = res; r.filepath = os.path.join(OUT, name + '.png'); bpy.ops.render.render(write_still=True); print('RENDER', name)

if DRY:
    shot('1_exterior', 1, (32, -26, 14), (0, 0, 0), 35, pad=False)
    shot('2_landed_ramp', 160, (14, -20, -1.2), (0, 0, -1.5), 30)
    shot('3_cutaway', 160, (6, -26, 30), (-1, 0, 0), 30, cut=1)
    shot('4_bridge', 160, P(6.8, -.5, .45), P(11.5, .2, .2), 18)
    shot('5_corridor', 160, P(-3.6, .3, .55), P(6.0, 0, .3), 20)
    shot('6_reactor', 160, P(-5.0, -1.6, 1.2), P(-8.2, 0, .6), 18)
    shot('7_cabin', 160, P(3.2, -1.4, .8), P(-2.0, -2.1, -.3), 18)
else:
    # walk-through: approach -> ramp -> corridor -> bridge
    keys = [(1, (40, -30, 12), (0, 0, 0)), (60, (18, -16, -1.0), (0, 0, -1.4)), (110, P(1.5, -1.5, -2.2), P(0, 0, -.6)),
            (150, P(.4, 0, .5), P(5.0, 0, .4)), (200, P(6.6, 0, .55), P(11.5, 0, .3)), (240, P(8.6, 0, .4), P(12, 0, .5))]
    for f in range(S0, S1 + 1):
        for (fa, la, ta), (fb, lb, tb) in zip(keys, keys[1:]):
            if fa <= f <= fb:
                t = (f - fa) / (fb - fa); t = t * t * (3 - 2 * t)
                loc = Vector(la).lerp(Vector(lb), t); tgt = Vector(ta).lerp(Vector(tb), t); break
        sc.frame_set(f); set_cut(0); look(loc, tgt, 24)
        r.resolution_x, r.resolution_y = 1280, 720; r.filepath = os.path.join(OUT, f'f_{f:04d}.png'); bpy.ops.render.render(write_still=True)
print('DONE')
