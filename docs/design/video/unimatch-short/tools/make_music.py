"""An original 30-second music bed for the Unimatch short — synthesized here, no samples.

120 BPM (a bar is 2 s), A minor, Am–F–C–G one chord per bar. The arrangement follows the
storyboard: a ticking intro under the typed question and a riser into the logo (3 s), the groove
under routes, passes and money (5–15 s), a kickless breakdown under the three answers (15–19 s),
the groove again for decide and plan (19–25 s), a final hit on the button (28 s) and a ring-out.
Accents sit on the animation's own cues (typed letters, route ends, rows, stamps, presses).
"""
import sys
import wave

import numpy as np

SR = 48000
DUR = 30.0
N = int(SR * DUR)
rng = np.random.default_rng(7)  # seeded: the same file every run
L = np.zeros(N)
R = np.zeros(N)


def at(t):
    return int(round(t * SR))


def add(sig, t, gain=1.0, pan=0.0):
    i = at(t)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * np.sqrt(0.5 * (1 - pan))
    R[i:i + len(sig)] += sig * np.sqrt(0.5 * (1 + pan))


def tt(d):
    return np.arange(int(d * SR)) / SR


def highpass(x, w=24):
    k = np.ones(w) / w
    return x - np.convolve(x, k, mode='same')


def lowpass(x, w=8):
    k = np.ones(w) / w
    return np.convolve(x, k, mode='same')


def saw(f, d, harmonics=10, bright=4.0):
    t = tt(d)
    y = np.zeros_like(t)
    for n in range(1, harmonics + 1):
        if f * n > SR / 2.2:
            break
        y += np.sin(2 * np.pi * f * n * t) / n * np.exp(-n / bright)
    return y


def env(d, a=0.01, r=0.1, sustain=1.0):
    n = int(d * SR)
    e = np.full(n, sustain)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, sustain, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


# ── instruments ──────────────────────────────────────────────────────────────────────────────────
def kick():
    t = tt(0.45)
    f = 45 + 105 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.16)
    y[:200] += rng.standard_normal(200) * 0.25 * np.linspace(1, 0, 200)
    return y


def clap():
    t = tt(0.25)
    n = highpass(rng.standard_normal(len(t)), 10)
    e = np.zeros_like(t)
    for k, off in enumerate((0, 0.011, 0.022)):
        i = at(off)
        e[i:] += np.exp(-(t[i:] - off) / (0.012 if k < 2 else 0.09))
    return n * e * 0.6


def hat(open_=False):
    t = tt(0.25 if open_ else 0.06)
    return highpass(rng.standard_normal(len(t)), 4) * np.exp(-t / (0.08 if open_ else 0.018)) * 0.5


def pluck(f, d=0.3):
    t = tt(d)
    y = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return y * np.exp(-t / 0.11) * env(d, 0.003, 0.03)


def bell(f, d=1.6):
    t = tt(d)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.7)
         + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.35)
         + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.15))
    return y * env(d, 0.002, 0.2)


def noise_sweep(d, rise=True, peak=1.0):
    """Whoosh / riser: noise that brightens as it swells."""
    n = rng.standard_normal(int(d * SR))
    out = np.zeros_like(n)
    seg = 2400
    for s in range(0, len(n), seg):
        p = s / len(n)
        w = int(2 + (1 - p if rise else p) * 40)
        chunk = n[max(0, s - 64): s + seg + 64]
        sm = np.convolve(chunk, np.ones(w) / w, mode='same')
        piece = (chunk - sm)[64 if s else 0:][:seg] if rise else sm[64 if s else 0:][:seg]
        out[s:s + len(piece)] = piece
    t = np.linspace(0, 1, len(n))
    shape = (t ** 2.2) if rise else np.sin(np.pi * t) ** 1.5
    return out * shape * peak


def thud(f=80, d=0.35):
    t = tt(d)
    y = np.sin(2 * np.pi * (f + 60 * np.exp(-t / 0.02)) * t) * np.exp(-t / 0.09)
    y[:300] += lowpass(rng.standard_normal(300), 6) * 0.5
    return y


def click():
    t = tt(0.012)
    return highpass(rng.standard_normal(len(t)), 3) * np.exp(-t / 0.003)


# ── harmony ──────────────────────────────────────────────────────────────────────────────────────
CHORDS = [  # (bass root, chord tones)
    (110.00, [220.00, 261.63, 329.63]),   # Am
    (87.31, [174.61, 220.00, 261.63]),    # F
    (130.81, [196.00, 261.63, 329.63]),   # C
    (98.00, [196.00, 246.94, 293.66]),    # G
]
BAR, BEAT = 2.0, 0.5


