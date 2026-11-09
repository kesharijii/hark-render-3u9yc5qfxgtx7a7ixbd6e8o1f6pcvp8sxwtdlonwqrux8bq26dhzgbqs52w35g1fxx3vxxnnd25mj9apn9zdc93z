# ---------------------------------------------------------------- v19 FULL INSPECTION TOUR (12 fps; frames interleaved across parts)
import json as _js
FPS19 = 12; SF19 = 240
def _cr(pts, u):     # catmull-rom through pts, u in [0,1]
    P_ = [Vector(p) for p in pts]
    if len(P_) == 1: return P_[0]
    n = len(P_) - 1; x = min(max(u, 0), 1) * n; i = min(int(x), n - 1); t = x - i
    p0, p1, p2, p3 = P_[max(i - 1, 0)], P_[i], P_[i + 1], P_[min(i + 2, n)]
    return .5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
def ez(u): return u * u * (3 - 2 * u)
def path(cams, tgts, lens, pad=False):
    return lambda u: (_cr(cams, ez(u)), _cr(tgts, ez(u)), lens, pad)
def orbit19(c, r0, r1, z0, z1, a0, a1, lens, tz=None, pad=False, ease=False):
    def f(u):
        v = ez(u) if ease else u; a = math.radians(a0 + (a1 - a0) * v); r = r0 + (r1 - r0) * v
        return Vector((c[0] + r * math.cos(a), c[1] + r * math.sin(a), z0 + (z1 - z0) * v)), Vector((c[0], c[1], c[2] if tz is None else tz)), lens, pad
    return f
def room19(prefs=None, pt=None, dz=1.1, sweep=260, lens=16, rmax=3.2, look_dz=.25):
    # orbit inside a room around its key object: radius per direction from 72 measured rays (keeps the camera off the walls)
    c = Vector(pt) if pt else _ctr(prefs)
    if c is None: c = Vector((0, 0, 0)); print('Error tour room none', prefs)
    dg = bpy.context.evaluated_depsgraph_get(); e = c + Vector((0, 0, dz)); D = []
    for k in range(72):
        a = 2 * math.pi * k / 72; hit, p_, *_ = sc.ray_cast(dg, e, Vector((math.cos(a), math.sin(a), 0)), distance=12); D.append((p_ - e).length if hit else 12)
    Dm = [min(D[(k + j) % 72] for j in range(-3, 4)) for k in range(72)]
    kb = max(range(72), key=lambda k: sum(Dm[(k + j) % 72] for j in range(-12, 13)))
    def f(u):
        a = kb * 5 - sweep / 2 + sweep * ez(u); k = int(round(a / 5)) % 72; R = min(max(Dm[k] - .45, .55), rmax)
        t = math.radians(a); return e + Vector((R * math.cos(t), R * math.sin(t), 0)), c + Vector((0, 0, look_dz)), lens, True
    return f
def ring_walk(r, z, a0, a1, lens, ahead=45, rt=6.5, tz=None, pad=True):
    def f(u):
        a = a0 + (a1 - a0) * u; b = a + ahead * (1 if a1 > a0 else -1)
        return Vector(pol(r, a, z)), Vector(pol(rt, b, z - .35 if tz is None else tz)), lens, pad
    return f
