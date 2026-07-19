# etsy-pipeline — CLAUDE.md

Project log and context for Claude Code. Update this file when something important is finished or changed.

---

## What is this project?

A Python pipeline that automatically generates and sells cat art posters on Etsy.

```
User                  Pipeline                          Etsy
  │                      │                                │
  └── ./generate ──► generate → (describe → mockup) ──► ./publish → draft listing
                     (images)   (AI text)  (room scene)   (Etsy API)
```

Run from the project root. Five commands, see `./help`:

| Command | What it does |
|---|---|
| `./generate [N]` | Generate N sets (default 1) — no menu, no prompts |
| `./reject <N>` | Move `set-N` to `products/rejected/` (reversible) |
| `./renumber` | Close gaps in `set-N` numbering after a reject |
| `./publish [N]` | Auto-describe (Claude) + publish everything unpublished, or just `set-N`. Never publishes twice. |
| `./help` | List all commands |

`pipeline/generate/run.py` still exists as an interactive menu for the experimental modes (Collection, Pattern, etc.) — but day-to-day production goes through the commands above.

---

## Project Structure

```
etsy-bot/
├── config.py                  — pricing, Etsy settings, API keys
├── requirements.txt
├── generate, reject, renumber, publish, help  — root-level command scripts (bash wrappers)
├── pipeline/
│   ├── products.py            — shared find_pair_folders()/find_set_dirs() (used by describe.py + publish.py)
│   ├── generate/
│   │   ├── palette.py         — Waals palette (143 named colors, HSL + CMYK)
│   │   ├── color_selector.py  — color theory and pair selection logic
│   │   ├── image_builder.py   — draws cat images (generate_collection, generate_set, find_set_pairs, renumber_sets)
│   │   ├── color_card.py      — generates a color card image per pair
│   │   ├── form_builder.py    — helper shapes for image generation
│   │   ├── run.py             — interactive menu (standalone, experimental modes)
│   │   ├── cli.py             — non-interactive set generator, backs ./generate
│   │   ├── reject.py          — backs ./reject
│   │   └── renumber.py        — backs ./renumber
│   ├── describe/
│   │   └── describe.py        — uses Claude AI to write Etsy titles and descriptions
│   ├── mockup/
│   │   ├── mockup.py          — places cat images into room scene PNG templates
│   │   ├── calibrate.py       — calibrates perspective frames in room scenes, has a "deactivate template" endpoint
│   │   └── calibration.json   — saved calibration points per template
│   └── publish/
│       ├── publish.py         — posts to Etsy via API
│       ├── cli.py             — describe (if needed) + publish in one step, backs ./publish
│       └── oauth.py           — Etsy OAuth2 flow
├── assets/
│   ├── color-compositions/    — pre-generated color compositions (PNG)
│   └── mockup-templates/      — room-scene templates; mockuptemplates_calibrated/deactivated/ holds disabled ones
└── products/
    ├── set-N/                 — current production path: 2 cats flat per set + description.json + published.json
    ├── rejected/set-N/        — sets moved aside via ./reject, excluded from production
    └── collection-N/pair-A/   — old per-pair structure, code path still exists but unused in practice
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

## What's Done

- [x] Core pipeline: generate → describe → mockup → publish
- [x] Waals palette with 143 colors
- [x] Tonal/Noir color pair system
- [x] Color theory system (complementary, analogous, triadic)
- [x] `generate_set()` — generates a complete set of all color combinations
- [x] Template tagging in the calibrator
- [x] Multi-frame mockup calibration (multiple frames per room scene)
- [x] Color cards (`color_card.py`)
- [x] Etsy OAuth2 and publishing via API
- [x] `generate_set()` output (`products/set-N/`, 2 cats flat per set) connected to `describe.py` and `publish.py` via `find_set_pairs()` in `image_builder.py` — each set-N becomes ONE combined Etsy draft listing (both cats named individually, e.g. "Yuki & Damson", `SET_PRICE_USD` from config.py), 4 print files as digital downloads + all mockups as listing photos, no Printify
- [x] Fixed `image_builder.py`'s bare `from form_builder import ...` so it can be imported as `pipeline.generate.image_builder`
- [x] 2026-07-19: Non-interactive command layer built — `./generate [N]`, `./reject <N>`, `./renumber`, `./publish [N]`, `./help` (root-level bash wrappers over `pipeline/generate/cli.py`, `reject.py`, `renumber.py`, `pipeline/publish/cli.py`). `./publish` auto-runs describe for anything missing `description.json`, then publishes anything missing `published.json` — never publishes twice.
- [x] `renumber_sets()` in `image_builder.py` closes gaps in `set-N` numbering (safe on already-published sets — `published.json` stores the Etsy `listing_id`/URL, not the folder name)
- [x] Deduplicated `_find_pair_folders()`/`_find_set_dirs()` (previously copy-pasted in both `describe.py` and `publish.py`) into `pipeline/products.py`, shared by both plus `pipeline/publish/cli.py`
- [x] Deleted `pipeline/run_all.py` (old, never-actually-used `collection-N/pair-X` entry point) and `pipeline/telegram_bot.py` (was wired to `run_all.py`, out of sync with the `set-N` flow) — user's call, 2026-07-19. No code depended on either beyond each other.
- [x] Mockup template deactivation via the existing `calibrate.py` mechanism (`active: false` in `all_segments.json` + move calibrated PNG to `mockuptemplates_calibrated/deactivated/`) — templates 0086 and 0107 deactivated 2026-07-19

---

## What's Left / Next Steps

*(Update this list as things get done or priorities change)*

- [ ] `PRINTIFY_API_TOKEN` in `.env` is expired/invalid (confirmed via `/v1/shops.json` → "Unauthenticated") — regenerate in Printify → My Account → Connections if the physical-poster (POD) path is needed later. Not required for the digital-download path.
- [ ] `products/collection-N/pair-X` (the structure `generate_collection()` expects) has never actually been produced — current production path is `set-N` via `./generate`. `generate_collection()` and the pair-based code paths in `describe.py`/`publish.py` still exist but are unused; leaving them for now since they're not causing duplication/confusion, unlike the deleted `run_all.py`.
- [ ] No Telegram (or other remote) control surface anymore — `./generate`/`./publish` etc. are terminal-only, run on the Mac. Revisit if remote control is wanted again; build it against `pipeline/generate/cli.py`'s `generate()` and `pipeline/publish/cli.py`'s `run()`, which already return structured results for exactly that purpose.

---

## Important Rules / Things to Remember

- Color choices are governed by the Waals palette — don't use random hex codes
- Aesthetic rules (Color Universe 02) must be respected when suggesting new colors
- Always run from the project root: `./generate`, `./publish`, etc. (not from `pipeline/`)
- Etsy API keys and tokens live in `.env` (not in code)
