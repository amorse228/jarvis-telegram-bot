import { chromium } from '/opt/node-tools/node_modules/playwright/index.mjs';
import { spawn } from 'child_process';
const FPS = 30, DUR = 30, N = FPS * DUR, WORKERS = +(process.env.WORKERS || 3), SCALE = +(process.env.SCALE || 2);
const b = await chromium.launch({ args: ['--disable-gpu-vsync'] });
const chunk = Math.ceil(N / WORKERS);
async function work(w) {
  const f0 = w * chunk, f1 = Math.min(N, f0 + chunk);
  const p = await b.newPage({ viewport: { width: 1920 * SCALE, height: 1080 * SCALE } });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('file://' + process.cwd() + '/scene.html?scale=' + SCALE);
  await p.evaluate(() => window.ready);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', '-tune', 'animation', `out/seg_${w}.mp4`], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = f0; f < f1; f++) {
    const data = await p.evaluate(t => { render(t); return document.getElementById('c').toDataURL('image/png').split(',')[1]; }, f / FPS);
    const buf = Buffer.from(data, 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 60 === 0) console.log(`w${w} frame ${f}/${f1}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
}
const t0 = Date.now();
await Promise.all([...Array(WORKERS).keys()].map(work));
await b.close();
console.log('done in', (Date.now() - t0) / 1000, 's');
