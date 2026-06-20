"""
pipeline/mockup/mockup.py — Generates mockups for each collection.

Supports two template types:
  PNG+JSON: perspective-warped frames (e.g. angled shelf). Needs calibration.
  PSD:      smart-object frames (e.g. straight-on room scene). No calibration.

Run from project root:
    python3 pipeline/mockup/mockup.py collection-9
    python3 pipeline/mockup/mockup.py            # all collections
"""
import json
import random
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

PRODUCTS_DIR  = Path("products")
TEMPLATES_DIR = Path("assets/mockup-templates")

FRAME_PADDING     = 1
IMAGE_GLOB        = "layered_*.png"
CALIB_FILE        = Path("pipeline/mockup/calibration.json")
ALL_SEGMENTS_FILE = TEMPLATES_DIR / "all_segments.json"

_calibration:   dict | None = None
_segments_cache: list | None = None
_entry_lookup:  dict | None = None

def _load_calibration() -> dict:
    global _calibration
    if _calibration is None:
        _calibration = json.loads(CALIB_FILE.read_text()) if CALIB_FILE.exists() else {}
    return _calibration

# Background color → warmth (used to match prints to room scenes)
BG_WARMTH = {
    "warm_cream":  "warm",
    "blush":       "warm",
    "pale_yellow": "warm",
    "terracotta":  "warm",
    "dusty_blue":  "cool",
    "lavender":    "cool",
    "navy":        "cool",
    "soft_sage":   "neutral",
    "stone":       "neutral",
    "forest":      "neutral",
}


# ── Helpers ────────────────────────────────────────────────────────────────

def _slug(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "_", path.stem.lower()).strip("_")


def _cat_name(print_path: Path) -> str:
    desc = print_path.parent / "description.json"
    if desc.exists():
        name = json.loads(desc.read_text()).get("cat_name", "")
        return name.lower().replace(" ", "_")
    return ""


def _collect_prints(collection_dir: Path, n_frames: int) -> list[Path]:
    layered = sorted(collection_dir.rglob(IMAGE_GLOB))
    if n_frames <= 1:
        return layered
    multi = sorted(collection_dir.rglob("multi_portrett_*.png"))
    # Pick one format randomly — never mix layered and multi in the same mockup
    return random.choice([layered, multi]) if multi else layered


def _print_warmth(print_path: Path) -> str:
    """Detect warmth from background colors in the layered filename."""
    m = re.match(
        r"layered_[a-z]+_[a-z_]+eyes_([a-z_]+)_([a-z_]+)_[a-f0-9]+$",
        print_path.stem,
    )
    if m:
        for bg in (m.group(1), m.group(2)):
            if bg in BG_WARMTH:
                return BG_WARMTH[bg]
    return "neutral"


# ── Template selection via segments.json ───────────────────────────────────

def _load_all_segments() -> list[dict]:
    global _segments_cache
    if _segments_cache is None:
        if ALL_SEGMENTS_FILE.exists():
            _segments_cache = json.loads(ALL_SEGMENTS_FILE.read_text())
        else:
            entries = []
            for jf in sorted(TEMPLATES_DIR.rglob("*.json")):
                if jf.name == "all_segments.json":
                    continue
                try:
                    entries.extend(json.loads(jf.read_text()))
                except Exception:
                    pass
            _segments_cache = entries
    return _segments_cache


def _get_entry(rel_path: str) -> dict | None:
    """Look up a segments entry by its relative PSD path (e.g. 'Frame Design/PSD Mockup (1).psd')."""
    global _entry_lookup
    if _entry_lookup is None:
        _entry_lookup = {e["path"]: e for e in _load_all_segments()}
    return _entry_lookup.get(rel_path)


def _scale_corners(b: dict, png_w: int, png_h: int) -> dict:
    """Scale PSD-coord corners to PNG pixel coords (handles different PNG/PSD sizes)."""
    sx = png_w / b.get("psd_w", png_w)
    sy = png_h / b.get("psd_h", png_h)
    return {
        "tl": [b["tl"][0] * sx, b["tl"][1] * sy],
        "tr": [b["tr"][0] * sx, b["tr"][1] * sy],
        "bl": [b["bl"][0] * sx, b["bl"][1] * sy],
        "br": [b["br"][0] * sx, b["br"][1] * sy],
    }


