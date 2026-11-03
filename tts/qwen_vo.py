"""Qwen3-TTS voiceover: design a host voice once, then clone it for every line (consistent speaker, no clipping)."""
import json, sys, time, os, gc
import numpy as np, soundfile as sf, torch
from qwen_tts import Qwen3TTSModel

cfg = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
torch.set_num_threads(os.cpu_count())
dev = 'cuda:0' if torch.cuda.is_available() else 'cpu'
dt = torch.bfloat16 if dev != 'cpu' else torch.float32
lang = cfg.get('language', 'English')
t0 = time.time()

ref = os.path.join(out, 'voice_ref.wav')
if cfg.get('ref_audio'):
    ref_audio = cfg['ref_audio']
else:
    dm = Qwen3TTSModel.from_pretrained(cfg.get('design_model', 'Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign'), device_map=dev, dtype=dt, attn_implementation='sdpa')
    w, sr = dm.generate_voice_design(text=cfg['ref_text'], language=lang, instruct=cfg['voice_instruct'])
    sf.write(ref, w[0], sr); ref_audio = ref
    print(f'designed ref {len(w[0]) / sr:.1f}s in {time.time() - t0:.0f}s', flush=True)
    del dm; gc.collect()

cm = Qwen3TTSModel.from_pretrained(cfg.get('clone_model', 'Qwen/Qwen3-TTS-12Hz-1.7B-Base'), device_map=dev, dtype=dt, attn_implementation='sdpa')
prompt = cm.create_voice_clone_prompt(ref_audio=ref_audio, ref_text=cfg['ref_text'], x_vector_only_mode=False)
gap = cfg.get('gap', 0.25); full = []; timing = []; pos = 0.0; SR = None
for i, ln in enumerate(cfg['lines']):
    t1 = time.time()
    w, sr = cm.generate_voice_clone(text=ln['text'], language=lang, voice_clone_prompt=prompt)
    a = np.asarray(w[0], dtype=np.float32); SR = sr
    a = np.concatenate([a, np.zeros(int(0.12 * sr), np.float32)])  # tail room so nothing is cut
    sf.write(os.path.join(out, f'line_{i:02d}.wav'), a, sr)
    d = len(a) / sr; timing.append({'i': i, 'text': ln['text'], 'start': round(pos, 3), 'dur': round(d, 3)})
    print(f'line {i} {d:.2f}s audio in {time.time() - t1:.0f}s: {ln["text"]}', flush=True)
    full += [a, np.zeros(int(ln.get('pause', gap) * sr), np.float32)]; pos += d + ln.get('pause', gap)
sf.write(os.path.join(out, 'vo_full.wav'), np.concatenate(full), SR)
json.dump(timing, open(os.path.join(out, 'timings.json'), 'w'), indent=1)
print(f'TOTAL {pos:.1f}s audio, wall {time.time() - t0:.0f}s', flush=True)
