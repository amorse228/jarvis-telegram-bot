// Usage: node snap.js out_dir t1 t2 ...   -> PNG stills at given times
const { chromium } = require('/opt/node-tools/node_modules/playwright');
const path = require('path');
(async () => {
  const [out, ...ts] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('console', m => console.log('console:', m.text()));
  page.on('pageerror', e => console.log('PAGEERROR', e.message));
  await page.goto('file://' + path.resolve(__dirname, '../index.html'));
  await page.evaluate(() => window.ready);
  for (const t of ts) {
    await page.evaluate(t => window.render(t), +t);
    await page.screenshot({ path: `${out}/t_${(+t).toFixed(2)}.png` });
  }
  await browser.close();
})();
