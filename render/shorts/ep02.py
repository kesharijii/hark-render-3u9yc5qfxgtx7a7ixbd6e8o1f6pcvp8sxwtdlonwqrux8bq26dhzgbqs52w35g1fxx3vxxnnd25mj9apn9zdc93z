"""Short 02 - "Careful What You Wish".

blender -b host.blend -P render/shorts/ep02.py -- OUTDIR ASSETDIR START END
Beat frames come from the voice timings (shorts/ep02/timings.json), so a re-voiced line re-times the film.

  A  hook       close on her face, night            "You made three wishes last night..."
  B  wish one   rainy street, giant clock; snap -> rain and clock freeze, colour drains
  C  wish two   sunset; gold rains down and piles up to her knees, she shrugs
  D  wish three lights die, one soft key; slow push in to her face
  E  CTA        extreme close-up on her eyes, slow blink
"""
import json, math, os, sys
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from lib.face import Face
from lib import stage as S

a = sys.argv[sys.argv.index('--') + 1:]
OUT, AD, START, END = a[0], a[1], int(a[2]), int(a[3])
SPP = int(os.environ.get('SPP', '16'))
EP = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shorts', 'ep02'))
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
FPS, VO_START = 15, 8
LINES = json.load(open(os.path.join(EP, 'timings.json')))
F = lambda t: VO_START + int(round(t * FPS))                      # voice time (s) -> film frame
LS = [F(l['start']) for l in LINES]; LE = [F(l['start'] + l['dur']) for l in LINES]
NFR = LE[-1] + 18
SHOTS = {'A': (1, LS[1] - 4), 'B': (LS[1] - 3, LS[2] - 4), 'C': (LS[2] - 3, LS[3] - 4), 'D': (LS[3] - 3, LS[4] - 4), 'E': (LS[4] - 3, NFR)}
FREEZE = LS[1] + int(.42 * (LE[1] - LS[1]))                      # the snap on "Done."
GOLD0, GOLD1 = LS[2] + 6, LS[2] + int(.55 * (LE[2] - LS[2]))      # coins start, pile reaches her knees
DARK = LS[3] - 2
print('TIMING', 'NFR', NFR, 'SHOTS', SHOTS, 'FREEZE', FREEZE, 'GOLD', GOLD0, GOLD1)

# ------------------------------------------------------------ cast
W = S.Witch(sc)
glow = S.mat('Glow', (1, .8, .45), .3, (1., .72, .35), 25)
wand, tip = W.wand(glow)
face = Face(W.arm, gain=1.6)
bpy.context.view_layer.update()
EYES = W.point('head', .45)
FACE = W.point('head', .3) + Vector((0, -.06, 0))

# ------------------------------------------------------------ worlds
world = S.World(sc, AD, [
    ('night', 'satara_night_2k.hdr', .7, 1.0, 40),
    ('rain', 'potsdamer_platz_2k.hdr', .45, .3, 0),
    ('frozen', 'potsdamer_platz_2k.hdr', .35, 0.0, 0),
    ('gold', 'small_harbour_sunset_2k.hdr', 1.0, 1.15, 200),
    ('void', 'satara_night_2k.hdr', .0, 1.0, 0),
])
world.go(SHOTS['B'][0], 'rain', ramp=1)
world.go(FREEZE + 3, 'frozen', ramp=3)
world.go(SHOTS['C'][0], 'gold', ramp=1)
world.go(DARK + 6, 'void', ramp=8)

stone = S.mat('WetStone', (.05, .05, .06), .12)
S.prim('cylinder', 'Ground', stone, radius=6, depth=.02, vertices=96, location=(0, 0, -.01))

# ------------------------------------------------------------ wish one: giant clock + rain that freezes
clock_face = S.mat('ClockFace', (.95, .92, .85), .4, (1, .95, .85), .6)
brass = S.mat('Brass', (.9, .65, .3), .3, metal=1.0)
ink = S.mat('Ink', (.02, .02, .02), .5)
CL = Vector((.9, 4.5, 3.2))
clock = [S.prim('cylinder', 'Clock', clock_face, radius=1.6, depth=.1, vertices=64, location=CL, rotation=(math.radians(90), 0, 0)),
         S.prim('torus', 'ClockRim', brass, major_radius=1.62, minor_radius=.08, location=CL, rotation=(math.radians(90), 0, 0))]
