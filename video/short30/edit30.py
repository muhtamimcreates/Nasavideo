"""Documentary edit: NASA stock footage + stills + website recordings, cut to the voiceover timeline.

usage: STOCK=<dir with stock clips/stills> CAPS=<dir with site recordings> python3 edit.py <work_dir> <out.mp4>
Every shot starts on a voiceover line (timeline.json); text overlays are Space Grotesk at -1px tracking (overlays.js).
"""
import json, os, subprocess, sys, html as H
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
STOCK = os.environ.get('STOCK', f'{HERE}/stock')
CAPS = os.environ.get('CAPS', f'{HERE}/captures')
WORK, OUT = sys.argv[1], sys.argv[2]
os.makedirs(f'{WORK}/seg', exist_ok=True)
tl = json.load(open(f'{HERE}/timeline.json'))
L, T = tl['lines'], tl['total']
WORDS = json.load(open(f'{HERE}/words.json'))
SLOTS = {s['slug']: s for s in json.load(open(f'{HERE}/site_slots.json'))}
FPS = 30


def S(i): return L[i]['start']
def C(i): return round(L[i]['start'] - 0.25, 3)       # cut a beat before the line
def W(i, word):                                        # absolute time a word is spoken
    for w in WORDS[i]:
        if w['w'].lower().strip('".,:;?!').startswith(word.lower()): return L[i]['start'] + w['start']
    raise KeyError(word)


# ---------- bases ----------
def V(name, ss, z0=1.0, z1=1.06, px=.5, py=.5, pre=None): return dict(k='v', f=f'{STOCK}/{name}.mp4', ss=ss, z0=z0, z1=z1, px0=px, px1=px, py0=py, py1=py, pre=pre)
MCC = (960, 720, 160, 0)   # the Apollo control-room reel has pillarbox bars burned in
def I(name, z0=1.0, z1=1.08, px0=.5, px1=.5, py0=.5, py1=.5): return dict(k='i', f=f'{STOCK}/{name}.jpg', z0=z0, z1=z1, px0=px0, px1=px1, py0=py0, py1=py1)
VOID = dict(k='void')
def SPLIT(a, b): return dict(k='split', a=a, b=b)
def SITE(slug): return dict(k='site', slug=slug)


OV = {}   # id -> html
def O(id, html, t=0.35, out=None, dy=18, blink=False, at=None):
    OV[id] = html
    return dict(id=id, t=t, out=out, dy=dy, blink=blink, at=at)


def tag(*parts, dot='orange'):
    d = f'<span class="dot {"blue" if dot == "blue" else ""}"></span>' if dot else ''
    return f'<div class="tag">{d}' + ' <span style="color:var(--dim)">/</span> '.join(parts) + '</div>'


def sig(text, dot='orange', pos='left:96px;top:80px'):
    return f'<div class="abs" style="{pos}"><span class="sig"><span class="dot {"blue" if dot == "blue" else ""}"></span>{text}</span></div>'


def center(inner, extra=''):
    return f'<div class="center shadow" style="{extra}">{inner}</div>'


def tabs(items, cols=None):
    out = ''
    for j, (bar, k, t, x, y, r) in enumerate(items):
        lines = ''.join(f'<div class="line" style="width:{w}%"></div>' for w in (92, 78, 85, 60))
        out += (f'<div class="tab" style="left:{x}px;top:{y}px;transform:rotate({r}deg)"><div class="bar"><i></i><i></i><i></i><span>{bar}</span></div>'
                f'<div class="body"><div class="k">{k}</div><div class="t">{t}</div>{lines}</div></div>')
    return out


TAB_ITEMS = [
    ('science.nasa.gov/mission/mer-opportunity', 'Mission page', 'Mars Exploration Rover: Opportunity', 150, 150, -2),
    ('jpl.nasa.gov/news', 'Press release', 'NASA’s Opportunity Rover Mission on Mars Comes to End', 980, 120, 2.5),
    ('Opportunity_EndOfMission.pdf', 'PDF', 'Mission Status Report — Sol 5352', 260, 470, 1.5),
    ('nssdc.gsfc.nasa.gov/nmc', 'Catalog', 'Surveyor 3 — Spacecraft details', 1050, 450, -3),
    ('voyager.jpl.nasa.gov/mission/status', 'Mission page', 'Voyager — Mission Status', 620, 300, -1),
    ('MER_Fact_Sheet_2004.pdf', 'PDF', 'Mars Exploration Rovers — Fact Sheet', 560, 560, 3),
]

