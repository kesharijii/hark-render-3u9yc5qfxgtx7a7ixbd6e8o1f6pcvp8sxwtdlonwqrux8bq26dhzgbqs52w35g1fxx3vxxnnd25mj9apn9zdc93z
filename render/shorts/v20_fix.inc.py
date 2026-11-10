# ---------------------------------------------------------------- v20 USER FIXES (2026-11-10): planks, sponson blisters, nose tuck, closed hatch, keel deck, real reactor
import bmesh as _bm
def _v20(step, fn):
    t_ = _tm0.time()
    try: fn(); print('MODEL v20', step, 'ok', round(_tm0.time() - t_, 1), 's')
    except Exception:
        import traceback; print('Error v20', step); traceback.print_exc()
def _wb(o):
    ws = [o.matrix_world @ Vector(v) for v in o.bound_box]
    return Vector((min(w.x for w in ws), min(w.y for w in ws), min(w.z for w in ws))), Vector((max(w.x for w in ws), max(w.y for w in ws), max(w.z for w in ws)))
def _cutbox(name, lo, hi):
    bpy.ops.mesh.primitive_cube_add(size=1, location=tuple((Vector(lo) + Vector(hi)) / 2))
    c = bpy.context.active_object; c.name = name; c.scale = tuple(Vector(hi) - Vector(lo)); c.hide_render = True; c.hide_viewport = True; c.display_type = 'WIRE'
    return c
def _bool(o, cutter, op='DIFFERENCE'):
    b = o.modifiers.new('C20', 'BOOLEAN'); b.operation = op; b.object = cutter; b.solver = 'EXACT'; return b

# 1. the two floating planks on the hall floor (old pit steps) + any other PStep left floating
def v20_planks():
    gone = []
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name.startswith('PStep'):
            lo, hi = _wb(o)
            if o.name in ('PStep107', 'PStep-107') or lo.z > Z0 + .04: gone.append(o.name); _rm(o)
    print('MODEL v20 planks removed', gone)

# 2. sponson boxes -> smooth super-ellipsoid blisters faired into the wing (rooms, windows and the hall untouched)
def _superhalf(n=4.0, NT=28, NP=112):
    e = 2.0 / n; sg = lambda v: math.copysign(abs(v) ** e, v)
    V = [(0.0, 1.0, 0.0)]; F = []
    for i in range(1, NT + 1):
        th = (math.pi / 2) * i / NT
        for j in range(NP):
            ph = 2 * math.pi * j / NP
            cx, cy, cz = math.sin(th) * math.cos(ph), math.cos(th), math.sin(th) * math.sin(ph)
            V.append((sg(cx), max(cy, 0.0) ** e, sg(cz)))
    for j in range(NP): F.append((0, 1 + j, 1 + (j + 1) % NP))
    for i in range(NT - 1):
        a0 = 1 + i * NP; a1 = a0 + NP
        for j in range(NP): F.append((a0 + j, a1 + j, a1 + (j + 1) % NP, a0 + (j + 1) % NP))
    rim = 1 + (NT - 1) * NP; c = len(V); V.append((0.0, 0.0, 0.0))
    for j in range(NP): F.append((rim + (j + 1) % NP, rim + j, c))
    return V, F
