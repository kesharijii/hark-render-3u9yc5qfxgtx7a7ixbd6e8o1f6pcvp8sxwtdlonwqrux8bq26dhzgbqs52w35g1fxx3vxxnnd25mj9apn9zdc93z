"""Word-by-word captions in the MoneyPrinterTurbo reel style: yellow #FFE14D, black stroke, ~80% height, pop-in."""
import json, re, sys
W = json.load(open('words.json'))
def ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return '%d:%02d:%05.2f' % (h, m, s)
hdr = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,Be Vietnam Pro,100,&H004DE1FF,&H004DE1FF,&H00111111,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
lines = []
for i, w in enumerate(W):
    t0 = w['t']; nxt = W[i+1]['t'] if i + 1 < len(W) else t0 + w['d'] + 0.6
    t1 = min(nxt, t0 + w['d'] + 0.45)
    if nxt - t1 < 0.12: t1 = nxt
    txt = re.sub(r'[^\w\'\-]', '', w['w'])
    lines.append('Dialogue: 0,%s,%s,Word,,0,0,0,,{\\pos(540,1536)\\fscx80\\fscy80\\t(0,90,\\fscx108\\fscy108)\\t(90,160,\\fscx100\\fscy100)}%s' % (ts(t0), ts(t1), txt))
open(sys.argv[1] if len(sys.argv) > 1 else 'captions.ass', 'w').write(hdr + '\n'.join(lines) + '\n')
print(len(lines))
