"""Mix voiceover + ambient score, drop in website captures, burn Space Grotesk captions.

usage: python3 compose.py <base.mp4> <vo_dir> <out.mp4>
Website captures: put video/captures/<slug>.mp4 (slugs in site_slots.json) and re-run;
each is scaled into the on-screen browser frame for its time slot.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
base, vo_dir, out = sys.argv[1:4]
tl = json.load(open(f'{HERE}/timeline.json'))
slots = json.load(open(f'{HERE}/site_slots.json'))
T = tl['total']
work = os.path.dirname(os.path.abspath(out))


def ts(t, sep='.'):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f'{h}:{m:02d}:{s:05.2f}' if sep == '.' else f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')


# ---- captions (.ass burned in, .srt for upload) ----
ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "WrapStyle: 0", "",
       "[V4+ Styles]",
       "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
       "Style: Cap,Space Grotesk Medium,50,&H00FFFFFF,&H00FFFFFF,&H64000000,&H64000000,0,0,0,0,100,100,0.5,0,3,14,0,2,200,200,70,1",
       "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
srt = []
caps = tl['captions']
for i, c in enumerate(caps):
    end = c['end']
    # hold a caption until the next one if the gap is short, so text doesn't flicker
    if i + 1 < len(caps) and caps[i + 1]['start'] - end < .6:
        end = caps[i + 1]['start']
    text = c['text'].replace('"', '“', 1).replace('"', '”', 1)
    ass.append(f"Dialogue: 0,{ts(c['start'])},{ts(end)},Cap,,0,0,0,,{{\\fad(120,120)}}{text}")
    srt += [str(i + 1), f"{ts(c['start'], ',')} --> {ts(end, ',')}", text, '']
open(f'{work}/captions.ass', 'w').write('\n'.join(ass) + '\n')
open(f'{HERE}/captions.srt', 'w').write('\n'.join(srt))

# ---- ambient score: low drone chord + filtered noise, synthesized ----
score = f'{work}/score.wav'
tones = [55, 82.41, 110, 130.81, 164.81]
expr = '+'.join(f'{.22 / (k + 1):.3f}*sin(2*PI*{f}*t)*(0.6+0.4*sin(2*PI*{.03 + .017 * k:.3f}*t+{k}))' for k, f in enumerate(tones))
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error',
                '-f', 'lavfi', '-i', f"aevalsrc='{expr}':s=48000:d={T}",
                '-f', 'lavfi', '-i', f'anoisesrc=color=brown:amplitude=0.05:d={T}:r=48000',
                '-filter_complex', f'[1]lowpass=f=400,volume=0.6[n];[0][n]amix=inputs=2:normalize=0,aecho=0.8:0.7:900|1400:0.3|0.2,'
                f'afade=t=in:d=3,afade=t=out:st={T - 5}:d=5,volume=0.5,aformat=channel_layouts=stereo',
                score], check=True)

# ---- voiceover track ----
inputs, parts = [], []
for i, l in enumerate(tl['lines']):
    inputs += ['-i', f'{vo_dir}/{i:02d}.wav']
    d = int(l['start'] * 1000)
    parts.append(f'[{i}]aresample=48000,aformat=channel_layouts=stereo,adelay={d}|{d}[v{i}]')
n = len(tl['lines'])
vo = f'{work}/voiceover.wav'
fc = ';'.join(parts) + ';' + ''.join(f'[v{i}]' for i in range(n)) + f'amix=inputs={n}:normalize=0,apad=whole_dur={T}[o]'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *inputs, '-filter_complex', fc, '-map', '[o]', '-t', str(T), vo], check=True)

# ---- final: captures overlay + captions + ducked mix ----
cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-i', base, '-i', vo, '-i', score]
vf, last, k = [], '[0:v]', 3
for s in slots:
    f = f'{HERE}/captures/{s["slug"]}.mp4'
    if not os.path.exists(f):
        continue
    r, dur = s['rect'], s['end'] - s['start']
    cmd += ['-stream_loop', '-1', '-t', f'{dur:.3f}', '-i', f]
    vf.append(f'[{k}:v]scale={r["w"]}:{r["h"]}:force_original_aspect_ratio=increase,crop={r["w"]}:{r["h"]},setpts=PTS-STARTPTS+{s["start"]:.3f}/TB[c{k}]')
    vf.append(f'{last}[c{k}]overlay={r["x"]}:{r["y"]}:eof_action=pass:enable=\'between(t,{s["start"]:.3f},{s["end"]:.3f})\'[o{k}]')
    last, k = f'[o{k}]', k + 1
    print('capture:', s['slug'])
vf.append(f"{last}ass={work}/captions.ass:fontsdir={HERE}/fonts[v]")
af = ('[2]volume=0.9[m];[1]asplit=2[vo][sc];[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=600[md];'
      '[vo][md]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]')
cmd += ['-filter_complex', ';'.join(vf) + ';' + af, '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-tune', 'grain', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', '-t', str(T), out]
subprocess.run(cmd, check=True)
print('wrote', out)
