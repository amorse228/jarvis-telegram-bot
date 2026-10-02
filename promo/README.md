# «Чистая Тема» — 15-second motion promo

`chistaya_temka_promo.mp4` is a 1080×1920 (9:16), 60 fps, 15.0 s promo for [@chistaya_temka_bot](https://t.me/chistaya_temka_bot) with a synthesized soundtrack.

Everything is generated from code. There's no stock footage and no audio samples.

| Time | Scene |
|---|---|
| 0.00–1.88 | Intro: the logo pops, the «ЧИСТАЯ ТЕМА» lettering slams in, and the logo flies into the phone as the chat avatar |
| 1.88–10.31 | Six features, 3 beats each: reminders, calculator (odometer), password (scramble), coin flip, 3D dice, choice roulette |
| 10.31–12.66 | Channel: «Чистая Тема», AI and smart tools for life, work and business, t.me/chistaya_temka_bot |
| 12.66–15.00 | Outro: @chistaya_temka_bot, the «Запусти бота — /start» button and a cursor tap |

The whole edit sits on a 128 BPM grid (32 beats = 15 s). Visuals and audio share one event timeline.

## Rebuild

```bash
# 1. frames (120 fps, headless Chromium via Playwright)
node tools/render.js 120 build/raw120.mp4        # also writes build/sfx.json
# 2. soundtrack from the same timeline (needs numpy + scipy)
python3 tools/synth.py build/sfx.json build/audio.wav
# 3. 120 -> 60 fps with 2-frame motion blur, mux audio
ffmpeg -i build/raw120.mp4 -i build/audio.wav \
  -vf "tmix=frames=2,fps=60,format=yuv420p" -c:v libx264 -preset slow -crf 16 \
  -profile:v high -movflags +faststart -c:a aac -b:a 256k -shortest chistaya_temka_promo.mp4
```

- Live preview: open `index.html?play` in a browser.
- Single frame: open `index.html?t=7.9`, or run `node tools/snap.js <dir> 7.9 12.5`.
