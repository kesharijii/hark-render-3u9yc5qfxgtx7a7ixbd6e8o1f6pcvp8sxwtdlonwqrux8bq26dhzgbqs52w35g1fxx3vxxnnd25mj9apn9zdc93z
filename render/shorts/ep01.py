"""Short 01 - "One Little Rhyme".

blender -b host.blend -P render/shorts/ep01.py -- OUTDIR ASSETDIR START END
ASSETDIR holds the HDRIs. 15 fps, 540x960 frames f_####.png (upscaled + 30 fps at assembly).

Beats (frames, voice starts at frame 8):
  A   1- 68  hook: close on her face, wand glowing, rainy street       "One little rhyme, darling..."
  B  69-166  rain falls; wand flick on "away" -> starry night (f153)   "Rain, rain, go away..."
  C 167-226  dark; wand up on "light" -> neon floods in (f213)         "Too dark? Then let there be light."
  D 227-300  neon; flick on "night" -> pull back: she's in a snow globe on a shelf (f278)
                                                                        "Too bright? Fine. Shrink the night."
  E 301-384  inside the globe, snow; she points at the viewer          "Your turn. Rhyme the next spell... if you dare."
"""
import math, os, sys
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from lib.face import Face
from lib import stage as S

a = sys.argv[sys.argv.index('--') + 1:]
OUT, AD, START, END = a[0], a[1], int(a[2]), int(a[3])
SPP = int(os.environ.get('SPP', '16'))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
NFR, VO_START = 384, 8
SHOTS = {'A': (1, 68), 'B': (69, 166), 'C': (167, 226), 'D': (227, 300), 'E': (301, 384)}
SKY_SWITCH, NEON_ON, GLOBE = 153, 213, 278

# ------------------------------------------------------------ cast
W = S.Witch(sc)
glow = S.mat('Glow', (1, .8, .45), .3, (1., .72, .35), 25)
wand, tip = W.wand(glow)
face = Face(W.arm)
bpy.context.view_layer.update()
EYES = W.point('head', .45)                     # roughly eye height, world space
FACE = W.point('head', .3) + Vector((0, -.06, 0))
print('EYES', EYES, 'FACE', FACE)

# ------------------------------------------------------------ world: rain -> night -> neon dark -> room
world = S.World(sc, AD, [
    ('rain', 'potsdamer_platz_2k.hdr', .45, .25, 0),
    ('night', 'satara_night_2k.hdr', .9, 1.0, 40),
    ('neon', 'cobblestone_street_night_2k.hdr', .25, 1.2, 0),
    ('room', 'lebombo_2k.hdr', .9, 1.0, 120),
])
world.go(SKY_SWITCH + 3, 'night', ramp=4)
world.go(NEON_ON + 4, 'neon', ramp=6)
world.go(GLOBE + 14, 'room', ramp=12)

# ------------------------------------------------------------ set: wet stone disc = top of the globe base
stone = S.mat('WetStone', (.05, .05, .06), .12)
ground = S.prim('cylinder', 'Ground', stone, radius=1.35, depth=.02, vertices=96, location=(0, 0, -.01))

# neon rings behind her, dark until NEON_ON
pink = S.mat('NeonPink', (1, .1, .6), .3, (1, .08, .55), 0)
cyan = S.mat('NeonCyan', (.1, .9, 1), .3, (.05, .85, 1), 0)
rings = [S.prim('torus', 'RingPink', pink, major_radius=.75, minor_radius=.025, location=(-.45, .9, 1.45), rotation=(math.radians(90), 0, 0))
S.prim('torus', 'RingCyan', cyan, major_radius=.48, minor_radius=.022, location=(.6, .7, .95), rotation=(math.radians(90), 0, 0)),
S.prim('cylinder', 'BarPink', pink, radius=.02, depth=1.6, location=(.95, 1.0, .9))]
for o in rings: S.show(o, NEON_ON)
for m in (pink, cyan):
    s_ = S.emission_socket(m); S.key_socket(s_, NEON_ON, 0); S.key_socket(s_, NEON_ON + 5, 18)

