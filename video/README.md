# Abandoned, But Not Forgotten — pitch video

Documentary-style pitch video (about 4:04, 1920×1080, 30 fps): cinematic 3D shots built from real NASA
3D Resources models (Voyager, Opportunity, Viking, Apollo LM, Pioneer, InSight, DSN dish) and photographic
planet textures, an AI voiceover, a synthesized slow space score, word-by-word highlighted captions,
and short screen recordings of the website (abandonedbutnotforgotten.netlify.app).

Type follows the website's scale ×1.4 for video (hero 88→124, h2 84→118, scene titles 56→78, stats 80→112,
lead 20→28, labels 13→19) in Space Grotesk 300/400/500/600. The look follows the website's own design tokens: void `#020307`, cobalt `#3d7bff`, signal `#6f9dff`,
silent `#7e8fb8`, body `#a7b3cf`, and uppercase two-tone titles with a periwinkle-to-white gradient
(`#86a3e8 → #b9cbf2 → #f5f7ff`). Moon, Mars and Earth use the site's textures with its blue duotone grade.

| Section | Time | Visuals |
|---|---|---|
| WHO | 0:00–0:46 | "Signal: none", Voyager in deep space with distance counter, Opportunity silent on Mars, split screen, Earth at night over Bangladesh, Moon surface, title over Earth's limb |
| WHY | 0:46–1:47 | Apollo LM on the Moon, Viking, Pioneer; Earth; "Abandoned" struck through; Dust / Cold / Fading power (InSight) / Distance; Opportunity driving (90 sols → 14+ years); the 2018 dust storm; DSN dish sending 1,000+ commands |
| WHAT | 1:47–2:55 | Short website recordings (Home, story, Timeline → Map, Final Signal, Inspect 3D, Mission Detective, Compare / Quiz / Game / Explore) over a slow Earth; sources; fact vs. creative interpretation |
| SO WHAT NEXT | 2:55–4:04 | About and NASA Data recordings, dates → stories, works offline (Earth at night), three asks (Moon), Voyager vs. Opportunity, end card |

## Files

- `script.json` — the voiceover lines and the scene each one plays over
- `timeline.json` — when each line and caption chunk plays (made by `build_timeline.py`)
- `film.html` + `render.js` — the 3D documentary shots and typography, rendered frame by frame
  (`scenes.html` is the earlier 2D version)
- `align.py` — forced alignment (pocketsphinx) that gives every spoken word its start/end time → `words.json`
- `music.py` — the slow cinematic space score (pads, sub drone, sparse bells, long reverb)
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
python3 align.py vo                      # word timings for the highlight captions
# serve this folder with ./assets -> the website files and ./three -> three@0.128.0, then:
PAGE_URL=http://localhost:8766/film.html node render.js base.mp4 30
# serve the website locally (e.g. python3 -m http.server 8765 in the site folder), then:
THREE_DIR=<three@0.128.0 package dir> node record_site.js http://localhost:8765/index.html captures
python3 compose.py base.mp4 vo final.mp4 captures
```

## Placeholders to fill in

- The team line is spoken as "We're a team from Bangladesh." Re-record line 04 as
  "I'm [Name], and this is Team [Team Name] from [City], Bangladesh." once the names are final.
- The end card shows `TEAM [TEAM NAME] · [CITY], BANGLADESH`. Edit `S.end` in `scenes.html`.
