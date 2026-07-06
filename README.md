# Katteboten 🐱

An automated pipeline that generates original cat-themed art, writes Etsy-ready
listing copy with Claude, renders it into realistic room mockups, and publishes
it to Etsy — all from a single command (or a Telegram bot).

```
run_all.py ──► generate ──► describe ──► mockup ──► publish
              (artwork)   (AI copy)   (room scene)  (Etsy API)
```

## Features

- **Generative art** — procedurally composed cat posters using a curated
  143-color palette (`palette.py`), driven by color theory (complementary,
  analogous, triadic pairings) rather than random hex codes.
- **AI-written listings** — Claude generates unique titles, tags, and
  descriptions for every product.
- **Room mockups** — artwork is warped into real photographed room scenes via
  calibrated perspective frames, so listings show the poster in context.
- **Etsy publishing** — listings are created as drafts directly via the Etsy
  API (OAuth2).
- **Telegram control** — trigger generation and publishing from your phone.

## Project structure

```
etsy-bot/
├── config.py                  — pricing, Etsy listing defaults
├── pipeline/
│   ├── run_all.py             — main entry point: generate + describe + mockup + publish
│   ├── telegram_bot.py        — Telegram bot for controlling the pipeline
│   ├── generate/               — artwork generation (palette, color theory, image builder)
│   ├── describe/                — Claude-written titles/descriptions
│   ├── mockup/                  — places artwork into room-scene templates
│   └── publish/                  — Etsy OAuth2 + publishing
├── assets/
│   └── mockup-templates/       — room-scene templates + calibration data
└── products/                   — generated collections (gitignored)
```

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   ```bash
   cp .env.template .env
   ```

   Fill in:

   | Variable | Purpose |
   |---|---|
   | `ANTHROPIC_API_KEY` | Claude API access, for listing copy |
   | `OPENAI_API_KEY` | (if used by the pipeline) |
   | `ETSY_CLIENT_ID`, `ETSY_SHARED_SECRET` | Etsy app credentials |
   | `ETSY_SHOP_ID`, `ETSY_USER_ID` | Your Etsy shop |
   | `ETSY_ACCESS_TOKEN` | Filled in automatically by the OAuth step below |
   | `DEFAULT_PRICE_USD` | Default listing price |

3. **Authorize with Etsy (one-time)**

   ```bash
   python3 pipeline/publish/oauth.py
   ```

   Opens a browser to authorize the app and saves the access/refresh tokens
   into `.env`.

## Usage

Always run from the project root.

```bash
python3 pipeline/run_all.py            # generate + describe 1 collection
python3 pipeline/run_all.py 3          # generate + describe 3 collections
python3 pipeline/run_all.py publish    # publish all unpublished pairs to Etsy
```

### Telegram bot

```bash
python3 pipeline/telegram_bot.py
```

Requires `TELEGRAM_BOT_TOKEN` and `TELEGRAM_OWNER_ID` in `.env`. Commands:

| Command | Action |
|---|---|
| `/generate` | Generate + describe 1 collection |
| `/generate 3` | Generate N collections |
| `/publish` | Publish all unpublished pairs |
| `/status` | Show published/total counts |

## Color system

Colors are drawn from the **Waals palette** — 143 named colors (after Nobel
laureates) defined in `pipeline/generate/palette.py`. Pairings follow a
tonal/noir system (one light+warm cat, one dark+cool cat) and are selected
using color theory rules in `color_selector.py`, rather than arbitrary hex
values.

## Status

Personal project, actively developed. See `CLAUDE.md` for detailed pipeline
notes and progress log.
