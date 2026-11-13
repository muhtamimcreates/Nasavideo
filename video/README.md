# Abandoned, But Not Forgotten — pitch video

Pitch video (about 4:04, 1920×1080, 30 fps) with an AI voiceover, a synthesized ambient score,
burned-in Space Grotesk captions, and real screen recordings of the website
(abandonedbutnotforgotten.netlify.app).

The look follows the website's own design tokens: void `#020307`, cobalt `#3d7bff`, signal `#6f9dff`,
silent `#7e8fb8`, body `#a7b3cf`, and uppercase two-tone titles with a periwinkle-to-white gradient
(`#86a3e8 → #b9cbf2 → #f5f7ff`). Moon, Mars and Earth use the site's textures with its blue duotone grade.

| Section | Time | Visuals |
|---|---|---|
| WHO | 0:00–0:46 | "SIGNAL: NONE", Voyager-style probe and distance counter, silent Mars rover, split screen, team, question, title |
| WHY | 0:46–1:47 | Moon / Mars / deep space, scattered tabs and PDFs, "ABANDONED" crossed out, Dust / Cold / Power / Distance, Opportunity 90 sols → 14+ years, 2018 dust storm with 1,000+ commands, "why it ended" |
| WHAT | 1:47–2:55 | Website recordings: Home, story scroll, Timeline → Hardware Map, Final Signal, Inspect 3D, Mission Detective, Compare / Quiz / 3D Game / Explore; then sources and fact vs. creative interpretation |
| SO WHAT NEXT | 2:55–4:04 | About and NASA Data recordings, dates → stories, works offline, three asks, Voyager vs. Opportunity, end card |

## Files

- `script.json` — the voiceover lines and the scene each one plays over
- `timeline.json` — when each line and caption chunk plays (made by `build_timeline.py`)
- `scenes.html` + `render.js` — the animated scenes, drawn on a canvas and rendered frame by frame
- `record_site.js` — records the website pages frame by frame (it freezes the page clock and steps it
  1/30 s per screenshot, so the 3D pages stay smooth even with software WebGL)
- `compose.py` — mixes the voice and score, drops the website recordings into the browser frame, burns the captions
- `captions.srt` — the captions as a separate file, for YouTube and similar sites
- `site_slots.json` — the time slots and on-screen frame for the website recordings
- `fonts/` — Space Grotesk (SIL Open Font License); `tex/` — planet textures from the website (Solar System Scope, CC BY 4.0)

## Rebuilding

```
pip install kokoro-onnx soundfile        # TTS (needs kokoro-v1.0.onnx + voices-v1.0.bin from the kokoro-onnx releases)
python3 gen.py am_michael vo             # one wav per script line
python3 build_timeline.py vo
node render.js base.mp4 30               # Playwright + Chromium
# serve the website locally (e.g. python3 -m http.server 8765 in the site folder), then:
THREE_DIR=<three@0.128.0 package dir> node record_site.js http://localhost:8765/index.html captures
python3 compose.py base.mp4 vo final.mp4 captures
```

## Placeholders to fill in

- The team line is spoken as "We're a team from Bangladesh." Re-record line 04 as
  "I'm [Name], and this is Team [Team Name] from [City], Bangladesh." once the names are final.
- The end card shows `TEAM [TEAM NAME] · [CITY], BANGLADESH`. Edit `S.end` in `scenes.html`.