EYE = 1.62; KE = KF + 1.55
CORE = _ctr(('MiniCore', 'CoreCapsule', 'Core', 'Pedestal')) or Vector((EX, 0, ZA + 1.0))
SHOTS = [
 ('EXTERIOR  |  full orbit', 24, orbit19((0, 0, 0), 64, 58, 15, 7, -40, 320, 32, tz=0)),
 ('EXTERIOR  |  low orbit', 14, orbit19((0, 0, -1), 44, 44, -3.4, -2.6, 200, 20, 30)),
 ('EXTERIOR  |  drone over the spine', 12, path([(44, 4, 22), (6, 3, 21), (-38, 4, 20)], [(22, 0, 1), (-8, 0, 1.5), (-26, 0, 1)], 24)),
 ('EXTERIOR  |  dome + fairing', 12, orbit19((HC.x, 0, 0), 17, 15, 13, 11, -60, 230, 28, tz=ZSO)),
 ('EXTERIOR  |  engines', 10, path([(-52, -15, 4), (-46, 0, 7), (-42, 13, 3)], [(-29, -2, 1.5), (-29, 0, 1.5), (-29, 2, 1.5)], 30)),
 ('EXTERIOR  |  nose + canopy', 10, path([(46, -13, 3), (42, 0, 6), (40, 13, 4)], [(24, 0, 1), (24, 0, 1.5), (24, 0, 1)], 30)),
 ('EXTERIOR  |  belly + wings', 10, path([(22, -23, -4.8), (-2, -24, -4.6), (-26, -23, -4.8)], [(22, 0, -2.6), (-2, 0, -2.4), (-26, 0, -2.6)], 22, True)),
 ('ENTRANCE  |  belly hatch', 10, path([(14, -9, -4.7), (5, -3, -4.9), (RH_C[0] + 1.6, -.4, -5.0)], [(RH_C[0], 0, -4.2), (RH_C[0], 0, -3.8), (RH_C[0], 0, KB + .2)], 20, True)),
 ('KEEL BAY  |  entrance deck', 12, ring_walk(3.4, KE, -20, 300, 16, ahead=60, rt=5.0, tz=KF + .9)),
 ('CENTRAL HALL  |  walk', 20, ring_walk(2.9, Z0 + EYE, 0, 360, 18, ahead=55, rt=6.0, tz=Z0 + 1.2)),
 ('CENTRAL HALL  |  drone rise to the dome', 14, lambda u: (Vector(pol(1.6 - .7 * u, 540 * u, Z0 + 1.8 + (ZD - 1.4 - Z0 - 1.8) * ez(u))), Vector(pol(5.2, 540 * u + 120, ZG - .4 * u)), 16, True)),
 ('HALL  |  port stair up to the gallery', 10, lambda u: (Vector(pol(6.12, 68 - 56 * ez(u), Z0 + EYE + (ZG - Z0) * min(max((68 - 56 * ez(u) - 62) / (14 - 62), 0), 1))), Vector(pol(6.0, 68 - 56 * ez(u) - 25, Z0 + EYE + (ZG - Z0) * min(max((68 - 56 * ez(u) - 87) / (14 - 62), 0), 1) - .3)), 18, True)),
 ('GALLERY  |  ring walk past every room', 20, ring_walk(4.6, ZG + EYE, 0, 360, 18, ahead=35, rt=6.8, tz=ZG + 1.2)),
 ('GALLERY  |  workshop', 8, lambda u: (Vector(pol(4.7, 138 + 28 * ez(u), ZG + 1.6)), Vector(pol(6.7, 152, TZ - .35)), 20, True)),
 ('MESS  |  galley', 12, room19(('MessTable', 'MessPed', 'MessThreshold'), dz=1.2)),
 ('MED BAY', 12, path([(-6.3, -8.0, Z0 + EYE), (-2.6, -8.1, Z0 + EYE), (0.3, -8.0, Z0 + EYE)], [(-3.6, -10.6, Z0 + .7), (-5.1, -10.4, Z0 + .6), (-6.4, -10.4, Z0 + .8)], 18, True)),
 ('REACTOR ROOM', 16, room19(pt=tuple(CORE), dz=1.2, sweep=300, rmax=3.0, look_dz=0)),
 ('CREW CORRIDOR', 14, lambda u: (Vector((4.2 + 7.8 * ez(u), 0, Z0 + EYE)), Vector((8.2 + 7.8 * ez(u), 2.6 * math.sin(4 * math.pi * u), Z0 + 1.3)), 18, True)),
 ('CREW CABIN', 10, room19(('Cabin0Bed', 'Cabin1Bed', 'Bed'), dz=1.1, rmax=2.2)),
 ('BRIDGE  |  walk to the pilots', 14, path([(12.0, 0, Z0 + EYE), (14.0, 0, ZB + 1.7), (16.6, -1.2, ZB + 1.7), (px - 1.2, -.05, ZB + 1.7), (px - .45, .2, ZB + 1.5)], [(16, 0, ZB + 1.0), (18, 0, ZB + 1.0), (nose_end + 1, 0, ZB + 1.1), (px + 1.2, .3, ZB + .9), (px + .45, .9, ZB + .8)], 18, True)),
 ('BRIDGE  |  lobby', 8, room19(pt=(16, 0, ZB + .45), dz=1.25, sweep=220)),
 ('BRIDGE  |  pilot stations', 8, room19(pt=(px, 0, ZB + .6), dz=1.0, sweep=200, rmax=2.0)),
 ('EXTERIOR  |  pull-back', 12, path([(-44, -26, 5), (-60, -38, 10), (-74, -46, 16)], [(0, 0, 0), (2, 0, 0.5), (4, 0, 1)], 30)),
]
NF19 = sum(int(d * FPS19) for _, d, _ in SHOTS)
def tour19_at(f):
    acc = 0
    for cap, d, fn in SHOTS:
        n = int(d * FPS19)
        if f <= acc + n: return cap, fn((f - acc - 1) / max(n - 1, 1))
        acc += n
def tour19_render(part, nparts, deadline):
    sc.cycles.samples = SPP; raised(False); set_cut2(0); sc.frame_set(SF19)
    for o in CEIL: o.hide_render = False
    r.image_settings.file_format = 'JPEG'; r.image_settings.quality = 90; r.use_persistent_data = True; r.resolution_x, r.resolution_y = 1280, 720
    sc.cycles.max_bounces = 4
    mine = [f for f in range(1, NF19 + 1) if (f - 1) % nparts == part]
    nb = max(1, (len(mine) - 1).bit_length()); order = sorted(range(len(mine)), key=lambda i: int(format(i, f'0{nb}b')[::-1], 2))
    caps = []; acc = 0
    for cap, d, _ in SHOTS: n = int(d * FPS19); caps.append({'cap': cap, 'start': acc + 1, 'end': acc + n}); acc += n
    if part == 0:
        with open(os.path.join(OUT, 'tour19_shots.json'), 'w') as fh: _js.dump({'fps': FPS19, 'nframes': NF19, 'shots': caps}, fh)
    print('TOUR19 frames', NF19, 'part', part, 'of', nparts, 'mine', len(mine))
    done = 0
    for i in order:
        if _tm0.time() - _TS > deadline: print('TIMING tour19 deadline after', done, 'frames'); break
        f = mine[i]; cap, (loc, tgt, lens, pad) = tour19_at(f)
        try:
            ground.hide_render = not pad
            loc = clear_cam(f'f{f}', tuple(loc), tuple(tgt)) if pad else tuple(loc)
            look(loc, tgt, lens); r.filepath = os.path.join(OUT, f'f_{f:04d}.jpg'); bpy.ops.render.render(write_still=True); done += 1
            if done % 10 == 1: print('RENDER tour19', f, cap, 'TIMING', round(_tm0.time() - _TS))
        except Exception:
            import traceback; print('Error tour19 frame', f); traceback.print_exc()
    print('TIMING tour19 done', done, 'of', len(mine), round(_tm0.time() - _TS))
