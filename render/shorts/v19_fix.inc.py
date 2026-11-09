# ---------------------------------------------------------------- v19 USER FIXES (2026-11-09): flat floor, planks, dome skin + fairing, clean top
def _v19(step, fn):
    t_ = _tm0.time()
    try: fn(); print('MODEL v19', step, 'ok', round(_tm0.time() - t_, 1), 's')
    except Exception:
        import traceback; print('Error v19', step); traceback.print_exc()
def _bbc(o):
    ws = [o.matrix_world @ Vector(v) for v in o.bound_box]; return sum(ws, Vector()) / 8, min(w.z for w in ws), max(w.z for w in ws), ws

def v19_floor():
    # hall floor is one flat surface now (holes removed at build); the hatch + holo well become flush closed panels with a lit outline
    for o in list(bpy.data.objects):
        if o.name.startswith(('HatchLeaf', 'HatchTrim', 'HatchArmour', 'HatchSeam', 'HatchEmblem', 'Anim_HatchLeaf', 'HoloTableRim')): _rm(o)
    for o in bpy.data.objects:
        if o.name.startswith('HatchFrame'): o.location.z = Z0 + .002
    Box('HatchFlushPanel', ((HX0 + HX1) / 2, 0, Z0 + .0015), (HX1 - HX0, 2 * HHW, .003), M_HATCH)
    Box('HatchFlushSeam', ((HX0 + HX1) / 2, 0, Z0 + .0035), (HX1 - HX0 - .1, .02, .002), M_CYAN)
    Cyl('HatchFlushEmblem', ((HX0 + HX1) / 2, 0, Z0 + .0035), .17, .002, M_GOLD, v=32)
    t_ = bpy.data.objects.get('HoloTableTop')
    if t_: t_.location.z = Z0 + .0015; t_.scale.z = .15
    ann('HoloFlushRing', .70, .745, 0, 360, Z0, Z0 + .004, M_CYAN, step=4)

def v19_planks():
    n = 0
    for o in list(bpy.data.objects):
        if o.name.startswith(('SofaBase2', 'SofaSeat2', 'SofaBack2', 'SofaArm2_', 'SofaBase3', 'SofaSeat3', 'SofaBack3', 'SofaArm3_')): _rm(o); n += 1
    print('MODEL v19 removed sofa parts at the stair feet', n)
    for o in list(bpy.data.objects):     # report (and drop) any other thin slab floating just above the hall floor near the stair feet
        if o.type != 'MESH': continue
        c, z0_, z1_, ws = _bbc(o); r_ = math.hypot(c.x - HC.x, c.y - HC.y); a_ = abs(math.degrees(math.atan2(c.y - HC.y, c.x - HC.x)))
        if 4.8 < r_ < 7.4 and 50 < a_ < 100 and Z0 + .04 < z0_ < Z0 + .9 and z1_ - z0_ < .14 and not o.name.startswith(('Stair', 'Gallery', 'Hole', 'UnderGal', 'Door', 'Floor')):
            print('MODEL v19 FLOATER', o.name, round(z0_ - Z0, 2), round(r_, 2), round(a_, 1)); _rm(o)

FW19 = 3.0; R19A = ROUT - 1.2
def _hz(x, y):
    h = hull_hit(x, y)
    return (h[0].z, h[1]) if h else (None, None)
def v19_dome():
    bl = bpy.data.objects.get('HallBlister')
    if bl:
        for i, s_ in enumerate(bl.material_slots):
            if i != 1: s_.material = M18_TI
    # fairing: tangent off the dome (r = ROUT-1.2) down into the hull skin (r = ROUT+3), hermite in r, never below the hull
    NA, NR = 180, 22; V = []; F = []; lo = 0
    dd = lambda r: (ZDO - ZSO) * (-r / ROUT ** 2) / math.sqrt(max(1e-4, 1 - (r / ROUT) ** 2))
    z1, s1 = dome_out(R19A), dd(R19A)
    for j in range(NA):
        a = j * 360.0 / NA; t = math.radians(a); dx, dy = math.cos(t), math.sin(t)
        r2 = ROUT + FW19; z2, n2 = _hz(HC.x + r2 * dx, HC.y + r2 * dy)
        if z2 is None: z2, s2 = ZSO - 1.0, 0.0
        else: s2 = -(n2.x * dx + n2.y * dy) / max(abs(n2.z), .2)
        L = r2 - R19A
        for i in range(NR):
            u = i / (NR - 1); r = R19A + L * u
            h00, h10, h01, h11 = 2*u**3 - 3*u**2 + 1, u**3 - 2*u**2 + u, -2*u**3 + 3*u**2, u**3 - u**2
            z = h00 * z1 + h10 * L * s1 + h01 * z2 + h11 * L * s2
            if r < ROUT: z = max(z, dome_out(r) + .01)
            else:
                zh, _n = _hz(HC.x + r * dx, HC.y + r * dy)
                if zh is not None: z = max(z, zh + .015)
                else: lo += 1
            V.append((HC.x + r * dx, HC.y + r * dy, z))
    for j in range(NA):
        for i in range(NR - 1):
            a_, b_ = j * NR + i, ((j + 1) % NA) * NR + i; F.append((a_, a_ + 1, b_ + 1, b_))
    mk('DomeFairing', V, F, M18_TI, smooth=True); print('MODEL v19 dome fairing verts', len(V), 'no-hull samples', lo, 'dome top', round(z1, 2), 'slope', round(s1, 2))

def v19_clean_top():
    keep = ('Hull', 'HallBlister', 'DomeFairing', 'Skylight', 'HallDome', 'Pad', 'Cam', 'Sun')
    gone = []
    for o in list(bpy.data.objects):
        if o.type != 'MESH' or o.name.startswith(keep): continue
        c, z0_, z1_, ws = _bbc(o); r_ = math.hypot(c.x - HC.x, c.y - HC.y)
        if r_ > ROUT + FW19 + 1.0 or c.z < ZSO - 2.5: continue
        if r_ < ROUT: on = SKY_R + .2 < r_ and c.z > dome_out(r_) - .15
        else:
            zh, _n = _hz(c.x, c.y); on = zh is not None and c.z > zh - .1
        if on: gone.append(o.name); _rm(o)
    print('MODEL v19 top-skin parts removed', len(gone), gone[:60])
for nm_, fn_ in (('floor', v19_floor), ('planks', v19_planks), ('dome', v19_dome), ('clean top', v19_clean_top)): _v19(nm_, fn_)
