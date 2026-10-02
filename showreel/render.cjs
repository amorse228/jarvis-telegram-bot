// Renders index.html frame-by-frame with headless Chromium and pipes it into ffmpeg.
//   node render.cjs                      -> grok-bot-showreel.mp4 (needs audio.wav from audio.py)
//   node render.cjs --stills 1.2,4.8,... -> stills/frame_<t>.png for review
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

(async () => {
  const dir = __dirname;
  const args = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(dir, 'index.html') + '?render=1');
  await page.evaluate(() => window.ready);
  const grab = (t, type, q) => page.evaluate(([t, type, q]) => { renderFrame(t); return document.getElementById('c').toDataURL(type, q); }, [t, type, q]);

  if (args[0] === '--stills') {
    fs.mkdirSync(path.join(dir, 'stills'), { recursive: true });
    for (const t of args[1].split(',').map(Number)) {
      const url = await grab(t, 'image/png');
      fs.writeFileSync(path.join(dir, 'stills', `frame_${t.toFixed(2)}.png`), Buffer.from(url.split(',')[1], 'base64'));
    }
    await browser.close();
    return;
  }

  const fps = await page.evaluate(() => window.FPS), dur = await page.evaluate(() => window.DUR);
  const out = path.join(dir, 'grok-bot-showreel.mp4');
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
    '-i', path.join(dir, 'audio.wav'), '-c:v', 'libx264', '-preset', 'slow', '-crf', '22', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const total = fps * dur;
  for (let i = 0; i < total; i++) {
    const url = await grab(i / fps, 'image/jpeg', 0.96);
    if (!ff.stdin.write(Buffer.from(url.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 60 === 0) process.stdout.write(`frame ${i}/${total}\n`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  console.log('wrote', out);
})();
