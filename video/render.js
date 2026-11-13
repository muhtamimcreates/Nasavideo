// Renders scenes.html frame-by-frame into base.mp4 (no captions/audio).
// usage: node render.js [out.mp4] [fps]   |   node render.js --stills t1,t2,... outdir
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs'), path = require('path');
(async () => {
  const tl = JSON.parse(fs.readFileSync(path.join(__dirname, 'timeline.json')));
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('pageerror', e => { console.error('PAGE ERROR', e); process.exit(1); });
  await page.goto('file://' + path.join(__dirname, 'scenes.html'));
  await page.evaluate(() => window.__ready);
  const slots = await page.evaluate(tl => setup(tl), tl);
  fs.writeFileSync(path.join(__dirname, 'site_slots.json'), JSON.stringify(slots, null, 1));
  const grab = async t => {
    const b64 = await page.evaluate(t => { draw(t); return document.getElementById('c').toDataURL('image/jpeg', .92).slice(23); }, t);
    return Buffer.from(b64, 'base64');
  };
  if (process.argv[2] === '--stills') {
    const dir = process.argv[4]; fs.mkdirSync(dir, { recursive: true });
    for (const t of process.argv[3].split(',').map(Number)) fs.writeFileSync(path.join(dir, `t${t.toFixed(1).padStart(6, '0')}.jpg`), await grab(t));
    await browser.close(); return;
  }
  const outFile = process.argv[2] || 'base.mp4', fps = +(process.argv[3] || 30);
  const n = Math.ceil(tl.total * fps);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(fps), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', outFile], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let i = 0; i < n; i++) {
    const buf = await grab(i / fps);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${n}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
  await browser.close();
})();
