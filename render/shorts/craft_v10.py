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
G = 1.5; GZ = G * 1.25   # v7: ship scaled x1.5, hull thickened (centre x1.25, wings up to x2.25)
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
    if o.parent is None: o.scale = (40 * G, 40 * G, 40 * G)
bpy.context.view_layer.update()
import numpy as np
# v10: cut the Tripo disc wheels + nose strut out of the hull (islands seeded by the lowest vertices)
import bmesh as _bm
_me = hull.data; _n = len(_me.vertices); _c = np.empty(_n * 3, dtype=np.float32); _me.vertices.foreach_get('co', _c); _c = _c.reshape(-1, 3)
_seed = _c[:, 2] < -0.056; print('MODEL wheel seeds', int(_seed.sum()))
_b = _bm.new(); _b.from_mesh(_me); _b.verts.ensure_lookup_table()
_todo = [ _b.verts[i] for i in np.where(_seed)[0] ]; _kill = set(v.index for v in _todo)
while _todo:
    v = _todo.pop()
    for e in v.link_edges:
        o = e.other_vert(v)
        if o.index not in _kill: _kill.add(o.index); _todo.append(o)
_bm.ops.delete(_b, geom=[_b.verts[i] for i in _kill], context='VERTS'); _b.to_mesh(_me); _b.free(); _me.update()
print('MODEL wheels removed verts', len(_kill))
me = hull.data; nv = len(me.vertices); co = np.empty(nv * 3, dtype=np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
mw = np.array(hull.matrix_world); W = (np.c_[co, np.ones(nv)] @ mw.T)[:, :3]
u_ = np.abs(W[:, 1]) / np.abs(W[:, 1]).max(); sm = np.clip((u_ - .22) / .5, 0, 1); sm = sm * sm * (3 - 2 * sm)
W[:, 2] *= 1.25 * (1 + .8 * sm)
loc_ = (np.c_[W, np.ones(nv)] @ np.linalg.inv(mw).T)[:, :3].astype(np.float32); me.vertices.foreach_set('co', loc_.ravel()); me.update()
print('MODEL hull verts', nv, 'bounds', W.min(0).round(2), W.max(0).round(2))
# ------------------------------------------------------------------ v10 LIVERY: vertex-colour paint scheme (survives GLB export)
def _ss(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
_nr = np.empty(nv * 3, dtype=np.float32); me.vertex_normals.foreach_get('vector', _nr); _nr = _nr.reshape(-1, 3)
_R = mw[:3, :3] / np.linalg.norm(mw[:3, 0]); Nw = _nr @ _R.T; Nw /= np.linalg.norm(Nw, axis=1, keepdims=True) + 1e-9
X_, Y_, Z_ = W[:, 0], np.abs(W[:, 1]), W[:, 2]; up = Nw[:, 2]
WHITE = np.array([.80, .81, .83]); CHAR = np.array([.055, .06, .07]); GUN = np.array([.16, .17, .19]); ORNG = np.array([1.0, .30, .03]); CYAN_ = np.array([.0, .55, .75]); YEL = np.array([.95, .7, .05])
col_ = WHITE * (1 - _ss(.15, -.35, up))[:, None] + CHAR * _ss(.15, -.35, up)[:, None]
upper = up > .25
xmin_, xmax_ = X_.min(), X_.max(); ymax_ = Y_.max()
# twin orange spine stripes + thin cyan pinstripe
st = upper & (((Y_ > .9) & (Y_ < 1.45)) | ((Y_ > 1.75) & (Y_ < 2.0))) & (X_ > xmin_ + 3)
col_[st] = ORNG; col_[upper & (Y_ > 2.25) & (Y_ < 2.35) & (X_ > xmin_ + 3)] = CYAN_
# wing leading edge: gunmetal band; wingtips orange
yb = np.round(W[:, 1] / .5).astype(int); lead = np.full(yb.max() - yb.min() + 1, -1e9); np.maximum.at(lead, yb - yb.min(), X_)
dlead = lead[yb - yb.min()] - X_
col_[(Y_ > 6) & (dlead < 1.4)] = GUN
col_[(Y_ > ymax_ - 2.2)] = ORNG
col_[(Y_ > ymax_ - 2.6) & (Y_ <= ymax_ - 2.2)] = CHAR
# scorched gunmetal toward the engines
sc_ = _ss(xmin_ + 4, xmin_ + .5, X_)[:, None]; col_ = col_ * (1 - sc_ * .8) + GUN * sc_ * .8
# hazard chevrons around the boarding ramp on the belly
hz = (up < -.3) & (np.abs(X_) < 1.85 * K * G) & (Y_ > .88 * K * G) & (Y_ < 1.1 * K * G)
col_[hz & ((np.floor((X_ + Y_) / .35) % 2) == 0)] = YEL; col_[hz & ((np.floor((X_ + Y_) / .35) % 2) == 1)] = CHAR
# panel lines (dark seams on a 2.4 m grid, offset per chord)
gx = np.abs(((X_ + .3) / 2.4) % 1 - .5) > .485; gy = np.abs(((Y_ + .9) / 3.0) % 1 - .5) > .488
col_[gx | gy] *= .55
# registration block "07": two small dark squares on each side of the nose top
col_[upper & (X_ > xmax_ - 9) & (X_ < xmax_ - 7.6) & (Y_ > 2.6) & (Y_ < 3.3)] = CHAR
ca = me.color_attributes.new('Livery', 'FLOAT_COLOR', 'POINT')
ca.data.foreach_set('color', np.c_[col_, np.ones(nv)].astype(np.float32).ravel())
for m in hull.data.materials:
    nt = m.node_tree; p = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    cn = nt.nodes.new('ShaderNodeVertexColor'); cn.layer_name = 'Livery'
    nt.links.new(cn.outputs['Color'], p.inputs['Base Color'])
    for nm_, v_ in (('Metallic', .25), ('Roughness', .38)):
        for l in list(p.inputs[nm_].links): nt.links.remove(l)
        p.inputs[nm_].default_value = v_
    try: p.inputs['Coat Weight'].default_value = .35
    except Exception: pass
print('MODEL livery painted', nv)

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
    m_cut = mul(cmp(X, 'GREATER_THAN', -11.8 * K * G), cmp(X, 'LESS_THAN', 12.6 * K * G), cmp(Y, 'LESS_THAN', 3.7 * K * G), cmp(Z, 'GREATER_THAN', .55 * K * GZ), cutv.outputs[0])
    m_win = mul(cmp(X, 'GREATER_THAN', 9.6 * K * G), cmp(X, 'LESS_THAN', 12.8 * K * G), cmp(Y, 'LESS_THAN', 1.05 * K * G), cmp(Z, 'GREATER_THAN', .9 * K * GZ))
    m_ramp = mul(cmp(X, 'GREATER_THAN', -1.6 * K * G), cmp(X, 'LESS_THAN', 1.6 * K * G), cmp(Y, 'LESS_THAN', .85 * K * G), cmp(Z, 'LESS_THAN', -.85 * K * GZ), cmp(rampv.outputs[0], 'GREATER_THAN', .03))
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

# 1. DESIGNED INTERIOR SHELL: a clean lofted lining fitted to the hull (real geometry, exports to GLB as rendered)
meas = hull.copy(); meas.data = hull.data.copy(); meas.name = 'Measure'; col.objects.link(meas); meas.modifiers.clear()
meas.parent = None; meas.matrix_world = hull.matrix_world.copy()
for o in bpy.context.selected_objects: o.select_set(False)
bpy.context.view_layer.objects.active = meas; meas.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
dm_ = meas.modifiers.new('D', 'DECIMATE'); dm_.ratio = .1; bpy.ops.object.modifier_apply(modifier='D')
bvh = BVHTree.FromObject(meas, bpy.context.evaluated_depsgraph_get())
bpy.data.objects.remove(meas)
def ray(p, d, far=14):
    h = bvh.ray_cast(Vector(p), Vector(d).normalized(), far); return (h[3] if h[0] is not None else None), h[0]
ZF, ZA, XS = -1.1 * GZ, .15 * GZ, -4.5 * G
HATCH = (-2.0 * G, 2.0 * G, 1.0)
BR = 8.2 * G; HW = 1.25; MARGIN = .4; NEXP = 3.0
def raw_profile(x, zf):
    up, h = ray((x, 0, zf + .1), (0, 0, 1)); dn, _ = ray((x, 0, zf + .1), (0, 0, -1))
    if up is None or dn is None: return None
    b = h.z - MARGIN - zf
    ws = []
    for zz in (zf + .5, zf + 1.0):
        for sgn in (-1, 1):
            d, hh = ray((x, 0, zz), (0, sgn, 0))
            ws.append(abs(hh.y) - MARGIN if d is not None else 0)
    a = min(ws)
    return a, b
def build_profile(x0, x1, zf, step=.5, amin=1.0, bmin=1.95):
    xs = np.arange(x0, x1 + 1e-6, step); A = []; B = []
    for x in xs:
        r = raw_profile(float(x), zf); A.append(r[0] if r else np.nan); B.append(r[1] if r else np.nan)
    A = np.array(A); B = np.array(B)
    def med(v, k=5):
        out = v.copy()
        for i in range(len(v)):
            w = v[max(0, i - k // 2): i + k // 2 + 1]; w = w[~np.isnan(w)]; out[i] = np.median(w) if len(w) else np.nan
        return out
    A = med(med(A, 7), 5); B = med(med(B, 7), 5)
    for v in (A, B):                       # light gaussian
        good = ~np.isnan(v); vv = np.convolve(np.where(good, v, 0), [.25, .5, .25], 'same'); ww = np.convolve(good.astype(float), [.25, .5, .25], 'same')
        v[good] = (vv / np.maximum(ww, 1e-6))[good]
    keep = (A >= amin) & (B >= bmin)
    # keep the longest contiguous usable run
    best, cur = (0, 0), None
    for i, k_ in enumerate(keep):
        if k_ and cur is None: cur = i
        if (not k_ or i == len(keep) - 1) and cur is not None:
            e = i if k_ else i - 1
            if e - cur > best[1] - best[0]: best = (cur, e)
            cur = None
    i0, i1 = best
    return xs[i0:i1 + 1], np.minimum(A[i0:i1 + 1], 11.0), np.minimum(B[i0:i1 + 1], 4.2)
def zprof(a, b, zf, y):            # ceiling height of the superellipse at lateral y
    u = min(abs(y) / a, 1.0); return zf + b * (1 - u ** NEXP) ** (1 / NEXP)
def yprof(a, b, zf, z):            # wall position at height z
    v = min(max((z - zf) / b, 0), 1.0); return a * (1 - v ** NEXP) ** (1 / NEXP)
SEG = {}
SEG['aft'] = (ZA, *build_profile(-17.5 * G, XS - .1, ZA, bmin=1.9))
SEG['mid'] = (ZF, *build_profile(XS, BR, ZF))
# bridge deck height: pick the floor that lets the nose segment reach furthest forward under the canopy
bestz, beste = ZF, None
for zb in np.arange(ZF, .9 * GZ, .1):
    xs_, a_, b_ = build_profile(BR, 18.5 * G, float(zb), amin=.9, bmin=1.85)
    if len(xs_) and (beste is None or xs_[-1] > beste + .2 and xs_[0] <= BR + .6): bestz, beste = float(zb), xs_[-1]
ZB = bestz
SEG['bridge'] = (ZB, *build_profile(BR, 18.5 * G, ZB, amin=.9, bmin=1.85))
for k, v in SEG.items(): print('MODEL seg', k, 'zf', round(v[0], 2), 'x', round(v[1][0], 2) if len(v[1]) else None, '->', round(v[1][-1], 2) if len(v[1]) else None, 'a', np.round(v[2][::4], 2).tolist(), 'b', np.round(v[3][::4], 2).tolist())
def seg_at(x):
    for k in ('aft', 'mid', 'bridge'):
        zf, xs, A, B = SEG[k]
        if len(xs) and xs[0] - .01 <= x <= xs[-1] + .01: return zf, float(np.interp(x, xs, A)), float(np.interp(x, xs, B))
    return None
def ceil_at(x, y, z=None):
    s_ = seg_at(x); return zprof(s_[1], s_[2], s_[0], y) if s_ else None
def outer_y(x, s, z):
    s_ = seg_at(x); return s * yprof(s_[1], s_[2], s_[0], z) if s_ else s * 2
def inside(p):
    s_ = seg_at(p[0])
    if not s_ or abs(p[1]) > s_[1]: return False, 0
    zc = zprof(s_[1], s_[2], s_[0], p[1]); return (p[2] < zc and p[2] > s_[0] - .3), zc - p[2]
nose_end = SEG['bridge'][1][-1] if len(SEG['bridge'][1]) else BR + 3
# panel lining material (procedural seams in renders, clean colour in GLB) + cutaway mask
def lining_mat():
    m = bpy.data.materials.new('Lining'); m.use_nodes = True; nt = m.node_tree; p = nt.nodes['Principled BSDF']; outn = nt.nodes['Material Output']
    p.inputs['Base Color'].default_value = (.6, .62, .64, 1); p.inputs['Metallic'].default_value = .2; p.inputs['Roughness'].default_value = .4
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sep.inputs[0])
    gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; nt.links.new(sep.outputs['Z'], gt.inputs[0]); gt.inputs[1].default_value = .55 * K * GZ
    cutv = nt.nodes.new('ShaderNodeValue'); cutv.name = 'CUT'; cutv.outputs[0].default_value = 0
    mu = nt.nodes.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; nt.links.new(gt.outputs[0], mu.inputs[0]); nt.links.new(cutv.outputs[0], mu.inputs[1])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(mu.outputs[0], mx.inputs[0]); nt.links.new(p.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], outn.inputs['Surface'])
    return m
M_LIN = lining_mat(); M_CANOPY = pbsdf('CanopyGlass', (.015, .03, .05), .0, .04, (.05, .18, .35), .6); M_LIND = pbsdf('LiningDark', (.3, .32, .35), .4, .4)
for m in (M_FLOOR, M_RIB, M_WALL, M_LIND, M_CYAN, M_AMBER, M_PIPE, M_SEAT, M_FAB, M_SCR, M_SCR2):   # every interior material gets the cutaway mask
    pass
NP = 40
WIN = (12.0 * G, 16.0 * G, 1.31 * G, .69 * GZ)      # canopy opening x0, x1, |y|, z>
def loft(name, key, cap0=True, cap1=True, door0=None, door1=None):
    zf, xs, A, B = SEG[key]
    if len(xs) < 2: return None
    bm = bmesh.new(); rings = []
    for x, a, b in zip(xs, A, B):
        ring = []
        for i in range(NP + 1):
            t = math.pi * i / NP; c, s_ = math.cos(t), math.sin(t)
            y = a * math.copysign(abs(c) ** (2 / NEXP), c); z = zf + b * abs(s_) ** (2 / NEXP)
            ring.append(bm.verts.new((float(x), y, z)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(NP):
            q = (r0[i], r1[i], r1[i + 1], r0[i + 1]); cx = (q[0].co.x + q[1].co.x) / 2; cz = sum(v.co.z for v in q) / 4; cy = sum(abs(v.co.y) for v in q) / 4
            f_ = bm.faces.new(q)
            if key == 'bridge' and WIN[0] < cx < WIN[1] and cy < WIN[2] and cz > WIN[3]: f_.material_index = 1   # canopy glass panel
    def cap(ring, door, flip):
        x = ring[0].co.x; zf_ = ring[0].co.z; a = abs(ring[0].co.y); b = max(v.co.z for v in ring) - zf_; n = 36
        for i in range(n):
            y0 = -a + 2 * a * i / n; y1 = -a + 2 * a * (i + 1) / n
            zt0, zt1 = zprof(a, b, zf_, y0), zprof(a, b, zf_, y1)
            spans = [(zf_, zf_, zt0, zt1)]
            if door and abs((y0 + y1) / 2) < door[0] / 2:
                lo, hi = zf_ + door[2], zf_ + door[2] + door[1]; spans = []
                if door[2] > 0: spans.append((zf_, zf_, min(lo, zt0), min(lo, zt1)))
                if zt0 > hi and zt1 > hi: spans.append((hi, hi, zt0, zt1))
            for zb0, zb1, ztop0, ztop1 in spans:
                if ztop0 - zb0 < .02 and ztop1 - zb1 < .02: continue
                vs = [bm.verts.new((x, y0, zb0)), bm.verts.new((x, y1, zb1)), bm.verts.new((x, y1, ztop1)), bm.verts.new((x, y0, ztop0))]
                bm.faces.new(vs[::-1] if flip else vs)
    if cap0: cap(rings[0], door0, False)
    if cap1: cap(rings[-1], door1, True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.001)
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new(name, me_); col.objects.link(o)
    me_.materials.append(M_LIN); me_.materials.append(M_CANOPY); o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons))
    so = o.modifiers.new('Sol', 'SOLIDIFY'); so.thickness = .06; so.offset = 1
    return o
loft('LiningAft', 'aft', door1=(2.2, 2.2, 0))
loft('LiningMid', 'mid', cap0=True, cap1=True, door0=(2.2, 9, ZA - ZF), door1=(1.5, 2.25, 0))
loft('LiningBridge', 'bridge', door0=(1.5, 2.3, 0), cap1=True)
# 2. decks: flat plates following each segment's floor width, hatch left open
def deck(name, key, hole=None):
    zf, xs, A, B = SEG[key]
    if len(xs) < 2: return
    bm = bmesh.new()
    def quad(x0, x1, ya0, yb0, ya1, yb1):
        bm.faces.new((bm.verts.new((x0, ya0, zf)), bm.verts.new((x1, ya1, zf)), bm.verts.new((x1, yb1, zf)), bm.verts.new((x0, yb0, zf))))
    for i in range(len(xs) - 1):
        x0, x1 = float(xs[i]), float(xs[i + 1]); a0, a1 = float(A[i]) + .03, float(A[i + 1]) + .03
        if hole and x0 >= hole[0] - 1e-6 and x1 <= hole[1] + 1e-6:
            quad(x0, x1, -a0, -hole[2], -a1, -hole[2]); quad(x0, x1, hole[2], a0, hole[2], a1)
        else: quad(x0, x1, -a0, a0, -a1, a1)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.1)
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new(name, me_); col.objects.link(o); me_.materials.append(M_FLOOR); return o
deck('DeckAft', 'aft'); deck('DeckFwd', 'mid', hole=HATCH); deck('DeckBridge', 'bridge')
for gx in (HATCH[0], HATCH[1]): Box(f'HatchEdge{gx}', (gx, 0, ZF + .01), (.06, 2 * HATCH[2] - .1, .03), M_AMBER)
# hall floor runner + plating seams
Box('HallRunner', ((-2.6 * G + BR) / 2 + 1.2, 0, ZF + .006), (BR + 2.6 * G - 2.4, 1.9, .012), M_LIND)
# 3. stairs between decks
for k in range(6):
    z = ZF + (k + 1) * (ZA - ZF) / 6; x = XS + 1.95 - k * .32
    Box(f'Stair{k}', (x, 0, z - .06), (.32, 2.0, .1), M_FLOOR); Box(f'StairLight{k}', (x + .15, 0, z - .005), (.03, 1.9, .015), M_AMBER)
Box('StairLanding', (XS + .1, 0, ZA - .06), (.4, 2.0, .1), M_FLOOR)
for s in (-1, 1): Box(f'StairRail{s}', (XS + 1.0, s * 1.05, (ZF + ZA) / 2 + .95), (2.2, .04, .04), M_AMBER, rot=(0, math.degrees(math.atan2(ZA - ZF, 1.9)), 0))
nst = max(0, int(round((ZB - ZF) / .2)))
for k in range(nst):
    z = ZF + (k + 1) * (ZB - ZF) / nst; Box(f'BrStair{k}', (BR + .25 + k * .3, 0, z - .06), (.3, 1.4, .1), M_FLOOR)
if nst:  # stairwell sides
    for s in (-1, 1): Box(f'BrStairSide{s}', (BR + .25 + nst * .15, s * .75, (ZF + ZB) / 2), (nst * .3 + .2, .06, ZB - ZF + .1), M_LIND)
# 4. designed frames: rectangular-section ribs swept on the exact lining profile every 1.6 m, plus ceiling light panels
def frame(x, key, w=.14, d=.1):
    zf, xs, A, B = SEG[key]; a = float(np.interp(x, xs, A)); b = float(np.interp(x, xs, B))
    bm = bmesh.new(); prev = None
    for i in range(NP + 1):
        t = math.pi * i / NP; c, s_ = math.cos(t), math.sin(t)
        y = a * math.copysign(abs(c) ** (2 / NEXP), c); z = zf + b * abs(s_) ** (2 / NEXP)
        n = Vector((0, -y / max(a, 1e-3), -(z - zf) / max(b, 1e-3))).normalized()   # inward-ish
        p_ = Vector((x, y, z))
        ring = [bm.verts.new(p_ + Vector((-w / 2, 0, 0))), bm.verts.new(p_ + Vector((w / 2, 0, 0))), bm.verts.new(p_ + Vector((w / 2, 0, 0)) + n * d), bm.verts.new(p_ + Vector((-w / 2, 0, 0)) + n * d)]
        if prev:
            for j in range(4): bm.faces.new((prev[j], ring[j], ring[(j + 1) % 4], prev[(j + 1) % 4]))
        prev = ring
    me_ = bpy.data.meshes.new(f'Frame{x:.1f}'); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new(f'Frame{x:.1f}', me_); col.objects.link(o); me_.materials.append(M_RIB); return o
def ceil_panel(name, x0, x1, key, yc, half=.18, mat=None):
    zf, xs, A, B = SEG[key]; bm = bmesh.new(); prev = None
    for x in np.linspace(x0, x1, max(2, int((x1 - x0) / .25) + 1)):
        a = float(np.interp(x, xs, A)); b = float(np.interp(x, xs, B))
        row = [bm.verts.new((float(x), y, zprof(a, b, zf, y) - .045)) for y in (yc - half, yc + half)]
        if prev: bm.faces.new((prev[0], row[0], row[1], prev[1]))
        prev = row
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new(name, me_); col.objects.link(o); me_.materials.append(mat or M_CYAN); return o
nfr = 0
for key in ('aft', 'mid', 'bridge'):
    zf, xs, A, B = SEG[key]
    if len(xs) < 2: continue
    for x in np.arange(xs[0] + .4, xs[-1] - .2, 2.0):
        frame(float(x), key); nfr += 1
        if key != 'bridge':
            for yc in (-.55, .55): ceil_panel(f'CeilLight{key}{x:.1f}{yc}', float(x) + .25, float(x) + 1.35, key, yc, .09)
print('MODEL frames', nfr)
# 5. hall walls + crew rooms (walls cut exactly to the lining profile)
def prof_wall(name, a_xy, b_xy, zf, gaps=(), mat=None, header=2.25, step=.1):
    a = Vector((*a_xy, 0)); b = Vector((*b_xy, 0)); L = (b - a).length; d = (b - a).normalized(); bm = bmesh.new(); cols = []
    n = max(2, int(L / step) + 1)
    for i in range(n):
        t = i * L / (n - 1); p = a + d * t; s_ = seg_at(p.x)
        if not s_ or abs(p.y) > s_[1] - .01: cols.append(None); continue
        zt = zprof(s_[1], s_[2], s_[0], p.y) - .01; g = any(g0 <= t <= g1 for g0, g1 in gaps); zb = zf + header if g else zf
        if zt <= zb + .03: cols.append(None); continue
        cols.append((bm.verts.new((p.x, p.y, zb)), bm.verts.new((p.x, p.y, zt)), g))
    for c0, c1 in zip(cols, cols[1:]):
        if c0 and c1 and c0[2] == c1[2]: bm.faces.new((c0[0], c1[0], c1[1], c0[1]))
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.1)
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new(name, me_); col.objects.link(o); me_.materials.append(mat or M_WALL); return o
PASS = (0.6, 8.0)   # v8: two passages a side lead from the spine to the wing corridors
ROOMS = [(-2.6 * G, PASS[0] - .75), (PASS[0] + .75, 4.3), (4.3, PASS[1] - .75), (PASS[1] + .75, BR - .15)]
for s in (-1, 1):
    gaps = [((x0 + x1) / 2 - .55 + 2.6 * G, (x0 + x1) / 2 + .55 + 2.6 * G) for x0, x1 in ROOMS] + [(xp - .65 + 2.6 * G, xp + .65 + 2.6 * G) for xp in PASS]
    prof_wall(f'HallWall{s}', (-2.6 * G, s * HW), (BR - .15, s * HW), ZF, gaps=gaps)
    for xd in sorted({x for r_ in ROOMS for x in r_}): prof_wall(f'RoomDiv{s}{xd:.2f}', (xd, s * (HW + .05)), (xd, s * 12), ZF)
    # hall wall trim + base strip
    Box(f'HallBase{s}', ((-2.6 * G + BR) / 2, s * (HW - .055), ZF + .06), (BR + 2.6 * G, .02, .12), M_LIND)