# snow globe, shelf and giant books appear on the flick
glass = S.mat('Glass', (1, 1, 1), 0.0, transmission=1.0, ior=1.45)
wood = S.mat('Wood', (.16, .08, .04), .45)
gold = S.mat('Gold', (1, .75, .35), .25, metal=1.0)
globe = S.prim('uv_sphere', 'Globe', glass, radius=1.45, segments=64, ring_count=32, location=(0, 0, 1.0))
bpy.ops.object.shade_smooth()
base = S.prim('cylinder', 'GlobeBase', wood, radius=1.4, depth=.55, vertices=96, location=(0, 0, -.3))
trim = S.prim('torus', 'GlobeTrim', gold, major_radius=1.4, minor_radius=.04, location=(0, 0, -.03))
shelf = S.prim('cube', 'Shelf', wood, size=1, location=(0, 1.2, -.725)); shelf.scale = (22, 6, .3)
books = []
for i, (x, h, col) in enumerate(((-3.1, 4.6, (.35, .05, .07)), (-4.2, 5.0, (.05, .12, .3)), (3.3, 4.2, (.08, .25, .12)), (4.4, 4.8, (.3, .18, .05)))):
    b = S.prim('cube', f'Book{i}', S.mat(f'Leather{i}', col, .55), size=1, location=(x, 1.5, -.575 + h / 2)); b.scale = (1.0, 3.4, h)
    books.append(b)
S.show(globe, GLOBE, SHOTS['E'][0])          # the camera sits inside the globe in E
for o in [base, trim, shelf] + books: S.show(o, GLOBE)

# ------------------------------------------------------------ weather
drop = S.prim('cylinder', 'Drop', S.mat('Rain', (.8, .85, 1), .05, (.6, .7, .9), .4, transmission=.6), radius=.0035, depth=.22, vertices=6)
rain_box = S.prim('plane', 'RainCloud', size=9, location=(0, -1.0, 5.5))
S.particles('Rain', rain_box, 1 - 30, SKY_SWITCH, 9000, drop, 26, vel=(0, 0, -9), gravity=0.3)      # drops keep their vertical axis
rain_mod = rain_box.modifiers['Rain']                         # every drop vanishes with the flash
for f, on in ((1, True), (SKY_SWITCH + 1, False)): rain_mod.show_render = on; rain_mod.keyframe_insert('show_render', frame=f)

flake = S.prim('ico_sphere', 'Flake', S.mat('Snow', (1, 1, 1), .6, (1, 1, 1), .3), radius=.012, subdivisions=1)
snow_box = S.prim('cube', 'SnowCloud', size=1, location=(0, 0, 2.15)); snow_box.scale = (1.7, 1.7, .25)
bpy.context.view_layer.objects.active = snow_box; bpy.ops.object.transform_apply(scale=True)
S.particles('Snow', snow_box, GLOBE - 10, NFR, 1400, flake, 70, vel=(0, 0, -.45), gravity=0.02, size_random=.7)

# ------------------------------------------------------------ lights
key = S.area('Key', (-1.6, -2.2, 2.4), FACE, 260, (.75, .82, 1.0), 1.2)
fill = S.area('Fill', (1.8, -1.6, .6), FACE, 60, (.7, .8, 1.0), 1.5)
rim = S.area('Rim', (.4, 2.2, 2.6), EYES, 220, (.8, .85, 1.0), .8)
wand_light = S.point_light('WandLight', (0, 0, 0), 0, (1, .75, .4), .03)
wand_light.parent = tip
pinkL = S.area('NeonPinkL', (-1.8, -.6, 1.6), FACE, 0, (1, .1, .6), .8)
cyanL = S.area('NeonCyanL', (1.9, -.2, 1.2), FACE, 0, (.1, .85, 1), .8)
roomL = S.area('RoomWarm', (-4, -6, 5), (0, 0, 1), 0, (1, .8, .55), 4)

