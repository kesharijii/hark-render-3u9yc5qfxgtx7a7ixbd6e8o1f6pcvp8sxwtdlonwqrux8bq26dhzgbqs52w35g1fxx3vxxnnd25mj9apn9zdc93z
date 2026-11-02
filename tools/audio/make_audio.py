"""Original background music (synthesised marimba/pluck + soft bass, C-G-Am-F, 104 bpm) + SFX + narration mix."""
import numpy as np, subprocess, json, wave
SR = 48000; DUR = 57.0; N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(3)
def note(f, dur, amp=0.3, kind='mar'):
    n = int(dur * SR); tt = np.arange(n) / SR
    if kind == 'mar':
        env = np.exp(-tt * 7.0)
        s = np.sin(2*np.pi*f*tt) + 0.35*np.sin(2*np.pi*f*4*tt)*np.exp(-tt*25) + 0.15*np.sin(2*np.pi*f*2*tt)
    elif kind == 'bass':
        env = np.minimum(1, tt*40) * np.exp(-tt * 2.5)
        s = np.sin(2*np.pi*f*tt) + 0.2*np.sin(2*np.pi*2*f*tt)
    else:  # pad
        env = np.minimum(1, tt*2) * np.minimum(1, (dur-tt)*2)
        s = sum(np.sin(2*np.pi*f*k*tt + rng.uniform(0, 6)) / k for k in (1, 2, 3)) * 0.5
    return s * env * amp
def add(buf, x, at):
    i = int(at*SR); j = min(len(buf), i+len(x))
    if j > i: buf[i:j] += x[:j-i]
mus = np.zeros(N)
bpm = 104; beat = 60/bpm
mid = lambda m: 440*2**((m-69)/12)
chords = [(60, [60, 64, 67, 72]), (55, [55, 59, 62, 67]), (57, [57, 60, 64, 69]), (53, [53, 57, 60, 65])]
mel = [72, 74, 76, 79, 76, 74, 72, 67, 69, 72, 74, 72, 69, 67, 65, 67]
bar = 0; tt0 = 0.0
while tt0 < DUR:
    root, ch = chords[bar % 4]
    add(mus, note(mid(root-12), beat*4, 0.22, 'bass'), tt0)
    add(mus, note(mid(root-12), beat*1.5, 0.12, 'bass'), tt0 + beat*2.5)
    add(mus, note(mid(ch[1]), beat*4, 0.035, 'pad'), tt0); add(mus, note(mid(ch[2]), beat*4, 0.035, 'pad'), tt0)
    for k in range(8):   # arpeggio eighths
        add(mus, note(mid(ch[[0, 2, 1, 3, 2, 1, 3, 2][k]]), beat*0.9, 0.07, 'mar'), tt0 + k*beat/2)
    if bar % 2 == 1:
        for k in range(4):
            add(mus, note(mid(mel[(bar*4+k) % 16]), beat*1.2, 0.09, 'mar'), tt0 + k*beat)
    bar += 1; tt0 += beat*4
# gentle fade in/out, duck the music a little at night (purr scene) and lift it for the kicker
g = np.ones(N); g *= np.clip(t/1.0, 0, 1); g *= np.clip((DUR - t)/2.5, 0, 1)
g *= np.where((t > 31.6) & (t < 38.6), 0.55, 1.0)
mus *= g
sfx = np.zeros(N)
# honks at "Cars honk" (26.66 s)
for at, dur in ((26.70, 0.32), (27.10, 0.45)):
    n = int(dur*SR); tt = np.arange(n)/SR
    h = (np.sign(np.sin(2*np.pi*415*tt)) + np.sign(np.sin(2*np.pi*349*tt))) * 0.5
    h = np.convolve(h, np.ones(12)/12, 'same') * np.minimum(1, tt*60) * np.minimum(1, (dur-tt)*60)
    add(sfx, h*0.10, at)
# purr: low rumble 25 Hz modulated noise, 33.9 s -> 38.6 s, swelling under "the windows shake"
n = int(4.7*SR); tt = np.arange(n)/SR
noise = np.convolve(rng.standard_normal(n), np.ones(160)/160, 'same')
purr = noise * (0.55 + 0.45*np.sin(2*np.pi*24*tt)) * (0.5 + 0.5*np.sin(2*np.pi*0.55*tt - 1.5))
purr *= np.minimum(1, tt/0.6) * np.minimum(1, (4.7-tt)/0.6) * (0.6 + 0.6*np.clip((tt-1.2)/1.5, 0, 1))
add(sfx, purr*1.6, 33.9)
# distant car alarm at 36.55 s: alternating two-tone whoop
n = int(2.0*SR); tt = np.arange(n)/SR
f = np.where((tt*4).astype(int) % 2 == 0, 900, 650)
al = np.sin(2*np.pi*np.cumsum(f)/SR) * np.minimum(1, tt*20) * np.minimum(1, (2.0-tt)*4)
add(sfx, al*0.035, 36.55)
# soft whoosh at the truck reversing beep (27.72 s): three beeps
for k in range(3):
    n = int(0.18*SR); tt = np.arange(n)/SR
    add(sfx, np.sin(2*np.pi*1150*tt)*0.04*np.minimum(1, tt*80)*np.minimum(1, (0.18-tt)*80), 27.9 + k*0.42)
bed = mus*0.55 + sfx
bed = bed / max(1e-6, np.abs(bed).max()) * 0.5
st = np.stack([bed, bed], 1)
w = wave.open('bed.wav', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st*32767).astype(np.int16).tobytes()); w.close()
