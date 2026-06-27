"""
color_selector.py — Color selection logic for the cat bot.

Answers the question: "which colors should we use?"

Implements the 5-step selection order from color_principles.md:
  1. Cat color first  (hue + lightness defines the whole gamut)
  2. Background filtered by cat temperature  (warm cat → prefer cool bg)
  3. L-contrast check  (ΔL ≥ 15 between cat and bg)
  4. Eyes filtered by cat hue  (ΔH 60–180° = strongest accent)
  5. Eye S boosted ~15%  (compensates for size-based chroma loss)
"""
import random

from palette import (
    WAALS,
    TONAL_CAT_POOL, NOIR_CAT_POOL,
    TONAL_EYE_POOL, NOIR_EYE_POOL,
    TONAL_BG_POOL, NOIR_BG_POOL,
    _CAT_DELTA, _EYE_DELTA,
    _sample_from, _sample_bg, _sample_hsl,
)


# ── Color theory helpers ──────────────────────────────────────────────────────

def hue_dist(h1: float, h2: float) -> float:
    """Shortest angular distance between two hues on the color wheel (0–360°)."""
    d = abs(h1 - h2) % 360
    return min(d, 360 - d)


def temperature(hue: float) -> str:
    """Classify a hue as warm, cool, or neutral (Itten cold-warm contrast)."""
    if hue < 60 or hue > 300:
        return "warm"
    elif 100 < hue < 260:
        return "cool"
    return "neutral"   # yellow-green and red-violet transition zones


def _l_contrast_ok(cat_l: float, bg_l: float, min_delta: float = 15.0) -> bool:
    """ΔL ≥ 15 ensures the cat is clearly visible against its background."""
    return abs(cat_l - bg_l) >= min_delta


def _eye_is_accent(cat_hue: float, eye_hue: float) -> bool:
    """Eyes 60–180° from cat hue give the strongest, clearest accent."""
    delta = abs((eye_hue - cat_hue + 180) % 360 - 180)
    return 60 <= delta <= 180


# ── CMYK gamut safety ────────────────────────────────────────────────────────

def _cmyk_safe_s(hue: float, s: float) -> float:
    """
    Cap saturation for hues that clip badly when converted to CMYK.

    Greens (H 80–165) are the worst offenders — a vivid green with S=94 on
    screen prints as a flat, muddy olive because CMYK simply can't mix that hue
    at full chroma.  Cyans (H 165–200) have a smaller but real gap.
    Warm hues (reds, oranges, yellows) are safe at any S.
    """
    if 80 <= hue <= 165:    # green family — worst CMYK gap
        return min(s, 65.0)
    if 165 < hue <= 200:    # cyan family — moderate gap
        return min(s, 75.0)
    return s                # warm hues and blues: fine at full S


def _sample_cat(pool: dict, delta: tuple) -> tuple[str, tuple]:
    """Sample a cat color with CMYK-aware S cap applied before jitter."""
    name = random.choice(list(pool.keys()))
    h, s, l = WAALS[name]
    return name, _sample_hsl(h, _cmyk_safe_s(h, s), l, delta)


# ── Step 2+3: Background with temperature contrast and L-contrast ─────────────

def _pick_bg(pool: dict, cat_l: float, cat_hue: float,
             max_tries: int = 30, min_delta: float = 15.0) -> tuple[str, tuple]:
    """
    Pick a background that:
      - Prefers the opposite temperature to the cat (warm cat → cool bg)
      - Has ΔL ≥ min_delta with the cat for visibility

    min_delta=8 for tonal (chroma contrast covers some lightness overlap),
    min_delta=15 for noir (dark cat needs a clearly lighter bg to read).

    Falls back gracefully: first drops temperature preference,
    then drops L-contrast, if the pool is too narrow.
    """
    preferred_temp = "cool" if temperature(cat_hue) == "warm" else "warm"

    # Pass 1: temperature match + L-contrast
    for _ in range(max_tries):
        name, rgb = _sample_bg(pool)
        bg_l = WAALS.get(name, (0, 0, 0))[2]
        bg_h = WAALS.get(name, (0, 0, 0))[0]
        if _l_contrast_ok(cat_l, bg_l, min_delta) and temperature(bg_h) == preferred_temp:
            return name, rgb

    # Pass 2: L-contrast only (drop temperature preference)
    for _ in range(max_tries):
        name, rgb = _sample_bg(pool)
        bg_l = WAALS.get(name, (0, 0, 0))[2]
        if _l_contrast_ok(cat_l, bg_l, min_delta):
            return name, rgb

    # Pass 3: any bg (pool may be too narrow)
    return _sample_bg(pool)


# ── Step 4+5: Eyes with hue accent and S boost ───────────────────────────────

