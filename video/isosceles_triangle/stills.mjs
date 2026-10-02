import { chromium } from '/opt/node-tools/node_modules/playwright/index.mjs';
const times = process.argv.slice(2).map(Number);
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
p.on('console', m => console.log('console:', m.text())); p.on('pageerror', e => console.log('ERR', e.message));
await p.goto('file://' + process.cwd() + '/scene.html?scale=1');
await p.evaluate(() => window.ready);
for (const t of times) { await p.evaluate(t => render(t), t); await p.screenshot({ path: `out/still_${t}.png` }); }
await b.close();
