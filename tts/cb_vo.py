"""Chatterbox Turbo/Nano voiceover: clone a reference clip, speak lines with [laugh]-style tags."""
import json, sys, os, time, torch, torchaudio as ta
from chatterbox.tts_turbo import ChatterboxTurboTTS
cfg = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
nano = cfg.get("model", "turbo") == "nano"
t0 = time.time(); m = ChatterboxTurboTTS.from_pretrained(device="cpu", nano=nano)
print(f"load {time.time()-t0:.1f}s nano={nano}")
ref = cfg["reference"]; pieces = []; sr = m.sr; timings = []; cur = 0.0
for i, ln in enumerate(cfg["lines"]):
    t = time.time(); w = m.generate(ln["text"], audio_prompt_path=ref).float().cpu()
    if w.dim() == 1: w = w.unsqueeze(0)
    ta.save(f"{out}/line_{i:02d}.wav", w, sr); d = w.shape[1] / sr
    print(f"line {i}: {d:.2f}s audio in {time.time()-t:.1f}s")
    timings.append({"i": i, "start": round(cur, 3), "dur": round(d, 3), "text": ln["text"]})
    pause = ln.get("pause", cfg.get("pause", 0.35)); pieces += [w, torch.zeros(1, int(pause * sr))]; cur += d + pause
ta.save(f"{out}/vo_full.wav", torch.cat(pieces, 1), sr)
json.dump(timings, open(f"{out}/timings.json", "w"), indent=1)