for i in range(12):
    ang = i * math.pi / 6
    t = S.prim('cube', f'Tick{i}', ink, size=1, location=CL + Vector((1.35 * math.sin(ang), -.07, 1.35 * math.cos(ang))))
    t.scale = (.05, .02, .22 if i % 3 == 0 else .12); t.rotation_euler = (0, ang, 0); clock.append(t)
pivot = bpy.data.objects.new('HandsPivot', None); sc.collection.objects.link(pivot); pivot.location = CL + Vector((0, -.09, 0))
hands = []
for n, length, wdt, speed in (('Minute', 1.25, .06, 2.6), ('Hour', .8, .09, .25)):
    h = S.prim('cube', n, brass, size=1, location=(0, 0, length / 2)); h.scale = (wdt, .03, length)
    piv = bpy.data.objects.new(n + 'Pivot', None); sc.collection.objects.link(piv); piv.parent = pivot
    h.parent = piv; hands.append(h); clock.append(h)
    for f, ang in ((SHOTS['B'][0], 0), (FREEZE, speed * (FREEZE - SHOTS['B'][0]) / FPS)):
        piv.rotation_euler = (0, ang, 0); piv.keyframe_insert('rotation_euler', frame=f)
    S.set_interp(piv, 'LINEAR')
for o in clock: S.show(o, SHOTS['B'][0], SHOTS['C'][0])

drop = S.prim('cylinder', 'Drop', S.mat('Rain', (.8, .85, 1), .05, (.6, .7, .9), .5, transmission=.6), radius=.0035, depth=.22, vertices=6)
rain_box = S.prim('plane', 'RainCloud', size=9, location=(0, -1.0, 5.5))
rain = S.particles('Rain', rain_box, SHOTS['B'][0] - 30, FREEZE, 9000, drop, 26, vel=(0, 0, -9), gravity=.3)
for f, v in ((FREEZE - 1, 1.0), (FREEZE + 2, 0.0)): rain.time_tweak = v; rain.keyframe_insert('time_tweak', frame=f)  # time stops
rain_mod = rain_box.modifiers['Rain']
for f, on in ((1, False), (SHOTS['B'][0], True), (SHOTS['C'][0], False)): rain_mod.show_render = on; rain_mod.keyframe_insert('show_render', frame=f)