def slide_door(name, c, width, axis, t, h=2.2, sgn=1):
    leaf = Box(name, c, (width if axis == 'x' else .07, .07 if axis == 'x' else width, h), M_WALL)
    Box(name + '_win', (c[0], c[1], c[2] + .35), ((width * .5 if axis == 'x' else .075), (.075 if axis == 'x' else width * .5), .5), M_LIND).parent = leaf
    bpy.data.objects[name + '_win'].matrix_parent_inverse = leaf.matrix_world.inverted()
    Box(name + '_lamp', (c[0], c[1], c[2] + h / 2 + .08), (.25 if axis == 'x' else .05, .05 if axis == 'x' else .25, .05), M_AMBER)
    leaf.keyframe_insert('location', frame=t)
    if axis == 'x': leaf.location.x += sgn * width * .95
    else: leaf.location.y += sgn * width * .95
    leaf.keyframe_insert('location', frame=t + 16); return leaf
for k, (x0, x1) in enumerate(ROOMS):
    for s in (-1, 1): slide_door(f'RoomDoor{s}{k}', ((x0 + x1) / 2, s * HW, ZF + 1.1), 1.1, 'x', 80 + k * 10 + (s > 0) * 5)
xb_ = SEG['bridge'][1][0] if len(SEG['bridge'][1]) else BR
slide_door('BridgeDoorL', (BR, -.37, ZF + 1.1), .74, 'y', 70, sgn=-1); slide_door('BridgeDoorR', (BR, .37, ZF + 1.1), .74, 'y', 70, sgn=1)
xe_ = SEG['aft'][1][-1] if len(SEG['aft'][1]) else XS
slide_door('EngineDoorL', (xe_, -.55, ZA + 1.1), 1.1, 'y', 95, sgn=-1); slide_door('EngineDoorR', (xe_, .55, ZA + 1.1), 1.1, 'y', 95, sgn=1)
for nm, x, z in (('HdrBridge', BR, ZF + 2.3), ('HdrEngine', xe_, ZA + 2.3)): Box(nm + '_head', (x, 0, z), (.16, 2.4, .12), M_RIB)
def strip(name, pts, mat, r=.025):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p_, q in zip(sp.points, pts): p_.co = (*q, 1)
    o = bpy.data.objects.new(name, cu); col.objects.link(o); cu.materials.append(mat); return o
