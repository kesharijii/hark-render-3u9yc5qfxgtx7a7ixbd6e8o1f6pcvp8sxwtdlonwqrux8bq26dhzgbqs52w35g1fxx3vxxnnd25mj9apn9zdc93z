# ================================================================== v18 EXTERIOR PASS (user spec 2026-11-06 18:38): EXTERIOR ONLY
#   materials (brushed titanium skin, ceramic belly tiles, carbon-carbon nose/leading edges, gold foil engine surrounds and
#   reactor vents, coated-silver radiators, dark-titanium nozzles with glow rings, tinted canopy), paint (small orange ID marks,
#   thin teal light lines, hazard patches + radiation symbols on the aft reactor access panels), wear (edge scratches, soot,
#   crevice grime, heat staining) and shape (aft fairing taper, belly chine, wing-root fillets, canted rudders, intakes).
#   The interior is not edited: hull deformation is clamped above every non-hull object, fillets only push the skin OUTWARD,
#   and back faces of the hull keep the v17 look (anything seen from inside stays as approved).
#   Every sub-step is timed and wrapped; an optional step is skipped once the pass budget is spent.
print('TIMING v18 start', round(_tm0.time() - _TS))
V18_T0 = _tm0.time(); V18_BUDGET = 900
def v18_left(): return V18_BUDGET - (_tm0.time() - V18_T0)
def v18_step(name, fn, optional=True):
    if optional and v18_left() < 0: print('MODEL v18 skip', name, '(budget)'); return None
    t = _tm0.time()
    try: r_ = fn()
    except Exception:
        import traceback; print('Error v18', name); traceback.print_exc(); r_ = None
    print('TIMING v18', name, round(_tm0.time() - t, 1), 's at', round(_tm0.time() - _TS)); return r_

def hexlin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((v / 12.92) if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c)
C_TI, C_CER, C_CC, C_GOLD = hexlin('8C8F94'), hexlin('1B1C1F'), hexlin('26282B'), hexlin('C9A24A')
C_RAD, C_NOZ, C_CAN = hexlin('D6D9DD'), hexlin('5D6065'), hexlin('1E6FB8')
C_ORN, C_TEAL = hexlin('F26B1D'), hexlin('19B5C8')

# ---------------------------------------------------------------- hull arrays + edge graph
def hull_arrays():
    me_ = hull.data; n_ = len(me_.vertices)
    c_ = np.empty(n_ * 3, np.float32); me_.vertices.foreach_get('co', c_); c_ = c_.reshape(-1, 3)
    M_ = np.array(hull.matrix_world); W_ = c_ @ M_[:3, :3].T + M_[:3, 3]
    nr = np.empty(n_ * 3, np.float32); me_.vertex_normals.foreach_get('vector', nr); nr = nr.reshape(-1, 3)
    R_ = M_[:3, :3] / np.linalg.norm(M_[:3, 0]); N_ = nr @ R_.T; N_ /= np.linalg.norm(N_, axis=1, keepdims=True) + 1e-9
    return c_, M_, W_, N_
def set_hull_world(W_, M_):
    loc = (W_ - M_[:3, 3]) @ np.linalg.inv(M_[:3, :3]).T
    hull.data.vertices.foreach_set('co', loc.astype(np.float32).ravel()); hull.data.update()
HE = np.empty(len(hull.data.edges) * 2, np.int32); hull.data.edges.foreach_get('vertices', HE); HE = HE.reshape(-1, 2)
HN = len(hull.data.vertices); HDEG = np.maximum(np.bincount(HE.ravel(), minlength=HN), 1).astype(np.float64)
def nb_avg(F):
    F = np.asarray(F, np.float64)
    if F.ndim == 1:
        return (np.bincount(HE[:, 0], F[HE[:, 1]], HN) + np.bincount(HE[:, 1], F[HE[:, 0]], HN)) / HDEG
    return np.stack([nb_avg(F[:, k]) for k in range(F.shape[1])], 1)
# boundary vertices (edges with one face) never move
_le = np.empty(len(hull.data.loops), np.int32); hull.data.loops.foreach_get('edge_index', _le)
_ec = np.bincount(_le, minlength=len(HE)); HBND = np.zeros(HN, bool); HBND[HE[_ec == 1].ravel()] = True
print('MODEL v18 hull verts', HN, 'edges', len(HE), 'boundary verts', int(HBND.sum()))
hco0, HM, HW0, HN0 = hull_arrays()
HXMIN, HXMAX, HYMAX = float(HW0[:, 0].min()), float(HW0[:, 0].max()), float(np.abs(HW0[:, 1]).max())
HCX, HCY = float(HC.x), float(HC.y)
HDISP = np.zeros((HN, 3))     # accumulated hull displacement (exterior parts sitting on the skin follow it)