def v20_sponsons():
    for nm, s in (('Mess', 1), ('Med', -1)):
        fo = bpy.data.objects.get(nm + 'Sponson')
        if not fo: print('Error v20 sponson missing', nm); continue
        fo.modifiers.clear(); lo, hi = _wb(fo)
        X0, X1, Zb, Zt = lo.x, hi.x, lo.z, hi.z
        Yi, Yo = (lo.y, hi.y) if s > 0 else (-hi.y, -lo.y)
        xc, zc = (X0 + X1) / 2, (Zb + Zt) / 2
        a, b, c = (X1 - X0) / 2 * 1.67, (Yo - Yi) + .35, (Zt - Zb) / 2 * 1.9
        V0, F0 = _superhalf()
        V = [(xc + a * v[0], s * (Yi + b * v[1]), zc + c * v[2]) for v in V0]
        F = [tuple(reversed(f)) for f in F0] if s < 0 else F0
        mats = list(fo.data.materials); old = fo.data
        me_ = bpy.data.meshes.new(nm + 'SponsonV20'); me_.from_pydata(V, [], F); me_.update()
        bm = _bm.new(); bm.from_mesh(me_); _bm.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me_); bm.free()
        me_.polygons.foreach_set('use_smooth', [True] * len(me_.polygons))
        for m in mats: me_.materials.append(m)
        fo.data = me_
        try: bpy.data.meshes.remove(old)
        except Exception: pass
        # hollow = the room box (as before), windows punched clean through the thicker skin, hall cylinder kept clear
        rc = _cutbox(nm + 'SponsonCut20', (X0 + .15, s * (Yi - .6) if s > 0 else -(Yo - .15), Zb + .15), (X1 - .15, (Yo - .15) if s > 0 else -(Yi - .6), Zt - .15))
        wg = bpy.data.objects.get(nm + 'WinGlass')
        if wg:
            wl, wh = _wb(wg); wc = _cutbox(nm + 'SponsonWinCut20', (wl.x - .02, -(Yo + 2.0) if s < 0 else Yo - .4, wl.z - .02), (wh.x + .02, (Yo + 2.0) if s > 0 else -(Yo - .4), wh.z + .02))
        else: wc = None
        bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=HR + .45, depth=20, location=(HC.x, HC.y, 0))
        hc = bpy.context.active_object; hc.name = nm + 'SponsonHallCut20'; hc.hide_render = True; hc.hide_viewport = True
        for cu in (rc, wc, hc):
            if cu: _bool(fo, cu); SIDE_CUTTERS.append(cu.name)
        for o in list(bpy.data.objects):
            if o.name == nm + 'SponsonStripe': _rm(o)
        print('MODEL v20 sponson', nm, 'x', round(X0, 2), round(X1, 2), 'y', round(Yi, 2), round(Yo, 2), 'z', round(Zb, 2), round(Zt, 2), 'blister a b c', round(a, 2), round(b, 2), round(c, 2))

# 3. bridge interior tucked inside the nose skin (deck, plate, lining, skirts, frames): every vertex clamped 0.1 m inside the hull
def _subdiv_to(o, edge=.3):
    me_ = o.data; bm = _bm.new(); bm.from_mesh(me_)
    for _ in range(6):
        long_ = [e for e in bm.edges if e.calc_length() > edge]
        if not long_: break
        _bm.ops.subdivide_edges(bm, edges=long_, cuts=1, use_grid_fill=True)
    bm.to_mesh(me_); bm.free(); me_.update()
def v20_nose():
    dg_ = bpy.context.evaluated_depsgraph_get(); HBn = bvh_of(['Hull'])
    def zr(x, y):
        b_ = HBn.ray_cast(Vector((x, y, -40)), Vector((0, 0, 1)), 80); t_ = HBn.ray_cast(Vector((x, y, 40)), Vector((0, 0, -1)), 80)
        return (b_[0].z if b_[0] is not None else None), (t_[0].z if t_[0] is not None else None)
    def yr(x, z):
        p_ = HBn.ray_cast(Vector((x, 40, z)), Vector((0, -1, 0)), 80); n_ = HBn.ray_cast(Vector((x, -40, z)), Vector((0, 1, 0)), 80)
        return (p_[0].y if p_[0] is not None else None), (n_[0].y if n_[0] is not None else None)
    tot = 0; objs = []
    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.name.startswith(('DeckBridge', 'BridgePlate', 'LiningBridge', 'BridgeSkirt', 'Frame', 'DeckFwd')): continue
        lo, hi = _wb(o)
        if hi.x < 11.0: continue
        objs.append(o)
    for o in objs:
        if len(o.data.vertices) < 400: _subdiv_to(o)
        M = o.matrix_world; Mi = M.inverted(); n = 0
        for v in o.data.vertices:
            P = M @ v.co
            if P.x < 11.0: continue
            Q = P.copy(); zb, zt = zr(P.x, P.y)
            if zb is not None and Q.z < zb + .1: Q.z = zb + .1
            if zt is not None and Q.z > zt - .1: Q.z = zt - .1
            yp, yn = yr(P.x, Q.z)
            if yp is not None and Q.y > yp - .1: Q.y = yp - .1
            if yn is not None and Q.y < yn + .1: Q.y = yn + .1
            if (Q - P).length > 1e-4: v.co = Mi @ Q; n += 1
        o.data.update(); tot += n
        print('MODEL v20 nose clamp', o.name, 'verts moved', n)
    print('MODEL v20 nose clamp total', tot, 'objects', len(objs))

