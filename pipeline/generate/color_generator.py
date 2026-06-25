"""
color_generator.py — Generates colored cat products from silhouettes.

Takes a transparent cat silhouette, picks colors, and saves
a finished product to the appropriate output directory.

Usage:
    from color_generator import generate_colored
    path = generate_colored()
"""
import random
import uuid
from pathlib import Path
from PIL import Image, ImageChops

from palette import (
    DARK_CAT_ANCHORS, LIGHT_CAT_ANCHORS, MUTED_BG_ANCHORS,
    WARM_BG_ANCHORS, DARK_BG_ANCHORS, EYE_ANCHORS, TONAL_EYE_ANCHORS,
    _CAT_DELTA, _BG_DELTA, _EYE_DELTA,
    _sample_anchor,
    _pick_colors, _pick_tonal_colors, _pick_noir_colors,
)

SILHOUETTES_DIR    = Path("assets/silhouettes")
COMPOSITIONS_DIR   = Path("assets/compositions")
OUTPUT_DIR         = Path("generated/single")
COMP_OUTPUT_DIR    = Path("generated/composition")
MULTI_OUTPUT_DIR   = Path("generated/multi")
SCATTER_OUTPUT_DIR = Path("generated/scatter")
LAYERED_OUTPUT_DIR = Path("generated/layered")
LAYERED_PAIR_OUT_DIR = Path("products")

CAT_TEMPLATE = Path("assets/precedents/portrait.png")


def next_generation_dir(base_dir: Path) -> Path:
    """Find the next generation folder (generation-1, generation-2, ...)."""
    base_dir.mkdir(parents=True, exist_ok=True)
    existing = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("generation-")]
    numbers  = [int(d.name.split("-")[1]) for d in existing if d.name.split("-")[1].isdigit()]
    next_n   = max(numbers, default=0) + 1
    gen_dir  = base_dir / f"generation-{next_n}"
    gen_dir.mkdir()
    return gen_dir


_silhouette_queue: list = []

def _pick_silhouette() -> Path:
    """Pick silhouettes in even rotation — no pose repeats until all are used."""
    global _silhouette_queue
    if not _silhouette_queue:
        options = list(SILHOUETTES_DIR.glob("cat-*.png"))
        if not options:
            raise FileNotFoundError(f"No cat-*.png files in {SILHOUETTES_DIR}")
        random.shuffle(options)
        _silhouette_queue = options
    return _silhouette_queue.pop()


def _colorize(silhouette_path: Path, cat_color: tuple, bg_color: tuple, eye_color: tuple) -> Image.Image:
    """
    Colorize a transparent cat silhouette.

    Dark pixels (body) → cat_color
    Light pixels (eyes, whiskers) → eye_color
    Background → bg_color
    """
    img  = Image.open(silhouette_path).convert("RGBA")
    r, g, b, a = img.split()

    gray         = Image.merge("RGB", (r, g, b)).convert("L")
    alpha_binary = a.point(lambda p: 255 if p > 10 else 0)

    body_mask = gray.point(lambda p: 255 if p < 128 else 0)
    body_mask = ImageChops.multiply(body_mask, alpha_binary)

    eye_mask = gray.point(lambda p: 255 if p >= 128 else 0)
    eye_mask = ImageChops.multiply(eye_mask, alpha_binary)

    bg        = Image.new("RGB", img.size, bg_color)
    cat_layer = Image.new("RGB", img.size, cat_color)
    eye_layer = Image.new("RGB", img.size, eye_color)

    bg.paste(cat_layer, mask=body_mask)
    bg.paste(eye_layer, mask=eye_mask)

    return bg


def generate_colored(silhouette_path: Path = None, out_dir: Path = None) -> Path:
    """Generate a single cat image with random colors. Returns the saved file path."""
    if silhouette_path is None:
        silhouette_path = _pick_silhouette()

    cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name = _pick_colors()

    print(f"  Silhouette: {silhouette_path.name}")
    print(f"  Cat:        {cat_name} {cat_rgb}")
    print(f"  Eyes:       {eye_name} {eye_rgb}")
    print(f"  Background: {bg_name} {bg_rgb}")

    result = _colorize(silhouette_path, cat_rgb, bg_rgb, eye_rgb)

    pose = silhouette_path.stem
    folder = out_dir or OUTPUT_DIR
    filename = folder / f"{pose}_{cat_name}_{eye_name}eyes_{bg_name}_{uuid.uuid4().hex[:6]}.png"
    result.save(filename)

    print(f"  Saved:      {filename}")
    return filename


