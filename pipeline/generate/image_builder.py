"""
image_builder.py — Rendering for the cat bot.

Answers the question: "paint it."

Takes a layout plan from form_builder + colors from color_selector,
and produces finished image files.
"""
import sys
import uuid
from pathlib import Path
from PIL import Image, ImageChops

# Allows this module to be imported as pipeline.generate.image_builder
# (e.g. from describe.py, publish.py) as well as run directly from this folder.
_here = str(Path(__file__).parent)
if _here not in sys.path:
    sys.path.insert(0, _here)

from form_builder import plan_layered, plan_multi
from color_selector import pick_pair_colors, pick_collection_colors, hue_dist
from palette import TONAL_BG_POOL, NOIR_BG_POOL, WAALS, _sample_bg


OUTPUT_DIR = Path("products")


def next_generation_dir(base_dir: Path) -> Path:
    """Find the next generation folder (generation-1, generation-2, ...)."""
    base_dir.mkdir(parents=True, exist_ok=True)
    existing = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("generation-")]
    numbers  = [int(d.name.split("-")[1]) for d in existing if d.name.split("-")[1].isdigit()]
    gen_dir  = base_dir / f"generation-{max(numbers, default=0) + 1}"
    gen_dir.mkdir()
    return gen_dir


# ── Core paint function ───────────────────────────────────────────────────────

def _colorize_rgba(silhouette_path: Path, cat_color: tuple, eye_color: tuple) -> Image.Image:
    """Paint a silhouette with cat_color and eye_color. Returns RGBA."""
    img  = Image.open(silhouette_path).convert("RGBA")
    r, g, b, a = img.split()
    gray         = Image.merge("RGB", (r, g, b)).convert("L")
    alpha_binary = a.point(lambda p: 255 if p > 10 else 0)
    body_mask = ImageChops.multiply(gray.point(lambda p: 255 if p < 128 else 0), alpha_binary)
    eye_mask  = ImageChops.multiply(gray.point(lambda p: 255 if p >= 128 else 0), alpha_binary)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(Image.new("RGB", img.size, cat_color), mask=body_mask)
    out.paste(Image.new("RGB", img.size, eye_color),  mask=eye_mask)
    r2, g2, b2 = out.split()[:3]
    return Image.merge("RGBA", (r2, g2, b2, alpha_binary))


# ── Render functions ──────────────────────────────────────────────────────────

def render_layered(form: dict, cat_rgb, eye_rgb, bg1_rgb, bg2_rgb) -> Image.Image:
    """
    Paint a layered portrait.
    Takes a form plan (from plan_layered) + four colors.
    Returns a finished image — does not save.
    """
    cat_rgba = _colorize_rgba(form["template"], cat_rgb, eye_rgb)
    w, h     = form["width"], form["height"]
    bg = Image.new("RGB", (w, h), bg1_rgb)
    bg.paste(Image.new("RGB", (w, h - form["split_y"]), bg2_rgb), (0, form["split_y"]))
    bg.paste(cat_rgba, (0, 0), mask=cat_rgba.split()[3])
    return bg


def render_multi(form: dict, cat_rgb, eye_rgb, bg_rgb) -> Image.Image:
    """
    Paint a 3-cat multi layout.
    Takes a form plan (from plan_multi) + three colors.
    Returns a finished image — does not save.
    """
    canvas = Image.new("RGB", (form["width"], form["height"]), bg_rgb)
    for cat in form["cats"]:
        cat_rgba = _colorize_rgba(cat["silhouette"], cat_rgb, eye_rgb)
        cat_rgba = cat_rgba.resize((cat["w"], cat["h"]), Image.LANCZOS)
        if cat["flip"]:
            cat_rgba = cat_rgba.transpose(Image.FLIP_LEFT_RIGHT)
        canvas.paste(cat_rgba, (cat["x"], cat["y"]), mask=cat_rgba.split()[3])
    return canvas


# ── Background helpers ────────────────────────────────────────────────────────

def _too_similar(c1, c2) -> bool:
    return max(abs(a - b) for a, b in zip(c1, c2)) < 15