# 4. belly hatch CLOSED by default (door + floor plate shown, boarding stair stowed/hidden); the tour can open it on demand later
def v20_hatch_closed():
    for nm_ in ('BellyHatchClosedDoor', 'BellyHatchClosedFloor'):
        o = bpy.data.objects.get(nm_)
        if o: o.hide_render = False; o.hide_viewport = False
    n = 0
    for o in bpy.data.objects:
        if o.name.startswith(('BoardRamp', 'BellyRampExt')): o.hide_render = True; o.hide_viewport = True; n += 1
    gl = bpy.data.objects.get('BellyHatchGlow')
    if gl: gl.hide_render = True
    print('MODEL v20 hatch closed, stair parts stowed', n)

# 5. keel bay: a clean deck plate over the hull's scratched inner floor (cells found by rays, so it follows the bay outline)
M20_DECK = pbsdf('KeelDeck20', (.045, .048, .055), .55, .42)
def v20_keel_deck():
    dg_ = bpy.context.evaluated_depsgraph_get(); step = .2; V = []; F = []; idx = {}
    def ok(x, y):
        hit, p_, n_, fi, ob, _m = sc.ray_cast(dg_, Vector((x, y, KF + .6)), Vector((0, 0, -1)), distance=1.2)
        return hit and ob is not None and ob.name in ('Hull', 'KeelFairing', 'HallBlisterBelly', 'KeelFloor') and abs(p_.z - KF) < .14 and abs(n_.z) > .8
    xs = np.arange(-12.0, 6.0, step); ys = np.arange(-6.0, 6.0, step)
    for x in xs:
        for y in ys:
            if math.hypot(x - RH_C[0], y - RH_C[1]) < RH_R + .05: continue
            if all(ok(x + dx, y + dy) for dx in (.02, step - .02) for dy in (.02, step - .02)):
                q = []
                for dx, dy in ((0, 0), (step, 0), (step, step), (0, step)):
                    k = (round(x + dx, 3), round(y + dy, 3))
                    if k not in idx: idx[k] = len(V); V.append((k[0], k[1], KF + .012))
                    q.append(idx[k])
                F.append(tuple(q))
    if F: mk('KeelDeck20', V, F, M20_DECK)
    print('MODEL v20 keel deck cells', len(F))

# 6. REACTOR: a real fusion-fission hybrid tokamak that fills the room, with power visibly flowing out to the ship
def _emat(name, col_, strength, flow=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*col_, 1)
    if flow:   # travelling pulses along the per-vertex 'u' attribute (metres along the conduit)
        at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'u'; at.attribute_type = 'GEOMETRY'
        tm = nt.nodes.new('ShaderNodeValue'); tm.label = 'time'
        d = tm.outputs[0].driver_add('default_value'); d.driver.expression = f'frame*{flow[0]}'
        sub = nt.nodes.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; nt.links.new(at.outputs['Fac'], sub.inputs[0]); nt.links.new(tm.outputs[0], sub.inputs[1])
        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = flow[1]; nt.links.new(sub.outputs[0], mul.inputs[0])
        fr = nt.nodes.new('ShaderNodeMath'); fr.operation = 'FRACT'; nt.links.new(mul.outputs[0], fr.inputs[0])
        pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 6.0; nt.links.new(fr.outputs[0], pw.inputs[0])
        ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = strength * 3.0; ad.inputs[2].default_value = strength * .25
        nt.links.new(pw.outputs[0], ad.inputs[0]); nt.links.new(ad.outputs[0], em.inputs['Strength'])
    else: em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs[0], out.inputs['Surface']); return m
def _tube(name, pts, r, mat, seg=16):
    P = [Vector(p) for p in pts]; dense = []
    for i in range(len(P) - 1):
        L = (P[i + 1] - P[i]).length; k = max(1, int(L / .15))
        for t in range(k): dense.append(P[i].lerp(P[i + 1], t / k))
    dense.append(P[-1]); V = []; F = []; U = []; acc = 0.0; up = Vector((0, 0, 1))
    for i, p in enumerate(dense):
        if i: acc += (p - dense[i - 1]).length
        t = (dense[min(i + 1, len(dense) - 1)] - dense[max(i - 1, 0)]).normalized()
        a = t.cross(up if abs(t.dot(up)) < .95 else Vector((1, 0, 0))).normalized(); b = t.cross(a).normalized()
        for j in range(seg):
            ang = 2 * math.pi * j / seg; V.append(tuple(p + r * (math.cos(ang) * a + math.sin(ang) * b))); U.append(acc)
    for i in range(len(dense) - 1):
        for j in range(seg): F.append((i * seg + j, i * seg + (j + 1) % seg, (i + 1) * seg + (j + 1) % seg, (i + 1) * seg + j))
    o = mk(name, V, F, mat, smooth=True); at = o.data.attributes.new('u', 'FLOAT', 'POINT'); at.data.foreach_set('value', U); return o