def _pick_diverse(pool: list[dict], count: int, exclude_sets: set | None = None) -> list[dict]:
    """Pick `count` entries from pool with diverse set names, skipping exclude_sets."""
    seen = set(exclude_sets or [])
    pool = pool[:]
    random.shuffle(pool)
    selected = []
    for entry in pool:
        s = entry.get("set", "")
        if s not in seen:
            selected.append(entry)
            seen.add(s)
            if len(selected) >= count:
                break
    return selected


def _select_single(warmth: str, n: int = 6) -> list[Path]:
    """Pick N templates split ~evenly: matching warmth / contrast / random."""
    all_entries   = _load_all_segments()
    active_single = [e for e in all_entries if e.get("active") and e.get("frames") == 1]

    contrast_map  = {"warm": "cool", "cool": "warm"}
    contrast      = contrast_map.get(warmth)  # None for neutral

    matching  = [e for e in active_single if e.get("warmth") == warmth]
    contrasts = [e for e in active_single if e.get("warmth") == contrast] if contrast else active_single[:]

    n_each = n // 3       # 2 for n=6
    n_rest = n - n_each * 2  # 2 for n=6

    match_picks    = _pick_diverse(matching, n_each)
    used_sets      = {e.get("set", "") for e in match_picks}

    contrast_picks = _pick_diverse(contrasts, n_each, exclude_sets=used_sets)
    used_sets     |= {e.get("set", "") for e in contrast_picks}

    random_picks   = _pick_diverse(active_single, n_rest, exclude_sets=used_sets)

    selected = match_picks + contrast_picks + random_picks
    random.shuffle(selected)

    return [TEMPLATES_DIR / entry["path"] for entry in selected]


def _select_multi(n_frames: int, count: int = 1) -> list[Path]:
    """Pick `count` multi-frame templates with exactly n_frames."""
    all_entries = _load_all_segments()
    pool        = [e for e in all_entries if e.get("active") and e.get("frames") == n_frames]
    if not pool:
        return []
    return [TEMPLATES_DIR / e["path"] for e in random.sample(pool, min(count, len(pool)))]


# ── PNG + JSON approach (perspective warp) ─────────────────────────────────

def _load_frames(coords_path: Path) -> list[np.ndarray]:
    data = json.loads(coords_path.read_text())
    frames = []
    for f in data["frames"]:
        pts = np.float32([f["top_left"], f["top_right"], f["bottom_right"], f["bottom_left"]])
        frames.append(pts)
    return frames


def _inset_quad(pts: np.ndarray, pad: int) -> np.ndarray:
    centroid = pts.mean(axis=0)
    dirs     = centroid - pts
    norms    = np.linalg.norm(dirs, axis=1, keepdims=True)
    return pts + (dirs / norms) * pad


def _warp_print(print_path: Path, dst_pts: np.ndarray, canvas: np.ndarray) -> np.ndarray:
    img          = np.array(Image.open(print_path).convert("RGB"))
    img          = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    canvas_float = canvas.astype(np.float32) / 255.0
    inner_pts    = _inset_quad(dst_pts, FRAME_PADDING) if FRAME_PADDING > 0 else dst_pts
    h, w         = img.shape[:2]
    src_pts      = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    M            = cv2.getPerspectiveTransform(src_pts, inner_pts)
    warped       = cv2.warpPerspective(img, M, (canvas.shape[1], canvas.shape[0]))
    inner_mask   = np.zeros(canvas.shape[:2], dtype=np.uint8)
    cv2.fillPoly(inner_mask, [inner_pts.astype(np.int32)], 255)
    warped_float = warped.astype(np.float32) / 255.0
    inner_3ch    = inner_mask[:, :, np.newaxis] / 255.0
    blended      = warped_float * canvas_float
    result       = canvas_float * (1 - inner_3ch) + blended * inner_3ch
    return (result * 255).astype(np.uint8)


def _generate_png(collection_dir: Path, template_path: Path, mockups_dir: Path) -> list[Path]:
    template_json = template_path.with_suffix(".json")
    if not template_path.exists() or not template_json.exists():
        return []
    template_name = _slug(template_path)
    frames        = _load_frames(template_json)
    layered       = _collect_prints(collection_dir, len(frames))
    if not layered:
        return []
    template = cv2.imread(str(template_path))
    outputs  = []
    if len(frames) == 1:
        for print_path in layered:
            canvas = template.copy()
            canvas = _warp_print(print_path, frames[0], canvas)
            prefix = _cat_name(print_path)
            name   = f"{prefix}_{template_name}.png" if prefix else f"{template_name}.png"
            out    = mockups_dir / name
            cv2.imwrite(str(out), canvas)
            outputs.append(out)
    else:
        picks  = random.sample(layered, min(len(frames), len(layered)))
        canvas = template.copy()
        for i, dst_pts in enumerate(frames):
            if i < len(picks):
                canvas = _warp_print(picks[i], dst_pts, canvas)
        out = mockups_dir / f"{template_name}.png"
        cv2.imwrite(str(out), canvas)
        outputs.append(out)
    return outputs


