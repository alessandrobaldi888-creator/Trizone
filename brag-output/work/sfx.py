"""Sound design for the Trizone logo stings. Everything rooted on A (55 Hz) so the
booms, the electric hum and the chrome shimmer sit in one key."""
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
DUR = 5.0
N = int(SR * DUR)
rng = np.random.default_rng(7)


def mulberry32(seed):
    a = seed & 0xFFFFFFFF
    def nxt():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = ((t ^ (t >> 15)) * (1 | t)) & 0xFFFFFFFF
        t = (t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF) ^ t) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return nxt


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'), x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'lowpass', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'highpass', fs=SR, output='sos'), x)


class Mix:
    def __init__(self):
        self.dry = np.zeros((N, 2))
        self.send = np.zeros((N, 2))

    def add(self, x, t0, gain=1.0, pan=0.0, verb=0.3):
        i = int(t0 * SR)
        if i >= N:
            return
        x = x[: N - i] * gain
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        st = np.stack([x * l, x * r], 1)
        self.dry[i:i + len(x)] += st
        self.send[i:i + len(x)] += st * verb

    def render(self, out):
        # simple stereo plate: decaying filtered noise, decorrelated per side
        tl = np.arange(int(SR * 2.2)) / SR
        ir = []
        for s in (1, 2):
            n = np.random.default_rng(s).standard_normal(len(tl)) * np.exp(-tl / 0.55)
            ir.append(lp(hp(n, 200), 6000) * 0.035)
        wet = np.stack([signal.fftconvolve(self.send[:, c], ir[c])[:N] for c in (0, 1)], 1)
        m = self.dry + wet
        m = hp(m.T, 28).T
        fade = np.ones(N)
        k = int(0.45 * SR)
        fade[-k:] = np.cos(np.linspace(0, np.pi / 2, k)) ** 2
        m *= fade[:, None]
        m = np.tanh(m * 1.15) / np.tanh(1.15)          # gentle glue / soft-clip
        m *= 10 ** (-1.0 / 20) / np.max(np.abs(m))      # -1 dBFS peak
        wavfile.write(out, SR, (m * 32767).astype(np.int16))