def _bg_pair_ok(name1: str, name2: str, rgb1, rgb2) -> bool:
    """Two background halves should be distinct but not clashing hues."""
    if name1 == name2 or _too_similar(rgb1, rgb2):
        return False
    h1 = WAALS.get(name1, (0, 0, 0))[0]
    h2 = WAALS.get(name2, (0, 0, 0))[0]
    return hue_dist(h1, h2) <= 100


def _pick_two_bg(pool: dict, locked_rgb=None, locked_name=None):
    """Pick two visually distinct, hue-harmonious background colors from a pool."""
    bg1_name, bg1_rgb = _sample_bg(pool)
    if locked_rgb is not None:
        bg2_rgb, bg2_name = locked_rgb, locked_name or "accent"
        for _ in range(50):
            if _bg_pair_ok(bg1_name, bg2_name, bg1_rgb, bg2_rgb):
                break
            bg1_name, bg1_rgb = _sample_bg(pool)
    else:
        bg2_name, bg2_rgb = _sample_bg(pool)
        for _ in range(50):
            if _bg_pair_ok(bg1_name, bg2_name, bg1_rgb, bg2_rgb):
                break
            bg2_name, bg2_rgb = _sample_bg(pool)
    return bg1_name, bg1_rgb, bg2_name, bg2_rgb


# ── Public generators ─────────────────────────────────────────────────────────

def generate_pair(out_dir: Path = None) -> tuple:
    """
    Generate one tonal/noir pair. Three clear steps:

      1. Form   — plan the layout
      2. Colors — pick the palette
      3. Build  — render and save

    Returns (katt1_layered, katt1_multi, katt2_layered, katt2_multi).
    """
    folder = out_dir or OUTPUT_DIR
    folder.mkdir(parents=True, exist_ok=True)

    # Step 1: Form
    layered_form = plan_layered()
    multi_form   = plan_multi("portrett")

    # Step 2: Colors
    (cat_rgb,  cat_name,  bg_rgb,  bg_name,  eye_rgb,  eye_name), \
    (cat_rgb2, cat_name2, bg_rgb2, bg_name2, eye_rgb2, eye_name2) = pick_pair_colors()

    # Step 3: Build
    print(f"  [katt_1 — tonal]  {cat_name} / {eye_name} eyes / {bg_name} bg")
    bg1_name, bg1_rgb, bg2_name, bg2_rgb = _pick_two_bg(TONAL_BG_POOL, bg_rgb, bg_name)
    tonal_hues = [WAALS[bg1_name][0], WAALS[bg2_name][0]]
    k1_layered = render_layered(layered_form, cat_rgb, eye_rgb, bg1_rgb, bg2_rgb)
    k1_multi   = render_multi(multi_form, cat_rgb, eye_rgb, bg2_rgb)
    uid1 = uuid.uuid4().hex[:6]
    k1_layered_path = folder / f"layered_{cat_name}_{eye_name}eyes_{bg1_name}_{bg2_name}_{uid1}.png"
    k1_multi_path   = folder / f"multi_portrett_{cat_name}_{eye_name}eyes_{bg2_name}_{uid1}.png"
    k1_layered.save(k1_layered_path)
    k1_multi.save(k1_multi_path)

    print(f"  [katt_2 — noir]   {cat_name2} / {eye_name2} eyes / {bg_name2} bg")
    for _ in range(20):
        bg1_name2, bg1_rgb2, bg2_name2, bg2_rgb2 = _pick_two_bg(NOIR_BG_POOL, bg_rgb2, bg_name2)
        noir_hues = [WAALS[bg1_name2][0], WAALS[bg2_name2][0]]
        if any(hue_dist(th, nh) <= 60 for th in tonal_hues for nh in noir_hues):
            break
    k2_layered = render_layered(layered_form, cat_rgb2, eye_rgb2, bg1_rgb2, bg2_rgb2)
    k2_multi   = render_multi(multi_form, cat_rgb2, eye_rgb2, bg2_rgb2)
    uid2 = uuid.uuid4().hex[:6]
    k2_layered_path = folder / f"layered_{cat_name2}_{eye_name2}eyes_{bg1_name2}_{bg2_name2}_{uid2}.png"
    k2_multi_path   = folder / f"multi_portrett_{cat_name2}_{eye_name2}eyes_{bg2_name2}_{uid2}.png"
    k2_layered.save(k2_layered_path)
    k2_multi.save(k2_multi_path)

    return k1_layered_path, k1_multi_path, k2_layered_path, k2_multi_path


