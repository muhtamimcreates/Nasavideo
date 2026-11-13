"""Slow cinematic space score, synthesized: evolving pads, sub drone, sparse bells, long reverb.
usage: python3 music.py <seconds> <out.wav>"""
import sys, json, numpy as np, soundfile as sf

T = float(sys.argv[1]); OUT = sys.argv[2]
SR = 48000; N = int(T * SR); t = np.arange(N) / SR
rng = np.random.default_rng(7)
tl = json.load(open('/home/user/Nasavideo/video/short30/timeline.json'))
starts = {l['scene']: l['start'] for l in reversed(tl['lines'])}

def hz(n): return 440 * 2 ** ((n - 69) / 12)

def onepole(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); s = 0.0
    # vectorised via lfilter-free recursion in blocks
    from scipy.signal import lfilter
    return lfilter([1 - a], [1, -a], x)

def pad_voice(freq, dur, detune=.12):
    n = int(dur * SR); tt = np.arange(n) / SR; v = np.zeros(n)
    for d in (-detune, 0, detune):
        f = freq * 2 ** (d / 12)
        ph = 2 * np.pi * f * tt + rng.uniform(0, 6.28)
        for h in range(1, 9):  # soft saw
            v += np.sin(h * ph) / h * (0.8 ** h)
    return v / 6

# chord progression (MIDI), long and unresolved: Am(add9) · Fmaj7 · C(add9)/E · G6sus · Dm9 · Am
prog = [[45, 57, 60, 64, 71], [41, 57, 60, 64, 67], [40, 55, 60, 62, 67], [43, 55, 59, 62, 64], [38, 57, 60, 64, 65], [45, 57, 60, 64, 69]]
seg = 14.0
pad = np.zeros(N)
k = 0; s0 = 0.0
while s0 < T:
    ch = prog[k % len(prog)]; dur = seg + 6  # overlap for crossfade
    n0 = int(s0 * SR); n = min(int(dur * SR), N - n0)
    env = np.ones(n); a = int(5 * SR); r = int(6 * SR)
    env[:min(a, n)] = np.linspace(0, 1, min(a, n)) ** 2
    if n > r: env[-r:] *= np.linspace(1, 0, r) ** 2
    for m in ch:
        pad[n0:n0 + n] += pad_voice(hz(m), dur)[:n] * env * (.7 if m < 50 else .6)
    s0 += seg; k += 1
# slow filter sweep for movement
from scipy.signal import lfilter
cut = 800 + 1400 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 37))
pad_f = np.zeros(N); blk = SR // 50; z1 = np.zeros(1); z2 = np.zeros(1)
for i in range(0, N, blk):
    a = np.exp(-2 * np.pi * cut[i] / SR)
    y1, z1 = lfilter([1 - a], [1, -a], pad[i:i + blk], zi=z1)
    pad_f[i:i + blk], z2 = lfilter([1 - a], [1, -a], y1, zi=z2)
pad = pad_f

# sub drone on A1 with slow breathing
sub = np.sin(2 * np.pi * hz(33) * t) * (0.55 + 0.25 * np.sin(2 * np.pi * t / 23)) * .22
# airy noise wind, band-limited
noise = rng.standard_normal(N)
def lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); return lfilter([1 - a], [1, -a], x)
wind = (lp(noise, 1400) - lp(noise, 250)) * .05
wind *= 0.6 + 0.4 * np.sin(2 * np.pi * t / 29 + 1)

# sparse glassy bells, A minor pentatonic, high register
bells = np.zeros(N); pent = [69, 72, 74, 76, 79, 81, 84]
bt = 3.0
while bt < T - 6:
    m = pent[rng.integers(len(pent))]; n0 = int(bt * SR); n = int(6 * SR); tt = np.arange(n) / SR
    f = hz(m)
    b = (np.sin(2 * np.pi * f * tt) + .35 * np.sin(2 * np.pi * f * 2.01 * tt) + .12 * np.sin(2 * np.pi * f * 3.98 * tt)) * np.exp(-tt / 1.8)
    b *= np.minimum(1, tt / .01)
    bells[n0:n0 + n] += b[:N - n0] * .09
    bt += rng.uniform(5.5, 10)

mix = pad * .5 + sub + wind + bells

# dynamics: swell into the title, the storm and the ending; dip under the website section
def bump(c, w, g):
    return g * np.exp(-((t - c) / w) ** 2)
dyn = 0.75 + bump(starts.get('title', 42), 4, .35) + bump(starts.get('storm', 85), 8, .3) + bump(T - 12, 7, .45)
dyn -= 0.15 * ((t > starts.get('site:Home', 107)) & (t < starts.get('sources', 162)))
mix *= dyn

# long hall reverb via FFT convolution with a decaying stereo noise tail
L = int(5.5 * SR); it = np.arange(L) / SR
irL = rng.standard_normal(L) * np.exp(-it / 1.6); irR = rng.standard_normal(L) * np.exp(-it / 1.6)
irL = lfilter([1], [1, -.6], irL); irR = lfilter([1], [1, -.6], irR)
def conv(x, ir):
    n = 1 << int(np.ceil(np.log2(len(x) + len(ir))))
    return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]
wetL, wetR = conv(mix, irL), conv(mix, irR)
wetL /= np.max(np.abs(wetL)) + 1e-9; wetR /= np.max(np.abs(wetR)) + 1e-9
dry = mix / (np.max(np.abs(mix)) + 1e-9)
L_ = .45 * dry + .75 * wetL; R_ = .45 * dry + .75 * wetR
hp = lambda x: (lambda y: y - lp(y, 60))(x - lp(x, 60))
L_, R_ = hp(L_), hp(R_)
out = np.stack([L_, R_], 1)
fade = np.ones(N); fi = int(4 * SR); fo = int(8 * SR)
fade[:fi] = np.linspace(0, 1, fi) ** 2; fade[-fo:] = np.linspace(1, 0, fo) ** 2
out *= fade[:, None]
out /= np.max(np.abs(out)) / .8
sf.write(OUT, out.astype(np.float32), SR)
print('wrote', OUT)
