// Frame-exact screen captures of the website, one clip per slot in site_slots.json.
// The page clock (performance.now, Date.now, rAF, timers, CSS/Web animations) is virtualised and advanced
// 1/30 s per screenshot, so slow software WebGL still yields smooth 30 fps footage.
// usage: node record_site.js <site_url> <out_dir> [slug,...]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const BASE = process.argv[2], OUT = process.argv[3], ONLY = process.argv[4] ? process.argv[4].split(',') : null;
const THREE = process.env.THREE_DIR, FPS = 30, VW = 1600, VH = 900;
const slots = Object.fromEntries(JSON.parse(fs.readFileSync(path.join(__dirname, 'site_slots.json'))).map(s => [s.slug, s.end - s.start]));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ez = x => { x = Math.max(0, Math.min(1, x)); return x < .5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2; };
// scroll keyframes: [[t, y], ...] eased between
const path_ = k => t => { if (t <= k[0][0]) return k[0][1]; for (let i = 1; i < k.length; i++) if (t <= k[i][0]) { const [ta, ya] = k[i - 1], [tb, yb] = k[i]; return ya + (yb - ya) * ez((t - ta) / (tb - ta)); } return k[k.length - 1][1]; };

const VIRTUAL_CLOCK = `(() => {
  const rNow = performance.now.bind(performance), rDate = Date.now, rRaf = window.requestAnimationFrame.bind(window),
        rCancel = window.cancelAnimationFrame.bind(window), rST = window.setTimeout.bind(window), rSI = window.setInterval.bind(window),
        rCT = window.clearTimeout.bind(window), rCI = window.clearInterval.bind(window);
  let on = false, vt = 0, d0 = 0, seq = 1e6; const raf = new Map(), timers = new Map(), born = new WeakMap();
  performance.now = () => on ? vt : rNow();
  Date.now = () => on ? d0 + vt : rDate();
  window.requestAnimationFrame = cb => on ? (raf.set(++seq, cb), seq) : rRaf(cb);
  window.cancelAnimationFrame = id => { raf.delete(id); rCancel(id); };
  window.setTimeout = (cb, ms = 0, ...a) => on ? (timers.set(++seq, { due: vt + (+ms || 0), cb, a }), seq) : rST(cb, ms, ...a);
  window.setInterval = (cb, ms = 0, ...a) => on ? (timers.set(++seq, { due: vt + (+ms || 0), cb, a, every: Math.max(4, +ms || 0) }), seq) : rSI(cb, ms, ...a);
  window.clearTimeout = id => { timers.delete(id); rCT(id); };
  window.clearInterval = id => { timers.delete(id); rCI(id); };
  const anims = () => { for (const a of document.getAnimations()) { if (!born.has(a)) born.set(a, vt - (+a.currentTime || 0)); try { a.pause(); a.currentTime = vt - born.get(a); } catch (e) {} } };
  window.__startVirtual = () => { vt = rNow(); d0 = rDate() - vt; on = true; anims(); };
  window.__step = dt => {
    vt += dt;
    for (let guard = 0; guard < 200; guard++) {
      let next = null; for (const [id, t] of timers) if (t.due <= vt && (!next || t.due < next[1].due)) next = [id, t];
      if (!next) break; const [id, t] = next;
      if (t.every) t.due += t.every; else timers.delete(id);
      try { typeof t.cb === 'function' ? t.cb(...t.a) : eval(t.cb); } catch (e) { console.error(e); }
    }
    const q = [...raf.values()]; raf.clear();
    for (const cb of q) try { cb(vt); } catch (e) { console.error(e); }
    anims();
  };
})();`;

