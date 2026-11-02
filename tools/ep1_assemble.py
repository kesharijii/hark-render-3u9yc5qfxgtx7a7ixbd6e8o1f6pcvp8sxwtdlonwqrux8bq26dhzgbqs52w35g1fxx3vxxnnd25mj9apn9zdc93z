# Assemble ep1: frames -> video (30 fps, 1080x1920) + TTS voice + synth SFX/music + captions.
import asyncio, json, os, subprocess, sys
import edge_tts
FR = sys.argv[1]; OUT = sys.argv[2]
FPS = 15; NFR = 810; FREEZE = 1.5
DUR = NFR / FPS + FREEZE
LINES = [  # (start s, text)
    (0.3, "I cast one spell to make my cat happy. Now he's bigger than my house."),
    (4.3, "He wanted more food. So I said one word: grow."),
    (11.0, "He did not stop at a little."),
    (18.6, "His purr sets off car alarms."),
    (23.4, "His naps close the highway."),
    (30.2, "I tried to undo it. He thought my wand was a toy."),
    (39.5, "So now he's my ride to work."),
    (48.6, "Next week: he finds the ocean. Follow so you don't miss it."),
]
VOICE = os.environ.get('VOICE', 'en-US-AvaMultilingualNeural')
async def tts(i, t):
    c = edge_tts.Communicate(t, VOICE, rate='+4%', pitch='+8Hz', boundary='WordBoundary')
    words = []
    with open(f'v{i}.mp3', 'wb') as f:
        async for ch in c.stream():
            if ch['type'] == 'audio': f.write(ch['data'])
            elif ch['type'] == 'WordBoundary': words.append((ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7, ch['text']))
    return words
async def allv(): return [await tts(i, t) for i, (_, t) in enumerate(LINES)]
WORDS = asyncio.run(allv())
def sh(c): print(c[:300]); subprocess.run(c, shell=True, check=True)

