#!/bin/bash
# frames (rendered at FPS) -> motion-interpolated 30 fps -> lanczos upscale 1080x1920 -> burned captions -> audio mux, loudnorm -14 LUFS
set -euo pipefail
STORY=$1; FPS=$2
J() { python3 -c "import json,sys;print(json.load(open('$STORY/story.json'))['$1'])"; }
DUR=$(J duration); OFPS=$(J out_fps); W=$(J width); H=$(J height); AUD=$(J audio); ASS=$(J captions)
NIN=$(python3 -c "print(int(round($DUR*$FPS)))"); NOUT=$(python3 -c "print(int(round($DUR*$OFPS)))")
mkdir -p out
python3 - <<P
import json,glob
r=[json.load(open(f)) for f in sorted(glob.glob('frames/report_part*.json'))]
json.dump(r,open('out/render_reports.json','w'),indent=1)
P
have=$(ls frames/f_*.png | wc -l); echo "frames: $have / $NIN"
test "$have" -eq "$NIN"
cp "$ASS" out/captions.ass
# two-pass loudnorm (linear) on the committed mix
M=$(ffmpeg -hide_banner -i "$AUD" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
mi=$(echo "$M" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['input_i'],d['input_tp'],d['input_lra'],d['input_thresh'],d['target_offset'])")
read II ITP ILRA ITH OFF <<< "$mi"
ffmpeg -hide_banner -loglevel error -y -i "$AUD" -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$II:measured_TP=$ITP:measured_LRA=$ILRA:measured_thresh=$ITH:offset=$OFF:linear=true,aresample=48000,atrim=0:$DUR" -c:a aac -b:a 192k out/audio.m4a
T0=$(date +%s)
ffmpeg -hide_banner -loglevel error -y -framerate $FPS -i frames/f_%05d.png \
  -vf "tpad=stop_mode=clone:stop=2,minterpolate=fps=$OFPS:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff:scd_threshold=6,hqdn3d=1.2:1.2:3:3,scale=$W:$H:flags=lanczos,unsharp=5:5:0.45:5:5:0,subtitles=out/captions.ass:fontsdir=fonts,format=yuv420p" \
  -frames:v $NOUT -c:v libx264 -preset slow -crf 18 -profile:v high -r $OFPS -movflags +faststart out/video.mp4
ffmpeg -hide_banner -loglevel error -y -i out/video.mp4 -i out/audio.m4a -map 0:v -map 1:a -c copy -t $DUR -movflags +faststart out/final.mp4
echo "join seconds: $(( $(date +%s) - T0 ))"
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,nb_frames -of compact out/final.mp4