def generate_set(out_dir: Path = None) -> Path:
    """
    Generate one set: 4 prints + 6 mockups, all flat in set-N/.

    Matches the structure of mockup_set_test_1:
      _print_layered_katt1_...png
      _print_layered_katt2_...png
      _print_multi_portrett_katt1_...png
      _print_multi_portrett_katt2_...png
      0018_windowsill_minimal_light.png
      ... (5 more mockups)

    Steps: 1. Form  2. Colors  3. Build prints  4. Mockups
    Returns the set directory.
    """
    # Lazy import so mockup.py adds its own sys.path first
    _root = Path(__file__).parent.parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from pipeline.mockup.mockup import (
        _generate_psd_single, _generate_psd_multi,
        _select_single, _select_multi, _get_entry,
        TEMPLATES_DIR as _TPL_DIR,
    )

    def _pick_room(warmth: str, exclude_stems: set = None) -> Path:
        """Pick a single-frame template. Avoids dark rooms and already-used stems."""
        exclude_stems = exclude_stems or set()
        for _ in range(15):
            for tpl in _select_single(warmth, n=6):
                rel   = str(tpl.relative_to(_TPL_DIR))
                entry = _get_entry(rel) or {}
                if entry.get("bg_tone") != "dark" and tpl.stem not in exclude_stems:
                    return tpl
        return _select_single(warmth, n=6)[0]  # fallback

    folder = out_dir or OUTPUT_DIR
    folder.mkdir(parents=True, exist_ok=True)
    existing = [d for d in folder.iterdir() if d.is_dir() and d.name.startswith("set-")]
    numbers  = [int(d.name.split("-")[1]) for d in existing if d.name.split("-")[1].isdigit()]
    n        = max(numbers, default=0) + 1
    set_dir  = folder / f"set-{n}"
    set_dir.mkdir()

    print(f"\n  Set {n}")
    print(f"  {'─' * 42}")

    # Step 1: Form
    layered_form  = plan_layered()
    multi_form_k1 = plan_multi("portrett")
    multi_form_k2 = plan_multi("portrett")

    # Step 2: Colors
    (cat_rgb,  cat_name,  bg_rgb,  bg_name,  eye_rgb,  eye_name), \
    (cat_rgb2, cat_name2, bg_rgb2, bg_name2, eye_rgb2, eye_name2) = pick_pair_colors()

    # Step 3: Build prints with _print_ prefix, saved flat in set_dir
    print(f"  [katt_1 — tonal]  {cat_name} / {eye_name} eyes / {bg_name} bg")
    bg1_name, bg1_rgb, bg2_name, bg2_rgb = _pick_two_bg(TONAL_BG_POOL, bg_rgb, bg_name)
    tonal_hues = [WAALS[bg1_name][0], WAALS[bg2_name][0]]
    k1_layered = render_layered(layered_form,  cat_rgb, eye_rgb, bg1_rgb, bg2_rgb)
    k1_multi   = render_multi(multi_form_k1, cat_rgb, eye_rgb, bg2_rgb)
    uid1 = uuid.uuid4().hex[:6]
    k1_layered_path = set_dir / f"_print_portrait_katt1_{cat_name}_{eye_name}eyes_{bg1_name}_{bg2_name}_{uid1}.png"
    k1_multi_path   = set_dir / f"_print_composition_katt1_{cat_name}_{eye_name}eyes_{bg2_name}_{uid1}.png"
    k1_layered.save(k1_layered_path)
    k1_multi.save(k1_multi_path)

    print(f"  [katt_2 — noir]   {cat_name2} / {eye_name2} eyes / {bg_name2} bg")
    for _ in range(20):
        bg1_name2, bg1_rgb2, bg2_name2, bg2_rgb2 = _pick_two_bg(NOIR_BG_POOL, bg_rgb2, bg_name2)
        noir_hues = [WAALS[bg1_name2][0], WAALS[bg2_name2][0]]
        if any(hue_dist(th, nh) <= 60 for th in tonal_hues for nh in noir_hues):
            break
    k2_layered = render_layered(layered_form,  cat_rgb2, eye_rgb2, bg1_rgb2, bg2_rgb2)
    k2_multi   = render_multi(multi_form_k2, cat_rgb2, eye_rgb2, bg2_rgb2)
    uid2 = uuid.uuid4().hex[:6]
    k2_layered_path = set_dir / f"_print_portrait_katt2_{cat_name2}_{eye_name2}eyes_{bg1_name2}_{bg2_name2}_{uid2}.png"
    k2_multi_path   = set_dir / f"_print_composition_katt2_{cat_name2}_{eye_name2}eyes_{bg2_name2}_{uid2}.png"
    k2_layered.save(k2_layered_path)
    k2_multi.save(k2_multi_path)

    # Step 4: Mockups — 4 single-frame + 2 double-frame, all flat in set_dir
    print(f"  [mockups]")

    # 4 single-frame: same room per print-type, both cats
    # Room warmth is derived from the actual cat bg colors (not hardcoded)
    from pipeline.mockup.mockup import BG_WARMTH
    warmth1 = BG_WARMTH.get(bg1_name, BG_WARMTH.get(bg2_name, "warm"))
    warmth2 = BG_WARMTH.get(bg1_name2, BG_WARMTH.get(bg2_name2, "cool"))

    portrait_tpl    = _pick_room(warmth1)
    composition_tpl = _pick_room(warmth2, exclude_stems={portrait_tpl.stem})

    def _single(print_path: Path, tpl: Path, suffix: str) -> None:
        try:
            outs = _generate_psd_single(print_path, tpl, set_dir)
            for f in outs:
                f.rename(f.parent / f.name.replace(".png", f"_{suffix}.png"))
        except Exception as e:
            print(f"    ERROR {tpl.name}: {e}")

    _single(k1_layered_path, portrait_tpl,    "katt1")   # katt_1 portrait
    _single(k2_layered_path, portrait_tpl,    "katt2")   # katt_2 portrait (same room)
    _single(k1_multi_path,   composition_tpl, "katt1")   # katt_1 composition
    _single(k2_multi_path,   composition_tpl, "katt2")   # katt_2 composition (same room)

    # 2 double-frame: portraits side by side, then compositions side by side
    double_tpls = _select_multi(2, count=2)
    double_pairs = [
        (double_tpls[0], [k1_layered_path, k2_layered_path]),   # portraits
        (double_tpls[1], [k1_multi_path,   k2_multi_path]),     # compositions
    ] if len(double_tpls) >= 2 else []
    for tpl, prints in double_pairs:
        try:
            _generate_psd_multi(set_dir, tpl, set_dir, prints=prints)
        except Exception as e:
            print(f"    ERROR {tpl.name}: {e}")

    print(f"\n  Done — set-{n} → {set_dir}/")
    return set_dir


