import numpy as np, wave
from scipy.signal import butter, sosfilt

SR = 48000
DUR = 30.0
N = int(SR * DUR)
rng = np.random.default_rng(3)
t_all = np.arange(N) / SR


def read(path):
    with wave.open(path) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return a


def place(buf, sig, at, gain=1.0):
    i = int(at * SR)
    j = min(N, i + len(sig))
    if j > i:
        buf[i:j] += sig[: j - i] * gain


def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)


def note(m):
    return 440 * 2 ** ((m - 69) / 12)


# ---------------- music ----------------
BPM = 120
beat = 60 / BPM
L = np.zeros(N); R = np.zeros(N)
drums = np.zeros(N); bass = np.zeros(N); arpL = np.zeros(N); arpR = np.zeros(N); pad = np.zeros(N)

# chords: Am F C G (2 beats each? -> one bar = 4 beats = 2s each)
prog_ = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # A3 C4 E4 / F3 A3 C4 / C3 E3 G3 / G3 B3 D4
roots = [45, 41, 36, 43]

def chord_at(tt):
    return int(tt // (4 * beat)) % 4

# kick
def kick():
    d = 0.32; n = int(d * SR); tt = np.arange(n) / SR
    f = 50 + 90 * np.exp(-tt * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-tt * 9) + 0.15 * np.exp(-tt * 300) * rng.standard_normal(n)

def hat(d=0.05):
    n = int(d * SR); tt = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-tt * 70)

def clap():
    n = int(0.22 * SR); tt = np.arange(n) / SR
    env = np.exp(-tt * 18)
    for k in (0.0, 0.012, 0.024):
        env += np.where(tt >= k, np.exp(-(tt - k) * 120), 0) * 0.6
    return bp(rng.standard_normal(n), 900, 4000) * env * 0.5

K, Hh, Cl = kick(), hat(), clap()
side = np.ones(N)  # sidechain envelope
nbeats = int(DUR / beat)
for b in range(nbeats):
    tb = b * beat
    if tb >= 29.0:
        break
    if tb >= 1.9:  # drums enter after the triangle closes
        place(drums, K, tb, 0.9)
        i = int(tb * SR); n = int(0.3 * SR)
        side[i:i + n] = np.minimum(side[i:i + n], 1 - 0.6 * np.exp(-np.arange(min(n, N - i)) / SR * 14))
        if b % 2 == 1:
            place(drums, Cl, tb, 0.55)
        place(drums, Hh, tb + beat / 2, 0.35)
        place(drums, hat(0.03), tb + beat / 4, 0.12)
        place(drums, hat(0.03), tb + 3 * beat / 4, 0.12)
    else:
        place(drums, hat(0.03), tb + beat / 2, 0.15)

# bass: eighth notes, saw, lowpassed
for e in range(int(DUR / (beat / 2))):
    te = e * beat / 2
    if te < 1.9 or te >= 29.0:
        continue
    f = note(roots[chord_at(te)])
    n = int(beat / 2 * SR * 0.9); tt = np.arange(n) / SR
    saw = 2 * ((tt * f) % 1) - 1 + 0.5 * np.sin(2 * np.pi * f / 2 * tt)
    env = np.minimum(1, tt * 200) * np.exp(-tt * 5)
    place(bass, saw * env, te, 0.35)
bass = lp(bass, 420, 4)

# arp: 16ths, plucky square, ping-pong stereo
pat = [0, 1, 2, 1, 2, 0, 1, 2]
for s in range(int(DUR / (beat / 4))):
    ts = s * beat / 4
    if ts >= 29.0:
        continue
    ch = prog_[chord_at(ts)]
    m = ch[pat[s % 8] % 3] + 12 + (12 if s % 16 in (6, 14) else 0)
    f = note(m)
    n = int(0.22 * SR); tt = np.arange(n) / SR
    sq = np.sign(np.sin(2 * np.pi * f * tt)) * 0.5 + np.sin(2 * np.pi * f * 2 * tt) * 0.3
    env = np.minimum(1, tt * 400) * np.exp(-tt * 16)
    g = 0.16 if ts >= 1.9 else 0.10 * min(1, ts / 1.5)
    if s % 2 == 0:
        place(arpL, sq * env, ts, g); place(arpR, sq * env, ts + 0.12, g * 0.35)
    else:
        place(arpR, sq * env, ts, g); place(arpL, sq * env, ts + 0.12, g * 0.35)
