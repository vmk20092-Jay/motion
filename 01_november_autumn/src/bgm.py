import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt
from scipy.io import wavfile

SR, DUR = 44100, 10.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(3)

def hz(n): return 440 * 2 ** ((n - 69) / 12)
L = np.zeros(N); R = np.zeros(N)

def add(sig, start, pan=0.0, gain=1.0):
    i = int(start * SR); n = min(len(sig), N - i)
    if n <= 0: return
    L[i:i + n] += sig[:n] * gain * np.sqrt(0.5 * (1 - pan))
    R[i:i + n] += sig[:n] * gain * np.sqrt(0.5 * (1 + pan))

def piano(note, dur=3.5, vel=0.5):
    """soft felt-piano: few harmonics, exponential decay, slight detune"""
    n = int(dur * SR); tt = np.arange(n) / SR; f = hz(note)
    s = np.zeros(n)
    for k, a in [(1, 1), (2, .35), (3, .12), (4, .06)]:
        s += a * np.sin(2 * np.pi * f * k * tt * (1 + .0007 * k)) * np.exp(-tt * (1.2 + k * .9))
    att = np.minimum(1, tt / .008)
    return s * att * vel

def pad(notes, dur, vel=.07):
    n = int(dur * SR); tt = np.arange(n) / SR
    s = np.zeros(n)
    for note in notes:
        for d in (-0.08, 0.08):
            f = hz(note + d)
            s += np.sin(2 * np.pi * f * tt) + .3 * np.sin(4 * np.pi * f * tt)
    env = np.minimum(1, tt / 1.2) * np.minimum(1, (dur - tt) / 1.0).clip(0)
    return s * env * vel / len(notes)

# progression aligned to scenes: Cmaj9 | Am9 (cool) | Fmaj9 (warm) | Cmaj7add9 (resolve)
chords = [
    (0.0,  [48, 55, 59, 62, 64], [64, 67, 71, 74, 76, 74, 71]),
    (2.6,  [45, 52, 55, 59, 60], [64, 67, 71, 72, 71, 67, 64]),
    (5.2,  [41, 48, 52, 55, 57], [65, 69, 72, 76, 79, 76, 72]),
    (7.8,  [48, 55, 59, 62, 64], [67, 71, 74, 76, 79]),
]
beat = 60 / 72 / 2  # eighth notes at 72 bpm
for st, padn, arp in chords:
    dur = 2.9 if st < 7.8 else 2.6
    p = pad(padn, dur)
    add(p, st, pan=-.3); add(p, st, pan=.3)
    add(piano(padn[0] - 12 + 12, 4, .45), st + .02, pan=-.2)          # bass note
    for k, nn in enumerate(arp):
        tt0 = st + .15 + k * beat
        if tt0 > 9.2: break
        add(piano(nn, 3, .22 + .06 * rng.random()), tt0 + rng.normal(0, .008), pan=np.sin(k) * .5)

# accent: high bell on "11월" landing and on final title
for tt0, nn in [(0.95, 88), (8.1, 91)]:
    add(piano(nn, 3, .12), tt0, pan=.4)

# wind gust synced with scene B exit (4.4-5.7s), band-passed noise sweep
n = int(1.6 * SR); tt = np.arange(n) / SR
noise = rng.normal(0, 1, n)
sos = butter(2, [300, 2400], btype='band', fs=SR, output='sos')
w = sosfilt(sos, noise) * np.sin(np.pi * tt / 1.6) ** 2 * .12
add(w, 4.35, pan=-.6); add(np.roll(w, 900), 4.35, pan=.6)

# leaf rustle / vinyl crackle bed
crk = (rng.random(N) > .9994) * rng.normal(0, .15, N)
crk = sosfilt(butter(1, 1500, btype='high', fs=SR, output='sos'), crk)
L += crk * .5; R += np.roll(crk, 300) * .5

# reverb: decaying noise IR, per channel
irn = int(2.4 * SR); it = np.arange(irn) / SR
def ir(seed):
    r = np.random.default_rng(seed).normal(0, 1, irn) * np.exp(-it * 2.6)
    return sosfilt(butter(1, 5000, fs=SR, output='sos'), r) / 60
wetL = fftconvolve(L, ir(1))[:N]; wetR = fftconvolve(R, ir(2))[:N]
L = L * .7 + wetL * .55; R = R * .7 + wetR * .55

# warm low-pass + fade in/out
lp = butter(2, 7000, fs=SR, output='sos')
L, R = sosfilt(lp, L), sosfilt(lp, R)
env = np.minimum(1, t / .25) * np.clip((DUR - t) / 1.2, 0, 1) ** 1.5
out = np.stack([L, R], 1) * env[:, None]
out /= np.abs(out).max() / 0.89
wavfile.write('bgm.wav', SR, (out * 32767).astype(np.int16))
print('rms dB', 20 * np.log10(np.sqrt((out ** 2).mean())))