def find_set_pairs(set_dir: Path) -> dict:
    """
    Group a set-N/ folder's flat files into its 2 virtual pairs (one per cat).

    Each pair gets its 2 print images (portrait + composition) and the
    mockups tagged for that cat, plus the shared double-frame mockups
    (which show both cats and have no katt1/katt2 tag).

    Returns {"katt1": {"portrait": Path, "composition": Path, "mockups": [Path, ...]}, "katt2": {...}}
    Missing/incomplete pairs are omitted.
    """
    shared_mockups = [
        p for p in sorted(set_dir.glob("*.png"))
        if not p.name.startswith("_print_") and not p.stem.endswith(("katt1", "katt2"))
    ]

    pairs = {}
    for tag in ("katt1", "katt2"):
        portrait    = next(iter(set_dir.glob(f"_print_portrait_{tag}_*.png")), None)
        composition = next(iter(set_dir.glob(f"_print_composition_{tag}_*.png")), None)
        if not portrait or not composition:
            continue
        own_mockups = sorted(set_dir.glob(f"*_{tag}.png"))
        pairs[tag] = {
            "portrait":    portrait,
            "composition": composition,
            "mockups":     own_mockups + shared_mockups,
        }
    return pairs


def renumber_sets(products_dir: Path = None) -> list:
    """
    Close any gaps in set-N numbering (e.g. after a ./reject) so folders are
    always sequential: 1, 2, 3, ... with no missing numbers.

    products/rejected/ is untouched — it's a differently-named folder, not
    matched by the "set-*" glob. Safe to run even on already-published sets:
    published.json stores the Etsy listing_id/url, not the folder name.

    Renames go through temp names first so an in-place shuffle (e.g. set-5 -> set-2)
    never collides with another set-N folder that hasn't been processed yet.
    """
    folder = products_dir or Path("products")
    dirs = sorted(
        (d for d in folder.glob("set-*") if d.is_dir() and d.name.split("-")[1].isdigit()),
        key=lambda d: int(d.name.split("-")[1]),
    )

    staged = []
    for d in dirs:
        tmp = d.with_name(f"_renumber_{d.name}")
        d.rename(tmp)
        staged.append(tmp)

    renamed = []
    for i, tmp in enumerate(staged, 1):
        final = folder / f"set-{i}"
        tmp.rename(final)
        renamed.append(final)
    return renamed