# ── Multi-cat generator ───────────────────────────────────────────────────────

CANVAS_SIZES = {
    "plakat":   (1500, 2000),   # 3:4  — standard poster
    "kvadrat":  (1080, 1080),   # 1:1  — Instagram feed
    "portrett": (1080, 1350),   # 4:5  — Instagram portrait
    "story":    (1080, 1920),   # 9:16 — Instagram story/reel
}

CAT_SCALE = 0.55   # default width: 55% of canvas width

# Per-cat scale override (cat-3 is horizontal and appears larger)
CAT_SCALE_OVERRIDE = {
    "cat-3": 0.40,
}

# Layout template for portrait format (derived from multi-composition-example.png)
# Zigzag: right → left → right
LAYOUT_TEMPLATE = [
    (0.69, 0.20),   # zone 1: upper right
    (0.45, 0.50),   # zone 2: middle left
    (0.62, 0.80),   # zone 3: lower right
]

# Layout template for square/landscape format
# Cats distributed horizontally: left → center → right, slight diagonal
LAYOUT_TEMPLATE_H = [
    (0.18, 0.35),   # left, slightly above center
    (0.50, 0.55),   # center, slightly below center
    (0.82, 0.35),   # right, slightly above center
]

LAYOUT_JITTER = 0.05  # ±5% random variation per image


def _colorize_rgba(silhouette_path: Path, cat_color: tuple, eye_color: tuple) -> Image.Image:
    """Colorize a silhouette and return as RGBA with transparent background."""
    img  = Image.open(silhouette_path).convert("RGBA")
    r, g, b, a = img.split()
    gray         = Image.merge("RGB", (r, g, b)).convert("L")
    alpha_binary = a.point(lambda p: 255 if p > 10 else 0)

    body_mask = ImageChops.multiply(gray.point(lambda p: 255 if p < 128 else 0), alpha_binary)
    eye_mask  = ImageChops.multiply(gray.point(lambda p: 255 if p >= 128 else 0), alpha_binary)

    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(Image.new("RGB", img.size, cat_color), mask=body_mask)
    out.paste(Image.new("RGB", img.size, eye_color), mask=eye_mask)

    r2, g2, b2 = out.split()[:3]
    return Image.merge("RGBA", (r2, g2, b2, alpha_binary))


def _push_apart(x, y, w, h, placed, gap=40):
    """
    Push (x, y) away from all already-placed bounding boxes.
    'placed' is a list of (px, py, pw, ph).
    Pushes up or down depending on which side the cat is closest to.
    """
    for _ in range(100):
        moved = False
        for px, py, pw, ph in placed:
            x_overlap = x < px + pw and x + w > px
            y_overlap = y < py + ph + gap and y + h + gap > py
            if x_overlap and y_overlap:
                my_center    = y + h / 2
                their_center = py + ph / 2
                if my_center >= their_center:
                    y = py + ph + gap   # push down
                else:
                    y = py - h - gap    # push up
                moved = True
        if not moved:
            break
    return x, y