for s in (-1, 1):
    fl = [(float(x), s * (HW - .08), ZF + .03) for x in np.arange(-2.5, BR, .5)]; strip(f'FloorStrip{s}', fl, M_CYAN, .015)

# 6. crew rooms fit-out (sized from the lining profile)
for k, (x0, x1) in enumerate(ROOMS):
    xc = (x0 + x1) / 2; bl = min(2.0, x1 - x0 - 1.15); bx = x0 + .65 + bl / 2
    for s in (-1, 1):
        yo = outer_y(bx, s, ZF + .7); by = yo - s * .5
        Box(f'Bed{s}{k}', (bx, by, ZF + .25), (bl + .1, .95, .3), M_RIB)
        Box(f'Mattress{s}{k}', (bx, by, ZF + .46), (bl, .88, .14), M_FAB)
        Box(f'Blanket{s}{k}', (bx + .25, by, ZF + .54), (bl * .65, .9, .04), M_LIND)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x0 + .85, by, ZF + .6)); pw = bpy.context.active_object; pw.name = f'Pillow{s}{k}'; pw.scale = (.3, .6, .1)
        pw.modifiers.new('S', 'SUBSURF').levels = 2; pw.data.materials.append(M_WALL)
        Box(f'BedLight{s}{k}', (bx, yo - s * .06, ZF + .95), (bl * .8, .03, .03), M_AMBER)
        Box(f'Desk{s}{k}', (x1 - .33, s * (HW + .7), ZF + .75), (.5, .8, .05), M_RIB)
        Box(f'DeskLeg{s}{k}', (x1 - .33, s * (HW + .7), ZF + .37), (.05, .7, .74), M_RIB)
        Box(f'DeskScr{s}{k}', (x1 - .1, s * (HW + .7), ZF + 1.25), (.02, .7, .42), M_SCR if k % 2 else M_SCR2)
        Box(f'Stool{s}{k}', (x1 - .75, s * (HW + .7), ZF + .25), (.35, .35, .5), M_SEAT)
        Box(f'Locker{s}{k}', (x0 + .33, s * (HW + .4), ZF + 1.0), (.5, .6, 2.0), M_WALL)
        Box(f'LockerLine{s}{k}', (x0 + .59, s * (HW + .4), ZF + 1.0), (.01, .02, 1.8), M_AMBER)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=.15, location=(x1 - .4, s * (HW + .9), ZF + .93)); bpy.context.active_object.name = f'Helmet{s}{k}'; bpy.context.active_object.data.materials.append(M_WALL)
        Area(f'RoomL{s}{k}', (xc, s * (HW + 1.2), (ceil_at(xc, s * (HW + 1.2)) or (ZF + 2.4)) - .2), 1.2, 70, (1, .82, .62))

# ------------------------------------------------------------------ v8 WING DECK: real corridors behind the side doors, measured from the hull
FW = -0.5            # wing-corridor floor (steps up from the spine deck)
FP = 1.0             # pod floor (inside the side nacelles)
WY0, WY1 = 3.6, 5.0  # wing corridor between these |y|
WX0, WX1 = -4.0, 10.5
PX0, PX1, PY0, PY1 = -13.5, -6.5, 5.0, 8.6
WXA = -9.0; DOOR = (-8.6, -7.2)   # corridor runs aft to WXA; doorway into the pod   # pod room footprint (|y|)
def hceil(x, y, f, cap):
    d, h = ray((x, y, f + .3), (0, 0, 1), 14)
    return min(h.z - .3, f + cap) if d is not None else f + cap
def hfield(name, x0, x1, y0, y1, f, cap, step=.35, mat=None):
    nx = max(2, int((x1 - x0) / step) + 1); ny = max(2, int((y1 - y0) / step) + 1); bm = bmesh.new(); V = {}
    for i, x in enumerate(np.linspace(x0, x1, nx)):
        for j, y in enumerate(np.linspace(y0, y1, ny)): V[i, j] = bm.verts.new((float(x), float(y), hceil(float(x), float(y), f, cap)))
    for i in range(nx - 1):
        for j in range(ny - 1): bm.faces.new((V[i, j], V[i, j + 1], V[i + 1, j + 1], V[i + 1, j]))
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new(name, me_); col.objects.link(o)
    me_.materials.append(mat or M_LIN); o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons)); return o
def hwall(name, a_xy, b_xy, f, cap, gaps=(), header=2.25, step=.2, mat=None, fl=None):
    a = Vector((*a_xy, 0)); b = Vector((*b_xy, 0)); L = (b - a).length; d = (b - a).normalized(); bm = bmesh.new(); cols = []
    n = max(2, int(L / step) + 1)
    for i in range(n):
        t = i * L / (n - 1); p = a + d * t; f_ = fl(p.x) if fl else f; zt = hceil(p.x, p.y, f_, cap)
        g = any(g0 <= t <= g1 for g0, g1 in gaps); zb = f_ + header if g else f_ - .02
        cols.append((bm.verts.new((p.x, p.y, zb)), bm.verts.new((p.x, p.y, zt)), g) if zt > zb + .03 else None)
    for c0, c1 in zip(cols, cols[1:]):
        if c0 and c1 and c0[2] == c1[2]: bm.faces.new((c0[0], c1[0], c1[1], c0[1]))
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.08)
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new(name, me_); col.objects.link(o); me_.materials.append(mat or M_LIN); return o
def ramp_floor(x):   # corridor floor: flat FW, then climbs to the pod floor aft of WX0
    return FW if x >= WX0 else FW + (FP - FW) * min(1, (WX0 - x) / (WX0 - PX1))
