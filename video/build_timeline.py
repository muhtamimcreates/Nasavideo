"""Place each voiceover line inside its section window and split captions into chunks."""
import json, re, soundfile as sf, sys
VO = sys.argv[1]
lines = json.load(open('/home/user/Nasavideo/video/script.json'))
windows = {'who': (2.5, 45), 'why': (46, 105), 'what': (106, 165), 'next': (166, 233)}
for i, l in enumerate(lines):
    l['dur'] = sf.info(f'{VO}/{i:02d}.wav').duration
out, prev_end = [], 0
for sec, (a, b) in windows.items():
    grp = [l for l in lines if l['sec'] == sec]
    start = max(a, prev_end + 0.8)
    speech = sum(l['dur'] for l in grp) + sum(l.get('pre', 0) for l in grp)
    gap = max(0.45, min(1.6, (b - start - speech) / max(1, len(grp) - 1)))
    t = start
    for j, l in enumerate(grp):
        t += l.get('pre', 0)
        l['start'], l['end'] = round(t, 3), round(t + l['dur'], 3)
        t = l['end'] + gap
        # scene changes get a little extra breathing room
        if j + 1 < len(grp) and grp[j + 1]['scene'] != l['scene']:
            t += 0.25
    prev_end = grp[-1]['end']
total = round(lines[-1]['end'] + 4.5, 2)
# caption chunks: <= ~42 chars, split on punctuation first
caps = []
for l in lines:
    words = l['text'].split()
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        s = ' '.join(cur)
        if len(s) > 34 and (re.search(r'[,.:;?!"]$', w) or len(s) > 44):
            chunks.append(s); cur = []
    if cur:
        if chunks and len(' '.join(cur)) < 12: chunks[-1] += ' ' + ' '.join(cur)
        else: chunks.append(' '.join(cur))
    n = sum(len(c) for c in chunks); t = l['start']
    for c in chunks:
        d = l['dur'] * len(c) / n
        caps.append({'start': round(t, 3), 'end': round(t + d, 3), 'text': c}); t += d
json.dump({'total': total, 'lines': lines, 'captions': caps}, open('/home/user/Nasavideo/video/timeline.json', 'w'), indent=1)
for l in lines: print(f"{l['start']:7.2f}-{l['end']:7.2f} {l['sec']:5} {l['scene']:12.12} {l['text'][:50]}")
print('total', total)