def _pick_eye(pool: dict, cat_hue: float, max_tries: int = 30) -> tuple[str, tuple]:
    """
    Pick eyes that:
      - Are 60–180° from cat hue (avoids analogous muddle, maximises accent)
      - Have S boosted ~15% to compensate for size-based chroma loss (Gurney)

    Falls back to any eye from the pool if no accent found.
    """
    for _ in range(max_tries):
        name = random.choice(list(pool.keys()))
        h, s, l = WAALS[name]
        if _eye_is_accent(cat_hue, h):
            capped_s  = _cmyk_safe_s(h, s)
            boosted_s = min(100.0, capped_s * 1.15)
            return name, _sample_hsl(h, boosted_s, l, _EYE_DELTA)

    # Fallback: any eye — still cap + boost S
    name = random.choice(list(pool.keys()))
    h, s, l = WAALS[name]
    capped_s  = _cmyk_safe_s(h, s)
    boosted_s = min(100.0, capped_s * 1.15)
    return name, _sample_hsl(h, boosted_s, l, _EYE_DELTA)


# ── Core pick functions ───────────────────────────────────────────────────────

def _pick_tonal() -> tuple:
    """
    Pick colors for a tonal cat (light, warm side of palette).

    Order: cat → bg (temp contrast + L-contrast) → eyes (hue accent + S boost)
    Returns: (cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name)
    """
    # Step 1: Cat (with CMYK S cap for green/cyan hues)
    cat_name, cat_rgb = _sample_cat(TONAL_CAT_POOL, _CAT_DELTA)
    cat_h, _, cat_l   = WAALS.get(cat_name, (0, 0, 0))

    # Steps 2+3: Background — softer threshold (S contrast covers lightness overlap)
    bg_name, bg_rgb = _pick_bg(TONAL_BG_POOL, cat_l, cat_h, min_delta=8)

    # Steps 4+5: Eyes
    eye_name, eye_rgb = _pick_eye(TONAL_EYE_POOL, cat_h)

    return cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name


def _pick_noir() -> tuple:
    """
    Pick colors for a noir cat (dark, cool side of palette).

    Order: cat → bg (temp contrast + L-contrast) → eyes (hue accent + S boost)
    Returns: (cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name)
    """
    # Step 1: Cat (with CMYK S cap for green/cyan hues)
    cat_name, cat_rgb = _sample_cat(NOIR_CAT_POOL, _CAT_DELTA)
    cat_h, _, cat_l   = WAALS.get(cat_name, (0, 0, 0))

    # Steps 2+3: Background — min_delta=10 (achievable for all noir cats vs pool max L=45)
    bg_name, bg_rgb = _pick_bg(NOIR_BG_POOL, cat_l, cat_h, min_delta=10)

    # Steps 4+5: Eyes
    eye_name, eye_rgb = _pick_eye(NOIR_EYE_POOL, cat_h)

    return cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name


# ── Public selectors ──────────────────────────────────────────────────────────

def pick_pair_colors() -> tuple:
    """
    Pick colors for a tonal/noir pair.

    katt_1 = tonal  (light + warm)
    katt_2 = noir   (dark + cool)

    Also guarantees ≥60° hue distance between the two cats when both
    are chromatic — avoids near-identical hue combinations.

    Returns: (tonal_combo, noir_combo)
    Each combo: (cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name)
    """
    tonal     = _pick_tonal()
    katt1_hsl = WAALS.get(tonal[1], (0, 0, 0))

    for _ in range(30):
        noir      = _pick_noir()
        katt2_hsl = WAALS.get(noir[1], (0, 0, 0))

        both_chromatic = katt1_hsl[1] > 10 and katt2_hsl[1] > 10
        if not both_chromatic or hue_dist(katt1_hsl[0], katt2_hsl[0]) >= 60:
            break

    return tonal, noir


def pick_collection_colors() -> list:
    """
    Pick 3 color combos for a collection.
    Applies the same 5-step selection logic per combo.
    Ensures no two combos share the same cat anchor color.

    Returns: list of 3 combos
    Each combo: (cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name)
    """
    all_cats  = {**TONAL_CAT_POOL, **NOIR_CAT_POOL}
    used_cats = []
    combos    = []

    for _ in range(3):
        cat_name, cat_rgb = _sample_from(all_cats, _CAT_DELTA)
        while cat_name in used_cats:
            cat_name, cat_rgb = _sample_from(all_cats, _CAT_DELTA)

        cat_h, _, cat_l = WAALS.get(cat_name, (0, 0, 0))
        bg_pool  = TONAL_BG_POOL if cat_l > 50 else NOIR_BG_POOL
        eye_pool = TONAL_EYE_POOL if cat_l > 50 else NOIR_EYE_POOL

        bg_name,  bg_rgb  = _pick_bg(bg_pool, cat_l, cat_h)
        eye_name, eye_rgb = _pick_eye(eye_pool, cat_h)

        combos.append((cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name))
        used_cats.append(cat_name)

    return combos
