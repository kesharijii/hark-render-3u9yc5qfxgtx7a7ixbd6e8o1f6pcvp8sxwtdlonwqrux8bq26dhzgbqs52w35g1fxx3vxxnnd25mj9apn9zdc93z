"""v3: hull-derived interior architecture + exterior detail. Interior + exterior engineering pass on the user's Tripo3D spacecraft_concept.glb.
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
M_GLASS = pbsdf('Visor', (.02, .03, .05), .3, .05)
M_CORE = pbsdf('ReactorCore', (.4, .8, 1), 0, .2, (.3, .8, 1), 0)

def screen_mat(name, tint):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); e = nt.nodes.new('ShaderNodeEmission')
    brk = nt.nodes.new('ShaderNodeTexBrick'); brk.inputs['Scale'].default_value = 9; brk.inputs['Mortar Size'].default_value = .03
    brk.inputs['Color1'].default_value = (.08, .08, .08, 1); brk.inputs['Color2'].default_value = (.12, .12, .12, 1); brk.inputs['Mortar'].default_value = (.9, .9, .9, 1)
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 6; wv.inputs['Distortion'].default_value = 4
    tc = nt.nodes.new('ShaderNodeTexCoord'); ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (.05, .05, .05, 1); ramp.color_ramp.elements[1].color = (.7, .7, .7, 1); ramp.color_ramp.elements[0].position = .45
    nt.links.new(tc.outputs['Object'], wv.inputs['Vector']); nt.links.new(wv.outputs['Fac'], ramp.inputs['Fac'])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'SCREEN'; mx.inputs['Factor'].default_value = .55
    nt.links.new(tc.outputs['Object'], brk.inputs['Vector']); nt.links.new(ramp.outputs['Color'], mx.inputs[6]); nt.links.new(brk.outputs['Color'], mx.inputs[7])
    tm = nt.nodes.new('ShaderNodeMix'); tm.data_type = 'RGBA'; tm.blend_type = 'MULTIPLY'; tm.inputs['Factor'].default_value = 1; tm.inputs[7].default_value = (*tint, 1)
    nt.links.new(mx.outputs[2], tm.inputs[6]); nt.links.new(tm.outputs[2], e.inputs['Color']); e.inputs['Strength'].default_value = 4
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
def room(name, x0, x1, yw, zf, zc, ribs=True, light=M_CYAN, endwalls=(True, True), gap=None):
    L = x1 - x0; cx = (x0 + x1) / 2; H = zc - zf
    if gap:
        g0, g1 = gap
        box(name + '_floorA', ((x0 + g0) / 2, 0, zf - .05), (g0 - x0, 2 * yw, .1), M_FLOOR); box(name + '_floorB', ((g1 + x1) / 2, 0, zf - .05), (x1 - g1, 2 * yw, .1), M_FLOOR)
        for gx in (g0, g1): box(name + f'_gapedge{gx}', (gx, 0, zf + .01), (.06, 2 * yw - .2, .03), M_AMBER)
    else:
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

M_FAB = pbsdf('Fabric', (.15, .18, .22), 0, .85)
# ------------------------------------------------------------------ INTERIOR v3: architecture derived from the hull itself (world coords, metres)
from mathutils.bvhtree import BVHTree
def Box(name, c, size, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c, rotation=[math.radians(r) for r in rot])
    o = bpy.context.active_object; o.name = name; o.scale = size; bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat); bv = o.modifiers.new('B', 'BEVEL'); bv.width = .012; bv.segments = 2; bv.limit_method = 'ANGLE'; return o
def Cyl(name, c, r, d, mat, rot=(0, 0, 0), v=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=c, rotation=[math.radians(x) for x in rot])
    o = bpy.context.active_object; o.name = name; o.data.materials.append(mat); o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons)); return o
def Area(name, c, size, energy, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = energy; ld.color = color
    o = bpy.data.objects.new(name, ld); col.objects.link(o); o.location = c; return o

# 1. inner skin = decimated hull pushed 0.3 m inward
skin = hull.copy(); skin.data = hull.data.copy(); skin.name = 'InnerSkin'; col.objects.link(skin)
skin.modifiers.clear(); skin.parent = None; skin.matrix_world = hull.matrix_world.copy()
bpy.context.view_layer.objects.active = skin
for o in bpy.context.selected_objects: o.select_set(False)
skin.select_set(True); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
rm = skin.modifiers.new('Rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = .12; rm.adaptivity = 0
bpy.ops.object.modifier_apply(modifier='Rm')
sm = skin.modifiers.new('Sm', 'LAPLACIANSMOOTH'); sm.iterations = 25; sm.lambda_factor = 1.0; sm.use_volume_preserve = True
bpy.ops.object.modifier_apply(modifier='Sm')
dec = skin.modifiers.new('Dec', 'DECIMATE'); dec.ratio = .35; bpy.ops.object.modifier_apply(modifier='Dec')
bm = bmesh.new(); bm.from_mesh(skin.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.normal_update()
for v in bm.verts: v.co -= v.normal * .35
bm.to_mesh(skin.data); bm.free()
skin.data.materials.clear()
def skin_mat():
    m = bpy.data.materials.new('InnerSkinPanels'); m.use_nodes = True; nt = m.node_tree; p = nt.nodes['Principled BSDF']; outn = nt.nodes['Material Output']
    p.inputs['Base Color'].default_value = (.58, .6, .62, 1); p.inputs['Metallic'].default_value = .25; p.inputs['Roughness'].default_value = .45
    tc = nt.nodes.new('ShaderNodeTexCoord'); br = nt.nodes.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = .45; br.inputs['Mortar Size'].default_value = .006
    br.inputs['Brick Width'].default_value = 1.4; br.inputs['Row Height'].default_value = .6
    br.inputs['Color1'].default_value = (1, 1, 1, 1); br.inputs['Color2'].default_value = (.93, .93, .93, 1); br.inputs['Mortar'].default_value = (0, 0, 0, 1)
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .5; bump.inputs['Distance'].default_value = .01
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1; mix.inputs[6].default_value = (.58, .6, .62, 1)
    nt.links.new(tc.outputs['Object'], br.inputs['Vector']); nt.links.new(br.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    nt.links.new(br.outputs['Color'], mix.inputs[7]); nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    # same cutaway + canopy masks as the hull
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sep.inputs[0])
    absy = nt.nodes.new('ShaderNodeMath'); absy.operation = 'ABSOLUTE'; nt.links.new(sep.outputs['Y'], absy.inputs[0])
    def cmp(sock, op, val):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op; nt.links.new(sock, n.inputs[0]); n.inputs[1].default_value = val; return n.outputs[0]
    def mul(*ss):
        cur = ss[0]
        for s_ in ss[1:]:
            n = nt.nodes.new('ShaderNodeMath'); n.operation = 'MULTIPLY'; nt.links.new(cur, n.inputs[0]); nt.links.new(s_, n.inputs[1]); cur = n.outputs[0]
        return cur
    X, Y, Z = sep.outputs['X'], absy.outputs[0], sep.outputs['Z']
    cutv = nt.nodes.new('ShaderNodeValue'); cutv.name = 'CUT'
    m_cut = mul(cmp(X, 'GREATER_THAN', -11.8 * K), cmp(X, 'LESS_THAN', 12.6 * K), cmp(Y, 'LESS_THAN', 3.7 * K), cmp(Z, 'GREATER_THAN', .55 * K), cutv.outputs[0])
    m_cut2 = mul(cmp(Z, 'GREATER_THAN', .55 * K), cutv.outputs[0])
    m_win = mul(cmp(X, 'GREATER_THAN', 9.6 * K), cmp(X, 'LESS_THAN', 12.8 * K), cmp(Y, 'LESS_THAN', 1.05 * K), cmp(Z, 'GREATER_THAN', .55 * K))
    hole = nt.nodes.new('ShaderNodeMath'); hole.operation = 'MAXIMUM'; nt.links.new(m_cut2, hole.inputs[0]); nt.links.new(m_win, hole.inputs[1])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(hole.outputs[0], mx.inputs[0]); nt.links.new(p.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], outn.inputs['Surface'])
    return m
skin.data.materials.append(skin_mat())
skin.data.polygons.foreach_set('use_smooth', [True] * len(skin.data.polygons))
bvh = BVHTree.FromObject(skin, bpy.context.evaluated_depsgraph_get())
print('MODEL skin faces', len(skin.data.polygons))
def ray(p, d, far=12):
    h = bvh.ray_cast(Vector(p), Vector(d).normalized(), far); return (h[3] if h[0] is not None else None), h[0]
def inside(p):
    up, _ = ray(p, (0, 0, 1)); dn, _ = ray(p, (0, 0, -1)); return up is not None and dn is not None, up
def ceil_at(x, y, z):
    d, h = ray((x, y, z), (0, 0, 1)); return h.z if d is not None else None

# 2. decks clipped to the hull: forward deck (x > XS) and raised aft deck
ZF, ZA, XS = -1.1, .15, -4.5
HATCH = (-1.9, 1.9, 1.0)   # ramp opening in the hall floor (x0, x1, half-width)
def deck(name, x0, x1, zf, step=.25, hole=None):
    bm = bmesh.new(); grid = {}
    nx, ny = int((x1 - x0) / step) + 1, int(16 / step) + 1
    for i in range(nx):
        for j in range(ny):
            x, y = x0 + i * step, -8 + j * step
            ok, up = inside((x, y, zf + .02))
            if ok and up > .35: grid[i, j] = bm.verts.new((x, y, zf))
    for (i, j), v in list(grid.items()):
        q = [grid.get(k) for k in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
        if all(q):
            cx = x0 + (i + .5) * step; cy = -8 + (j + .5) * step
            if hole and hole[0] < cx < hole[1] and abs(cy) < hole[2]: continue
            bm.faces.new(q)
    loose = [v for v in bm.verts if not v.link_faces]; bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.08)
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new(name, me_); col.objects.link(o); me_.materials.append(M_FLOOR); return o
best = (ZF, BR_ := 8.2)
for zb in np.arange(ZF, .8, .05):
    e = 8.2
    for x in np.arange(8.2, 19, .2):
        ok, up = inside((float(x), 0, float(zb) + .02))
        if not ok or up < 1.95: break
        e = float(x)
    if e > best[1] + .05: best = (float(zb), e)
ZB = best[0]; print('MODEL bridge deck z', round(ZB, 2), 'reaches x', round(best[1], 2))
deck('DeckFwd', XS, 8.25, ZF, hole=HATCH)
deck('DeckBridge', 8.25, 19.0, ZB)
nst = max(0, int(round((ZB - ZF) / .2)))
for k in range(nst):
    z = ZF + (k + 1) * (ZB - ZF) / nst; Box(f'BrStair{k}', (8.45 + k * .3, 0, z - .06), (.3, 1.4, .1), M_FLOOR)
deck('DeckAft', -19.5, XS - .05, ZA)
for gx in (HATCH[0], HATCH[1]): Box(f'HatchEdge{gx}', (gx, 0, ZF + .01), (.06, 2 * HATCH[2] - .1, .03), M_AMBER)
# deck plating seams + grating stripes down the hall
for i in range(24):
    x = XS + .6 + i * .9
    if HATCH[0] - .1 < x < HATCH[1] + .1 or not inside((x, 0, ZF + .05))[0]: continue
    Box(f'Seam{i}', (x, 0, ZF + .004), (.03, 2.2, .008), M_RIB)

# 3. stairs between decks (full riser wall across the hull follows the skin)
for k in range(6):
    z = ZF + (k + 1) * (ZA - ZF) / 6; x = XS + .15 - k * .32
    Box(f'Stair{k}', (x + .5, 0, z - .06), (.32, 2.0, .1), M_FLOOR); Box(f'StairLight{k}', (x + .5 + .15, 0, z - .005), (.03, 1.9, .015), M_AMBER)
def snapped_wall(name, a, b, z0, gaps=(), mat=None, step=.2, top_pad=.02, header=2.25):
    """Vertical wall from point a to b (XY), bottom z0, top snapped to the inner skin by raycast. gaps: list of (t0,t1) in metres along the wall."""
    a = Vector((a[0], a[1], 0)); b = Vector((b[0], b[1], 0)); L = (b - a).length; d = (b - a).normalized()
    bm = bmesh.new(); cols = []
    n = int(L / step) + 1
    for i in range(n):
        t = i * L / (n - 1); p = a + d * t
        ok, up = inside((p.x, p.y, z0 + .05))
        in_gap = any(g0 <= t <= g1 for g0, g1 in gaps)
        if not ok: cols.append(None); continue
        ztop = z0 + .05 + up - top_pad
        zb = z0 + header if in_gap else z0
        if in_gap and ztop <= zb + .05: cols.append(None); continue
        cols.append((bm.verts.new((p.x, p.y, zb)), bm.verts.new((p.x, p.y, ztop)), in_gap))
    for c0, c1 in zip(cols, cols[1:]):
        if c0 and c1 and c0[2] == c1[2]: bm.faces.new((c0[0], c1[0], c1[1], c0[1]))
    loose = [v for v in bm.verts if not v.link_faces]; bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.1)
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new(name, me_); col.objects.link(o); me_.materials.append(mat or M_WALL); return o

# 4. hull-following frame ribs: slice the inner skin every 1.6 m, keep what is above the deck
def rib(x, zf):
    bm = bmesh.new(); bm.from_mesh(skin.data)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(x, 0, 0), plane_no=(1, 0, 0))
    keep = set(e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge) and all(v.co.z > zf + .02 for v in e.verts))
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if e not in keep], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context='VERTS')
    if len(bm.edges) < 3: bm.free(); return None
    for v in bm.verts: v.co.x = x
    me_ = bpy.data.meshes.new(f'Rib{x:.1f}'); bm.to_mesh(me_); bm.free()
    o = bpy.data.objects.new(f'Rib{x:.1f}', me_); col.objects.link(o)
    for s in bpy.context.selected_objects: s.select_set(False)
    bpy.context.view_layer.objects.active = o; o.select_set(True); bpy.ops.object.convert(target='CURVE')
    o.data.bevel_mode = 'PROFILE' if False else 'ROUND'; o.data.bevel_depth = .07; o.data.bevel_resolution = 1
    o.data.materials.append(M_RIB); return o
nrib = 0
for x in np.arange(-17.5, 16.6, 1.6):
    if rib(float(x), ZA if x <= XS else (ZB if x > 8.25 else ZF)): nrib += 1
print('MODEL ribs', nrib)

# 5. bulkheads + crew rooms (3 per side) off a central hall
HW = 1.25                                     # hall half-width
BR = 8.2                                      # bridge bulkhead station
snapped_wall('BulkBridge', (BR, -8), (BR, 8), ZF, gaps=[(8 - .75, 8 + .75)])
snapped_wall('BulkEngine', (XS - .05, -8), (XS - .05, 8), ZA, gaps=[(8 - 1.1, 8 + 1.1)])
ROOMS = [(-2.6, .3), (.3, 3.2), (3.2, BR - .1)]
for s in (-1, 1):
    # hall walls with one doorway per room
    gaps = [((x0 + x1) / 2 - .5 + 2.6, (x0 + x1) / 2 + .5 + 2.6) for x0, x1 in ROOMS]
    snapped_wall(f'HallWall{s}', (-2.6, s * HW), (BR, s * HW), ZF, gaps=gaps)
    for x0, x1 in ROOMS: snapped_wall(f'RoomDiv{s}{x0}', (x0, s * (HW + .05)), (x0, s * 8), ZF)
    snapped_wall(f'RoomDivEnd{s}', (BR - .1, s * (HW + .05)), (BR - .1, s * 8), ZF)
# sliding doors in the doorways (crew rooms open 80-120, bridge 70, engine 95)
def slide_door(name, c, width, axis, t, h=2.2, sgn=1):
    leaf = Box(name, c, (width if axis == 'x' else .07, .07 if axis == 'x' else width, h), M_WALL)
    Box(name + '_lamp', (c[0], c[1], c[2] + h / 2 + .08), (.25 if axis == 'x' else .05, .05 if axis == 'x' else .25, .05), M_AMBER)
    leaf.keyframe_insert('location', frame=t)
    if axis == 'x': leaf.location.x += sgn * width * .95
    else: leaf.location.y += sgn * width * .95
    leaf.keyframe_insert('location', frame=t + 16); return leaf
for k, (x0, x1) in enumerate(ROOMS):
    for s in (-1, 1): slide_door(f'RoomDoor{s}{k}', ((x0 + x1) / 2, s * HW, ZF + 1.1), 1.0, 'x', 80 + k * 10 + (s > 0) * 5)
slide_door('BridgeDoorL', (BR, -.37, ZF + 1.1), .74, 'y', 70, sgn=-1); slide_door('BridgeDoorR', (BR, .37, ZF + 1.1), .74, 'y', 70, sgn=1)
slide_door('EngineDoorL', (XS - .05, -.55, ZA + 1.1), 1.1, 'y', 95, sgn=-1); slide_door('EngineDoorR', (XS - .05, .55, ZA + 1.1), 1.1, 'y', 95, sgn=1)
# hazard headers over the main doors
for nm, x, z in (('HdrBridge', BR, ZF + 2.3), ('HdrEngine', XS - .05, ZA + 2.3)):
    Box(nm + '_head', (x, 0, z), (.16, 2.4, .12), M_RIB)

# 6. light strips that follow the hull curve (ceiling raycast), along the hall and in each room
def strip(name, pts, mat, r=.025):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p_, q in zip(sp.points, pts): p_.co = (*q, 1)
    o = bpy.data.objects.new(name, cu); col.objects.link(o); cu.materials.append(mat); return o
for s in (-1, 1):
    pts = []
    for x in np.arange(-16, 15, .4):
        zf = ZF if x > XS else ZA; z = ceil_at(float(x), s * .6, zf + .1)
        if z: pts.append((float(x), s * .6, z - .04))
    if len(pts) > 2: strip(f'CeilStrip{s}', pts, M_CYAN)
    fl = [(float(x), s * (HW - .08), ZF + .03) for x in np.arange(-2.5, BR, .5)]; strip(f'FloorStrip{s}', fl, M_CYAN, .015)
# 7. room-by-room fit-out
def outer_y(x, s, z):
    d, h = ray((x, s * (HW + .2), z), (0, s, 0)); return h.y if d is not None else s * 4
for k, (x0, x1) in enumerate(ROOMS):
    xc = (x0 + x1) / 2
    for s in (-1, 1):
        yo = outer_y(xc, s, ZF + .45)           # where the sloping hull meets bed height
        by = yo - s * .55
        Box(f'Bed{s}{k}', (xc, by, ZF + .3), (min(2.1, x1 - x0 - .4), .9, .25), M_RIB)
        Box(f'Mattress{s}{k}', (xc, by, ZF + .48), (min(2.0, x1 - x0 - .5), .85, .12), M_FAB if 'M_FAB' in globals() else M_SEAT)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(xc - (x1 - x0) / 2 + .55, by, ZF + .62)); pw = bpy.context.active_object; pw.scale = (.35, .6, .1)
        pw.modifiers.new('S', 'SUBSURF').levels = 2; pw.data.materials.append(M_WALL)
        Box(f'Desk{s}{k}', (x1 - .45, s * (HW + 1.0), ZF + .75), (.6, 1.0, .05), M_RIB)
        Box(f'DeskScr{s}{k}', (x1 - .14, s * (HW + 1.0), ZF + 1.25), (.02, .8, .45), M_SCR if k % 2 else M_SCR2)
        Box(f'Locker{s}{k}', (x0 + .35, s * (HW + .45), ZF + 1.0), (.5, .6, 2.0), M_WALL)
        Box(f'LockerLine{s}{k}', (x0 + .61, s * (HW + .45), ZF + 1.0), (.01, .02, 1.8), M_AMBER)
        zc = ceil_at(xc, s * (HW + 1.2), ZF + .1) or (ZF + 2.4)
        Area(f'RoomL{s}{k}', (xc, s * (HW + 1.2), zc - .15), 1.2, 70, (1, .82, .62))
        bpy.ops.mesh.primitive_uv_sphere_add(radius=.15, location=(x1 - .5, s * (HW + .8), ZF + .93)); bpy.context.active_object.data.materials.append(M_WALL)
# hall: handrails, wall screens, emergency lights, lights
for s in (-1, 1):
    Cyl(f'Handrail{s}', (2.8, s * (HW - .1), ZF + .95), .025, 10.6, M_RIB, rot=(0, 90, 0))
    for x in (-1.2, 1.6, 4.6, 7.2): Box(f'HallScr{s}{x}', (x, s * (HW - .06), ZF + 1.45), (.55, .02, .3), M_SCR)
for x in (-1.0, 2.0, 5.5): Area(f'HallL{x}', (x, 0, (ceil_at(x, 0, ZF + .1) or 2) - .15), 1.0, 80, (.8, .9, 1))
# bridge under the real canopy: seats + consoles placed relative to where the deck ends in the nose
nose_end = BR
for x in np.arange(BR, 19, .2):
    ok_, up_ = inside((float(x), 0, ZB + .05))
    if not ok_ or up_ < 1.5: break
    nose_end = float(x)
print('MODEL bridge', BR, '->', round(nose_end, 2))
def seat(name, x, y, z):
    Box(name + '_base', (x, y, z + .22), (.28, .28, .44), M_RIB); Box(name + '_seat', (x, y, z + .5), (.6, .55, .1), M_SEAT, rot=(0, -6, 0))
    Box(name + '_back', (x - .3, y, z + .95), (.1, .55, .85), M_SEAT, rot=(0, -12, 0))
    for s in (-1, 1): Box(name + f'_arm{s}', (x, y + s * .3, z + .72), (.5, .06, .06), M_RIB)
px = nose_end - 2.3
for s in (-1, 1):
    seat(f'Pilot{s}', px, s * .7, ZB)
    Box(f'Console{s}', (px + 1.15, s * .7, ZB + .45), (.75, 1.0, .9), M_RIB)
    Box(f'ConsoleScr{s}', (px + .95, s * .7, ZB + .97), (.55, .9, .02), M_SCR, rot=(0, -55, 0))
    for a_ in range(3):
        for b_ in range(5): Box(f'Btn{s}{a_}{b_}', (px + 1.2 + a_ * .1, s * .7 + (b_ - 2) * .13, ZB + .92 + a_ * .02), (.06, .07, .02), (M_CYAN, M_AMBER, M_RED, M_GREEN)[(a_ + b_) % 4])
    yo = outer_y(px - 1.5, s, ZB + 1.0)
    Box(f'SideStation{s}', (px - 1.5, yo - s * .45, ZB + .5), (1.6, .6, 1.0), M_RIB)
    Box(f'SideScr{s}', (px - 1.5, yo - s * .16, ZB + 1.3), (1.4, .02, .55), M_SCR2)
seat('Captain', px - 2.2, 0, ZB)
Cyl('HoloBase', (px - 1.0, 0, ZB + .25), .32, .5, M_RIB)
holo = Cyl('HoloGlobe', (px - 1.0, 0, ZB + .95), .24, .5, M_CYAN, v=32); holo.scale.z = .3
dr = holo.driver_add('rotation_euler', 2); dr.driver.expression = 'frame*0.05'
for x in (px - 2.0, px): Area(f'BrL{x}', (x, 0, (ceil_at(x, 0, ZB + .1) or 2) - .15), 1.4, 90, (.75, .9, 1))
# engine room on the raised aft deck
EX = -10.0
Cyl('ReactorBase', (EX, 0, ZA + .1), 1.0, .2, M_RIB, v=48)
ztop = (ceil_at(EX, 0, ZA + .1) or (ZA + 2.3)) - .05
core = Cyl('ReactorCore', (EX, 0, (ZA + .2 + ztop - .25) / 2), .3, ztop - .25 - ZA - .2, M_CORE, v=32)
Cyl('ReactorCap', (EX, 0, ztop - .12), .75, .2, M_RIB, v=48)
for i, (R_, ax) in enumerate(((.8, 0), (.66, 1), (.54, 2))):
    bpy.ops.mesh.primitive_torus_add(major_radius=R_, minor_radius=.05, location=(EX, 0, core.location.z), major_segments=48, minor_segments=12)
    t = bpy.context.active_object; t.name = f'ReactorRing{i}'; t.data.materials.append(M_PIPE if i != 1 else M_CYAN)
    d = t.driver_add('rotation_euler', ax); d.driver.expression = f'frame*{0.06 + i * 0.035:.3f}'
cs = M_CORE.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']; d = cs.driver_add('default_value'); d.driver.expression = '18+10*sin(frame*0.25)'
ld = bpy.data.lights.new('ReactorLight', 'POINT'); ld.energy = 900; ld.color = (.35, .8, 1); ld.shadow_soft_size = .3
lo = bpy.data.objects.new('ReactorLight', ld); col.objects.link(lo); lo.location = core.location
for s in (-1, 1):
    for k in range(3): Cyl(f'Post{s}{k}', (EX - 1.3 + k * 1.3, s * 1.5, ZA + .5), .03, .9, M_RIB)
    Box(f'Rail{s}', (EX, s * 1.5, ZA + .95), (2.8, .04, .04), M_AMBER)
    for j, z in enumerate((.35, .7, 1.2)):  # coolant pipes hugging the hull side
        pts = []
        for x in np.arange(-15, -5, .5):
            y_ = outer_y(float(x), s, ZA + z) - s * (.15 + .1 * j)
            pts.append((float(x), y_, ZA + z))
        strip(f'Coolant{s}{j}', pts, M_PIPE, .07 + .02 * (j == 1))
    Box(f'EngConsole{s}', (-6.2, s * 2.2, ZA + .5), (1.0, .5, 1.0), M_RIB)
    Box(f'EngScr{s}', (-6.2, s * 1.93, ZA + 1.1), (.8, .02, .45), M_SCR2, rot=(-15 * s, 0, 0))
    Box(f'Tank{s}', (-13.0, s * 1.8, ZA + .7), (1.1, .9, 1.4), M_THR)
    for k in range(3): Box(f'Crate{s}{k}', (-7.6 + k * .6, s * 2.6, ZA + .25 + (k == 1) * .5), (.5, .5, .48), M_RIB if k % 2 else M_THR)
for k in range(4):  # sagging cables under the aft ceiling
    y_ = (k - 1.5) * .8; zc = (ceil_at(-12, y_, ZA + .1) or ZA + 2.2) - .05
    cu = bpy.data.curves.new(f'Cable{k}', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = .025; sp = cu.splines.new('BEZIER'); sp.bezier_points.add(2)
    for j, (x_, z_) in enumerate(((-13.5, zc), (-11.0 - k * .3, zc - .45 - k * .08), (-8.0, zc))):
        bp = sp.bezier_points[j]; bp.co = (x_, y_, z_); bp.handle_left_type = bp.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(f'Cable{k}', cu); col.objects.link(o); cu.materials.append(M_PIPE)
for x in (-12.5, -7.0): Area(f'EnL{x}', (x, 0, (ceil_at(x, 0, ZA + .1) or 2) - .15), 1.6, 140, (.7, .85, 1))
# boarding ramp under the hatch (hinged at its aft edge, forward end lowers 40-100)
ramp_piv = bpy.data.objects.new('RampPivot', None); col.objects.link(ramp_piv); ramp_piv.location = (HATCH[0], 0, ZF - .1)
rp = Box('Ramp', (0, 0, ZF - .15), (HATCH[1] - HATCH[0], 2 * HATCH[2] - .15, .12), M_FLOOR); rp.parent = ramp_piv; rp.matrix_parent_inverse = ramp_piv.matrix_world.inverted()
for i in range(7):
    r_ = Box(f'RampTread{i}', (HATCH[0] + .3 + i * .5, 0, ZF - .085), (.06, 1.7, .03), M_AMBER); r_.parent = ramp_piv; r_.matrix_parent_inverse = ramp_piv.matrix_world.inverted()
ramp_piv.keyframe_insert('rotation_euler', frame=40); ramp_piv.rotation_euler.y = math.radians(28); ramp_piv.keyframe_insert('rotation_euler', frame=100)
Area('RampSpill', (0, 0, ZF + .6), 2.0, 250, (1, .8, .55))

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


# ================================================================== v2 DETAIL PASS
import random; random.seed(7)
M_GRB = pbsdf('Greeble', (.74, .72, .68), .35, .42)
M_GRBD = pbsdf('GreebleDark', (.22, .22, .24), .6, .38)
M_GOLD = pbsdf('GoldTrim', (.85, .66, .28), .9, .3)
M_CABLE = pbsdf('Cable', (.04, .04, .045), .1, .5)
def mhaz():
    m = bpy.data.materials.new('Hazard'); m.use_nodes = True; nt = m.node_tree; p = nt.nodes['Principled BSDF']
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.wave_profile = 'SAW'; wv.inputs['Scale'].default_value = 6; tc = nt.nodes.new('ShaderNodeTexCoord')
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.interpolation = 'CONSTANT'; cr.color_ramp.elements[0].color = (.02, .02, .02, 1); cr.color_ramp.elements[1].color = (.9, .65, .05, 1); cr.color_ramp.elements[1].position = .5
    nt.links.new(tc.outputs['Object'], wv.inputs['Vector']); nt.links.new(wv.outputs['Fac'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], p.inputs['Base Color']); p.inputs['Roughness'].default_value = .5
    return m
M_HAZ = mhaz()
for o in bpy.data.objects:
    if o.name.endswith('_head'): o.data.materials[0] = M_HAZ

def wbox(name, c, size, mat, q=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c); o = bpy.context.active_object; o.name = name; o.scale = size
    if q is not None: o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = q
    o.data.materials.append(mat); return o
def wcyl(name, c, r, d, mat, q=None, v=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=c); o = bpy.context.active_object; o.name = name
    if q is not None: o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = q
    o.data.materials.append(mat); return o

# --- surface-placed greebles from the hull's own normals
nrm = np.empty(nv * 3, dtype=np.float32); me.vertex_normals.foreach_get('vector', nrm); nrm = nrm.reshape(-1, 3)
win = (W[:, 0] > 9.0 * K) & (W[:, 0] < 13.2 * K) & (np.abs(W[:, 1]) < 1.4 * K)
def pick(mask, n, spacing):
    idx = np.flatnonzero(mask); np.random.seed(3); np.random.shuffle(idx); chosen = []
    for i in idx[:20000]:
        p = W[i]
        if all(np.linalg.norm(p - W[j]) > spacing for j in chosen[-400:]): chosen.append(i)
        if len(chosen) >= n: break
    return chosen
top = pick((nrm[:, 2] > .9) & ~win & (np.abs(W[:, 0]) < 18.5), 230, 1.1)
bot = pick((nrm[:, 2] < -.9) & (np.abs(W[:, 0]) < 17), 70, 1.4)
Zup = Vector((0, 0, 1))
gcount = 0
for i in top + bot:
    p = Vector(W[i]); n = Vector(nrm[i]).normalized(); q = Zup.rotation_difference(n)
    t = random.random(); gcount += 1
    def at(dz): return p + n * dz
    if t < .42:   # flush access panel
        sx, sy = random.uniform(.5, 1.5), random.uniform(.35, 1.0)
        wbox('gPanel', at(.02), (sx, sy, .05), M_GRB if random.random() < .75 else M_GRBD, q)
        if random.random() < .3: wbox('gPanelTrim', at(.05), (sx * .9, .04, .02), M_GOLD, q)
    elif t < .66: # vent with slats
        sx, sy = random.uniform(.5, .9), random.uniform(.35, .6)
        wbox('gVent', at(.03), (sx, sy, .06), M_GRBD, q)
        for k in range(4):
            off = (q @ Vector(((k - 1.5) * sx / 4.5, 0, 0)))
            wbox('gSlat', at(.065) + off, (.035, sy * .85, .03), M_GRB, q)
    elif t < .8:  # sensor puck
        r = random.uniform(.12, .25); wcyl('gSensor', at(.04), r, .08, M_GRBD, q); wcyl('gLens', at(.09), r * .5, .03, M_GLOW if random.random() < .3 else M_GRB, q)
    elif t < .9:  # hatch with handle
        wbox('gHatch', at(.02), (.8, .8, .04), M_GRB, q); wbox('gHandle', at(.06), (.3, .05, .03), M_GOLD, q)
    else:         # antenna
        L = random.uniform(.4, 1.1); wcyl('gAntBase', at(.05), .06, .1, M_GRBD, q, 8); wcyl('gAnt', at(.05 + L / 2), .015, L, M_GRBD, q, 6)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=.035, location=at(.06 + L)); bpy.context.active_object.data.materials.append(M_RED)
print('MODEL greebles', gcount)
# --- dorsal sensor dish on the high point
hp = Vector(W[iz1])
wcyl('DishMast', hp + Vector((-.9, 0, .25)), .1, .5, M_GRBD)
bpy.ops.mesh.primitive_uv_sphere_add(radius=.55, location=hp + Vector((-.9, 0, .62)), segments=32, ring_count=16)
dish = bpy.context.active_object; dish.name = 'Dish'; dish.scale = (1, 1, .28); dish.data.materials.append(M_GRB)
dr = dish.driver_add('rotation_euler', 2); dr.driver.expression = 'frame*0.03'
# --- RCS thruster blocks at the four outer corners
for nm, sel in (('RCS_fp', W[:, 0] + np.abs(W[:, 1]) * 0 ), ):
    pass
corners = [W[np.argmax(W[:, 0] * .3 + W[:, 1])], W[np.argmax(W[:, 0] * .3 - W[:, 1])], W[np.argmax(-W[:, 0] + W[:, 1] * .8)], W[np.argmax(-W[:, 0] - W[:, 1] * .8)]]
for k, c in enumerate(corners):
    c = Vector(c); wbox(f'RCS{k}', c + Vector((0, 0, .12)), (.5, .4, .25), M_GRBD)
    for d in (Vector((0, 1, 0)), Vector((0, -1, 0)), Vector((0, 0, 1))):
        wcyl(f'RCSn{k}', c + Vector((0, 0, .12)) + d * .22, .06, .08, M_THR, Zup.rotation_difference(d), 10)
# --- thruster plumes + nozzle lights (same keyframes as the exhaust glow)
def plume_mat():
    m = bpy.data.materials.new('Plume'); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
    tc = nt.nodes.new('ShaderNodeTexCoord'); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); cr = nt.nodes.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (0, 0, 0, 1); cr.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(tc.outputs['Generated'], sp.inputs[0]); nt.links.new(sp.outputs['Z'], cr.inputs['Fac'])
    em.inputs['Color'].default_value = (.25, .55, 1, 1)
    fm = nt.nodes.new('ShaderNodeMath'); fm.operation = 'MULTIPLY_ADD'; fm.use_clamp = True; nt.links.new(sp.outputs['Z'], fm.inputs[0]); fm.inputs[1].default_value = .55; fm.inputs[2].default_value = .4
    nt.links.new(fm.outputs[0], mx.inputs[0]); nt.links.new(em.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o.inputs['Surface'])
    s_ = em.inputs['Strength']
    for f, v in ((1, .0), (150, .0), (200, 6)): s_.default_value = v; s_.keyframe_insert('default_value', frame=f)
    return m
M_PLUME = plume_mat()
for o in [o for o in bpy.data.objects if o.name.startswith('Exhaust')]:
    loc = o.location.copy(); r_ = o.dimensions.y / 2
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=r_ * .95, radius2=r_ * .25, depth=4.5, location=loc - Vector((2.25, 0, 0)), rotation=(0, math.radians(-90), 0), end_fill_type='NOTHING')
    pl = bpy.context.active_object; pl.name = 'Plume'; pl.data.materials.append(M_PLUME)
    ld = bpy.data.lights.new('NozL', 'POINT'); ld.color = (.4, .7, 1); lo = bpy.data.objects.new('NozL', ld); col.objects.link(lo); lo.location = loc - Vector((.6, 0, 0))
    for f, v in ((1, 0), (150, 0), (200, 2500)): ld.energy = v; ld.keyframe_insert('energy', frame=f)
for o in bpy.data.objects:
    if o.name.startswith('Thruster'):
        for k in range(5):  # cooling rings on the nozzles
            bpy.ops.mesh.primitive_torus_add(major_radius=o.dimensions.y / 2 * (.98 - k * .04), minor_radius=.035, location=o.location + Vector((-.6 + k * .3, 0, 0)), rotation=(0, math.radians(90), 0))
            bpy.context.active_object.data.materials.append(M_GOLD if k == 0 else M_GRBD)
# --- detailed landing gear (piston, torque links, pad, hydraulic line) parented to existing pivots
for i in range(3):
    piv = bpy.data.objects[f'GearPiv{i}']; base = piv.matrix_world.translation.copy()
    parts = [wcyl(f'G{i}piston', base + Vector((0, 0, -1.55)), .1, 1.0, M_GRB), wcyl(f'G{i}collar', base + Vector((0, 0, -1.05)), .17, .12, M_GOLD),
             wbox(f'G{i}linkA', base + Vector((.2, 0, -1.2)), (.06, .08, .45), M_GRBD), wbox(f'G{i}linkB', base + Vector((.2, 0, -1.6)), (.06, .08, .45), M_GRBD),
             wcyl(f'G{i}pad', base + Vector((0, 0, -2.02)), .55, .14, M_GRBD, None, 24), wcyl(f'G{i}hyd', base + Vector((-.16, 0, -.9)), .025, 1.6, M_CABLE, None, 8),
             wcyl(f'G{i}light', base + Vector((.24, 0, -.5)), .05, .06, M_WHITE, Zup.rotation_difference(Vector((1, 0, 0))), 12)]
    for o in parts: o.parent = piv; o.matrix_parent_inverse = piv.matrix_world.inverted()
# --- ramp side rails + hydraulics
rpiv = bpy.data.objects['RampPivot']
for s_ in (-1, 1):
    for o in (box(f'RampRail{s_}', (0, s_ * .78, -.9), (3.0, .05, .2), M_GRBD), box(f'RampRailL{s_}', (0, s_ * .74, -.82), (2.8, .02, .03), M_AMBER)):
        o.parent = rpiv; o.matrix_parent_inverse = rpiv.matrix_world.inverted()
CEIL = [o for o in bpy.data.objects if any(t in o.name for t in ('CeilStrip', 'Cable', 'ReactorCap'))]

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

def set_cut2(v):
    set_cut(v)
    for m in skin.data.materials: m.node_tree.nodes['CUT'].outputs[0].default_value = v
def look(loc, tgt, lens=28):
    cam.location = Vector(loc); cam.data.lens = lens; cam.data.clip_start = .05
    cam.rotation_euler = (Vector(tgt) - cam.location).to_track_quat('-Z', 'Y').to_euler()
def shot(name, frame, loc, tgt, lens=28, cut=0, res=(1600, 900), pad=True):
    sc.frame_set(frame); set_cut2(cut); ground.hide_render = not pad; look(loc, tgt, lens)
    for o in CEIL: o.hide_render = bool(cut)
    r.resolution_x, r.resolution_y = res; r.filepath = os.path.join(OUT, name + '.png'); bpy.ops.render.render(write_still=True); print('RENDER', name)

def export_glbs():
    for o in bpy.context.selected_objects: o.select_set(False)
    curves = [o for o in bpy.data.objects if o.type == 'CURVE']
    for o in curves: o.select_set(True)
    if curves:
        bpy.context.view_layer.objects.active = curves[0]; bpy.ops.object.convert(target='MESH')
    lite = hull.copy(); lite.data = hull.data.copy(); lite.name = 'HullLite'; col.objects.link(lite)
    dm = lite.modifiers.new('D', 'DECIMATE'); dm.ratio = .2
    for i, m in enumerate(lite.data.materials):
        m2 = m.copy(); nt = m2.node_tree; p = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]; o_ = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
        nt.links.new(p.outputs[0], o_.inputs['Surface']); lite.data.materials[i] = m2
    hide = {'Hull', 'InnerSkin', 'Pad', 'Cam', 'Sun'}
    inner = [o for o in bpy.data.objects if o.type == 'MESH' and o.name not in hide and o.name != 'HullLite' and not o.name.startswith(('Thruster', 'Exhaust', 'Plume', 'g', 'RCS', 'Dish', 'Nav', 'Strobe', 'Gear', 'G0', 'G1', 'G2'))]
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in inner: o.select_set(True)
    for nm in ('RampPivot',): bpy.data.objects[nm].select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'craft_interior_only.glb'), export_format='GLB', use_selection=True, export_apply=True, export_animations=True, export_lights=False)
    for o in bpy.data.objects:
        if o.type in ('MESH', 'EMPTY') and o.name not in hide: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'craft_full.glb'), export_format='GLB', use_selection=True, export_apply=True, export_animations=True, export_lights=False)
    print('MODEL glb', os.path.getsize(os.path.join(OUT, 'craft_full.glb')), os.path.getsize(os.path.join(OUT, 'craft_interior_only.glb')))

if DRY:
    shot('1_exterior', 1, (32, -26, 14), (0, 0, 0), 35, pad=False)
    shot('2_landed_ramp', 160, (14, -20, -1.2), (0, 0, -1.8), 30)
    shot('3_cutaway', 160, (6, -26, 30), (-1, 0, 0), 30, cut=1)
    shot('4_bridge', 160, (px - 3.0, -.6, ZB + 1.65), (nose_end + 1, .2, ZB + 1.0), 18)
    shot('5_hall', 160, (XS - .8, 0, ZA + 1.6), (BR, 0, ZF + 1.0), 18)
    shot('6_reactor', 160, (-5.6, -.9, ZA + 1.7), (EX, .3, ZA + 1.0), 18)
    shot('7_cabin', 160, (.6, -(HW + .3), ZF + 1.75), (2.8, -3.8, ZF + .4), 15)
    shot('8_thrusters', 215, (-36, -16, 5), (-14, 0, 0), 40, pad=False)
    shot('9_topdetail', 1, (4, -14, 16), (2, 0, 1.5), 40, pad=False)
    try: export_glbs()
    except Exception as e: print('Error glb', e)
else:
    keys = [(1, (40, -30, 12), (0, 0, 0)), (60, (16, -14, -1.5), (0, 0, -2)), (110, (1.0, -2.8, -3.6), (0, 0, -.5)),
            (140, (0.4, 0, ZF + 1.6), (4, 0, ZF + 1.4)), (175, (4.0, 0, ZF + 1.6), (BR + 2, 0, ZF + 1.2)),
            (215, (px - 3, 0, ZB + 1.7), (nose_end + 1, 0, ZB + 1.1)), (240, (px - 1.6, 0, ZB + 1.55), (nose_end + 2, 0, ZB + 1.3))]
    for f in range(S0, S1 + 1):
        for (fa, la, ta), (fb, lb, tb) in zip(keys, keys[1:]):
            if fa <= f <= fb:
                t = (f - fa) / (fb - fa); t = t * t * (3 - 2 * t)
                loc = Vector(la).lerp(Vector(lb), t); tgt = Vector(ta).lerp(Vector(tb), t); break
        sc.frame_set(f); set_cut(0)
        for o in CEIL: o.hide_render = False
        look(loc, tgt, 20)
        r.resolution_x, r.resolution_y = 1280, 720; r.filepath = os.path.join(OUT, f'f_{f:04d}.png'); bpy.ops.render.render(write_still=True)
print('DONE')
