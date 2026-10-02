"""Synthesises the 15s soundtrack (120 BPM), hit-synced to the cuts in scene.js. Writes audio.wav."""
import wave
import numpy as np

SR = 48000
DUR = 15.0
N = int(SR * DUR)
L = np.zeros(N)
R = np.zeros(N)
rng = np.random.default_rng(3)


def add(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - max(0, pan))
    R[i:i + len(sig)] += sig * gain * (1 + min(0, pan))


def tt(d):
    return np.arange(int(d * SR)) / SR


def lowpass(x, cutoff):
    """One-pole lowpass; cutoff may be scalar or per-sample array (Hz)."""
    c = np.broadcast_to(np.asarray(cutoff, float), x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def saw(f, t):
    return 2 * ((f * t) % 1) - 1


# ---- instruments ----
def kick():
    t = tt(0.45)
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7) + 0.3 * rng.standard_normal(len(t)) * np.exp(-t * 300)


def hat(open_=False):
    t = tt(0.25 if open_ else 0.06)
    n = rng.standard_normal(len(t))
    n = np.diff(n, prepend=0)
    return n * np.exp(-t * (14 if open_ else 60)) * 0.5


def clap():
    t = tt(0.3)
    n = lowpass(rng.standard_normal(len(t)), 3500) - lowpass(rng.standard_normal(len(t)), 600) * 0.5
    env = np.exp(-t * 16) + 0.6 * np.exp(-((t - 0.012) % 0.011) * 400) * (t < 0.035)
    return n * env * 0.9


def impact(big=1.0):
    t = tt(2.2)
    f = 30 + 70 * np.exp(-t * 6)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.8)
    noise = lowpass(rng.standard_normal(len(t)), 2500 * np.exp(-t * 3) + 200) * np.exp(-t * 4) * 1.4
    return (sub + noise) * big


def riser(d):
    t = tt(d)
    k = t / d
    n = lowpass(rng.standard_normal(len(t)), 300 + 9000 * k ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(180 + 1400 * k ** 3) / SR) * 0.25
    return (n * 0.8 + tone) * k ** 2


def whoosh(d=0.35):
    t = tt(d)
    k = t / d
    env = np.sin(np.pi * k) ** 2
    return lowpass(rng.standard_normal(len(t)), 600 + 5000 * np.sin(np.pi * k)) * env


def tick():
    t = tt(0.02)
    return np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 400) * 0.5


def pluck(f, d=0.9):
    t = tt(d)
    return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)) * np.exp(-t * 4.5)


# ---- arrangement ----
BEAT = 0.5
NOTE = {'A1': 55.0, 'F1': 43.65, 'C2': 65.41, 'G1': 49.0}
CHORDS = {'Am': [220.0, 261.63, 329.63], 'F': [174.61, 220.0, 261.63], 'C': [196.0, 261.63, 329.63], 'G': [196.0, 246.94, 293.66],
          'Fmaj7': [174.61, 220.0, 261.63, 329.63], 'Cadd9': [130.81, 196.0, 293.66, 329.63]}
PROG = [('Am', 'A1'), ('F', 'F1'), ('C', 'C2'), ('G', 'G1')]

# pad
t_all = np.arange(N) / SR
pad = np.zeros(N)
segments = [(0.0, 1.5, 'Am')] + [(1.5 + i * 2, 3.5 + i * 2, PROG[i % 4][0]) for i in range(5)] + [(11.5, 13.25, 'Fmaj7'), (13.25, 15.0, 'Cadd9')]
for a, b, ch in segments:
    i0, i1 = int(a * SR), int(b * SR)
    tt_ = t_all[i0:i1]
    for f in CHORDS[ch]:
        for det in (-0.12, 0.0, 0.11):
            pad[i0:i1] += saw(f * (1 + det / 100), tt_) / 9
