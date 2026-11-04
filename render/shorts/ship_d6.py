"""Procedural hard-surface build of the 'D6' delta fighter concept (spine + swept horseshoe frame + twin pods).
blender -b any.blend -P render/shorts/ship_d6.py -- OUTDIR ASSETDIR START END
Outputs: ship_d6.glb, ship_d6.blend, hero_a.png, hero_b.png, top.png, side.png, front.png
Nose points +Y. Units ~ metres (length about 21.5).
"""
import math, os, sys, urllib.request
import bpy, bmesh
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
OUT, AD = a[0], a[1]
os.makedirs(OUT, exist_ok=True)
SPP = int(os.environ.get('SPP', '64'))
hdr = os.path.join(AD, 'small_harbour_sunset_2k.hdr')
if not os.path.exists(hdr):
    try: urllib.request.urlretrieve('https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/small_harbour_sunset_2k.hdr', hdr)
    except Exception as e: print('HDR fail', e); hdr = None

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
col = sc.collection

# ---------------------------------------------------------------- materials
def mat(name, base, metal=.6, rough=.35, emit=None, estr=0, bump=0, panel_scale=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*base, 1); p.inputs['Metallic'].default_value = metal; p.inputs['Roughness'].default_value = rough
    if emit:
        p.inputs['Emission Color'].default_value = (*emit, 1); p.inputs['Emission Strength'].default_value = estr
    if bump:
        tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (panel_scale, panel_scale, panel_scale)
        br = nt.nodes.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = 1.0
        br.inputs['Mortar Size'].default_value = .012; br.inputs['Brick Width'].default_value = 1.6; br.inputs['Row Height'].default_value = .7
        br.inputs['Color1'].default_value = (1, 1, 1, 1); br.inputs['Color2'].default_value = (.9, .9, .9, 1); br.inputs['Mortar'].default_value = (0, 0, 0, 1)
        nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3
        bm = nt.nodes.new('ShaderNodeBump'); bm.inputs['Strength'].default_value = bump; bm.inputs['Distance'].default_value = .02
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = .25
        nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], br.inputs['Vector'])
        nt.links.new(br.outputs['Fac'], bm.inputs['Height'])
        nt.links.new(bm.outputs['Normal'], p.inputs['Normal'])
        # subtle grime variation on the colour
        nt.links.new(mp.outputs['Vector'], nz.inputs['Vector'])
        mix.inputs[6].default_value = (*base, 1); nt.links.new(nz.outputs['Color'], mix.inputs[7])
        nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    return m
M_HULL = mat('Hull', (.60, .62, .64), .55, .32, bump=.35, panel_scale=.55)
M_DARK = mat('HullDark', (.13, .14, .16), .5, .45, bump=.25, panel_scale=.9)
M_TRIM = mat('TrimYellow', (.85, .62, .04), .3, .4)
M_GLOW = mat('Exhaust', (1, .45, .15), 0, .5, emit=(1, .42, .12), estr=40)
M_GLASS = mat('Canopy', (.02, .025, .03), .2, .08)
M_RED = mat('Accent', (.7, .05, .04), .2, .4)

# ---------------------------------------------------------------- loft helper
PROF_SPINE = [(1, 0), (.72, .55), (.25, .85), (0, 1), (-.25, .85), (-.72, .55), (-1, 0), (-.7, -.5), (0, -.62), (.7, -.5)]
PROF_SLAB = [(1, 0), (.8, .7), (-.8, .7), (-1, 0), (-.8, -.6), (.8, -.6)]
PROF_POD = [(math.cos(i / 8 * 2 * math.pi), math.sin(i / 8 * 2 * math.pi)) for i in range(8)]