arpL = lp(arpL, 3800); arpR = lp(arpR, 3800)

# pad: detuned saws per bar
for bar in range(int(DUR / (4 * beat)) + 1):
    tb = bar * 4 * beat
    ch = prog_[bar % 4]
    n = int(4 * beat * SR + 0.4 * SR); tt = np.arange(n) / SR
    sig = np.zeros(n)
    for m in ch:
        for det in (-0.12, 0.0, 0.12):
            f = note(m + det)
            sig += 2 * ((tt * f + rng.random()) % 1) - 1
    env = np.minimum(1, tt / 0.4) * np.minimum(1, (n / SR - tt) / 0.4)
    place(pad, sig * env, tb, 0.025)
pad = lp(pad, 1500, 2)

# final chord ring-out at 29.0
n = int(1.0 * SR); tt = np.arange(n) / SR
fin = np.zeros(n)
for m in [57, 60, 64, 69, 76]:
    fin += np.sin(2 * np.pi * note(m) * tt) * np.exp(-tt * 3)
place(pad, fin, 29.0, 0.12)

# riser into the finale
n = int(1.2 * SR); tt = np.arange(n) / SR
riser = bp(rng.standard_normal(n), 800, 6000) * (tt / 1.2) ** 2
place(drums, riser, 23.8, 0.18)

music_L = drums + bass * side + arpL * side + pad * side
music_R = drums + bass * side + arpR * side + pad * side

# ---------------- voice ----------------
VO = [(1, 0.9), (2, 4.65), (3, 7.5), (4, 10.4), (5, 14.15), (6, 17.25), (7, 19.1), (8, 20.4), (9, 21.5), (10, 22.95), (11, 25.15)]
voice = np.zeros(N)
for i, at in VO:
    v = read(f'vo/r{i}.wav')
    v = v / (np.max(np.abs(v)) + 1e-9)
    place(voice, v, at, 0.85)
voice = hp(voice, 90)
# light presence boost
voice = voice + 0.25 * bp(voice, 2500, 6000)

# ducking envelope from voice
env = np.abs(voice)
env = lp(env, 8, 1)
env = env / (env.max() + 1e-9)
duck = 1 - 0.5 * np.clip(env * 4, 0, 1)

# ---------------- sfx ----------------
sfxL = np.zeros(N); sfxR = np.zeros(N)

def whoosh(d=0.45, lo=300, hi=5000, pan=0.0):
    n = int(d * SR); tt = np.arange(n) / SR
    noise = rng.standard_normal(n)
    fcs = np.geomspace(min(lo, hi), max(lo, hi), 7)
    k = np.sin(np.pi * tt / d * 0.5)  # 0..1 sweep position
    if hi < lo: k = 1 - k
    pos = k * (len(fcs) - 1)
    out = np.zeros(n)
    for j, fc in enumerate(fcs):
        w = np.clip(1 - np.abs(pos - j), 0, 1)
        out += bp(noise, fc * 0.7, min(fc * 1.4, SR / 2 - 100)) * w
    s = out * np.sin(np.pi * tt / d) ** 2
    s = s / (np.max(np.abs(s)) + 1e-9)
    return s * (1 - pan * 0.6), s * (1 + pan * 0.6)

def click(f=1800, d=0.06):
    n = int(d * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.exp(-tt * 60)

def pop(f0=500, f1=1400, d=0.12):
    n = int(d * SR); tt = np.arange(n) / SR
    f = f0 + (f1 - f0) * (tt / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 25)

def chime(m=81, d=0.8):
    n = int(d * SR); tt = np.arange(n) / SR
    f = note(m)
    return (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 2 * tt) + 0.25 * np.sin(2 * np.pi * f * 3 * tt)) * np.exp(-tt * 5)

