"""Soundtrack synthesizer for the promo.

Reads sfx.json (exported by render.js from the same timeline the visuals use)
and writes a stereo 48 kHz WAV: a 128 BPM track (A minor, Am-F-C-G) plus
sound design hits locked to every on-screen event.

Usage: python3 synth.py sfx.json out.wav
"""
import json
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
BPM = 128
BEAT = 60 / BPM
rng = np.random.default_rng(42)


def t_axis(d):
    return np.arange(int(d * SR)) / SR


def env(d, a=0.005, decay=None):
    t = t_axis(d)
    e = np.minimum(1, t / max(a, 1e-4))
    if decay:
        e *= np.exp(-t / decay)
    return e


def filt(x, kind, f):
    sos = butter(2, f, btype=kind, fs=SR, output='sos')
    return sosfilt(sos, x)


def sweep_bp(x, f0, f1, q=2.0):
    """Time-varying state-variable band-pass (log sweep f0 -> f1)."""
    n = len(x)
    fs = f0 * (f1 / f0) ** (np.arange(n) / max(1, n - 1))
    out = np.zeros(n)
    low = band = 0.0
    damp = 1 / q
    for i in range(n):
        f = 2 * np.sin(np.pi * min(fs[i], SR / 6) / SR)
        high = x[i] - low - damp * band
        band += f * high
        low += f * band
        out[i] = band
    return out


def noise(d):
    return rng.standard_normal(int(d * SR))


def saw(freq, d, detune=(0,)):
    t = t_axis(d)
    s = np.zeros_like(t)
    for c in detune:
        f = freq * 2 ** (c / 1200)
        s += 2 * ((t * f + rng.random()) % 1) - 1
    return s / len(detune)


def sine_sweep(f0, f1, d, curve=8):
    t = t_axis(d)
    f = f1 + (f0 - f1) * np.exp(-t * curve)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def mix(*xs):
    """Sum arrays of different lengths (zero-padded)."""
    out = np.zeros(max(len(x) for x in xs))
    for x in xs:
        out[:len(x)] += x
    return out


NOTE = lambda n: 440 * 2 ** ((n - 69) / 12)  # midi -> Hz

# ---------------------------------------------------------------- instruments
def kick():
    d = .45
    return mix(sine_sweep(170, 44, d, 28) * env(d, .001, .16), filt(noise(.02), 'highpass', 2000) * env(.02, .0005, .004) * .4)


def clap():
    d = .3
    n = filt(noise(d), 'bandpass', [900, 4000])
    e = np.zeros(int(d * SR))
    for off in (0, .011, .022):
        i = int(off * SR)
        e[i:] += np.exp(-np.arange(len(e) - i) / SR / (.012 if off < .02 else .11))
    return n * e * .5


def hat(open_=False):
    d = .25 if open_ else .06
    return filt(noise(d), 'highpass', 7000) * env(d, .0005, .07 if open_ else .014) * .25


def crash(d=1.8):
    n = filt(noise(d), 'highpass', 4500)
    return filt(n, 'lowpass', 12000) * env(d, .001, .45) * .2


def boom(d=1.4, f0=90, f1=32):
    return sine_sweep(f0, f1, d, 4) * env(d, .002, .45)


def bell(freq, d=1.0, amp=.5):
    t = t_axis(d)
    s = (np.sin(2 * np.pi * freq * t) + .5 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t * 6)
         + .25 * np.sin(2 * np.pi * freq * 5.4 * t) * np.exp(-t * 12))
    return s * env(d, .002, .35) * amp


def pluck(freq, d=.35, bright=3000):
    s = saw(freq, d, (-6, 6))
    return filt(s, 'lowpass', bright) * env(d, .002, .09)


def pad(freqs, d):
    s = sum(saw(f, d, (-12, -4, 5, 13)) for f in freqs) / len(freqs)
    return filt(s, 'lowpass', 1800)


def click(f=2400, d=.02, amp=.3):
    t = t_axis(d)
    return np.sin(2 * np.pi * f * t) * np.exp(-t / (d / 5)) * amp


def whoosh(d, f0, f1, amp=.6):
    n = noise(d)
    s = sweep_bp(n, f0, f1, 1.6)
    t = t_axis(d)
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5
    return s * e * amp


# ---------------------------------------------------------------- mixing
class Bus:
    def __init__(self, dur):
        self.L = np.zeros(int(dur * SR) + SR * 3)
        self.R = np.zeros_like(self.L)

    def add(self, t, x, gain=1.0, pan=0.0):
        i = int(round(t * SR))
        if i < 0:
            x = x[-i:]
            i = 0
        j = min(len(self.L), i + len(x))
        x = x[: j - i] * gain
        self.L[i:j] += x * np.sqrt((1 - pan) / 2) * 1.414
        self.R[i:j] += x * np.sqrt((1 + pan) / 2) * 1.414


