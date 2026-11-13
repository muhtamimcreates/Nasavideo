// Renders text/graphic overlays to transparent 1920x1080 PNGs.
// Type: Space Grotesk, -1px tracking everywhere; colours from the website's design tokens.
// usage: node overlays.js <overlays.json> <out_dir>      (json: { id: html, ... })
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [, , IN, OUT] = process.argv;
const F = path.join(__dirname, 'fonts');
const face = (w, f) => `@font-face{font-family:SG;font-weight:${w};src:url(data:font/ttf;base64,${fs.readFileSync(path.join(F, f)).toString('base64')}) format('truetype')}`;
const CSS = `
${face(300, 'SpaceGrotesk-300.ttf')}${face(400, 'SpaceGrotesk-Regular.ttf')}${face(500, 'SpaceGrotesk-Medium.ttf')}${face(600, 'SpaceGrotesk-600.ttf')}${face(700, 'SpaceGrotesk-Bold.ttf')}
:root{--void:#05070d;--panel:#0d1220;--hair:rgba(150,170,210,.22);--blue:#3f7ce0;--blue-b:#6fa2f2;--orange:#cf6a34;--orange-b:#e8925a;--white:#f2f4f9;--muted:#8b93a8;--dim:#5c6478}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1920px;height:1080px;background:transparent;overflow:hidden}
body{font-family:SG;letter-spacing:-1px;color:var(--white);position:relative;-webkit-font-smoothing:antialiased}
.abs{position:absolute}
.tag{position:absolute;left:96px;top:80px;display:flex;gap:18px;align-items:center;font:500 24px SG;letter-spacing:-1px;text-transform:uppercase;color:var(--muted)}
.tag b{color:var(--white);font-weight:600}
.dot{width:12px;height:12px;border-radius:50%;background:var(--orange-b);box-shadow:0 0 16px var(--orange-b)}
.dot.blue{background:var(--blue-b);box-shadow:0 0 16px var(--blue-b)}
.sig{display:inline-flex;gap:14px;align-items:center;font:600 26px SG;letter-spacing:-1px;text-transform:uppercase;color:var(--white);padding:12px 22px;border:1px solid var(--hair);border-radius:4px;background:rgba(5,7,13,.55);backdrop-filter:blur(6px)}
.kicker{font:600 26px SG;letter-spacing:-1px;text-transform:uppercase;color:var(--orange-b)}
.h1{font:700 132px/0.92 SG;letter-spacing:-1px;text-transform:uppercase}
.h2{font:700 88px/0.95 SG;letter-spacing:-1px;text-transform:uppercase}
.h3{font:600 56px/1.02 SG;letter-spacing:-1px;text-transform:uppercase}
.sub{font:400 32px/1.3 SG;letter-spacing:-1px;color:var(--muted)}
.grad{background:linear-gradient(180deg,#ffffff 30%,#b9c4dc);-webkit-background-clip:text;color:transparent}
.shadow{text-shadow:0 2px 30px rgba(0,0,0,.65)}
.shadow .grad,.grad.shadow{text-shadow:none;filter:drop-shadow(0 3px 24px rgba(0,0,0,.55))}
.center{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:26px}
.left{position:absolute;left:120px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;gap:22px}
.stat{font:700 168px/0.9 SG;letter-spacing:-1px}
.rule{width:96px;height:3px;background:var(--orange-b)}
.tab{position:absolute;width:760px;border:1px solid var(--hair);border-radius:8px;background:var(--panel);box-shadow:0 30px 80px rgba(0,0,0,.6);overflow:hidden}
.tab .bar{height:46px;display:flex;align-items:center;gap:10px;padding:0 16px;background:#121829;border-bottom:1px solid var(--hair);font:500 20px SG;letter-spacing:-1px;color:var(--muted)}
.tab .bar i{width:11px;height:11px;border-radius:50%;background:#2a3350;display:inline-block}
.tab .bar span{margin-left:12px;color:var(--white)}
.tab .body{padding:26px 28px;display:flex;flex-direction:column;gap:14px}
.tab .line{height:14px;border-radius:3px;background:#1c2438}
.tab .k{font:600 18px SG;letter-spacing:-1px;color:var(--orange-b);text-transform:uppercase}
.tab .t{font:600 34px/1.05 SG;letter-spacing:-1px}
.card{border:1px solid var(--hair);border-radius:8px;background:rgba(13,18,32,.82);padding:34px 40px;backdrop-filter:blur(10px)}
`;
(async () => {
  const items = JSON.parse(fs.readFileSync(IN));
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  for (const [id, html] of Object.entries(items)) {
    await p.setContent(`<!doctype html><html><head><style>${CSS}</style></head><body>${html}</body></html>`);
    await p.evaluate(async () => { for (const w of [400, 500, 600, 700]) if (!(await document.fonts.load(w + ' 40px SG')).length) throw new Error('font ' + w + ' not loaded'); await document.fonts.ready; });
    await p.screenshot({ path: path.join(OUT, id + '.png'), omitBackground: true });
  }
  await b.close();
  console.log('overlays:', Object.keys(items).length);
})();
