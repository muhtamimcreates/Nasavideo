"""Word-level timings for each voiceover line (pocketsphinx forced alignment).
Writes words.json: per line, a list of {w, start, end} in seconds relative to the line's audio.
Falls back to a length-weighted split for any line the aligner can't handle."""
import json, re, sys, numpy as np, soundfile as sf
from pocketsphinx import Decoder

VO = sys.argv[1]
lines = json.load(open('/home/user/Nasavideo/video/short30/script.json'))
dec = Decoder(samprate=16000, bestpath=False, loglevel='FATAL')
SPECIAL = {'1977': 'nineteen seventy seven', '1966': 'nineteen sixty six', '2018': 'twenty eighteen',
           '1960s': 'nineteen sixties', '3d': 'three d', 'jpl': 'j p l', 'html,': 'h t m l', 'css,': 'c s s',
           'html': 'h t m l', 'css': 'c s s', 'pdfs.': 'p d fs', 'nasa': 'nasa', 'javascript.': 'java script', '3,': 'three', '3': 'three', 'md': 'mohammad'}

def spoken(tok):
    t = tok.lower().strip('"“”.,:;?!')
    if tok.lower() in SPECIAL: return SPECIAL[tok.lower()].split()
    if t in SPECIAL: return SPECIAL[t].split()
    t = t.replace("’", "'").replace('-', ' ')
    return [w for w in t.split() if w]

def resample(x, sr):
    n = int(len(x) * 16000 / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)

out = []
for i, l in enumerate(lines):
    audio, sr = sf.read(f'{VO}/{i:02d}.wav')
    dur = len(audio) / sr
    toks = l['text'].split()
    sp = [spoken(t) for t in toks]
    words = [w for s in sp for w in s]
    res = None
    if all(dec.lookup_word(w) for w in words):
        try:
            pcm = (np.clip(resample(audio, sr), -1, 1) * 32767).astype(np.int16).tobytes()
            dec.set_align_text(' '.join(words))
            dec.start_utt(); dec.process_raw(pcm, full_utt=True); dec.end_utt()
            segs = [(s.word, s.start_frame / 100, (s.end_frame + 1) / 100) for s in dec.seg() if s.word not in ('<s>', '</s>', '<sil>', '[NOISE]')]
            segs = [(re.sub(r'\(\d+\)$', '', w), a, b) for w, a, b in segs]
            if [w for w, _, _ in segs] == words:
                res, k = [], 0
                for t, s in zip(toks, sp):
                    res.append({'w': t, 'start': round(segs[k][1], 3), 'end': round(segs[k + len(s) - 1][2], 3)}); k += len(s)
        except Exception as e:
            print('align error', i, e)
    if res is None:
        oov = [w for w in words if not dec.lookup_word(w)]
        print(f'line {i}: fallback split', oov)
        w8 = [len(t) + 2 for t in toks]; tot = sum(w8); t0 = .08; span = dur - .2; res = []
        for t, w in zip(toks, w8):
            d = span * w / tot; res.append({'w': t, 'start': round(t0, 3), 'end': round(t0 + d, 3)}); t0 += d
    out.append(res)
json.dump(out, open('/home/user/Nasavideo/video/short30/words.json', 'w'), indent=0)
print('aligned', sum(1 for r in out), 'lines')
