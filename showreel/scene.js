// Grok Bot — 15s motion reel. Deterministic: renderFrame(t) draws time t (seconds).
const W = 1920, H = 1080, DUR = 15, FPS = 60;
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');
const buf = document.createElement('canvas'); buf.width = W; buf.height = H;
const bctx = buf.getContext('2d');
const off = document.createElement('canvas'); off.width = W; off.height = H;
const octx = off.getContext('2d');

// ---------- utils ----------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const lerp = (a, b, k) => a + (b - a) * k;
const E = {
  outExpo: k => (k >= 1 ? 1 : 1 - Math.pow(2, -10 * k)),
  inExpo: k => (k <= 0 ? 0 : Math.pow(2, 10 * k - 10)),
  outCubic: k => 1 - Math.pow(1 - k, 3),
  inCubic: k => k * k * k,
  inOutCubic: k => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
  inOutExpo: k => (k <= 0 ? 0 : k >= 1 ? 1 : k < 0.5 ? Math.pow(2, 20 * k - 10) / 2 : (2 - Math.pow(2, -20 * k + 10)) / 2),
  outBack: k => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); },
};
function rng(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const CYAN = '#3df5ff', MAGENTA = '#ff2d6f', AMBER = '#ffb547';

function setFont(c, size, fam, w, ls) {
  c.font = `${w} ${size}px ${fam}`;
  c.letterSpacing = (ls || 0) + 'px';
}
function text(s, x, y, o = {}) {
  const { size = 100, fam = 'IN', w = 900, color = '#fff', align = 'center', base = 'middle', ls = 0, alpha = 1, c = ctx } = o;
  c.save();
  c.globalAlpha *= alpha;
  setFont(c, size, fam, w, ls);
  c.textAlign = align; c.textBaseline = base; c.fillStyle = color;
  c.fillText(s, align === 'center' ? x + ls / 2 : x, y);
  c.restore();
}
function chroma(s, x, y, o, amt) {
  if (amt > 0.3) {
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    text(s, x - amt, y, { ...o, color: MAGENTA, alpha: (o.alpha ?? 1) * 0.9 });
    text(s, x + amt, y + amt * 0.25, { ...o, color: CYAN, alpha: (o.alpha ?? 1) * 0.9 });
    ctx.restore();
  }
  text(s, x, y, o);
}
// per-letter layout: returns [{ch, x}] where x is letter center relative to string center
function letters(s, size, fam, w, ls) {
  setFont(ctx, size, fam, w, ls);
  const ws = [...s].map(ch => ctx.measureText(ch).width);
  const total = ws.reduce((a, b) => a + b, 0) - ls;
  let x = -total / 2; const out = [];
  [...s].forEach((ch, i) => { out.push({ ch, x: x + (ws[i] - ls) / 2 }); x += ws[i]; });
  return out;
}

// ---------- global timing ----------
const IMPACTS = [[1.5, 1], [2.5, 0.5], [3.0, 0.6], [6.0, 1], [7.4, 0.8], [9.0, 0.7], [9.5, 0.7], [10.0, 0.7], [11.5, 1], [12.3, 0.3]];
const GLITCHES = [1.5, 2.5, 6.0, 9.0, 9.5, 10.0, 11.5];
function shake(t) {
  let x = 0, y = 0;
  for (const [ti, a] of IMPACTS) if (t >= ti) {
    const d = t - ti, e = a * Math.exp(-d * 9) * 26;
    x += Math.sin(d * 93 + ti * 7) * e; y += Math.cos(d * 71 + ti * 3) * e;
  }
  return [x, y];
}
function flashAmt(t) {
  let f = 0;
  for (const [ti, a] of IMPACTS) if (t >= ti) f = Math.max(f, a * Math.exp(-(t - ti) * 14));
  return f;
}

// ---------- precomputed assets ----------
const grain = [];
function buildGrain() {
  const r = rng(7);
  for (let g = 0; g < 6; g++) {
    const c = document.createElement('canvas'); c.width = 480; c.height = 270;
    const x = c.getContext('2d'); const id = x.createImageData(480, 270);
    for (let i = 0; i < id.data.length; i += 4) { const v = r() * 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255; }
    x.putImageData(id, 0, 0); grain.push(c);
  }
}

const nodes = [];
function buildNodes() {
  const r = rng(21);
  for (let i = 0; i < 95; i++) nodes.push({ x: r() * W, y: r() * H, ph: r() * 6.28, sp: 0.3 + r() * 0.7, amp: 20 + r() * 40 });
}

let particles = [];
const LOGO_Y = 480;
function buildLogoParticles() {
  octx.clearRect(0, 0, W, H);
  text('GROK BOT', W / 2, LOGO_Y, { size: 290, w: 900, ls: 4, c: octx });
  const d = octx.getImageData(0, 0, W, H).data;
  const r = rng(99);
  for (let y = 0; y < H; y += 5) for (let x = 0; x < W; x += 5) {
    if (d[(y * W + x) * 4 + 3] > 128) {
      const a = r() * Math.PI * 2, rad = 700 + r() * 900;
      particles.push({
        tx: x, ty: y, sx: W / 2 + Math.cos(a) * rad, sy: LOGO_Y + Math.sin(a) * rad * 0.7,
        delay: 0.05 + (x / W) * 0.4 + r() * 0.12, dur: 0.55 + r() * 0.25, cyan: r() < 0.25, sz: 2 + r() * 2.5,
        dx: (r() - 0.5) * 2, dy: (r() - 0.5) * 2,
      });
    }
  }
  octx.clearRect(0, 0, W, H);
}

const embers = [];
function buildEmbers() {
  const r = rng(5);
  for (let i = 0; i < 160; i++) {
    const a = r() * Math.PI * 2, v = 200 + r() * 900;
    embers.push({ vx: Math.cos(a) * v, vy: Math.sin(a) * v * 0.6, x0: W / 2 + (r() - 0.5) * 300, y0: H / 2 + (r() - 0.5) * 100, rise: 20 + r() * 60, sz: 1 + r() * 2.5, ph: r() * 6.28 });
  }
}

// ---------- scene helpers ----------
function background(t, tint = '61,245,255', strength = 0.08) {
  ctx.fillStyle = '#050507'; ctx.fillRect(0, 0, W, H);
  const g = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, 1100);
  g.addColorStop(0, `rgba(${tint},${strength})`); g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
}
function rings(t, alpha, cx = W / 2, cy = H / 2) {
  ctx.save(); ctx.translate(cx, cy);
  [[300, 0.4, [4, 14]], [430, -0.25, [40, 12, 4, 12]], [580, 0.15, [2, 22]], [760, -0.1, [120, 30]]].forEach(([rad, sp, dash], i) => {
    ctx.save(); ctx.rotate(t * sp + i);
    ctx.setLineDash(dash); ctx.strokeStyle = `rgba(255,255,255,${alpha * (0.35 - i * 0.06)})`; ctx.lineWidth = i === 1 ? 2 : 1.2;
    ctx.beginPath(); ctx.arc(0, 0, rad, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
  });
  ctx.restore();
}
function typed(str, t, a, b) { return str.slice(0, Math.floor(seg(t, a, b) * str.length + 0.0001)); }
function caret(t, x, y, h, color = '#fff') { if (Math.floor(t * 4) % 2 === 0) { ctx.fillStyle = color; ctx.fillRect(x + 6, y - h / 2, 3, h); } }
function measure(s, size, fam, w, ls = 0) { setFont(ctx, size, fam, w, ls); return ctx.measureText(s).width; }
function sweep(drawFn, t, a, b, color = 'rgba(255,255,255,0.9)', width = 260) {
  // draws content via drawFn on offscreen canvas, then a diagonal light band clipped to it
  const k = seg(t, a, b); if (k <= 0 || k >= 1) return;
  octx.save(); octx.clearRect(0, 0, W, H); drawFn(octx);
  octx.globalCompositeOperation = 'source-in';
  const x = lerp(-400, W + 400, E.inOutCubic(k));
  const g = octx.createLinearGradient(x - width, 0, x + width, 0);
  g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(0.5, color); g.addColorStop(1, 'rgba(255,255,255,0)');
  octx.fillStyle = g; octx.fillRect(0, 0, W, H); octx.restore();
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.drawImage(off, 0, 0); ctx.restore();
}
const GLYPHS = '!<>-_\\/[]{}=+*^?#@$%&01';
function scramble(str, t, a, b, seed) {
  const k = seg(t, a, b); const r = rng(seed + Math.floor(t * 30));
  return [...str].map((ch, i) => {
    const at = i / str.length;
    if (ch === ' ') return ' ';
    if (k >= at + 0.25) return ch;
    if (k >= at) return GLYPHS[Math.floor(r() * GLYPHS.length)];
    return '';
  }).join('');
}

// ---------- SCENE 1 : 0 – 1.5  ignition ----------
function scene1(t) {
  background(t, '61,245,255', 0.05 + 0.06 * seg(t, 0, 1.5));
  const r = rng(11);
  ctx.save(); ctx.translate(W / 2, H / 2);
  for (let i = 0; i < 160; i++) {
    const a = r() * Math.PI * 2, d0 = 900 + r() * 800, st = r() * 0.6, sp = 0.5 + r() * 0.5, cy = r() < 0.3, lw = 1 + r() * 2.2;
    const k = seg(t, st, st + sp); if (k <= 0 || k >= 1) continue;
    const d = lerp(d0, 10, E.inCubic(k)), len = lerp(20, 300, Math.sin(k * Math.PI));
    ctx.strokeStyle = cy ? `rgba(61,245,255,${0.8 * Math.sin(k * Math.PI)})` : `rgba(255,255,255,${0.7 * Math.sin(k * Math.PI)})`;
    ctx.lineWidth = lw; ctx.beginPath();
    ctx.moveTo(Math.cos(a) * d, Math.sin(a) * d); ctx.lineTo(Math.cos(a) * (d + len), Math.sin(a) * (d + len)); ctx.stroke();
  }
  // core
  const form = E.outExpo(seg(t, 1.0, 1.42));
  const core = (3 + 16 * E.outExpo(seg(t, 0.05, 1.0))) * (1 + 0.15 * Math.sin(t * 40)) * (1 - form * 0.6);
  ctx.shadowColor = CYAN; ctx.shadowBlur = 60;
  ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(0, 0, core, 0, Math.PI * 2); ctx.fill();
  // slash forms
  if (form > 0) {
    ctx.rotate(0.38); ctx.shadowBlur = 80;
    ctx.fillRect(-10, -380 * form, 20, 760 * form);
  }
  ctx.restore();
  // terminal line
  const s = '> summoning grok_bot';
  const shown = typed(s, t, 0.1, 0.95);
  const w = measure(s, 30, 'JB', 500, 2);
  text(shown, W / 2 - w / 2, 880, { size: 30, fam: 'JB', w: 500, ls: 2, align: 'left', color: 'rgba(220,240,255,0.85)' });
  caret(t, W / 2 - w / 2 + measure(shown, 30, 'JB', 500, 2), 880, 34, CYAN);
}

// ---------- SCENE 2 : 1.5 – 3.5  kinetic type ----------
function scene2(t) {
  background(t, '61,245,255', 0.07);
  // diagonal speed stripes
  ctx.save(); ctx.translate(W / 2, H / 2); ctx.rotate(0.38);
  const r = rng(3);
  for (let i = 0; i < 26; i++) {
    const x = (r() - 0.5) * 2600, w = 1 + r() * 4, sp = 900 + r() * 1800, len = 200 + r() * 600;
    const y = ((r() * 3000 + (t - 1.5) * sp) % 3000) - 1500;
    ctx.fillStyle = `rgba(255,255,255,${0.04 + r() * 0.08})`; ctx.fillRect(x, y, w, len);
  }
  ctx.restore();
  rings(t, E.outExpo(seg(t, 1.5, 2.0)));
  // the slash from scene 1 exits left in triplicate
  const ex = E.inExpo(seg(t, 1.5, 1.85));
  if (ex < 1) {
    ctx.save(); ctx.translate(W / 2, H / 2);
    [[0, '#fff'], [60, CYAN], [-60, MAGENTA]].forEach(([o, c], i) => {
      ctx.save(); ctx.translate(-ex * (1500 + i * 300) + o * ex, 0); ctx.rotate(0.38);
      ctx.fillStyle = c; ctx.globalAlpha = i ? 0.6 : 1; ctx.fillRect(-10, -380, 20, 760); ctx.restore();
    });
    ctx.restore();
  }
  const lt = t - 1.5;
  if (t < 2.5) {
    const o = { size: 250, w: 900, ls: -6 };
    const L = letters('ONE TAG.', o.size, 'IN', o.w, o.ls);
    const amt = 18 * Math.exp(-lt * 6);
    L.forEach((l, i) => {
      const k = seg(t, 1.5 + i * 0.035, 1.5 + i * 0.035 + 0.4);
      if (k <= 0) return;
      const y = lerp(-320, 0, E.outExpo(k)), rot = (1 - E.outExpo(k)) * (i % 2 ? 0.4 : -0.4);
      ctx.save(); ctx.translate(W / 2 + l.x, H / 2 + y); ctx.rotate(rot);
      chroma(l.ch, 0, 0, { ...o, alpha: clamp(k * 4) }, amt);
      ctx.restore();
    });
    // subtle push
    const sub = E.outExpo(seg(t, 1.9, 2.3));
    text('ONE TAG. ANY QUESTION. RIGHT IN THE THREAD.', W / 2, 720, { size: 22, fam: 'JB', w: 500, ls: 10, color: 'rgba(255,255,255,0.55)', alpha: sub });
  } else {
    const k1 = E.outExpo(seg(t, 2.5, 3.0)), k2 = E.outExpo(seg(t, 3.0, 3.25));
    const ls = lerp(180, 6, k1);
    const y1 = lerp(H / 2, 440, k2);
    const amt1 = 14 * Math.exp(-(t - 2.5) * 7);
    chroma('INFINITE', W / 2, y1, { size: 210, w: 900, ls, alpha: clamp((t - 2.5) * 8) }, amt1);
    if (t >= 3.0) {
      const sc = lerp(1.9, 1, k2);
      // motion trail
      for (let j = 4; j >= 1; j--) {
        const s2 = lerp(1.9, 1, E.outExpo(seg(t - j * 0.012, 3.0, 3.25)));
        ctx.save(); ctx.translate(W / 2, 650); ctx.scale(s2, s2);
        text('ANSWERS.', 0, 0, { size: 210, w: 900, ls: 6, color: CYAN, alpha: 0.12 }); ctx.restore();
      }
      ctx.save(); ctx.translate(W / 2, 650); ctx.scale(sc, sc);
      chroma('ANSWERS.', 0, 0, { size: 210, w: 900, ls: 6, color: CYAN }, 16 * Math.exp(-(t - 3.0) * 7));
      ctx.restore();
    }
  }
  // transition bars in
  const cols = 10;
  for (let i = 0; i < cols; i++) {
    const k = E.inOutCubic(seg(t, 3.28 + i * 0.015, 3.47 + i * 0.015));
    if (k <= 0) continue;
    ctx.fillStyle = i % 3 === 1 ? CYAN : '#f4f6fb';
    ctx.fillRect(i * W / cols, H - H * k, W / cols + 1, H * k);
  }
}

// ---------- SCENE 3 : 3.5 – 6.0  the conversation ----------
const Q_TEXT = '@grok explain black holes like I\'m five';
const A_TEXT = 'Picture a cosmic drain so strong that not even light can climb back out. That\'s a black hole.';
const CARD_W = 1000, CX0 = (W - CARD_W) / 2;
const C1Y = 285, C2Y = 535;
const AV2 = [CX0 + 70, C2Y + 72];
function wrapWords(s, size, maxW) {
  setFont(ctx, size, 'IN', 400, 0);
  const words = s.split(' '); const out = []; let x = 0, line = 0; const sp = ctx.measureText(' ').width;
  words.forEach(wd => { const w = ctx.measureText(wd).width; if (x + w > maxW) { x = 0; line++; } out.push({ wd, x, line, w }); x += w + sp; });
  return out;
}
function avatarGrok(x, y, r, glow) {
  ctx.save();
  ctx.shadowColor = CYAN; ctx.shadowBlur = 30 * glow;
  ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
  ctx.shadowBlur = 0; ctx.strokeStyle = CYAN; ctx.lineWidth = 2.5; ctx.stroke();
  ctx.translate(x, y); ctx.rotate(0.38); ctx.fillStyle = '#fff'; ctx.fillRect(-2.5, -r * 0.55, 5, r * 1.1);
  ctx.restore();
}
function card(x, y, w, h, alpha) {
  ctx.save(); ctx.globalAlpha *= alpha;
  ctx.fillStyle = 'rgba(16,18,24,0.94)'; ctx.strokeStyle = 'rgba(255,255,255,0.13)'; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.roundRect(x, y, w, h, 28); ctx.fill(); ctx.stroke(); ctx.restore();
}
function scene3(t) {
  background(t, '80,110,255', 0.1);
  ctx.save();
  // camera
  const s = lerp(1.12, 1.18, E.inOutCubic(seg(t, 3.5, 5.7)));
  ctx.translate(W / 2, H / 2); ctx.scale(s, s); ctx.translate(-W / 2, -H / 2);
  const z = lerp(1, 30, E.inExpo(seg(t, 5.65, 6.0)));
  ctx.translate(AV2[0], AV2[1]); ctx.scale(z, z); ctx.translate(-AV2[0], -AV2[1]);
  // network
  const P = nodes.map(n => [n.x + Math.sin(t * n.sp + n.ph) * n.amp, n.y + Math.cos(t * n.sp * 0.8 + n.ph) * n.amp]);
  ctx.lineWidth = 1;
  for (let i = 0; i < P.length; i++) for (let j = i + 1; j < P.length; j++) {
    const dx = P[i][0] - P[j][0], dy = P[i][1] - P[j][1], d = Math.hypot(dx, dy);
    if (d < 200) { ctx.strokeStyle = `rgba(140,170,255,${0.18 * (1 - d / 200)})`; ctx.beginPath(); ctx.moveTo(P[i][0], P[i][1]); ctx.lineTo(P[j][0], P[j][1]); ctx.stroke(); }
  }
  P.forEach(([x, y], i) => { ctx.fillStyle = i % 7 === 0 ? CYAN : 'rgba(255,255,255,0.5)'; ctx.fillRect(x - 1.5, y - 1.5, 3, 3); });
  // data links into the reply card while streaming
  const linkA = seg(t, 4.6, 4.9) * (1 - seg(t, 5.8, 6.0));
  if (linkA > 0) {
    for (let i = 0; i < P.length; i += 4) {
      const [x, y] = P[i]; const tx = AV2[0], ty = AV2[1];
      ctx.strokeStyle = `rgba(61,245,255,${0.12 * linkA})`; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(tx, ty); ctx.stroke();
      const p = ((t * 1.4 + i * 0.13) % 1);
      ctx.fillStyle = `rgba(61,245,255,${0.9 * linkA})`; ctx.fillRect(lerp(x, tx, p) - 2, lerp(y, ty, p) - 2, 4, 4);
    }
  }
  // card 1 — the question
  const k1 = E.outExpo(seg(t, 3.55, 4.0));
  const y1 = C1Y + 260 * (1 - k1);
  card(CX0, y1, CARD_W, 210, k1);
  ctx.save(); ctx.globalAlpha = k1;
  const g = ctx.createLinearGradient(CX0 + 40, y1 + 40, CX0 + 100, y1 + 100); g.addColorStop(0, '#ff8a5b'); g.addColorStop(1, '#ff2d6f');
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(CX0 + 70, y1 + 72, 32, 0, Math.PI * 2); ctx.fill();
  text('You', CX0 + 122, y1 + 60, { size: 30, w: 900, align: 'left' });
  text('@curious_human · now', CX0 + 190, y1 + 61, { size: 26, w: 400, align: 'left', color: '#7b8394' });
  const q = typed(Q_TEXT, t, 3.8, 4.5);
  const qx = CX0 + 122, qy = y1 + 125;
  const tag = q.slice(0, 5), rest = q.slice(5);
  text(tag, qx, qy, { size: 38, w: 500, align: 'left', color: CYAN });
  const tw = measure('@grok', 38, 'IN', 500);
  text(rest, qx + tw, qy, { size: 38, w: 400, align: 'left', color: '#eef1f7' });
  if (t < 4.65) caret(t, qx + (q.length > 5 ? tw + measure(rest, 38, 'IN', 400) : measure(tag, 38, 'IN', 500)), qy, 42, CYAN);
  ctx.restore();
  // card 2 — the reply
  const k2 = E.outExpo(seg(t, 4.55, 4.95));
  if (k2 > 0) {
    const y2 = C2Y + 160 * (1 - k2);
    // glow border while thinking
    card(CX0, y2, CARD_W, 300, k2);
    ctx.save(); ctx.globalAlpha = k2;
    const think = seg(t, 4.6, 4.75) * (1 - seg(t, 5.7, 5.9));
    ctx.strokeStyle = `rgba(61,245,255,${0.55 * think})`; ctx.lineWidth = 2; ctx.shadowColor = CYAN; ctx.shadowBlur = 24 * think;
    ctx.beginPath(); ctx.roundRect(CX0, y2, CARD_W, 300, 28); ctx.stroke(); ctx.shadowBlur = 0;
    avatarGrok(CX0 + 70, y2 + 72, 32, think);
    text('Grok', CX0 + 122, y2 + 60, { size: 30, w: 900, align: 'left' });
    text('@grok · replying', CX0 + 207, y2 + 61, { size: 26, w: 400, align: 'left', color: '#7b8394' });
    if (t < 4.98) {
      for (let i = 0; i < 3; i++) {
        const b = Math.max(0, Math.sin(t * 14 - i * 0.9));
        ctx.fillStyle = `rgba(255,255,255,${0.4 + 0.6 * b})`; ctx.beginPath(); ctx.arc(CX0 + 140 + i * 26, y2 + 130 - b * 8, 7, 0, Math.PI * 2); ctx.fill();
      }
    } else {
      const words = wrapWords(A_TEXT, 36, 820);
      const n = words.length; let lastX = 0, lastY = 0;
      words.forEach((wd, i) => {
        const at = lerp(5.0, 5.7, i / n), k = E.outCubic(seg(t, at, at + 0.12));
        if (k <= 0) return;
        const x = CX0 + 122 + wd.x, y = y2 + 128 + wd.line * 52;
        text(wd.wd, x, y + (1 - k) * 14, { size: 36, w: 400, align: 'left', color: '#eef1f7', alpha: k });
        lastX = x + wd.w; lastY = y;
      });
      if (lastX) { ctx.shadowColor = CYAN; ctx.shadowBlur = 16; ctx.fillStyle = CYAN; ctx.fillRect(lastX + 8, lastY - 18, 14, 36); ctx.shadowBlur = 0; }
    }
    ctx.restore();
  }
  ctx.restore();
  // retracting bars from the previous transition
  const cols = 10;
  for (let i = 0; i < cols; i++) {
    const k = 1 - E.inOutCubic(seg(t, 3.5 + i * 0.018, 3.72 + i * 0.018));
    if (k <= 0) continue;
    ctx.fillStyle = i % 3 === 1 ? CYAN : '#f4f6fb';
    ctx.fillRect(i * W / cols, 0, W / cols + 1, H * k);
  }
}

// ---------- SCENE 4 : 6.0 – 9.0  logo reveal ----------
function scene4(t) {
  background(t, '61,245,255', 0.06 + 0.08 * seg(t, 7.3, 7.6));
  ctx.save();
  const push = lerp(1, 1.14, E.inExpo(seg(t, 8.5, 9.0)));
  ctx.translate(W / 2, LOGO_Y); ctx.scale(push, push); ctx.translate(-W / 2, -LOGO_Y);
  // big ticked dial behind
  const dial = E.outExpo(seg(t, 6.1, 7.2));
  ctx.save(); ctx.translate(W / 2, LOGO_Y); ctx.rotate(t * 0.12);
  for (let i = 0; i < 180; i++) {
    if (i / 180 > dial) break;
    const a = (i / 180) * Math.PI * 2, long = i % 15 === 0;
    ctx.strokeStyle = `rgba(255,255,255,${long ? 0.35 : 0.13})`; ctx.lineWidth = long ? 2 : 1;
    ctx.beginPath(); ctx.moveTo(Math.cos(a) * 520, Math.sin(a) * 520); ctx.lineTo(Math.cos(a) * (long ? 560 : 540), Math.sin(a) * (long ? 560 : 540)); ctx.stroke();
  }
  ctx.restore();
  rings(t, 0.6 * dial, W / 2, LOGO_Y);
  // HUD rails
  const rail = E.outExpo(seg(t, 6.3, 7.1));
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  [LOGO_Y - 190, LOGO_Y + 170].forEach(y => {
    ctx.fillRect(W / 2 - 800 * rail, y, 1600 * rail, 1);
    for (let i = -16; i <= 16; i++) { const x = W / 2 + i * 50; if (Math.abs(i * 50) < 800 * rail) ctx.fillRect(x, y - (i % 4 ? 4 : 10), 1, i % 4 ? 8 : 20); }
  });
  // particles
  const lock = seg(t, 7.35, 7.55);
  const fade = 1 - seg(t, 7.4, 7.9);
  if (fade > 0) {
    ctx.save();
    for (const p of particles) {
      const k = seg(t, 6.0 + p.delay, 6.0 + p.delay + p.dur);
      const pos = kk => {
        const e = E.inOutCubic(kk); const ang = (1 - e) * 1.3;
        let x = lerp(p.sx, p.tx, e) - W / 2, y = lerp(p.sy, p.ty, e) - LOGO_Y;
        const c = Math.cos(ang), s = Math.sin(ang);
        return [x * c - y * s + W / 2, x * s + y * c + LOGO_Y];
      };
      let [x, y] = pos(k);
      const after = Math.max(0, t - 7.4); x += p.dx * after * 220; y += p.dy * after * 220;
      const a = clamp(k * 3) * fade;
      if (a <= 0) continue;
      if (k > 0 && k < 1) {
        const [px, py] = pos(Math.max(0, k - 0.06));
        ctx.strokeStyle = p.cyan ? `rgba(61,245,255,${a * 0.7})` : `rgba(255,255,255,${a * 0.5})`;
        ctx.lineWidth = p.sz * 0.7; ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(x, y); ctx.stroke();
      }
      ctx.fillStyle = p.cyan ? `rgba(61,245,255,${a})` : `rgba(255,255,255,${a})`;
      ctx.fillRect(x - p.sz / 2, y - p.sz / 2, p.sz, p.sz);
    }
    ctx.restore();
  }
  // solid logo
  const amt = t >= 7.4 ? 22 * Math.exp(-(t - 7.4) * 5) + 1.5 : 0;
  if (lock > 0) chroma('GROK BOT', W / 2, LOGO_Y, { size: 290, w: 900, ls: 4, alpha: E.outCubic(lock) }, amt);
  sweep(c => text('GROK BOT', W / 2, LOGO_Y, { size: 290, w: 900, ls: 4, c }), t, 7.6, 8.4, 'rgba(61,245,255,1)', 220);
  // shockwave
  const sk = seg(t, 7.4, 8.4);
  if (sk > 0 && sk < 1) {
    const e = E.outExpo(sk);
    ctx.strokeStyle = `rgba(255,255,255,${0.8 * (1 - sk)})`; ctx.lineWidth = 40 * (1 - sk) + 1;
    ctx.beginPath(); ctx.ellipse(W / 2, LOGO_Y, 60 + e * 1300, (60 + e * 1300) * 0.55, 0, 0, Math.PI * 2); ctx.stroke();
  }
  // corner brackets snap around the logo
  const br = E.outBack(seg(t, 7.4, 7.7));
  if (br > 0) {
    const bw = 780 + (1 - br) * 120, bh = 200 + (1 - br) * 60;
    ctx.strokeStyle = CYAN; ctx.lineWidth = 3; ctx.globalAlpha = clamp(br);
    [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(([sx, sy]) => {
      const x = W / 2 + sx * bw, y = LOGO_Y + sy * bh;
      ctx.beginPath(); ctx.moveTo(x - sx * 50, y); ctx.lineTo(x, y); ctx.lineTo(x, y - sy * 50); ctx.stroke();
    });
    ctx.globalAlpha = 1;
  }
  // subtitle with decode effect
  const sub = scramble('AI, SUMMONED INTO THE CONVERSATION', t, 7.7, 8.35, 42);
  text(sub, W / 2, LOGO_Y + 250, { size: 32, fam: 'JB', w: 500, ls: 12, color: '#c9d2e3' });
  const u = E.outExpo(seg(t, 8.2, 8.55));
  text('x.com/bot   ·   x.ai/bot', W / 2, LOGO_Y + 320 + (1 - u) * 20, { size: 26, fam: 'JB', w: 500, ls: 4, color: CYAN, alpha: u });
  ctx.restore();
}

// ---------- SCENE 5 : 9.0 – 11.5  rapid fire + tunnel ----------
function bigWord(t, t0, word, sub, idx, bg, fg, subColor) {
  const lt = t - t0;
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
  const sc = lerp(1.25, 1, E.outExpo(seg(lt, 0, 0.35))) + lt * 0.08;
  ctx.save(); ctx.translate(W / 2, H / 2 - 30); ctx.scale(sc, sc);
  if (typeof fg === 'object') {
    chroma(word, 0, 0, { size: 400, w: 900, ls: -14, color: fg.c }, 14 * Math.exp(-lt * 8) + 2);
  } else text(word, 0, 0, { size: 400, w: 900, ls: -14, color: fg });
  ctx.restore();
  const k = E.outExpo(seg(lt, 0.08, 0.3));
  text(sub, W / 2, H / 2 + 230 + (1 - k) * 20, { size: 30, fam: 'JB', w: 500, ls: 8, color: subColor, alpha: k });
  text(`0${idx} / 03`, 90, 120, { size: 22, fam: 'JB', w: 500, ls: 4, color: subColor, align: 'left' });
}
function scene5(t) {
  if (t < 9.5) bigWord(t, 9.0, 'ASK.', 'ANY QUESTION, RIGHT IN THE THREAD', 1, '#f4f6fb', '#050507', '#4a5160');
  else if (t < 10.0) bigWord(t, 9.5, 'TAG.', 'JUST MENTION @GROK', 2, '#050507', { c: CYAN }, '#8a93a6');
  else if (t < 10.5) {
    const g = ctx.createLinearGradient(0, 0, W, H); g.addColorStop(0, '#6e5bff'); g.addColorStop(1, '#00e0ff');
    bigWord(t, 10.0, 'KNOW.', 'ANSWERS WHERE YOU ALREADY ARE', 3, g, '#050507', 'rgba(5,5,7,0.7)');
  } else {
    const lt = t - 10.5;
    background(t, '110,91,255', 0.15);
    const travel = 0.5 * lt + 1.4 * lt * lt;
    const N = 28;
    const list = [];
    for (let i = 0; i < N; i++) { let z = 1 - (((i / N) + travel) % 1); list.push([z, i]); }
    list.sort((a, b) => b[0] - a[0]);
    ctx.save(); ctx.translate(W / 2, H / 2);
    for (const [z, i] of list) {
      const s = 140 / (z + 0.04);
      const a = clamp((1 - z) * 2) * clamp(z * 10);
      ctx.save(); ctx.rotate(z * 0.9 + lt * 0.6);
      ctx.strokeStyle = i % 3 === 0 ? `rgba(61,245,255,${a})` : i % 3 === 1 ? `rgba(110,91,255,${a})` : `rgba(255,255,255,${a * 0.8})`;
      ctx.lineWidth = Math.min(14, 1.5 / (z + 0.08));
      ctx.beginPath(); ctx.roundRect(-s, -s * 0.62, s * 2, s * 1.24, s * 0.12); ctx.stroke();
      ctx.restore();
    }
    // speed lines
    const r = rng(77 + Math.floor(t * 60));
    for (let i = 0; i < 40 * seg(t, 10.6, 11.4); i++) {
      const a = r() * Math.PI * 2, d = 300 + r() * 700, len = 100 + r() * 400;
      ctx.strokeStyle = `rgba(255,255,255,${0.15 + r() * 0.3})`; ctx.lineWidth = 1 + r() * 2;
      ctx.beginPath(); ctx.moveTo(Math.cos(a) * d, Math.sin(a) * d); ctx.lineTo(Math.cos(a) * (d + len), Math.sin(a) * (d + len)); ctx.stroke();
    }
    ctx.restore();
    const gs = lerp(0.9, 1.25, E.inCubic(seg(t, 10.5, 11.5)));
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(gs, gs);
    chroma('@grok', 0, 0, { size: 200, w: 900, ls: -4, alpha: E.outExpo(seg(t, 10.5, 10.7)) }, 6 + 20 * seg(t, 10.9, 11.5));
    ctx.restore();
    // white flare
    const fl = E.inExpo(seg(t, 11.25, 11.5));
    if (fl > 0) {
      const g = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, 1200 * fl + 1);
      g.addColorStop(0, `rgba(255,255,255,${fl})`); g.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    }
  }
}

// ---------- SCENE 6 : 11.5 – 15  Max Tracy ----------
function scene6(t) {
  ctx.fillStyle = '#070605'; ctx.fillRect(0, 0, W, H);
  const glow = ctx.createRadialGradient(W / 2, H * 0.62, 0, W / 2, H * 0.62, 1000);
  glow.addColorStop(0, `rgba(255,170,60,${0.16 + 0.04 * Math.sin(t * 3)})`); glow.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = glow; ctx.fillRect(0, 0, W, H);
  // embers
  const lt = t - 11.5;
  embers.forEach(e => {
    const damp = (1 - Math.exp(-lt * 3)) / 3;
    const x = e.x0 + e.vx * damp + Math.sin(t * 2 + e.ph) * 10;
    const y = e.y0 + e.vy * damp - e.rise * lt * 2;
    const a = (0.35 + 0.35 * Math.sin(t * 6 + e.ph)) * clamp(lt * 4);
    ctx.fillStyle = `rgba(255,190,110,${a})`; ctx.fillRect(x, y, e.sz, e.sz);
  });
  // question
  const q = 'WANT TO ACTUALLY PUT AI TO WORK?';
  const shown = typed(q, t, 11.6, 12.2);
  const qw = measure(q, 30, 'JB', 500, 6);
  text(shown, W / 2 - qw / 2, 285, { size: 30, fam: 'JB', w: 500, ls: 6, align: 'left', color: '#d8cfc1' });
  if (t < 12.4) caret(t, W / 2 - qw / 2 + measure(shown, 30, 'JB', 500, 6), 285, 34, AMBER);
  // label
  const lb = E.outExpo(seg(t, 12.3, 12.7));
  text('READ THE BLOG', W / 2, 375, { size: 22, fam: 'JB', w: 500, ls: 14, color: AMBER, alpha: lb });
  // name — letters rise out of a mask
  const NY = 520;
  const o = { size: 210, fam: 'SG', w: 700, ls: -4 };
  const L = letters('MAX TRACY', o.size, o.fam, o.w, o.ls);
  ctx.save(); ctx.beginPath(); ctx.rect(0, NY - 130, W, 250); ctx.clip();
  L.forEach((l, i) => {
    const k = E.outExpo(seg(t, 12.3 + i * 0.045, 12.3 + i * 0.045 + 0.7));
    if (k <= 0) return;
    text(l.ch, W / 2 + l.x, NY + (1 - k) * 240, { ...o, ls: 0, color: '#fbf7f0' });
  });
  ctx.restore();
  sweep(c => L.forEach(l => text(l.ch, W / 2 + l.x, NY, { ...o, ls: 0, c })), t, 13.0, 13.8, 'rgba(255,181,71,1)', 240);
  // underline
  const ul = E.outExpo(seg(t, 12.85, 13.4));
  if (ul > 0) {
    const g = ctx.createLinearGradient(W / 2 - 400, 0, W / 2 + 400, 0);
    g.addColorStop(0, 'rgba(255,181,71,0)'); g.addColorStop(0.5, AMBER); g.addColorStop(1, 'rgba(255,181,71,0)');
    ctx.fillStyle = g; ctx.fillRect(W / 2 - 400 * ul, 640, 800 * ul, 4);
  }
  // tagline words
  const tag = 'The most useful insights on applying AI'.split(' ');
  setFont(ctx, 44, 'IN', 500, 0);
  const sp = ctx.measureText(' ').width;
  const widths = tag.map(w => ctx.measureText(w).width);
  let x = W / 2 - (widths.reduce((a, b) => a + b, 0) + sp * (tag.length - 1)) / 2;
  tag.forEach((w, i) => {
    const k = E.outCubic(seg(t, 13.15 + i * 0.06, 13.5 + i * 0.06));
    text(w, x, 720 + (1 - k) * 24, { size: 44, w: 500, align: 'left', color: w === 'AI' ? AMBER : '#eee8de', alpha: k });
    x += widths[i] + sp;
  });
  // pills
  const pills = ['PERSONAL LIFE', 'WORK', 'BUSINESS'];
  setFont(ctx, 26, 'JB', 500, 6);
  const pw = pills.map(p => ctx.measureText(p).width + 64);
  const gap = 28; let px = W / 2 - (pw.reduce((a, b) => a + b, 0) + gap * 2) / 2;
  pills.forEach((p, i) => {
    const k = seg(t, 13.6 + i * 0.14, 14.0 + i * 0.14);
    if (k > 0) {
      const s = E.outBack(k);
      ctx.save(); ctx.translate(px + pw[i] / 2, 820); ctx.scale(s, s); ctx.globalAlpha = clamp(k * 3);
      ctx.fillStyle = 'rgba(255,181,71,0.09)'; ctx.strokeStyle = 'rgba(255,181,71,0.75)'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.roundRect(-pw[i] / 2, -32, pw[i], 64, 32); ctx.fill(); ctx.stroke();
      text(p, 0, 2, { size: 26, fam: 'JB', w: 500, ls: 6, color: '#ffd9a0' });
      ctx.restore();
    }
    px += pw[i] + gap;
  });
  const ft = E.outExpo(seg(t, 14.1, 14.5));
  text('FEATURING GROK BOT  ·  X.AI/BOT', W / 2, 990, { size: 18, fam: 'JB', w: 500, ls: 6, color: '#8c8273', alpha: ft });
}

// ---------- HUD / post ----------
function hud(t) {
  const a = 0.55 * seg(t, 0.15, 0.5) * (1 - seg(t, 11.3, 11.5));
  if (a <= 0) return;
  ctx.save(); ctx.globalCompositeOperation = 'difference'; ctx.globalAlpha = a;
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; const m = 48, l = 36;
  [[m, m, 1, 1], [W - m, m, -1, 1], [W - m, H - m, -1, -1], [m, H - m, 1, -1]].forEach(([x, y, sx, sy]) => {
    ctx.beginPath(); ctx.moveTo(x, y + sy * l); ctx.lineTo(x, y); ctx.lineTo(x + sx * l, y); ctx.stroke();
  });
  const scene = t < 1.5 ? 1 : t < 3.5 ? 2 : t < 6 ? 3 : t < 9 ? 4 : 5;
  const o = { size: 16, fam: 'JB', w: 500, ls: 4, color: '#fff', base: 'middle' };
  text('GROK BOT — MOTION REEL', m + 54, m + 4, { ...o, align: 'left' });
  text(`SC 0${scene} / 06`, W - m - 54, m + 4, { ...o, align: 'right' });
  const f = Math.floor(t * FPS), ss = Math.floor(f / FPS), ff = f % FPS;
  text(`TC 00:00:${String(ss).padStart(2, '0')}:${String(ff).padStart(2, '0')}`, W - m - 54, H - m - 4, { ...o, align: 'right' });
  text('1920×1080 · 60P', m + 54, H - m - 4, { ...o, align: 'left' });
  // rec dot
  if (Math.floor(t * 2) % 2 === 0) { ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(m + 18, H - m - 18, 6, 0, Math.PI * 2); ctx.fill(); }
  ctx.restore();
}
function glitch(t) {
  let g = -1;
  for (const gt of GLITCHES) if (t >= gt && t < gt + 0.1) g = gt;
  if (g < 0) return;
  const k = 1 - (t - g) / 0.1;
  bctx.clearRect(0, 0, W, H); bctx.drawImage(cv, 0, 0);
  const r = rng(Math.floor(t * FPS) * 13 + 1);
  for (let i = 0; i < 14; i++) {
    const y = r() * H, h = 6 + r() * 70, dx = (r() - 0.5) * 140 * k;
    ctx.drawImage(buf, 0, y, W, h, dx, y, W, h);
    if (r() < 0.3) { ctx.fillStyle = r() < 0.5 ? `rgba(61,245,255,${0.25 * k})` : `rgba(255,45,111,${0.25 * k})`; ctx.fillRect(0, y, W, h); }
  }
}
function post(t) {
  const fl = flashAmt(t);
  if (fl > 0.01) { ctx.fillStyle = `rgba(255,255,255,${fl * 0.6})`; ctx.fillRect(0, 0, W, H); }
  glitch(t);
  // vignette
  const v = ctx.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 1.05);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.55)');
  ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
  // grain
  ctx.save(); ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = 0.09;
  ctx.drawImage(grain[Math.floor(t * FPS) % grain.length], 0, 0, W, H); ctx.restore();
  ctx.save(); ctx.globalAlpha = 0.025; ctx.drawImage(grain[(Math.floor(t * FPS) + 3) % grain.length], 0, 0, W, H); ctx.restore();
  // scanline sheen
  ctx.fillStyle = 'rgba(0,0,0,0.06)';
  for (let y = 0; y < H; y += 4) ctx.fillRect(0, y, W, 1);
  // fade out
  const fo = seg(t, 14.72, 15.0);
  if (fo > 0) { ctx.fillStyle = `rgba(0,0,0,${fo})`; ctx.fillRect(0, 0, W, H); }
  // fade in
  const fi = 1 - seg(t, 0, 0.12);
  if (fi > 0) { ctx.fillStyle = `rgba(0,0,0,${fi})`; ctx.fillRect(0, 0, W, H); }
}

function renderFrame(t) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  ctx.save();
  const [sx, sy] = shake(t); ctx.translate(sx, sy);
  if (t < 1.5) scene1(t);
  else if (t < 3.5) scene2(t);
  else if (t < 6.0) scene3(t);
  else if (t < 9.0) scene4(t);
  else if (t < 11.5) scene5(t);
  else scene6(t);
  ctx.restore();
  hud(t);
  post(t);
}

window.ready = (async () => {
  await Promise.all([
    document.fonts.load('900 100px IN'), document.fonts.load('500 100px IN'), document.fonts.load('400 100px IN'),
    document.fonts.load('700 100px SG'), document.fonts.load('500 100px JB'),
  ]);
  buildGrain(); buildNodes(); buildLogoParticles(); buildEmbers();
  window.renderFrame = renderFrame;
  window.DUR = DUR; window.FPS = FPS;
  if (!/render/.test(location.search)) {
    const start = performance.now();
    const loop = () => { renderFrame(((performance.now() - start) / 1000) % DUR); requestAnimationFrame(loop); };
    loop();
  }
  return true;
})();
