import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR, DUR, B = 44100, 30.0, 0.5      # 120 BPM, beat = 0.5 s (matches video.py)
N = int(SR * DUR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(5)
def hz(n): return 440 * 2 ** ((n - 69) / 12)
def add(sig, t0, g=1., pan=0.):
    i = int(t0 * SR); n = min(len(sig), N - i)
    if n <= 0 or i < 0: return
    L[i:i+n] += sig[:n] * g * np.sqrt(.5 * (1 - pan)); R[i:i+n] += sig[:n] * g * np.sqrt(.5 * (1 + pan))
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype='band', fs=SR, output='sos'), x)
def hp(x, f): return sosfilt(butter(2, f, btype='high', fs=SR, output='sos'), x)
def lp(x, f): return sosfilt(butter(2, f, fs=SR, output='sos'), x)

BREAKS = [(5.5, 7.0), (17.5, 19.0)]             # riser sections, no kick
END = 28.0                                       # last hit; drums stop
def in_break(t): return any(a <= t < b for a, b in BREAKS) 

# --- drums ---
def kick():
    n = int(.32 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9) + .3 * np.exp(-t * 300) * rng.normal(0, 1, n)
def clap():
    n = int(.22 * SR); t = np.arange(n) / SR
    env = np.exp(-t * 22) * (1 + .6 * np.exp(-((t % .011) * 400)))
    return bp(rng.normal(0, 1, n), 900, 3200) * env * 1.4
def hat(o=False):
    n = int((.18 if o else .05) * SR); t = np.arange(n) / SR
    return hp(rng.normal(0, 1, n), 7000) * np.exp(-t * (14 if o else 70))
K, C = kick(), clap()
for k in range(56):
    t = k * B
    if not in_break(t):
        add(K, t, .95)
        if k % 2 == 1: add(C, t, .45, .1)
        add(hat(k % 4 == 3), t + B / 2, .22, .3)
        add(hat(), t + B / 4, .08, -.3); add(hat(), t + 3 * B / 4, .08, -.3)
    else:
        add(C, t, .25)                                   # half-time claps in the build
# snare roll into the drop
for st in (6.0, 18.0):
  for i in range(16):
    t = st + i * (1.0 / 16)
    add(clap(), t, .12 + .3 * i / 16)

# --- harmony: C | G | Am | F (1 bar each = 2 s), bright pop-house ---
PROG = [(48, [60, 64, 67, 71]), (43, [59, 62, 67, 69]), (45, [60, 64, 69, 71]), (41, [60, 65, 69, 72])]
def saw(f, dur, det=0.):
    t = np.arange(int(dur * SR)) / SR
    return sum(2 * ((t * f * (1 + d)) % 1) - 1 for d in (-det, 0, det)) / 3
def stab(notes, dur=.22):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(saw(hz(m), dur, .006) for m in notes) / len(notes)
    return lp(s, 3800) * np.exp(-t * 11) * np.minimum(1, t / .004)
def bass(note, dur=.24):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * hz(note) * t) + .35 * saw(hz(note), dur)
    return lp(s, 900) * np.minimum(1, t / .005) * np.exp(-t * 5)
STAB_PAT = [0, .75, 1.5, 2.5, 3.25]               # beats within a bar (syncopated)
for bar in range(14):
    t0 = bar * 4 * B
    root, ch = PROG[bar % 4]
    for k in range(4):                               # offbeat bass (house)
        tb = t0 + k * B + B / 2
        if tb < END and not in_break(tb): add(bass(root), tb, .55)
    for sbt in STAB_PAT:
        ts = t0 + sbt * B
        if ts >= END: continue
        g = .16 if in_break(ts) else .30
        add(stab(ch), ts, g, -.25); add(stab([n + 12 for n in ch[:2]]), ts + .01, g * .4, .35)

# --- pluck melody hook on the drop & brand section ---
MEL = [(7.0, 76), (7.25, 79), (7.5, 81), (8.0, 79), (8.5, 76), (8.75, 74), (9.0, 76), (9.5, 72),
       (19.0, 76), (19.25, 79), (19.5, 81), (20.0, 79), (20.5, 76), (20.75, 74), (21.0, 76), (21.5, 72),
       (24.0, 79), (24.25, 81), (24.5, 84), (25.0, 83), (25.5, 79), (26.0, 81), (26.5, 84),
       (27.0, 83), (27.25, 81), (27.5, 79), (28.0, 84)]
for t0, m in MEL:
    n = int(.4 * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * hz(m) * t) + .5 * np.sin(4 * np.pi * hz(m) * t) + .2 * saw(hz(m), .4)) * np.exp(-t * 7)
    add(s, t0, .2, .2)

# --- riser 5.5 -> 7.0, impacts at the drop and the brand slam ---
n = int(1.5 * SR); t = np.arange(n) / SR
noise = rng.normal(0, 1, n); riser = np.zeros(n)
for i in range(0, n, 2048):                          # sweeping band-pass in blocks
    f = 500 + 7000 * (i / n) ** 2
    seg = bp(noise[max(0, i - 4096):i + 2048], f * .7, min(f * 1.4, 20000))[-min(2048, n - i):]
    riser[i:i + len(seg)] = seg
tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * (t / 1.5) ** 2) / SR) * .25
add((riser + tone) * (t / 1.5) ** 2, 5.5, .35); add((riser + tone) * (t / 1.5) ** 2, 17.5, .4)
def impact():
    n = int(1.2 * SR); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(35 + 60 * np.exp(-t * 6)) / SR) * np.exp(-t * 3)
    crash = hp(rng.normal(0, 1, n), 4000) * np.exp(-t * 3.5) * .5
    return boom + crash
add(impact(), 7.0, .7); add(impact(), 19.0, .7); add(impact(), 24.0, .6)
add(impact(), 28.0, .55)
_t = np.arange(int(1.9 * SR)) / SR
add(lp(sum(saw(hz(n), 1.9, .006) for n in PROG[0][1] + [72, 76]) / 6, 3000) * np.exp(-_t * 1.6), 28.0, .45)   # final chord

# --- mixdown: sidechain pump, light room, master ---
pump = np.ones(N)
for k in range(56):
    t0 = k * B
    if in_break(t0): continue
    i = int(t0 * SR); m = min(int(.3 * SR), N - i)
    pump[i:i+m] = np.minimum(pump[i:i+m], .45 + .55 * (np.arange(m) / m) ** .6)
irn = int(.9 * SR); ir = rng.normal(0, 1, irn) * np.exp(-np.arange(irn) / SR * 6) / 120
L = L * pump * .85 + fftconvolve(L, ir)[:N] * .3
R = R * pump * .85 + fftconvolve(R, ir)[:N] * .3
out = np.stack([L, R], 1)
out = np.tanh(out / np.abs(out).max() * 1.6) / np.tanh(1.6) * .9   # soft clip for loudness
fade = np.clip((DUR - np.arange(N) / SR) / 1.2, 0, 1)[:, None]
wavfile.write('music.wav', SR, (out * fade * 32767).astype(np.int16))
print('ok')