def loft(name, stations, prof, material, caps=True, tangent=None):
    """stations: list of (Vector centre, w, h). Section plane perpendicular to the path tangent in XY; up = Z."""
    bm = bmesh.new(); rings = []
    n = len(stations)
    for i, (c, w, h) in enumerate(stations):
        c = Vector(c)
        if tangent: t = Vector(tangent)
        else:
            p0 = Vector(stations[max(i - 1, 0)][0]); p1 = Vector(stations[min(i + 1, n - 1)][0]); t = p1 - p0
        t.z = 0
        if t.length < 1e-6: t = Vector((0, 1, 0))
        t.normalize(); s = Vector((t.y, -t.x, 0)); up = Vector((0, 0, 1))
        rings.append([bm.verts.new(c + s * px * w + up * pz * h) for px, pz in prof])
    k = len(prof)
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(k):
            try: bm.faces.new((r0[j], r0[(j + 1) % k], r1[(j + 1) % k], r1[j]))
            except ValueError: pass
    if caps:
        for r, rev in ((rings[0], True), (rings[-1], False)):
            try: bm.faces.new(list(reversed(r)) if rev else r)
            except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); col.objects.link(ob); me.materials.append(material)
    return ob

def mirror_x(ob):
    m = ob.modifiers.new('MirX', 'MIRROR'); m.use_axis[0] = True; m.use_bisect_axis[0] = False; m.use_clip = False
    return ob

def box(name, centre, size, material, rot=(0, 0, 0), bev=.06):
    bpy.ops.mesh.primitive_cube_add(size=1, location=centre, rotation=[math.radians(r) for r in rot])
    ob = bpy.context.active_object; ob.name = name; ob.scale = size
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True); ob.data.materials.append(material)
    return ob

# ---------------------------------------------------------------- 1. central spine / fuselage
spine = loft('Spine', [
    ((0, -2.2, .05), .35, .28), ((0, -1.4, .05), .75, .55), ((0, 0, .05), 1.15, .78), ((0, 2.5, .08), 1.45, .95),
    ((0, 6, .1), 1.55, 1.0), ((0, 10, .06), 1.35, .86), ((0, 13.5, 0), 1.05, .66), ((0, 16.5, -.06), .68, .44),
    ((0, 18.5, -.12), .36, .25), ((0, 19.6, -.16), .12, .1), ((0, 19.9, -.17), .02, .02)], PROF_SPINE, M_HULL)
# dorsal armour plate (darker) along the spine top
dorsal = loft('DorsalPlate', [((0, -.6, .82), .5, .14), ((0, 3, .99), .62, .16), ((0, 8, .98), .58, .15), ((0, 12, .72), .42, .12), ((0, 14.4, .55), .2, .08)], PROF_SLAB, M_DARK)
# canopy
canopy = loft('Canopy', [((0, 11.0, .72), .05, .05), ((0, 11.6, .78), .32, .2), ((0, 12.6, .7), .34, .2), ((0, 13.6, .58), .22, .14), ((0, 14.1, .5), .04, .04)], PROF_SPINE, M_GLASS)
# yellow nose band
band = loft('NoseBand', [((0, 16.85, -.07), .66, .43), ((0, 17.2, -.08), .62, .41)], PROF_SPINE, M_TRIM)
band.scale = (1.035, 1, 1.05)
# red nose detail
box('NoseAccent', (0, 15.6, .35), (.18, .5, .06), M_RED)
# spine exhaust
spine_noz = loft('SpineNozzle', [((0, -2.35, .05), .28, .22), ((0, -2.25, .05), .32, .25)], PROF_POD, M_GLOW)

# ---------------------------------------------------------------- 2. swept horseshoe frame (right arm, mirrored)
arm = loft('FrameArm', [
    ((4.7, -1.6, .02), 1.25, .42), ((5.05, .2, .04), 1.45, .5), ((5.1, 2.6, .05), 1.4, .5), ((4.6, 5.6, .04), 1.2, .44),
    ((3.6, 8.6, .02), 1.0, .38), ((2.4, 11.4, 0), .82, .33), ((1.25, 13.9, -.02), .62, .28), ((.7, 15.0, -.03), .4, .2)], PROF_SLAB, M_HULL)
