"""v11: v10 + grand hall (hall_v11.inc.py inlined). v3: hull-derived interior architecture + exterior detail. Interior + exterior engineering pass on the user's Tripo3D spacecraft_concept.glb.
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
# v17: world-space wheel cut AFTER the z-thickening (v10's local-space cut missed the fused port wheel and two islands)
def _wcut(P_):
    x, y, z = P_[:, 0], np.abs(P_[:, 1]), P_[:, 2]
    zx = (x > -17.6) & (x < -3.0)
    return zx & (((y > 9.4) & (y < 13.0) & (z < -2.35)) | ((y >= 13.0) & (y < 13.6) & (z < -2.6)) | ((y >= 13.6) & (y < 14.7) & (z < -3.4)))
_b = _bm.new(); _b.from_mesh(me); _b.verts.ensure_lookup_table()
_cut = np.where(_wcut(W))[0]
_bm.ops.delete(_b, geom=[_b.verts[i] for i in _cut], context='VERTS'); _b.verts.index_update(); _b.verts.ensure_lookup_table()
_seen = set(); _isl = []
for v0 in _b.verts:
    if v0.index in _seen: continue
    comp = [v0]; _seen.add(v0.index); st_ = [v0]
    while st_:
        v = st_.pop()
        for e in v.link_edges:
            o = e.other_vert(v)
            if o.index not in _seen: _seen.add(o.index); comp.append(o); st_.append(o)
    if len(comp) < 4000:
        Pc = np.array([tuple(hull.matrix_world @ v.co) for v in comp])
        inb = (Pc[:, 0].min() > -17.8) and (Pc[:, 0].max() < -2.8) and (np.abs(Pc[:, 1]).min() > 9.0) and (np.abs(Pc[:, 1]).max() < 15.0) and (Pc[:, 2].max() < -1.0)
        if inb: _isl.extend(comp)
_bm.ops.delete(_b, geom=_isl, context='VERTS'); _b.to_mesh(me); _b.free(); me.update()
print('MODEL v17 wheel cut verts', len(_cut), 'islands verts', len(_isl))
nv = len(me.vertices); co = np.empty(nv * 3, dtype=np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
W = (np.c_[co, np.ones(nv)] @ mw.T)[:, :3]
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
# v17: belly hazard chevrons removed
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
# v17: ramp-hole keyframes removed (the keel bay is carved in geometry)

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

# ================================================================== v11 GRAND HALL (central atrium, gallery ring, dome, shield wall)
# Plan (user, 2026-11-05): 14 m round hall at x -10..+4, open two-level atrium, gallery ring at +3.4 m, 7.5 m dome with skylight,
# reactor (realistic fusion core, behind the shield wall) seen through lead-glass windows. Old interior inside the hall volume is carved out.
import random
from mathutils import Euler
sc.frame_set(120); bpy.context.view_layer.update()
HC = Vector((-3.0, 0.0)); HR = 7.0
Z0 = -1.0; ZG = Z0 + 3.4; ZS = Z0 + 4.6; ZD = Z0 + 7.5           # floor, gallery top, springline, dome crown (inside)
ROUT = HR + .4; ZSO = Z0 + 5.0; ZDO = ZD + .35; ZBO = Z0 - .35     # outer blister
SKY_R = 1.4
def dome_in(r): return ZS + (ZD - ZS) * math.sqrt(max(0.0, 1 - (r / HR) ** 2))
def dome_out(r): return ZSO + (ZDO - ZSO) * math.sqrt(max(0.0, 1 - (r / ROUT) ** 2))
def pol(r, a, z): t = math.radians(a); return (HC.x + r * math.cos(t), HC.y + r * math.sin(t), z)
def dang(w, r=HR): return math.degrees(w / r)
PIT = (-3.2, 3.2, 2.8)   # entrance well around the boarding hatch: x0, x1, |y|
LANE = (PIT[1] - .05, HC.x + HR + .9, 1.0)   # v12: forward lane at deck level from the well to the crew corridor

# ---------------------------------------------------------------- 1. carve the old interior + hull inside the hall volume
def t_old(P):
    r = np.hypot(P[:, 0] - HC.x, P[:, 1] - HC.y); z = P[:, 2]
    a = (r < HR + .05) & (z > Z0 - .3) & (z < ZDO + .5)
    b = (P[:, 0] > PIT[0] - .1) & (P[:, 0] < PIT[1] + .1) & (np.abs(P[:, 1]) < PIT[2] + .2) & (z > ZF + .03) & (z < ZDO + .5)
    d = (P[:, 0] > LANE[0]) & (P[:, 0] < LANE[1]) & (np.abs(P[:, 1]) < LANE[2] + .05) & (z > ZF + .03) & (z < Z0 + 2.4)
    c = (P[:, 0] > -12.7) & (P[:, 0] < -9.5) & (np.abs(P[:, 1]) < 3.1) & (z > Z0 - .3) & (z < 4.6)
    return a | b | c | d
def t_hull(P):
    r = np.hypot(P[:, 0] - HC.x, P[:, 1] - HC.y); z = P[:, 2]
    dz = ZSO + (ZDO - ZSO) * np.sqrt(np.clip(1 - (r / ROUT) ** 2, 0, 1))
    zlo = np.where(np.abs(P[:, 1]) < 2.6, Z0 + .05, ZBO + .02)
    return (r < ROUT - .02) & (z < dz - .03) & (z > zlo)
def bisect_grid(o):
    me_ = o.data
    if me_.users > 1: o.data = me_ = me_.copy()
    mi = o.matrix_world.inverted(); bm = bmesh.new(); bm.from_mesh(me_)
    planes = [((x, 0, 0), (1, 0, 0)) for x in np.arange(-12.0, 5.01, 1.0)] + [((0, y, 0), (0, 1, 0)) for y in np.arange(-7.0, 7.01, 1.0)] + [((0, 0, z), (0, 0, 1)) for z in (ZF + .05, Z0 - .3, Z0 + .1, Z0 + 1.5, ZG)]
    for co, no in planes:
        c_ = mi @ Vector(co); n_ = (mi.to_3x3().transposed().inverted() @ Vector(no)).normalized() if False else (o.matrix_world.to_3x3().transposed() @ Vector(no)).normalized()
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=c_, plane_no=n_, clear_inner=False, clear_outer=False)
    bm.to_mesh(me_); bm.free(); me_.update()
def carve_faces(o, test, cut=False):
    me_ = o.data
    if me_.users > 1: o.data = me_ = me_.copy()
    if cut:
        bb_ = np.array([list(o.matrix_world @ Vector(c)) for c in o.bound_box])
        if bb_[:, 0].max() > HC.x - HR - 3 and bb_[:, 0].min() < HC.x + HR + 1 and np.abs(bb_[:, 1]).min() < HR + .5 and bb_[:, 2].max() > ZF: bisect_grid(o)
        me_ = o.data
    n = len(me_.polygons)
    if n == 0: return 0
    cen = np.empty(n * 3, np.float32); me_.polygons.foreach_get('center', cen); cen = cen.reshape(-1, 3)
    mw_ = np.array(o.matrix_world); cw = cen @ mw_[:3, :3].T + mw_[:3, 3]
    kill = test(cw)
    if not kill.any(): return 0
    if kill.all(): bpy.data.objects.remove(o); return n
    bm = bmesh.new(); bm.from_mesh(me_); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.where(kill)[0]], context='FACES')
    bm.to_mesh(me_); bm.free(); me_.update(); return int(kill.sum())
KEEPN = {'Hull', 'Ramp', 'RampPivot', 'Pad', 'Sun', 'Cam'}
KEEPP = ('Anim_', 'GearPiv', 'Ctrl_', 'Winglet', 'Strake', 'GearDoor', 'Thruster', 'Exhaust', 'Plume', 'Nav', 'Strobe', 'G0', 'G1', 'G2', 'Gear', 'Cryo', 'Vacuum', 'Central', 'Solenoid', 'PFCoil', 'TFCoil', 'Core', 'Plenum')
n_obj = n_face = 0
for o in list(bpy.data.objects):
    if o.name in KEEPN or o.name.startswith(KEEPP): continue
    if o.type == 'MESH':
        if o.children:
            n_face += carve_faces(o, t_old, cut=True) if len(o.data.polygons) >= 6 else 0; continue
        cs_ = np.array([list(o.matrix_world @ Vector(c)) for c in o.bound_box])
        ins = t_old(cs_)
        if ins.all(): bpy.data.objects.remove(o); n_obj += 1; continue
        if len(o.data.polygons) < 60 and not (cs_.max(0) - cs_.min(0) > 2.5).any():
            if t_old(cs_.mean(0)[None])[0]: bpy.data.objects.remove(o); n_obj += 1
            continue
        n_face += carve_faces(o, t_old, cut=True)
    elif o.type in ('LIGHT', 'CURVE', 'EMPTY'):
        if o.type == 'EMPTY' and o.children: continue
        p_ = np.array([list(o.matrix_world.translation)])
        if t_old(p_)[0]: bpy.data.objects.remove(o); n_obj += 1
print('MODEL hall carve old objects', n_obj, 'faces', n_face)
print('MODEL hall carve hull faces', carve_faces(hull, t_hull))

# ---------------------------------------------------------------- v13 1b. clear the old v8-v10 nacelle pods + aft wing corridors; carve the side-room volumes
SX0, SX1, SYI, SYO = -7.0, 1.0, 7.6, 11.0          # side rooms (mess port +y, med starboard -y): x range, inner / outer |y|
SZC = Z0 + 2.7                                     # side-room ceiling (2.7 m, same floor as the hall)
FX0, FX1, FYI, FYO, FZ0, FZ1 = SX0 - .3, SX1 + .3, 6.7, SYO + .5, Z0 - .3, SZC + .3   # exterior sponson fairing
OLD_PRE = ('Pod', 'Mess', 'Med', 'Galley', 'Cargo', 'Plate', 'Tray', 'FoodDispenser', 'Disp', 'Fridge', 'MonArm', 'IVPole', 'IVBag', 'WingAftEnd', 'CeilStripWingR')
n_old = 0
for o in list(bpy.data.objects):
    if o.name in KEEPN or o.name.startswith(KEEPP): continue
    cs_ = np.array([list(o.matrix_world @ Vector(c)) for c in o.bound_box]) if o.type == 'MESH' else np.array([list(o.matrix_world.translation)])
    c_ = cs_.mean(0)
    if o.name.startswith(OLD_PRE) or o.name in ('Tap', 'Sink'):
        if o.type == 'EMPTY' and o.children: continue
        bpy.data.objects.remove(o); n_old += 1; continue
    if o.name.startswith(('Wing', 'CeilStripWing', 'Extinguisher', 'EmLocker')) and not o.name.startswith('Winglet'):
        if o.type == 'MESH' and cs_[:, 0].max() > 3.9 and cs_[:, 0].min() < 3.9:
            carve_faces(o, lambda P: P[:, 0] < 3.9)
        elif c_[0] < 3.9: bpy.data.objects.remove(o); n_old += 1
for s_ in (-1, 1):   # cap the surviving forward wing corridors where they used to run aft into the hall
    Box(f'WingCapAft{s_}', (3.95, s_ * 4.3, FW + 1.35), (.1, 1.5, 2.7), M_LIN)
def t_side(P):
    ay = np.abs(P[:, 1])
    return (P[:, 0] > FX0 + .15) & (P[:, 0] < FX1 - .15) & (ay > FYI + .25) & (ay < FYO - .2) & (P[:, 2] > FZ0 - .2) & (P[:, 2] < FZ1 - .15)
for o in list(bpy.data.objects):
    if o.type != 'MESH' or o.name in KEEPN or o.name.startswith(KEEPP): continue
    cs_ = np.array([list(o.matrix_world @ Vector(c)) for c in o.bound_box])
    if t_side(cs_).all(): bpy.data.objects.remove(o); n_old += 1; continue
    lo_, hi_ = cs_.min(0), cs_.max(0)
    if hi_[0] > FX0 and lo_[0] < FX1 and hi_[2] > FZ0 and lo_[2] < FZ1 and max(abs(lo_[1]), abs(hi_[1])) > FYI: carve_faces(o, t_side)
print('MODEL v13 old pods/wing removed', n_old, '; side-room hull faces carved', carve_faces(hull, t_side))

# ---------------------------------------------------------------- 2. materials
def glass(name, tint, rough=.02):
    m = pbsdf(name, tint, 0, rough); p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Transmission Weight'].default_value = 1.0; p.inputs['IOR'].default_value = 1.45; return m
M_HW = pbsdf('HallWall', (.52, .53, .53), .12, .5)
M_HD = pbsdf('HallDark', (.11, .12, .14), .6, .32)
M_HFL = pbsdf('HallFloor', (.028, .03, .034), .5, .3)
M_RAILG = glass('RailGlass', (.85, .93, .97))
M_LEADG = glass('LeadGlass', (.55, .85, .8), .03)
M_SKYG = glass('SkyGlass', (.85, .93, 1))
M_RING = pbsdf('RingLight', (1, .95, .85), 0, .5, (1, .92, .8), 16)
M_SHLD = pbsdf('ShieldConcrete', (.19, .2, .21), .1, .75)
M_WOOD = pbsdf('Wood', (.33, .19, .09), 0, .45)
M_LEAF = pbsdf('Leaf', (.06, .22, .07), 0, .6)
M_POT = pbsdf('Pot', (.75, .74, .7), 0, .4)
M_CRATE = pbsdf('Crate', (.22, .25, .2), .2, .6)
M_LABW = pbsdf('LabWhite', (.85, .86, .88), 0, .3)
M_COREGLOW = pbsdf('CoreGlow', (.3, .75, 1), 0, .3, (.3, .75, 1), 25)
M_BK = [pbsdf(f'Book{i}', c, 0, .6) for i, c in enumerate(((.38, .07, .05), (.06, .14, .3), (.55, .45, .25), (.08, .2, .1), (.15, .15, .16)))]

def mk(name, V, F, mat, mats=None, fidx=None, smooth=False):
    me_ = bpy.data.meshes.new(name); me_.from_pydata(V, [], F); me_.update()
    o = bpy.data.objects.new(name, me_); col.objects.link(o); me_.materials.append(mat)
    if mats:
        for m in mats: me_.materials.append(m)
        me_.polygons.foreach_set('material_index', fidx)
    if smooth: me_.polygons.foreach_set('use_smooth', [True] * len(me_.polygons))
    return o
def ann(name, r0, r1, a0, a1, z0, z1, mat, step=3.0):
    n = max(2, int(math.ceil(abs(a1 - a0) / step)) + 1); A = [a0 + (a1 - a0) * i / (n - 1) for i in range(n)]
    V = []; F = []
    for a in A: V += [pol(r0, a, z0), pol(r1, a, z0), pol(r1, a, z1), pol(r0, a, z1)]
    for i in range(n - 1):
        b, c = 4 * i, 4 * (i + 1)
        for k in range(4): F.append((b + k, b + (k + 1) % 4, c + (k + 1) % 4, c + k))
    F.append((3, 2, 1, 0)); e = 4 * (n - 1); F.append((e, e + 1, e + 2, e + 3))
    return mk(name, V, F, mat)
def ribbon(name, lo, hi, mat):
    n = len(lo); return mk(name, list(lo) + list(hi), [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)], mat)
def arcpts(r, a0, a1, zf, n=24): return [pol(r, a0 + (a1 - a0) * i / (n - 1), zf(a0 + (a1 - a0) * i / (n - 1))) for i in range(n)]
def pbox(name, r, a, z, size, mat, tilt=0):
    return Box(name, pol(r, a, z), size, mat, rot=(0, tilt, a))
def polar_grid(name, r0, r1, z_of_r, mat, skip=None, dr=.25, da=2.0):
    nr = max(1, int(math.ceil((r1 - r0) / dr))); R = [r0 + (r1 - r0) * i / nr for i in range(nr + 1)]
    na = int(round(360 / da)); idx = {}; V = []; F = []
    def vid(i, j):
        k = (i, j % na)
        if k not in idx: idx[k] = len(V); V.append(pol(R[i], (j % na) * da, z_of_r(R[i])))
        return idx[k]
    for i in range(nr):
        for j in range(na):
            if skip:
                c = pol((R[i] + R[i + 1]) / 2, (j + .5) * da, 0)
                if skip(c[0], c[1]): continue
            F.append((vid(i, j), vid(i, j + 1), vid(i + 1, j + 1), vid(i + 1, j)))
    return mk(name, V, F, mat)

# ---------------------------------------------------------------- 3. openings in the round wall
OPEN = []
def opening(nm, a, half_w, z0, z1): OPEN.append((nm, a - dang(half_w), a + dang(half_w), z0, z1))
OPEN.append(('Fwd', -dang(LANE[2]), dang(LANE[2]), Z0 - .01, Z0 + 2.4))   # v17: full 2.4 m door at hall level
for nm, a in (('Mess', 90), ('Med', 270)): opening(nm, a, .8, Z0, Z0 + 2.3)
OPEN.append(('Reactor', 180 - math.degrees(math.asin(.75 / HR)), 180 + math.degrees(math.asin(.75 / HR)), Z0, Z0 + 2.4))
WZ0, WZ1, WY0_, WY1_ = Z0 + 1.3, Z0 + 3.3, 1.3, 2.5
for s, nm in ((1, 'WinP'), (-1, 'WinS')):
    aa = sorted((180 - s * math.degrees(math.asin(WY1_ / HR)), 180 - s * math.degrees(math.asin(WY0_ / HR))))
    OPEN.append((nm, aa[0], aa[1], WZ0, WZ1))
def in_open(a, z):
    a %= 360
    for nm, a0, a1, z0, z1 in OPEN:
        for aa in (a, a - 360, a + 360):
            if a0 < aa < a1 and z0 < z < z1: return True
    return False
# wall grid (edges snap to every opening edge)
AE = sorted(set([round(i * 2.0, 4) for i in range(180)] + [round(o[1] % 360, 4) for o in OPEN] + [round(o[2] % 360, 4) for o in OPEN]))
ZE = sorted(set([Z0, ZS, ZG - .3, ZG] + [o[3] for o in OPEN] + [o[4] for o in OPEN] + list(np.round(np.linspace(Z0, ZS, 7), 4))))
ZE = [z for z in ZE if Z0 <= z <= ZS]
V = []; F = []; idx = {}
def wv(i, j):
    k = (i % len(AE), j)
    if k not in idx: idx[k] = len(V); V.append(pol(HR, AE[i % len(AE)], ZE[j]))
    return idx[k]
for i in range(len(AE)):
    a0 = AE[i]; a1 = AE[(i + 1) % len(AE)] + (360 if i == len(AE) - 1 else 0)
    for j in range(len(ZE) - 1):
        if in_open((a0 + a1) / 2, (ZE[j] + ZE[j + 1]) / 2): continue
        F.append((wv(i, j), wv(i + 1, j), wv(i + 1, j + 1), wv(i, j + 1)))
mk('HallWall', V, F, M_HW)
# reveals (0.6 m deep) round every opening
for nm, a0, a1, z0, z1 in OPEN:
    R1 = HR + .6; n = 6; A = [a0 + (a1 - a0) * i / n for i in range(n + 1)]
    V = []; F = []
    for zz in ((z1,) if z0 <= Z0 + .01 else (z0, z1)):
        b = len(V)
        for a in A: V += [pol(HR, a, zz), pol(R1, a, zz)]
        F += [(b + 2 * i, b + 2 * i + 2, b + 2 * i + 3, b + 2 * i + 1) for i in range(n)]
    for a in (a0, a1):
        b = len(V); V += [pol(HR, a, z0), pol(R1, a, z0), pol(R1, a, z1), pol(HR, a, z1)]; F.append((b, b + 1, b + 2, b + 3))
    mk(f'HallReveal{nm}', V, F, M_HD)

# ---------------------------------------------------------------- 4. dome, skylight, floor, outer blister
polar_grid('HallDome', SKY_R, HR, dome_in, M_HW, dr=.3, da=3.0)
ann('SkylightWell', SKY_R, SKY_R + .04, 0, 360, dome_in(SKY_R) - .02, dome_out(SKY_R) + .02, M_HD, step=6)
Cyl('SkylightGlass', (HC.x, HC.y, dome_out(SKY_R)), SKY_R + .05, .06, M_SKYG, v=48)
Tor('SkylightRing', (HC.x, HC.y, dome_in(SKY_R + .15) - .06), SKY_R + .15, .05, M_RING, ms=64, ns=8)
for k, rr in enumerate((3.4, 5.6)):
    Tor(f'DomeRingLight{k}', (HC.x, HC.y, dome_in(rr) - .1), rr, .05, M_RING, ms=96, ns=8)
# 16 ribs: up the wall, over the dome
for k in range(16):
    a = 11.25 + k * 22.5; pts = []
    zst = Z0
    for nm, a0, a1, z0, z1 in OPEN:
        if a0 - 1.5 < a < a1 + 1.5 and z0 < Z0 + .5: zst = max(zst, z1 + .05)
    for zz in np.linspace(zst, ZS, 6): pts.append(pol(HR - .06, a, float(zz)))
    for rr in np.linspace(HR - .06, SKY_R + .35, 14)[1:]: pts.append(pol(float(rr), a, dome_in(float(rr)) - .06))
    cu = bpy.data.curves.new(f'HallRib{k}', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = .07; cu.bevel_resolution = 1
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
    o = bpy.data.objects.new(f'HallRib{k}', cu); col.objects.link(o); cu.materials.append(M_HD)
def pit_hole(x, y): return (-7.2 < x < -4.6 and abs(y) < .65) or math.hypot(x - HC.x, y - HC.y) < .75   # v17: off-centre hatch + flush holo-table well
fl = polar_grid('HallFloor', 0.0, HR, lambda r: Z0, M_HFL, skip=pit_hole)
so = fl.modifiers.new('Sol', 'SOLIDIFY'); so.thickness = .2; so.offset = -1
# floor inlays: cyan ring under the gallery edge, warm ring at the wall
def ring_inlay(name, rr, w, mat):
    V = []; F = []
    for j in range(180):
        a0, a1 = j * 2.0, (j + 1) * 2.0; c = pol(rr, a0 + 1, 0)
        if pit_hole(c[0], c[1]): continue
        b = len(V); V += [pol(rr - w, a0, Z0 + .004), pol(rr + w, a0, Z0 + .004), pol(rr + w, a1, Z0 + .004), pol(rr - w, a1, Z0 + .004)]; F.append((b, b + 1, b + 2, b + 3))
    return mk(name, V, F, mat)
ring_inlay('FloorRingInner', 4.0, .035, M_CYAN); ring_inlay('FloorRingWall', 6.92, .03, M_AMBER)
# outer blister (exterior): lathe profile + flat belly with the fuselage strip left open
prof = []
for t in np.linspace(-90, 0, 5): prof.append((ROUT - .35 + .35 * math.cos(math.radians(t)), ZBO + .35 + .35 * math.sin(math.radians(t))))
for zz in sorted(set([round(float(z_), 4) for z_ in np.linspace(ZBO + .35, ZSO, 6)[1:]] + [round(o[k], 4) for o in OPEN for k in (3, 4) if ZBO + .4 < o[k] < ZSO - .05])): prof.append((ROUT, float(zz)))   # v14: rows at every opening edge
for rr in np.linspace(ROUT, SKY_R, 18)[1:]: prof.append((float(rr), dome_out(float(rr))))
# v14: the blister wall (r 7.4) sat 0.4 m behind every hall opening and blocked the mess, med, reactor doorways and the lead-glass windows.
#      Columns now snap to every opening edge and the faces inside an opening are left out.
BA = sorted(set([round(j * 3.0, 4) for j in range(120)] + [round(o[k] % 360, 4) for o in OPEN for k in (1, 2)]))
na = len(BA); V = []; F = []; FI = []; NBH = 0
for j in range(na):
    for (rr, zz) in prof: V.append(pol(rr, BA[j], zz))
npf = len(prof)
for j in range(na):
    a0b = BA[j]; a1b = BA[(j + 1) % na] + (360 if j == na - 1 else 0)
    for i in range(npf - 1):
        a_, b_ = j * npf + i, ((j + 1) % na) * npf + i
        zc = (prof[i][1] + prof[i + 1][1]) / 2
        if prof[i][0] > ROUT - .01 and prof[i + 1][0] > ROUT - .01 and in_open((a0b + a1b) / 2, zc): NBH += 1; continue
        F.append((a_, b_, b_ + 1, a_ + 1))
        FI.append(1 if zc < ZBO + .3 else (2 if ZSO - .4 < zc < ZSO - .1 else 0))
mk('HallBlister', V, F, M_WHT, mats=[M_CHR, M_ORNG], fidx=FI, smooth=True)
print('MODEL v14 blister faces opened', NBH)
polar_grid('HallBlisterBelly', 0.0, ROUT - .35, lambda r: ZBO, M_CHR, skip=lambda x, y: abs(y) < 2.6, dr=.35, da=3.0)

# ---------------------------------------------------------------- 5. entrance well around the boarding hatch (stepped sides)
RISE = (Z0 - ZF) / 6
for s in (-1, 1):
    for k in range(6):
        y0_, y1_ = 1.0 + k * .3, 1.3 + k * .3; zt = ZF + (k + 1) * RISE
        Box(f'PitStep{s}{k}', ((PIT[0] + PIT[1]) / 2, s * (y0_ + y1_) / 2, (ZF + zt) / 2), (PIT[1] - PIT[0], .3, zt - ZF), M_HFL)
        Box(f'PitNose{s}{k}', ((PIT[0] + PIT[1]) / 2, s * (y0_ + .02), zt + .003), (PIT[1] - PIT[0] - .1, .03, .008), M_AMBER)
x = PIT[0]
Box(f'PitEnd{x:.1f}', (x, 0, (ZF + Z0) / 2), (.12, 2 * PIT[2], Z0 - ZF), M_HD)
Box(f'PitRail{x:.1f}', (x, 0, Z0 + .5), (.03, 2 * PIT[2], 1.0), M_RAILG)
Box(f'PitRailTop{x:.1f}', (x, 0, Z0 + 1.02), (.06, 2 * PIT[2] + .04, .04), M_HD)
# forward end: the well's flat bottom carries on as a lane at deck level, through the forward door to the crew corridor
for e in (-1, 1):
    Box(f'PitEndSide{e}', (PIT[1], e * (PIT[2] + LANE[2]) / 2, (ZF + Z0) / 2), (.12, PIT[2] - LANE[2], Z0 - ZF), M_HD)
    Box(f'PitRailF{e}', (PIT[1], e * (PIT[2] + LANE[2]) / 2, Z0 + .5), (.03, PIT[2] - LANE[2], 1.0), M_RAILG)
    Box(f'PitRailFTop{e}', (PIT[1], e * (PIT[2] + LANE[2]) / 2, Z0 + 1.02), (.06, PIT[2] - LANE[2] + .04, .04), M_HD)
    Box(f'LaneWall{e}', ((LANE[0] + HC.x + HR) / 2, e * (LANE[2] + .06), (ZF + Z0) / 2), (HC.x + HR - LANE[0], .12, Z0 - ZF), M_HD)
    Box(f'LaneRail{e}', ((LANE[0] + HC.x + HR) / 2, e * (LANE[2] + .06), Z0 + .5), (HC.x + HR - LANE[0], .03, 1.0), M_RAILG)
    Box(f'LaneRailTop{e}', ((LANE[0] + HC.x + HR) / 2, e * (LANE[2] + .06), Z0 + 1.02), (HC.x + HR - LANE[0], .06, .04), M_HD)
    Box(f'LaneStrip{e}', ((LANE[0] + LANE[1]) / 2, e * (LANE[2] - .05), ZF + .01), (LANE[1] - LANE[0], .03, .01), M_CYAN)
Box('LaneFloor', ((LANE[0] + LANE[1]) / 2, 0, ZF - .05), (LANE[1] - LANE[0], 2 * LANE[2], .1), M_HFL)
Box('LaneLintel', (HC.x + HR + .3, 0, ZF + 2.4 + .1), (.6, 2 * LANE[2] + .2, .2), M_HD)

# ---------------------------------------------------------------- 6. gallery ring, railings, curved stairs
ST = (14.0, 62.0, 5.3, 6.95, 20)            # port stair: top angle, bottom angle, r0, r1, steps (starboard mirrored)
ann('GalleryInner', 4.0, 5.2, 0, 360, ZG - .3, ZG, M_HFL, step=2)
ann('GalleryFwd', 5.2, HR, -ST[0], ST[0], ZG - .3, ZG, M_HFL, step=2)
ann('GalleryRooms', 5.2, HR, ST[1], 360 - ST[1], ZG - .3, ZG, M_HFL, step=2)
ann('GalleryEdge', 3.96, 4.0, 0, 360, ZG - .3, ZG + .01, M_HD, step=2)
ribbon('GalleryRail', arcpts(4.02, 0, 360, lambda a: ZG, 181), arcpts(4.02, 0, 360, lambda a: ZG + 1.05, 181), M_RAILG)
ann('GalleryHandrail', 3.97, 4.07, 0, 360, ZG + 1.05, ZG + 1.1, M_HD, step=2)
for k in range(36): pbox(f'GalleryPost{k}', 4.02, k * 10 + 5, ZG + .55, (.04, .04, 1.1), M_HD)
for k in range(48):
    a = k * 7.5
    if not (ST[0] < a < ST[1] or 360 - ST[1] < a < 360 - ST[0]): Area(f'UnderGal{k}', pol(5.6, a, ZG - .32), .4, 22, (1, .9, .78))
for s in (1, -1):
    sg = 'P' if s > 0 else 'S'; a_t, a_b, r0, r1, n = ST
    da_ = (a_b - a_t) / n; rise = (ZG - Z0) / n
    for k in range(n):
        aa0 = a_b - (k + 1) * da_; aa1 = a_b - k * da_; zt = Z0 + (k + 1) * rise
        lo_, hi_ = (aa0, aa1) if s > 0 else (-aa1, -aa0)
        ann(f'Stair{sg}{k:02d}', r0, r1, lo_, hi_, max(Z0, zt - .55), zt, M_HFL, step=1.2)
        ann(f'StairNose{sg}{k:02d}', r0 + .05, r1 - .05, (aa0 if s > 0 else -aa0 - .25), (aa0 + .25 if s > 0 else -aa0), zt, zt + .008, M_AMBER, step=.25)
    zs_ = lambda a: Z0 + (a_b - abs(a)) / (a_b - a_t) * (ZG - Z0)
    A0, A1 = (a_b, a_t) if s > 0 else (-a_b, -a_t)
    ribbon(f'StairRail{sg}', arcpts(r0 - .02, A0, A1, zs_, 24), arcpts(r0 - .02, A0, A1, lambda a: zs_(a) + 1.0, 24), M_RAILG)
    lo2 = arcpts(r0 - .02, A0, A1, lambda a: zs_(a) + 1.0, 24); hi2 = arcpts(r0 - .02, A0, A1, lambda a: zs_(a) + 1.05, 24); ribbon(f'StairHandrail{sg}', lo2, hi2, M_HD)
    ribbon(f'StairStringer{sg}', arcpts(r0 - .01, A0, A1, lambda a: zs_(a) - .6, 24), arcpts(r0 - .01, A0, A1, lambda a: zs_(a) + .02, 24), M_HD)
    # gallery guard over the stair hole + end panel
    G0_, G1_ = (a_t, a_b) if s > 0 else (-a_b, -a_t)
    ribbon(f'HoleRail{sg}', arcpts(5.18, G0_, G1_, lambda a: ZG, 16), arcpts(5.18, G0_, G1_, lambda a: ZG + 1.05, 16), M_RAILG)
    ae = s * a_b; ribbon(f'HoleEnd{sg}', [pol(5.2, ae, ZG), pol(HR, ae, ZG)], [pol(5.2, ae, ZG + 1.05), pol(HR, ae, ZG + 1.05)], M_RAILG)

# ---------------------------------------------------------------- 7. doors, signs, shield wall with lead-glass windows, reactor glow
def hall_door(nm, a, zc, h, w=1.6, mat=M_HD, frame=M_CYAN):
    pbox(f'Door{nm}', HR + .2, a, zc, (.1, w, h), mat)
    pbox(f'DoorSeam{nm}', HR + .14, a, zc, (.02, .02, h - .1), frame)
    for e in (-1, 1): pbox(f'DoorJamb{nm}{e}', HR - .01, a + e * dang(w / 2 + .03), zc, (.05, .05, h), frame)
    pbox(f'DoorHead{nm}', HR - .01, a, zc + h / 2 + .03, (.05, w + .1, .05), frame)
    pbox(f'DoorSign{nm}', HR - .02, a, zc + h / 2 + .3, (.03, .7, .16), M_SCR)
for nm, a in (('Mess', 90), ('Med', 270)): hall_door(nm, a, Z0 + 1.15, 2.3)
for e in (-1, 1): Box(f'FwdJamb{e}', (HC.x + HR + .3, e * (LANE[2] + .03), (ZF + ZF + 2.4) / 2), (.6, .05, 2.4), M_CYAN)
Box('FwdSign', (HC.x + HR - .03, 0, ZF + 2.4 + .35), (.03, 1.2, .2), M_SCR)
pbox('GalFwdScreen', HR - .02, 0, ZG + 1.4, (.03, 2.4, 1.3), M_SCR)   # forward gallery landing: wall display instead of a dead-end door
hall_door('Reactor', 180, Z0 + 1.2, 2.4, w=1.5, mat=M_CHR, frame=M_AMBER)
for n_ in ('DoorReactor', 'DoorSeamReactor'): bpy.data.objects.remove(bpy.data.objects[n_])   # v12: open blast doorway
for k in range(6): Box(f'ReactorHaz{k}', (-10.05 + .35, -.75 + k * .3, Z0 + .005), (.6, .15, .01), M_ORNG if k % 2 == 0 else M_CHR)
# shield wall: 2.5 m slab of water/fuel tanks + concrete between the hall and the reactor bay
XSF, XSB = -10.05, -12.6
def slab(nm, y0, y1, z0, z1): Box(f'Shield{nm}', ((XSF + XSB) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (XSF - XSB, y1 - y0, z1 - z0), M_SHLD)
slab('A0', -2.2, -.85, -.9, WZ0); slab('A1', .85, 2.2, -.9, WZ0)
slab('B0', -2.9, -WY1_, WZ0, Z0 + 2.4); slab('B1', -WY0_, -.85, WZ0, Z0 + 2.4); slab('B2', .85, WY0_, WZ0, Z0 + 2.4); slab('B3', WY1_, 2.9, WZ0, Z0 + 2.4)
ZTOP = ZA + 2.25   # passage headroom above the engine-room floor
slab('B1', -WY0_, -.85, Z0 + 2.4, WZ1); slab('B2', .85, WY0_, Z0 + 2.4, WZ1)
slab('C0', -2.9, -WY1_, Z0 + 2.4, WZ1); slab('C2', WY1_, 2.9, Z0 + 2.4, WZ1)
slab('D0', -2.9, -.85, WZ1, 4.3); slab('D1', .85, 2.9, WZ1, 4.3); slab('D2', -.85, .85, ZTOP, 4.3)
NST = 7; rs_ = (ZA - Z0) / NST; run_ = (XSF - XSB) / NST
for k in range(NST):
    zt = Z0 + (k + 1) * rs_; x1_ = XSF - k * run_
    Box(f'ShieldStep{k}', (x1_ - run_ / 2, 0, (Z0 - .1 + zt) / 2), (run_, 1.7, zt - Z0 + .1), M_HFL)
    Box(f'ShieldStepNose{k}', (x1_ - run_ + .02, 0, zt + .004), (.03, 1.6, .008), M_AMBER)
Box('ShieldLanding', (XSB - .4, 0, ZA - .05), (.9, 1.7, .1), M_HFL)
for e in (-1, 1): Box(f'ShieldStepRail{e}', ((XSF + XSB) / 2, e * .8, (Z0 + ZA) / 2 + .95), (XSF - XSB, .04, .04), M_AMBER, rot=(0, math.degrees(math.atan2(ZA - Z0, XSF - XSB)), 0))
Area('ShieldPassLight', ((XSF + XSB) / 2, 0, ZTOP - .1), .8, 60, (1, .8, .55))
for s in (-1, 1):
    yc = s * (WY0_ + WY1_) / 2; ww = WY1_ - WY0_
    Box(f'LeadGlass{s}a', (-11.0, yc, (WZ0 + WZ1) / 2), (.06, ww, WZ1 - WZ0), M_LEADG)
    Box(f'LeadGlass{s}b', (-11.6, yc, (WZ0 + WZ1) / 2), (.06, ww, WZ1 - WZ0), M_LEADG)
    for zz in (WZ0, WZ1): Box(f'WinTun{s}{zz:.1f}', (-9.95, yc, zz), (.45, ww + .1, .06), M_HD)
    for yy in (WY0_, WY1_): Box(f'WinTunS{s}{yy:.1f}', (-9.95, s * yy, (WZ0 + WZ1) / 2), (.45, .06, WZ1 - WZ0), M_HD)
    Box(f'WinSill{s}', (-9.75, yc, WZ0 + .01), (.05, ww, .02), M_CYAN)

Tor('ReactorBand', (EX, 0, zc_), 1.5, .06, M_COREGLOW, ms=64, ns=8)
Tor('ReactorBand2', (EX, 0, zc_), 1.12, .03, M_COREGLOW, rot=(90, 0, 0), ms=48, ns=6)
lp = bpy.data.lights.new('ReactorGlow', 'POINT'); lp.energy = 1500; lp.color = (.4, .75, 1); lp.shadow_soft_size = .6
o = bpy.data.objects.new('ReactorGlow', lp); col.objects.link(o); o.location = (EX + 1.8, 0, zc_)

# ---------------------------------------------------------------- 8. gallery rooms: library, workshop, lab, ops
for a in (125, 180, 235): pbox(f'GalPartition{a}', 6.45, a, ZG + 1.3, (1.1, .12, 2.6), M_HW)
# library (port forward)
for k in range(6): ann(f'LibShelf{k}', 6.55, 6.95, 68, 120, ZG + .05 + k * .42, ZG + .08 + k * .42, M_WOOD, step=2)
for a in range(68, 121, 13): pbox(f'LibUpright{a}', 6.75, a, ZG + 1.1, (.4, .04, 2.2), M_WOOD)
random.seed(7); bm = bmesh.new(); fidx = []
for k in range(5):
    a = 68.4
    while a < 119.6:
        wb = random.uniform(.03, .06); hb = random.uniform(.22, .34); da_ = math.degrees(wb / 6.75)
        if random.random() < .06: a += da_ * 2; continue
        c = Vector(pol(6.75, a + da_ / 2, ZG + .08 + k * .42 + hb / 2))
        r_ = bmesh.ops.create_cube(bm, size=1.0)['verts']
        for v in r_:
            v.co = Vector((v.co.x * .24, v.co.y * wb * .92, v.co.z * hb))
            v.co.rotate(Euler((0, 0, math.radians(a + da_ / 2)))); v.co += c
        fidx += [random.randrange(5)] * 6; a += da_
me_ = bpy.data.meshes.new('LibBooks'); bm.to_mesh(me_); bm.free(); ob_ = bpy.data.objects.new('LibBooks', me_); col.objects.link(ob_)
for m in M_BK: me_.materials.append(m)
me_.polygons.foreach_set('material_index', fidx[:len(me_.polygons)])
for k, a in enumerate((82, 104)):
    soft(pbox(f'ReadChair{k}', 5.75, a, ZG + .3, (.75, .75, .45), M_FAB), 2); soft(pbox(f'ReadChairBack{k}', 6.1, a, ZG + .7, (.15, .75, .7), M_FAB), 2)
Cyl('ReadTable', pol(5.6, 93, ZG + .5), .35, .04, M_WOOD, v=32); Cyl('ReadTableLeg', pol(5.6, 93, ZG + .25), .04, .5, M_HD)
# workshop (port aft)
ann('WorkBench', 6.2, 6.95, 132, 172, ZG + .86, ZG + .92, M_WOOD, step=2)
for a in (133, 152, 171): pbox(f'WorkBenchLeg{a}', 6.55, a, ZG + .43, (.6, .06, .86), M_HD)
ann('PegBoard', 6.9, 6.96, 132, 172, ZG + 1.1, ZG + 2.25, M_LIND, step=2)
random.seed(3)
for k in range(22):
    a = random.uniform(134, 170); z = random.uniform(ZG + 1.2, ZG + 2.1)
    pbox(f'Tool{k}', 6.86, a, z, (.04, random.uniform(.05, .14), random.uniform(.15, .4)), M_ORNG if k % 3 == 0 else M_RIB)
bx_ = pol(5.75, 150, ZG); Cyl('RobotBase', (bx_[0], bx_[1], ZG + .1), .28, .2, M_ORNG, v=32)
Cyl('RobotLink1', (bx_[0], bx_[1], ZG + .6), .09, .9, M_ORNG, rot=(0, 15, 150)); Cyl('RobotLink2', (bx_[0] - .25, bx_[1] + .2, ZG + 1.15), .07, .7, M_WHT, rot=(0, 70, 150))
for k, a in enumerate((138, 164)): pbox(f'Crate{k}', 5.75, a, ZG + .3, (.6, .6, .6), M_CRATE)
# lab (starboard aft)
ann('LabBench', 6.2, 6.95, 188, 228, ZG + .88, ZG + .93, M_LABW, step=2)
ann('LabBenchBody', 6.25, 6.95, 188, 228, ZG, ZG + .88, M_HW, step=2)
for k, a in enumerate((191, 225)):
    pbox(f'LabCabinet{k}', 6.7, a, ZG + 1.85, (.45, .9, 1.4), M_RAILG)
    for j in range(3): pbox(f'LabCabShelf{k}{j}', 6.7, a, ZG + 1.3 + j * .4, (.42, .86, .02), M_LABW)
random.seed(5)
for k in range(14):
    a = random.uniform(196, 220); Cyl(f'Tube{k}', pol(6.55, a, ZG + 1.02), .02, .16, M_CYAN if k % 2 else M_AMBER, v=10)
Cyl('Centrifuge', pol(6.5, 214, ZG + 1.05), .2, .25, M_LABW, v=32)
pbox('LabScreen', 6.92, 207, ZG + 1.55, (.03, .9, .55), M_SCR)
# ops (starboard forward)
ann('OpsDesk', 6.0, 6.6, 250, 286, ZG + .74, ZG + .78, M_HD, step=2); ann('OpsDeskBody', 6.3, 6.6, 250, 286, ZG, ZG + .74, M_HD, step=2)
for k, a in enumerate((256, 268, 280)): pbox(f'OpsScreen{k}', 6.45, a, ZG + 1.1, (.03, .65, .42), M_SCR if k != 1 else M_SCR2, tilt=-12)
pbox('OpsWallScreen', 6.95, 268, ZG + 1.75, (.03, 2.6, 1.2), M_SCR)
for k, a in enumerate((259, 277)):
    Cyl(f'OpsChairBase{k}', pol(5.55, a, ZG + .25), .05, .5, M_HD); soft(pbox(f'OpsChair{k}', 5.55, a, ZG + .52, (.5, .5, .1), M_SEAT), 2); soft(pbox(f'OpsChairBack{k}', 5.3, a, ZG + .85, (.08, .48, .6), M_SEAT), 2)
for k in range(8): Area(f'GalLight{k}', pol(6.1, 85 + k * 27.5, ZG + 2.7), .7, 55, (1, .93, .82))

# ---------------------------------------------------------------- 9. lower hall: benches, planters, light
for a0, a1 in ((108, 150), (210, 252)):
    ann(f'Bench{a0}', 6.35, 6.85, a0, a1, Z0, Z0 + .45, M_FAB, step=2); ann(f'BenchBack{a0}', 6.8, 6.95, a0, a1, Z0 + .45, Z0 + .95, M_FAB, step=2)
for a in (103, 155, 205, 257):
    pass   # v12: placeholder ball plants removed
lk = bpy.data.lights.new('Skylight', 'AREA'); lk.size = 2.6; lk.energy = 1400; lk.color = (.85, .9, 1)
o = bpy.data.objects.new('Skylight', lk); col.objects.link(o); o.location = (HC.x, HC.y, ZD - .25)
Area('HallFill', (HC.x, HC.y, ZS + .4), 3.0, 220, (1, .95, .88))
# ---- v12 accent: the reactor windows are the hall's one colour source (cyan, from the plasma behind the shield)
M_WINGLOW = pbsdf('WinGlow', (.02, .55, 1), 0, .3, (.02, .6, 1), 7)
for s in (-1, 1):
    yc = s * (WY0_ + WY1_) / 2; ww = WY1_ - WY0_
    Box(f'WinBackGlow{s}', (-12.75, yc, (WZ0 + WZ1) / 2), (.04, ww + .1, WZ1 - WZ0 + .1), M_WINGLOW)
    for zz in (WZ0 - .05, WZ1 + .05): Box(f'WinFrameGlow{s}{zz:.1f}', (-9.72, yc, zz), (.04, ww + .2, .05), M_WINGLOW)
    for yy in (WY0_ - .05, WY1_ + .05): Box(f'WinFrameGlowS{s}{yy:.1f}', (-9.72, s * yy, (WZ0 + WZ1) / 2), (.04, .05, WZ1 - WZ0 + .15), M_WINGLOW)
    la = Area(f'WinSpill{s}', (-10.0, yc, (WZ0 + WZ1) / 2), 1.0, 320, (.3, .8, 1)); la.data.shape = 'RECTANGLE'; la.data.size = ww; la.data.size_y = WZ1 - WZ0
    la.rotation_euler = (0, math.radians(-90), 0)   # faces +x, into the hall
    Box(f'WinWallWash{s}', (-9.7, yc, Z0 + .01), (.5, ww, .012), M_WINGLOW)

# ---- v12 wear: procedural grime + panel seams, decals and scuffs near doors
def grime(m, scale, amt, rough_add=.15):
    nt = m.node_tree; p = nt.nodes['Principled BSDF']; base = tuple(p.inputs['Base Color'].default_value)
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 8
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = .45; cr.color_ramp.elements[1].position = .75
    nt.links.new(nz.outputs['Fac'], cr.inputs['Fac'])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = (base[0] * (1 - amt), base[1] * (1 - amt), base[2] * (1 - amt), 1); mx.inputs[7].default_value = base
    nt.links.new(cr.outputs['Color'], mx.inputs[0]); nt.links.new(mx.outputs[2], p.inputs['Base Color'])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs[3].default_value = p.inputs['Roughness'].default_value + rough_add; mr.inputs[4].default_value = p.inputs['Roughness'].default_value
    nt.links.new(cr.outputs['Color'], mr.inputs[0]); nt.links.new(mr.outputs[0], p.inputs['Roughness'])
grime(M_HW, 3.0, .22); grime(M_HFL, 5.0, .35, .25)
M_SEAM = pbsdf('PanelSeam', (.08, .08, .085), .3, .6); M_SCUFF = pbsdf('Scuff', (.012, .012, .013), 0, .85)
M_DECW = pbsdf('DecalWhite', (.8, .8, .78), 0, .5); M_DECY = pbsdf('DecalYellow', (.75, .55, .05), 0, .5)
for zz in (Z0 + 1.25, Z0 + 2.6): ann(f'WallSeamH{zz:.1f}', HR - .012, HR - .002, 0, 360, zz, zz + .012, M_SEAM, step=2)
for k in range(32):
    a = k * 11.25 + 5.6
    if in_open(a, Z0 + 1.0) or in_open(a, ZG + 1.0): continue
    pbox(f'WallSeamV{k}', HR - .008, a, (Z0 + ZS) / 2, (.01, .012, ZS - Z0), M_SEAM)
for rr in (2.0, 5.2):
    ring_inlay(f'FloorSeam{rr:.0f}', rr, .006, M_SEAM)
for k in range(12):
    a = k * 30 + 15; c0 = pol(1.0, a, 0)
    if pit_hole(c0[0], c0[1]): continue
    for j in range(8):
        r_ = .5 + j * .8; c = pol(r_ + .4, a, 0)
        if r_ + .8 > HR or pit_hole(c[0], c[1]): continue
        pbox(f'FloorSeamR{k}_{j}', r_ + .4, a, Z0 + .003, (.8, .008, .004), M_SEAM)
random.seed(11)
for nm_, a_, zf_ in (('Mess', 90, Z0), ('Med', 270, Z0), ('Reactor', 180, Z0)):
    for j in range(7):   # scuffs on the floor at the threshold (trolleys, boots)
        rr = HR - random.uniform(.25, 1.3); aa = a_ + random.uniform(-7, 7)
        pbox(f'ScuffF{nm_}{j}', rr, aa, zf_ + .004, (random.uniform(.15, .5), random.uniform(.04, .12), .003), M_SCUFF, tilt=0)
    for e in (-1, 1):    # kick marks at the jambs + small decals
        pbox(f'ScuffW{nm_}{e}', HR - .006, a_ + e * dang(1.05), zf_ + .2, (.01, .25, .3), M_SCUFF)
        pbox(f'DecalPlate{nm_}{e}', HR - .008, a_ + e * dang(1.25), zf_ + 1.5, (.008, .16, .1), M_DECW)
        pbox(f'DecalStripe{nm_}{e}', HR - .008, a_ + e * dang(1.25), zf_ + 1.42, (.008, .16, .02), M_DECY)
for k in range(10):     # deck markings on the floor
    a = random.uniform(0, 360); c = pol(3.0, a, 0)
    if not pit_hole(c[0], c[1]): pbox(f'FloorArrow{k}', 3.0, a, Z0 + .004, (.25, .06, .002), M_DECY)

# ---- v13: no scale figures (user approved the scale on 2026-11-05); sizes unchanged
print('MODEL scale (no figure): floor to dome crown', round(ZD - Z0, 2), 'm; floor to gallery', round(ZG - Z0, 2), '; gallery to springline', round(ZS - ZG, 2), '; hall diameter', 2 * HR)

# ---- v13 real foliage: procedural leafy plants in pots (hall x4 where the ball plants stood, mess, med)
M_SOIL = pbsdf('Soil', (.05, .035, .025), 0, .9)
M_LEAF2 = pbsdf('LeafLight', (.11, .32, .07), 0, .5); M_LEAF3 = pbsdf('LeafDark', (.03, .14, .04), 0, .55)
for m_ in (M_LEAF, M_LEAF2, M_LEAF3):
    p_ = m_.node_tree.nodes['Principled BSDF']; p_.inputs['Subsurface Weight'].default_value = .15 if 'Subsurface Weight' in p_.inputs else 0
def plant(nm, x, y, z, seed, h=1.0, n=24, pot_r=.24):
    rnd = random.Random(seed)
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=pot_r * .72, radius2=pot_r, depth=.46, location=(x, y, z + .23))
    po = bpy.context.active_object; po.name = f'{nm}Pot'; po.data.materials.append(M_POT); soft(po, 1)
    Cyl(f'{nm}Soil', (x, y, z + .44), pot_r - .02, .02, M_SOIL, v=32)
    bm = bmesh.new(); fi = []; base = Vector((x, y, z + .43)); UP = Vector((0, 0, 1))
    for i in range(n):
        th = rnd.uniform(0, 2 * math.pi) if i else 0; L = h * rnd.uniform(.5, 1.0); up = rnd.uniform(.7, 1.5)
        W = L * rnd.uniform(.17, .26); d = Vector((math.cos(th), math.sin(th), 0)); side = Vector((-d.y, d.x, 0))
        tw = rnd.uniform(-.5, .5); stem = h * rnd.uniform(.0, .45); off = d * rnd.uniform(0, pot_r * .5)
        sd = side * math.cos(tw) + UP * math.sin(tw); rows = []
        for k in range(9):
            t = k / 8
            c = base + off + d * (L * .8 * t) + UP * (stem * min(1, t * 3) + L * up * .55 * (t - .7 * t * t))
            w = W * math.sin(math.pi * min(t * 1.05, 1)) ** .75 * (1 if t > .02 else .1)
            fold = UP * w * .18
            rows.append((bm.verts.new(c - sd * w / 2 + fold), bm.verts.new(c), bm.verts.new(c + sd * w / 2 + fold)))
        mi = rnd.randrange(3)
        for r0, r1 in zip(rows, rows[1:]):
            for j in range(2): bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1])); fi.append(mi)
    me_ = bpy.data.meshes.new(f'{nm}Leaves'); bm.to_mesh(me_); bm.free(); ob = bpy.data.objects.new(f'{nm}Leaves', me_); col.objects.link(ob)
    for m_ in (M_LEAF, M_LEAF2, M_LEAF3): me_.materials.append(m_)
    me_.polygons.foreach_set('material_index', fi); me_.polygons.foreach_set('use_smooth', [True] * len(me_.polygons)); return ob
for k, a in enumerate((103, 155, 205, 257)):
    c = pol(6.45, a, Z0); plant(f'HallPlant{k}', c[0], c[1], Z0, 40 + k, h=1.15 if k % 2 == 0 else .9, n=28)

# ---- v13 side rooms: MESS (port, +y) and MED BAY (starboard, -y), same floor as the hall, entered through the hall's 90/270 doors
for nm_ in ('Mess', 'Med'):
    for p_ in ('Door', 'DoorSeam'):
        o = bpy.data.objects.get(p_ + nm_)
        if o: bpy.data.objects.remove(o)
M_MESSF = pbsdf('MessFloor', (.2, .13, .08), 0, .42); M_MEDF = pbsdf('MedFloor', (.4, .43, .46), 0, .32)
M_PORTG = glass('PortGlass', (.85, .93, 1)); M_CEILP = pbsdf('CeilPanel', (1, .96, .9), 0, .5, (1, .93, .82), 6)
M_STEEL = pbsdf('Steel', (.62, .62, .64), 1.0, .22); M_CNT = pbsdf('Counter', (.07, .07, .08), .1, .18)
M_CAB = pbsdf('Cabinet', (.66, .66, .63), 0, .4); M_MATT = pbsdf('Mattress', (.86, .89, .92), 0, .7)
M_CURT = pbsdf('Curtain', (.32, .52, .58), 0, .85); M_GRN = pbsdf('MedGreen', (.1, .9, .4), 0, .5, (.1, 1, .45), 5)
M_SKIN = M_WHT
grime(M_MESSF, 4.0, .25, .2); grime(M_MEDF, 6.0, .12, .1)
WIN = (SX0 + 1.0, SX1 - .8, Z0 + .95, Z0 + 1.85)    # window: x0, x1, z0, z1 (outer wall)
DX0, DX1 = HC.x - .8, HC.x + .8                       # doorway from the hall
def YB(s, y0, y1): return (s * (y0 + y1) / 2, abs(y1 - y0))
def side_shell(s, nm, floor_m, wall_m):
    xc = (SX0 + SX1) / 2; L = SX1 - SX0; D = SYO - SYI
    Box(f'{nm}Floor', (xc, s * (SYI + SYO) / 2, Z0 - .075), (L, D, .15), floor_m)
    Box(f'{nm}Threshold', (HC.x, s * 7.25, Z0 - .075), (DX1 - DX0 + .1, .75, .15), floor_m)
    Box(f'{nm}Ceiling', (xc, s * (SYI + SYO) / 2, SZC + .04), (L, D, .08), wall_m)
    # inner wall (toward the hall) with the doorway
    for x0, x1 in ((SX0, DX0), (DX1, SX1)): Box(f'{nm}WallIn{x0:.0f}', ((x0 + x1) / 2, s * (SYI - .05), (Z0 + SZC) / 2), (x1 - x0, .1, SZC - Z0), wall_m)
    Box(f'{nm}WallInHead', (HC.x, s * (SYI - .05), (Z0 + 2.3 + SZC) / 2), (DX1 - DX0, .1, SZC - Z0 - 2.3), wall_m)
    # outer wall with a long window
    wx0, wx1, wz0, wz1 = WIN; yo = s * (SYO + .03)
    Box(f'{nm}WallOutLo', (xc, yo, (Z0 + wz0) / 2), (L, .06, wz0 - Z0), wall_m); Box(f'{nm}WallOutHi', (xc, yo, (wz1 + SZC) / 2), (L, .06, SZC - wz1), wall_m)
    Box(f'{nm}WallOutA', ((SX0 + wx0) / 2, yo, (wz0 + wz1) / 2), (wx0 - SX0, .06, wz1 - wz0), wall_m); Box(f'{nm}WallOutF', ((wx1 + SX1) / 2, yo, (wz0 + wz1) / 2), (SX1 - wx1, .06, wz1 - wz0), wall_m)
    rv = (FYO - .15) - (SYO + .06); yr = s * (SYO + .06 + rv / 2)
    for zz in (wz0, wz1): Box(f'{nm}WinRev{zz:.1f}', ((wx0 + wx1) / 2, yr, zz), (wx1 - wx0, rv, .04), M_HD)
    for xx in (wx0, wx1): Box(f'{nm}WinRevS{xx:.1f}', (xx, yr, (wz0 + wz1) / 2), (.04, rv, wz1 - wz0), M_HD)
    Box(f'{nm}WinGlass', ((wx0 + wx1) / 2, s * (FYO - .08), (wz0 + wz1) / 2), (wx1 - wx0, .03, wz1 - wz0), M_PORTG)
    Box(f'{nm}WinSill', ((wx0 + wx1) / 2, s * (SYO - .02), wz0 - .02), (wx1 - wx0 + .1, .12, .04), M_HD)
    for xx in (SX0 - .03, SX1 + .03): Box(f'{nm}WallEnd{xx:.0f}', (xx, s * (SYI + SYO) / 2, (Z0 + SZC) / 2), (.06, SYO - SYI + .1, SZC - Z0), wall_m)
    # seams + skirting
    for k in range(1, 8):
        x = SX0 + k * (SX1 - SX0) / 8
        if not (wx0 < x < wx1): Box(f'{nm}SeamO{k}', (x, s * (SYO - .005), (Z0 + SZC) / 2), (.012, .01, SZC - Z0), M_SEAM)
        if not (DX0 - .1 < x < DX1 + .1): Box(f'{nm}SeamI{k}', (x, s * (SYI + .005), (Z0 + SZC) / 2), (.012, .01, SZC - Z0), M_SEAM)
    for y_ in (SYI + .01, SYO - .01): Box(f'{nm}Skirt{y_:.0f}', ((SX0 + SX1) / 2, s * y_, Z0 + .05), (SX1 - SX0, .02, .1), M_HD)
    # ceiling light panels + lights (lights hidden from camera at render time)
    for k, x in enumerate((SX0 + 1.5, HC.x, SX1 - 1.5)):
        Box(f'{nm}CeilPanel{k}', (x, s * (SYI + SYO) / 2, SZC - .01), (1.5, .7, .02), M_CEILP)
        Area(f'{nm}Light{k}', (x, s * (SYI + SYO) / 2, SZC - .12), 1.3, 110, (1, .9, .78) if s > 0 else (.92, .97, 1))
    # exterior sponson fairing: bevelled box, hollowed, window cut, livery stripe
    fo = Box(f'{nm}Sponson', ((FX0 + FX1) / 2, s * (FYI + FYO) / 2, (FZ0 + FZ1) / 2), (FX1 - FX0, FYO - FYI, FZ1 - FZ0), M_SKIN)
    bv = fo.modifiers.new('Bev', 'BEVEL'); bv.width = .28; bv.segments = 5; bv.limit_method = 'ANGLE'
    bpy.ops.mesh.primitive_cube_add(size=1, location=((FX0 + FX1) / 2, s * (FYI - .3 + FYO - .15) / 2, (FZ0 + .15 + FZ1 - .15) / 2))
    cut = bpy.context.active_object; cut.name = f'{nm}SponsonCut'; cut.scale = (FX1 - FX0 - .3, FYO - .15 - (FYI - .3), FZ1 - FZ0 - .3)
    bpy.ops.mesh.primitive_cube_add(size=1, location=((wx0 + wx1) / 2, s * FYO, (wz0 + wz1) / 2))
    wcut = bpy.context.active_object; wcut.name = f'{nm}SponsonWinCut'; wcut.scale = (wx1 - wx0, .8, wz1 - wz0)
    for c_ in (cut, wcut):
        b_ = fo.modifiers.new('Cut', 'BOOLEAN'); b_.operation = 'DIFFERENCE'; b_.object = c_; b_.solver = 'EXACT'; c_.hide_render = True; c_.hide_viewport = True
        c_.display_type = 'WIRE'
    Box(f'{nm}SponsonStripe', ((FX0 + FX1) / 2 + .1, s * (FYO + .004), Z0 + .45), (FX1 - FX0 - .7, .01, .12), M_ORNG)
    return fo
SIDE_CUTTERS = []
for s, nm in ((1, 'Mess'), (-1, 'Med')):
    side_shell(s, nm, M_MESSF if s > 0 else M_MEDF, M_HW if s > 0 else M_LABW)
    SIDE_CUTTERS += [f'{nm}SponsonCut', f'{nm}SponsonWinCut']

# MESS fit-out (port)
s = 1; YM = (SYI + SYO) / 2
Box('GalleyBase', (SX0 + .33, s * 9.3, Z0 + .45), (.65, 2.9, .9), M_CAB); Box('GalleyTopV13', (SX0 + .34, s * 9.3, Z0 + .92), (.69, 2.94, .04), M_CNT)
Box('GalleyUpper', (SX0 + .19, s * 9.3, Z0 + 1.95), (.36, 2.9, .7), M_CAB)
Box('GalleyUnderLight', (SX0 + .36, s * 9.3, Z0 + 1.58), (.02, 2.8, .02), M_RING)
for k in range(4): Box(f'GalleyDoorLine{k}', (SX0 + .665, s * (7.95 + k * .72), Z0 + .45), (.005, .01, .8), M_SEAM)
Box('GalleySink', (SX0 + .36, s * 8.4, Z0 + .943), (.42, .5, .01), M_STEEL); Cyl('GalleyTap', (SX0 + .12, s * 8.4, Z0 + 1.05), .016, .22, M_STEEL)
for k in range(4): Cyl(f'Hob{k}', (SX0 + .24 + (k % 2) * .22, s * (9.7 + (k // 2) * .26), Z0 + .944), .08, .006, M_HD, v=24)
Box('CoffeeMachine', (SX0 + .28, s * 10.45, Z0 + 1.12), (.32, .28, .36), M_HD); Box('CoffeeScr', (SX0 + .445, s * 10.45, Z0 + 1.2), (.005, .14, .08), M_SCR2)
Box('FridgeV13', (SX1 - .36, s * 10.5, Z0 + 1.0), (.66, .8, 2.0), M_STEEL); Box('FridgeHandleV13', (SX1 - .7, s * 10.2, Z0 + 1.1), (.03, .03, .7), M_HD)
Box('MenuWall', (SX1 - .02, s * 9.0, Z0 + 1.6), (.02, 1.3, .65), M_SCR2)
Box('WindowBench', ((WIN[0] + WIN[1]) / 2, s * (SYO - .27), Z0 + .23), (WIN[1] - WIN[0], .5, .46), M_FAB)
Box('WindowBenchBack', ((WIN[0] + WIN[1]) / 2, s * (SYO - .06), Z0 + .68), (WIN[1] - WIN[0], .1, .5), M_FAB)
for k, tx in enumerate((-4.6, -1.5)):
    Box(f'MessTop{k}', (tx, s * 9.95, Z0 + .74), (1.7, .85, .04), M_WOOD); Cyl(f'MessPed{k}', (tx, s * 9.95, Z0 + .36), .06, .72, M_STEEL); Cyl(f'MessFoot{k}', (tx, s * 9.95, Z0 + .01), .3, .02, M_STEEL, v=32)
    for e in (-1, 1):
        cx = tx + e * .45
        soft(Box(f'MessChair{k}{e}', (cx, s * 9.15, Z0 + .46), (.44, .44, .06), M_SEAT), 2); soft(Box(f'MessChairBack{k}{e}', (cx, s * 8.93, Z0 + .76), (.44, .05, .5), M_SEAT), 2)
        Cyl(f'MessChairPost{k}{e}', (cx, s * 9.15, Z0 + .22), .025, .44, M_STEEL)
    for j in range(3): Cyl(f'MessPlateV13{k}{j}', (tx - .55 + j * .55, s * (9.95 + (j % 2 - .5) * .3), Z0 + .767), .11, .012, M_LABW, v=24)
    Cyl(f'MessMug{k}', (tx + .3, s * 9.75, Z0 + .81), .04, .1, M_ORNG, v=16)
plant('MessPlant', SX1 - .4, s * (SYI + .45), Z0, 61, h=.95, n=24)

# MED BAY fit-out (starboard)
s = -1
for k, bx in enumerate((-5.1, -1.0)):
    yb = s * 10.35
    Box(f'MedBedBase{k}', (bx, yb, Z0 + .3), (1.95, .86, .26), M_CAB); soft(Box(f'MedMattress{k}', (bx, yb, Z0 + .51), (1.9, .82, .16), M_MATT), 2)
    soft(Box(f'MedPillow{k}', (bx - .72, yb, Z0 + .63), (.34, .6, .09), M_MATT), 2)
    bpy.ops.mesh.primitive_torus_add(major_radius=.7, minor_radius=.045, location=(bx + .25, yb, Z0 + .45), rotation=(0, math.radians(90), 0))
    ao = bpy.context.active_object; ao.name = f'MedScanArch{k}'; ao.data.materials.append(M_CYAN)
    Cyl(f'MedMonPost{k}', (bx - 1.15, s * 9.75, Z0 + .9), .03, 1.8, M_STEEL); Box(f'MedMonArm{k}', (bx - 1.0, s * 9.75, Z0 + 1.7), (.35, .04, .04), M_STEEL)
    Box(f'MedMonitorV13{k}', (bx - .85, s * 9.75, Z0 + 1.55), (.03, .5, .34), M_SCR, rot=(0, 0, 25))
    Cyl(f'MedIV{k}', (bx + 1.15, s * 9.8, Z0 + .95), .015, 1.9, M_STEEL); Box(f'MedIVBag{k}', (bx + 1.15, s * 9.8, Z0 + 1.7), (.05, .13, .22), M_RAILG)
# curtain between the beds on a ceiling track
Box('MedCurtTrack', (-3.05, s * 9.9, SZC - .06), (.04, 2.2, .03), M_STEEL)
V = []; F = []
for i in range(25):
    y_ = 8.9 + 2.0 * i / 24; xw = -3.05 + .06 * math.sin(i * 1.3)
    V += [(xw, s * y_, Z0 + .25), (xw, s * y_, SZC - .1)]
for i in range(24): F.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
mk('MedCurtain', V, F, M_CURT, smooth=True)
Box('MedCabBase', (SX0 + .3, s * 9.3, Z0 + .45), (.6, 2.7, .9), M_LABW); Box('MedCabTop', (SX0 + .31, s * 9.3, Z0 + .92), (.63, 2.74, .04), M_CNT)
Box('MedCabUpper', (SX0 + .19, s * 9.3, Z0 + 1.9), (.36, 2.7, .8), M_LABW); Box('MedCabGlass', (SX0 + .38, s * 9.3, Z0 + 1.9), (.01, 2.6, .7), M_RAILG)
random.seed(21)
for k in range(18): Cyl(f'MedBottle{k}', (SX0 + .2, s * (8.1 + random.uniform(0, 2.4)), Z0 + 1.6 + (k % 2) * .38), .035, random.uniform(.1, .2), M_AMBER if k % 3 == 0 else M_LABW, v=12)
Box('MedSinkV13', (SX0 + .33, s * 8.3, Z0 + .943), (.4, .45, .01), M_STEEL); Cyl('MedTap', (SX0 + .1, s * 8.3, Z0 + 1.05), .016, .22, M_STEEL)
Box('MedDesk', (SX1 - .35, s * 8.6, Z0 + .74), (.6, 1.4, .04), M_CNT); Box('MedDeskBody', (SX1 - .35, s * 8.2, Z0 + .37), (.58, .5, .72), M_LABW)
Box('MedTerminal', (SX1 - .1, s * 8.6, Z0 + 1.25), (.03, .9, .5), M_SCR, rot=(0, -8, 0))
soft(Box('MedStool', (SX1 - .95, s * 8.7, Z0 + .5), (.4, .4, .06), M_SEAT), 2); Cyl('MedStoolPost', (SX1 - .95, s * 8.7, Z0 + .25), .025, .5, M_STEEL)
Box('MedScanner', (SX1 - .32, s * 10.45, Z0 + 1.0), (.56, .9, 2.0), M_LABW); Box('MedScannerStrip', (SX1 - .6, s * 10.45, Z0 + 1.0), (.01, .05, 1.6), M_CYAN)
Box('MedCrossH', (SX1 - .02, s * 8.6, Z0 + 2.15), (.02, .36, .11), M_GRN); Box('MedCrossV', (SX1 - .02, s * 8.6, Z0 + 2.15), (.02, .11, .36), M_GRN)
Box('MedDefib', (SX0 + 2.6, s * (SYI + .06), Z0 + 1.4), (.35, .1, .4), M_GRN)
plant('MedPlant', SX1 - .4, s * (SYI + .45), Z0, 77, h=.85, n=22)
print('MODEL v13 side rooms: x', SX0, SX1, '|y|', SYI, SYO, 'floor', Z0, 'ceiling', SZC, '; sponson x', FX0, FX1, '|y|', FYI, FYO, 'z', FZ0, FZ1)
dg_ = bpy.context.evaluated_depsgraph_get()
for nm_, a_, zz_ in (('fwd_lane', 0, ZF + 1.2), ('mess', 90, Z0 + 1.2), ('med', 270, Z0 + 1.2), ('reactor', 180, Z0 + 1.2), ('gal_fwd', 0, ZG + 1.2)):
    o_ = Vector(pol(HR + .45, a_, zz_)); d_ = (o_ - Vector((HC.x, HC.y, zz_))).normalized()
    h1 = sc.ray_cast(dg_, o_, d_, distance=12); h2 = sc.ray_cast(dg_, o_ + d_ * 1.0, Vector((0, 0, -1)), distance=4)
    print('MODEL door', nm_, 'ahead', (h1[4].name if h1[0] else None), round((h1[1] - o_).length, 2) if h1[0] else None,
          'floor', (h2[4].name if h2[0] else None), round(h2[1].z, 2) if h2[0] else None)
print('MODEL hall built: floor', Z0, 'gallery', ZG, 'dome', ZD, 'centre', tuple(HC))

CEIL = [o for o in bpy.data.objects if any(t in o.name for t in ('CeilStrip', 'CeilLight', 'Cable', 'ReactorCap', 'Frame'))]


# ================================================================== v15: ARC REACTOR replaces the tokamak; cabins re-dressed
for o in list(bpy.data.objects):
    if o.name.startswith(('VacuumVessel', 'PlasmaPort', 'CentralSolenoid', 'SolenoidBand', 'TFCoil', 'PFCoil', 'ReactorBand', 'NBInjector', 'NBDuct', 'CryoColumn', 'CryoTopRing')):
        bpy.data.objects.remove(o)
M_ARC = pbsdf('ArcGlow', (.35, .85, 1), 0, .2, (.3, .85, 1), 45)
M_ARCCORE = pbsdf('ArcCore', (.9, 1, 1), 0, .1, (.75, .97, 1), 120)
M_ARCRIM = pbsdf('ArcRim', (.55, .57, .6), 1, .25)
RA = 1.2; XR = EX + .3          # reactor disc faces +x (towards the shield stairs and the hall windows)
Box('ArcPedestal', (XR - .35, 0, (ZA + .3 + zc_ - RA) / 2 + .05), (.7, 1.1, zc_ - RA - ZA - .1), M_ARCRIM)
Cyl('ArcBackplate', (XR - .25, 0, zc_), RA + .2, .25, M_THR, rot=(0, 90, 0), v=64)
Tor('ArcOuterRim', (XR, 0, zc_), RA + .08, .12, M_ARCRIM, rot=(0, 90, 0), ms=96, ns=16)
Tor('ArcOuterGlow', (XR + .06, 0, zc_), RA - .08, .035, M_ARC, rot=(0, 90, 0), ms=96, ns=8)
NSEG = 10
for k in range(NSEG):   # copper-wound coil blocks around the ring, glowing gaps between them
    a = k * 360 / NSEG; t = math.radians(a); rr = RA - .3
    Box(f'ArcCoil{k}', (XR + .05, rr * math.cos(t), zc_ + rr * math.sin(t)), (.22, .3, .2), M_COPPER, rot=(a, 0, 0))
    for j in range(4): Box(f'ArcWind{k}_{j}', (XR + .17, (rr - .1 + j * .066) * math.cos(t), zc_ + (rr - .1 + j * .066) * math.sin(t)), (.01, .3, .02), M_ARCRIM, rot=(a, 0, 0))
    ta = math.radians(a + 180 / NSEG)
    Box(f'ArcGap{k}', (XR + .03, rr * math.cos(ta), zc_ + rr * math.sin(ta)), (.12, .06, .26), M_ARC, rot=(a + 180 / NSEG, 0, 0))
spin = piv('Anim_ArcSpin', (XR, 0, zc_))
Tor('ArcInnerRing', (XR + .1, 0, zc_), .5, .05, M_ARC, rot=(0, 90, 0), ms=64, ns=8)
for k in range(6):
    a = k * 60; t = math.radians(a)
    att(Box(f'ArcSpoke{k}', (XR + .12, .3 * math.cos(t), zc_ + .3 * math.sin(t)), (.04, .05, .5), M_ARCRIM, rot=(a + 90, 0, 0)), spin)
keyv(spin, 0, [(1, 0), (240, 240 * .2)], lin=True)
Cyl('ArcCore', (XR + .1, 0, zc_), .28, .2, M_ARCCORE, rot=(0, 90, 0), v=48)
bpy.ops.mesh.primitive_uv_sphere_add(radius=.3, location=(XR + .2, 0, zc_)); o = bpy.context.active_object; o.name = 'ArcDome'; o.scale = (.45, 1, 1); o.data.materials.append(M_LEADG if False else glass('ArcDomeGlass', (.8, .95, 1), .02))
for nm_ in ('ReactorGlow', 'ReactorLight'):
    L_ = bpy.data.objects.get(nm_)
    if L_: L_.location = (XR + .9, 0, zc_); L_.data.energy = 2500; L_.data.color = (.35, .8, 1)
# lead-glass windows: clearer so the reactor glow reads from the hall
for o in bpy.data.objects:
    if o.name.startswith('LeadGlass'): o.data.materials.clear(); o.data.materials.append(glass('LeadGlassClear', (.8, .95, .95), .01))
print('MODEL v15 arc reactor at', round(XR, 2), 0, round(zc_, 2), 'radius', RA)
# cabins: warmer, softer, a view screen over each bunk
M_LINEN = pbsdf('Linen', (.85, .84, .8), 0, .8); M_BLANK = pbsdf('Blanket', (.55, .2, .07), 0, .85)
M_HEAD = pbsdf('Headboard', (.32, .3, .28), 0, .9); M_VIEW = pbsdf('CabinView', (.02, .04, .1), 0, .1, (.06, .16, .4), 3)
for k in (2, 3):
    x0, x1 = ROOMS[k]; xc = (x0 + x1) / 2; bl = min(2.0, x1 - x0 - 1.15); bx = x0 + .65 + bl / 2
    for s in (-1, 1):
        for pre, m in (('Mattress', M_LINEN), ('Pillow', M_LINEN), ('Blanket', M_BLANK), ('Desk', M_WOOD), ('Nightstand', M_WOOD)):
            o = bpy.data.objects.get(f'{pre}{s}{k}')
            if o: o.data.materials.clear(); o.data.materials.append(m)
        yo = outer_y(bx, s, ZF + .7); by = yo - s * .5
        soft(Box(f'Headboard{s}{k}', (x0 + .63, by, ZF + .85), (.08, .95, .75), M_HEAD), 2)
        Box(f'ViewScreen{s}{k}', (bx + .2, yo - s * .05, ZF + 1.5), (bl * .6, .02, .45), M_VIEW)
        Box(f'ViewFrame{s}{k}', (bx + .2, yo - s * .04, ZF + 1.5), (bl * .6 + .08, .015, .53), M_ARCRIM)
        for st in range(14):
            random.seed(k * 100 + st + (s > 0) * 50)
            Box(f'Star{s}{k}{st}', (bx + .2 + random.uniform(-bl * .28, bl * .28), yo - s * .062, ZF + 1.5 + random.uniform(-.2, .2)), (.012, .003, .012), M_RING)
        soft(Box(f'DeskChair{s}{k}', (x1 - .75, s * (HW + .7), ZF + .47), (.42, .42, .06), M_SEAT), 2)
        L_ = bpy.data.objects.get(f'RoomL{s}{k}')
        if L_: L_.data.energy = 150

# ================================================================== v16: FUSION-FISSION HYBRID core, exterior detailing
for o in list(bpy.data.objects):
    if o.name.startswith(('Arc', 'Anim_ArcSpin')): bpy.data.objects.remove(o)
M_PLASMA = pbsdf('Plasma', (.3, .5, 1), 0, .2, (.3, .5, 1), 7)
M_PLASMAH = pbsdf('PlasmaHalo', (.5, .3, 1), 0, .3, (.55, .3, 1), 3)
M_CHER = pbsdf('Cherenkov', (.08, .3, 1), 0, .2, (.1, .4, 1), 1.8)
M_ROD = pbsdf('ControlRod', (.06, .06, .07), .8, .35)
M_TANK = glass('TankGlass', (.85, .95, 1), .02)
T0, T1 = ZA + .35, ZA + 2.85
Cyl('BlanketTank', (EX, 0, (T0 + T1) / 2), 1.62, T1 - T0, M_TANK, v=64)
for z in (T0 + .02, T1): Tor(f'TankRim{z:.1f}', (EX, 0, z), 1.64, .06, M_ARCRIM, ms=64, ns=8)
for k in range(8):
    a = k * math.pi / 4; Cyl(f'TankRib{k}', (EX + 1.66 * math.cos(a), 1.66 * math.sin(a), (T0 + T1) / 2), .035, T1 - T0, M_ARCRIM)
# fission blanket: hexagonal fuel assemblies in two rings, glowing Cherenkov blue
for ring, (rr, n) in enumerate(((1.12, 18), (1.38, 22))):
    for k in range(n):
        a = (k + ring * .5) * 2 * math.pi / n
        Cyl(f'FuelAsm{ring}_{k}', (EX + rr * math.cos(a), rr * math.sin(a), T0 + 1.1), .085, 1.9, M_CHER, v=6)
        Cyl(f'FuelCap{ring}_{k}', (EX + rr * math.cos(a), rr * math.sin(a), T0 + 2.08), .09, .06, M_ARCRIM, v=6)
for k in range(8):   # control rods withdrawn half way, drive mechanisms on the gantry
    a = k * math.pi / 4 + math.pi / 8; x_, y_ = EX + 1.25 * math.cos(a), 1.25 * math.sin(a)
    Cyl(f'CtrlRod{k}', (x_, y_, T1 - .1), .045, 1.4, M_ROD)
    Box(f'CtrlDrive{k}', (x_, y_, T1 + .75), (.16, .16, .3), M_THR)
Tor('RodGantry', (EX, 0, T1 + .6), 1.25, .05, M_RIB, ms=64, ns=8)
for k in range(4):
    a = k * math.pi / 2; Box(f'GantryBeam{k}', (EX + .62 * math.cos(a), .62 * math.sin(a), T1 + .6), (1.25, .08, .08), M_RIB, rot=(0, 0, math.degrees(a)))
# fusion core: blue plasma ring with a purple halo, inside a cage of copper field coils
Tor('FusionPlasma', (EX, 0, zc_), .68, .13, M_PLASMA, ms=96, ns=16)
Tor('FusionHalo', (EX, 0, zc_), .68, .21, M_PLASMAH, ms=96, ns=16)
for k in range(14):
    a = k * 2 * math.pi / 14; Tor(f'FieldCoil{k}', (EX + .68 * math.cos(a), .68 * math.sin(a), zc_), .3, .022, M_COPPER, rot=(90, 0, math.degrees(a) + 90), ms=32, ns=6)
Cyl('FusionSolenoid', (EX, 0, zc_), .16, 1.6, M_RIB, v=32)
Cyl('CorePlinth', (EX, 0, (T0 + zc_ - .45) / 2), .35, zc_ - .45 - T0, M_ARCRIM, v=32)
for nm_, loc_, col_, e_ in (('ReactorGlow', (EX + 1.9, 0, zc_), (.3, .5, 1), 300), ('ReactorLight', (EX, 0, zc_ + .45), (.55, .35, 1), 120)):
    L_ = bpy.data.objects.get(nm_)
    if L_: L_.location = loc_; L_.data.energy = e_; L_.data.color = col_
print('MODEL v16 hybrid core: fuel assemblies 40, control rods 8, plasma R .68')
# exterior: hull plating, vents, nav lights placed on the skin by ray casting
M_PLATE = pbsdf('HullPlate', (.62, .64, .67), .55, .38); M_PLATED = pbsdf('HullPlateDark', (.2, .21, .23), .6, .45)
M_NAVR = pbsdf('NavRed', (1, .1, .05), 0, .3, (1, .1, .05), 30); M_NAVG = pbsdf('NavGreen', (.1, 1, .2), 0, .3, (.1, 1, .2), 30)
dg = bpy.context.evaluated_depsgraph_get()
bb = [hull.matrix_world @ Vector(c) for c in hull.bound_box]
bx0, bx1 = min(v.x for v in bb), max(v.x for v in bb); by0, by1 = min(v.y for v in bb), max(v.y for v in bb); bz0, bz1 = min(v.z for v in bb), max(v.z for v in bb)
random.seed(16); placed = 0; tip = {1: None, -1: None}
def skin_hit(o_, d_):
    hit, p_, n_, fi, ob, m_ = sc.ray_cast(dg, Vector(o_), Vector(d_))
    if not hit or ob is None or ob.name != 'Hull': return None
    try:
        mn = (ob.material_slots[ob.data.polygons[fi].material_index].material.name or '').lower()
        if any(w in mn for w in ('glass', 'canopy', 'window', 'light', 'emit')): return None
    except Exception: pass
    return p_, n_
def plate(name, p_, n_, size, mat):
    o = Box(name, (0, 0, 0), size, mat); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(n_)
    o.location = p_ + n_ * (size[2] / 2 - .005); return o
for x in np.arange(bx0 + .6, bx1 - .6, .85):
    for y in np.arange(by0 + .4, by1 - .4, 1.0):
        r = skin_hit((x + random.uniform(-.2, .2), y, bz1 + 3), (0, 0, -1))
        if not r: continue
        p_, n_ = r
        if n_.z < .3: continue
        s_ = 1 if y > 0 else -1
        if tip[s_] is None or abs(y) > abs(tip[s_].y): tip[s_] = p_.copy()
        u = random.random()
        if u < .22: plate(f'XPlate{placed}', p_, n_, (random.uniform(.4, 1.1), random.uniform(.3, .8), .035), M_PLATE)
        elif u < .30: plate(f'XVent{placed}', p_, n_, (.6, .32, .05), M_PLATED); [plate(f'XVentSlat{placed}_{j}', p_ + Vector((-.24 + j * .12, 0, 0)), n_, (.03, .3, .075), M_PLATE) for j in range(5)]
        elif u < .34: plate(f'XHatch{placed}', p_, n_, (.5, .5, .04), M_PLATED)
        else: continue
        placed += 1
for side in (-1, 1):
    for x in np.arange(bx0 + .6, bx1 - .6, .9):
        for z in np.linspace(bz0 + .5, bz1 - .5, 5):
            if random.random() > .35: continue
            r = skin_hit((x, side * (by1 + 3), z), (0, -side, 0))
            if not r: continue
            p_, n_ = r
            if abs(n_.y) < .4: continue
            plate(f'XSide{placed}', p_, n_, (random.uniform(.5, 1.4), random.uniform(.25, .6), .035), M_PLATE if random.random() < .7 else M_PLATED); placed += 1
for s_, m_, c_ in ((1, M_NAVR, (1, .1, .05)), (-1, M_NAVG, (.1, 1, .2))):   # port red (+y), starboard green
    if tip[s_] is None: continue
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.12, location=tip[s_] + Vector((0, 0, .1))); o = bpy.context.active_object; o.name = f'NavLight{s_}'; o.data.materials.append(m_)
    ld = bpy.data.lights.new(f'NavL{s_}', 'POINT'); ld.energy = 60; ld.color = c_; lo = bpy.data.objects.new(f'NavL{s_}', ld); col.objects.link(lo); lo.location = tip[s_] + Vector((0, 0, .4))
print('MODEL v16 exterior details', placed, 'tips', tip)
# ================================================================== v17 PASS: clean hull, crew deck at hall level, keel entrance bay
print('MODEL v17 pass start')
from mathutils.bvhtree import BVHTree as _BVH
def _rm(o):
    try: bpy.data.objects.remove(o, do_unlink=True)
    except Exception as e: print('Error rm', e)
# ---- A1. drop the script's own landing gear / nose strut, old stepped ramp + rails + pivot, hall pit + lane, hazard stripes, h5 back glow
V17_DEL = ('GearPiv', 'Gear0_', 'Gear1_', 'Gear2_', 'G0', 'G1', 'G2', 'GearDoor', 'Anim_GearDoor', 'Ramp', 'PitStep', 'PitNose', 'PitEnd', 'PitRail',
           'LaneWall', 'LaneRail', 'LaneStrip', 'LaneFloor', 'LaneLintel', 'FwdJamb', 'ReactorHaz', 'WinBackGlow', 'HatchEdge', 'Bench')
_nd = 0
for o in list(bpy.data.objects):
    if o.name.startswith(V17_DEL): _rm(o); _nd += 1
for o in bpy.data.objects:
    if o.type == 'MESH':
        for i, m in enumerate(o.data.materials):
            if m == M_HAZ: o.data.materials[i] = M_HD
print('MODEL v17 removed gear/ramp/pit/haz/bench objects', _nd)
dg = bpy.context.evaluated_depsgraph_get()
def bvh_of(names):
    V = []; F = []
    for nm in names:
        o = bpy.data.objects.get(nm)
        if not o or o.type != 'MESH': continue
        oe = o.evaluated_get(dg); me_ = oe.to_mesh(); M = o.matrix_world; b = len(V)
        n_ = len(me_.vertices); c_ = np.empty(n_ * 3, np.float32); me_.vertices.foreach_get('co', c_); c_ = c_.reshape(-1, 3)
        Mw = np.array(M); c_ = c_ @ Mw[:3, :3].T + Mw[:3, 3]
        V += [tuple(v) for v in c_.tolist()]; F += [tuple(b + i for i in p.vertices) for p in me_.polygons]
        oe.to_mesh_clear()
    return _BVH.FromPolygons(V, F)
HB = bvh_of(['Hull'])
def hdist(p, d, far=20.0):
    h = HB.ray_cast(Vector(p), Vector(d).normalized(), far); return h[3] if h[0] is not None else None
def arc_x(y, r=HR): return HC.x + math.sqrt(max(r * r - y * y, 0.0))
def rr_(P_): return np.hypot(P_[:, 0] - HC.x, P_[:, 1] - HC.y)

# ---- A2. crew block outline from the hull (ray cast at floor, waist, head and ceiling height), inset 0.23 m
CX0, CX1, CXB = 2.2, 12.15, 12.45
CXS = np.arange(CX0, CX1 + .001, .25)
def hw_at(x):
    ws = []
    for z in (Z0 - .22, Z0 + .3, Z0 + 1.2, Z0 + 2.46):
        for s in (1, -1):
            d = hdist((x, 0, z), (0, s, 0)); ws.append(d if d else 6.0)
    return min(ws)
CHW = np.array([min(4.6, hw_at(float(x)) - .23) for x in CXS])
print('MODEL v17 crew half-width', np.round(CXS[::4], 2).tolist(), np.round(CHW[::4], 2).tolist())
def chw(x): return float(np.interp(x, CXS, CHW))
# clear everything old inside the crew block volume (old ZF deck, v3 rooms, lining, partitions, lights), keep the hall and the exterior
def t_crew(P_):
    x, y, z = P_[:, 0], np.abs(P_[:, 1]), P_[:, 2]
    return (rr_(P_) > HR + .45) & (x < CXB) & (y < np.interp(x, CXS, CHW) + .15) & (z > -2.45) & (z < 3.6) & ~((x > CX1 + .05) & (z < ZB + .05))
KEEP_PFX = ('Hull', 'Hall', 'X', 'Nav', 'Strobe', 'Thruster', 'Exhaust', 'Plume', 'Winglet', 'Strake', 'Skylight', 'Dome')
_nc = 0
for o in list(bpy.data.objects):
    if o.name.startswith(KEEP_PFX): continue
    if o.type == 'MESH':
        try: _nc += carve_faces(o, t_crew)
        except Exception as e: print('Error crewcarve', o.name, e)
    elif o.type in ('LIGHT', 'CURVE'):
        if t_crew(np.array([list(o.matrix_world.translation)]))[0]: _rm(o); _nc += 1
print('MODEL v17 crew volume cleared faces/objs', _nc)
# floor: one continuous plate at hall level (Z0), aft edge on the hall circle, sides inset from the hull
def strip_mesh(name, z, mat, th, off=-1, nv_=24, x0=None):
    V = []; F = []; xs_ = [x for x in CXS if x0 is None or x >= x0]
    for x in xs_:
        h_ = chw(x)
        for j in range(nv_ + 1):
            y = (j / nv_ * 2 - 1) * h_; V.append((max(float(x), arc_x(y) - .02), y, z))
    for i in range(len(xs_) - 1):
        for j in range(nv_):
            a = i * (nv_ + 1) + j; F.append((a, a + nv_ + 1, a + nv_ + 2, a + 1))
    o = mk(name, V, F, mat); s_ = o.modifiers.new('S', 'SOLIDIFY'); s_.thickness = th; s_.offset = off; return o
strip_mesh('CrewFloor', Z0, M_HFL, .2)
CZC = Z0 + 2.4                                   # cabin / corridor ceiling (below 2.4 m clear), storage loft above
cl = strip_mesh('CrewCeiling', CZC + .06, M_CEILP, .06)
try: CEIL.append(cl)
except Exception: pass
for k, x in enumerate(np.arange(5.0, 12.0, 1.4)): Box(f'CrewFloorSeam{k}', (x, 0, Z0 + .003), (.01, 2 * chw(x) - .2, .004), M_SEAM)
CW = .85                                         # corridor half width
RA = 7.56                                        # curved aft wall radius about the hall centre
# outer walls follow the hull outline (0.1 m)
for s in (1, -1):
    xs_ = [x for x in CXS if x >= arc_x(chw(x), RA) - .05]
    V = []; F = []
    for x in xs_: V += [(float(x), s * chw(x), Z0), (float(x), s * chw(x), CZC)]
    for i in range(len(xs_) - 1):
        a = 2 * i; F.append((a, a + 2, a + 3, a + 1) if s > 0 else (a, a + 1, a + 3, a + 2))
    o = mk(f'CrewOuterWall{s}', V, F, M_HW); so_ = o.modifiers.new('S', 'SOLIDIFY'); so_.thickness = .1; so_.offset = 0
# curved aft wall (joins the round hall) + flared vestibule fairings
a_d = math.degrees(math.asin(1.0 / RA))
for s in (1, -1):
    a_m = a_d
    while a_m < 80:
        p_ = pol(RA, a_m + .5, 0)
        if abs(p_[1]) > chw(p_[0]) - .02: break
        a_m += .5
    lo_, hi_ = (a_d, a_m) if s > 0 else (-a_m, -a_d)
    ann(f'CrewAftWall{s}', RA - .05, RA + .05, lo_, hi_, Z0, CZC, M_HW, step=1.5)
    ann(f'CrewFairing{s}', HR + .38, RA + .05, lo_, hi_, CZC, CZC + .5, M_HD, step=1.5)        # curved cornice where the block meets the blister
    # vestibule: flared jambs from the hall door (|y| 1.0) to the corridor (|y| CW)
    xa, xb = arc_x(1.0, HR), arc_x(1.0, RA) + .5
    L_ = math.hypot(xb - xa, 1.0 - CW); ang = math.degrees(math.atan2(-(1.0 - CW), xb - xa)) * s
    Box(f'CrewVestibule{s}', ((xa + xb) / 2, s * (1.0 + CW) / 2 + s * .06, Z0 + CZC / 2 - Z0 / 2), (L_, .1, CZC - Z0), M_HD, rot=(0, 0, ang))
    Box(f'CrewVestibuleLight{s}', ((xa + xb) / 2, s * (1.0 + CW) / 2, Z0 + .06), (L_, .02, .02), M_CYAN, rot=(0, 0, ang))
ann('CrewVestibuleHead', HR - .02, RA + .05, -a_d, a_d, CZC, CZC + .5, M_HD, step=1.0)
# corridor walls with cabin doors, partitions at x 8.3, forward bulkhead with the bridge door
XP = 8.3; XV = arc_x(1.0, RA) + .5
CAB = []
for s in (1, -1):
    for (x0, x1) in ((XV, XP - .06), (XP + .06, CX1 - .05)):
        dc = (x0 + x1) / 2                                  # door at the middle of the cabin
        for (a_, b_) in ((x0 - .06, dc - .45), (dc + .45, x1 + .06)):
            if b_ - a_ > .02: Box(f'CrewCorrWall{s}_{a_:.1f}', ((a_ + b_) / 2, s * (CW + .05), (Z0 + CZC) / 2), (b_ - a_, .1, CZC - Z0), M_HW)
        Box(f'CrewDoorHead{s}_{dc:.1f}', (dc, s * (CW + .05), (Z0 + 2.1 + CZC) / 2), (.9, .1, CZC - Z0 - 2.1), M_HW)
        Box(f'CrewDoorFrame{s}_{dc:.1f}', (dc, s * (CW + .0), Z0 + 2.12), (.96, .03, .04), M_CYAN)
        Box(f'CrewDoorLeaf{s}_{dc:.1f}', (dc + .62, s * (CW + .12), Z0 + 1.05), (.9, .04, 2.08), M_HD)   # slid open behind the wall
        CAB.append((s, x0, x1, dc))
    yo = chw(XP)
    Box(f'CrewPartition{s}', (XP, s * (CW + .1 + yo) / 2, (Z0 + CZC) / 2), (.1, yo - CW - .1, CZC - Z0), M_HW)
    yf = chw(CX1)
    Box(f'CrewFwdWall{s}', (CX1, s * (CW + yf) / 2, (Z0 + CZC) / 2), (.1, yf - CW, CZC - Z0), M_HW)
Box('CrewFwdHead', (CX1, 0, (Z0 + 2.3 + CZC) / 2), (.1, 2 * CW + .1, CZC - Z0 - 2.3), M_HW)
# steps down to the bridge deck
NBS = max(1, int(round((Z0 - ZB) / .2))); rs_ = (Z0 - ZB) / NBS
for k in range(NBS):
    zt = Z0 - (k + 1) * rs_; x0 = CX1 + .05 + k * .28
    Box(f'BridgeStep{k}', (x0 + .14, 0, (zt + ZB - .05) / 2), (.28, 2 * CW - .1, zt - ZB + .05), M_HFL)
    Box(f'BridgeStepNose{k}', (x0 + .02, 0, zt + .004), (.03, 2 * CW - .2, .008), M_AMBER)
# cabins: bed, mattress, pillow, desk, locker, screen, light (each under the 2.4 m ceiling)
for k, (s, x0, x1, dc) in enumerate(CAB):
    yo = min(chw(x0 + .3), chw(x1 - .3)) - .05; nm = f'Cabin{k}'
    bx = x1 - 1.1 if dc < (x0 + x1) / 2 else x0 + 1.1
    Box(f'{nm}Bed', (bx, s * (yo - .5), Z0 + .2), (2.0, .95, .4), M_CAB)
    Box(f'{nm}Mattress', (bx, s * (yo - .5), Z0 + .48), (1.94, .9, .16), M_MATT)
    Box(f'{nm}Pillow', (bx + (.75 if bx > (x0 + x1) / 2 else -.75), s * (yo - .5), Z0 + .61), (.35, .6, .1), M_LINEN)
    Box(f'{nm}Blanket', (bx - (.25 if bx > (x0 + x1) / 2 else -.25), s * (yo - .5), Z0 + .57), (1.3, .92, .04), M_BLANK)
    Box(f'{nm}Screen', (bx, s * (yo - .04), Z0 + 1.45), (1.0, .02, .56), M_VIEW)
    dx = x0 + .5 if bx > (x0 + x1) / 2 else x1 - .5
    Box(f'{nm}Desk', (dx, s * (yo - .32), Z0 + .74), (.8, .6, .04), M_WOOD)
    Box(f'{nm}DeskLeg', (dx, s * (yo - .1), Z0 + .37), (.7, .04, .74), M_STEEL)
    Box(f'{nm}Locker', (dx, s * (CW + .45), Z0 + 1.0), (.75, .55, 2.0), M_CAB)
    Box(f'{nm}LockerSeam', (dx, s * (CW + .17), Z0 + 1.0), (.01, .01, 1.9), M_SEAM)
    Area(f'{nm}Light', ((x0 + x1) / 2, s * (CW + yo) / 2, CZC - .08), 1.0, 45, (1, .9, .78))
for k, x in enumerate((5.6, 8.3, 11.0)): Area(f'CrewCorrL{k}', (x, 0, CZC - .08), .8, 55, (.85, .92, 1))
for s in (1, -1): Box(f'CrewCorrStrip{s}', ((XV + CX1) / 2, s * (CW - .02), Z0 + .05), (CX1 - XV, .02, .02), M_CYAN)
# storage loft above the cabins: open racks (posts, shelves, crates) under the hull roof, ladder + hatch from the corridor
_nr = 0
for s in (1, -1):
    for yr in (1.5, 2.9):
        for x in np.arange(5.4, 11.6, 1.35):
            if yr + .35 > chw(x): continue
            up_ = hdist((x, s * yr, CZC + .1), (0, 0, 1)); h = min(1.5, (up_ or 0) - .2)
            if h < .7: continue
            zb_ = CZC + .06; nm = f'LoftRack{s}_{yr}_{x:.1f}'
            for dx_ in (-.55, .55):
                for dy_ in (-.25, .25): Box(f'{nm}Post{dx_}{dy_}', (x + dx_, s * yr + dy_, zb_ + h / 2), (.04, .04, h), M_STEEL)
            for zz in (zb_ + .08, zb_ + h * .55):
                Box(f'{nm}Shelf{zz:.2f}', (x, s * yr, zz), (1.14, .54, .03), M_STEEL)
                Box(f'{nm}Crate{zz:.2f}', (x - .2, s * yr, zz + .17), (.5, .42, .32), M_CRATE)
            _nr += 1
Box('LoftLadderL', (11.5, .55, (Z0 + CZC) / 2 + .1), (.04, .04, CZC - Z0 + .2), M_STEEL); Box('LoftLadderR', (11.5, .25, (Z0 + CZC) / 2 + .1), (.04, .04, CZC - Z0 + .2), M_STEEL)
for k in range(8): Box(f'LoftLadderRung{k}', (11.5, .4, Z0 + .3 + k * .28), (.03, .3, .03), M_STEEL)
Box('LoftHatchFrame', (11.5, .4, CZC + .07), (.75, .7, .03), M_AMBER)
print('MODEL v17 crew block: cabins', len(CAB), 'loft racks', _nr)

# ---- B1. keel entrance bay: faired bulge under the hall (superellipse n=4), floor -4.2, open centre, racks, storage, ramp, stair
KR, KT, KB, KF = 7.05, -1.25, -4.55, -4.2
KD = KT - KB
RAMP_X0, RAMP_L, RAMP_A = -1.5, 2.9, 27.0
def ramp_hole(x, y): return RAMP_X0 - .02 < x < RAMP_X0 + RAMP_L * math.cos(math.radians(RAMP_A)) + .08 and abs(y) < .95
def t_keel(P_): return (rr_(P_) < KR - .05) & (P_[:, 2] < Z0 - .25) & (P_[:, 2] > KB - .3)
_nk = carve_faces(hull, lambda P_: (rr_(P_) < KR - .03) & (P_[:, 2] < KT - .05) & (P_[:, 2] > KB - .5))
for o in list(bpy.data.objects):
    if o.name.startswith(('Hull', 'Skylight', 'Dome')) or o == hull: continue
    if o.name.startswith('X'):
        if t_keel(np.array([list(o.matrix_world.translation)]))[0] or (rr_(np.array([list(o.matrix_world.translation)]))[0] < KR + .1 and o.matrix_world.translation.z < KT): _rm(o)
        continue
    if o.type == 'MESH':
        try: _nk += carve_faces(o, t_keel)
        except Exception as e: print('Error keelcarve', o.name, e)
print('MODEL v17 keel volume carved', _nk)
prof_k = [(KR * math.cos(t) ** .5, KT - KD * math.sin(t) ** .5) for t in np.linspace(0, math.pi / 2, 16)]
NA_ = 96; V = []; F = []
for j in range(NA_):
    a = 360 * j / NA_
    for (r_, z_) in prof_k: V.append(pol(r_, a, z_))
npk = len(prof_k)
for j in range(NA_):
    for i in range(npk - 1):
        a_, b_ = j * npk + i, ((j + 1) % NA_) * npk + i
        c_ = [(V[a_][0] + V[b_ + 1][0]) / 2, (V[a_][1] + V[b_ + 1][1]) / 2]
        if ramp_hole(c_[0], c_[1]) and V[a_][2] < KF - .05: continue
        F.append((a_, a_ + 1, b_ + 1, b_))
ks = mk('KeelShell', V, F, M_CHR, smooth=True); so_ = ks.modifiers.new('S', 'SOLIDIFY'); so_.thickness = .08; so_.offset = 1
Tor('KeelShellBand', (HC.x, HC.y, KT - .25), KR - .02, .04, M_ORNG, ms=96, ns=6)
fk = polar_grid('KeelFloor', 0.0, 5.4, lambda r: KF, M_HFL, skip=ramp_hole, dr=.3, da=3.0)
so_ = fk.modifiers.new('S', 'SOLIDIFY'); so_.thickness = .15; so_.offset = -1
for k, x in enumerate((RAMP_X0, RAMP_X0 + RAMP_L * math.cos(math.radians(RAMP_A)) + .06)): Box(f'RampWellEdge{k}', (x, 0, KF + .005), (.05, 1.9, .01), M_AMBER)
# ramp: hinged at the bay floor, 2.9 m at 27 deg, lands on the ground at -5.5
hx = RAMP_X0; ca_, sa_ = math.cos(math.radians(RAMP_A)), math.sin(math.radians(RAMP_A))
Box('BellyRamp', (hx + ca_ * RAMP_L / 2, 0, KF - .05 - sa_ * RAMP_L / 2), (RAMP_L, 1.8, .1), M_HFL, rot=(0, RAMP_A, 0))
for k in range(9): Box(f'BellyRampTread{k}', (hx + ca_ * (.25 + k * .3), 0, KF + .005 - sa_ * (.25 + k * .3)), (.05, 1.6, .02), M_HD, rot=(0, RAMP_A, 0))
for s in (1, -1):
    Box(f'BellyRampRail{s}', (hx + ca_ * RAMP_L / 2, s * .86, KF + .1 - sa_ * RAMP_L / 2), (RAMP_L, .05, .22), M_STEEL, rot=(0, RAMP_A, 0))
    Box(f'BellyRampLight{s}', (hx + ca_ * RAMP_L / 2, s * .8, KF + .02 - sa_ * RAMP_L / 2), (RAMP_L - .1, .02, .02), M_CYAN, rot=(0, RAMP_A, 0))
    Cyl(f'BellyRampPiston{s}', (hx + .5, s * .95, KF - .35), .05, 1.0, M_STEEL, rot=(0, 90 - 35, 0), v=12)
print('MODEL v17 ramp lower end z', round(KF - sa_ * RAMP_L, 2))
# straight stair up to the off-centre hatch (16 risers, 0.2 m)
HX0, HX1, HHW = -7.2, -4.6, .65
SX0_ = -8.2; NSR = 16; srise = (Z0 - KF) / NSR; srun = (HX1 - SX0_) / NSR
for k in range(NSR):
    zt = KF + (k + 1) * srise; x0 = SX0_ + k * srun
    Box(f'KeelStairTread{k:02d}', (x0 + srun / 2, 0, zt - .025), (srun + .02, 1.1, .05), M_HFL)
    Box(f'KeelStairNose{k:02d}', (x0 + .02, 0, zt + .003), (.03, 1.0, .006), M_CYAN)
sl = math.hypot(HX1 - SX0_, Z0 - KF); sang = math.degrees(math.atan2(Z0 - KF, HX1 - SX0_))
for s in (1, -1):
    Box(f'KeelStairStringer{s}', ((SX0_ + HX1) / 2, s * .58, (KF + Z0) / 2 - .1), (sl, .05, .3), M_STEEL, rot=(0, -sang, 0))
    Box(f'KeelStairRail{s}', ((SX0_ + HX1) / 2, s * .6, (KF + Z0) / 2 + .85), (sl, .04, .04), M_HD, rot=(0, -sang, 0))
    for k in range(5):
        xx = SX0_ + .3 + k * (HX1 - SX0_ - .6) / 4; zz = KF + (xx - SX0_) / (HX1 - SX0_) * (Z0 - KF)
        Box(f'KeelStairPost{s}{k}', (xx, s * .6, zz + .45), (.03, .03, .9), M_STEEL)
# two-leaf armoured sliding hatch (leaves slide sideways into the floor slab: closed 1-150, open 175+), emblem, glowing seam
for s in (1, -1):
    h = piv(f'Anim_HatchLeaf{s}', ((HX0 + HX1) / 2, s * HHW / 2, Z0 - .05))
    att(Box(f'HatchLeaf{s}', ((HX0 + HX1) / 2, s * HHW / 2, Z0 - .05), (HX1 - HX0 - .02, HHW - .01, .09), M_STEEL), h)
    for k in range(4): att(Box(f'HatchArmour{s}{k}', (HX0 + .35 + k * .63, s * HHW / 2, Z0 - .003), (.08, HHW - .12, .012), M_HD), h)
    att(Box(f'HatchSeam{s}', ((HX0 + HX1) / 2, s * .012, Z0 - .004), (HX1 - HX0 - .06, .02, .01), M_CYAN), h)
    att(Cyl(f'HatchEmblem{s}', ((HX0 + HX1) / 2, s * .2, Z0 - .002), .17, .01, M_GOLD, v=32), h)
    h.location.y = s * HHW / 2; h.keyframe_insert('location', frame=150); h.location.y = s * (HHW / 2 + HHW); h.keyframe_insert('location', frame=175)
for (x_, sy_) in ((HX0, None), (HX1, None)): Box(f'HatchFrameX{x_}', (x_, 0, Z0 + .003), (.06, 2 * HHW + .1, .008), M_AMBER)
for s in (1, -1): Box(f'HatchFrameY{s}', ((HX0 + HX1) / 2, s * (HHW + .02), Z0 + .003), (HX1 - HX0, .04, .008), M_AMBER)
for s in (1, -1): Box(f'HatchWell{s}', ((HX0 + HX1) / 2, s * (HHW + .02), Z0 - .3), (HX1 - HX0, .04, .6), M_HD)
# artillery racks + loader (port side), storage (starboard), lights, lift pillar under the holo table
M_MSL = pbsdf('Ordnance', (.55, .57, .6), .7, .3)
for k, a in enumerate((60, 80, 100, 120)):
    c_ = pol(4.95, a, 0); t_ = (-math.sin(math.radians(a)), math.cos(math.radians(a)))
    for e in (-1, 1):
        q_ = (c_[0] + t_[0] * e * .9, c_[1] + t_[1] * e * .9)
        Box(f'ArtRackUpright{k}{e}', (q_[0], q_[1], KF + 1.0), (.12, .12, 2.0), M_STEEL, rot=(0, 0, a))
    for j in range(3):
        zz = KF + .45 + j * .6
        Box(f'ArtRackArm{k}{j}', (c_[0], c_[1], zz - .2), (.5, 1.9, .06), M_HD, rot=(0, 0, a))
        Cyl(f'ArtShell{k}{j}', (c_[0], c_[1], zz), .17, 2.0, M_MSL, rot=(90, 0, a), v=20)
        for e in (-1, 1):
            q_ = (c_[0] + t_[0] * e * 1.05, c_[1] + t_[1] * e * 1.05)
            if e > 0: bpy.ops.mesh.primitive_cone_add(vertices=20, radius1=.17, depth=.35, location=(q_[0], q_[1], zz), rotation=(math.radians(-90), 0, math.radians(a))); o = bpy.context.active_object; o.name = f'ArtShellTip{k}{j}'; o.data.materials.append(M_ORNG)
    Box(f'ArtRackLabel{k}', (pol(4.62, a, 0)[0], pol(4.62, a, 0)[1], KF + 2.05), (.02, .6, .12), M_SCR2, rot=(0, 0, a))
# overhead loader: curved rail at r 4.2 + gantry trolley with a claw and a cradle cart on the floor
ann('LoaderRail', 4.15, 4.3, 50, 130, -1.62, -1.5, M_STEEL, step=2)
lc = pol(4.22, 90, 0)
Box('LoaderTrolley', (lc[0], lc[1], -1.7), (.5, .4, .2), M_HD); Cyl('LoaderMast', (lc[0], lc[1], -2.35), .05, 1.1, M_STEEL, v=12)
Box('LoaderClaw', (lc[0], lc[1], -2.95), (.25, .6, .12), M_ORNG)
cc = pol(3.4, 92, 0)
Box('LoaderCart', (cc[0], cc[1], KF + .35), (.9, 1.4, .1), M_STEEL); Cyl('LoaderCartShell', (cc[0], cc[1], KF + .6), .17, 2.0, M_MSL, rot=(90, 0, 0), v=20)
for e in (-1, 1):
    for f_ in (-1, 1): Cyl(f'LoaderCartWheel{e}{f_}', (cc[0] + e * .35, cc[1] + f_ * .55, KF + .12), .12, .08, M_HD, rot=(0, 90, 0), v=16)
for k, a in enumerate(range(236, 306, 9)):
    Box(f'BayLocker{k}', pol(5.05, a, KF + 1.0), (.55, .62, 2.0), M_CAB, rot=(0, 0, a))
    Box(f'BayLockerSeam{k}', pol(4.77, a, KF + 1.0), (.01, .01, 1.9), M_SEAM, rot=(0, 0, a))
for k, (a, n) in enumerate(((210, 3), (222, 2), (314, 3), (326, 1))):
    for j in range(n): Box(f'BayCrate{k}{j}', pol(4.6, a, KF + .3 + j * .6), (.6, .6, .6), M_CRATE, rot=(0, 0, a + 7 * j))
Cyl('HoloLiftShaft', (HC.x, HC.y, (KF - Z0) / 2 + Z0 - .1), .8, Z0 - KF - .2, M_HD, v=48)
Tor('HoloLiftRing', (HC.x, HC.y, KF + .05), .82, .03, M_CYAN, ms=48, ns=6)
for k, (r_, a) in enumerate(((2.5, 90), (2.5, 270), (2.5, 0), (2.5, 180), (4.3, 45), (4.3, 315))): Area(f'BayLight{k}', pol(r_, a, -1.5), 1.0, 70, (.85, .92, 1))
Area('RampLight', (RAMP_X0 + 1.0, 0, -1.6), 1.2, 90, (1, .85, .65))

# ---- B2. hall: holo table flush in the centre (raised copy hidden), curved sofas along the edge
def holo_table(nm, dz):
    parts = [Cyl(f'{nm}Body', (HC.x, HC.y, Z0 - .45 + dz), .73, .9, M_HD, v=48),
             Cyl(f'{nm}Top', (HC.x, HC.y, Z0 - .01 + dz), .7, .02, M_HOLO, v=48),
             Tor(f'{nm}Rim', (HC.x, HC.y, Z0 + dz), .72, .025, M_CYAN, ms=48, ns=6)]
    return parts
for o in holo_table('HoloTable', 0.0): pass
RAISED = holo_table('HoloTable_raised', .95)
gl_ = bpy.ops.mesh.primitive_uv_sphere_add(radius=.38, location=(HC.x, HC.y, Z0 + .95 + .55)); hgl = bpy.context.active_object; hgl.name = 'HoloTable_raisedGlobe'
hgl.data.materials.append(M_HOLO); w_ = hgl.modifiers.new('W', 'WIREFRAME'); w_.thickness = .006; RAISED.append(hgl)
for o in RAISED: o.hide_render = True
for k, (a0, a1) in enumerate(((108, 150), (210, 252), (64, 82), (278, 296))):
    ann(f'SofaBase{k}', 6.2, 6.9, a0, a1, Z0, Z0 + .3, M_HD, step=2)
    ann(f'SofaSeat{k}', 6.2, 6.85, a0 + .3, a1 - .3, Z0 + .3, Z0 + .46, M_FAB, step=2)
    ann(f'SofaBack{k}', 6.7, 6.92, a0 + .3, a1 - .3, Z0 + .46, Z0 + 1.0, M_FAB, step=2)
    for a in (a0, a1): ann(f'SofaArm{k}_{a}', 6.2, 6.92, a - .8 if a == a0 else a, a if a == a0 else a + .8, Z0, Z0 + .62, M_HD, step=.8)

# ---- A3. exterior X* plates follow the hull (parented)
_npl = 0
for o in bpy.data.objects:
    if o.name.startswith(('XPlate', 'XVent', 'XHatch', 'XSide')):
        mw0 = o.matrix_world.copy(); o.parent = hull; o.matrix_parent_inverse = hull.matrix_world.inverted(); o.matrix_world = mw0; _npl += 1
print('MODEL v17 X plates parented to Hull', _npl)

# ---- A4. outside-hull check: interior objects (centre inside the shell) must not poke through hull / blister / keel / sponsons
SHELL = ['Hull', 'HallBlister', 'HallBlisterBelly', 'KeelShell', 'SkylightGlass'] + [o.name for o in bpy.data.objects if o.name.endswith('Sponson')]
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
SB = bvh_of(SHELL)
DIRS = [Vector(d) for d in ((0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
def outside_pts(P_):
    out = np.zeros(len(P_), bool)
    for i, p in enumerate(P_):
        miss = 0
        for d in DIRS:
            if SB.ray_cast(Vector(p), d, 40.0)[0] is None: miss += 1
        out[i] = miss >= 2
    return out
EXT_PFX = ('Hull', 'X', 'Nav', 'Strobe', 'Thruster', 'Exhaust', 'Plume', 'Winglet', 'Strake', 'Keel', 'BellyRamp', 'Pad', 'Skylight', 'HoloTable_raised', 'NozL')
_off = []; _fix = 0
for o in list(bpy.data.objects):
    if o.type != 'MESH' or o.name.startswith(EXT_PFX) or o.name in SHELL or o.name.endswith(('Sponson', 'SponsonCut', 'SponsonWinCut', 'SponsonStripe')): continue
    try:
        me_ = o.data; n_ = len(me_.vertices)
        if n_ == 0: continue
        c_ = np.empty(n_ * 3, np.float32); me_.vertices.foreach_get('co', c_); c_ = c_.reshape(-1, 3)
        Mw = np.array(o.matrix_world); P_ = c_ @ Mw[:3, :3].T + Mw[:3, 3]
        cen = P_.mean(0)
        if outside_pts([cen])[0]: continue                      # exterior part
        sub = P_[:: max(1, n_ // 120)]
        out = outside_pts(sub)
        if not out.any(): continue
        dim = (P_.max(0) - P_.min(0)).max()
        if dim < 1.5 and out.mean() <= .5:
            moved = False
            for step in range(1, 9):
                dy = -math.copysign(.05 * step, cen[1]) if abs(cen[1]) > .3 else 0.0
                dz = .05 * step if (sub[out][:, 2].mean() < cen[2]) else -.05 * step
                if not outside_pts(sub + np.array([0, dy, dz * (0 if dy else 1)])).any():
                    o.location.y += dy; o.location.z += dz * (0 if dy else 1); moved = True; break
            if moved: _fix += 1; continue
        _off.append((o.name, round(float(out.mean()), 2), round(float(dim), 2)))
    except Exception as e: print('Error hullcheck', o.name, e)
print('MODEL v17 outside-hull: auto-inset', _fix, 'offenders', len(_off))
for t in sorted(_off, key=lambda t: -t[1])[:60]: print('MODEL v17 OFFENDER', t)
print('MODEL v17 pass done')

# ------------------------------------------------------------------ world, camera, render
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True; nt = w.node_tree; bg = nt.nodes['Background']
if os.path.exists(hdr):
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(hdr); nt.links.new(env.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = .9
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); col.objects.link(sun); sun.data.energy = 3; sun.data.color = (1, .87, .72)
sun.rotation_euler = (math.radians(50), 0, math.radians(135))
gp = bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -5.5))   # v17: ground at -5.5 (ramp foot); ground = bpy.context.active_object; ground.name = 'Pad'
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
def hide_lights():
    for o in bpy.data.objects:
        if o.type == 'LIGHT':
            try: o.visible_camera = False
            except Exception as e: print('Error vis', e)
hide_lights()
def clear_cam(name, loc, tgt):
    # v15: never render from inside a solid: if 5+ of 6 axis rays hit a back face, step towards the target
    dg = bpy.context.evaluated_depsgraph_get(); L = Vector(loc); T = Vector(tgt)
    for it in range(15):
        bad = 0
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            hit, p_, n_, *_ = sc.ray_cast(dg, L, Vector(d))
            if hit and (n_.dot(Vector(d)) > 0 or (p_ - L).length < .08): bad += 1
        if bad < 5:
            if it: print('MODEL camcheck', name, 'moved', it * .35, 'm')
            return tuple(L)
        L = L + (T - L).normalized() * .35
    print('Error camcheck', name, 'still inside'); return tuple(L)
def shot(name, frame, loc, tgt, lens=28, cut=0, res=(1600, 900), pad=True):
    sc.frame_set(frame); set_cut2(cut); ground.hide_render = not pad
    if not cut: loc = clear_cam(name, loc, tgt)
    look(loc, tgt, lens)
    for o in CEIL: o.hide_render = bool(cut)
    r.resolution_x, r.resolution_y = res; r.filepath = os.path.join(OUT, name + '.png'); bpy.ops.render.render(write_still=True); print('RENDER', name)

def export_glbs():
    for o in bpy.context.selected_objects: o.select_set(False)
    curves = [o for o in bpy.data.objects if o.type == 'CURVE']
    for o in curves: o.select_set(True)
    if curves:
        bpy.context.view_layer.objects.active = curves[0]; bpy.ops.object.convert(target='MESH')
    lite = hull.copy(); lite.data = hull.data.copy(); lite.name = 'HullLite'; col.objects.link(lite)
    for o in [o for o in bpy.data.objects if o.parent == hull]:   # v17: exterior plates ride on the exported hull
        mw0 = o.matrix_world.copy(); o.parent = lite; o.matrix_parent_inverse = lite.matrix_world.inverted(); o.matrix_world = mw0
    dm = lite.modifiers.new('D', 'DECIMATE'); dm.ratio = .2
    for i, m in enumerate(lite.data.materials):
        m2 = m.copy(); nt = m2.node_tree; p = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]; o_ = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
        nt.links.new(p.outputs[0], o_.inputs['Surface']); lite.data.materials[i] = m2
    nt = M_LIN.node_tree; nt.links.new(nt.nodes['Principled BSDF'].outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    hide = {'Hull', 'InnerSkin', 'Pad', 'Cam', 'Sun'} | set(SIDE_CUTTERS)
    inner = [o for o in bpy.data.objects if o.type == 'MESH' and o.name not in hide and o.name != 'HullLite' and not o.name.startswith(('Thruster', 'Exhaust', 'Plume', 'g', 'RCS', 'Dish', 'Nav', 'Strobe', 'Gear', 'G0', 'G1', 'G2'))]
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in inner: o.select_set(True)
    pass
    for o in bpy.data.objects:
        if o.type in ('MESH', 'EMPTY') and o.name not in hide: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'spacecraft_v17.glb'), export_format='GLB', use_selection=True, export_apply=True, export_animations=True, export_lights=False)
    print('MODEL glb', os.path.getsize(os.path.join(OUT, 'spacecraft_v17.glb')))

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
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'spacecraft_v17.blend'), compress=True)
        print('MODEL blend', os.path.getsize(os.path.join(OUT, 'spacecraft_v17.blend')))
    except Exception as e: print('Error blend', e)


# ------------------------------------------------------------------ v10 HOUSE-TOUR walk-through (shot list, cuts between rooms)
sc.frame_set(120); bpy.context.view_layer.update()
RX0, RZ0, RX1, RZ1 = RAMP_X0 + RAMP_L * math.cos(math.radians(RAMP_A)), -5.44, RAMP_X0, KF   # v17 belly ramp
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

def raised(on):
    for o in bpy.data.objects:
        if o.name.startswith('HoloTable_raised'): o.hide_render = not on
        elif o.name.startswith('HoloTable'): o.hide_render = on
def topdown(name, z=1.38, res=(1600, 1000)):
    hid = [o for o in bpy.data.objects if (o.name in ('Hull', 'Pad') or o.name.startswith(('X', 'HallDome', 'Skylight', 'HallRib', 'DomeRing'))) and not o.hide_render]
    for o in hid: o.hide_render = True
    for o in CEIL: o.hide_render = True
    sc.frame_set(200); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 62; cam.data.clip_start = .01; cam.data.clip_end = 40
    cam.location = (0, 0, z); cam.rotation_euler = (0, 0, 0)
    r.resolution_x, r.resolution_y = res; r.filepath = os.path.join(OUT, name + '.png'); bpy.ops.render.render(write_still=True); print('RENDER', name)
    cam.data.type = 'PERSP'
    for o in hid: o.hide_render = False
    for o in CEIL: o.hide_render = False
if DRY:
    sc.cycles.samples = SPP
    shot('x1_exterior_below', 120, (30, -34, -10), (0, 0, -2.5), 30, pad=False)
    shot('b2_ramp_exterior', 200, (9.5, -6.5, -4.6), (-2.5, 0, -3.6), 22)
    shot('b1_entrance_bay', 200, (-0.6, 3.9, -2.3), (-6.6, -.6, -3.0), 16)
    shot('h1_hall_empty', 120, (2.4, -1.8, Z0 + 1.7), (-7.5, .8, Z0 + .5), 18)
    raised(True); shot('h2_hall_table_raised', 120, (1.2, 2.9, Z0 + 2.1), (HC.x, 0, Z0 + .9), 20); raised(False)
    shot('c1_corridor_from_hall', 160, (HC.x + HR - 2.6, 0, Z0 + 1.65), (CX1 + 1, 0, Z0 + 1.2), 18)
    shot('c2_cabin', 160, (7.9, 1.15, Z0 + 1.75), (5.4, 3.3, Z0 + .5), 16)
    shot('h5_reactor_window', 240, (-7.6, 1.9, Z0 + 1.9), (EX, 1.0, 1.7), 24)
    shot('r1_hybrid_core', 240, (XSB + .2, -.6, ZA + 2.1), (EX, 0, zc_ - .1), 18)
    topdown('t1_topdown_section')
    save_blend()
    try: export_glbs()
    except Exception as e: print('Error glb', e)
else:
    r.image_settings.file_format = 'JPEG'; r.image_settings.quality = 92; r.use_persistent_data = True
    for f in range(S0, min(S1, NTOUR) + 1):
        tour_frame(f, os.path.join(OUT, f'f_{f:04d}.jpg'))
print('DONE')