X_START = WXA
# cut the passages through the mid lining
for xp in PASS:
    for s in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(xp, s * (HW + 2.0), (ZF + FW + 2.4) / 2)); cutter = bpy.context.active_object
        cutter.scale = (1.5, 3.6, FW + 2.4 - ZF + .1); cutter.name = f'Cut{s}{xp}'
        for ln in ('LiningMid',):
            lo = bpy.data.objects.get(ln)
            if lo:
                bpy.context.view_layer.objects.active = lo
                for m_ in list(lo.modifiers):
                    if m_.type == 'SOLIDIFY': bpy.ops.object.modifier_apply(modifier=m_.name)
                bo = lo.modifiers.new('Cut', 'BOOLEAN'); bo.operation = 'DIFFERENCE'; bo.object = cutter; bo.solver = 'EXACT'
                bpy.ops.object.modifier_apply(modifier=bo.name)
        bpy.data.objects.remove(cutter)
nstep = 9
for s in (-1, 1):
    # passages: steps, side walls, ceiling, door on the spine
    for k, xp in enumerate(PASS):
        for j in range(nstep):
            y0 = HW + .05 + j * (WY0 - HW - .05) / nstep; z = ZF + (j + 1) * (FW - ZF) / nstep
            Box(f'PStep{s}{k}{j}', (xp, s * (y0 + (WY0 - HW) / nstep / 2), (z + ZF) / 2), (1.4, (WY0 - HW) / nstep + .01, z - ZF), M_FLOOR)
            Box(f'PStepL{s}{k}{j}', (xp, s * (y0 + .02), z + .004), (1.3, .03, .01), M_AMBER)
        for e in (-1, 1): Box(f'PWall{s}{k}{e}', (xp + e * .75, s * (HW + WY0) / 2, (ZF + FW + 2.45) / 2), (.08, WY0 - HW, FW + 2.45 - ZF), M_WALL)
        Box(f'CeilStripP{s}{k}', (xp, s * (HW + WY0) / 2, FW + 2.45), (1.58, WY0 - HW, .08), M_WALL)
        Box(f'PLight{s}{k}', (xp, s * (HW + WY0) / 2, FW + 2.4), (.12, WY0 - HW - .4, .02), M_CYAN)
        for e in (-1, 1): Cyl(f'PRail{s}{k}{e}', (xp + e * .62, s * (HW + WY0) / 2, (ZF + FW) / 2 + .95), .025, math.hypot(WY0 - HW, FW - ZF), M_RIB, rot=(-s * math.degrees(math.atan2(FW - ZF, WY0 - HW)) + 90, 0, 0))
        slide_door(f'PassDoor{s}{k}', (xp, s * HW, ZF + 1.1), 1.3, 'x', 120 + k * 8)
    # wing corridor: floor, walls, ceiling that follows the hull, lights, screens
    xs_f = np.linspace(WXA, WX1, 60); bm = bmesh.new(); prev = None
    for x in xs_f:
        f_ = ramp_floor(float(x)); row = [bm.verts.new((float(x), s * WY0, f_)), bm.verts.new((float(x), s * WY1, f_))]
        if prev: bm.faces.new((prev[0], row[0], row[1], prev[1]))
        prev = row
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.1)
    me_ = bpy.data.meshes.new(f'WingFloor{s}'); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new(f'WingFloor{s}', me_); col.objects.link(o); me_.materials.append(M_FLOOR)
    gaps = [(xp - .7 - WXA, xp + .7 - WXA) for xp in PASS]
    hwall(f'WingWallIn{s}', (WXA, s * WY0), (WX1, s * WY0), FW, 3.2, gaps=gaps, header=2.45, fl=ramp_floor)
    hwall(f'WingWallOut{s}', (WXA, s * WY1), (WX1, s * WY1), FW, 3.2, gaps=[(DOOR[0] - WXA, DOOR[1] - WXA)], header=2.4, fl=ramp_floor)
    hwall(f'WingAftEnd{s}', (WXA, s * WY0), (WXA, s * WY1), FP, 3.2)
    hwall(f'WingEnd{s}', (WX1, s * WY0), (WX1, s * WY1), FW, 3.0)
    # ceiling: follows the hull; climbs with the ramp toward the pod
    cbm = hfield(f'CeilStripWing{s}', WX0, WX1, min(s * WY0, s * WY1), max(s * WY0, s * WY1), FW, 3.0)
    hfield(f'CeilStripWingR{s}', WXA, WX0, min(s * WY0, s * WY1), max(s * WY0, s * WY1), FP, 3.2)
    for x in np.arange(WXA + 1, WX1 - .5, 3.0):
        Area(f'WingL{s}{x:.0f}', (float(x), s * (WY0 + WY1) / 2, hceil(float(x), s * (WY0 + WY1) / 2, ramp_floor(float(x)), 3.0) - .15), .9, 60, (.8, .9, 1))
        Box(f'WingScr{s}{x:.0f}', (float(x) + 1.5, s * (WY1 - .05), ramp_floor(float(x) + 1.5) + 1.45), (.7, .02, .35), M_SCR if s > 0 else M_SCR2)
    strip(f'WingStrip{s}', [(float(x), s * (WY1 - .1), ramp_floor(float(x)) + .03) for x in np.linspace(WXA + .1, WX1 - .1, 40)], M_CYAN, .015)
    Box(f'WingView{s}', (WX1 - .06, s * (WY0 + WY1) / 2, FW + 1.4), (.02, 1.0, .7), M_SCR)
    # pod room inside the nacelle (port = mess hall, starboard = med bay + cargo)
    ya, yb = s * PY0, s * PY1; Y0, Y1 = min(ya, yb), max(ya, yb)
    Box(f'PodFloor{s}', ((PX0 + PX1) / 2, s * (PY0 + PY1) / 2, FP - .05), (PX1 - PX0, PY1 - PY0, .1), M_FLOOR)
    hwall(f'PodWallOut{s}', (PX0, yb), (PX1, yb), FP, 4.5)
    hwall(f'PodWallIn{s}', (PX0, ya), (WXA, ya), FP, 4.5)
    hwall(f'PodWallAft{s}', (PX0, ya), (PX0, yb), FP, 4.5)
    hwall(f'PodWallFwd{s}', (PX1, ya), (PX1, yb), FP, 4.5)
    hfield(f'CeilStripPod{s}', PX0, PX1, Y0, Y1, FP, 4.5, step=.4)
    slide_door(f'PodDoor{s}', ((DOOR[0] + DOOR[1]) / 2, s * WY1, FP + 1.1), DOOR[1] - DOOR[0] - .05, 'x', 150)
    for x in (PX0 + 1.8, (PX0 + PX1) / 2, PX1 - 1.8):
        Area(f'PodL{s}{x:.0f}', (x, s * (PY0 + PY1) / 2, hceil(x, s * (PY0 + PY1) / 2, FP, 4.5) - .2), 1.6, 160, (1, .88, .7) if s > 0 else (.8, .92, 1))
    ym = s * (PY0 + PY1) / 2
    if s > 0:   # MESS: long table, benches, galley counter, screen
        Box('MessTable', ((PX0 + PX1) / 2, ym, FP + .74), (4.2, .9, .06), M_RIB); Box('MessTableLeg', ((PX0 + PX1) / 2, ym, FP + .37), (3.8, .12, .72), M_RIB)
        for e in (-1, 1): Box(f'MessBench{e}', ((PX0 + PX1) / 2, ym + e * .8, FP + .23), (4.0, .38, .46), M_SEAT)
        for k in range(5): Cyl(f'MessCup{k}', ((PX0 + PX1) / 2 - 1.6 + k * .8, ym + (k % 2 - .5) * .3, FP + .82), .04, .1, M_WALL)
        Box('Galley', (PX0 + .45, ym, FP + .46), (.7, PY1 - PY0 - .6, .92), M_WALL); Box('GalleyTop', (PX0 + .45, ym, FP + .94), (.74, PY1 - PY0 - .55, .04), M_RIB)
        Box('GalleyScr', (PX0 + .05, ym, FP + 1.6), (.02, 1.6, .7), M_SCR2)
        Box('MessSign', (PX1 - .06, s * (PY1 - .9), FP + 2.0), (.02, .9, .25), M_SCR2)
    else:       # MED BAY + CARGO: two med beds with scanner arches, cabinets, crates
        for k, x in enumerate((PX1 - 1.6, PX1 - 3.6)):
            Box(f'MedBed{k}', (x, ym, FP + .45), (2.0, .85, .14), M_WALL); Box(f'MedBase{k}', (x, ym, FP + .2), (1.2, .4, .4), M_RIB)
            arch = bpy.ops.mesh.primitive_torus_add(major_radius=.75, minor_radius=.05, location=(x, ym, FP + .5), rotation=(0, math.radians(90), 0)); ao = bpy.context.active_object; ao.name = f'MedArch{k}'; ao.data.materials.append(M_CYAN)
            Box(f'MedScr{k}', (x, ym + s * -.0 + (PY1 - PY0) / 2 * s * -1 + s * .0 if False else s * (PY1 - .06), FP + 1.5), (.8, .02, .5), M_SCR)
        Box('MedCab', (PX1 - 2.6, s * (PY0 + .35), FP + 1.0), (2.2, .5, 2.0), M_WALL)
        for k in range(6): Box(f'Cargo{k}', (PX0 + .6 + (k % 3) * 1.05, ym + (k // 3 - .5) * 1.1, FP + .45), (.95, .95, .9), M_RIB if k % 2 else M_THR)
        Box('CargoNet', (PX0 + 3.5, ym, FP + 1.2), (.02, PY1 - PY0 - .3, 2.4), M_LIND)

# hall: handrails, wall screens, emergency lights, lights
for s in (-1, 1):
    Cyl(f'Handrail{s}', ((BR - 2.6 * G) / 2, s * (HW - .1), ZF + .95), .025, BR + 2.6 * G - .4, M_RIB, rot=(0, 90, 0))
    for x in (-1.2 * G, 2.6, 4.3, 6.4): Box(f'HallScr{s}{x}', (x, s * (HW - .06), ZF + 1.45), (.55, .02, .3), M_SCR)
for x in (-1.0 * G, 2.0 * G, 5.5 * G, 7.5 * G): Area(f'HallL{x}', (x, 0, (ceil_at(x, 0, ZF + .1) or 2) - .15), 1.0, 80, (.8, .9, 1))
# bridge under the real canopy: seats + consoles placed relative to where the deck ends in the nose
print('MODEL bridge', BR, '->', round(nose_end, 2))
def seat(name, x, y, z):
    Box(name + '_base', (x, y, z + .22), (.28, .28, .44), M_RIB); Box(name + '_seat', (x, y, z + .5), (.6, .55, .1), M_SEAT, rot=(0, -6, 0))
    Box(name + '_back', (x - .3, y, z + .95), (.1, .55, .85), M_SEAT, rot=(0, -12, 0))
    for s in (-1, 1): Box(name + f'_arm{s}', (x, y + s * .3, z + .72), (.5, .06, .06), M_RIB)
px = nose_end - 2.3
seat('Captain', px - 2.2, 0, ZB)
Cyl('HoloBase', (px - 1.0, 0, ZB + .25), .32, .5, M_RIB)
holo = Cyl('HoloGlobe', (px - 1.0, 0, ZB + .95), .24, .5, M_CYAN, v=32); holo.scale.z = .3
for x in (px - 2.0, px): Area(f'BrL{x}', (x, 0, (ceil_at(x, 0, ZB + .1) or 2) - .15), 1.4, 90, (.75, .9, 1))
# engine room: rebuilt in the v9 detail pass
# boarding ramp under the hatch (hinged at its aft edge, forward end lowers 40-100)
ramp_piv = bpy.data.objects.new('RampPivot', None); col.objects.link(ramp_piv); ramp_piv.location = (HATCH[0], 0, ZF - .1)
rp = Box('Ramp', (0, 0, ZF - .15), (HATCH[1] - HATCH[0], 2 * HATCH[2] - .15, .12), M_FLOOR); rp.parent = ramp_piv; rp.matrix_parent_inverse = ramp_piv.matrix_world.inverted()
for i in range(7):
    r_ = Box(f'RampTread{i}', (HATCH[0] + .3 + i * .5, 0, ZF - .085), (.06, 1.7, .03), M_AMBER); r_.parent = ramp_piv; r_.matrix_parent_inverse = ramp_piv.matrix_world.inverted()
ramp_piv.keyframe_insert('rotation_euler', frame=40); ramp_piv.rotation_euler.y = min(math.radians(55), math.asin(min(.95, (ZF - (float(W[:, 2].min()) - 2.1)) / (HATCH[1] - HATCH[0])))); ramp_piv.keyframe_insert('rotation_euler', frame=100)
Area('RampSpill', (0, 0, ZF + .6), 2.0, 250, (1, .8, .55))

# ------------------------------------------------------------------ EXTERIOR engineering
xmin, xmax = W[:, 0].min(), W[:, 0].max()
aft = W[W[:, 0] < xmin + 1.2]
# thrusters: three nozzles (centre + pair) at the aft face, placed from the hull's actual aft geometry
def mid_z(yc):
    s = aft[np.abs(aft[:, 1] - yc) < 1.0]
    return float(s[:, 2].mean()) if len(s) else 0.5
for i, yc in enumerate((0.0, -4.5 * G, 4.5 * G)):
    x0 = float(xmin) + .6; z0 = mid_z(yc); r = (1.0 if i == 0 else .75) * G
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
for i, (x, y) in enumerate(((9.0 * K * G, 0), (-6.0 * K * G, -3.0 * K * G), (-6.0 * K * G, 3.0 * K * G))):
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

Zup = Vector((0, 0, 1))
print('MODEL greebles 0 (removed v6)')
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
# ------------------------------------------------------------------ v9 DETAIL PASS: working controls, real engine room, room fit-out
from mathutils import Euler, Matrix
def piv(name, loc):
    e = bpy.data.objects.new(name, None); col.objects.link(e); e.location = loc; e.empty_display_size = .08; bpy.context.view_layer.update(); return e
def att(o, e): o.parent = e; o.matrix_parent_inverse = e.matrix_world.inverted()
def keyv(e, idx, fv, path='rotation_euler', lin=False):
    for f, v in fv:
        getattr(e, path)[idx] = v; e.keyframe_insert(path, index=idx, frame=f)
    if lin and e.animation_data and e.animation_data.action:
        try:
            for fc in e.animation_data.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
        except Exception: pass
def soft(o, lv=2):
    o.modifiers.new('S', 'SUBSURF').levels = lv; o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons)); return o
def Tor(name, c, R, r, mat, rot=(0, 0, 0), ms=32, ns=10):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=c, rotation=[math.radians(a) for a in rot], major_segments=ms, minor_segments=ns)
    o = bpy.context.active_object; o.name = name; o.data.materials.append(mat); o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons)); return o