mirror_x(arm)
# inner dark rail on the arm's top
rail = loft('ArmRail', [((4.5, -1.2, .45), .5, .08), ((4.65, 2.5, .53), .55, .09), ((3.5, 8.5, .4), .4, .07), ((1.6, 13.0, .27), .25, .05)], PROF_SLAB, M_DARK)
mirror_x(rail)
# tail "ear" blocks: chunky angular end caps on the arms
ear = loft('TailEar', [((5.0, -2.6, .05), .9, .45), ((5.25, -1.9, .1), 1.5, .62), ((5.35, .4, .12), 1.65, .7), ((5.2, 1.6, .1), 1.45, .62), ((5.05, 2.4, .06), 1.1, .5)], PROF_SLAB, M_DARK)
mirror_x(ear)
ear_trim = loft('EarTrim', [((5.3, .55, .12), 1.68, .72), ((5.3, .8, .12), 1.68, .72)], PROF_SLAB, M_TRIM)
ear_trim.scale = (1, 1, 1.02); mirror_x(ear_trim)
# ear exhaust slots
slot = loft('EarGlow', [((5.0, -2.7, .05), .55, .18), ((5.0, -2.62, .05), .6, .2)], PROF_SLAB, M_GLOW)
mirror_x(slot)
# rear cross brace connecting arms to the spine (low, under the pods)
brace = loft('RearBrace', [((-4.4, -.9, -.12), .55, .16), ((0, -.9, -.12), .55, .16), ((4.4, -.9, -.12), .55, .16)], PROF_SLAB, M_DARK, tangent=(1, 0, 0))
brace.rotation_euler = (0, 0, 0)

# ---------------------------------------------------------------- 3. twin top nacelles on pylons
pod = loft('Nacelle', [
    ((2.05, -1.1, .62), .42, .42), ((2.05, -.7, .62), .56, .56), ((2.05, 1.5, .62), .6, .6), ((2.05, 4.5, .62), .58, .58),
    ((2.05, 6.0, .58), .42, .42), ((2.05, 6.6, .55), .2, .2)], PROF_POD, M_DARK)
mirror_x(pod)
pod_cowl = loft('NacelleCowl', [((2.05, -.4, .7), .64, .55), ((2.05, 3.8, .7), .64, .55)], PROF_SLAB, M_HULL)
mirror_x(pod_cowl)
pod_band = loft('NacelleBand', [((2.05, 4.0, .62), .615, .615), ((2.05, 4.3, .62), .615, .615)], PROF_POD, M_TRIM)
mirror_x(pod_band)
pod_glow = loft('NacelleGlow', [((2.05, -1.2, .62), .36, .36), ((2.05, -1.1, .62), .4, .4)], PROF_POD, M_GLOW)
mirror_x(pod_glow)
pylon = box('Pylon', (1.45, 2.2, .3), (1.1, 3.6, .3), M_DARK)
mirror_x(pylon)
# pod-to-arm struts (thin), so the pods read as bridging spine and frame like the concept's isometric
strut = box('Strut', (3.35, .8, .25), (2.4, .7, .16), M_HULL, rot=(0, 0, -8))
mirror_x(strut)

# ---------------------------------------------------------------- 4. chin intakes + small details
intake = loft('Intake', [((1.0, 7.6, -.55), .32, .22), ((1.05, 9.5, -.58), .42, .28), ((1.0, 12.0, -.48), .34, .22), ((.8, 13.4, -.38), .18, .12)], PROF_SLAB, M_DARK)
mirror_x(intake)
intake_mouth = loft('IntakeMouth', [((1.05, 13.0, -.42), .2, .1), ((1.0, 13.2, -.41), .16, .08)], PROF_SLAB, M_GLASS)
mirror_x(intake_mouth)
for i, y in enumerate((3.0, 5.5, 8.0)):
    g = box(f'Greeble{i}', (.55, y, 1.02 - i * .03), (.22, .7, .06), M_DARK); mirror_x(g)