def reverb(x, secs=1.8):
    ir = rng.standard_normal(int(secs * SR)) * np.exp(-np.arange(int(secs * SR)) / SR / (secs / 5))
    ir = filt(ir, 'lowpass', 6000)
    ir /= np.sqrt(np.sum(ir ** 2))
    return fftconvolve(x, ir)[: len(x)]


def main(sfx_path, out_path):
    spec = json.load(open(sfx_path))
    DUR = spec['dur']
    events = spec['sfx']
    O0 = 27 * BEAT
    tap_t = next(e['t'] for e in events if e['type'] == 'tap')

    drums, music, fx, verb = Bus(DUR), Bus(DUR), Bus(DUR), Bus(DUR)
    duck = np.ones(len(drums.L))

    # ---------- music bed
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
    roots = [45, 41, 36, 43]
    drum_end = 30  # beats; final stab replaces drums after the tap
    for b in range(32):
        tb = b * BEAT
        ci = (b // 4) % 4
        if b % 4 == 0:
            d = 4 * BEAT + .3
            p = pad([NOTE(n) for n in chords[ci]] + [NOTE(chords[ci][0] + 12)], d)
            p *= np.minimum(1, t_axis(d) / .08) * np.minimum(1, (d - t_axis(d)) / .3)
            g = .16 if b < 4 else .22
            if b >= drum_end:
                g = 0
            music.add(tb, p, g, -.2)
            music.add(tb + .012, p, g, .2)
        if 4 <= b < drum_end and b != 26:
            drums.add(tb, kick(), .9)
            i = int(tb * SR)
            k = 1 - .6 * np.exp(-np.arange(int(.35 * SR)) / SR / .09)
            duck[i:i + len(k)] = np.minimum(duck[i:i + len(k)], k)
            if (b - 4) % 2 == 1:
                drums.add(tb, clap(), .7)
                verb.add(tb, clap(), .25)
            for s in range(4):
                if s == 2:
                    drums.add(tb + s * BEAT / 4, hat(open_=b % 4 == 3), .6, .3)
                elif s in (1, 3):
                    drums.add(tb + s * BEAT / 4, hat(), .35, -.3)
            # rolling bass on 8ths/16ths
            for s in (1, 2, 3):
                bp = pluck(NOTE(roots[ci] - 12 + (12 if s == 2 else 0)), .16, 900)
                music.add(tb + s * BEAT / 4, bp, .55)
        # 16th arpeggio during the feature section
        if 4 <= b < 22:
            arp = chords[ci] + [chords[ci][1] + 12]
            for s in range(4):
                n = arp[(b * 4 + s) % len(arp)] + 12
                pl = pluck(NOTE(n), .25, 3800)
                pan = -.45 if s % 2 else .45
                music.add(tb + s * BEAT / 4, pl, .09, pan)
                verb.add(tb + s * BEAT / 4, pl, .05)
        if b < 4:  # intro: gentle sparkle arpeggio
            for s in range(2):
                n = [69, 72, 76, 79, 81, 84, 88, 91][(b * 2 + s) % 8]
                verb.add(tb + s * BEAT / 2, bell(NOTE(n), 1.2, .16))
    # drum fill into outro
    for s in range(4):
        drums.add(26 * BEAT + s * BEAT / 4, clap(), .35 + s * .12)

    # ---------- sound design
    pent = [72, 74, 76, 79, 81, 84, 86]
    for e in events:
        t, ty = e['t'], e['type']
        if ty == 'riser':
            d = e['dur']
            r = whoosh(d, 200, 9000, .9) * np.linspace(0, 1, int(d * SR)) ** 2
            fx.add(t, r, .25)
            verb.add(t, r, .1)
        elif ty in ('impact', 'impactBig', 'drop'):
            big = ty != 'impact'
            fx.add(t, boom(1.6 if big else 1.0, 110, 30), .9 if big else .6)
            fx.add(t, crash(2.2 if big else 1.2), .8 if big else .45, .1)
            verb.add(t, crash(1.0), .3)
        elif ty == 'swish':
            fx.add(t - .12, whoosh(.22, 600, 7000, .5), .45, rng.uniform(-.6, .6))
        elif ty == 'whooshUp':
            fx.add(t, whoosh(.5, 300, 8000, .8), .5)
        elif ty == 'whooshBig':
            fx.add(t - .05, whoosh(.45, 8000, 250, .9), .6)
        elif ty == 'key':
            fx.add(t, filt(noise(.012), 'bandpass', [2500, 6000]) * env(.012, .0005, .003), .35, rng.uniform(-.2, .2))
        elif ty == 'send':
            fx.add(t, sine_sweep(450, 1300, .09, 30) * env(.09, .002, .03), .35, .3)
        elif ty == 'typing':
            for k in range(3):
                fx.add(t + k * .06, click(1600, .015, .25), .4, -.3)
        elif ty == 'pop':
            p = sine_sweep(900, 420, .12, 40) * env(.12, .001, .035)
            fx.add(t, p, .65, -.15)
            verb.add(t, p, .15)
        elif ty == 'flip':
            fx.add(t, click(1200, .03, .5), .5)
        elif ty == 'ding':
            n = pent[e.get('note', 0) % len(pent)]
            dg = mix(bell(NOTE(n), 1.4, .45), bell(NOTE(n + 7), 1.4, .2))
            fx.add(t, dg, .55, .1)
            verb.add(t, dg, .35)
        elif ty == 'tick':
            fx.add(t, click(2200, .02, .35), .5, rng.uniform(-.3, .3))
        elif ty == 'tickHi':
            fx.add(t, click(3600, .012, .25), .35, rng.uniform(-.4, .4))
        elif ty == 'coinToss':
            for k in range(10):
                fx.add(t + k * .065, click(3000 + k * 120, .02, .18), .4, (-1) ** k * .4)
        elif ty == 'coin':
            tt = t_axis(1.6)
            s = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * dcy)
                    for f, a, dcy in ((2093, .5, 2.5), (3322, .35, 3.2), (5160, .25, 4.5), (7040, .12, 6)))
            fx.add(t, s * env(1.6, .001), .45)
            verb.add(t, s, .25)
        elif ty == 'diceRoll':
            for k in range(7):
                kk = filt(noise(.03), 'bandpass', [700, 2500]) * env(.03, .001, .008)
                fx.add(t + k * .055 + rng.uniform(0, .02), kk, .5, rng.uniform(-.5, .5))
        elif ty == 'clack':
            c = mix(filt(noise(.06), 'bandpass', [500, 1800]) * env(.06, .0005, .015), click(950, .05, .4))
            fx.add(t, c, .8)
        elif ty == 'slam':
            fx.add(t, boom(.5, 140, 50), .5)
            fx.add(t, filt(noise(.12), 'bandpass', [1500, 6000]) * env(.12, .001, .03), .35, (e.get('i', 1) - 1) * .5)
        elif ty == 'type':
            for k in range(14):
                fx.add(t + k * .03, filt(noise(.012), 'bandpass', [2500, 6000]) * env(.012, .0005, .003), .35, rng.uniform(-.3, .3))
        elif ty == 'tap':
            fx.add(t, mix(click(1800, .03, .6), sine_sweep(1200, 500, .1, 30) * env(.1, .001, .03) * .5), .7)
        elif ty == 'final':
            d = DUR - t + 1.5
            stab = sum(saw(NOTE(n), d, (-10, 0, 10)) for n in (45, 57, 64, 67, 71, 76)) / 6
            stab = filt(stab, 'lowpass', 3500) * env(d, .005, .9)
            fx.add(t, stab, .45, -.1)
            fx.add(t + .01, stab, .45, .1)
            verb.add(t, stab, .4)
            fx.add(t, boom(1.8, 100, 30), .9)
            fx.add(t, crash(2.5), .7)
            for k, n in enumerate((81, 84, 88, 93)):
                verb.add(t + .08 * k, bell(NOTE(n), 1.5, .3))

    # ---------- sum
    n = int(DUR * SR)
    mL = music.L * duck + drums.L + fx.L
    mR = music.R * duck + drums.R + fx.R
    vL, vR = reverb(verb.L + music.L * .15), reverb(verb.R + music.R * .15)
    vR = np.roll(vR, int(.013 * SR))
    L, R = (mL + vL * .55)[:n], (mR + vR * .55)[:n]
    # master: glue + soft clip + fades
    st = np.stack([L, R], 1)
    st = np.tanh(st / np.max(np.abs(st)) * 1.6) / np.tanh(1.6)
    fade = np.ones(n)
    fade[-int(.25 * SR):] = np.linspace(1, 0, int(.25 * SR))
    fade[:int(.01 * SR)] = np.linspace(0, 1, int(.01 * SR))
    st *= fade[:, None] * .89
    wavfile.write(out_path, SR, (st * 32767).astype(np.int16))
    print('wrote', out_path, f'{n / SR:.3f}s')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