S.light_key(wand_light, 1, 2.5)
# rain: soft grey-blue
for L, e in ((key, 260), (fill, 60), (rim, 220)): S.light_key(L, SKY_SWITCH - 2, e)
# flash on the sky switch
S.light_key(wand_light, SKY_SWITCH - 2, 2.5); S.light_key(wand_light, SKY_SWITCH, 400); S.light_key(wand_light, SKY_SWITCH + 4, 4)
# night: cool moonlight, darker fill
S.light_key(key, SKY_SWITCH + 3, 140, (.55, .65, 1.0)); S.light_key(fill, SKY_SWITCH + 3, 18, (.5, .6, 1.0))
S.light_key(rim, SKY_SWITCH + 3, 260, (.6, .7, 1.0))
# too dark: dim further before the neon
S.light_key(key, NEON_ON - 1, 70); S.light_key(rim, NEON_ON - 1, 160)
S.light_key(wand_light, NEON_ON - 2, 4); S.light_key(wand_light, NEON_ON, 300); S.light_key(wand_light, NEON_ON + 4, 4)
# neon: magenta key, cyan rim
for L, e in ((pinkL, 0), (cyanL, 0)): S.light_key(L, NEON_ON, e)
S.light_key(pinkL, NEON_ON + 4, 300); S.light_key(cyanL, NEON_ON + 4, 320)
S.light_key(key, NEON_ON + 4, 25, (.9, .5, 1.0)); S.light_key(rim, NEON_ON + 4, 120, (.3, .9, 1.0))
# globe: flash, then warm room light from outside, neon kept low inside
S.light_key(wand_light, GLOBE - 2, 4); S.light_key(wand_light, GLOBE, 400); S.light_key(wand_light, GLOBE + 4, 4)
S.light_key(roomL, GLOBE, 0); S.light_key(roomL, GLOBE + 10, 2400)
S.light_key(pinkL, GLOBE + 10, 150); S.light_key(cyanL, GLOBE + 10, 160)
S.light_key(key, GLOBE + 10, 120, (1, .85, .7))

# ------------------------------------------------------------ performance: body
W.breathe(1, NFR)
W.arm_pose(1, 'L', 'relax')
W.arm_pose(1, 'R', 'raise'); W.arm_pose(60, 'R', 'raise')               # A: wand by her face
W.arm_pose(76, 'R', 'relax'); W.arm_pose(140, 'R', 'relax')            # B
W.arm_pose(147, 'R', 'flick'); W.arm_pose(SKY_SWITCH, 'R', 'up'); W.arm_pose(166, 'R', 'up')
W.arm_pose(176, 'R', 'relax'); W.arm_pose(198, 'R', 'relax')           # C: spin the wand up
for k, f in enumerate(range(202, NEON_ON, 3)):
    W.arm_pose(f, 'R', 'raise', wobble=(0, 0, 18 * (-1) ** k))
W.arm_pose(NEON_ON, 'R', 'up'); W.arm_pose(224, 'R', 'up')
W.arm_pose(234, 'R', 'relax'); W.arm_pose(268, 'R', 'relax')          # D: bored, then flick
W.arm_pose(GLOBE - 4, 'R', 'flick'); W.arm_pose(GLOBE, 'R', 'up'); W.arm_pose(296, 'R', 'relax')
W.arm_pose(305, 'R', 'relax'); W.arm_pose(318, 'R', 'point'); W.arm_pose(370, 'R', 'point')  # E: points at you
W.arm_pose(330, 'L', 'relax')

# ------------------------------------------------------------ performance: face
for f, look in ((1, 'smug'), (34, 'sultry'), (70, 'tease'), (124, 'menace'), (SKY_SWITCH + 2, 'delight'),
                (172, 'annoyed'), (192, 'smug'), (NEON_ON + 1, 'delight'), (230, 'annoyed'), (246, 'pout'),
                (258, 'menace'), (GLOBE + 4, 'smug'), (303, 'tease'), (338, 'menace'), (358, 'smug')):
    face.express(f, look)