def onp(c, rot_deg, off):   # point on a tilted panel
    return tuple(Vector(c) + Euler([math.radians(a) for a in rot_deg]).to_matrix() @ Vector(off))
M_GRIP = pbsdf('Grip', (.03, .03, .035), .1, .7); M_STRAP = pbsdf('Strap', (.6, .25, .05), 0, .7); M_COPPER = pbsdf('Copper', (.75, .4, .2), 1, .3)
M_REDP = pbsdf('RedPaint', (.6, .03, .02), .1, .4); M_GLASS = pbsdf('PlasmaPort', (.3, .8, 1), 0, .1, (.3, .8, 1), 6)

# ---- PILOT STATIONS (each control is a named part on its own pivot, keyframed so it really moves)
def pilot_seat(nm, x, y, z):
    Cyl(nm + '_pedestal', (x, y, z + .16), .12, .32, M_RIB); Box(nm + '_rail', (x, y, z + .02), (.6, .3, .04), M_RIB)
    soft(Box(nm + '_pan', (x + .02, y, z + .42), (.5, .5, .1), M_SEAT, rot=(0, -6, 0)))
    soft(Box(nm + '_back', (x - .26, y, z + .9), (.1, .5, .8), M_SEAT, rot=(0, -14, 0)))
    soft(Box(nm + '_head', (x - .37, y, z + 1.42), (.09, .3, .2), M_SEAT, rot=(0, -14, 0)))
    for e in (-1, 1):
        soft(Box(nm + f'_bolster{e}', (x - .2, y + e * .25, z + .85), (.12, .07, .6), M_SEAT, rot=(0, -14, 0)), 1)
        Box(nm + f'_arm{e}', (x + .02, y + e * .33, z + .68), (.45, .09, .05), M_RIB)
        Box(nm + f'_strap{e}', (x - .12, y + e * .11, z + .95), (.03, .05, .7), M_STRAP, rot=(e * 4, -24, 0))
    Box(nm + '_lap', (x + .05, y, z + .5), (.04, .48, .05), M_STRAP); Cyl(nm + '_buckle', (x + .08, y, z + .62), .045, .02, M_GOLD, rot=(0, 90, 0))
px = nose_end - 2.3
for s in (-1, 1):
    yc = s * .7; pilot_seat(f'Pilot{s}', px, yc, ZB)
    # side-stick on the outer armrest: pitch + roll pivot at the boot
    st = piv(f'Ctrl_Stick_{s}', (px + .2, yc + s * .33, ZB + .71))
    parts = [Cyl(f'StickBoot{s}', (px + .2, yc + s * .33, ZB + .74), .04, .06, M_GRIP), Cyl(f'StickShaft{s}', (px + .2, yc + s * .33, ZB + .82), .012, .12, M_RIB),
             soft(Box(f'StickGrip{s}', (px + .21, yc + s * .33, ZB + .93), (.05, .045, .12), M_GRIP, rot=(0, 10, 0))),
             Box(f'StickTrigger{s}', (px + .24, yc + s * .33, ZB + .93), (.015, .02, .03), M_RED), Cyl(f'StickHat{s}', (px + .215, yc + s * .33, ZB + 1.0), .01, .015, M_RIB),
             Cyl(f'StickBtn{s}', (px + .2, yc + s * .33 - s * .015, ZB + 1.0), .008, .012, M_REDP)]
    for o in parts: att(o, st)
    keyv(st, 1, [(1, 0), (160, 0), (185, .22), (205, -.15), (225, .12), (240, 0)]); keyv(st, 0, [(1, 0), (170, 0), (195, s * .2), (215, -s * .18), (240, 0)])
    # throttle on the inner armrest: lever in a slotted track, pushes forward for the burn
    Box(f'ThrTrack{s}', (px + .12, yc - s * .33, ZB + .715), (.28, .05, .03), M_RIB); Box(f'ThrSlot{s}', (px + .12, yc - s * .33, ZB + .731), (.24, .012, .004), M_SEAT)
    th = piv(f'Ctrl_Throttle_{s}', (px + .05, yc - s * .33, ZB + .72))
    for o in (Box(f'ThrLever{s}', (px + .05, yc - s * .33, ZB + .79), (.018, .018, .14), M_RIB), soft(Box(f'ThrKnob{s}', (px + .06, yc - s * .33, ZB + .87), (.07, .05, .05), M_GRIP))): att(o, th)
    keyv(th, 1, [(1, 0), (175, 0), (200, .55), (240, .55)])
    # rudder pedals on hinges
    for e in (-1, 1):
        pd = piv(f'Ctrl_Pedal_{s}_{"L" if e < 0 else "R"}', (px + .82, yc + e * .13, ZB + .04))
        att(Box(f'Pedal{s}{e}', (px + .76, yc + e * .13, ZB + .16), (.03, .1, .24), M_RIB, rot=(0, -25, 0)), pd); att(Box(f'PedalGrip{s}{e}', (px + .745, yc + e * .13, ZB + .16), (.01, .09, .2), M_GRIP, rot=(0, -25, 0)), pd)
        keyv(pd, 1, [(1, 0), (180, 0), (195, e * .12), (215, -e * .1), (240, 0)])
    # instrument panel: two MFDs with bezel keys, glareshield, angled
    Box(f'PanelBase{s}', (px + 1.15, yc, ZB + .45), (.45, .95, .9), M_RIB)
    pc = (px + 1.05, yc, ZB + 1.1); rot = (0, -22, 0)
    Box(f'PanelFace{s}', pc, (.05, 1.0, .42), M_RIB, rot=rot)
    for j, dy in enumerate((-.24, .24)):
        Box(f'MFDBezel{s}{j}', onp(pc, rot, (-.03, dy, 0)), (.02, .42, .34), M_SEAT, rot=rot)
        Box(f'MFD{s}{j}', onp(pc, rot, (-.042, dy, .0)), (.005, .32, .25), M_SCR if j == 0 else M_SCR2, rot=rot)
        for b in range(5):
            for zz in (-.15, .15): Box(f'MFDKey{s}{j}{b}{zz}', onp(pc, rot, (-.045, dy - .13 + b * .065, zz)), (.012, .04, .02), M_RIB, rot=rot)
    soft(Box(f'Glare{s}', onp(pc, rot, (.02, 0, .26)), (.3, 1.05, .04), M_SEAT, rot=(0, -6, 0)), 1)
    yo = outer_y(px - 1.5, s, ZB + 1.0)
    Box(f'SideStation{s}', (px - 1.5, yo - s * .45, ZB + .5), (1.6, .6, 1.0), M_RIB)
    Box(f'SideScr{s}', (px - 1.5, yo - s * .16, ZB + 1.3), (1.4, .02, .55), M_SCR2)
# centre pedestal: landing-gear lever (drops with the gear, frames 1-30) + flap/thrust-mode levers
Box('Pedestal', (px + .55, 0, ZB + .33), (.9, .32, .66), M_RIB); Box('PedestalTop', (px + .55, 0, ZB + .67), (.86, .3, .02), M_SEAT)
gl = piv('Ctrl_GearLever', (px + .85, .08, ZB + .68))
for o in (Box('GearLeverShaft', (px + .85, .08, ZB + .76), (.015, .015, .16), M_RIB), Cyl('GearLeverWheel', (px + .85, .08, ZB + .85), .03, .02, M_WALL, rot=(90, 0, 0))): att(o, gl)
keyv(gl, 1, [(1, -.5), (12, .5)])
for k in range(3):
    lv = piv(f'Ctrl_ModeLever_{k}', (px + .4 + k * .1, -.08, ZB + .68))
    for o in (Box(f'ModeShaft{k}', (px + .4 + k * .1, -.08, ZB + .74), (.012, .012, .12), M_RIB), Box(f'ModeKnob{k}', (px + .4 + k * .1, -.08, ZB + .8), (.04, .03, .025), (M_CYAN, M_AMBER, M_WALL)[k])): att(o, lv)
    keyv(lv, 1, [(1, -.35), (150 + k * 6, -.35), (158 + k * 6, .35)])
