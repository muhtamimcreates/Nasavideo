"""Mix voiceover + cinematic score, drop in website captures, burn word-highlight Space Grotesk captions.

usage: python3 compose.py <base.mp4> <vo_dir> <out.mp4> [captures_dir]
Website captures: put video/captures/<slug>.mp4 (slugs in site_slots.json) and re-run;
each is scaled into the on-screen browser frame for its time slot.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
base, vo_dir, out = sys.argv[1:4]
CAPS = sys.argv[4] if len(sys.argv) > 4 else f'{HERE}/captures'
tl = json.load(open(f'{HERE}/timeline.json'))
slots = json.load(open(f'{HERE}/site_slots.json'))
T = tl['total']
work = os.path.dirname(os.path.abspath(out))


def ts(t, sep='.'):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f'{h}:{m:02d}:{s:05.2f}' if sep == '.' else f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')


# ---- captions: word-by-word highlight (.ass burned in), plus .srt for upload ----
# colours from the website: unspoken = dust #a7b3cf, current = signal #6f9dff, spoken = white #eef3ff
DUST, SIGNAL, WHITE = '&HCFB3A7&', '&HFF9D6F&', '&HFFF3EE&'
words = json.load(open(f'{HERE}/words.json'))
ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "WrapStyle: 2", "",
       "[V4+ Styles]",
       "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
       "Style: Cap,Space Grotesk Medium,46,&H00FFF3EE,&H00FFF3EE,&H96020307,&H96020307,0,0,0,0,100,100,0,0,1,0,2,2,200,200,66,1",
       "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
chunks = []   # list of [ {w, s, e} ... ] in absolute time
for l, ws in zip(tl['lines'], words):
    cur = []
    for j, w in enumerate(ws):
        cur.append({'w': w['w'].replace('"', ''), 's': l['start'] + w['start'], 'e': l['start'] + w['end']})
        txt = ' '.join(x['w'] for x in cur)
        last = j == len(ws) - 1
        if last or len(txt) > 40 or (len(txt) >= 20 and w['w'][-1] in ',.:;?!'):
            if not last and len(' '.join(x['w'] for x in ws[j + 1:][:3])) < 8 and len(ws) - j - 1 <= 1:
                continue   # avoid a lonely last word
            chunks.append(cur); cur = []
srt = []
for ci, ch in enumerate(chunks):
    end = ch[-1]['e'] + .25
    if ci + 1 < len(chunks) and chunks[ci + 1][0]['s'] - end < .6:
        end = chunks[ci + 1][0]['s']
    for k, w in enumerate(ch):
        a0 = w['s'] if k else ch[0]['s']
        a1 = ch[k + 1]['s'] if k + 1 < len(ch) else end
        if a1 <= a0: continue
        parts = []
        for m, x in enumerate(ch):
            col = WHITE if m < k else SIGNAL if m == k else DUST
            parts.append(f"{{\\c{col}}}{x['w']}")
        ass.append(f"Dialogue: 0,{ts(a0)},{ts(a1)},Cap,,0,0,0,," + ' '.join(parts))
    srt += [str(ci + 1), f"{ts(ch[0]['s'], ',')} --> {ts(end, ',')}", ' '.join(x['w'] for x in ch), '']
open(f'{work}/captions.ass', 'w').write('\n'.join(ass) + '\n')
open(f'{HERE}/captions.srt', 'w').write('\n'.join(srt))

# ---- cinematic score (music.py) ----
score = f'{work}/score.wav'
subprocess.run([sys.executable, f'{HERE}/music.py', str(T), score], check=True)

# ---- voiceover track ----
inputs, parts = [], []
for i, l in enumerate(tl['lines']):
    inputs += ['-i', f'{vo_dir}/{i:02d}.wav']
    d = int(l['start'] * 1000)
    parts.append(f'[{i}]aresample=48000,aformat=channel_layouts=stereo,adelay={d}|{d}[v{i}]')
n = len(tl['lines'])
vo = f'{work}/voiceover.wav'
fc = ';'.join(parts) + ';' + ''.join(f'[v{i}]' for i in range(n)) + (f'amix=inputs={n}:normalize=0,highpass=f=75,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3200:t=q:w=1.2:g=2.5,'
      f'acompressor=threshold=0.12:ratio=3:attack=8:release=180:makeup=1.6,aecho=0.9:0.5:38|61:0.12|0.07,apad=whole_dur={T}[o]')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *inputs, '-filter_complex', fc, '-map', '[o]', '-t', str(T), vo], check=True)

# ---- final: captures overlay + captions + ducked mix ----
cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-i', base, '-i', vo, '-i', score]
vf, last, k = [], '[0:v]', 3
for s in slots:
    f = f'{CAPS}/{s["slug"]}.mp4'
    if not os.path.exists(f):
        continue
    r, dur, a, e = s['rect'], s['end'] - s['start'], s['start'], s['end']
    # fade with the scene cross-dissolve, except where two captures butt against each other
    fades = ''
    if not any(abs(o['end'] - a) < .05 for o in slots):
        fades += f',fade=t=in:st={a:.3f}:d=0.5:alpha=1'
    if not any(abs(o['start'] - e) < .05 for o in slots):
        fades += f',fade=t=out:st={e - .5:.3f}:d=0.5:alpha=1'
    cmd += ['-stream_loop', '-1', '-t', f'{dur:.3f}', '-i', f]
    vf.append(f'[{k}:v]scale={r["w"]}:{r["h"]}:force_original_aspect_ratio=increase,crop={r["w"]}:{r["h"]},format=yuva420p,setpts=PTS-STARTPTS+{a:.3f}/TB{fades}[c{k}]')
    vf.append(f'{last}[c{k}]overlay={r["x"]}:{r["y"]}:eof_action=pass:enable=\'between(t,{s["start"]:.3f},{s["end"]:.3f})\'[o{k}]')
    last, k = f'[o{k}]', k + 1
    print('capture:', s['slug'])
vf.append(f"{last}hqdn3d=4:3:8:6,ass={work}/captions.ass:fontsdir={HERE}/fonts[v]")
af = ('[2]volume=0.75[m];[1]asplit=2[vo][sc];[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=600[md];'
      '[vo][md]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]')
cmd += ['-filter_complex', ';'.join(vf) + ';' + af, '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', '-t', str(T), out]
subprocess.run(cmd, check=True)
print('wrote', out)
