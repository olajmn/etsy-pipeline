"""
pipeline/generate/color_card.py — Generate color palette card for each pair.

Parses the layered_*.png filename to extract color names, looks up RGB values
from the palette, converts to CMYK, and produces:
  - colors.json  (machine-readable: hex, RGB, CMYK per color)
  - color_card.png (visual swatch card for Etsy listing)

Run from project root:
    python3 pipeline/generate/color_card.py products/collection-9/pair-A
    python3 pipeline/generate/color_card.py          # all pairs
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

PRODUCTS_DIR = Path("products")

# ── Palette (mirrored from color_generator.py) ────────────────────────────

CAT_COLORS = {
    "black":   (30,  30,  35),
    "ginger":  (210, 110, 55),
    "rust":    (175, 75,  60),
    "cream":   (235, 220, 195),
    "slate":   (95,  115, 135),
    "sage":    (120, 148, 112),
    "blush":   (195, 140, 130),
    "caramel": (195, 145, 80),
}

BG_COLORS = {
    "dusty_blue":  (165, 195, 215),
    "warm_cream":  (245, 238, 218),
    "soft_sage":   (195, 212, 182),
    "blush":       (238, 208, 200),
    "pale_yellow": (248, 238, 185),
    "stone":       (220, 215, 202),
    "terracotta":  (205, 130, 98),
    "forest":      (98,  138, 108),
    "lavender":    (195, 185, 220),
    "navy":        (58,  75,  102),
}

EYE_COLORS = {
    "lime":         (180, 210, 80),
    "bright_green": (80,  190, 100),
    "sky_blue":     (80,  170, 225),
    "ice_blue":     (160, 210, 235),
    "coral":        (235, 110, 90),
    "white":        (240, 238, 230),
    "bright_gold":  (240, 200, 50),
}

ALL_COLORS = {**CAT_COLORS, **BG_COLORS, **EYE_COLORS}


# ── Color math ─────────────────────────────────────────────────────────────

def rgb_to_hex(r, g, b) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"

def rgb_to_cmyk(r, g, b) -> tuple[int, int, int, int]:
    r, g, b = r / 255, g / 255, b / 255
    k = 1 - max(r, g, b)
    if k == 1:
        return 0, 0, 0, 100
    c = (1 - r - k) / (1 - k)
    m = (1 - g - k) / (1 - k)
    y = (1 - b - k) / (1 - k)
    return round(c * 100), round(m * 100), round(y * 100), round(k * 100)

def is_dark(r, g, b) -> bool:
    return (0.299*r + 0.587*g + 0.114*b) < 128


# ── Filename parsing ────────────────────────────────────────────────────────

def parse_colors_from_filename(png_path: Path) -> list[dict] | None:
    """Extract color info from a layered_*.png or multi_*.png filename."""
    name = png_path.stem

    # layered_{cat}_{eye}eyes_{bg1}_{bg2}_{hash}
    # Cat name is always one word (no underscores); eye/bg names can have them.
    m = re.match(
        r"layered_([a-z]+)_([a-z_]+)eyes_([a-z_]+)_([a-z_]+)_[a-f0-9]+$", name
    )
    if m:
        cat_name, eye_name, bg1_name, bg2_name = m.groups()
        entries = [
            ("Cat",          cat_name, CAT_COLORS.get(cat_name)),
            ("Eyes",         eye_name, EYE_COLORS.get(eye_name)),
            ("Background 1", bg1_name, BG_COLORS.get(bg1_name)),
            ("Background 2", bg2_name, BG_COLORS.get(bg2_name)),
        ]
        return _build_entries(entries)

    # multi_{size}_{cat}_{eye}eyes_{bg}_{hash}
    m = re.match(
        r"multi_[a-z]+_([a-z]+)_([a-z_]+)eyes_([a-z_]+)_[a-f0-9]+$", name
    )
    if m:
        cat_name, eye_name, bg_name = m.groups()
        entries = [
            ("Cat",        cat_name, CAT_COLORS.get(cat_name)),
            ("Eyes",       eye_name, EYE_COLORS.get(eye_name)),
            ("Background", bg_name,  BG_COLORS.get(bg_name)),
        ]
        return _build_entries(entries)

    return None


def _build_entries(entries: list) -> list[dict]:
    result = []
    for label, name, rgb in entries:
        if rgb is None:
            continue
        r, g, b = rgb
        c, m, y, k = rgb_to_cmyk(r, g, b)
        result.append({
            "label": label,
            "name":  name.replace("_", " ").title(),
            "hex":   rgb_to_hex(r, g, b),
            "rgb":   {"r": r, "g": g, "b": b},
            "cmyk":  {"c": c, "m": m, "y": y, "k": k},
        })
    return result


# ── Visual card ─────────────────────────────────────────────────────────────

CARD_W      = 900
SWATCH_SIZE = 160
PADDING     = 32
TEXT_H      = 80
CARD_BG     = (250, 250, 248)
FONT_LABEL  = 22
FONT_VALUES = 18


def _font(size: int):
    for name in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
        "/Library/Fonts/Arial.ttf",
    ]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def draw_color_card(colors: list[dict], cat_name: str) -> Image.Image:
    n      = len(colors)
    card_h = PADDING * 2 + SWATCH_SIZE + TEXT_H + 60
    img    = Image.new("RGB", (CARD_W, card_h), CARD_BG)
    draw   = ImageDraw.Draw(img)

    # Title
    f_title = _font(24)
    draw.text((PADDING, 14), f"Color palette — {cat_name}", font=f_title, fill=(60, 60, 60))

    swatch_w    = (CARD_W - PADDING * (n + 1)) // n
    y_swatch    = 55

    for i, c in enumerate(colors):
        x = PADDING + i * (swatch_w + PADDING)
        r, g, b = c["rgb"]["r"], c["rgb"]["g"], c["rgb"]["b"]

        # Swatch
        draw.rectangle([x, y_swatch, x + swatch_w, y_swatch + SWATCH_SIZE], fill=(r, g, b))

        # Text color based on lightness
        text_color = (255, 255, 255) if is_dark(r, g, b) else (40, 40, 40)
        draw.text((x + 8, y_swatch + 8), c["label"], font=_font(FONT_LABEL), fill=text_color)
        draw.text((x + 8, y_swatch + 34), c["name"],  font=_font(FONT_LABEL - 2), fill=text_color)

        # Values below swatch
        y_text = y_swatch + SWATCH_SIZE + 8
        fc     = (80, 80, 80)
        fv     = _font(FONT_VALUES)
        cmyk   = c["cmyk"]
        draw.text((x, y_text),      c["hex"],                    font=fv, fill=(30, 30, 30))
        draw.text((x, y_text + 22), f"RGB {r} {g} {b}",          font=fv, fill=fc)
        draw.text((x, y_text + 42), f"C{cmyk['c']} M{cmyk['m']} Y{cmyk['y']} K{cmyk['k']}", font=fv, fill=fc)

    return img


# ── Main logic ──────────────────────────────────────────────────────────────

def generate_color_card(pair_dir: Path) -> Path | None:
    pngs = sorted(pair_dir.glob("layered_*.png")) or sorted(pair_dir.glob("multi_*.png"))
    if not pngs:
        return None

    colors = parse_colors_from_filename(pngs[0])
    if not colors:
        print(f"  Could not parse colors from: {pngs[0].name}")
        return None

    # Load cat name from description.json if available
    desc_file = pair_dir / "description.json"
    cat_name  = "Unknown"
    if desc_file.exists():
        cat_name = json.loads(desc_file.read_text()).get("cat_name", cat_name)

    # Save JSON
    colors_json = pair_dir / "colors.json"
    colors_json.write_text(json.dumps({"cat_name": cat_name, "colors": colors}, indent=2))

    # Save card
    card     = draw_color_card(colors, cat_name)
    card_out = pair_dir / "color_card.png"
    card.save(str(card_out))

    return card_out


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None

    if target:
        pair_dirs = [Path(target)]
    else:
        pair_dirs = sorted(PRODUCTS_DIR.glob("collection-*/pair-*"))

    for pair_dir in pair_dirs:
        out = generate_color_card(pair_dir)
        if out:
            print(f"{pair_dir.parent.name}/{pair_dir.name} → {out.name}")


if __name__ == "__main__":
    main()