# overhead switch panel: 3 rows x 6 toggles, flipped in sequence during start-up
zc = (ceil_at(px + .3, 0, ZB + .1) or ZB + 2.0) - .12
Box('OverheadPanel', (px + .3, 0, zc), (.75, .9, .06), M_RIB)
for r_ in range(3):
    for k in range(6):
        sx, sy = px + .05 + r_ * .25, -.35 + k * .14
        sw = piv(f'Ctrl_Switch_{r_}{k}', (sx, sy, zc - .03))
        att(Cyl(f'SwTog{r_}{k}', (sx, sy, zc - .055), .006, .05, M_WALL, v=8), sw); Box(f'SwGuard{r_}{k}', (sx, sy, zc - .035), (.04, .05, .01), M_SEAT)
        att(Cyl(f'SwTip{r_}{k}', (sx, sy, zc - .08), .009, .012, (M_RED, M_AMBER, M_GREEN)[r_], v=8), sw)
        keyv(sw, 1, [(1, -.45), (130 + (r_ * 6 + k) * 2, -.45), (132 + (r_ * 6 + k) * 2, .45)])
# bridge floor plate (covers the hull tear) following the deck outline
zf_, xs_b, A_b, _ = SEG['bridge']
if len(xs_b) > 1:
    bm = bmesh.new(); prev = None
    for x, a in zip(xs_b, A_b):
        row = [bm.verts.new((float(x), -float(a) + .05, ZB + .045)), bm.verts.new((float(x), float(a) - .05, ZB + .045))]
        if prev: bm.faces.new((prev[0], row[0], row[1], prev[1]))
        prev = row
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.04)
    me_ = bpy.data.meshes.new('BridgePlate'); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new('BridgePlate', me_); col.objects.link(o); me_.materials.append(M_FLOOR)
for s in (-1, 1): Box(f'BridgeRunner{s}', ((BR + nose_end) / 2, s * .3, ZB + .07), (nose_end - BR - 1, .03, .01), M_CYAN)

# ---- ENGINE ROOM: compact tokamak fusion core feeding a magnetic nozzle
EX = -10.0 * G; zc_ = ZA + 1.75
Cyl('CryoBase', (EX, 0, ZA + .15), 1.75, .3, M_RIB, v=48); Tor('CryoBaseLip', (EX, 0, ZA + .3), 1.72, .04, M_AMBER, ms=48)
Tor('VacuumVessel', (EX, 0, zc_), 1.05, .42, M_THR, ms=64, ns=24)
for k in range(8):   # viewing ports onto the plasma
    a = k * math.pi / 4; Cyl(f'PlasmaPort{k}', (EX + 1.47 * math.cos(a), 1.47 * math.sin(a), zc_), .09, .03, M_GLASS, rot=(0, 90, math.degrees(a)))
Cyl('CentralSolenoid', (EX, 0, zc_), .32, 2.7, M_RIB, v=32)
for k in range(5): Tor(f'SolenoidBand{k}', (EX, 0, zc_ - 1.0 + k * .5), .33, .02, M_CYAN if k % 2 else M_COPPER, ms=32, ns=8)
for k in range(12):   # toroidal-field coils (D-shaped, copper) around the vessel
    a = k * math.pi / 6; t = Tor(f'TFCoil{k}', (EX + 1.05 * math.cos(a), 1.05 * math.sin(a), zc_), .6, .06, M_COPPER, rot=(90, 0, math.degrees(a)), ms=32, ns=8); t.scale = (1.0, 1.0, 1.0); t.scale[1] = 1.0
    t.scale = (.9, 1.0, 1.3) if False else t.scale
for z in (zc_ - .75, zc_ + .75): Tor(f'PFCoil{z:.1f}', (EX, 0, z), 1.62, .07, M_COPPER, ms=64)
for k in range(6):
    a = k * math.pi / 3 + math.pi / 6; Cyl(f'CryoColumn{k}', (EX + 1.75 * math.cos(a), 1.75 * math.sin(a), (ZA + .3 + zc_ + 1.1) / 2), .06, zc_ + 1.1 - ZA - .3, M_RIB)
Tor('CryoTopRing', (EX, 0, zc_ + 1.1), 1.75, .06, M_RIB, ms=48)
Box('NBInjector', (EX + 1.6, -1.2, zc_), (1.1, .45, .45), M_THR, rot=(0, 0, -30)); Cyl('NBDuct', (EX + 1.15, -.75, zc_), .12, .7, M_RIB, rot=(0, 90, -30))
# heat exchangers (finned) and turbopumps, joined by flanged coolant loops
def pipe(name, pts, r, mat=M_PIPE):
    strip(name, pts, mat, r)
    for i_, p_ in enumerate((pts[0], pts[-1])):
        d_ = Vector(pts[1]) - Vector(pts[0]) if i_ == 0 else Vector(pts[-1]) - Vector(pts[-2]); q = Vector((0, 0, 1)).rotation_difference(d_.normalized())
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=r * 1.6, depth=.06, location=p_); fo = bpy.context.active_object; fo.rotation_mode = 'QUATERNION'; fo.rotation_quaternion = q; fo.name = name + f'_fl{i_}'; fo.data.materials.append(M_RIB)
for s in (-1, 1):
    hx, hy = EX - 3.6, s * 1.75
    Box(f'HeatX{s}', (hx, hy, ZA + 1.1), (1.3, .7, 1.8), M_RIB)
    for k in range(14): Box(f'HXFin{s}{k}', (hx - .6 + k * .092, hy - s * .36, ZA + 1.1), (.02, .04, 1.65), M_THR)
    px_, py_ = EX + 3.2, s * 1.6
    Cyl(f'PumpHousing{s}', (px_, py_, ZA + .55), .32, .7, M_THR, rot=(0, 90, 0)); Cyl(f'PumpMotor{s}', (px_ + .55, py_, ZA + .55), .24, .45, M_RIB, rot=(0, 90, 0))
    for e in (-1, 1): Tor(f'PumpFlange{s}{e}', (px_ + e * .35, py_, ZA + .55), .33, .03, M_RIB, rot=(0, 90, 0), ms=24, ns=6)
    imp = piv(f'Anim_PumpRotor_{s}', (px_ - .37, py_, ZA + .55))
    for b in range(6): att(Box(f'PumpBlade{s}{b}', (px_ - .37, py_, ZA + .55), (.02, .5, .07), M_GOLD, rot=(b * 30, 0, 0)), imp)
    keyv(imp, 0, [(1, 0), (240, 240 * .35)], lin=True)
    Box(f'PumpSkid{s}', (px_ + .2, py_, ZA + .1), (1.3, .7, .2), M_RIB)
    pipe(f'HotLeg{s}', [(EX + s * 0, s * 1.47, zc_ - .2), (EX - 1.2, s * 1.9, zc_ - .1), (hx + .5, hy, ZA + 1.8)], .09, M_COPPER)
    pipe(f'ColdLeg{s}', [(hx + .5, hy, ZA + .4), (EX, s * 2.2, ZA + .4), (px_ - .4, py_, ZA + .55)], .08)
    pipe(f'Return{s}', [(px_ + .2, py_, ZA + .87), (EX + 1.4, s * 1.3, zc_ + .5), (EX + .8, s * .8, zc_ + .3)], .07)
    # power conduits running aft to the nozzle plenum
    for j in range(3): strip(f'PowerConduit{s}{j}', [(EX - 1.2, s * (.5 + j * .2), ZA + .32), (EX - 4.8, s * (.5 + j * .2), ZA + .32), (SEG['aft'][1][0] + 1.2, s * (.4 + j * .15), ZA + .9)], M_CABLE, .05)
    # coolant headers along the hull side
    for j, z in enumerate((.35, .7)):
        pts = [(float(x), outer_y(float(x), s, ZA + z) - s * (.15 + .1 * j), ZA + z) for x in np.arange(SEG['aft'][1][0] + .3, SEG['aft'][1][-1] - .3, .5)]
        strip(f'Coolant{s}{j}', pts, M_PIPE, .06)
    # grated catwalk + rail around the core
for k in range(24):
    a = k * math.pi / 12; Box(f'Grate{k}', (EX + 2.05 * math.cos(a), 2.05 * math.sin(a), ZA + .02), (.5, .3, .02), M_GRBD, rot=(0, 0, math.degrees(a) + 90))
    if k % 3 == 0 and not (-.6 < math.sin(a) < .6 and math.cos(a) > 0): Cyl(f'CorePost{k}', (EX + 2.2 * math.cos(a), 2.2 * math.sin(a), ZA + .55), .025, 1.0, M_RIB)
Tor('CoreRail', (EX, 0, ZA + 1.05), 2.2, .025, M_AMBER, ms=64, ns=6)
Tor('CoreHazard', (EX, 0, ZA + .01), 1.85, .05, M_AMBER, ms=64, ns=4)
# magnetic nozzle plenum at the aft bulkhead
xa = SEG['aft'][1][0] + .9
Cyl('Plenum', (xa, 0, ZA + 1.3), .85, 1.4, M_THR, rot=(0, 90, 0), v=40)
for k in range(4): Tor(f'PlenumCoil{k}', (xa - .5 + k * .33, 0, ZA + 1.3), .9, .06, M_COPPER, rot=(0, 90, 0), ms=40, ns=8)
# engineering station
ex_ = EX + 4.6
Box('EngDesk', (ex_, -1.5, ZA + .5), (.6, 1.2, 1.0), M_RIB); Box('EngDeskTop', (ex_ - .05, -1.5, ZA + 1.0), (.7, 1.25, .04), M_SEAT, rot=(0, -15, 0))
for j, dy in enumerate((-.4, 0, .4)): Box(f'EngMon{j}', (ex_ + .2, -1.5 + dy, ZA + 1.45), (.02, .36, .26), M_SCR2 if j == 1 else M_SCR, rot=(0, -10, (dy * -25)))
Box('EngKeys', (ex_ - .12, -1.5, ZA + 1.03), (.18, .45, .015), M_GRIP, rot=(0, -15, 0))
pilot_seat('EngChair', ex_ - .7, -1.5, ZA)
for x in (EX - 2.5, EX, EX + 2.5): Area(f'EnL{x:.1f}', (x, 0, (ceil_at(x, 0, ZA + .1) or ZA + 3) - .15), 1.4, 160, (.7, .85, 1))
ld = bpy.data.lights.new('ReactorLight', 'POINT'); ld.energy = 500; ld.color = (.35, .8, 1); ld.shadow_soft_size = .3
lo = bpy.data.objects.new('ReactorLight', ld); col.objects.link(lo); lo.location = (EX + 1.9, 0, zc_)