# captions: 3-4 word chunks, karaoke-style pop
def ts(t): h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60; return f"{h}:{m:02d}:{s:05.2f}"
ass = ["[Script Info]", "PlayResX: 1080", "PlayResY: 1920", "", "[V4+ Styles]",
 "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
 "Style: Cap,DejaVu Sans,84,&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,6,2,2,60,60,520,1",
 "Style: Title,DejaVu Sans,78,&H0000E5FF,&H0000E5FF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,6,2,8,60,60,230,1",
 "Style: Big,DejaVu Sans,150,&H0000E5FF,&H0000E5FF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,9,3,5,60,60,0,1",
 "Style: Small,DejaVu Sans,30,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,1,2,40,40,70,1",
 "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
for (st, _), ws in zip(LINES, WORDS):
    for k in range(0, len(ws), 3):
        ch = ws[k:k + 3]
        a = st + ch[0][0]; b = st + (ws[k + 3][0] if k + 3 < len(ws) else ch[-1][1] + 0.25)
        txt = ' '.join(w[2] for w in ch).upper()
        ass.append(f"Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\fscx80\\fscy80\\t(0,90,\\fscx100\\fscy100)}}{txt}")
ass.append(f"Dialogue: 0,{ts(0)},{ts(3.4)},Title,,0,0,0,,OOPS, I SUPERSIZED MY CAT")
ass.append(f"Dialogue: 0,{ts(NFR / FPS - 0.1)},{ts(DUR)},Big,,0,0,0,,{{\\fad(120,0)}}PART 2")
ass.append(f"Dialogue: 0,{ts(NFR / FPS - 0.1)},{ts(DUR)},Small,,0,0,0,,3D models: henrryShayne, JonasDichelle (CC-BY)  |  HDRIs: Poly Haven (CC0)")
open('caps.ass', 'w').write('\n'.join(ass) + '\n')

# video
sh(f"ffmpeg -y -framerate {FPS} -start_number 1 -i '{FR}/f_%04d.png' -vf \"tpad=stop_mode=clone:stop_duration={FREEZE},"
   f"minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:vsbmc=1:scd=fdiff:scd_threshold=8,scale=1080:1920:flags=lanczos,"
   f"eq=saturation=1.1:contrast=1.04,subtitles=caps.ass\" -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -an vid.mp4")

# audio: music box arpeggio + ocean + purr + car alarm + chimes + voice
note = "261.63*(1+0.26*eq(mod(floor(t*4),8),1)+0.498*eq(mod(floor(t*4),8),2)+0.68*eq(mod(floor(t*4),8),3)+1*eq(mod(floor(t*4),8),4)+0.68*eq(mod(floor(t*4),8),5)+0.498*eq(mod(floor(t*4),8),6)+0.26*eq(mod(floor(t*4),8),7))"
inputs = [
 f"-f lavfi -t {DUR} -i \"aevalsrc='0.25*sin(2*PI*t*{note})*exp(-5*mod(t,0.25))+0.12*sin(4*PI*t*{note})*exp(-8*mod(t,0.25))':s=44100\"",
 f"-f lavfi -t {DUR} -i \"anoisesrc=color=brown:amplitude=0.5:r=44100\"",
 f"-f lavfi -t 5.2 -i \"anoisesrc=color=brown:amplitude=0.9:r=44100\"",
 f"-f lavfi -t 3.6 -i \"aevalsrc='0.35*sin(2*PI*t*(800+400*gt(mod(t,0.5),0.25)))*(0.6+0.4*sin(2*PI*8*t))':s=44100\"",
 f"-f lavfi -t 1.6 -i \"aevalsrc='0.4*(sin(2*PI*1760*t)+0.6*sin(2*PI*2637*t)+0.4*sin(2*PI*3520*t))*exp(-3*t)*(0.7+0.3*sin(2*PI*14*t))':s=44100\"",
]
for i in range(len(LINES)): inputs.append(f"-i v{i}.mp3")
fc = [
 "[0]volume=0.10,afade=t=out:st=%.2f:d=1.5[mus]" % (DUR - 1.5),
 "[1]lowpass=f=500,volume=0.5,tremolo=f=0.12:d=0.7[sea]",
 "[2]lowpass=f=120,tremolo=f=24:d=0.9,volume=2.2,afade=t=in:d=0.4,afade=t=out:st=4.6:d=0.6,adelay=18000|18000[purr]",
 "[3]volume=0.5,afade=t=out:st=3.0:d=0.6,adelay=19400|19400[alarm]",
 "[4]asplit=3[c1][c2][c3]", "[c1]adelay=7400|7400[ch1]", "[c2]adelay=10200|10200,volume=1.3[ch2]", "[c3]adelay=33300|33300,volume=0.8[ch3]",
]
vl = []
for i, (st, _) in enumerate(LINES):
    d = int(st * 1000); fc.append(f"[{5 + i}]aresample=44100,volume=1.6,adelay={d}|{d}[v{i}]"); vl.append(f"[v{i}]")
fc.append(f"{''.join(vl)}amix=inputs={len(vl)}:normalize=0,apad[vo]")
fc.append("[vo]asplit=2[vo1][vo2]")
fc.append("[mus][sea][purr][alarm][ch1][ch2][ch3]amix=inputs=7:normalize=0[bed]")
fc.append("[bed][vo1]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=300[duck]")
fc.append("[duck][vo2]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
open('fc.txt', 'w').write(';\n'.join(fc))
sh(f"ffmpeg -y {' '.join(inputs)} -filter_complex_script fc.txt -map '[aout]' -t {DUR} -c:a aac -b:a 192k aud.m4a")
sh(f"ffmpeg -y -i vid.mp4 -i aud.m4a -c:v copy -c:a copy -shortest -movflags +faststart {OUT}")
sh(f"ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate,nb_frames:format=duration -of default=nw=1 {OUT}")