# ------------------------------------------------------------ wish two: gold rains and piles up
gold = bpy.data.materials.new('CoinPile'); gold.use_nodes = True
nt = gold.node_tree; bs = nt.nodes['Principled BSDF']
bs.inputs['Base Color'].default_value = (1, .7, .25, 1); bs.inputs['Metallic'].default_value = 1; bs.inputs['Roughness'].default_value = .28
vor = nt.nodes.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 28
bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .8
nt.links.new(vor.outputs['Distance'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
mound = S.prim('uv_sphere', 'GoldPile', gold, radius=1.8, segments=48, ring_count=24, location=(0, .1, 0))
bpy.ops.object.shade_smooth()
for f, z in ((1, .001), (GOLD0, .001), (GOLD1, .27), (SHOTS['D'][0], .29)):
    mound.scale = (1, 1, z); mound.keyframe_insert('scale', frame=f)
S.show(mound, GOLD0, SHOTS['D'][0])
coin = S.prim('cylinder', 'Coin', S.mat('Coin', (1, .72, .28), .25, metal=1.0), radius=.035, depth=.006, vertices=16)
coin_box = S.prim('plane', 'CoinCloud', size=4, location=(0, -.2, 4.2))
coins = S.particles('Coins', coin_box, GOLD0 - 8, SHOTS['D'][0] - 8, 2600, coin, 30, vel=(0, 0, -3), gravity=1.0, size_random=.3)
coins.use_rotations = True; coins.rotation_mode = 'NONE'; coins.phase_factor_random = 2.0; coins.angular_velocity_mode = 'RAND'; coins.angular_velocity_factor = 6
coin_mod = coin_box.modifiers['Coins']
for f, on in ((1, False), (GOLD0 - 8, True), (SHOTS['D'][0], False)): coin_mod.show_render = on; coin_mod.keyframe_insert('show_render', frame=f)

# ------------------------------------------------------------ lights
key = S.area('Key', (-1.4, -2.2, 2.3), FACE, 240, (1, .82, .9), 1.0)
fill = S.area('Fill', (1.8, -1.6, .7), FACE, 50, (.7, .8, 1.0), 1.5)
rim = S.area('Rim', (.4, 2.2, 2.6), EYES, 220, (.85, .8, 1.0), .8)
glowL = S.area('GoldBounce', (0, -1.2, .1), FACE, 0, (1, .7, .3), 2.0)
S.light_key(key, SHOTS['B'][0] - 1, 240, (1, .82, .9))
S.light_key(key, SHOTS['B'][0], 220, (.8, .85, 1.0)); S.light_key(rim, SHOTS['B'][0], 220, (.8, .85, 1.0))
S.light_key(key, FREEZE + 3, 200, (.7, .8, 1.0))                        # cold, drained
S.light_key(key, SHOTS['C'][0], 260, (1, .78, .55)); S.light_key(rim, SHOTS['C'][0], 300, (1, .7, .4))
S.light_key(glowL, GOLD0, 0); S.light_key(glowL, GOLD1, 160)
S.light_key(glowL, SHOTS['D'][0] - 1, 160); S.light_key(glowL, SHOTS['D'][0], 0)
for L in (fill, rim): S.light_key(L, DARK, L.data.energy); S.light_key(L, DARK + 6, 0)   # lights die
S.light_key(key, DARK, 260); S.light_key(key, DARK + 6, 110, (1, .75, .85))
wand_light = S.point_light('WandLight', (0, 0, 0), 2.5, (1, .75, .4), .03); wand_light.parent = tip
S.light_key(wand_light, FREEZE - 2, 2.5); S.light_key(wand_light, FREEZE, 300); S.light_key(wand_light, FREEZE + 4, 2.5)
S.light_key(wand_light, DARK, 2.5); S.light_key(wand_light, DARK + 6, .4)

# ------------------------------------------------------------ body
W.breathe(1, NFR)
W.arm_pose(1, 'L', 'relax'); W.arm_pose(1, 'R', 'relax')
W.arm_pose(FREEZE - 8, 'R', 'relax'); W.arm_pose(FREEZE - 2, 'R', 'flick'); W.arm_pose(FREEZE + 1, 'R', 'up')   # snap
W.arm_pose(FREEZE + 14, 'R', 'raise'); W.arm_pose(SHOTS['C'][0] - 1, 'R', 'raise')
W.arm_pose(SHOTS['C'][0], 'R', 'relax'); W.arm_pose(SHOTS['C'][0], 'L', 'relax')
W.arm_pose(GOLD1 - 4, 'L', 'relax'); W.arm_pose(GOLD1 + 2, 'L', 'shock'); W.arm_pose(GOLD1 + 2, 'R', 'shock')   # shrug
W.arm_pose(GOLD1 + 14, 'L', 'relax'); W.arm_pose(GOLD1 + 14, 'R', 'relax')
W.arm_pose(LS[4] + 6, 'L', 'relax'); W.arm_pose(LS[4] + 14, 'L', 'point'); W.arm_pose(NFR, 'L', 'point')        # "yours"
W.alive(1, NFR, seed=2)
env = json.load(open(os.path.join(EP, 'vo_analysis.json')))['env']
pk = sorted(env)[int(len(env) * .95)]; last = -99
for i in range(1, len(env) - 1):                                         # free hand beats on stressed words
    f = VO_START + i
    if env[i] > .8 * pk and env[i] >= env[i - 1] and env[i] >= env[i + 1] and f - last > 18 and not (GOLD1 - 4 < f < GOLD1 + 16) and f < LS[4]:
        W.gesture(f, 'L', .8); last = f

# ------------------------------------------------------------ face
SEQ = [(1, 'sultry'), (LS[0] + 10, 'smug'), (LE[0] - 6, 'tease'),
       (LS[1], 'pout'), (FREEZE - 3, 'menace'), (FREEZE + 6, 'delight'), (LE[1] - 8, 'smug'),
       (LS[2], 'tease'), (GOLD1 - 4, 'surprise'), (GOLD1 + 6, 'annoyed'), (LE[2] - 6, 'smug'),
       (LS[3], 'pout'), (DARK + 10, 'sultry'), (LE[3] - 10, 'tease'),
       (LS[4], 'smug'), (LS[4] + int(.55 * (LE[4] - LS[4])), 'menace'), (LE[4] + 2, 'tease')]
for f, look in SEQ: face.express(f, look)
face.speak(os.path.join(EP, 'vo_analysis.json'), VO_START, FPS)
face.blinks(1, NFR, FPS, every_s=3.0)
face.gaze(1, DARK, FPS, at_camera=.65)
face.look(DARK, NFR, 0, 0)                                                # wish three onward: eyes locked on you
face.look(GOLD0 - 2, GOLD0 + 12, 2, 10)                                   # glance up at the gold
for f in (FREEZE - 1,): face.blink(f)
face.head_pose(1, 0, 0, 0)
face.head_pose(FREEZE + 2, 0, 0, -6); face.head_pose(FREEZE + 14, 0, 0, 0)
face.head_pose(GOLD1, 0, 6, 5); face.head_pose(GOLD1 + 16, 0, 0, 0)
face.head_pose(LS[3] + 20, 0, 0, -7)                                       # tilts her head as she leans in
face.head_pose(NFR - 10, 0, 0, -4)
for f in (NFR - 8, NFR - 7, NFR - 6, NFR - 5): face._dense('blink', f, 1.0)  # slow final blink
face.bake(max(1, START - 2), min(NFR, END + 2))

# ------------------------------------------------------------ cameras
cams = S.Cameras(sc)
up = lambda d, el: Vector((0, -d * math.cos(math.radians(el)), -d * math.sin(math.radians(el))))
M = S.Cameras.move
a0, a1 = SHOTS['A']
c = cams.shot('A', a0, 60)
M(c, a0, FACE + up(1.8, 19) + Vector((-.3, 0, 0)), FACE, 60); M(c, a1, FACE + up(1.15, 20) + Vector((-.15, 0, 0)), FACE, 60)

b0, b1 = SHOTS['B']; mid = Vector((0, 0, 1.3))
c = cams.shot('B', b0, 30)
M(c, b0, mid + up(3.4, 9) + Vector((.6, 0, 0)), mid + Vector((.2, 0, .3)), 30)
M(c, FREEZE, mid + up(3.1, 9) + Vector((.5, 0, 0)), mid + Vector((.2, 0, .3)), 30)
M(c, b1, mid + up(3.0, 9) + Vector((.48, 0, 0)), mid + Vector((.2, 0, .3)), 30)      # almost frozen camera too
S.Cameras.shake(c, FREEZE - 1, FREEZE + 4, .025, 4)

c0, c1 = SHOTS['C']; chest = Vector((0, 0, 1.2))
c = cams.shot('C', c0, 35)
M(c, c0, chest + up(2.6, 10) + Vector((-.4, 0, 0)), chest, 35)
M(c, c1, chest + up(3.4, 14) + Vector((-.5, 0, 0)), chest + Vector((0, 0, -.15)), 32)   # widen to show the pile

d0, d1 = SHOTS['D']
c = cams.shot('D', d0, 50)
M(c, d0, FACE + up(2.4, 16), FACE + Vector((0, 0, -.1)), 50)
M(c, d1, FACE + up(.85, 19), FACE, 50)                                    # slow creep in

e0, e1 = SHOTS['E']
c = cams.shot('E', e0, 85)
M(c, e0, EYES + up(1.25, 17) + Vector((.05, 0, -.02)), EYES + Vector((0, 0, -.03)), 85)
M(c, e1, EYES + up(1.0, 18) + Vector((.03, 0, -.02)), EYES + Vector((0, 0, -.03)), 85)

# ------------------------------------------------------------ render
S.bake_particles(-40, NFR)
S.render_setup(sc, OUT, spp=SPP)
sc.frame_start, sc.frame_end = START, min(END, NFR)
print('RENDER', START, min(END, NFR))
if os.environ.get('DRY'):
    sc.render.resolution_x, sc.render.resolution_y = 270, 480; sc.cycles.samples = 6
    for fr in [int(x) for x in os.environ['DRY'].split(',')]:
        sc.frame_set(fr); sc.render.filepath = os.path.join(OUT, f'dry_{fr:04d}.png')
        bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
print('DONE')