def v20_reactor():
    old = ('MiniCore', 'MiniRod', 'CoreFeed', 'CoreRet', 'CorePed', 'CoreRail', 'CoreHazardRing', 'CoreHalo', 'CoreLight')
    gone = 0
    for o in list(bpy.data.objects):
        if o.name.startswith(old): _rm(o); gone += 1
    sh = bpy.data.objects.get('ReactorShellFwd'); dk = [o for o in bpy.data.objects if o.name.startswith('ReactorShell') and o.type == 'MESH']
    zf = .3; zc = 4.6
    for o in dk:
        lo, hi = _wb(o)
        if hi.z - lo.z < .3: zf = hi.z
        else: zc = min(zc, hi.z)
    XT, YT = -20.5, 0.0; ZT = zf + 1.95; R, r = 1.42, .5
    M_VES = pbsdf('TokVessel20', (.16, .17, .19), .95, .26)
    M_COIL = pbsdf('TokCoil20', (.72, .42, .18), 1.0, .3)
    M_BLK = pbsdf('TokBlanket20', (.09, .1, .12), .7, .4)
    M_PLA = _emat('TokPlasma20', (.35, .55, 1.0), 40.0, flow=(.06, 1.6))
    M_CHER = _emat('TokCherenkov20', (.25, .6, 1.0), 14.0)
    M_PWR = _emat('TokPower20', (.42, .45, 1.0), 9.0, flow=(.09, .9))
    M_PUR = _emat('TokPurple20', (.62, .3, 1.0), 10.0)
    M_GL = pbsdf('TokGlass20', (.7, .8, .9), 0, .05); M_GL.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = .92
    # plasma ring inside a vessel cut away at four viewports, so the glowing plasma is always visible
    Tor('TokPlasma', (XT, YT, ZT), R, .3, M_PLA, ms=96, ns=24)
    Tor('TokPlasmaHalo', (XT, YT, ZT), R, .36, M_PUR, ms=96, ns=16).visible_glossy = False
    for k in range(4):
        a0 = 90 * k + 20; a1 = 90 * k + 70; n_ = 18; V = []; F = []
        for i in range(n_ + 1):
            a = math.radians(a0 + (a1 - a0) * i / n_)
            for j in range(24):
                b = 2 * math.pi * j / 24; rr = R + r * math.cos(b); V.append((XT + rr * math.cos(a), YT + rr * math.sin(a), ZT + r * math.sin(b)))
        for i in range(n_):
            for j in range(24): F.append((i * 24 + j, i * 24 + (j + 1) % 24, (i + 1) * 24 + (j + 1) % 24, (i + 1) * 24 + j))
        mk(f'TokVessel{k}', V, F, M_VES, smooth=True)
        o = Tor(f'TokPort{k}', (XT, YT, ZT), R, r - .02, M_GL, ms=96, ns=16)   # glass port over the 40 deg gap between vessel segments
        bm = _bm.new(); bm.from_mesh(o.data)
        dele = [f for f in bm.faces if abs(((math.degrees(math.atan2(f.calc_center_median().y, f.calc_center_median().x)) - (90 * k + 90) + 180) % 360) - 180) > 21]
        _bm.ops.delete(bm, geom=dele, context='FACES'); bm.to_mesh(o.data); bm.free()
    # 16 D-shaped toroidal field coils
    for k in range(16):
        a = 360 * k / 16; c_ = (XT + R * math.cos(math.radians(a)), YT + R * math.sin(math.radians(a)), ZT)
        Tor(f'TokCoil{k:02d}', c_, r + .2, .07, M_COIL, rot=(90, 0, a), ms=40, ns=8)
    # central solenoid floor-to-ceiling with glowing bands, top and bottom poloidal rings
    Cyl('TokSolenoid', (XT, YT, (zf + zc) / 2), .42, zc - zf - .1, M_VES, v=48)
    for k in range(7): Cyl(f'TokSolBand{k}', (XT, YT, zf + .5 + k * (zc - zf - 1.0) / 6), .44, .06, M_PUR, v=48)
    for z_, rr in ((ZT + .82, R + .1), (ZT - .82, R + .1)): Tor(f'TokPF{z_:.1f}', (XT, YT, z_), rr, .06, M_COIL, ms=96, ns=10)
    for z_, rr in ((ZT + .55, R + r + .45), (ZT - .55, R + r + .45)): Tor(f'TokPFO{z_:.1f}', (XT, YT, z_), rr, .07, M_COIL, ms=96, ns=10)
    # fission blanket: 8 segments around the outside with Cherenkov-blue slots (the hybrid part)
    for k in range(8):
        a = math.radians(360 * k / 8 + 22.5); rr = R + r + .32
        bx = Box(f'TokBlanket{k}', (XT + rr * math.cos(a), YT + rr * math.sin(a), ZT), (.36, .9, 1.1), M_BLK, rot=(0, 0, math.degrees(a)))
        for j in range(3): Box(f'TokBlanketSlot{k}_{j}', (XT + (rr + .185) * math.cos(a), YT + (rr + .185) * math.sin(a), ZT - .3 + j * .3), (.02, .7, .05), M_CHER, rot=(0, 0, math.degrees(a)))
    # plinth, legs and a lit floor ring
    Cyl('TokPlinth', (XT, YT, zf + .12), R + r + .5, .24, M_VES, v=96)
    Tor('TokPlinthGlow', (XT, YT, zf + .245), R + r + .47, .02, M_PUR, ms=128, ns=6)
    for k in range(4):
        a = math.radians(45 + 90 * k); p_ = (XT + (R + .1) * math.cos(a), YT + (R + .1) * math.sin(a))
        Cyl(f'TokLeg{k}', (p_[0], p_[1], (zf + .24 + ZT - r) / 2), .12, ZT - r - zf - .2, M_VES, v=20)
    # power takeoff: four busbar conduits from the blanket down into a glass-topped floor duct, forward to the bulkhead junction, up and out to the ship
    xf = (_wb(sh)[0].x - .25) if sh else -12.9
    Box('TokDuct', ((XT + R + r + .5 + xf) / 2, 0, zf + .07), (xf - (XT + R + r + .5), .8, .14), M_VES)
    Box('TokDuctGlass', ((XT + R + r + .5 + xf) / 2, 0, zf + .145), (xf - (XT + R + r + .5) - .05, .7, .01), M_GL)
    for sy in (-1, 1):
        a = math.radians(-35 * sy); bx_ = XT + (R + r + .5) * math.cos(a); by_ = YT + (R + r + .5) * math.sin(a)
        _tube(f'TokFeed{sy}', [(bx_, by_, ZT - .2), (bx_ + .45, by_ * .6, zf + .6), (XT + R + r + .55, -.18 * sy, zf + .08), (xf - .3, -.18 * sy, zf + .08), (xf - .3, -.18 * sy, zf + .3)], .07, M_PWR)
        a = math.radians(180 + 40 * sy); bx_ = XT + (R + r + .5) * math.cos(a); by_ = YT + (R + r + .5) * math.sin(a)
        _tube(f'TokFeedAft{sy}', [(bx_, by_, ZT + .2), (bx_, by_, zc - .35), (bx_ + .4, .8 * sy, zc - .35), (xf - .3, .8 * sy, zc - .35), (xf + .3, .8 * sy, zc - .35)], .08, M_PWR)
    Box('TokJunction', (xf - .3, 0, (zf + zc) / 2), (.5, 1.4, zc - zf - .3), M_BLK)
    for j in range(6): Box(f'TokJunctionBar{j}', (xf - .56, -.55 + j * .22, (zf + zc) / 2), (.02, .06, zc - zf - .6), M_PWR)
    _tube('TokFeedUp', [(xf - .3, 0, zf + .35), (xf - .3, 0, zc - .2), (xf + .3, 0, zc - .2)], .1, M_PWR)
    # light from the plasma
    for k in range(4):
        a = math.radians(90 * k + 45); ld = bpy.data.lights.new(f'TokLight{k}', 'POINT'); ld.energy = 260; ld.color = (.55, .5, 1.0); ld.shadow_soft_size = .6
        lo_ = bpy.data.objects.new(f'TokLight{k}', ld); col.objects.link(lo_); lo_.location = (XT + R * math.cos(a), YT + R * math.sin(a), ZT + .9)
    print('MODEL v20 reactor: removed old core parts', gone, 'tokamak at', XT, YT, round(ZT, 2), 'floor', round(zf, 2), 'ceiling', round(zc, 2), 'bulkhead x', round(xf, 2))

for nm_, fn_ in (('planks', v20_planks), ('sponsons', v20_sponsons), ('nose', v20_nose), ('hatch', v20_hatch_closed), ('keel deck', v20_keel_deck), ('reactor', v20_reactor)): _v20(nm_, fn_)