// a clip is a list of parts; each part loads a route fresh, then is captured frame by frame
// part: { route, dur (s) or share (fraction of slot), wait (ms load time), prep(p), scroll: [[t,y]...] (relative to start y), ev: [[t, fn]], each(p, t) }
const at = (t, fn) => [t, fn];
const clickText = (text, sel = 'button, a, [role=button], label') => async p => { const el = p.locator(sel, { hasText: text }).first(); if (await el.count()) await el.click({ timeout: 3000, force: true }).catch(e => console.log('click fail', text)); else console.log('no', text); };
const scrollToText = (text, off = 140) => async p => { await p.evaluate(([t, off]) => { const el = [...document.querySelectorAll('h1,h2,h3,button,label,p,div')].find(e => e.children.length < 3 && e.textContent.trim().startsWith(t)); if (el) window.scrollTo({ top: el.getBoundingClientRect().top + scrollY - off, behavior: 'instant' }); }, [text, off]); };
const skipIntro = async p => { await clickText('Skip intro')(p); await sleep(1200); };
const bigCanvas = async p => p.evaluate(() => { let best = null, A = 0; for (const c of document.querySelectorAll('canvas')) { const r = c.getBoundingClientRect(); if (r.width * r.height > A && r.width > 200) { A = r.width * r.height; best = { x: r.x, y: r.y, width: r.width, height: r.height }; } } return best; });
function dragCanvas(t0, t1, dx, dy = 0) {
  let box = null, down = false;
  return async (p, t) => {
    if (t < t0 || (t > t1 && !down)) return;
    if (!box) box = await bigCanvas(p);
    if (!box) return;
    const cx = box.x + box.width / 2, cy = box.y + box.height / 2, k = Math.min(1, (t - t0) / (t1 - t0));
    if (!down) { await p.mouse.move(cx - dx / 2, cy); await p.mouse.down(); down = true; }
    await p.mouse.move(cx - dx / 2 + dx * ez(k), cy + dy * Math.sin(k * Math.PI));
    if (k >= 1) { await p.mouse.up(); down = false; t1 = -1; }
  };
}
const selectMission = name => async p => { const s = p.locator('select').first(); if (await s.count()) { const v = await s.evaluate((el, n) => { const o = [...el.options].find(o => o.textContent.includes(n)); return o && o.value; }, name); if (v) await s.selectOption(v).catch(() => {}); } };
const CLIPS = {
  'home': [{ route: '', wait: 2500, share: 1, ev: [at(5.6, clickText('Skip intro'))], scroll: [[7.0, 0], [9.8, 420]] }],
  'home-scroll': [{ route: '', wait: 2500, share: 1, prep: skipIntro, scroll: [[.1, 300], [7.4, 4200]] }],
  'timeline-map': [
    { route: 'timeline', wait: 3000, share: .5, prep: scrollToText('Six decades', 120), ev: [at(.6, clickText('1970s')), at(1.7, clickText('2000s'))] },
    { route: 'map', wait: 4000, share: .5, ev: [at(.7, clickText('Mars'))], scroll: [[1.2, 0], [2.9, 260]] }],
  'final-signal': [{ route: 'final-signal', wait: 3000, share: 1, ev: [at(.8, selectMission('Opportunity'))], scroll: [[2.0, 0], [6.5, 600], [8.5, 600], [12.6, 1150]] }],
  'inspect-3d': [{ route: 'inspect', wait: 7000, share: 1, each: dragCanvas(.1, 3.5, 560, -30) }],
  'mission-detective': [{ route: 'detective', wait: 3000, share: 1, ev: [at(1.4, clickText('Start Game'))], scroll: [[2.4, 0], [5.0, 120]] }],
  'montage': [
    { route: 'compare', wait: 3000, share: .25, prep: scrollToText('Select', 300), ev: [at(.1, clickText('Spirit', '.compare-pick-item')), at(.5, clickText('Opportunity', '.compare-pick-item'))] },
    { route: 'quiz', wait: 3000, share: .25, ev: [at(.4, clickText('Mars', '.quiz-option'))] },
    { route: 'game', wait: 6000, share: .25 },
    { route: 'explore', wait: 5000, share: .25 }],
  'about': [{ route: 'about', wait: 3000, share: 1, scroll: [[.3, 0], [3.0, 380]] }],
  'nasa-data': [{ route: 'data', wait: 3000, share: 1, scroll: [[1.5, 0], [8.0, 900]] }],
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  for (const [slug, parts] of Object.entries(CLIPS)) {
    if (ONLY && !ONLY.includes(slug)) continue;
    const total = slots[slug], outFile = path.join(OUT, slug + '.mp4');
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', outFile], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now(); let frames = 0;
    for (const part of parts) {
      const ctx = await b.newContext({ viewport: { width: VW, height: VH } });
      const p = await ctx.newPage();
      await p.addInitScript(VIRTUAL_CLOCK);
      await p.route(/\.netlify\/scripts/, r => r.abort());
      await p.addInitScript(() => document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style'); s.textContent = '[class*=netlify i],[id*=netlify i]{display:none!important}'; document.head.appendChild(s); }));
      if (THREE) {
        await p.route(/three\.min\.js/, r => r.fulfill({ path: THREE + '/build/three.min.js', contentType: 'text/javascript' }));
        await p.route(/GLTFLoader\.js/, r => r.fulfill({ path: THREE + '/examples/js/loaders/GLTFLoader.js', contentType: 'text/javascript' }));
        await p.route(/DRACOLoader\.js/, r => r.fulfill({ path: THREE + '/examples/js/loaders/DRACOLoader.js', contentType: 'text/javascript' }));
      }
      await p.goto(BASE.replace(/\/$/, '') + '/' + part.route, { waitUntil: 'load' });
      await sleep(part.wait);
      if (part.route) await p.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
      if (part.prep) await part.prep(p);
      await sleep(400);
      const y0 = await p.evaluate(() => scrollY);
      await p.evaluate(() => window.__startVirtual());
      const n = Math.round((part.dur || part.share * total) * FPS), sy = part.scroll ? path_(part.scroll) : null, ev = [...(part.ev || [])];
      for (let i = 0; i < n; i++) {
        const t = i / FPS;
        if (sy) await p.evaluate(y => window.scrollTo({ top: y, behavior: 'instant' }), y0 + sy(t));
        while (ev.length && ev[0][0] <= t) await ev.shift()[1](p);
        if (part.each) await part.each(p, t);
        await p.evaluate(dt => window.__step(dt), 1000 / FPS);
        const buf = await p.screenshot({ type: 'jpeg', quality: 92 });
        if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
        frames++;
      }
      await ctx.close();
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
    console.log(`${slug}: ${frames} frames (${(frames / FPS).toFixed(1)}s) in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  await b.close();
})();