# ── PSD approach (smart object, multiply blend) ────────────────────────────

def _multiply_blend(bg: np.ndarray, fg: np.ndarray) -> np.ndarray:
    bg_f = bg.astype(np.float32) / 255.0
    fg_f = fg.astype(np.float32) / 255.0
    return (fg_f * bg_f * 255).astype(np.uint8)


def _place_print(bg: np.ndarray, result: np.ndarray, frame, print_path: Path,
                 cal: dict | None = None) -> None:
    o      = cal or {}
    pad    = FRAME_PADDING
    ft     = frame.top    + pad + o.get("top", 0)
    fl     = frame.left   + pad + o.get("left", 0)
    fb     = frame.bottom - pad - o.get("bottom", 0)
    fr     = frame.right  - pad - o.get("right", 0)
    fw, fh = fr - fl, fb - ft

    src     = Image.open(print_path).convert("RGB")
    iw, ih  = src.size
    scale   = max(fw / iw, fh / ih)
    new_w   = int(iw * scale)
    new_h   = int(ih * scale)
    resized = src.resize((new_w, new_h), Image.LANCZOS)
    crop_x  = (new_w - fw) // 2
    crop_y  = (new_h - fh) // 2
    cropped = resized.crop((crop_x, crop_y, crop_x + fw, crop_y + fh))
    arr     = np.array(cropped)
    blended = _multiply_blend(bg[ft:fb, fl:fr], arr)
    result[ft:fb, fl:fr] = blended


def _cover_crop(src_w: int, src_h: int, frame_w: float, frame_h: float):
    """Return (x0, y0, x1, y1) crop of source that fills frame — cover mode, centered."""
    src_ratio   = src_w / src_h
    frame_ratio = frame_w / frame_h
    if src_ratio > frame_ratio:
        # Source wider than frame → crop sides
        crop_h = src_h
        crop_w = int(src_h * frame_ratio)
    else:
        # Source taller than frame → crop top/bottom
        crop_w = src_w
        crop_h = int(src_w / frame_ratio)
    x0 = (src_w - crop_w) // 2
    y0 = (src_h - crop_h) // 2
    return x0, y0, x0 + crop_w, y0 + crop_h


