# Abandoned, But Not Forgotten — pitch video

Documentary-style pitch video (4:00.5, 1920×1080, 30 fps) cut from public-domain NASA stock footage and stills
(NASA Image and Video Library), short screen recordings of the live website
(abandonedbutnotforgottenchallenge.netlify.app), an AI voiceover, a synthesized space score and word-by-word
highlighted captions. All type is Space Grotesk at -1px tracking; colours are the website's tokens
(void `#05070d`, panel `#0d1220`, Mars orange `#cf6a34`/`#e8925a`, blue `#6fa2f2`, white `#f2f4f9`, muted `#8b93a8`).
Voiceover lines with exact times: `voiceover_timestamps.md`.

| Section | Time | Visuals |
|---|---|---|
| WHO | 0:00–0:50 | "Signal: none" on black, Voyager (artist concept) + 24 billion km, JPL team receiving Voyager data (2024), Opportunity (artist concept) "Signal: none", split screen, South Asia at night (team), Moon flyover (question), Earth limb + title |
| WHY | 0:50–1:47 | Saturn V, Apollo 11, Opportunity's Cabo Frio pan, Voyager; browser tabs opening one by one; "Abandoned"; Apollo mission control; Dust / Cold / Fading power / Distance; 90 sols → 14+ years; 2018 dust storm (Mars before/after, dimming Sun); Goldstone + 1,000+ commands; Opportunity's last message ("No response"); traverse map; "10 tabs?" |
| WHAT | 1:47–2:51 | Live-site recordings in a browser frame: Home, Home scroll, Timeline → Hardware Map, Final Signal (Opportunity), Inspect 3D, Mission Detective, Compare/Quiz/Game/Explore; sources + "creative interpretation" label |
| SO WHAT NEXT | 2:51–4:00 | About, dates → stories, HTML/CSS/JS + offline, NASA Data, three asks (01/02/03), Voyager vs. Opportunity, end card |

## Files

- `script.json` — voiceover lines and the scene each one plays over
- `timeline.json` — when each line plays (made by `build_timeline.py`); `words.json` — word timings (`align.py`)
- `edit.py` — the shot list and edit: NASA clips/stills with slow push-ins, grade and caption scrim, text overlays,
  website recordings in a browser frame; renders each shot, then concatenates
- `overlays.js` — renders the text overlays (Space Grotesk, -1px tracking) to transparent PNGs
- `record_site.js` — records the live website frame by frame (virtual page clock, 1/30 s per screenshot)
- `music.py` — slow synthesized space score; `compose.py` — mixes voice + score (ducked, -16 LUFS), adds grain, burns captions
- `captions.srt` — captions for YouTube and similar sites; `voiceover_timestamps.md` — the script with times
- `film.html`, `render.js`, `scenes.html` — the earlier 3D-model and 2D versions

## Stock footage and stills (NASA Image and Video Library, public domain)

Video: Voyager 1 Team Reacts to Receiving Engineering Data (JPL, 2024); Ultimate Saturn V Launch; Apollo Mission Control
B-roll (jsc2019m000563); Earth from Space in 4K – Expedition 65; Lee Lincoln Scarp Moon Flyover (GSFC); Lights of Human
Activity – Earth at Night (GSFC); The Flight of Apollo 11 (HQ-194). Stills: PIA04495, PIA17049, PIA14111 (Voyager);
PIA04413, PIA04239, PIA04240 (MER artist concepts); PIA01292 (Cabo Frio); PIA22519, PIA22487, PIA22521 (2018 storm);
PIA07108 (frost); PIA23645 (Pale Blue Dot Revisited); PIA23214 (Goldstone); PIA22929 (Opportunity's last message);
PIA23178 (traverse map). NASA content is not copyrighted; NASA's logo and insignia are not used as branding.

## Rebuilding

```
pip install kokoro-onnx soundfile scipy pillow pocketsphinx   # kokoro-v1.0.onnx + voices-v1.0.bin (huggingface.co/fastrtc/kokoro-onnx) as kokoro.onnx / voices.bin
VO_SPEED=1.0 python3 gen.py am_michael vo      # one wav per script line (the "Dust./Cold./…" lines were made at speed 0.9)
python3 build_timeline.py vo && python3 align.py vo
# stock: download the items above into stock/ as <name>.mp4 / <name>.jpg (names are in edit.py)
node record_site.js https://abandonedbutnotforgottenchallenge.netlify.app captures
python3 edit.py work work/edit.mp4
python3 compose.py work/edit.mp4 vo final.mp4 none
```

## Team

Team Cosmic Eclipse, Sylhet, Bangladesh: Maliha (team leader), Nuhza (designer), Fatema (data scientist), Omi (developer),
Montaha (researcher), Md Mahiyan Noor Mahi (storyteller, narrator line). "Md" is voiced as "Mohammad" (`say` in `script.json`).