# small antennas on the frame tips
for y in (14.2,):
    ant = box('Antenna', (1.05, y, .3), (.04, 1.4, .04), M_DARK, rot=(8, 0, 0)); mirror_x(ant)

# ---------------------------------------------------------------- finishing: bevel + smooth-by-angle on everything
ship = [o for o in col.objects if o.type == 'MESH']
for o in ship:
    bv = o.modifiers.new('Bevel', 'BEVEL'); bv.width = .03; bv.segments = 2; bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(35); bv.harden_normals = False
    if 'MirX' in o.modifiers:  # keep mirror before bevel
        o.modifiers.move(o.modifiers.find('MirX'), 0)
    wn = o.modifiers.new('WN', 'WEIGHTED_NORMAL'); wn.keep_sharp = True
    for p in o.data.polygons: p.use_smooth = True
    try:
        o.data.set_sharp_from_angle(angle=math.radians(40))
    except Exception: pass
root = bpy.data.objects.new('Ship_D6', None); col.objects.link(root)
for o in ship: o.parent = root
print('MODEL parts', len(ship), 'tris', sum(len(o.data.polygons) for o in ship))

# ---------------------------------------------------------------- export model files
bpy.ops.object.select_all(action='DESELECT')
for o in ship: o.select_set(True)
root.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'ship_d6.glb'), export_format='GLB', use_selection=True, export_apply=True)

# ---------------------------------------------------------------- render setup
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
nt = w.node_tree; bg = nt.nodes['Background']
if hdr:
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(hdr)
    mp = nt.nodes.new('ShaderNodeMapping'); tc = nt.nodes.new('ShaderNodeTexCoord'); mp.inputs['Rotation'].default_value[2] = math.radians(120)
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
sund = bpy.data.lights.new('Sun', 'SUN'); sund.energy = 4; sund.angle = math.radians(2); sund.color = (1, .86, .7)
sun = bpy.data.objects.new('Sun', sund); col.objects.link(sun); sun.rotation_euler = (math.radians(55), 0, math.radians(140))
cd = bpy.data.cameras.new('Cam'); cam = bpy.data.objects.new('Cam', cd); col.objects.link(cam); sc.camera = cam
r = sc.render; r.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SPP; sc.cycles.use_denoising = True
r.image_settings.file_format = 'PNG'; sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'ship_d6.blend'))

C = Vector((0, 8.5, .2))
def shoot(name, loc, ortho=None, rot=None, res=(1600, 900), lens=50, plain=False):
    r.resolution_x, r.resolution_y = res
    cd.type = 'ORTHO' if ortho else 'PERSP'
    if ortho: cd.ortho_scale = ortho
    cd.lens = lens; cd.clip_end = 500
    cam.location = Vector(loc)
    cam.rotation_euler = rot if rot else (C - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bg.inputs['Strength'].default_value = .15 if plain else 1.0
    r.film_transparent = False
    if plain:  # dark flat backdrop for the blueprint views, HDRI still lights
        lp = nt.nodes.get('LP') or nt.nodes.new('ShaderNodeLightPath'); lp.name = 'LP'
    r.filepath = os.path.join(OUT, name + '.png'); bpy.ops.render.render(write_still=True)
shoot('hero_a', C + Vector((-17, 15, 11)), lens=55)
shoot('hero_b', C + Vector((16, -14, 8)), lens=55)
shoot('top', (0, 8.5, 40), ortho=24, rot=(0, 0, math.radians(90)), plain=True)
shoot('side', (40, 8.5, .2), ortho=24, rot=(math.radians(90), 0, math.radians(90)), plain=True)
shoot('front', (0, 50, .2), ortho=13, rot=(math.radians(90), 0, math.radians(180)), plain=True)
print('DONE')