def chord_at(t):
    return CHORDS[int(t // BAR) % 4]


def section_groove(t):
    return (5.0 <= t < 15.0) or (19.0 <= t < 28.0)


# pad: every bar, softer in the groove, fuller in the breakdown and the ring-out
for b in range(15):
    t0 = b * BAR
    root, tones = chord_at(t0)
    level = 0.05 if t0 < 3 else 0.09 if 15 <= t0 < 19 else 0.12 if t0 >= 28 else 0.06
    d = 2.0 if t0 < 28 else 2.0
    for f in tones:
        for cents, pan in ((-7, -0.5), (0, 0), (7, 0.5)):
            v = saw(f * 2 ** (cents / 1200), d, 8, 3.0) * env(d, 0.35, 0.45)
            add(v, t0, level / 3, pan)

# bass: eighth-note pulses on the root in the groove; held sub in the breakdown and intro
for b in range(15):
    t0 = b * BAR
    root, _ = chord_at(t0)
    if section_groove(t0):
        for k in range(16):
            tk = t0 + k * 0.125 * 1
            if k % 2:
                continue
            octave = 2 if k % 8 == 6 else 1
            add(saw(root * octave, 0.22, 6, 2.0) * env(0.22, 0.004, 0.06), tk, 0.28)
    elif t0 < 28:
        add(np.sin(2 * np.pi * root * tt(2.0)) * env(2.0, 0.2, 0.4), t0, 0.18)

# drums
for k in range(int(DUR / BEAT)):
    tk = k * BEAT
    if section_groove(tk):
        add(kick(), tk, 0.9)
        if k % 2 == 1:
            add(clap(), tk, 0.55, 0.05)
        add(hat(), tk + 0.25, 0.35, 0.3)
        if k % 4 == 3:
            add(hat(True), tk + 0.25, 0.25, 0.3)
    if tk < 3.0:  # the intro ticks: sixteenths, quiet, like a keyboard clock
        for s in range(4):
            add(hat(), tk + s * 0.125, 0.12 + 0.05 * (s == 0), -0.3)

# arpeggio: sixteenths over the chord, up an octave, in the groove
for k in range(int(DUR / 0.125)):
    tk = k * 0.125
    if not section_groove(tk) or 15 <= tk < 19:
        continue
    _, tones = chord_at(tk)
    seq = [tones[0] * 2, tones[1] * 2, tones[2] * 2, tones[1] * 2]
    add(pluck(seq[k % 4]), tk, 0.07, 0.4 if k % 2 else -0.4)

# ── accents on the animation's cues ──────────────────────────────────────────────────────────────
# 01 · typed letters
for j in range(11):
    add(click(), 0.05 + j * 0.052, 0.18, -0.2)
for j in range(5):
    add(click(), 0.70 + j * 0.056, 0.18, -0.2)
add(thud(70, 0.4), 2.0, 0.35)
add(thud(70, 0.4), 2.25, 0.3)
add(noise_sweep(1.0, rise=True, peak=0.22), 2.0)
# 02 · into one place: impact, then the tile's chime
add(kick(), 3.0, 1.0)
add(np.sin(2 * np.pi * 49 * tt(1.2)) * np.exp(-tt(1.2) / 0.5), 3.0, 0.45)
add(noise_sweep(0.5, rise=False, peak=0.18), 3.0)
add(bell(880.0), 3.5, 0.2, 0.2)
add(bell(1318.5), 3.5, 0.1, -0.2)
# 03 · route ends (tint plinks, rising through the chord)
for i, f in enumerate([659.25, 783.99, 880.0, 1046.5, 1318.5]):
    add(bell(f, 0.9), 5.0 + 1.0 + i * 0.4 + 0.42, 0.10, -0.4 + i * 0.2)
# 04 · three cards flick up
for i in range(3):
    add(noise_sweep(0.35, rise=False, peak=0.16), 9.0 + i * 0.32, 1.0, -0.3 + 0.3 * i)
# 05 · rows tick, the total lands, the stamp
for tk in (12.05, 12.55):
    add(click(), tk, 0.35)
    add(pluck(1318.5, 0.25), tk, 0.06)
add(thud(60, 0.6), 13.5, 0.55)
add(thud(110, 0.25), 14.0, 0.45)
# 06 · breakdown: three stamps and a riser back in
for tk in (15.15, 16.15, 17.15):
    add(thud(75, 0.5), tk, 0.5)
    add(highpass(rng.standard_normal(int(0.08 * SR)), 6) * np.exp(-tt(0.08) / 0.02), tk, 0.25)
add(noise_sweep(1.0, rise=True, peak=0.25), 18.0)
add(kick(), 19.0, 1.0)
# 07 · presses and the cards flying to their piles
for tk in (20.0, 21.0):
    add(click(), tk, 0.4)
    add(noise_sweep(0.4, rise=False, peak=0.14), tk + 0.08)
    add(pluck(987.77, 0.3), tk + 0.5, 0.08)
# 08 · tickets slide
for i in range(3):
    add(noise_sweep(0.35, rise=False, peak=0.13), 22.85 + i * 0.5, 1.0, 0.4)
# 09 · the button, the final hit, the ring-out
add(kick(), 28.0, 1.0)
add(np.sin(2 * np.pi * 55 * tt(2.0)) * np.exp(-tt(2.0) / 0.7), 28.0, 0.4)
add(bell(880.0, 2.0), 28.0, 0.16, 0.2)
add(bell(659.25, 2.0), 28.0, 0.12, -0.2)

# ── master: fade-in, end fade, soft clip, normalise ──────────────────────────────────────────────
mix = np.stack([L, R])
fade_in = np.clip(np.arange(N) / (0.05 * SR), 0, 1)
fade_out = np.clip((N - np.arange(N)) / (1.6 * SR), 0, 1)
mix *= fade_in * fade_out
mix = np.tanh(mix * 1.3) / np.tanh(1.3)
mix *= 0.89 / np.max(np.abs(mix))
pcm = (mix.T * 32767).astype('<i2')
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('wrote', sys.argv[1], f'{N / SR:.1f}s', 'peak', round(float(np.max(np.abs(mix))), 3))
