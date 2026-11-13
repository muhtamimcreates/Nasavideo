// Frame-exact screen captures of the website, one clip per slot in site_slots.json.
// The page clock (performance.now, Date.now, rAF, timers, CSS/Web animations) is virtualised and advanced
// 1/30 s per screenshot, so slow software WebGL still yields smooth 30 fps footage.
// usage: THREE_DIR=<three pkg dir> node record_site.js <site_url> <out_dir> [slug,...]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const BASE = process.argv[2], OUT = process.argv[3], ONLY = process.argv[4] ? process.argv[4].split(',') : null;
const THREE = process.env.THREE_DIR, FPS = 30, VW = 1680, VH = 740;
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
// part: { hash, dur (s) or share (fraction of slot), wait (ms load time), prep(p), scroll: [[t,y]...] (relative to start y), ev: [[t, fn]], each(p, t) }
const at = (t, fn) => [t, fn];
const click = (sel, text) => async p => { const el = p.locator(sel, { hasText: text }).first(); if (await el.count()) await el.click({ timeout: 3000, force: true }).catch(e => console.log('click fail', sel, text)); };
const scrollToSel = sel => async p => { await p.evaluate(sel => { const s = document.querySelector(sel); if (s) window.scrollTo({ top: s.getBoundingClientRect().top + scrollY - 110, behavior: 'instant' }); }, sel); };
function dragOn(sel, t0, t1, dx, dy = 0) {
  let box = null, down = false;
  return async (p, t) => {
    if (t < t0 || (t > t1 && !down)) return;
    if (!box) box = await p.locator(sel).first().boundingBox();
    if (!box) return;
    const cx = box.x + box.width / 2, cy = box.y + box.height / 2, k = Math.min(1, (t - t0) / (t1 - t0));
    if (!down) { await p.mouse.move(cx - dx / 2, cy); await p.mouse.down(); down = true; }
    await p.mouse.move(cx - dx / 2 + dx * ez(k), cy + dy * Math.sin(k * Math.PI));
    if (k >= 1) { await p.mouse.up(); down = false; t1 = -1; }
  };
}
const CLIPS = {
  'home': [{ hash: 'home', wait: 6000, share: 1, scroll: [[4.4, 0], [8.2, 640]] }],
  'home-scroll': [{ hash: 'home', wait: 6000, share: 1, prep: scrollToSel('.story'), scroll: [[.2, 0], [7.5, 2500]] }],
  'timeline-hardware-map': [
    { hash: 'timeline', wait: 3500, share: .5, prep: scrollToSel('.dec-tabs'), ev: [at(.5, click('.dtab', '1970s')), at(1.6, click('.dtab', '2000s'))] },
    { hash: 'map', wait: 6000, share: .5, prep: scrollToSel('.map-ui'), each: dragOn('.map-stage canvas', .2, 2.9, 380, 40) }],
  'final-signal': [{ hash: 'final-signal', wait: 3500, share: 1, scroll: [[2.4, 0], [6.4, 520], [8.0, 520], [12.2, 1100]] }],
  'inspect-3d': [{ hash: 'inspect', wait: 7000, share: 1, prep: scrollToSel('.insp-pick'), each: dragOn('.insp-stage canvas', .2, 3.6, 520, -30) }],
  'mission-detective': [{ hash: 'detective', wait: 3500, share: 1, scroll: [[2.2, 0], [3.8, 330]], ev: [at(4.8, click('.opt', 'Spirit')), at(6.1, click('.game-card button.cta', ''))] }],
  'compare-quiz-3d-game-explore-mars': [
    { hash: 'compare', wait: 3500, share: .25, scroll: [[.1, 0], [1.1, 300]] },
    { hash: 'quiz', wait: 3500, share: .25, ev: [at(.5, click('.opt', 'Mars'))] },
    { hash: 'game', wait: 7000, share: .25, prep: scrollToSel('.game-stage'), ev: [at(0, p => p.locator('.game-stage').first().focus().catch(() => {})), at(.05, p => p.keyboard.down('ArrowUp')), at(1.1, p => p.keyboard.up('ArrowUp'))] },
    { hash: 'explore', wait: 7000, share: .25, prep: scrollToSel('.exp-tabs') }],
  'about': [{ hash: 'about', wait: 3500, share: 1, scroll: [[.2, 0], [2.2, 240]] }],
  'nasa-data': [{ hash: 'data', wait: 3500, share: 1, scroll: [[2.0, 0], [6.6, 700]] }],
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
      if (THREE) {
        await p.route(/three\.min\.js/, r => r.fulfill({ path: THREE + '/build/three.min.js', contentType: 'text/javascript' }));
        await p.route(/GLTFLoader\.js/, r => r.fulfill({ path: THREE + '/examples/js/loaders/GLTFLoader.js', contentType: 'text/javascript' }));
        await p.route(/DRACOLoader\.js/, r => r.fulfill({ path: THREE + '/examples/js/loaders/DRACOLoader.js', contentType: 'text/javascript' }));
      }
      await p.goto(BASE + '#' + part.hash, { waitUntil: 'load' });
      await sleep(part.wait);
      await p.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
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
