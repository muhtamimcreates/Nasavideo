# Abandoned, But Not Forgotten — pitch video

Pitch video (about 4:04, 1920×1080, 30 fps) with an AI voiceover, a synthesized ambient score
and burned-in captions set in **Space Grotesk**.

| Section | Time | Visuals |
|---|---|---|
| WHO | 0:00–0:46 | "SIGNAL: NONE", Voyager-style probe and distance counter, silent Mars rover, split screen, team, question, title |
| WHY | 0:46–1:47 | Moon / Mars / deep space, scattered tabs and PDFs, "ABANDONED" crossed out, Dust / Cold / Power / Distance, Opportunity 90 sols → 14+ years, 2018 dust storm with 1,000+ commands, "why it ended" |
| WHAT | 1:47–2:55 | **Website capture slots** (Home, scroll, Timeline/Map, Final Signal, 3D, Detective, Compare/Quiz/Game), sources, fact vs. creative interpretation |
| SO WHAT NEXT | 2:55–4:04 | About / NASA Data slots, dates → stories, works offline, three asks, Voyager vs. Opportunity, end card |

## Files

- `script.json` — the voiceover lines and the scene each one plays over
- `timeline.json` — when each line and caption chunk plays (made by `build_timeline.py`)
- `scenes.html` — every scene, drawn on a canvas; `render.js` renders it frame by frame
- `compose.py` — mixes the voice and score, drops in website captures, burns the captions
- `captions.srt` — the captions as a separate file, for YouTube and similar sites
- `site_slots.json` — the time slots for the website captures
- `fonts/` — Space Grotesk (SIL Open Font License)

## Adding the website recordings

Each website scene is a browser-frame placeholder for now. Record the site at 16:9 and save the clips as:

```
captures/home.mp4                               107.0–116.8 s
captures/home-scroll.mp4                        116.8–124.6 s
captures/timeline-hardware-map.mp4              124.6–130.8 s
captures/final-signal.mp4                       130.8–144.2 s
captures/inspect-3d.mp4                         144.2–148.1 s
captures/mission-detective.mp4                  148.1–156.8 s
captures/compare-quiz-3d-game-explore-mars.mp4  156.8–161.5 s
captures/about.mp4                              175.3–177.5 s
captures/nasa-data.mp4                          201.0–208.9 s
```

Then run `python3 compose.py base.mp4 <vo_dir> final.mp4`. Each clip is cropped to fill the browser
frame and looped if it is shorter than its slot.

## Rebuilding from scratch

```
pip install kokoro-onnx soundfile          # TTS (needs kokoro-v1.0.onnx + voices-v1.0.bin)
python3 gen.py am_michael vo               # one wav per script line
python3 build_timeline.py vo
node render.js base.mp4 30                 # needs Playwright + Chromium
python3 compose.py base.mp4 vo final.mp4
```

## Placeholders to fill in

- The team line is spoken as "We're a team from Bangladesh." Re-record line 04 as
  "I'm [Name], and this is Team [Team Name] from [City], Bangladesh." once the names are final.
- The end card shows `[ SITE URL ]` and `TEAM [TEAM NAME] · [CITY], BANGLADESH`. Edit `S.end` in `scenes.html`.