def generate_multi(out_dir: Path = None, canvas_size: str = "plakat",
                   cat_rgb=None, cat_name=None, bg_rgb=None, bg_name=None,
                   eye_rgb=None, eye_name=None) -> Path:
    """
    Three cats placed according to LAYOUT_TEMPLATE (zigzag: right→left→right).
    canvas_size: "plakat", "kvadrat", "portrett", or "story"
    """
    silhouettes = sorted(SILHOUETTES_DIR.glob("cat-*.png"))
    if len(silhouettes) < 2:
        raise FileNotFoundError("Need at least 2 silhouettes in assets/silhouettes/")

    cw, ch = CANVAS_SIZES.get(canvas_size, CANVAS_SIZES["plakat"])

    if cat_rgb is None:
        cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name = _pick_colors()

    print(f"  Format:     {canvas_size} ({cw}×{ch})")
    print(f"  Cat:        {cat_name}")
    print(f"  Eyes:       {eye_name}")
    print(f"  Background: {bg_name}")

    canvas   = Image.new("RGB", (cw, ch), bg_rgb)
    shuffled = silhouettes[:3]
    random.shuffle(shuffled)
    placed   = []
    template = LAYOUT_TEMPLATE_H if cw >= ch else LAYOUT_TEMPLATE

    for zone_idx, sil_path in enumerate(shuffled):
        cat_rgba = _colorize_rgba(sil_path, cat_rgb, eye_rgb)

        scale    = CAT_SCALE_OVERRIDE.get(sil_path.stem, CAT_SCALE)
        target_w = int(cw * scale)
        ratio    = target_w / cat_rgba.width
        new_w    = target_w
        new_h    = int(cat_rgba.height * ratio)
        cat_rgba = cat_rgba.resize((new_w, new_h), Image.LANCZOS)

        if random.random() < 0.5:
            cat_rgba = cat_rgba.transpose(Image.FLIP_LEFT_RIGHT)

        cx_rel, cy_rel = template[zone_idx]
        cx_rel += random.uniform(-LAYOUT_JITTER, LAYOUT_JITTER)
        cy_rel += random.uniform(-LAYOUT_JITTER, LAYOUT_JITTER)

        x = int(cw * cx_rel) - new_w // 2
        y = int(ch * cy_rel) - new_h // 2

        x, y = _push_apart(x, y, new_w, new_h, placed)

        # Soft clamp: cats can bleed off edge but never more than 50%
        x = max(-new_w // 2, min(x, cw - new_w // 2))
        y = max(-new_h // 2, min(y, ch - new_h // 2))

        placed.append((x, y, new_w, new_h))
        canvas.paste(cat_rgba, (x, y), mask=cat_rgba.split()[3])

    folder   = out_dir or MULTI_OUTPUT_DIR
    filename = folder / f"multi_{canvas_size}_{cat_name}_{eye_name}eyes_{bg_name}_{uuid.uuid4().hex[:6]}.png"
    canvas.save(filename)

    print(f"  Saved:      {filename}")
    return filename


# ── Composition generator ─────────────────────────────────────────────────────

def _sample_bg_colors(img: Image.Image) -> tuple[tuple, tuple]:
    """Sample background colors from the corners of the image."""
    pixels = img.load()
    w, h   = img.size
    bg1    = pixels[20, 20][:3]
    bg2    = pixels[w - 20, h - 20][:3]
    return bg1, bg2


def _color_mask(img: Image.Image, target: tuple, tolerance: int = 38):
    """Create a mask where pixels close to target color are white."""
    tr, tg, tb = target
    r, g, b    = img.split()[:3]
    rm = r.point(lambda p: 255 if abs(p - tr) < tolerance else 0)
    gm = g.point(lambda p: 255 if abs(p - tg) < tolerance else 0)
    bm = b.point(lambda p: 255 if abs(p - tb) < tolerance else 0)
    return ImageChops.multiply(ImageChops.multiply(rm, gm), bm)


def _recolor_composition(img_path: Path, new_color1: tuple, new_color2: tuple) -> Image.Image:
    """Replace the two background colors in a composition with new colors."""
    img  = Image.open(img_path).convert("RGB")
    bg1, bg2 = _sample_bg_colors(img)

    mask1 = _color_mask(img, bg1)
    mask2 = _color_mask(img, bg2)

    result = img.copy()
    result.paste(Image.new("RGB", img.size, new_color1), mask=mask1)
    result.paste(Image.new("RGB", img.size, new_color2), mask=mask2)
    return result


def generate_composition(comp_path: Path = None, out_dir: Path = None) -> Path:
    """Generate a new color variant of an existing composition. Returns the saved file path."""
    if comp_path is None:
        options = list(COMPOSITIONS_DIR.glob("*.png"))
        comp_path = random.choice(options)

    color1_name, color1_rgb = _sample_anchor(MUTED_BG_ANCHORS, _BG_DELTA)
    color2_name, color2_rgb = _sample_anchor(MUTED_BG_ANCHORS, _BG_DELTA)
    while color2_name == color1_name:
        color2_name, color2_rgb = _sample_anchor(MUTED_BG_ANCHORS, _BG_DELTA)

    print(f"  Composition: {comp_path.name}")
    print(f"  Color 1:     {color1_name} {color1_rgb}")
    print(f"  Color 2:     {color2_name} {color2_rgb}")

    result   = _recolor_composition(comp_path, color1_rgb, color2_rgb)
    stem     = comp_path.stem.replace(" ", "_")
    folder   = out_dir or COMP_OUTPUT_DIR
    filename = folder / f"{stem}_{color1_name}_{color2_name}_{uuid.uuid4().hex[:6]}.png"
    result.save(filename)

    print(f"  Saved:       {filename}")
    return filename


def generate_scatter(count: int = 60, out_dir: Path = None) -> Path:
    """Pattern mode: cats in a grid with brick offset. Even distribution, no gaps."""
    import math
    cw, ch = 3000, 3000

    cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name = _pick_colors()

    print(f"  Count:      {count}")
    print(f"  Cat:        {cat_name}")
    print(f"  Eyes:       {eye_name}")
    print(f"  Background: {bg_name}")

    canvas      = Image.new("RGB", (cw, ch), bg_rgb)
    silhouettes = sorted(SILHOUETTES_DIR.glob("cat-*.png"))
    random.shuffle(silhouettes)
    weights     = [0.50, 0.35, 0.15]   # primary → secondary → tertiary

    cols   = math.ceil(math.sqrt(count))
    rows   = math.ceil(count / cols)
    cell_w = cw // cols
    cell_h = ch // rows

    # Offset rows start at col=-1 to fill edges
    cells = []
    for r in range(rows):
        col_range = range(-1, cols) if r % 2 == 1 else range(cols)
        for c in col_range:
            cells.append((c, r))

    for col, row in cells:
        sil_path = random.choices(silhouettes, weights=weights, k=1)[0]
        cat_rgba = _colorize_rgba(sil_path, cat_rgb, eye_rgb)

        override_ratio = CAT_SCALE_OVERRIDE.get(sil_path.stem, CAT_SCALE) / CAT_SCALE
        base_scale = (cell_w / cw) * 0.85   # always 85% of cell size
        scale      = base_scale * override_ratio
        target_w = int(cw * scale)
        ratio    = target_w / cat_rgba.width
        new_w    = target_w
        new_h    = int(cat_rgba.height * ratio)
        cat_rgba = cat_rgba.resize((new_w, new_h), Image.LANCZOS)

        if random.random() < 0.30:
            cat_rgba = cat_rgba.transpose(Image.FLIP_LEFT_RIGHT)

        offset = cell_w // 2 if row % 2 == 1 else 0
        cx = col * cell_w + cell_w // 2 + offset
        cy = row * cell_h + cell_h // 2
        x  = cx - new_w // 2
        y  = cy - new_h // 2

        canvas.paste(cat_rgba, (x, y), mask=cat_rgba.split()[3])

    folder   = out_dir or SCATTER_OUTPUT_DIR
    folder.mkdir(parents=True, exist_ok=True)
    filename = folder / f"scatter_{cat_name}_{eye_name}eyes_{bg_name}_{uuid.uuid4().hex[:6]}.png"
    canvas.save(filename)
    print(f"  Saved:      {filename}")
    return filename


def _build_layered_image(cat_rgb=None, cat_name=None, eye_rgb=None, eye_name=None,
                          bg_rgb=None, bg_name=None, bg_anchors=None) -> tuple:
    """Build a layered portrait image.
    Returns (image, name_stem, bg1_name, bg2_name, bg1_rgb, bg2_rgb).
    bg2 = the passed bg (accent/bottom strip); bg1 = freshly sampled (dominant/top).
    bg_anchors: which anchor dict to sample bg1 from (default: MUTED_BG_ANCHORS).
    """
    if cat_rgb is None:
        cat_name, cat_rgb = _sample_anchor(DARK_CAT_ANCHORS, _CAT_DELTA)
        eye_name, eye_rgb = _sample_anchor(EYE_ANCHORS,      _EYE_DELTA)

    def _too_similar(c1, c2):
        return max(abs(a - b) for a, b in zip(c1, c2)) < 30

    anchors = bg_anchors or MUTED_BG_ANCHORS
    bg1_name, bg1_rgb = _sample_anchor(anchors, _BG_DELTA)
    if bg_rgb is not None:
        bg2_rgb  = bg_rgb
        bg2_name = bg_name or "accent"
        while bg1_name == bg2_name or _too_similar(bg1_rgb, bg2_rgb):
            bg1_name, bg1_rgb = _sample_anchor(anchors, _BG_DELTA)
    else:
        bg2_name, bg2_rgb = _sample_anchor(anchors, _BG_DELTA)
        while bg2_name == bg1_name or _too_similar(bg1_rgb, bg2_rgb):
            bg2_name, bg2_rgb = _sample_anchor(anchors, _BG_DELTA)

    print(f"  Cat:        {cat_name}")
    print(f"  Eyes:       {eye_name}")
    print(f"  Background: {bg1_name} + {bg2_name}")
    cat_rgba = _colorize_rgba(CAT_TEMPLATE, cat_rgb, eye_rgb)
    w, h = cat_rgba.size
    split_y = int(h * 0.6694)  # proportion measured from color-pallette-example.png
    bg = Image.new("RGB", (w, h), bg1_rgb)
    bg.paste(Image.new("RGB", (w, h - split_y), bg2_rgb), (0, split_y))
    bg.paste(cat_rgba, (0, 0), mask=cat_rgba.split()[3])
    stem = f"layered_{cat_name}_{eye_name}eyes_{bg1_name}_{bg2_name}_{uuid.uuid4().hex[:6]}"
    return bg, stem, bg1_name, bg2_name, bg1_rgb, bg2_rgb


def generate_layered(out_dir: Path = None) -> Path:
    """Combine background template + transparent cat composition. Saves full size."""
    img, stem, *_ = _build_layered_image()
    folder = out_dir or LAYERED_OUTPUT_DIR
    folder.mkdir(parents=True, exist_ok=True)
    filename = folder / f"{stem}.png"
    img.save(filename)
    print(f"  Saved:      {filename}")
    return filename


def _hue_dist(h1: float, h2: float) -> float:
    """Circular distance between two hue angles (0–360°)."""
    d = abs(h1 - h2) % 360
    return min(d, 360 - d)


def generate_layered_pair(out_dir: Path = None) -> tuple:
    """Generate two cats: katt_1 tonal (lys+varm) + katt_2 noir (mørk+kjølig).
    Guarantees ≥60° hue distance between the two cats (if both are chromatic).
    """
    folder = out_dir or LAYERED_PAIR_OUT_DIR
    folder.mkdir(parents=True, exist_ok=True)

    print("  [katt_1 — tonal]")
    cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name = _pick_tonal_colors()
    katt1_hsl = LIGHT_CAT_ANCHORS.get(cat_name, (0, 0, 0))

    print("  [katt_2 — noir]")
    for _ in range(30):
        cat_rgb2, cat_name2, bg_rgb2, bg_name2, eye_rgb2, eye_name2 = _pick_noir_colors()
        katt2_hsl = DARK_CAT_ANCHORS.get(cat_name2, (0, 0, 0))
        both_chromatic = katt1_hsl[1] > 10 and katt2_hsl[1] > 10
        if not both_chromatic or _hue_dist(katt1_hsl[0], katt2_hsl[0]) >= 60:
            break

    img, stem, *_ = _build_layered_image(cat_rgb=cat_rgb, cat_name=cat_name,
                                          eye_rgb=eye_rgb, eye_name=eye_name,
                                          bg_rgb=bg_rgb, bg_name=bg_name,
                                          bg_anchors=WARM_BG_ANCHORS)
    katt1_portrait = folder / f"{stem}.png"
    img.save(katt1_portrait)
    katt1_comp = generate_multi(out_dir=folder, canvas_size="portrett",
                                cat_rgb=cat_rgb, cat_name=cat_name,
                                bg_rgb=bg_rgb, bg_name=bg_name,
                                eye_rgb=eye_rgb, eye_name=eye_name)

    img2, stem2, *_ = _build_layered_image(cat_rgb=cat_rgb2, cat_name=cat_name2,
                                            eye_rgb=eye_rgb2, eye_name=eye_name2,
                                            bg_rgb=bg_rgb2, bg_name=bg_name2,
                                            bg_anchors=DARK_BG_ANCHORS)
    katt2_portrait = folder / f"{stem2}.png"
    img2.save(katt2_portrait)
    katt2_comp = generate_multi(out_dir=folder, canvas_size="portrett",
                                cat_rgb=cat_rgb2, cat_name=cat_name2,
                                bg_rgb=bg_rgb2, bg_name=bg_name2,
                                eye_rgb=eye_rgb2, eye_name=eye_name2)

    return katt1_portrait, katt1_comp, katt2_portrait, katt2_comp


def _pick_collection_colors() -> list:
    """Pick 3 color combos for a collection, ensuring no repeated cat anchors."""
    all_cats  = {**DARK_CAT_ANCHORS, **LIGHT_CAT_ANCHORS}
    used_cats = []
    combos    = []
    for _ in range(3):
        cat_name, cat_rgb = _sample_anchor(all_cats,         _CAT_DELTA)
        while cat_name in used_cats:
            cat_name, cat_rgb = _sample_anchor(all_cats,     _CAT_DELTA)
        bg_name,  bg_rgb  = _sample_anchor(MUTED_BG_ANCHORS, _BG_DELTA)
        eye_name, eye_rgb = _sample_anchor(EYE_ANCHORS,      _EYE_DELTA)
        combos.append((cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name))
        used_cats.append(cat_name)
    return combos


def generate_collection(base_dir: Path = None) -> list:
    """
    Generate 3 harmonious pairs as a collection.
    Saves to products/collection-N/pair-A|B|C/
    """
    root = base_dir or LAYERED_PAIR_OUT_DIR
    root.mkdir(parents=True, exist_ok=True)
    existing = [d for d in root.iterdir() if d.is_dir() and d.name.startswith("collection-")]
    numbers  = [int(d.name.split("-")[1]) for d in existing if d.name.split("-")[1].isdigit()]
    n = max(numbers, default=0) + 1
    collection_dir = root / f"collection-{n}"
    collection_dir.mkdir()

    print(f"\n  Collection {n}  (3 pairs)")
    print(f"  {'─' * 42}")

    combos  = _pick_collection_colors()
    results = []

    for i, (cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name) in enumerate(combos):
        label    = ["A", "B", "C"][i]
        pair_dir = collection_dir / f"pair-{label}"
        pair_dir.mkdir()

        print(f"\n  [Pair {label}]  {cat_name} cat / {eye_name} eyes / {bg_name} bg")

        img, stem, _, bg2_name, _, bg2_rgb = _build_layered_image(
            cat_rgb=cat_rgb, cat_name=cat_name,
            eye_rgb=eye_rgb, eye_name=eye_name,
            bg_rgb=bg_rgb, bg_name=bg_name,
        )
        layered_path = pair_dir / f"{stem}.png"
        img.save(layered_path)
        print(f"  Saved (layered):   {layered_path.name}")

        portrait_path = generate_multi(
            out_dir=pair_dir, canvas_size="portrett",
            cat_rgb=cat_rgb, cat_name=cat_name,
            bg_rgb=bg2_rgb, bg_name=bg2_name,
            eye_rgb=eye_rgb, eye_name=eye_name,
        )
        results.append((layered_path, portrait_path))

    print(f"\n  Done — collection-{n}: 3 pairs, 6 images → {collection_dir}/")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--count",        type=int,  default=1)
    parser.add_argument("--compositions", action="store_true", help="Generate compositions instead of single cats")
    args = parser.parse_args()

    for i in range(args.count):
        print(f"\n[{i+1}/{args.count}]")
        if args.compositions:
            generate_composition()
        else:
            generate_colored()

    folder = "generated/composition" if args.compositions else "generated/single"
    print(f"\nDone! Check {folder}/")