# ---- CABIN fit-out
for k, (x0, x1) in enumerate(ROOMS):
    bl = min(2.0, x1 - x0 - 1.15); bx = x0 + .65 + bl / 2; xc = (x0 + x1) / 2
    for s in (-1, 1):
        yo = outer_y(bx, s, ZF + .7); by = yo - s * .5; yd = s * (HW + .7)
        Box(f'Shelf{s}{k}', (x1 - .3, yd, ZF + 1.75), (.24, .8, .025), M_RIB)
        for b in range(6): Box(f'Book{s}{k}{b}', (x1 - .3, yd - .32 + b * .1 + (b > 3) * .04, ZF + 1.86 - (b == 2) * .02), (.18, .04 + (b % 2) * .015, .2 - (b % 3) * .03), (M_REDP, M_LIND, M_STRAP, M_SEAT)[b % 4])
        Box(f'Frame{s}{k}x', (x1 - .45, yd - s * .25, ZF + .87), (.02, .12, .15), M_GOLD, rot=(0, -12, 0)) if False else None
        Box(f'Photo{s}{k}', (x1 - .45, yd - s * .25, ZF + .87), (.02, .12, .15), M_SCR2, rot=(0, -12, 0))
        Box(f'Rug{s}{k}', (xc, s * (HW + .9), ZF + .006), (1.3, .8, .01), M_STRAP if k % 2 else M_LIND)
        Box(f'Nightstand{s}{k}', (min(bx + bl / 2 + .25, x1 - .7), by, ZF + .27), (.38, .42, .54), M_WALL)
        Cyl(f'LampBase{s}{k}', (min(bx + bl / 2 + .25, x1 - .7), by, ZF + .6), .05, .12, M_RIB); bpy.ops.mesh.primitive_uv_sphere_add(radius=.07, location=(min(bx + bl / 2 + .25, x1 - .7), by, ZF + .72)); bpy.context.active_object.name = f'LampBulb{s}{k}'; bpy.context.active_object.data.materials.append(M_AMBER)
        Cyl(f'Hook{s}{k}', (x0 + .62, s * (HW + .78), ZF + 1.7), .012, .1, M_RIB, rot=(90, 0, 0))
        soft(Box(f'Jacket{s}{k}', (x0 + .64, s * (HW + .8), ZF + 1.35), (.08, .42, .7), M_FAB), 1)
        zv = (ceil_at(xc, s * (HW + .9)) or ZF + 2.4) - .03
        Box(f'Vent{s}{k}', (xc, s * (HW + .9), zv), (.4, .25, .02), M_RIB)
        for v in range(5): Box(f'VentSlat{s}{k}{v}', (xc - .16 + v * .08, s * (HW + .9), zv - .012), (.015, .22, .01), M_SEAT)
        Box(f'CabinScr{s}{k}', (xc, s * (HW + .07), ZF + 1.5), (.5, .02, .3), M_SCR if k % 2 else M_SCR2)
# ---- MESS fit-out
ym = (PY0 + PY1) / 2; xm = (PX0 + PX1) / 2
for k in range(6): Cyl(f'Plate{k}', (xm - 1.5 + k * .6, ym + (k % 2 - .5) * .45, FP + .78), .12, .012, M_WALL, v=24)
for k in range(3): Box(f'Tray{k}', (xm - 1.2 + k * 1.2, ym, FP + .78), (.4, .3, .015), M_LIND)
Box('FoodDispenser', (PX0 + .45, ym + 1.2, FP + 1.55), (.5, .9, .9), M_RIB); Box('DispSlot', (PX0 + .71, ym + 1.2, FP + 1.35), (.02, .4, .25), M_SEAT); Box('DispScr', (PX0 + .71, ym + 1.2, FP + 1.8), (.02, .5, .25), M_SCR)
Box('Fridge', (PX0 + .45, ym - 1.25, FP + 1.0), (.6, .7, 2.0), M_WALL); Box('FridgeHandle', (PX0 + .77, ym - .95, FP + 1.1), (.03, .03, .6), M_RIB)
Cyl('Tap', (PX0 + .55, ym, FP + 1.05), .015, .2, M_RIB); Box('Sink', (PX0 + .45, ym, FP + .93), (.4, .4, .04), M_THR)
for k in range(3):
    zv = hceil(xm - 2 + k * 2, ym, FP, 4.5) - .03; Box(f'MessVent{k}', (xm - 2 + k * 2, ym, zv), (.6, .3, .02), M_RIB)
Box('MessMenu', (xm, PY1 - .06, FP + 1.7), (1.4, .02, .6), M_SCR2)
for k in range(3): soft(Box(f'MessPlant{k}', (PX1 - .5, PY1 - .5 - k * .02, FP + .4 + k * .12), (.3, .3, .3), M_GREEN), 2) if k == 0 else None
# ---- MED BAY: one bed + scanner, monitor arm, IV, drawers, sink (second bed removed to clear the room)
for nm in ('MedBed1', 'MedBase1', 'MedArch1', 'MedScr1'):
    o = bpy.data.objects.get(nm)
    if o: bpy.data.objects.remove(o)
mx = PX1 - 1.6; my = -ym
Cyl('MonArmPost', (mx + 1.0, my - .6, FP + 1.0), .03, 2.0, M_RIB); Box('MonArm', (mx + .7, my - .5, FP + 1.7), (.6, .04, .04), M_RIB); Box('MedMonitor', (mx + .4, my - .45, FP + 1.55), (.03, .45, .32), M_SCR, rot=(0, 0, 20))
Cyl('IVPole', (mx - .9, my + .55, FP + .9), .015, 1.8, M_RIB); Box('IVBag', (mx - .9, my + .55, FP + 1.65), (.04, .12, .2), M_GLASS)
Box('MedDrawers', (mx - 2.4, -(PY1 - .35), FP + .45), (1.4, .5, .9), M_WALL)
for d in range(3): Box(f'MedDrawer{d}', (mx - 2.4, -(PY1 - .6), FP + .2 + d * .28), (1.3, .01, .02), M_RIB)
Box('MedSink', (mx - 2.4, -(PY1 - .35), FP + .92), (.4, .35, .04), M_THR); Box('MedCross', (mx, -(PY1 - .06), FP + 2.2), (.25, .02, .08), M_REDP); Box('MedCross2', (mx, -(PY1 - .06), FP + 2.2), (.08, .02, .25), M_REDP)
for k in range(2): Box(f'CargoStrap{k}', (PX0 + .6 + k * 1.05, -ym, FP + .45), (.97, .97 + .02, .05), M_STRAP)
# ---- CORRIDOR accessories
for s in (-1, 1):
    for x in np.arange(WXA + .6, WX1, 1.2):
        if any(abs(x - xp) < .9 for xp in PASS) or DOOR[0] - .2 < x < DOOR[1] + .2: continue
        Box(f'WingSeam{s}{x:.1f}', (float(x), s * (WY1 - .045), ramp_floor(float(x)) + 1.2), (.02, .01, 2.2), M_LIND)
    for xp in PASS:
        Cyl(f'Extinguisher{s}{xp}', (xp + 1.1, s * (WY1 - .12), FW + .45), .07, .45, M_REDP); Box(f'EmLocker{s}{xp}', (xp - 1.3, s * (WY1 - .14), FW + 1.0), (.5, .2, .9), M_WALL)
        Box(f'EmLockerLine{s}{xp}', (xp - 1.3, s * (WY1 - .25), FW + 1.42), (.48, .01, .04), M_REDP)
    Box(f'PodSign{s}', ((DOOR[0] + DOOR[1]) / 2, s * (WY1 - .05), FP + 2.55), (.9, .02, .18), M_SCR2 if s > 0 else M_SCR)
    for x in np.arange(WX0 + .5, WX1 - .3, .9): Box(f'WingGrate{s}{x:.1f}', (float(x), s * (WY0 + WY1) / 2, FW + .003), (.8, .5, .006), M_GRBD)

# ------------------------------------------------------------------ v10 AERO + GEAR DOORS + BRIDGE FIXES
M_ORNG = pbsdf('LiveryOrange', (1.0, .3, .03), .2, .35); M_WHT = pbsdf('LiveryWhite', (.8, .81, .83), .25, .38); M_CHR = pbsdf('LiveryChar', (.055, .06, .07), .3, .4)
def fin(name, root, chord_r, chord_t, span, sweep, dirv, th, mat):
    # swept trapezoid fin: root along x at 'root', grows along dirv
    d = Vector(dirv).normalized(); rx = Vector(root)
    pts = [rx + Vector((chord_r * .5, 0, 0)), rx + Vector((-chord_r * .5, 0, 0)), rx + d * span + Vector((-sweep - chord_t * .5, 0, 0)), rx + d * span + Vector((-sweep + chord_t * .5, 0, 0))]
    bm = bmesh.new(); vs = [bm.verts.new(p) for p in pts]; bm.faces.new(vs)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=th)
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new(name, me_); col.objects.link(o); me_.materials.append(mat)
    o.modifiers.new('B', 'BEVEL').width = th * .45; return o
# canted winglets on both wingtips (cut tip vortices) + ventral strakes (yaw stability)
for nm, idx, s in (('WingletPort', W[:, 1].argmax(), 1), ('WingletStbd', W[:, 1].argmin(), -1)):
    tip = Vector(W[idx]); tip.y -= s * .25
    fin(nm, tip, 4.2, 1.6, 3.0, 2.4, (0, s * .26, 1), .16, M_ORNG)
    fin(nm + 'Low', tip, 2.6, 1.0, 1.1, 1.2, (0, s * .3, -1), .12, M_CHR)
for s in (-1, 1):
    x0_ = float(W[:, 0].min()) + 5.0; y0_ = s * 4.0
    fin(f'Strake{s}', (x0_, y0_, belly_z(x0_, y0_) + .1), 6.0, 2.4, 1.3, 2.0, (0, s * .35, -1), .14, M_CHR)
# gear-bay doors: hinge open (frames 1-12) ahead of the legs, closed after retraction
for i in range(3):
    piv_ = bpy.data.objects[f'GearPiv{i}']; c_ = piv_.matrix_world.translation.copy(); bz_ = belly_z(c_.x, c_.y)
    for e in (-1, 1):
        h = piv(f'Anim_GearDoor_{i}_{e}', (c_.x, c_.y + e * .75, bz_ - .02))
        att(Box(f'GearDoor{i}{e}', (c_.x, c_.y + e * .4, bz_ - .04), (2.4, .7, .05), M_CHR), h)
        att(Box(f'GearDoorEdge{i}{e}', (c_.x, c_.y + e * .08, bz_ - .07), (2.3, .04, .02), M_ORNG), h)
        keyv(h, 0, [(1, 0), (12, e * math.radians(-95)), (240, e * math.radians(-95))])