def env(n, a, d, curve=1.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
    return e ** curve


def noise(sec):
    return rng.standard_normal(int(sec * SR))


# ---------------- building blocks ----------------
def zap(sec=0.04, lo=1800, hi=5500):
    """one short electric snap"""
    n = int(sec * SR)
    x = bp(noise(sec), lo, hi) * env(n, 0.001, sec / 4)
    t = np.arange(n) / SR
    buzz = signal.sawtooth(2 * np.pi * 220 * t) * env(n, 0.001, sec / 3)
    return x * 0.8 + bp(buzz, 800, 4000) * 0.35


def crackle(sec, density, decay=None, seed=0):
    """field of electric arcs: random snaps + chopped 110 Hz buzz"""
    r = np.random.default_rng(seed)
    n = int(sec * SR)
    out = np.zeros(n)
    t = 0.0
    while t < sec:
        t += r.exponential(1 / density)
        z = zap(0.008 + r.random() * 0.035, 1200 + r.random() * 1500, 4000 + r.random() * 3000)
        i = int(t * SR)
        if i < n:
            out[i:i + len(z)] += z[: n - i] * (0.4 + 0.6 * r.random())
    tt = np.arange(n) / SR
    chop = (r.random(int(sec * 90) + 2) < 0.45).astype(float)
    chop = np.repeat(chop, SR // 90)[:n]
    chop = lp(np.pad(chop, (0, n - len(chop))), 300)
    buzz = bp(signal.sawtooth(2 * np.pi * 110 * tt) + 0.5 * signal.sawtooth(2 * np.pi * 220.7 * tt), 400, 3500) * chop * 0.25
    out += buzz
    if decay:
        out *= np.exp(-tt / decay)
    return out


def boom(sec=1.6, f0=110, f1=41.2, depth=1.0):
    """sub impact sweeping down onto low E (A-minor friendly)"""
    n = int(sec * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.09)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env(n, 0.002, 0.42 * depth)
    click = lp(noise(sec), 2500) * env(n, 0.0005, 0.012)
    return np.tanh(body * 1.6) * 0.9 + click * 0.5


def crack(sec=0.5):
    """the bright split of a lightning strike"""
    n = int(sec * SR)
    x = noise(sec)
    return hp(x, 900) * env(n, 0.0008, 0.05) + bp(x, 200, 1800) * env(n, 0.002, 0.12) * 0.6


def rumble(sec=3.5, decay=1.1):
    n = int(sec * SR)
    t = np.arange(n) / SR
    x = lp(noise(sec), 160, 4) * 3
    wob = 0.6 + 0.4 * lp(rng.standard_normal(n), 3)
    return x * wob * env(n, 0.06, decay)


def sweep(sec, f_lo, f_hi, rise=True, bands=10):
    """filtered-noise whoosh/riser built from crossfaded log bands"""
    n = int(sec * SR)
    x = noise(sec)
    fs = np.geomspace(f_lo, f_hi, bands)
    p = np.linspace(0, 1, n) if rise else np.linspace(1, 0, n)
    out = np.zeros(n)
    for k, fc in enumerate(fs):
        g = np.exp(-((p * (bands - 1) - k) ** 2) / 1.2)
        out += bp(x, fc / 1.25, min(fc * 1.25, SR / 2 - 100)) * g
    return out


def shimmer(sec=1.6, seed=0):
    """chrome glint: A-major-ish partials, slightly detuned, staggered"""
    r = np.random.default_rng(seed)
    n = int(sec * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for i, f in enumerate([1760, 2217.5, 2637, 3520, 4434.9, 5274]):
        d = int((0.03 * i + r.random() * 0.02) * SR)
        e = np.zeros(n)
        e[d:] = env(n - d, 0.01, 0.35 + r.random() * 0.25)
        out += np.sin(2 * np.pi * f * (1 + (r.random() - .5) * 0.003) * t) * e / (1 + i * 0.5)
    return out


def hum(sec, f=55):
    t = np.arange(int(sec * SR)) / SR
    x = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2 * f * t) + 0.18 * signal.sawtooth(2 * np.pi * 2 * f * t)
    return lp(x, 900)


def ramp_in(x, power=2.0):
    return x * np.linspace(0, 1, len(x)) ** power


# ---------------- V1 · STRIKE ----------------
def v1(out):
    m = Mix()
    S = 0.9
    # distant weather before the hit
    m.add(rumble(2.0, 0.6), 0.0, 0.10, 0, 0.5)
    m.add(crackle(0.12, 60, 0.05, 1), 0.30, 0.12, -0.6, 0.6)
    m.add(crackle(0.1, 60, 0.05, 2), 0.62, 0.16, 0.6, 0.6)
    m.add(ramp_in(sweep(0.88, 300, 6000), 2.5), 0.02, 0.22, 0, 0.4)
    # the strike
    m.add(crack(0.6), S, 0.85, 0, 0.45)
    m.add(boom(1.8, 110, 41.2, 1.1), S, 1.0, 0, 0.25)
    m.add(rumble(3.6, 1.3), S + 0.05, 0.55, 0, 0.6)
    m.add(crackle(1.4, 45, 0.45, 3), S + 0.02, 0.32, 0.15, 0.35)
    # letters igniting (same onsets as the picture)
    for i in range(17):
        if "ROMA TRIZONE CLUB"[i] == " ":
            continue
        on = 2.0 + mulberry32(500 + i)() * 0.55
        pan = (i - 8) / 10
        m.add(zap(0.03, 2000, 6000), on, 0.11, pan, 0.35)
        m.add(zap(0.02, 2500, 7000), on + 0.07, 0.06, pan, 0.35)
    m.add(hum(0.9, 55) * env(int(0.9 * SR), 0.15, 0.3), 2.0, 0.10, 0, 0.2)
    # chrome glint
    m.add(sweep(0.75, 2500, 11000) * env(int(0.75 * SR), 0.3, 0.2), 3.2, 0.06, 0, 0.5)
    m.add(shimmer(1.6, 1), 3.45, 0.05, 0.2, 0.7)
    m.add(crackle(0.12, 40, 0.06, 4), 4.35, 0.08, -0.3, 0.5)
    m.render(out)


# ---------------- V2 · CHARGE ----------------
def v2(out):
    m = Mix()
    B = 1.85
    m.add(zap(0.05), 0.15, 0.25, 0, 0.4)
    ch = crackle(1.7, 70, None, 5)
    m.add(ramp_in(ch, 1.2), 0.15, 0.32, 0, 0.3)
    m.add(ramp_in(hum(1.7, 55), 1.8), 0.15, 0.22, 0, 0.15)
    m.add(ramp_in(sweep(1.7, 200, 9000), 3), 0.15, 0.28, 0, 0.35)
    # boom + shockwave
    m.add(boom(1.8, 130, 41.2, 1.2), B, 1.0, 0, 0.25)
    m.add(crack(0.4), B, 0.55, 0, 0.4)
    m.add(sweep(0.8, 300, 5000, rise=False) * env(int(0.8 * SR), 0.01, 0.3), B + 0.02, 0.35, 0, 0.6)
    m.add(rumble(2.5, 0.9), B + 0.05, 0.35, 0, 0.6)
    m.add(crackle(1.0, 40, 0.35, 6), B + 0.03, 0.25, -0.1, 0.35)
    # electric line draws across, name rises behind it
    line = crackle(0.4, 90, None, 7) * env(int(0.4 * SR), 0.05, 0.25)
    for k, pan in enumerate(np.linspace(-0.7, 0.7, 5)):
        seg = line[int(k * 0.06 * SR):]
        m.add(seg[: int(0.12 * SR)] * np.hanning(min(len(seg), int(0.12 * SR))), 2.35 + k * 0.06, 0.22, pan, 0.35)
    m.add(sweep(0.45, 400, 4000) * env(int(0.45 * SR), 0.25, 0.1), 2.45, 0.16, 0, 0.4)
    m.add(boom(0.6, 90, 55, 0.35), 2.72, 0.35, 0, 0.3)
    # chrome glint
    m.add(sweep(0.75, 2500, 11000) * env(int(0.75 * SR), 0.3, 0.2), 3.3, 0.06, 0, 0.5)
    m.add(shimmer(1.5, 2), 3.55, 0.05, -0.2, 0.7)
    m.add(crackle(0.1, 40, 0.05, 8), 4.4, 0.07, 0.3, 0.5)
    m.render(out)


def pop(f=880, sec=0.25):
    n = int(sec * SR); t = np.arange(n) / SR
    fr = f * (1 + 1.2 * np.exp(-t / 0.012))
    x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * env(n, 0.001, 0.06)
    return x + hp(noise(sec), 3000) * env(n, 0.0005, 0.004) * 0.3


def tick(sec=0.03):
    n = int(sec * SR)
    return bp(noise(sec), 2500, 8000) * env(n, 0.0005, 0.005)


def whoosh(sec, lo=300, hi=5000, rise=True):
    n = int(sec * SR)
    e = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return sweep(sec, lo, hi, rise, 8) * e


# ---------------- V3 · MORPH ----------------
def v3(out):
    m = Mix()
    m.add(pop(880), 0.07, 0.45, 0, 0.3)
    m.add(whoosh(0.3, 300, 2500, False), 0.34, 0.10, 0, 0.2)
    m.add(boom(0.4, 110, 55, 0.25), 0.62, 0.45, 0, 0.2)
    m.add(tick(), 0.62, 0.25, 0, 0.2)
    m.add(whoosh(0.45, 300, 6000), 0.72, 0.18, 0, 0.3)
    m.add(pop(440, 0.3), 1.12, 0.25, 0, 0.3)
    m.add(whoosh(0.45, 500, 4000), 1.15, 0.16, 0, 0.3)
    m.add(boom(0.6, 130, 55, 0.4), 1.6, 0.75, 0, 0.25)
    m.add(pop(220, 0.3), 1.6, 0.30, 0, 0.3)
    m.add(tick(0.04), 1.6, 0.35, 0, 0.3)
    m.add(whoosh(0.5, 2500, 11000), 1.72, 0.07, 0, 0.5)
    m.add(shimmer(1.4, 3), 1.9, 0.06, 0.15, 0.7)
    m.add(whoosh(0.55, 200, 2500), 2.25, 0.10, 0, 0.3)
    for i in range(17):
        if "ROMA TRIZONE CLUB"[i] != " ":
            m.add(tick(0.02), 2.58 + i * 0.032, 0.07, (i - 8) / 10, 0.3)
    m.add(whoosh(0.6, 2500, 11000), 3.85, 0.05, 0, 0.5)
    m.add(shimmer(1.2, 4), 4.05, 0.018, -0.15, 0.7)
    m.render(out)


# ---------------- V4 · TRI ----------------
def v4(out):
    m = Mix()
    snaps = [(0.34, 440, -0.5), (0.64, 554.4, 0.5), (0.94, 659.3, -0.2)]   # A - C# - E
    for k, (ts, f, pan) in enumerate(snaps):
        m.add(whoosh(0.22, 400, 5000), ts - 0.22, 0.14, pan, 0.25)
        m.add(pop(f, 0.35), ts, 0.30, pan * 0.5, 0.35)
        m.add(tick(0.04), ts, 0.35, pan * 0.5, 0.2)
        m.add(boom(0.5, 120, 55, 0.3 + 0.2 * (k == 2)), ts, 0.45 + 0.4 * (k == 2), 0, 0.2)
    m.add(whoosh(0.5, 300, 6000), 1.25, 0.16, 0, 0.35)
    m.add(tick(0.04), 1.5, 0.2, 0, 0.3)
    m.add(shimmer(1.4, 5), 1.5, 0.06, 0.1, 0.7)
    m.add(whoosh(0.35, 400, 5000), 1.95, 0.12, -0.5, 0.25)
    m.add(tick(0.03), 2.3, 0.15, 0.5, 0.2)
    m.add(whoosh(0.4, 400, 5000, False), 2.35, 0.12, 0.3, 0.25)
    m.add(pop(880, 0.3), 2.75, 0.12, 0.5, 0.4)
    m.add(whoosh(0.6, 2500, 11000), 3.6, 0.05, 0, 0.5)
    m.add(shimmer(1.2, 6), 3.8, 0.018, -0.15, 0.7)
    m.render(out)


if __name__ == "__main__":
    {"v1": v1, "v2": v2, "v3": v3, "v4": v4}[sys.argv[1]](sys.argv[2])