def _place_print_quad(bg: np.ndarray, result: np.ndarray, corners: dict,
                      print_path: Path, white_fill: bool = False) -> None:
    """Place print into a calibrated quadrilateral using perspective warp."""
    tl, tr, bl, br = corners["tl"], corners["tr"], corners["bl"], corners["br"]

    src_img         = np.array(Image.open(print_path).convert("RGB"))
    h_src, w_src    = src_img.shape[:2]
    bg_h, bg_w      = bg.shape[:2]

    # Cover mode: crop source to match frame aspect ratio, then fill frame entirely
    dst_w = max(np.linalg.norm(np.array(tr) - np.array(tl)),
                np.linalg.norm(np.array(br) - np.array(bl)))
    dst_h = max(np.linalg.norm(np.array(bl) - np.array(tl)),
                np.linalg.norm(np.array(br) - np.array(tr)))
    x0, y0, x1, y1 = _cover_crop(w_src, h_src, dst_w, dst_h)
    src_img = src_img[y0:y1, x0:x1]
    h_src, w_src = src_img.shape[:2]

    # Pre-resize to ~4x destination to avoid large downscale in warpPerspective
    scale = min(dst_w * 4 / w_src, dst_h * 4 / h_src, 1.0)
    if scale < 0.9:
        new_w = max(int(w_src * scale), 1)
        new_h = max(int(h_src * scale), 1)
        src_img = cv2.resize(src_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        h_src, w_src = src_img.shape[:2]

    src_pts = np.float32([[0, 0], [w_src, 0], [w_src, h_src], [0, h_src]])
    dst_pts = np.float32([tl, tr, br, bl])   # TL TR BR BL — clockwise

    M      = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(src_img, M, (bg_w, bg_h), flags=cv2.INTER_CUBIC,
                                 borderValue=(255, 255, 255))

    mask = np.zeros((bg_h, bg_w), dtype=np.uint8)
    cv2.fillPoly(mask, [dst_pts.astype(np.int32)], 255)
    mask = cv2.GaussianBlur(mask, (3, 3), 1)  # anti-alias the edge

    if white_fill:
        bg_blend = bg.copy()
        cv2.fillPoly(bg_blend, [dst_pts.astype(np.int32)], (255, 255, 255))
    else:
        bg_blend = bg

    blended = _multiply_blend(bg_blend, warped)
    mask_3  = mask[:, :, np.newaxis] / 255.0
    result[:] = (blended * mask_3 + result * (1 - mask_3)).astype(np.uint8)


def _open_psd_bg(template_path: Path):
    from psd_tools import PSDImage
    psd          = PSDImage.open(str(template_path))
    bg_layers    = [l for l in psd if l.kind != "smartobject"]
    bg_pil       = bg_layers[0].composite() if len(bg_layers) == 1 else psd.composite()
    bg           = np.array(bg_pil.convert("RGB"))
    smart_layers = [l for l in psd if l.kind == "smartobject"]
    return bg, smart_layers


def _generate_psd_single(print_path: Path, template_path: Path, mockups_dir: Path) -> list[Path]:
    """Generate one mockup using PNG+JSON bounds when available, PSD as fallback."""
    rel_path = str(template_path.relative_to(TEMPLATES_DIR))
    entry    = _get_entry(rel_path)
    slug     = entry["template"] if entry else _slug(template_path)
    cal      = _load_calibration().get(slug, {})
    flat_png = TEMPLATES_DIR / "all_mockuptemplates" / f"{slug}.png"
    png_path = flat_png if flat_png.exists() else template_path.with_suffix(".png")
    raw_b    = (entry.get("bounds") or [{}])[0] if entry else {}

    if png_path.exists() and ("tl" in cal or raw_b):
        # Fast path: PNG directly, no psd_tools
        OUTPUT_SIZE = 3000
        bg_pil      = Image.open(png_path).convert("RGB")
        orig_w, orig_h = bg_pil.size
        # Upscale template to OUTPUT_SIZE for a sharp composite
        bg_pil = bg_pil.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)
        bg     = np.array(bg_pil)
        png_h, png_w = bg.shape[:2]
        if "tl" in cal:
            corners = _scale_corners(
                {**cal, "psd_w": raw_b.get("psd_w", orig_w),
                        "psd_h": raw_b.get("psd_h", orig_h)},
                png_w, png_h,
            )
        else:
            corners = _scale_corners(
                {**raw_b, "psd_w": raw_b.get("psd_w", orig_w),
                          "psd_h": raw_b.get("psd_h", orig_h)},
                png_w, png_h,
            )
        result = bg.copy()
        white_fill = entry.get("flagged", False) if entry else False
        _place_print_quad(bg, result, corners, print_path, white_fill=white_fill)
        prefix = _cat_name(print_path)
        name   = f"{prefix}_{slug}.png" if prefix else f"{slug}.png"
        out    = mockups_dir / name
        Image.fromarray(result).save(str(out))
        return [out]

    # Fallback: PSD via psd_tools (until extract_bounds.py has run)
    if not template_path.exists():
        return []
    bg, smart_layers = _open_psd_bg(template_path)
    if not smart_layers:
        return []
    result = bg.copy()
    if "tl" in cal:
        _place_print_quad(bg, result, cal, print_path)
    else:
        _place_print(bg, result, smart_layers[0], print_path, cal=cal)
    prefix = _cat_name(print_path)
    name   = f"{prefix}_{slug}.png" if prefix else f"{slug}.png"
    out    = mockups_dir / name
    Image.fromarray(result).save(str(out))
    return [out]


