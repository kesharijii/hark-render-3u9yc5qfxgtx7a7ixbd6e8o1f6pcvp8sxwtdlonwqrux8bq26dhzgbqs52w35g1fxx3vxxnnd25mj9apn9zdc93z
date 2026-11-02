"""QA for the final reel: writes qa.json + contact.jpg. Exit code 1 if any check fails."""
import json, re, subprocess, sys, os
mp4, story, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
S = json.load(open(os.path.join(story, 'story.json')))
def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)
pr = json.loads(run(['ffprobe', '-v', 'error', '-count_frames', '-show_entries',
                     'format=duration:stream=codec_type,width,height,r_frame_rate,nb_read_frames', '-of', 'json', mp4]).stdout)
v = [s for s in pr['streams'] if s['codec_type'] == 'video'][0]
a = [s for s in pr['streams'] if s['codec_type'] == 'audio']
dur = float(pr['format']['duration']); nf = int(v['nb_read_frames'])
num, den = map(int, v['r_frame_rate'].split('/')); fps = num / den
exp_n = int(round(S['duration'] * S['out_fps']))
checks = {}
checks['resolution'] = dict(value='%dx%d' % (v['width'], v['height']), expected='%dx%d' % (S['width'], S['height']),
                            pass_=(v['width'], v['height']) == (S['width'], S['height']))
checks['fps'] = dict(value=round(fps, 3), expected=S['out_fps'], pass_=abs(fps - S['out_fps']) < 0.01)
checks['duration'] = dict(value=round(dur, 3), expected=S['duration'], pass_=abs(dur - S['duration']) <= 0.05)
checks['frame_count'] = dict(value=nf, expected=exp_n, pass_=nf == exp_n)
checks['audio_present'] = dict(value=len(a), pass_=len(a) == 1)
fr = run(['ffmpeg', '-hide_banner', '-i', mp4, '-vf', 'freezedetect=n=-60dB:d=1.5', '-map', '0:v', '-f', 'null', '-']).stderr
frz = re.findall(r'freeze_duration: ([\d.]+)', fr)
frz_open = 'freeze_start' in fr and len(re.findall('freeze_start', fr)) > len(frz)
checks['no_frozen_gt_1.5s'] = dict(value=[float(x) for x in frz] + (['open-ended'] if frz_open else []), pass_=not frz and not frz_open)
bl = run(['ffmpeg', '-hide_banner', '-i', mp4, '-vf', 'blackdetect=d=1.0:pix_th=0.06:pic_th=0.95', '-map', '0:v', '-f', 'null', '-']).stderr
blk = re.findall(r'black_duration:([\d.]+)', bl)
checks['no_near_black_gt_1s'] = dict(value=[float(x) for x in blk], pass_=not blk)
eb = run(['ffmpeg', '-hide_banner', '-i', mp4, '-map', '0:a', '-af', 'ebur128=peak=true', '-f', 'null', '-']).stderr
summ = eb[eb.rfind('Summary:'):]
I = float(re.search(r'I:\s+(-?[\d.]+) LUFS', summ).group(1))
TP = float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', summ).group(1))
checks['loudness_-14_LUFS'] = dict(value=I, expected='-14 +/- 1', pass_=abs(I + 14) <= 1.0)
checks['true_peak_le_-1_dBTP'] = dict(value=TP, expected='<= -1.0', pass_=TP <= -1.0)
# contact sheet: 12 frames spread over the reel
step = max(1, nf // 12)
run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', mp4, '-vf',
     "select='not(mod(n\\,%d))',scale=270:480,tile=6x2:padding=6:color=black" % step, '-frames:v', '1', '-q:v', '3',
     os.path.join(outdir, 'contact.jpg')])
res = {k: dict(value=c['value'], expected=c.get('expected'), passed=bool(c['pass_'])) for k, c in checks.items()}
res['all_passed'] = all(c['passed'] for c in res.values() if isinstance(c, dict))
json.dump(res, open(os.path.join(outdir, 'qa.json'), 'w'), indent=1)
print(json.dumps(res, indent=1))
sys.exit(0 if res['all_passed'] else 1)