# ---------- the shot list (30 s, "30 Seconds of Glory": intro 0, lead 2, name 5, idea 10, future 20) ----------
def card(k, h, sub=''):
    return f'<div class="left shadow"><div class="kicker">{k}</div><div class="h2">{h}</div>' + (f'<div class="sub">{sub}</div>' if sub else '') + '</div>'
def chips(items, top=760):
    return f'<div class="abs" style="left:120px;top:{top}px;display:flex;gap:14px">' + ''.join(f'<span class="sig" style="font-size:26px">{r}</span>' for r in items) + '</div>'
SHOTS = [
    # 0:00 introduce yourself
    dict(t0=0, base=V('earthnight', 46.6, 1.12, 1.2, .5, .75), ov=[
        O('s_intro', card('Team Cosmic Eclipse', 'Mahi', 'Sylhet, Bangladesh'), t=.15)]),
    # 0:02 lead us in
    dict(t0=C(1), base=I('voy_art2', 1.0, 1.1, .55, .45), ov=[O('s_voy', sig('Voyager 1 · still talking', 'blue'), t=.1)]),
    dict(t0=W(1, 'where') - .2, base=I('mer1', 1.04, 1.12, .5, .5, .4, .5), ov=[O('s_oppy', sig('Opportunity · signal: none'), t=.05, dy=0, blink=True)]),
    # 0:05 name your solution
    dict(t0=C(2), base=V('earth4k', 2000, 1.1, 1.16, .9, .3), ov=[
        O('s_title', center('<div class="h1 grad">Abandoned,<br>but not forgotten</div>'), at=W(2, 'abandoned') - .3, dy=30),
        O('s_tagline', center('<div class="kicker" style="font-size:30px">15 missions · why each one ended</div>', 'justify-content:flex-end;padding-bottom:250px'), at=W(2, 'fifteen') - .2)]),
    # 0:10 describe your idea (live site, quick cuts)
    dict(t0=W(3, 'scroll') - .3, base=SITE('home-scroll')),
    dict(t0=W(3, 'search') - .2, base=SITE('timeline-map')),
    dict(t0=W(3, 'turn') - .2, base=SITE('inspect-3d')),
    dict(t0=W(3, 'play') - .2, base=SITE('mission-detective')),
    dict(t0=C(4), base=I('mer2', 1.0, 1.1, .4, .6), ov=[
        O('s_src', card('Every fact', 'NASA &amp; JPL<br>sources'), t=.2),
        O('s_off', chips(['HTML · CSS · JS', 'No backend', 'Works offline']), at=W(4, 'works') - .2)]),
    # 0:20 look into the future
    dict(t0=C(5), base=V('mcc', 87.0, 1.0, 1.06, pre=MCC), ov=[O('s_a1', '<div class="left shadow"><div class="stat" style="color:var(--orange-b)">01</div><div class="h2">Expert review</div></div>', t=.1)]),
    dict(t0=W(5, 'more') - .2, base=V('moonfly', 15.0, 1.0, 1.05), ov=[O('s_a2', '<div class="left shadow"><div class="stat" style="color:var(--orange-b)">02</div><div class="h2">More NASA data</div></div>', t=.05)]),
    dict(t0=W(5, 'bangla') - .2, base=V('earthnight', 46.0, 1.12, 1.18, .5, .75), ov=[O('s_a3', '<div class="left shadow"><div class="stat" style="color:var(--orange-b)">03</div><div class="h2">A Bangla version</div><div class="sub">for schools</div></div>', t=.05)]),
    dict(t0=C(6), base=SPLIT(I('voy_art', 1.05, 1.12), I('mer3', 1.05, 1.12, .5, .5, .45, .5)), ov=[
        O('s_l', '<div class="abs" style="left:96px;top:80px"><span class="sig"><span class="dot blue"></span>Voyager · still talking</span></div>', t=.1),
        O('s_r', '<div class="abs" style="left:1056px;top:80px"><span class="sig"><span class="dot"></span>Opportunity · went quiet</span></div>', at=W(6, 'opportunity') - .1)]),
    dict(t0=W(6, 'we') - .2, base=VOID, ov=[
        O('s_end', center('<div class="h1 grad" style="font-size:112px">Abandoned,<br>but not forgotten</div>'), t=.1, dy=24),
        O('s_url', center('<div class="sub" style="color:var(--white)">abandonedbutnotforgottenchallenge.netlify.app</div>'
                          '<div class="kicker" style="font-size:22px">Team Cosmic Eclipse · Sylhet, Bangladesh</div>', 'justify-content:flex-end;padding-bottom:150px'), t=.4)]),
]
SHOTS.sort(key=lambda s: s['t0'])
for a, b in zip(SHOTS, SHOTS[1:] + [dict(t0=T)]):
    a['t1'] = b['t0']
