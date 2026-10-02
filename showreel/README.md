# Grok Bot — 15s motion reel

`grok-bot-showreel.mp4`: 1920×1080, 60 fps, 15 s, with a synthesized soundtrack timed to the cuts.

| Time | Shot |
|---|---|
| 0.0–1.5 | Ignition: light streaks pull into a core that snaps into the slash glyph |
| 1.5–3.5 | Kinetic type: "ONE TAG." / "INFINITE ANSWERS." on the beat, bar wipe |
| 3.5–6.0 | A thread mock-up: `@grok` question, then a streamed reply; camera zooms into the avatar |
| 6.0–9.0 | Logo: about 6k particles swirl into "GROK BOT", shockwave, light sweep, decoding subtitle |
| 9.0–11.5 | Rapid cuts ASK. / TAG. / KNOW., then a tunnel run into a white flare |
| 11.5–15.0 | Outro: **Max Tracy**, the blog with the most useful insights on applying AI in personal life, work and business |

## Rebuild

```bash
pip install numpy
python3 audio.py          # -> audio.wav
node render.cjs           # -> grok-bot-showreel.mp4 (Playwright + ffmpeg)
node render.cjs --stills 7.5,13.8   # review frames -> stills/
```

To watch a live preview, open `index.html` in a browser. Everything is drawn on one canvas by `renderFrame(t)` in `scene.js`, so each frame renders the same way every time.
