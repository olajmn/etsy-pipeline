# etsy-pipeline

A pipeline that generates cat-themed poster art, writes Etsy listing copy via
the Claude API, composites the art into photographed room scenes, and
publishes the listing through the Etsy API.

## Pipeline

```
run_all.py ──► generate ──► describe ──► mockup ──► publish
              (artwork)   (AI copy)   (room scene)  (Etsy API)
```

| Stage | Module | Description |
|---|---|---|
| Generate | `pipeline/generate/` | Composes poster art from a fixed 143-color palette (`palette.py`), pairing colors by color-theory rules (`color_selector.py`) rather than arbitrary values. Each product is a tonal/noir pair — one light+warm cat, one dark+cool cat. |
| Describe | `pipeline/describe/` | Calls the Claude API to generate a title, tags, and description per product. |
| Mockup | `pipeline/mockup/` | Warps the generated art into calibrated perspective frames over photographed room templates (`assets/mockup-templates/`). |
| Publish | `pipeline/publish/` | Creates the listing as an Etsy draft via the Etsy API (OAuth2). |

Each collection is written to `products/collection-N/pair-X/`, with the
generated images, `description.json`, and (after publishing)
`published.json`.

## Project structure

```
etsy-pipeline/
├── config.py                  — pricing, Etsy listing defaults
├── pipeline/
│   ├── run_all.py             — entry point: generate + describe + mockup + publish
│   ├── telegram_bot.py        — Telegram interface for the same commands
│   ├── generate/               — palette, color theory, image composition
│   ├── describe/                — Claude-generated listing copy
│   ├── mockup/                  — room-scene compositing + calibration
│   └── publish/                  — Etsy OAuth2 + listing creation
├── assets/
│   └── mockup-templates/       — room-scene templates + calibration data (not tracked in git)
└── products/                   — generated output (not tracked in git)
```

## Setup

```bash
pip install -r requirements.txt
cp .env.template .env
```

`.env` needs:

- `ANTHROPIC_API_KEY` — Claude API, used by `describe/`
- `ETSY_CLIENT_ID`, `ETSY_SHARED_SECRET`, `ETSY_SHOP_ID`, `ETSY_USER_ID` — Etsy app credentials
- `ETSY_ACCESS_TOKEN` — populated by the OAuth step below, not set manually
- `DEFAULT_PRICE_USD` — listing price
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_OWNER_ID` — only needed for `telegram_bot.py`

One-time Etsy authorization:

```bash
python3 pipeline/publish/oauth.py
```

Opens a browser to authorize the app, writes the access/refresh tokens to
`.env`.

## Usage

Run from the project root.

```bash
python3 pipeline/run_all.py            # generate + describe 1 collection
python3 pipeline/run_all.py 3          # generate + describe 3 collections
python3 pipeline/run_all.py publish    # publish all unpublished pairs
```

or via Telegram:

```bash
python3 pipeline/telegram_bot.py
```

| Command | Action |
|---|---|
| `/generate [n]` | Generate + describe n collections (default 1) |
| `/publish` | Publish all unpublished pairs |
| `/status` | Show published/total counts |

See `CLAUDE.md` for implementation notes and current progress.
