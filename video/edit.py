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

# ---------- the shot list ----------
SHOTS = [
    # WHO  ------------------------------------------------------------
    dict(t0=0, base=VOID, ov=[O('signal_none', center('<span class="sig" style="font-size:34px;padding:16px 28px"><span class="dot"></span>SIGNAL: NONE</span>'), t=.6, dy=0, blink=True)]),
    dict(t0=2.3, base=I('voy_art2', 1.0, 1.12, .55, .45, .45, .5), ov=[
        O('voy_tag', tag('<b>Voyager 1</b>', 'Launched 1977', dot='blue'), t=.4),
        O('voy_dist', '<div class="abs shadow" style="right:110px;top:300px;text-align:right"><div class="kicker" style="color:var(--blue-b)">Distance from Earth</div>'
          '<div class="stat grad">24,000,000,000+</div><div class="h3" style="color:var(--muted)">kilometres</div></div>', at=W(0, 'twenty') - .3)]),
    dict(t0=8.2, base=V('voyteam', 1.0, 1.0, 1.08), ov=[
        O('voy_live', sig('Signal: received', 'blue'), t=.3),
        O('voy_jpl', '<div class="abs sub shadow" style="left:96px;top:150px">JPL, 2024 — Voyager 1 sends engineering data again</div>', t=.6)]),
    dict(t0=C(1), base=I('mer1', 1.04, 1.14, .5, .5, .4, .55), ov=[
        O('oppy_tag', tag('<b>Opportunity</b>', 'Mars', 'Last contact 10 June 2018'), t=.3),
        O('oppy_none', sig('Signal: none', 'orange', 'right:96px;top:72px'), t=1.4, dy=0, blink=True)]),
    dict(t0=C(2), base=SPLIT(I('voy_art', 1.0, 1.08), I('mer3', 1.02, 1.1, .5, .5, .45, .5)), ov=[
        O('split_lbl', '<div class="abs" style="left:96px;top:80px"><span class="sig"><span class="dot blue"></span>Voyager · still talking</span></div>'
          '<div class="abs" style="left:1056px;top:80px"><span class="sig"><span class="dot"></span>Opportunity · silent</span></div>', t=.2),
        O('split_txt', '<div class="abs h3 shadow" style="left:0;right:0;top:760px;text-align:center">Same agency. Same promise.</div>', at=W(2, 'same') - .1),
        O('split_txt2', '<div class="abs h3 shadow" style="left:0;right:0;top:830px;text-align:center;color:var(--orange-b)">Two very different endings.</div>', at=W(2, 'two') - .1)]),
    dict(t0=C(3), base=V('earthnight', 46.4, 1.12, 1.2, .5, .75), ov=[
        O('team', '<div class="left shadow"><div class="kicker">Team [Team Name]</div><div class="h2">[City],<br>Bangladesh</div>'
          '<div class="sub">I’m [Name]</div></div>', t=.3)]),
    dict(t0=C(4), base=V('earth4k', 1500, 1.0, 1.06), ov=[
        O('roles', '<div class="left shadow"><div class="kicker">We are</div><div style="display:flex;gap:14px">' + ''.join(
            f'<span class="sig" style="font-size:28px">{r}</span>' for r in ('a developer', 'a researcher', 'a designer', 'a storyteller')) + '</div></div>', t=.3)]),
    dict(t0=C(5), base=V('moonfly', 13.0, 1.0, 1.05), ov=[
        O('question', center('<div class="kicker">One question</div><div class="h2 grad" style="max-width:1500px">When a mission goes quiet,<br>where does its story go?</div>'), at=W(5, 'when') - .2)]),
    dict(t0=C(6), base=V('earth4k', 2000, 1.1, 1.16, .9, .3), ov=[
        O('title_sig', center('<span class="sig"><span class="dot"></span>Signal: none</span>', 'justify-content:flex-start;padding-top:250px'), t=.2, dy=0),
        O('title', center('<div class="h1 grad">Abandoned,<br>but not forgotten</div>'), at=W(6, 'abandoned') - .3, dy=30)]),
    # WHY  ------------------------------------------------------------
    dict(t0=C(7), base=V('saturnv', 116.5, 1.02, 1.1), ov=[O('since', tag('<b>1966 → today</b>', 'Moon', 'Mars', 'Deep space'), t=.4)]),
    dict(t0=W(7, 'moon') - .2, base=V('apollo11', 16 * 60 + 33, 1.0, 1.06)),
    dict(t0=W(7, 'mars') - .1, base=I('cabo', 1.0, 1.05, .2, .8)),
    dict(t0=W(7, 'deep') - .2, base=I('voy_model', 1.0, 1.1)),
    dict(t0=C(8), base=VOID, ov=[O(f'tab{j}', tabs([it]), at=W(8, 'scattered') - .5 + j * .55, dy=40) for j, it in enumerate(TAB_ITEMS)]
         + [O('facts', '<div class="abs h3" style="left:96px;top:72px;color:var(--muted)">The facts exist.</div>', t=.2)]),
    dict(t0=C(9), base=VOID, ov=[
        O('word', center('<div class="kicker" style="color:var(--muted)">One word hides the truth</div><div class="h1" style="font-size:190px">“Abandoned”</div>'), t=.3),
        O('strike', '<div class="abs" style="left:330px;right:330px;top:585px;height:12px;background:var(--orange-b);box-shadow:0 0 24px var(--orange-b)"></div>', at=L[9]['end'] + .2, dy=0)]),
    dict(t0=C(10), base=V('mcc', 12.5, 1.0, 1.06, pre=MCC), ov=[
        O('home', '<div class="abs h3 shadow" style="left:96px;top:760px">Nobody drove them home.</div>', t=.4),
        O('until', '<div class="abs h3 shadow" style="left:96px;top:830px;color:var(--orange-b)">They worked until something stopped them.</div>', at=W(10, 'they') - .1)]),
    dict(t0=C(11), base=I('storm2018', 1.05, 1.2), ov=[O('w_dust', '<div class="left"><div class="h1 shadow">Dust.</div></div>', t=.1, dy=24)]),
    dict(t0=C(12), base=I('oppy_frost', 1.0, 1.15), ov=[O('w_cold', '<div class="left"><div class="h1 shadow">Cold.</div></div>', t=.1, dy=24)]),
    dict(t0=C(13), base=I('darkness', 1.0, 1.12, .2, .9), ov=[O('w_power', '<div class="left"><div class="h1 shadow">Fading<br>power.</div></div>', t=.1, dy=24)]),
    dict(t0=C(14), base=I('paleblue', 1.25, 1.0, .5, .5, .3, .5), ov=[O('w_dist', '<div class="left"><div class="h1 shadow">Distance.</div></div>', t=.1, dy=24)]),
    dict(t0=C(15), base=I('mer2', 1.0, 1.12, .4, .6), ov=[
        O('o_tag', tag('<b>Opportunity</b>', 'Meridiani Planum', '2004 – 2018'), t=.3),
        O('o_90', '<div class="abs shadow" style="right:120px;top:300px;text-align:right"><div class="kicker">Built to last</div><div class="stat">90</div><div class="h3">Martian days</div></div>', at=W(15, 'ninety') - .3, out=W(15, 'fourteen') - C(15) - .2),
        O('o_14', '<div class="abs shadow" style="right:120px;top:300px;text-align:right"><div class="kicker" style="color:var(--blue-b)">It worked for</div><div class="stat grad">14+</div><div class="h3">years</div></div>', at=W(15, 'fourteen') - .3)]),
    dict(t0=C(16), base=I('mars_before_after', 1.0, 1.1), ov=[
        O('storm_tag', tag('<b>2018</b>', 'Planet-encircling dust storm', 'Mars before / after'), t=.3)]),
    dict(t0=W(16, 'blocked') - .2, base=I('darkness', 1.15, 1.3, .1, 1.0), ov=[O('sun', tag('Sunlight at Opportunity’s site, June 2018'), t=.2)]),
    dict(t0=C(17), base=I('goldstone', 1.0, 1.1, .4, .55), ov=[
        O('dsn_tag', tag('<b>Deep Space Network</b>', 'Goldstone, California', dot='blue'), t=.3),
        O('cmds', '<div class="abs shadow" style="right:120px;top:320px;text-align:right"><div class="kicker" style="color:var(--blue-b)">Recovery commands sent</div><div class="stat">1,000+</div></div>', at=W(17, 'thousand') - .3)]),
    dict(t0=W(17, 'nothing') - .3, base=I('lastmsg', 1.0, 1.08), ov=[O('noresp', center('<span class="sig" style="font-size:34px;padding:16px 28px"><span class="dot"></span>No response</span>'), t=.2, dy=0, blink=True)]),
    dict(t0=C(18), base=I('traverse', 1.0, 1.12, .3, .5, .2, .7), ov=[
        O('why', '<div class="left shadow"><div class="kicker">The part that matters most</div><div class="h2">Why a mission<br>ended.</div></div>', t=.6),
        O('hard', '<div class="abs sub shadow" style="left:120px;top:780px">…and the hardest part to find.</div>', at=W(18, 'and') - .1)]),
    dict(t0=C(19), base=VOID, ov=[O(f'tb{j}', tabs([(it[0], it[1], it[2], 80 + (j % 5) * 220, 70 + (j // 5) * 330 + (j % 3) * 40, (j % 4 - 1.5) * 2)]), at=C(19) + .1 + j * .17, dy=30)
                                  for j, it in enumerate((TAB_ITEMS * 2)[:10])]
         + [O('tentabs', center('<div class="h1" style="font-size:180px;text-shadow:0 0 60px #05070d,0 0 30px #05070d">10 tabs?</div>'), at=W(19, 'tabs') - .1)]),
    # WHAT  ------------------------------------------------------------
    *[dict(t0=SLOTS[s]['start'], base=SITE(s), ov=[O(f'lbl_{s}', '', t=0)]) for s in
      ('home', 'home-scroll', 'timeline-map', 'final-signal', 'inspect-3d', 'mission-detective', 'montage')],
    dict(t0=C(28), base=I('mer1', 1.0, 1.1, .5, .5, .5, .4), ov=[
        O('src', '<div class="left shadow"><div class="kicker">Every fact</div><div class="h2">NASA &amp; JPL<br>sources</div></div>', t=.3),
        O('quote', '<div class="abs card" style="right:110px;top:300px;width:720px"><div class="kicker" style="color:var(--muted)">Opportunity — in first person</div>'
          '<div class="h3" style="text-transform:none;margin:18px 0 26px">“I was built for ninety days. I kept driving for fourteen years.”</div>'
          '<span class="sig" style="font-size:22px"><span class="dot"></span>Creative interpretation · not a real transmission</span></div>', at=W(29, 'speaks') - .3)]),
    # SO WHAT NEXT  ----------------------------------------------------
    dict(t0=SLOTS['about']['start'], base=SITE('about')),
    dict(t0=C(31), base=V('moonfly', 0.0, 1.0, 1.06), ov=[
        O('dates', '<div class="abs h3 shadow" style="left:120px;top:330px;color:var(--muted)">1966 · 1971 · 2004 · 2018</div>', t=.4),
        O('stories', '<div class="left shadow" style="top:120px"><div class="h2">A story.<br>An ending.<br><span style="color:var(--orange-b)">A reason.</span></div></div>', at=W(31, 'stories') - .2)]),
    dict(t0=C(32), base=V('earthnight', 20.6, 1.0, 1.1, .5, .5), ov=[
        O('stack', '<div class="left shadow"><div class="kicker">Built with</div><div class="h2">HTML · CSS<br>JavaScript</div></div>', t=.3),
        O('nofw', '<div class="abs" style="left:120px;top:760px;display:flex;gap:14px">' + ''.join(
            f'<span class="sig" style="font-size:24px">{r}</span>' for r in ('No framework', 'No backend', 'Works offline')) + '</div>', at=W(32, 'no') - .2)]),
    dict(t0=C(33), base=V('earth4k', 13 * 60 + 40, 1.0, 1.08), ov=[
        O('class', '<div class="left shadow"><div class="kicker">For a classroom</div><div class="h2">with a weak<br>connection</div></div>', t=.3)]),
    dict(t0=SLOTS['nasa-data']['start'], base=SITE('nasa-data')),
    dict(t0=C(35), base=V('apollo11', 21 * 60 + 25, 1.0, 1.06), ov=[
        O('v1', '<div class="left shadow"><div class="kicker">Version 1</div><div class="h2">15 missions.<br>Three asks.</div></div>', t=.3)]),
    dict(t0=C(36), base=V('mcc', 87.0, 1.0, 1.06, pre=MCC), ov=[O('ask1', '<div class="left shadow"><div class="stat" style="color:var(--orange-b)">01</div><div class="h2">Expert review</div><div class="sub">to check and expand the archive</div></div>', t=.2)]),
    dict(t0=C(37), base=V('moonfly', 15.0, 1.0, 1.05), ov=[O('ask2', '<div class="left shadow"><div class="stat" style="color:var(--orange-b)">02</div><div class="h2">More NASA imagery<br>&amp; 3D surface data</div></div>', t=.2)]),
    dict(t0=C(38), base=V('earthnight', 45.9, 1.12, 1.18, .5, .75), ov=[O('ask3', '<div class="left shadow"><div class="stat" style="color:var(--orange-b)">03</div><div class="h2">A Bangla version</div><div class="sub">with teacher resources, for schools here</div></div>', t=.2)]),
    dict(t0=C(39), base=SPLIT(I('voy_art', 1.05, 1.12), I('mer3', 1.05, 1.12, .5, .5, .45, .5)), ov=[
        O('end_l', '<div class="abs" style="left:96px;top:80px"><span class="sig"><span class="dot blue"></span>Voyager · still talking</span></div>', t=.2),
        O('end_r', '<div class="abs" style="left:1056px;top:80px"><span class="sig"><span class="dot"></span>Opportunity · went quiet</span></div>', at=W(39, 'opportunity') - .1)]),
    dict(t0=C(40), base=V('earth4k', 1500, 1.0, 1.06), ov=[O('heard', center('<div class="h2 grad">Both are heard.</div>'), at=W(40, 'both') - .1)]),
    dict(t0=C(41), base=VOID, ov=[
        O('end_sig', center('<span class="sig"><span class="dot"></span>Signal: none</span>', 'justify-content:flex-start;padding-top:230px'), t=.1, dy=0),
        O('end_title', center('<div class="h1 grad">Abandoned,<br>but not forgotten</div>'), t=.25, dy=30),
        O('end_url', center('<div class="sub" style="color:var(--white)">abandonedbutnotforgottenchallenge.netlify.app</div>'
                            '<div class="kicker" style="font-size:22px">Team [Team Name] · [City], Bangladesh</div>', 'justify-content:flex-end;padding-bottom:150px'), t=1.4),
        O('end_credit', '<div class="abs" style="left:0;right:0;bottom:56px;text-align:center;font:400 18px SG;letter-spacing:-1px;color:var(--dim)">Footage and imagery: NASA / JPL-Caltech / GSFC / JSC / KSC. Planet textures and site: Abandoned, But Not Forgotten.</div>', t=1.8)]),
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