face.speak(os.path.join(REPO, 'shorts', 'ep01', 'vo_analysis.json'), VO_START, 15)
face.blinks(1, NFR, 15, every_s=3.4)
for f in (SKY_SWITCH - 1, NEON_ON - 1, GLOBE - 1): face.blink(f)       # flinch at each flash
face.head_pose(1, 0, 0, 0)
face.head_pose(SKY_SWITCH, 0, 0, -6); face.head_pose(SKY_SWITCH + 10, 0, 0, 0)
face.head_pose(246, 0, 8, 4); face.head_pose(262, 0, 0, 0)            # "Fine." bored head turn
face.head_pose(338, 0, -4, -5); face.head_pose(372, 0, 0, -3)
face.bake(max(1, START - 2), min(NFR, END + 2))

# ------------------------------------------------------------ cameras (low, under the hat brim)
cams = S.Cameras(sc)
up = lambda d, el: Vector((0, -d * math.cos(math.radians(el)), -d * math.sin(math.radians(el))))
M = S.Cameras.move

c = cams.shot('A', SHOTS['A'][0], 60)                                   # push in
M(c, 1, FACE + up(1.9, 20) + Vector((.35, 0, 0)), FACE + Vector((0, 0, .02)), 60)
M(c, 68, FACE + up(1.15, 20) + Vector((.2, 0, 0)), FACE + Vector((0, 0, .03)), 60)

c = cams.shot('B', SHOTS['B'][0], 35)                                   # medium, rain; tilt up on the switch
mid = Vector((0, 0, 1.3))
M(c, 69, mid + up(3.0, 9) + Vector((-.5, 0, 0)), mid, 35)
M(c, SKY_SWITCH - 2, mid + up(2.6, 9) + Vector((-.35, 0, 0)), mid, 35)
M(c, 166, mid + up(2.9, 22) + Vector((-.3, 0, 0)), mid + Vector((0, 0, .35)), 32)
S.Cameras.shake(c, SKY_SWITCH - 1, SKY_SWITCH + 6, .03, 1)

c = cams.shot('C', SHOTS['C'][0], 45)                                   # close-medium, slow drift
chest = Vector((0, 0, 1.45))
M(c, 167, chest + up(2.2, 14) + Vector((.45, 0, 0)), chest, 45)
M(c, 226, chest + up(1.9, 15) + Vector((.2, 0, 0)), chest + Vector((0, 0, .05)), 45)
S.Cameras.shake(c, NEON_ON - 1, NEON_ON + 6, .03, 2)

c = cams.shot('D', SHOTS['D'][0], 40)                                   # medium, then big pull back
M(c, 227, chest + up(2.4, 14) + Vector((-.3, 0, 0)), chest, 40)
M(c, GLOBE, chest + up(2.6, 14) + Vector((-.3, 0, 0)), chest, 40)
M(c, GLOBE + 16, Vector((-1.2, -8.0, 2.4)), Vector((0, 0, .9)), 32)
M(c, 300, Vector((-1.4, -9.5, 2.6)), Vector((0, 0, .8)), 32)
S.Cameras.shake(c, GLOBE - 1, GLOBE + 5, .03, 3)

c = cams.shot('E', SHOTS['E'][0], 50)                                   # inside the globe; she leans in
M(c, 301, FACE + up(1.6, 18) + Vector((-.3, 0, -.05)), FACE, 50)
M(c, 345, FACE + up(1.05, 20) + Vector((-.15, 0, 0)), FACE, 50)
M(c, 384, FACE + up(.95, 21) + Vector((-.1, 0, 0)), FACE + Vector((0, 0, .01)), 50)

# ------------------------------------------------------------ render
S.bake_particles(-40, NFR)
S.render_setup(sc, OUT, spp=SPP)
sc.frame_start, sc.frame_end = START, END
print('RENDER', START, END)
if os.environ.get('DRY'):
    sc.render.resolution_x, sc.render.resolution_y = 270, 480; sc.cycles.samples = 6
    for fr in [int(x) for x in os.environ['DRY'].split(',')]:
        sc.frame_set(fr); sc.render.filepath = os.path.join(OUT, f'dry_{fr:04d}.png')
        bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
print('DONE')