def generate_collection(base_dir: Path = None) -> list:
    """
    Generate 3 pairs as a collection. Three clear steps per pair:

      1. Form   — plan the layout
      2. Colors — pick the palette
      3. Build  — render and save

    Saves to products/collection-N/pair-A|B|C/
    """
    root = base_dir or OUTPUT_DIR
    root.mkdir(parents=True, exist_ok=True)
    existing = [d for d in root.iterdir() if d.is_dir() and d.name.startswith("collection-")]
    numbers  = [int(d.name.split("-")[1]) for d in existing if d.name.split("-")[1].isdigit()]
    n        = max(numbers, default=0) + 1
    col_dir  = root / f"collection-{n}"
    col_dir.mkdir()

    print(f"\n  Collection {n}  (3 pairs)")
    print(f"  {'─' * 42}")

    results = []
    for i, (cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name) in enumerate(pick_collection_colors()):
        label    = ["A", "B", "C"][i]
        pair_dir = col_dir / f"pair-{label}"
        pair_dir.mkdir()
        print(f"\n  [Pair {label}]  {cat_name} / {eye_name} eyes / {bg_name} bg")

        # Step 1: Form
        layered_form = plan_layered()
        multi_form   = plan_multi("portrett")

        # Step 2: Colors
        pool = TONAL_BG_POOL if i == 0 else NOIR_BG_POOL
        bg1_name, bg1_rgb, bg2_name, bg2_rgb = _pick_two_bg(pool, bg_rgb, bg_name)

        # Step 3: Build
        layered = render_layered(layered_form, cat_rgb, eye_rgb, bg1_rgb, bg2_rgb)
        multi   = render_multi(multi_form, cat_rgb, eye_rgb, bg2_rgb)
        uid = uuid.uuid4().hex[:6]
        layered_path = pair_dir / f"layered_{cat_name}_{eye_name}eyes_{bg1_name}_{bg2_name}_{uid}.png"
        multi_path   = pair_dir / f"multi_portrett_{cat_name}_{eye_name}eyes_{bg2_name}_{uid}.png"
        layered.save(layered_path)
        multi.save(multi_path)
        print(f"  Saved: {layered_path.name}")
        results.append((layered_path, multi_path))

    print(f"\n  Done — collection-{n} → {col_dir}/")
    return results