swell = np.clip(t_all / 1.5, 0, 1) * 0.6 + 0.4
cut = 400 + 2500 * np.clip(t_all / 1.5, 0, 1) - 1200 * ((t_all > 11.5) & (t_all < 12.3))
pad = lowpass(pad, cut) * swell * 0.55
L += pad * 0.9
R += np.roll(pad, 240) * 0.9

# drums 1.5 – 11.5
for i in range(20):
    b = 1.5 + i * BEAT
    halftime = 3.5 <= b < 6.0
    if not halftime or i % 2 == 0:
        add(kick(), b, 1.0)
    add(hat(), b + BEAT / 2, 0.45, pan=0.3)
    if b >= 6.0 and i % 2 == 1:
        add(clap(), b, 0.55, pan=-0.1)
    if b >= 9.0:
        add(hat(), b + BEAT / 4, 0.25, pan=-0.3)
        add(hat(), b + 3 * BEAT / 4, 0.25, pan=0.3)

# bass: eighth notes, sidechained
bass = np.zeros(N)
for i in range(40):
    s = 1.5 + i * BEAT / 2
    if s >= 11.5:
        break
    bar = int((s - 1.5) // 2) % 4
    f = NOTE[PROG[bar][1]] * (2 if i % 4 == 3 else 1)
    t = tt(BEAT / 2)
    note = saw(f, t) * np.exp(-t * 6)
    i0 = int(s * SR)
    bass[i0:i0 + len(t)] += note[: N - i0]
bass = lowpass(bass, 700) * 0.9
duck = np.ones(N)
for i in range(20):
    b = 1.5 + i * BEAT
    i0 = int(b * SR)
    d = tt(0.25)
    duck[i0:i0 + len(d)] = np.minimum(duck[i0:i0 + len(d)], 1 - 0.8 * np.exp(-d * 14))
L += bass * duck
R += bass * duck

# fx
add(riser(1.45), 0.05, 0.7)
add(riser(1.0), 10.5, 0.8)
add(riser(0.5), 3.0, 0.35)
for t0, g in [(1.5, 1.0), (6.0, 1.0), (7.4, 0.7), (11.5, 1.1), (12.3, 0.45)]:
    add(impact(g), t0, 0.9)
for t0 in (2.5, 3.0):
    add(impact(0.35), t0, 0.8)
for t0 in (2.25, 5.6):
    add(whoosh(0.4), t0, 0.5)
for t0, p in [(8.85, 0.4), (9.35, -0.4), (9.85, 0.4)]:
    add(whoosh(0.18), t0, 0.6, pan=p)

# typing ticks (must match typed() ranges in scene.js)
for text_, a, b in [('> summoning grok_bot', 0.1, 0.95), ("@grok explain black holes like I'm five", 3.8, 4.5), ('WANT TO ACTUALLY PUT AI TO WORK?', 11.6, 12.2)]:
    n = len(text_)
    for c in range(1, n + 1):
        if text_[c - 1] != ' ':
            add(tick(), a + (c / n) * (b - a), 0.35, pan=((c * 37) % 11 - 5) / 10)
# streamed reply blips
for i in range(18):
    add(tick() * 0.6, 5.0 + i * 0.7 / 18, 0.25, pan=0.2)

# outro arpeggio
arp = [349.23, 440.0, 523.25, 659.25, 523.25, 440.0, 392.0, 523.25, 587.33, 659.25, 587.33, 523.25]
for i, f in enumerate(arp):
    add(pluck(f), 12.3 + i * 0.22, 0.22, pan=0.5 if i % 2 else -0.5)

# master
fade = np.clip((DUR - t_all) / 0.35, 0, 1)
L, R = np.tanh(L * 0.9) * fade, np.tanh(R * 0.9) * fade
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = L / peak * 0.89, R / peak * 0.89
data = (np.stack([L, R], 1) * 32767).astype('<i2')
with wave.open('audio.wav', 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(data.tobytes())
print('wrote audio.wav')