# ---------------------------------------------------------------- keep-out height map: highest point of every non-hull object
def keepout_grid():
    gx0, gy0, cs = HXMIN - 2, -HYMAX - 2, .5
    nx_, ny_ = int((HXMAX - HXMIN + 4) / cs) + 1, int((2 * HYMAX + 4) / cs) + 1
    KZ = np.full((nx_, ny_), -1e9)
    for o in bpy.data.objects:
        if o.type != 'MESH' or o == hull or o.name.startswith(('X', 'Pad', 'Plume', 'HullLite')) or o.hide_render: continue
        nv_ = len(o.data.vertices)
        if nv_ == 0: continue
        c_ = np.empty(nv_ * 3, np.float32); o.data.vertices.foreach_get('co', c_); c_ = c_.reshape(-1, 3)[:: max(1, nv_ // 40000)]
        M_ = np.array(o.matrix_world); P_ = c_ @ M_[:3, :3].T + M_[:3, 3]
        ix = np.clip(((P_[:, 0] - gx0) / cs).astype(int), 0, nx_ - 1); iy = np.clip(((P_[:, 1] - gy0) / cs).astype(int), 0, ny_ - 1)
        np.maximum.at(KZ, (ix, iy), P_[:, 2])
    K2 = KZ.copy()   # dilate 2 cells (1 m)
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            K2 = np.maximum(K2, np.roll(np.roll(KZ, dx, 0), dy, 1))
    return K2, gx0, gy0, cs

# ---------------------------------------------------------------- 1. aft fairing taper (~8 deg over ~18 m, clamped)
def do_taper():
    global HDISP
    K2, gx0, gy0, cs = keepout_grid()
    c_, M_, W_, N_ = hull_arrays(); X, Y, Z = W_[:, 0], W_[:, 1], W_[:, 2]
    nx_, ny_ = K2.shape
    ix = np.clip(((X - gx0) / cs).astype(int), 0, nx_ - 1); iy = np.clip(((Y - gy0) / cs).astype(int), 0, ny_ - 1)
    HB = np.full(K2.shape, 1e9); np.minimum.at(HB, (ix, iy), Z)          # hull bottom per cell: never fold the skin through
    HB[HB > 1e8] = -1e9
    FL = np.maximum(K2 + .35, HB + .4)
    FLc = np.maximum.accumulate(FL, axis=0)                               # monotonic from the tail forward: no valleys
    XT0 = -11.4; sel0 = np.abs(Y) < 1.0
    zc = Z[sel0 & (np.abs(X - XT0) < .5)]
    z0 = float(zc.max()) if len(zc) else 4.9
    line = z0 - math.tan(math.radians(8)) * np.maximum(XT0 - X, 0)
    target = np.maximum(line, FLc[ix, iy])
    wup = _ss(.05, .45, N_[:, 2]); wy = _ss(8.0, 6.0, np.abs(Y)); wx = _ss(XT0, XT0 - 1.5, X)
    whall = _ss(9.0, 10.0, np.hypot(X - HCX, Y - HCY))
    dz = np.minimum(0, target - Z) * wup * wy * wx * whall
    dz[HBND] = 0
    for _ in range(12): dz = .5 * dz + .5 * nb_avg(dz); dz[HBND] = 0
    dz = np.maximum(dz, np.minimum(0, FLc[ix, iy] - Z)); dz = np.minimum(dz, 0)
    W_[:, 2] += dz; set_hull_world(W_, M_); HDISP[:, 2] += dz
    print('MODEL v18 taper z0', round(z0, 2), 'moved', int((dz < -.01).sum()), 'max drop', round(float(-dz.min()), 2))
v18_step('taper', do_taper)

# ---------------------------------------------------------------- 2. wing-root fillets: concave creases pushed OUTWARD only
def do_fillets():
    global HDISP
    c_, M_, W_, N_ = hull_arrays(); X, Y, Z = W_[:, 0], np.abs(W_[:, 1]), W_[:, 2]
    A = nb_avg(W_); el = np.sqrt(((W_[HE[:, 0]] - W_[HE[:, 1]]) ** 2).sum(1))
    ml = (np.bincount(HE[:, 0], el, HN) + np.bincount(HE[:, 1], el, HN)) / HDEG + 1e-6
    cv = ((A - W_) * N_).sum(1) / ml                                          # >0 concave
    for _ in range(6): cv = .5 * cv + .5 * nb_avg(cv)
    reg = (Y > 2.5) & (Y < 9.5) & (X > -24) & (X < 22) & (Z > -2.6)
    reg &= np.hypot(X - HCX, W_[:, 1] - HCY) > 7.8
    reg &= ~((X > 12) & (Y < 4.4)) & ~((X > -24) & (X < -12) & (Y < 5.8))
    mask = _ss(.03, .14, cv) * reg
    for _ in range(8): mask = np.maximum(mask, .7 * nb_avg(mask))
    mask[HBND] = 0
    P0 = W_.copy(); t0 = _tm0.time(); it = 0
    for it in range(70):
        if _tm0.time() - t0 > 120: break
        d = nb_avg(W_) - W_; dn = np.maximum((d * N_).sum(1), 0) * mask * .6
        W_ += N_ * dn[:, None]
        off = ((W_ - P0) * N_).sum(1); over = off > .3
        if over.any(): W_[over] = P0[over] + N_[over] * .3
    D = W_ - P0; set_hull_world(W_, M_); HDISP += D
    print('MODEL v18 fillets iters', it + 1, 'verts in mask', int((mask > .05).sum()), 'moved >1cm', int((np.linalg.norm(D, axis=1) > .01).sum()), 'max', round(float(np.linalg.norm(D, axis=1).max()), 3))
v18_step('fillets', do_fillets)

# ---------------------------------------------------------------- 3. parts that sit on the skin follow it
def follow_skin():
    from mathutils.kdtree import KDTree
    mv = np.linalg.norm(HDISP, axis=1) > .005
    if not mv.any(): print('MODEL v18 follow: nothing moved'); return
    idx = np.where(np.linalg.norm(HDISP, axis=1) > 1e-4)[0]
    _, _, W_, _ = hull_arrays()
    kd = KDTree(len(idx))
    for k, i in enumerate(idx): kd.insert(W_[i] - HDISP[i], k)
    kd.balance(); n_ = 0
    for o in bpy.data.objects:
        if not (o.name.startswith(('X', 'Nav', 'Strobe', 'Strake')) and o.type in ('MESH', 'LIGHT')): continue
        p = o.matrix_world.translation; co, k, dist = kd.find(p)
        if co is None or dist > .9: continue
        d = Vector(HDISP[idx[k]])
        if d.length < .003: continue
        mw_ = o.matrix_world.copy(); mw_.translation = p + d; o.matrix_world = mw_; n_ += 1
    print('MODEL v18 follow-skin moved parts', n_)
v18_step('follow', follow_skin)
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 4. per-vertex zones, paint and wear (baked into 'Livery' for the GLB)
TH_ = []
for i in range(3):
    t_ = bpy.data.objects.get(f'Exhaust{i}')
    if t_: c = t_.matrix_world.translation; TH_.append((float(c.y), float(c.z), float(t_.dimensions.y / 2 / .74)))
def zones(W_, N_, convex=None, grime=None, is_hull=True):
    X, Ya, Z = W_[:, 0], np.abs(W_[:, 1]), W_[:, 2]; up = N_[:, 2]; n_ = len(W_)
    yb = np.round(W_[:, 1] / .5).astype(int) - LEAD_Y0; yb = np.clip(yb, 0, len(LEAD) - 1); dlead = LEAD[yb] - X
    cer = _ss(-.25, -.55, up)
    nose = _ss(HXMAX - 4.5, HXMAX - 2.0, X)
    le = (Ya > 4.5) * _ss(.9, .5, dlead)
    gold = np.zeros(n_); soot = np.zeros(n_)
    for (yc, zc_, r_) in TH_:
        d = np.hypot(W_[:, 1] - yc, Z - zc_)
        gold = np.maximum(gold, _ss(HXMIN + 2.8, HXMIN + 2.0, X) * _ss(r_ + 1.15, r_ + .85, d) * _ss(r_ * .6, r_ * .85, d))
        soot = np.maximum(soot, _ss(HXMIN + 4.0, HXMIN + .4, X) * _ss(r_ + 2.6, r_ + .8, d))
    cc = np.maximum(nose, le) * (1 - gold)
    cer = cer * (1 - cc) * (1 - gold)
    paint = np.zeros(n_); glow = np.zeros(n_)
    if is_hull:
        upper = up > .25
        paint[(Ya > HYMAX - .9)] = 1                                                     # wingtip tips
        paint[upper & (Ya < .28) & (X > 12.5) & (X < 17.0)] = 1                           # short spine stripe near the nose
        # v18-2: the vertex-painted wing edge line read as blotchy dashes; teal lines live on the chines + sponson edges instead
    skin = np.clip(1 - cer - cc - gold, 0, 1)
    heat = np.clip((Ya > 4.5) * _ss(2.4, .9, dlead) + _ss(HXMAX - 6.5, HXMAX - 4.5, X) * (1 - nose), 0, 1) * (1 - gold) * (1 - cer * .5)
    seam = (np.abs(((X + .3) / 2.4) % 1 - .5) > .485) | (np.abs(((W_[:, 1] + .9) / 3.0) % 1 - .5) > .488)
    cx_, cy_ = np.floor((X + .3) / 2.4), np.floor((W_[:, 1] + .9) / 3.0)
    h = np.sin(cx_ * 12.9898 + cy_ * 78.233) * 43758.5453; h = h - np.floor(h); tone = .92 + .16 * h
    convex = np.zeros(n_) if convex is None else convex; grime = np.zeros(n_) if grime is None else grime
    col = (np.array(C_TI) * (tone * skin)[:, None] + np.array(C_CER) * cer[:, None] + np.array(C_CC) * cc[:, None] + np.array(C_GOLD) * gold[:, None])
    col = col * (1 - paint[:, None]) + np.array(C_ORN) * paint[:, None]
    col = col * (1 - glow[:, None]) + np.array(C_TEAL) * glow[:, None]
    tint = np.array([.10, .11, .24])[None, :] * (1 - _ss(.7, 2.2, dlead))[:, None] + np.array([.42, .30, .12])[None, :] * _ss(.7, 2.2, dlead)[:, None]
    hh = (heat * .45 * (1 - paint) * (1 - glow))[:, None]; col = col * (1 - hh) + tint * hh
    col = col * (1 - .45 * seam)[:, None] * (1 - .35 * grime)[:, None]
    s_ = (soot * .7)[:, None]; col = col * (1 - s_) + .02 * s_
    col = col + (.06 * convex * skin * (1 - paint))[:, None]
    gw = np.clip(grime + .6 * seam, 0, 1)
    return (np.clip(col, 0, 1), np.c_[cer, cc, gold, paint], np.c_[convex, soot, heat, gw], glow)
_, _, HW1, HN1 = hull_arrays()
_yb = np.round(HW1[:, 1] / .5).astype(int); LEAD_Y0 = int(_yb.min()); LEAD = np.full(int(_yb.max()) - LEAD_Y0 + 1, -1e9)
np.maximum.at(LEAD, _yb - LEAD_Y0, HW1[:, 0])
def set_attr(me_, name, arr4):
    old = me_.color_attributes.get(name)
    if old: me_.color_attributes.remove(old)
    ca_ = me_.color_attributes.new(name, 'FLOAT_COLOR', 'POINT'); ca_.data.foreach_set('color', np.asarray(arr4, np.float32).ravel()); return ca_
def paint_hull():
    me_ = hull.data
    lv = me_.color_attributes.get('Livery')
    if lv: lv.name = 'Livery17'
    _, _, W_, N_ = hull_arrays()
    A = nb_avg(W_); el = np.sqrt(((W_[HE[:, 0]] - W_[HE[:, 1]]) ** 2).sum(1))
    ml = (np.bincount(HE[:, 0], el, HN) + np.bincount(HE[:, 1], el, HN)) / HDEG + 1e-6
    cv = ((A - W_) * N_).sum(1) / ml; cv = .5 * cv + .5 * nb_avg(cv)
    col, zn, wr, gl = zones(W_, N_, convex=_ss(-.02, -.12, cv), grime=_ss(.02, .12, cv))
    ca_ = set_attr(me_, 'Livery', np.c_[col, np.ones(HN)])
    set_attr(me_, 'Zone', zn); set_attr(me_, 'Wear', wr); set_attr(me_, 'Glow', np.c_[gl, gl, gl, np.ones(HN)])
    try: me_.color_attributes.active_color = ca_
    except Exception: pass
    print('MODEL v18 hull painted: ceramic', int((zn[:, 0] > .5).sum()), 'carbon', int((zn[:, 1] > .5).sum()), 'gold', int((zn[:, 2] > .5).sum()),
          'orange', int((zn[:, 3] > .5).sum()), 'teal', int((gl > .5).sum()))
v18_step('paint hull', paint_hull, optional=False)

# ---------------------------------------------------------------- 5. hull shader: procedural detail on top of the baked paint
def _nd(nt, t, **kw):
    n = nt.nodes.new(t)
    for k, v in kw.items(): setattr(n, k, v)
    return n
def _mth(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]
def _sum(nt, *terms):
    cur = terms[0]
    for t in terms[1:]: cur = _mth(nt, 'ADD', cur, t)
    return cur
def _attr(nt, name):
    a = _nd(nt, 'ShaderNodeAttribute', attribute_name=name, attribute_type='GEOMETRY')
    s = _nd(nt, 'ShaderNodeSeparateColor'); nt.links.new(a.outputs['Color'], s.inputs[0]); return a.outputs['Color'], s.outputs
def _noise(nt, vec, scale, detail=4.0, rough=.55):
    n = _nd(nt, 'ShaderNodeTexNoise'); nt.links.new(vec, n.inputs['Vector']); n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough; return n
def _mapv(nt, vec, scale, rotz=0.0):
    m = _nd(nt, 'ShaderNodeMapping'); nt.links.new(vec, m.inputs['Vector']); m.inputs['Scale'].default_value = scale
    m.inputs['Rotation'].default_value = (0, 0, math.radians(rotz)); return m.outputs[0]
def _ms(m, io, name):
    return [s_ for s_ in (m.inputs if io == 'i' else m.outputs) if s_.name == name and s_.enabled][0]
def _fmix(nt, fac, a, b):
    m = _nd(nt, 'ShaderNodeMix', data_type='FLOAT'); nt.links.new(fac, _ms(m, 'i', 'Factor'))
    for sock, v in ((_ms(m, 'i', 'A'), a), (_ms(m, 'i', 'B'), b)):
        if isinstance(v, (int, float)): sock.default_value = v
        else: nt.links.new(v, sock)
    return _ms(m, 'o', 'Result')
def _cmix(nt, fac, a, b):
    m = _nd(nt, 'ShaderNodeMix', data_type='RGBA'); nt.links.new(fac, _ms(m, 'i', 'Factor'))
    for sock, v in ((_ms(m, 'i', 'A'), a), (_ms(m, 'i', 'B'), b)):
        if isinstance(v, tuple): sock.default_value = (*v, 1) if len(v) == 3 else v
        else: nt.links.new(v, sock)
    return _ms(m, 'o', 'Result')
def _unlink(nt, sock):
    for l in list(sock.links): nt.links.remove(l)
def v18_hull_shader(m, back_attr='Livery17'):
    nt = m.node_tree; p = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    geo = _nd(nt, 'ShaderNodeNewGeometry'); pos = geo.outputs['Position']; back = geo.outputs['Backfacing']
    sx = _nd(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(pos, sx.inputs[0]); X, Y = sx.outputs['X'], sx.outputs['Y']
    liv, _ = _attr(nt, 'Livery'); liv17, _ = _attr(nt, back_attr)
    _, zn = _attr(nt, 'Zone'); _, wr = _attr(nt, 'Wear'); _, gl = _attr(nt, 'Glow')
    cer, cc, gold = zn[0], zn[1], zn[2]
    za = _nd(nt, 'ShaderNodeAttribute', attribute_name='Zone', attribute_type='GEOMETRY'); paint = za.outputs['Alpha']
    wa = _nd(nt, 'ShaderNodeAttribute', attribute_name='Wear', attribute_type='GEOMETRY')
    convex, soot, heat, grm = wr[0], wr[1], wr[2], wa.outputs['Alpha']; glow = gl[0]
    skin = _mth(nt, 'SUBTRACT', 1.0, _sum(nt, cer, cc, gold), clamp=True)
    nb = _noise(nt, _mapv(nt, pos, (.35, 25, 25)), 3.0, 6.0, .6).outputs['Fac']                 # brushing along the panels (x)
    def gridline(c, s, w):
        f = _mth(nt, 'FRACT', _mth(nt, 'MULTIPLY', c, 1 / s)); return _mth(nt, 'GREATER_THAN', _mth(nt, 'ABSOLUTE', _mth(nt, 'SUBTRACT', f, .5)), w)
    tile = _mth(nt, 'MAXIMUM', gridline(X, .32, .462), gridline(Y, .32, .462))                     # ceramic tile grid
    cmb = _nd(nt, 'ShaderNodeCombineXYZ'); nt.links.new(_mth(nt, 'FLOOR', _mth(nt, 'MULTIPLY', X, 1 / .32)), cmb.inputs[0]); nt.links.new(_mth(nt, 'FLOOR', _mth(nt, 'MULTIPLY', Y, 1 / .32)), cmb.inputs[1])
    tt = _noise(nt, cmb.outputs[0], 37.3, 0.0).outputs['Fac']
    vo = _nd(nt, 'ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); dn = _noise(nt, pos, 6.0, 2.0)
    vm = _nd(nt, 'ShaderNodeVectorMath', operation='MULTIPLY_ADD'); nt.links.new(dn.outputs['Color'], vm.inputs[0]); vm.inputs[1].default_value = (.06, .06, .06); nt.links.new(pos, vm.inputs[2])
    nt.links.new(vm.outputs[0], vo.inputs['Vector']); vo.inputs['Scale'].default_value = 16.0
    crink = _mth(nt, 'SUBTRACT', 1.0, _mth(nt, 'MULTIPLY', vo.outputs['Distance'], 6.0), clamp=True)       # gold-foil crinkle ridges
    s1 = _mth(nt, 'GREATER_THAN', _noise(nt, _mapv(nt, pos, (2, 70, 70), 25), 2.0, 2.0).outputs['Fac'], .66)
    s2 = _mth(nt, 'GREATER_THAN', _noise(nt, _mapv(nt, pos, (2, 70, 70), -40), 2.0, 2.0).outputs['Fac'], .67)
    scratch = _mth(nt, 'MULTIPLY', _mth(nt, 'MAXIMUM', s1, s2), _mth(nt, 'MULTIPLY', convex, 1.4), clamp=True)
    # base colour
    mf = _sum(nt, 1.0, _mth(nt, 'MULTIPLY', _mth(nt, 'SUBTRACT', nb, .5), _mth(nt, 'MULTIPLY', skin, .16)),
              _mth(nt, 'MULTIPLY', _mth(nt, 'SUBTRACT', tt, .5), _mth(nt, 'MULTIPLY', cer, .35)),
              _mth(nt, 'MULTIPLY', tile, _mth(nt, 'MULTIPLY', cer, -.55)))
    vs = _nd(nt, 'ShaderNodeVectorMath', operation='SCALE'); nt.links.new(liv, vs.inputs[0]); nt.links.new(mf, vs.inputs['Scale'])
    front = _cmix(nt, _mth(nt, 'MULTIPLY', scratch, .65), vs.outputs[0], (.52, .53, .55))
    _unlink(nt, p.inputs['Base Color']); nt.links.new(_cmix(nt, back, front, liv17), p.inputs['Base Color'])
    met = _mth(nt, 'SUBTRACT', 1.0, _sum(nt, cer, _mth(nt, 'MULTIPLY', cc, .7), _mth(nt, 'MULTIPLY', paint, .8), glow), clamp=True)
    _unlink(nt, p.inputs['Metallic']); nt.links.new(_fmix(nt, back, met, .25), p.inputs['Metallic'])
    rgh = _sum(nt, .35, _mth(nt, 'MULTIPLY', cer, .45), _mth(nt, 'MULTIPLY', cc, .15), _mth(nt, 'MULTIPLY', gold, -.10), _mth(nt, 'MULTIPLY', paint, .1),
               _mth(nt, 'MULTIPLY', _mth(nt, 'SUBTRACT', nb, .5), _mth(nt, 'MULTIPLY', skin, .14)), _mth(nt, 'MULTIPLY', grm, .22), _mth(nt, 'MULTIPLY', soot, .3), _mth(nt, 'MULTIPLY', scratch, .18))
    _unlink(nt, p.inputs['Roughness']); nt.links.new(_fmix(nt, back, _mth(nt, 'MINIMUM', rgh, 1.0), .38), p.inputs['Roughness'])
    try:
        _unlink(nt, p.inputs['Coat Weight']); nt.links.new(_fmix(nt, back, _mth(nt, 'MULTIPLY', cc, .3), .35), p.inputs['Coat Weight'])
    except Exception as e: print('Error v18 coat', e)
    hgt = _sum(nt, _mth(nt, 'MULTIPLY', nb, _mth(nt, 'MULTIPLY', skin, .4)), _mth(nt, 'MULTIPLY', tile, _mth(nt, 'MULTIPLY', cer, -1.0)),
               _mth(nt, 'MULTIPLY', crink, _mth(nt, 'MULTIPLY', gold, .8)), _mth(nt, 'MULTIPLY', scratch, -.3))
    bump = _nd(nt, 'ShaderNodeBump'); bump.inputs['Strength'].default_value = .3; bump.inputs['Distance'].default_value = .02
    nt.links.new(hgt, bump.inputs['Height'])
    old_n = p.inputs['Normal'].links[0].from_socket if p.inputs['Normal'].links else None
    if old_n is not None: nt.links.new(old_n, bump.inputs['Normal'])
    _unlink(nt, p.inputs['Normal']); nt.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    _unlink(nt, p.inputs['Emission Color']); p.inputs['Emission Color'].default_value = (*C_TEAL, 1)
    _unlink(nt, p.inputs['Emission Strength']); nt.links.new(_mth(nt, 'MULTIPLY', glow, _mth(nt, 'MULTIPLY', _mth(nt, 'SUBTRACT', 1.0, back), 6.0)), p.inputs['Emission Strength'])
    for g in [n for n in nt.nodes if n.type == 'BSDF_GLASS']:      # canopy: tinted glass
        g.inputs['Color'].default_value = (*C_CAN, 1); g.inputs['Roughness'].default_value = .05
def shade_hull():
    for m in hull.data.materials: v18_hull_shader(m)
    print('MODEL v18 hull shader on', len(hull.data.materials), 'materials')
v18_step('hull shader', shade_hull, optional=False)

# ---------------------------------------------------------------- 6. keel fairing (belly disc) follows the same zones
def paint_fairing():
    ks_ = bpy.data.objects.get('KeelFairing')
    if not ks_: print('MODEL v18 no KeelFairing'); return
    me_ = ks_.data; n_ = len(me_.vertices)
    lv = me_.color_attributes.get('Livery')
    if lv: lv.name = 'Livery17'
    c_ = np.empty(n_ * 3, np.float32); me_.vertices.foreach_get('co', c_); c_ = c_.reshape(-1, 3)
    M_ = np.array(ks_.matrix_world); W_ = c_ @ M_[:3, :3].T + M_[:3, 3]
    nr = np.empty(n_ * 3, np.float32); me_.vertex_normals.foreach_get('vector', nr); nr = nr.reshape(-1, 3)
    N_ = nr @ (M_[:3, :3] / np.linalg.norm(M_[:3, 0])).T; N_ /= np.linalg.norm(N_, axis=1, keepdims=True) + 1e-9
    col, zn, wr, gl = zones(W_, N_, is_hull=False)
    set_attr(me_, 'Livery', np.c_[col, np.ones(n_)]); set_attr(me_, 'Zone', zn); set_attr(me_, 'Wear', wr); set_attr(me_, 'Glow', np.c_[gl, gl, gl, np.ones(n_)])
    for m in me_.materials: v18_hull_shader(m)
    print('MODEL v18 fairing painted', n_)
v18_step('fairing', paint_fairing)

# ---------------------------------------------------------------- 7. materials for separate exterior parts
def mat18(name, base, metal, rough, kind='plain', emit=None, estr=0.0, back=None, coat=0.0):
    m = pbsdf(name, base, metal, rough, emit, estr); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    tc = _nd(nt, 'ShaderNodeTexCoord'); ob = tc.outputs['Object']; oi = _nd(nt, 'ShaderNodeObjectInfo')
    if coat:
        try: p.inputs['Coat Weight'].default_value = coat
        except Exception: pass
    hgt = None; colsock = None
    if kind == 'brushed':
        nb = _noise(nt, _mapv(nt, ob, (.35, 25, 25)), 3.0, 6.0, .6).outputs['Fac']
        tone = _sum(nt, .93, _mth(nt, 'MULTIPLY', oi.outputs['Random'], .14), _mth(nt, 'MULTIPLY', _mth(nt, 'SUBTRACT', nb, .5), .12))
        vs = _nd(nt, 'ShaderNodeVectorMath', operation='SCALE'); vs.inputs[0].default_value = base; nt.links.new(tone, vs.inputs['Scale']); colsock = vs.outputs[0]
        nt.links.new(_sum(nt, rough, _mth(nt, 'MULTIPLY', _mth(nt, 'SUBTRACT', nb, .5), .14)), p.inputs['Roughness']); hgt = _mth(nt, 'MULTIPLY', nb, .4)
    elif kind == 'tile':
        sx = _nd(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(ob, sx.inputs[0])
        def gl_(c):
            f = _mth(nt, 'FRACT', _mth(nt, 'MULTIPLY', c, 1 / .32)); return _mth(nt, 'GREATER_THAN', _mth(nt, 'ABSOLUTE', _mth(nt, 'SUBTRACT', f, .5)), .462)
        t_ = _mth(nt, 'MAXIMUM', gl_(sx.outputs['X']), gl_(sx.outputs['Y']))
        vs = _nd(nt, 'ShaderNodeVectorMath', operation='SCALE'); vs.inputs[0].default_value = base; nt.links.new(_mth(nt, 'SUBTRACT', 1.0, _mth(nt, 'MULTIPLY', t_, .55)), vs.inputs['Scale']); colsock = vs.outputs[0]
        hgt = _mth(nt, 'MULTIPLY', t_, -1.0)
    elif kind == 'crinkle':
        vo = _nd(nt, 'ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); dn = _noise(nt, ob, 6.0, 2.0)
        vm = _nd(nt, 'ShaderNodeVectorMath', operation='MULTIPLY_ADD'); nt.links.new(dn.outputs['Color'], vm.inputs[0]); vm.inputs[1].default_value = (.06, .06, .06); nt.links.new(ob, vm.inputs[2])
        nt.links.new(vm.outputs[0], vo.inputs['Vector']); vo.inputs['Scale'].default_value = 16.0
        hgt = _mth(nt, 'SUBTRACT', 1.0, _mth(nt, 'MULTIPLY', vo.outputs['Distance'], 6.0), clamp=True)
        nt.links.new(_sum(nt, rough, _mth(nt, 'MULTIPLY', dn.outputs['Fac'], .12)), p.inputs['Roughness'])
    elif kind == 'flatpanel':     # radiator: flat panels with fine fin lines
        sx = _nd(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(ob, sx.inputs[0])
        f = _mth(nt, 'FRACT', _mth(nt, 'MULTIPLY', sx.outputs['X'], 1 / .06)); hgt = _mth(nt, 'GREATER_THAN', f, .85)
    if hgt is not None:
        bump = _nd(nt, 'ShaderNodeBump'); bump.inputs['Strength'].default_value = .3; bump.inputs['Distance'].default_value = .02
        nt.links.new(hgt, bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    if back is not None:          # back faces keep the old look (anything seen from inside is unchanged)
        geo = _nd(nt, 'ShaderNodeNewGeometry')
        src = colsock if colsock is not None else None
        nt.links.new(_cmix(nt, geo.outputs['Backfacing'], src if src is not None else tuple(base), tuple(back[0])), p.inputs['Base Color'])
        nt.links.new(_fmix(nt, geo.outputs['Backfacing'], metal, back[1]), p.inputs['Metallic'])
        if not p.inputs['Roughness'].links: nt.links.new(_fmix(nt, geo.outputs['Backfacing'], rough, back[2]), p.inputs['Roughness'])
    elif colsock is not None: nt.links.new(colsock, p.inputs['Base Color'])
    return m
M18_TI = mat18('V18Titanium', C_TI, 1.0, .35, 'brushed')
M18_TIB = mat18('V18TitaniumSponson', C_TI, 1.0, .35, 'brushed', back=((.8, .81, .83), .25, .38))
M18_CER = mat18('V18Ceramic', C_CER, 0.0, .8, 'tile')
M18_CC = mat18('V18Carbon', C_CC, .3, .5, 'plain', coat=.3)
M18_GOLD = mat18('V18GoldFoil', C_GOLD, 1.0, .25, 'crinkle')
M18_RAD = mat18('V18Radiator', C_RAD, .6, .4, 'flatpanel')
M18_NOZ = mat18('V18Nozzle', C_NOZ, 1.0, .3, 'brushed')
M18_ORN = mat18('V18Orange', C_ORN, .2, .4)
M18_TEAL = mat18('V18TealLine', C_TEAL, 0.0, .3, emit=C_TEAL, estr=6.0)
M18_RING = mat18('V18GlowRing', (.6, .8, 1.0), 0.0, .3, emit=(.45, .72, 1.0), estr=10.0)
M18_DARK = mat18('V18IntakeDark', (.008, .008, .009), 0.0, .9)
def mhaz18():
    m = bpy.data.materials.new('V18Hazard'); m.use_nodes = True; nt = m.node_tree; p = nt.nodes['Principled BSDF']
    tc = _nd(nt, 'ShaderNodeTexCoord'); wv = _nd(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='DIAGONAL', wave_profile='SAW'); wv.inputs['Scale'].default_value = 3.0
    nt.links.new(tc.outputs['Object'], wv.inputs['Vector'])
    cr = _nd(nt, 'ShaderNodeValToRGB'); cr.color_ramp.interpolation = 'CONSTANT'; cr.color_ramp.elements[0].color = (.015, .015, .015, 1)
    cr.color_ramp.elements[1].color = (.9, .62, .02, 1); cr.color_ramp.elements[1].position = .5
    nt.links.new(wv.outputs['Fac'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Metallic'].default_value = .1; p.inputs['Roughness'].default_value = .55; return m
def mrad18(half=.3):
    m = bpy.data.materials.new('V18Radiation'); m.use_nodes = True; nt = m.node_tree; p = nt.nodes['Principled BSDF']
    tc = _nd(nt, 'ShaderNodeTexCoord'); sx = _nd(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sx.inputs[0])
    u, v = sx.outputs['X'], sx.outputs['Y']
    r_ = _mth(nt, 'SQRT', _mth(nt, 'ADD', _mth(nt, 'MULTIPLY', u, u), _mth(nt, 'MULTIPLY', v, v)))
    a_ = _mth(nt, 'ARCTAN2', v, u)
    sector = _mth(nt, 'LESS_THAN', _mth(nt, 'FRACT', _mth(nt, 'MULTIPLY', _mth(nt, 'ADD', a_, math.pi / 2 + math.pi / 6), 3 / (2 * math.pi))), .5)
    blade = _mth(nt, 'MULTIPLY', sector, _mth(nt, 'MULTIPLY', _mth(nt, 'GREATER_THAN', r_, half * .26), _mth(nt, 'LESS_THAN', r_, half * .80)))
    dot = _mth(nt, 'LESS_THAN', r_, half * .17)
    blk = _mth(nt, 'MAXIMUM', blade, dot)
    m_ = _cmix(nt, blk, (.92, .66, .02), (.012, .012, .012)); nt.links.new(m_, p.inputs['Base Color'])
    p.inputs['Metallic'].default_value = .1; p.inputs['Roughness'].default_value = .5; return m
M18_HAZ = mhaz18(); M18_RADSYM = mrad18()

# ---------------------------------------------------------------- 8. assign materials to the existing exterior parts
REACT_X = (-24.3, -11.5)
def assign_parts():
    cnt = {}
    def setm(o, m):
        if not o.data.materials: o.data.materials.append(m)
        else:
            for i in range(len(o.data.materials)): o.data.materials[i] = m
        cnt[m.name] = cnt.get(m.name, 0) + 1
    for o in list(bpy.data.objects):
        if o.type != 'MESH': continue
        nm = o.name; c = o.matrix_world.translation
        nz = (o.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized().z
        inreact = REACT_X[0] < c.x < REACT_X[1] and abs(c.y) < 6.5
        if nm.startswith(('XPlate', 'XSide')):
            setm(o, M18_CER if nz < -.4 else (M18_CC if c.x > HXMAX - 3.0 else M18_TI))
        elif nm.startswith('XVentSlat'): setm(o, M18_GOLD if inreact else M18_TI)
        elif nm.startswith('XVent'): setm(o, M18_GOLD if inreact else M18_NOZ)
        elif nm.startswith('XHatch'): setm(o, M18_HAZ if inreact else (M18_CER if nz < -.4 else M18_NOZ))
        elif nm.startswith('ThrusterRing') or nm in ('Thruster0', 'Thruster1', 'Thruster2'): setm(o, M18_NOZ)
        elif nm.startswith('Strake'): setm(o, M18_CC)
        elif nm.endswith('Sponson'): setm(o, M18_TIB)
        elif nm.endswith('SponsonStripe'): setm(o, M18_TEAL)
    print('MODEL v18 part materials', cnt)
v18_step('part materials', assign_parts, optional=False)

# ---------------------------------------------------------------- 9. new exterior parts
def obox(name, c, ex, ey, ez, hs, mat):
    c = Vector(c); V_ = []
    for sx_ in (-1, 1):
        for sy_ in (-1, 1):
            for sz_ in (-1, 1): V_.append(tuple(c + ex * (sx_ * hs[0]) + ey * (sy_ * hs[1]) + ez * (sz_ * hs[2])))
    F_ = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    o = mk(name, V_, F_, mat); o.data.update(); return o
def hull_hit(x, y, zfrom=14.0, d=(0, 0, -1)):
    dg_ = bpy.context.evaluated_depsgraph_get(); o_ = Vector((x, y, zfrom))
    for _ in range(16):
        hit, p_, n_, fi, ob, _m = sc.ray_cast(dg_, o_, Vector(d))
        if not hit: return None
        if ob is not None and ob.name == 'Hull': return p_, n_
        o_ = p_ + Vector(d) * .03
    return None
def winglets():
    for o in [o for o in bpy.data.objects if o.name.startswith('Winglet')]: bpy.data.objects.remove(o)
    _, _, W_, _ = hull_arrays(); n_ = 0
    cant = math.radians(20)
    for nm, idx, s in (('WingletPort', W_[:, 1].argmax(), 1), ('WingletStbd', W_[:, 1].argmin(), -1)):
        tip = Vector(W_[idx]); tip.y -= s * .25
        d = Vector((0, s * math.sin(cant), math.cos(cant)))
        cr_, ct_, sp_, sw_ = 3.6, 1.4, 3.3, 2.4
        f = fin(nm, tip, cr_, ct_, sp_, sw_, d, .16, M18_TI)                                          # fixed canted fin
        rr = tip + Vector((-cr_ / 2 - .5, 0, 0)); rs = sp_ * .9
        r_ = fin(nm + 'Rudder', rr, .9, .55, rs, (sw_ + ct_ / 2 + .35) - (cr_ / 2 + .5), d, .12, M18_NOZ)   # rudder behind the hinge line
        fr = .86; cf = cr_ + (ct_ - cr_) * fr
        fin(nm + 'Tip', tip + d * (sp_ * fr) + Vector((-sw_ * fr, 0, 0)), cf, ct_, sp_ * (1 - fr) + .02, sw_ * (1 - fr), d, .175, M18_ORN)   # orange ID tip
        fin(nm + 'Low', tip, 2.4, 1.0, 1.1, 1.2, Vector((0, s * .36, -1)), .12, M18_CC)
        n_ += 1
    print('MODEL v18 winglets rebuilt (canted rudders, 20 deg)', n_)
def chine():
    _, _, W_, N_ = hull_arrays(); X, Ya, Z, up = W_[:, 0], np.abs(W_[:, 1]), W_[:, 2], N_[:, 2]
    x_end = HXMAX - 3.5; xs = np.arange(7.2, x_end, .4); made = 0
    for s in (1, -1):
        pts = []
        for x in xs:
            sl = (np.abs(X - x) < .2) & (np.abs(W_[:, 1]) < 6) & (np.sign(W_[:, 1] + 1e-6) == s) & (up < -.8)
            if sl.sum() < 8: pts.append(None); continue
            zb = Z[sl].min(); band = sl & (Z < zb + .35)
            yc = np.percentile(Ya[band], 97); zz = Z[band & (Ya > yc - .15)]
            pts.append((x, yc, float(zz.mean()) if len(zz) else zb) if yc > .6 else None)
        runs, cur = [], []
        for p_ in pts + [None]:
            if p_ is not None and cur and (abs(p_[1] - cur[-1][1]) > .4 or abs(p_[2] - cur[-1][2]) > .25): runs.append(cur); cur = []
            if p_ is None:
                if cur: runs.append(cur)
                cur = []
            else: cur.append(p_)
        runs = [r_ for r_ in runs if len(r_) >= 8]
        if not runs: print('MODEL v18 chine side', s, 'no belly run'); continue
        for ri, run in enumerate(runs): made += chine_run(s, ri, run)
    print('MODEL v18 chines', made)
def chine_run(s, ri, run):
    if True:
        R = np.array(run); k = 5
        for j in (1, 2): R[:, j] = np.convolve(np.pad(R[:, j], (k // 2, k // 2), mode='edge'), np.ones(k) / k, mode='valid')
        n = len(R); V_ = []; F_ = []; L_ = []
        for i, (x, yc, zc_) in enumerate(R):
            e = min(1.0, i / 3.0, (n - 1 - i) / 3.0)
            prof = [(yc - .10, zc_ + .015), (yc + .02 + .10 * e, zc_ - .03 * e), (yc - .03, zc_ + .13)]
            for (yy, zz) in prof: V_.append((float(x), s * float(yy), float(zz)))
            L_.append((float(x), s * float(yc + .02 + .10 * e), float(zc_ - .03 * e)))
        for i in range(n - 1):
            a0, b0 = 3 * i, 3 * (i + 1)
            for j in range(3):
                q = (a0 + j, b0 + j, b0 + (j + 1) % 3, a0 + (j + 1) % 3)
                F_.append(q if s > 0 else q[::-1])
        F_.append((0, 1, 2) if s < 0 else (2, 1, 0)); F_.append((3 * (n - 1), 3 * (n - 1) + 1, 3 * (n - 1) + 2) if s > 0 else (3 * (n - 1) + 2, 3 * (n - 1) + 1, 3 * (n - 1)))
        o = mk(f'XChine{s}_{ri}', V_, F_, M18_CER); o.data.update()
        V2 = []; F2 = []
        for i, (x, y, z) in enumerate(L_):
            for (dy, dz) in ((0, .014), (s * .014, 0), (0, -.014), (-s * .014, 0)): V2.append((x, y + dy, z + dz))
        for i in range(len(L_) - 1):
            for j in range(4): F2.append((4 * i + j, 4 * (i + 1) + j, 4 * (i + 1) + (j + 1) % 4, 4 * i + (j + 1) % 4))
        mk(f'XChineLight{s}_{ri}', V2, F2, M18_TEAL)
        print('MODEL v18 chine side', s, 'x', round(R[0, 0], 1), '->', round(R[-1, 0], 1), 'y', round(R[:, 1].min(), 2), round(R[:, 1].max(), 2))
        return 1
def intakes():
    made = 0
    for s in (1, -1):
        xi, yi = -19.0, s * 7.6
        h0 = hull_hit(xi + 1.3, yi); h1 = hull_hit(xi - 1.3, yi); hc = hull_hit(xi, yi)
        if not (h0 and h1 and hc): print('MODEL v18 intake', s, 'no skin hit'); continue
        ex = (h0[0] - h1[0]).normalized(); nz = hc[1].normalized(); ey = nz.cross(ex).normalized(); ez = ex.cross(ey).normalized()
        base = (h0[0] + h1[0]) / 2
        gap, L, Wd, H, t = .1, 2.6, 1.1, .55, .06
        b0 = base + ez * gap
        obox(f'XIntakeSplitter{s}', b0 + ex * .25 + ez * .015, ex, ey, ez, (L / 2 + .25, Wd / 2 + .06, .015), M18_TI)
        for k, xo in enumerate((-.8, .5)): obox(f'XIntakePost{s}_{k}', base + ex * xo + ez * (gap / 2), ex, ey, ez, (.08, .3, gap / 2 + .03), M18_NOZ)
        for side in (-1, 1): obox(f'XIntakeWall{s}_{side}', b0 + ey * (side * (Wd / 2 - t / 2)) + ez * (H / 2 + .03), ex, ey, ez, (L / 2, t / 2, H / 2), M18_TI)
        obox(f'XIntakeRoof{s}', b0 + ez * (H + .03 - t / 2), ex, ey, ez, (L / 2, Wd / 2, t / 2), M18_TI)
        obox(f'XIntakeLip{s}', b0 + ex * (L / 2 - .03) + ez * (H + .03 - t / 2), ex, ey, ez, (.05, Wd / 2 + .01, t / 2 + .012), M18_CC)
        obox(f'XIntakeMouth{s}', b0 + ex * (-.35) + ez * (H / 2 + .03), ex, ey, ez, (L / 2 - .4, Wd / 2 - t, H / 2 - .005), M18_DARK)
        # sloped compression ramp on the duct floor: rises from the lip back into the dark throat
        p0 = b0 + ex * (L / 2) + ez * .03; p1 = b0 + ex * (L / 2 - 1.5) + ez * (.03 + H * .55)
        V_ = []
        for side in (-1, 1):
            w = ey * (side * (Wd / 2 - t))
            V_ += [tuple(p0 + w), tuple(p1 + w), tuple(b0 + ex * (L / 2 - 1.5) + ez * .03 + w)]
        o = mk(f'XIntakeRamp{s}', V_, [(0, 1, 4, 3), (1, 2, 5, 4), (0, 3, 5, 2), (0, 2, 1), (3, 4, 5)], M18_NOZ); o.data.update()
        made += 1
    print('MODEL v18 intakes', made)
def radiators():
    n_ = 0
    for s in (1, -1):
        for x in np.arange(-20.0, -16.3, 1.0):
            for y in np.arange(10.2, 12.7, .6):
                h = hull_hit(float(x), float(s * y))
                if not h or h[1].z < .3: continue
                plate(f'XRadiator{s}_{n_}', h[0], h[1], (.94, .55, .03), M18_RAD); n_ += 1
    print('MODEL v18 radiator panels', n_)
def reactor_panels():
    n_ = 0
    for s in (1, -1):
        for xc in (-20.5, -16.8):
            h = hull_hit(xc, s * 2.6)
            if not h or h[1].z < .3: continue
            p_, nrm = h; q = Vector((0, 0, 1)).rotation_difference(nrm)
            ex, ey, ez = q @ Vector((1, 0, 0)), q @ Vector((0, 1, 0)), nrm.normalized()
            obox(f'XReactorAccess{s}_{n_}', p_ + ez * .02, ex, ey, ez, (.75, .55, .02), M18_NOZ)
            for k, (o_, hs) in enumerate((((0, .5), (.75, .06)), ((0, -.5), (.75, .06)), ((.69, 0), (.06, .44)), ((-.69, 0), (.06, .44)))):
                obox(f'XReactorHaz{s}_{n_}_{k}', p_ + ex * o_[0] + ey * o_[1] + ez * .045, ex, ey, ez, (hs[0], hs[1], .006), M18_HAZ)
            sym = obox(f'XReactorRadSym{s}_{n_}', (0, 0, 0), Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), (.3, .3, .006), M18_RADSYM)
            sym.rotation_mode = 'QUATERNION'; sym.rotation_quaternion = q; sym.location = p_ + ez * .047
            n_ += 1
    print('MODEL v18 reactor access panels', n_)
def registry():
    _, _, W_, N_ = hull_arrays(); cs = .2
    up_ = N_[:, 2] > .3; P_ = W_[up_]
    gx0, gy0 = P_[:, 0].min(), P_[:, 1].min(); ix = ((P_[:, 0] - gx0) / cs).astype(int); iy = ((P_[:, 1] - gy0) / cs).astype(int)
    ZT = np.full((ix.max() + 1, iy.max() + 1), np.nan); ZT[:] = -1e9; np.maximum.at(ZT, (ix, iy), P_[:, 2])
    def ztop(x, y):
        i, j = int((x - gx0) / cs), int((y - gy0) / cs)
        best = -1e9
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if 0 <= i + di < ZT.shape[0] and 0 <= j + dj < ZT.shape[1]: best = max(best, ZT[i + di, j + dj])
        return best
    n_ = 0
    for s, yc in ((1, 13.4), (-1, -13.4)):
        xc = REG_X
        cu = bpy.data.curves.new(f'XRegistry{s}', 'FONT'); cu.body = 'HK-07'; cu.size = 1.05; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
        o = bpy.data.objects.new(f'XRegistry{s}', cu); col.objects.link(o); o.location = (xc, yc, 0); o.rotation_euler = (0, 0, math.radians(-90))
        for ob in bpy.context.selected_objects: ob.select_set(False)
        o.select_set(True); bpy.context.view_layer.objects.active = o; bpy.ops.object.convert(target='MESH')
        o = bpy.context.active_object; bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2, use_grid_fill=True)
        bad = 0
        for v in bm.verts:
            z = ztop(v.co.x, v.co.y)
            if z < -1e8: bad += 1; z = 0
            v.co.z = z + .016
        bm.to_mesh(o.data); bm.free(); o.data.materials.clear(); o.data.materials.append(M18_ORN)
        print('MODEL v18 registry', o.name, 'verts', len(o.data.vertices), 'unprojected', bad); n_ += 1
    print('MODEL v18 registry marks', n_)
REG_X = -14.6
for nm_, fn_ in (('winglets', winglets), ('chine', chine), ('intakes', intakes), ('radiators', radiators), ('reactor panels', reactor_panels), ('registry', registry)):
    v18_step(nm_, fn_)
def nozzle_rings():
    n_ = 0
    for i in range(3):
        e = bpy.data.objects.get(f'Exhaust{i}')
        if not e: continue
        R = e.dimensions.y / 2 * 1.1
        Tor(f'ThrusterGlowRing{i}', e.matrix_world.translation + Vector((.02, 0, 0)), R, .05, M18_RING, rot=(0, 90, 0), ms=48, ns=8); n_ += 1
    print('MODEL v18 nozzle glow rings', n_)
v18_step('nozzle rings', nozzle_rings)
bpy.context.view_layer.update()
print('TIMING v18 done', round(_tm0.time() - _TS), 'pass s', round(_tm0.time() - V18_T0))
