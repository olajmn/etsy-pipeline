# Katteboten — CLAUDE.md

Project log and context for Claude Code. Update this file when something important is finished or changed.

---

## What is this project?

A Python pipeline that automatically generates and sells cat art posters on Etsy.

```
User                  Pipeline                    Etsy
  │                      │                          │
  └── run_all.py ──► generate → describe → mockup → publish
                     (images)  (AI text)  (room scene) (API)
```

Run from the project root: `python3 pipeline/run_all.py`

---

## Project Structure

```
etsy-bot/
├── config.py                  — pricing, Etsy settings, API keys
├── requirements.txt
├── pipeline/
│   ├── run_all.py             — main entry point: generate + describe + mockup + publish
│   ├── telegram_bot.py        — Telegram bot for controlling the pipeline from phone
│   ├── generate/
│   │   ├── palette.py         — Waals palette (143 named colors, HSL + CMYK)
│   │   ├── color_selector.py  — color theory and pair selection logic
│   │   ├── image_builder.py   — draws cat images (generate_collection, generate_set)
│   │   ├── color_card.py      — generates a color card image per pair
│   │   ├── form_builder.py    — helper shapes for image generation
│   │   └── run.py             — interactive menu (standalone)
│   ├── describe/
│   │   └── describe.py        — uses Claude AI to write Etsy titles and descriptions
│   ├── mockup/
│   │   ├── mockup.py          — places cat images into room scene PNG templates
│   │   ├── calibrate.py       — calibrates perspective frames in room scenes
│   │   └── calibration.json   — saved calibration points per template
│   └── publish/
│       ├── publish.py         — posts to Etsy via API
│       └── oauth.py           — Etsy OAuth2 flow
├── assets/
│   └── color-compositions/    — pre-generated color compositions (PNG)
└── products/
    └── collection-N/
        └── pair-A/            — one product pair: images + description.json + published.json
```

---

## Color System

- **Waals palette**: 143 colors named after Nobel Prize laureates (in `palette.py`)
- **Color Universe 02** (Forskningsrådet): backgrounds sampled at S=25% (muted tones)
- **Tonal/Noir system**: cat_1 = light+warm, cat_2 = dark+cool
- **Color theory**: complementary, analogous, triadic — controlled by `color_selector.py`
- Dynamic pools via `_waals_filter()` — no hardcoded anchor lists

**Product formats:**
- `layered_*.png` — portrait format, split background (60/40)
- `multi_portrett_*.png` — 3 cats in zigzag layout
- Collections: 3 pairs (pair-A/B/C) per `collection-N/`

---

## Pipeline Steps (in order)

| Step | File | What it does |
|------|------|--------------|
| 1. Generate | `image_builder.py` | Draws cat images with selected colors |
| 2. Describe | `describe.py` | Claude AI writes title, tags, description |
| 3. Color card | `color_card.py` | Creates a color card image per pair |
| 4. Mockup | `mockup.py` | Places images into room scene PNG templates |
| 5. Publish | `publish.py` | Posts as an Etsy listing via API |

---

## What's Done ✅

- [x] Core pipeline: generate → describe → mockup → publish
- [x] Waals palette with 143 colors
- [x] Tonal/Noir color pair system
- [x] Color theory system (complementary, analogous, triadic)
- [x] `generate_set()` — generates a complete set of all color combinations
- [x] Template tagging in the calibrator
- [x] Multi-frame mockup calibration (multiple frames per room scene)
- [x] Color cards (`color_card.py`)
- [x] Telegram bot for controlling the pipeline from phone
- [x] Etsy OAuth2 and publishing via API

---

## What's Left / Next Steps 🔜

*(Update this list as things get done or priorities change)*

- [ ] ?

---

## Important Rules / Things to Remember

- Color choices are governed by the Waals palette — don't use random hex codes
- Aesthetic rules (Color Universe 02) must be respected when suggesting new colors
- Always run from the project root: `python3 pipeline/run_all.py` (not from `pipeline/`)
- Etsy API keys and tokens live in `.env` (not in code)