def _generate_psd_multi(collection_dir: Path, template_path: Path, mockups_dir: Path,
                        prints: list[Path] | None = None, suffix: str = "") -> list[Path]:
    """Generate one mockup for a multi-frame template. Uses calibrated corners when available."""
    slug       = _slug(template_path)
    cal        = _load_calibration().get(slug, {})
    cal_frames = cal.get("frames", [])
    flat_png   = TEMPLATES_DIR / "all_mockuptemplates" / f"{slug}.png"

    if cal_frames and all(f and "tl" in f for f in cal_frames) and flat_png.exists():
        # Fast path: calibrated corners + flat PNG (same as single-frame)
        entry  = _get_entry(str(template_path.relative_to(TEMPLATES_DIR)))
        raw_b  = (entry.get("bounds") or [{}])[0] if entry else {}
        OUTPUT_SIZE = 3000
        bg_pil = Image.open(flat_png).convert("RGB")
        orig_w, orig_h = bg_pil.size
        bg_pil = bg_pil.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)
        bg     = np.array(bg_pil)
        png_h, png_w = bg.shape[:2]

        pool   = prints if prints is not None else _collect_prints(collection_dir, len(cal_frames))
        if not pool:
            return []
        picks  = random.sample(pool, min(len(cal_frames), len(pool)))
        result = bg.copy()
        white_fill = entry.get("flagged", False) if entry else False
        for i, frame_cal in enumerate(cal_frames):
            if i < len(picks):
                corners = _scale_corners(
                    {**frame_cal, "psd_w": raw_b.get("psd_w", orig_w),
                                  "psd_h": raw_b.get("psd_h", orig_h)},
                    png_w, png_h,
                )
                _place_print_quad(bg, result, corners, picks[i], white_fill=white_fill)
        name = f"{slug}{suffix}.png"
        out  = mockups_dir / name
        Image.fromarray(result).save(str(out))
        return [out]

    # Fallback: PSD smart objects (uncalibrated)
    if not template_path.exists():
        return []
    bg, smart_layers = _open_psd_bg(template_path)
    if not smart_layers:
        return []
    pool = prints if prints is not None else _collect_prints(collection_dir, len(smart_layers))
    if not pool:
        return []
    picks  = random.sample(pool, min(len(smart_layers), len(pool)))
    result = bg.copy()
    for i, frame in enumerate(smart_layers):
        if i < len(picks):
            _place_print(bg, result, frame, picks[i])
    name = f"{slug}{suffix}.png"
    out  = mockups_dir / name
    Image.fromarray(result).save(str(out))
    return [out]


# ── Main entry ─────────────────────────────────────────────────────────────

def generate_mockup(collection_dir: Path) -> list[Path]:
    mockups_dir = collection_dir / "mockups"
    mockups_dir.mkdir(exist_ok=True)
    (mockups_dir / "good").mkdir(exist_ok=True)
    (mockups_dir / "good" / "generally_good").mkdir(exist_ok=True)
    (mockups_dir / "good" / "superliked").mkdir(exist_ok=True)
    (mockups_dir / "good" / "fix_placement").mkdir(exist_ok=True)
    (mockups_dir / "bad").mkdir(exist_ok=True)
    (mockups_dir / "bad" / "bad_generated").mkdir(exist_ok=True)
    (mockups_dir / "bad" / "bad_match").mkdir(exist_ok=True)
    (mockups_dir / "bad" / "no_use").mkdir(exist_ok=True)
    all_outputs = []

    # Single-frame: 6 per print, matched to scene warmth
    for pair_dir in sorted(collection_dir.glob("pair-*")):
        for print_path in sorted(pair_dir.glob("layered_*.png")):
            warmth = _print_warmth(print_path)
            for tpl_path in _select_single(warmth, n=6):
                try:
                    all_outputs.extend(_generate_psd_single(print_path, tpl_path, mockups_dir))
                except Exception as e:
                    print(f"    ERROR {tpl_path.name}: {e}")

    # 2-frame: 1 mockup (random format)
    for tpl_path in _select_multi(2, count=1):
        try:
            all_outputs.extend(_generate_psd_multi(collection_dir, tpl_path, mockups_dir))
        except Exception as e:
            print(f"    ERROR {tpl_path.name}: {e}")

    # 3-frame: 2 mockups — one layered, one multi
    layered_prints  = sorted(collection_dir.rglob(IMAGE_GLOB))
    multi_prints    = sorted(collection_dir.rglob("multi_portrett_*.png"))
    three_tpls      = _select_multi(3, count=2)
    if len(three_tpls) == 1:
        three_tpls = three_tpls * 2  # reuse same template for both formats
    for tpl_path, prints, suffix in zip(
        three_tpls,
        [layered_prints, multi_prints],
        ["_layered", "_multi"],
    ):
        try:
            all_outputs.extend(_generate_psd_multi(collection_dir, tpl_path, mockups_dir,
                                                    prints=prints, suffix=suffix))
        except Exception as e:
            print(f"    ERROR {tpl_path.name}: {e}")

    return all_outputs


