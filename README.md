# etsy-pipeline

A pipeline that generates cat-themed poster art, writes Etsy listing copy via
the Claude API, composites the art into photographed room scenes, and
publishes the listing through the Etsy API.

## Pipeline

```
./generate ──► generate + mockup ──► ./publish ──► describe (if needed) ──► Etsy draft
              (artwork + room scene)                (AI copy)              (Etsy API)
```

| Stage | Module | Description |
|---|---|---|
| Generate | `pipeline/generate/` | Composes poster art from a fixed 143-color palette (`palette.py`), pairing colors by color-theory rules (`color_selector.py`) rather than arbitrary values. Each set is two cats — one light+warm, one dark+cool — and `generate_set()` also composites the mockups (`pipeline/mockup/mockup.py`) into the same folder. |
| Describe | `pipeline/describe/` | Calls the Claude API to generate a title, tags, and description. Runs automatically from `./publish` for anything missing `description.json`. |
| Publish | `pipeline/publish/` | Creates the listing as an Etsy draft via the Etsy API (OAuth2). Never publishes the same item twice. |

Each set is written to `products/set-N/`, with the generated images,
mockups, `description.json`, and (after publishing) `published.json`.

## Project structure

```
etsy-pipeline/
├── config.py                  — pricing, Etsy listing defaults
├── generate, reject, renumber, publish, help  — root-level commands, see Usage below
├── pipeline/
│   ├── products.py             — shared folder-discovery helpers
│   ├── generate/                — palette, color theory, image composition, cli.py/reject.py/renumber.py
│   ├── describe/                — Claude-generated listing copy
│   ├── mockup/                  — room-scene compositing + calibration
│   └── publish/                  — Etsy OAuth2 + listing creation, cli.py
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
- `DEFAULT_PRICE_USD`, `SET_PRICE_USD` — listing prices

One-time Etsy authorization:

```bash
python3 pipeline/publish/oauth.py
```

Opens a browser to authorize the app, writes the access/refresh tokens to
`.env`.

## Usage

Run from the project root.

| Command | Action |
|---|---|
| `./generate [N]` | Generate N sets (default 1) |
| `./reject <N>` | Move `set-N` to `products/rejected/` (reversible) |
| `./renumber` | Close gaps in `set-N` numbering after a reject |
| `./publish [N]` | Describe (if needed) + publish everything unpublished, or just `set-N`. Never publishes twice. |
| `./help` | List all commands |

See `CLAUDE.md` for implementation notes and current progress.
