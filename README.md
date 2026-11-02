# Vertical 3D reel renderer

Blender (Cycles CPU) render pipeline for 1080x1920 30 fps vertical reels, run on GitHub Actions.

* `.github/workflows/render.yml` — assets (Blender 4.3.2 + MakeHuman CC0, cached), optional MoMask text-to-motion, a matrix of up to 6 render jobs, then join + audio + captions + QA.
* `render/retarget.py` — retargets HumanML3D motion onto an MPFB2 rig.
* `motion/` — MoMask checkpoint list, patch, take picker and small fallback clips.
* `tools/` — audio (TTS, music/SFX, captions), `join.sh` (interpolate, upscale, captions, loudnorm) and `qa.py`.

A story lives in `stories/<name>/` (scene.py, prompts.txt, names.txt, story.json, audio, captions) and is only present in the repo while it is being rendered.

Licenses: pipeline code MIT. Blender GPL, MPFB2 GPL-3.0 (installed at job time, not vendored), MakeHuman system assets CC0, MoMask MIT, Be Vietnam Pro font OFL 1.1.