# site labels (chip above the browser frame)
for s in SHOTS:
    if s['base']['k'] == 'site':
        sl = SLOTS[s['base']['slug']]
        OV[f'frame_{sl["slug"]}'] = (
            '<svg class="abs" style="left:0;top:0" width="1920" height="1080"><defs><radialGradient id="g" cx="50%" cy="45%" r="70%">'
            '<stop offset="0" stop-color="#0f1a33"/><stop offset=".75" stop-color="#05070d"/></radialGradient><mask id="m"><rect width="1920" height="1080" fill="white"/>'
            '<rect x="240" y="92" width="1440" height="810" rx="14" fill="black"/></mask></defs><rect width="1920" height="1080" fill="url(#g)" mask="url(#m)"/>'
            '<rect x="240.5" y="92.5" width="1439" height="809" rx="14" fill="none" stroke="rgba(150,170,210,.32)"/></svg>'
            f'<div class="abs" style="left:240px;top:30px;display:flex;gap:14px;align-items:center"><span class="sig" style="font-size:22px;padding:8px 16px"><span class="dot"></span>Live site</span>'
            f'<span style="font:600 26px SG;letter-spacing:-1px;text-transform:uppercase">{H.escape(sl["label"])}</span></div>')
        s['ov'] = [o for o in s.get('ov', []) if OV.get(o['id'])]

# ---------- render overlays ----------
json.dump({k: v for k, v in OV.items() if v}, open(f'{WORK}/overlays.json', 'w'))
subprocess.run(['node', f'{HERE}/overlays.js', f'{WORK}/overlays.json', f'{WORK}/ov'], check=True,
               env={**os.environ, 'NODE_PATH': subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip()})
# caption scrim (soft dark gradient at the bottom) for stock shots
sc = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0))
for y in range(640, 1080):
    a = int(170 * ((y - 640) / 440) ** 1.6)
    sc.paste((2, 3, 7, a), (0, y, 1920, y + 1))
sc.save(f'{WORK}/scrim.png')

GRADE = 'eq=contrast=1.05:saturation=0.84:gamma=0.98,colorbalance=bs=0.035:bm=0.02:rh=0.015,vignette=angle=0.5'


def cover(w, h, W_=1920, H_=1080):
    k = max(W_ / w, H_ / h); return w * k, h * k


def base_chain(b, dur, inp, W_=1920, H_=1080, lbl='b'):
    """returns (input args, filter string producing [lbl])"""
    if b['k'] == 'void':
        return ['-f', 'lavfi', '-t', f'{dur:.3f}', '-i', f'color=c=0x05070d:s={W_}x{H_}:r={FPS}'], f'[{inp}]format=yuv420p[{lbl}]'
    if b['k'] == 'v':
        args = ['-ss', f'{b["ss"]:.3f}', '-t', f'{dur + .1:.3f}', '-i', b['f']]
        p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', b['f']], capture_output=True, text=True).stdout.strip().split(',')
        w, h = map(int, p[:2])
        if b.get('pre'): w, h = b['pre'][:2]
    else:
        args = ['-loop', '1', '-framerate', str(FPS), '-t', f'{dur + .1:.3f}', '-i', b['f']]
        w, h = Image.open(b['f']).size
    cw, ch = cover(w, h, W_, H_)
    z = f"({b['z0']}+({b['z1']}-{b['z0']})*t/{dur:.3f})"
    px = f"({b['px0']}+({b['px1']}-{b['px0']})*t/{dur:.3f})"
    py = f"({b['py0']}+({b['py1']}-{b['py0']})*t/{dur:.3f})"
    pre = f"crop={b['pre'][0]}:{b['pre'][1]}:{b['pre'][2]}:{b['pre'][3]}," if b.get('pre') else ''
    f = (f"[{inp}]{pre}fps={FPS},setpts=PTS-STARTPTS,scale=w='2*ceil({cw:.1f}*{z}/2)':h='2*ceil({ch:.1f}*{z}/2)':eval=frame:flags=bicubic,"
         f"crop={W_}:{H_}:x='(iw-{W_})*{px}':y='(ih-{H_})*{py}',setsar=1,format=yuv420p[{lbl}]")
    return args, f


