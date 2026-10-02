// Renders every frame of index.html in parallel headless-Chromium workers and
// encodes them losslessly-ish with ffmpeg; also writes sfx.json for synth.py.
// Usage: node render.js <fps> <out.mp4> [workers]
const { chromium } = require('/opt/node-tools/node_modules/playwright');
const { spawn, execFileSync } = require('child_process');
const fs = require('fs'), path = require('path');

const fps = +(process.argv[2] || 120);
const out = path.resolve(process.argv[3] || 'raw.mp4');
const workers = +(process.argv[4] || 4);
const dir = path.dirname(out);
const page_url = 'file://' + path.resolve(__dirname, '../index.html');

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => console.log('PAGEERROR', e.message));
  await page.goto(page_url);
  await page.evaluate(() => window.ready);
  return page;
}

async function worker(id, from, to) {
  const browser = await chromium.launch({ args: ['--disable-gpu'] });
  const page = await openPage(browser);
  const cdp = await page.context().newCDPSession(page);
  const seg = path.join(dir, `seg_${id}.mp4`);
  const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '6', '-pix_fmt', 'yuv444p', seg], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let i = from; i < to; i++) {
    await page.evaluate(t => window.render(t), i / fps);
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', optimizeForSpeed: true });
    if (!ff.stdin.write(Buffer.from(data, 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
    if ((i - from) % 60 === 0) console.log(`w${id}: ${i - from}/${to - from}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
  await browser.close();
  return seg;
}

(async () => {
  const browser = await chromium.launch();
  const page = await openPage(browser);
  const { sfx, dur } = await page.evaluate(() => ({ sfx: window.SFX, dur: window.DUR }));
  await browser.close();
  fs.writeFileSync(path.join(dir, 'sfx.json'), JSON.stringify({ dur, sfx }, null, 1));
  const n = Math.round(dur * fps), per = Math.ceil(n / workers);
  const segs = await Promise.all([...Array(workers)].map((_, k) => worker(k, k * per, Math.min(n, (k + 1) * per))));
  const list = path.join(dir, 'segs.txt');
  fs.writeFileSync(list, segs.map(s => `file '${s}'`).join('\n'));
  execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', out]);
  console.log('done', out, n, 'frames');
})();