def _build_lookups() -> tuple[dict, dict]:
    """Build cat_slug→prints and template_slug→psd_path lookups."""
    cat_lookup = {}
    for desc in sorted(PRODUCTS_DIR.rglob("description.json")):
        data = json.loads(desc.read_text())
        cat  = data.get("cat_name", "")
        if not cat:
            continue
        slug    = cat.lower().replace(" ", "_")
        pair    = desc.parent
        layered = sorted(pair.glob("layered_*.png"))
        multi   = sorted(pair.glob("multi_portrett_*.png"))
        if layered:
            cat_lookup[slug] = {
                "layered": layered[0],
                "multi":   multi[0] if multi else layered[0],
                "col_dir": pair.parent,
            }
    tpl_lookup = {_slug(p): p for p in sorted(TEMPLATES_DIR.rglob("*.psd"))}
    return cat_lookup, tpl_lookup


def _parse_mockup_stem(stem: str, cat_lookup: dict) -> tuple[str | None, str, str]:
    """Returns (cat_slug, tpl_slug, fmt) from a mockup filename stem."""
    fmt = ""
    for sfx in ("_layered", "_multi"):
        if stem.endswith(sfx):
            stem = stem[:-len(sfx)]
            fmt  = sfx[1:]
            break
    for cat_slug in sorted(cat_lookup, key=len, reverse=True):
        if stem.startswith(cat_slug + "_"):
            return cat_slug, stem[len(cat_slug) + 1:], fmt
    return None, stem, fmt


def _find_col_dir(path: Path) -> Path | None:
    for p in path.parents:
        if p.parent == PRODUCTS_DIR and p.name.startswith("collection-"):
            return p
    return None


def repad_all() -> None:
    """Regenerate every mockup (sorted + unsorted) in place with current FRAME_PADDING."""
    cat_lookup, tpl_lookup = _build_lookups()
    SORT_DIRS = {"generally_good", "superliked", "fix_placement",
                 "bad_generated", "bad_match", "no_use"}

    for png in sorted(PRODUCTS_DIR.rglob("mockups/**/*.png")):
        if not png.is_file():
            continue

        cat_slug, tpl_slug, fmt = _parse_mockup_stem(png.stem, cat_lookup)
        tpl_path = tpl_lookup.get(tpl_slug)
        if not tpl_path:
            print(f"  skip {png.name} — template ikke funnet")
            continue

        try:
            if cat_slug and cat_slug in cat_lookup:
                info       = cat_lookup[cat_slug]
                print_path = info["multi"] if fmt == "multi" else info["layered"]
                outs       = _generate_psd_single(print_path, tpl_path, png.parent)
                if outs and outs[0] != png:
                    outs[0].replace(png)
            else:
                col_dir = _find_col_dir(png)
                if col_dir:
                    prints = (sorted(col_dir.rglob("multi_portrett_*.png"))
                              if fmt == "multi" else sorted(col_dir.rglob(IMAGE_GLOB)))
                    outs = _generate_psd_multi(col_dir, tpl_path, png.parent,
                                               prints=prints, suffix=f"_{fmt}" if fmt else "")
                    if outs and outs[0] != png:
                        outs[0].replace(png)
            print(f"  ✓ {png.parent.name}/{png.name}")
        except Exception as e:
            print(f"  ERROR {png.name}: {e}")


def _find_collections() -> list[Path]:
    return sorted(PRODUCTS_DIR.glob("collection-*"))


def main():
    if "--repad" in sys.argv:
        print(f"Regenererer alle mockups med FRAME_PADDING={FRAME_PADDING}...\n")
        repad_all()
        return

    args   = [a for a in sys.argv[1:] if not a.startswith("--")]
    target = args[0] if args else None
    dirs   = [PRODUCTS_DIR / target] if target else _find_collections()

    for col_dir in dirs:
        if not col_dir.exists():
            print(f"Not found: {col_dir}")
            continue
        try:
            outputs = generate_mockup(col_dir)
            for out in outputs:
                print(f"{col_dir.name} → {out.name}")
        except Exception as e:
            print(f"{col_dir.name}: ERROR — {e}")


if __name__ == "__main__":
    main()