def render(i, s):
    dur = round(s['t1'] - s['t0'], 3)
    out = f'{WORK}/seg/{i:03d}.mp4'
    b = s['base']; args, fl, k = [], [], 0
    if b['k'] == 'split':
        a1, f1 = base_chain(b['a'], dur, 0, 960, 1080, 'ba'); a2, f2 = base_chain(b['b'], dur, 1, 960, 1080, 'bb')
        args += a1 + a2; fl += [f1, f2, '[ba][bb]hstack,drawbox=x=958:y=0:w=4:h=1080:color=0x05070d:t=fill,' + GRADE + '[b0]']; k = 2
    elif b['k'] == 'site':
        sl = SLOTS[b['slug']]; cap = f'{CAPS}/{b["slug"]}.mp4'
        args += ['-f', 'lavfi', '-t', f'{dur:.3f}', '-i', f'color=c=0x05070d:s=1920x1080:r={FPS}', '-t', f'{dur + .1:.3f}', '-i', cap]
        fl += [f'[1]fps={FPS},setpts=PTS-STARTPTS,scale=1440:810:flags=lanczos,tpad=stop_mode=clone:stop_duration=5[rec]', '[0][rec]overlay=240:92:shortest=0[b0]']; k = 2
    else:
        a1, f1 = base_chain(b, dur, 0)
        args += a1; fl += [f1.replace('[b]', ''), ] if False else [f1[:-3] + (',' + GRADE if b['k'] != 'void' else '') + '[b0]']; k = 1
    cur = 'b0'
    if b['k'] in ('v', 'i', 'split'):
        args += ['-loop', '1', '-framerate', str(FPS), '-t', f'{dur:.3f}', '-i', f'{WORK}/scrim.png']
        fl.append(f'[{cur}][{k}]overlay=0:0[s{k}]'); cur = f's{k}'; k += 1
    if b['k'] == 'site':
        args += ['-loop', '1', '-framerate', str(FPS), '-t', f'{dur:.3f}', '-i', f'{WORK}/ov/frame_{b["slug"]}.png']
        fl.append(f'[{cur}][{k}]overlay=0:0[s{k}]'); cur = f's{k}'; k += 1
    for o in s.get('ov', []):
        st = max(0, (o['at'] - s['t0']) if o['at'] is not None else o['t'])
        args += ['-loop', '1', '-framerate', str(FPS), '-t', f'{dur:.3f}', '-i', f'{WORK}/ov/{o["id"]}.png']
        fd = f'fade=t=in:st={st:.3f}:d=0.55:alpha=1'
        if o['out']: fd += f',fade=t=out:st={o["out"] - .4:.3f}:d=0.4:alpha=1'
        y = f"'{o['dy']}*pow(max(0,1-(t-{st:.3f})/0.9),3)*gte(t,{st:.3f})+{o['dy']}*lt(t,{st:.3f})'" if o['dy'] else '0'
        en = f":enable='lt(mod(t-{st:.3f},1.1),0.78)+lt(t,{st:.3f})'" if o['blink'] else ''
        fl.append(f'[{k}]format=rgba,{fd}[o{k}]')
        fl.append(f'[{cur}][o{k}]overlay=x=0:y={y}:eval=frame{en}[s{k}]'); cur = f's{k}'; k += 1
    fl.append(f'[{cur}]format=yuv420p,trim=duration={dur:.3f},setpts=PTS-STARTPTS[v]')
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', *args, '-filter_complex', ';'.join(fl), '-map', '[v]', '-r', str(FPS),
           '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', '-an', out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: print('FAIL', i, r.stderr[-1500:]); raise SystemExit(1)
    return out


with ThreadPoolExecutor(4) as ex:
    segs = list(ex.map(lambda a: render(*a), enumerate(SHOTS)))
open(f'{WORK}/segs.txt', 'w').write(''.join(f"file '{p}'\n" for p in segs))
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{WORK}/segs.txt', '-c', 'copy', OUT], check=True)
json.dump([dict(t0=s['t0'], t1=s['t1'], base=s['base'].get('f', s['base'].get('slug', s['base']['k']))) for s in SHOTS], open(f'{WORK}/shots.json', 'w'), indent=1)
print('shots', len(SHOTS), 'wrote', OUT)