# bridge: sloped skirting panels hide the hull skin at the floor edges; softer holo table
zf_, xs_b, A_b, _ = SEG['bridge']
for s in (-1, 1):
    bm = bmesh.new(); prev = None
    for x, a in zip(xs_b, A_b):
        row = [bm.verts.new((float(x), s * max(float(a) - .75, .3), ZB + .05)), bm.verts.new((float(x), s * (float(a) - .02), ZB + .8))]
        if prev: bm.faces.new((prev[0], row[0], row[1], prev[1]) if s > 0 else (prev[1], row[1], row[0], prev[0]))
        prev = row
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.03)
    me_ = bpy.data.meshes.new(f'BridgeSkirt{s}'); bm.to_mesh(me_); bm.free(); o = bpy.data.objects.new(f'BridgeSkirt{s}', me_); col.objects.link(o); me_.materials.append(M_LIND)
M_HOLO = pbsdf('Holo', (.2, .8, 1), 0, .2, (.2, .8, 1), 3.0)
hg = bpy.data.objects.get('HoloGlobe')
if hg:
    hg.data.materials.clear(); hg.data.materials.append(M_HOLO); w_ = hg.modifiers.new('W', 'WIREFRAME'); w_.thickness = .008
    keyv(hg, 2, [(1, 0), (240, 6.28)], lin=True)

CEIL = [o for o in bpy.data.objects if any(t in o.name for t in ('CeilStrip', 'CeilLight', 'Cable', 'ReactorCap', 'Frame'))]

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
    M_LIN.node_tree.nodes['CUT'].outputs[0].default_value = v
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
    nt = M_LIN.node_tree; nt.links.new(nt.nodes['Principled BSDF'].outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    hide = {'Hull', 'InnerSkin', 'Pad', 'Cam', 'Sun'}
    inner = [o for o in bpy.data.objects if o.type == 'MESH' and o.name not in hide and o.name != 'HullLite' and not o.name.startswith(('Thruster', 'Exhaust', 'Plume', 'g', 'RCS', 'Dish', 'Nav', 'Strobe', 'Gear', 'G0', 'G1', 'G2'))]
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in inner: o.select_set(True)
    for nm in ('RampPivot',): bpy.data.objects[nm].select_set(True)
    pass
    for o in bpy.data.objects:
        if o.type in ('MESH', 'EMPTY') and o.name not in hide: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'spacecraft_v10.glb'), export_format='GLB', use_selection=True, export_apply=True, export_animations=True, export_lights=False)
    print('MODEL glb', os.path.getsize(os.path.join(OUT, 'spacecraft_v10.glb')))

KEYS = None
def walk_keys():
    return [(1, (60, -45, 18), (0, 0, 0)), (60, (24, -21, ZF - 3.0), (0, 0, ZF - 3.0)), (110, (1.5, -4.0, ZF - 5.5), (0, 0, ZF - .5)),
            (140, (0.6, 0, ZF + 1.6), (6, 0, ZF + 1.4)), (175, (6.0, 0, ZF + 1.6), (BR + 2, 0, ZF + 1.2)),
            (215, (px - 3, 0, ZB + 1.7), (nose_end + 1, 0, ZB + 1.1)), (240, (px - 1.6, 0, ZB + 1.55), (nose_end + 2, 0, ZB + 1.3))]
def keyframe_walk():
    keys = walk_keys()
    for f in range(1, 241):
        for (fa, la, ta), (fb, lb, tb) in zip(keys, keys[1:]):
            if fa <= f <= fb:
                t = (f - fa) / (fb - fa); t = t * t * (3 - 2 * t)
                loc = Vector(la).lerp(Vector(lb), t); tgt = Vector(ta).lerp(Vector(tb), t); break
        look(loc, tgt, 20); cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
    set_cut2(0); ground.hide_render = False
    for o in CEIL: o.hide_render = False
    r.resolution_x, r.resolution_y = 1280, 720; sc.frame_set(1)
def save_blend():
    try:
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'spacecraft_v10.blend'), compress=True)
        print('MODEL blend', os.path.getsize(os.path.join(OUT, 'spacecraft_v10.blend')))
    except Exception as e: print('Error blend', e)


# ------------------------------------------------------------------ v10 HOUSE-TOUR walk-through (shot list, cuts between rooms)
sc.frame_set(120); bpy.context.view_layer.update()
_rp = bpy.data.objects['Ramp']; _cs = [_rp.matrix_world @ Vector(c) for c in _rp.bound_box]
_lo = min(_cs, key=lambda v: v.z); _hi = max(_cs, key=lambda v: v.z)
RX0, RZ0, RX1, RZ1 = _lo.x, _lo.z + .06, HATCH[0] + .2, ZF
yc_ = (WY0 + WY1) / 2; xc2 = (ROOMS[2][0] + ROOMS[2][1]) / 2
def orbit(a0, a1, r0, r1, z0, z1, n=6):
    return [(k / (n - 1), (math.cos(math.radians(a0 + (a1 - a0) * k / (n - 1))) * (r0 + (r1 - r0) * k / (n - 1)), math.sin(math.radians(a0 + (a1 - a0) * k / (n - 1))) * (r0 + (r1 - r0) * k / (n - 1)), z0 + (z1 - z0) * k / (n - 1)), (0, 0, -1)) for k in range(n)]
TOUR = [  # name, caption, frames, scene-frame range, waypoints (t, cam, target), lens
 ('exterior', 'THE SHIP  |  new livery', 192, (120, 120), orbit(-35, -150, 62, 52, 20, 7), 32),
 ('entrance', 'MAIN ENTRANCE  |  boarding ramp', 168, (120, 120), [(0, (RX0 + 9, -3.5, RZ0 + 1.2), (RX1, 0, RZ1 + .8)), (.35, (RX0 + 2.5, -.4, RZ0 + 1.7), (RX1, 0, RZ1 + 1.4)), (1, (RX1 + .4, 0, RZ1 + 1.65), (RX1 - 6, 0, RZ1 + 1.5))], 20),
 ('hall', 'CENTRAL HALL  |  crew deck', 132, (160, 160), [(0, (XS + .6, 0, ZF + 1.65), (BR, 0, ZF + 1.3)), (1, (XS + 7.5, 0, ZF + 1.65), (BR + 4, 0, ZF + 1.2))], 18),
 ('engine', 'ENGINE ROOM  |  fusion core', 156, (90, 240), [(0, (EX + 4.4, 1.7, ZA + 2.3), (EX, 0, ZA + 1.6)), (1, (EX + 3.9, -.8, ZA + 1.9), (EX - .4, .2, ZA + 1.4))], 16),
 ('wing', 'WING CORRIDOR  |  port side', 132, (160, 160), [(0, (WX1 - .5, yc_, FW + 1.65), (WX0 - 3, yc_, FW + 1.3)), (1, (DOOR[1] + 1.4, yc_, ramp_floor(DOOR[1] + 1.4) + 1.65), (DOOR[0] - 2, yc_ + .6, ramp_floor(DOOR[0]) + 1.4))], 16),
 ('mess', 'MESS HALL  |  galley', 132, (215, 215), [(0, (PX1 - .5, PY0 + .4, FP + 1.8), (PX0, PY1 - .8, FP + .6)), (1, (PX1 - .8, PY1 - .5, FP + 1.75), (PX0 + .3, PY0 + .5, FP + .8))], 15),
 ('medbay', 'MED BAY  |  cargo hold', 132, (215, 215), [(0, (PX0 + .6, -(PY0 + .5), FP + 1.85), (PX1 - 1.6, -(PY1 - .6), FP + .6)), (1, (PX0 + 1.4, -(PY0 + .45), FP + 1.8), (PX1 - 1.2, -(PY1 - .9), FP + .7))], 15),
 ('cabin', 'CREW CABIN  |  1 of 8', 120, (160, 160), [(0, (ROOMS[2][1] - .45, -(HW + .2), ZF + 1.72), (ROOMS[2][0] + .3, -(HW + 1.6), ZF + .6)), (1, (ROOMS[2][1] - .8, -(HW + .45), ZF + 1.6), (ROOMS[2][0] + .2, -(HW + 1.3), ZF + .5))], 16),
 ('bridge', 'BRIDGE  |  live flight controls', 180, (130, 240), [(0, (px - 3.4, -.1, ZB + 1.8), (nose_end + 1, 0, ZB + 1.1)), (.55, (px - 1.2, -.05, ZB + 1.7), (px + 1.2, .3, ZB + .9)), (1, (px - .45, .2, ZB + 1.45), (px + .45, .9, ZB + .8))], 20),
 ('finale', 'ENGINES ONLINE', 144, (140, 240), [(0, (-44, -26, 5), (0, 0, 0)), (1, (-72, -44, 15), (4, 0, 1))], 30),
]
def tour_at(f):
    acc = 1
    for nm, cap, n, (s0, s1), wps, lens in TOUR:
        if f < acc + n:
            t = (f - acc) / max(n - 1, 1); te = t * t * (3 - 2 * t)
            for (ta, la, ga), (tb, lb, gb) in zip(wps, wps[1:]):
                if ta <= te <= tb:
                    u = (te - ta) / max(tb - ta, 1e-6); loc = Vector(la).lerp(Vector(lb), u); g_ = ga if ga != (0, 0, -1) else (0, 0, 0); h_ = gb if gb != (0, 0, -1) else (0, 0, 0); tgt = Vector(g_).lerp(Vector(h_), u); break
            return nm, int(round(s0 + (s1 - s0) * t)), loc, tgt, lens
        acc += n
    return None
NTOUR = sum(t[2] for t in TOUR); acc = 1
for nm, cap, n, *_ in TOUR: print('TOUR', nm, acc, acc + n - 1, cap); acc += n
print('TOUR total', NTOUR)
def tour_frame(f, path, res=(1280, 720)):
    nm, sf, loc, tgt, lens = tour_at(f)
    sc.frame_set(sf); set_cut2(0); ground.hide_render = False
    for o in CEIL: o.hide_render = False
    look(loc, tgt, lens); r.resolution_x, r.resolution_y = res; r.filepath = path; bpy.ops.render.render(write_still=True)

if DRY:
    shot('1_exterior', 1, (48, -39, 21), (0, 0, 0), 35, pad=False)
    shot('1b_exterior_rear', 1, (-46, 34, 16), (0, 0, 0), 35, pad=False)
    shot('1c_underside', 120, (30, -34, -8), (0, 0, -3), 35)
    shot('4_bridge', 200, (px - 3.0, -.6, ZB + 1.65), (nose_end + 1, .2, ZB + 1.0), 18)
    sc.cycles.samples = 10
    acc = 1
    for nm, cap, n, *_ in TOUR:
        tour_frame(acc + n // 2, os.path.join(OUT, f't_{nm}.png'), (960, 540)); print('RENDER t', nm); acc += n
    sc.cycles.samples = SPP; save_blend()
    try: export_glbs()
    except Exception as e: print('Error glb', e)
else:
    r.image_settings.file_format = 'JPEG'; r.image_settings.quality = 92; r.use_persistent_data = True
    for f in range(S0, min(S1, NTOUR) + 1):
        tour_frame(f, os.path.join(OUT, f'f_{f:04d}.jpg'))
print('DONE')