def add_st(sig, at, g, pan=0.0):
    if isinstance(sig, tuple):
        place(sfxL, sig[0], at, g); place(sfxR, sig[1], at, g)
    else:
        place(sfxL, sig, at, g * (1 - pan * 0.6)); place(sfxR, sig, at, g * (1 + pan * 0.6))

# dots
for at, f in [(0.15, 900), (0.3, 1200), (0.45, 1500)]:
    add_st(pop(f * 0.6, f), at, 0.25)
# lines grow
add_st(whoosh(0.6, 300, 4000, -0.5), 0.7, 0.35)
add_st(whoosh(0.6, 300, 4000, 0.5), 1.0, 0.35)
add_st(whoosh(0.6, 300, 4000, 0.0), 1.3, 0.35)
add_st(chime(81, 1.2), 2.0, 0.12)
add_st(whoosh(0.7, 400, 7000), 1.7, 0.3)           # title
for at in (2.0, 2.15, 2.3):
    add_st(click(2200), at, 0.15)
add_st(whoosh(0.5, 600, 5000, -0.3), 4.0, 0.2)     # header
# section 2
add_st(click(1600), 4.6, 0.22); add_st(whoosh(0.4, 500, 5000), 4.5, 0.2)
add_st(click(2400), 5.0, 0.3, -0.4); add_st(click(2400), 5.25, 0.3, 0.4)
add_st(pop(700, 1600), 5.7, 0.22)
add_st(click(1500), 7.2, 0.25); add_st(click(1600), 7.45, 0.22)
add_st(whoosh(0.5, 400, 5000), 7.4, 0.2)
# section 3: fold
add_st(whoosh(0.7, 300, 3000), 10.2, 0.25)
add_st(click(1600), 10.4, 0.2)
add_st(whoosh(1.8, 200, 3000, 0.3), 10.8, 0.4)
add_st(chime(84, 1.0), 12.6, 0.16)
add_st(whoosh(1.0, 300, 3000, -0.3), 13.2, 0.3)
add_st(click(2400), 14.0, 0.25, -0.4); add_st(click(2400), 14.25, 0.25, 0.4)
add_st(click(1600), 14.1, 0.2)
add_st(pop(700, 1600), 15.0, 0.22)
# section 4
add_st(click(1600), 17.25, 0.2)
add_st(whoosh(1.0, 6000, 400), 17.4, 0.35)  # falling whoosh for BH
add_st(click(1200), 18.4, 0.3)
for at, m in [(19.1, 76), (20.4, 79), (21.5, 83)]:
    add_st(whoosh(0.4, 600, 6000, 0.6), at - 0.05, 0.22)
    add_st(chime(m, 0.6), at, 0.12)
add_st(whoosh(0.5, 500, 6000), 22.85, 0.3)
add_st(chime(88, 1.2), 22.95, 0.14)
# finale
add_st(whoosh(1.6, 200, 5000), 25.1, 0.4)
for at, pan in [(25.35, -0.6), (25.8, 0.6), (26.25, 0.0)]:
    add_st(pop(600, 1500), at, 0.25, pan); add_st(click(2000), at, 0.12, pan)
add_st(whoosh(0.6, 500, 6000), 26.65, 0.25)
add_st(chime(81, 1.4), 27.1, 0.14)

# ---------------- mix ----------------
mg = 0.36
fade = np.clip((DUR - t_all) / 0.6, 0, 1) * np.clip(t_all / 0.3, 0, 1)
outL = (music_L * mg * duck + sfxL * 0.9 + voice) * fade
outR = (music_R * mg * duck + sfxR * 0.9 + voice) * fade
st = np.stack([outL, outR], 1)
st = np.tanh(st * 1.1) / np.tanh(1.1)  # soft limiter
st = st / np.max(np.abs(st)) * 0.93
with wave.open('out/audio.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print('ok', st.shape)
def rms(x): return 20*np.log10(np.sqrt(np.mean(x**2))+1e-12)
m = (env > 0.15)
print('voice rms (active)', rms(voice[m]), 'music under voice', rms((music_L*mg*duck)[m]), 'music free', rms((music_L*mg)[~m][int(3*SR):]))
