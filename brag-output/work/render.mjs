// usage: node render.mjs <v1|v2> [stills t1,t2,...]
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const root = path.dirname(new URL(import.meta.url).pathname);
const types = { '.html': 'text/html', '.png': 'image/png', '.json': 'application/json', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  fs.readFile(p, (e, b) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); res.end(b); });
}).listen(0);
const port = server.address().port;

const [v, stills] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--disable-gpu'] }).catch(() => chromium.launch());
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
page.on('console', m => console.log('page:', m.text()));
page.on('pageerror', e => console.log('pageerror:', e.message));
await page.goto(`http://127.0.0.1:${port}/render.html`);
await page.evaluate(() => window.ready);
const canvas = await page.$('canvas');
const shot = async (t, file) => { await page.evaluate(([v, t]) => window.renderFrame(v, t), [v, t]); await canvas.screenshot({ path: file, type: 'png' }); };

if (stills) {
  fs.mkdirSync(path.join(root, 'stills'), { recursive: true });
  for (const t of stills.split(',').map(Number)) await shot(t, path.join(root, 'stills', `${v}_${t.toFixed(2)}.png`));
} else {
  const dir = path.join(root, `frames_${v}`); fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir);
  const dur = await page.evaluate(v => window.durationOf(v), v), fps = 30, n = Math.round(dur * fps);
  for (let i = 0; i < n; i++) await shot(i / fps, path.join(dir, String(i).padStart(4, '0') + '.png'));
  console.log('frames', n);
}
await browser.close(); server.close();
