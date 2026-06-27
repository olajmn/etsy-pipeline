"""
form_builder.py — Layout and structure for the cat bot.

Answers the question: "what does the image look like?"
(canvas size, silhouette selection, cat positions)

No colors here. All color logic lives in color_selector.py.
All rendering lives in image_builder.py.
"""
import random
from pathlib import Path
from PIL import Image


SILHOUETTES_DIR = Path("assets/silhouettes")
CAT_TEMPLATE    = Path("assets/precedents/portrait.png")

CANVAS_SIZES = {
    "plakat":   (1500, 2000),
    "kvadrat":  (1080, 1080),
    "portrett": (1080, 1350),
    "story":    (1080, 1920),
}

CAT_SCALE          = 0.55
CAT_SCALE_OVERRIDE = {"cat-3": 0.40}
LAYOUT_JITTER      = 0.05

LAYOUT_TEMPLATE = [
    (0.69, 0.20),   # zone 1: upper right
    (0.45, 0.50),   # zone 2: middle left
    (0.62, 0.80),   # zone 3: lower right
]

LAYOUT_TEMPLATE_H = [
    (0.18, 0.35),   # left
    (0.50, 0.55),   # center
    (0.82, 0.35),   # right
]


_silhouette_queue: list = []

def _pick_silhouette() -> Path:
    """Pick silhouettes in rotation — no repeats until all are used."""
    global _silhouette_queue
    if not _silhouette_queue:
        options = list(SILHOUETTES_DIR.glob("cat-*.png"))
        if not options:
            raise FileNotFoundError(f"No cat-*.png in {SILHOUETTES_DIR}")
        random.shuffle(options)
        _silhouette_queue = options
    return _silhouette_queue.pop()


def _push_apart(x, y, w, h, placed, gap=40):
    """Push (x, y) away from already-placed cats to avoid overlap."""
    for _ in range(100):
        moved = False
        for px, py, pw, ph in placed:
            if x < px + pw and x + w > px and y < py + ph + gap and y + h + gap > py:
                my_center    = y + h / 2
                their_center = py + ph / 2
                y = py + ph + gap if my_center >= their_center else py - h - gap
                moved = True
        if not moved:
            break
    return x, y


def plan_layered() -> dict:
    """
    Plan a layered portrait layout.

    Returns a dict with the geometry needed to build the image.
    No colors — just structure.

    Example output:
      {
        "template": Path("assets/precedents/portrait.png"),
        "width": 1080, "height": 1350,
        "split_y": 904
      }
    """
    with Image.open(CAT_TEMPLATE) as img:
        w, h = img.size
    return {
        "template": CAT_TEMPLATE,
        "width":    w,
        "height":   h,
        "split_y":  int(h * 0.6694),
    }


def plan_multi(canvas_size: str = "portrett") -> dict:
    """
    Plan a 3-cat multi layout.

    Returns a dict with the canvas size and a list of cat positions.
    No colors — just structure.

    Example output:
      {
        "width": 1080, "height": 1350,
        "cats": [
          {"silhouette": Path(...), "x": 100, "y": 200, "w": 400, "h": 600, "flip": True},
          ...
        ]
      }
    """
    silhouettes = sorted(SILHOUETTES_DIR.glob("cat-*.png"))
    if len(silhouettes) < 2:
        raise FileNotFoundError("Need at least 2 silhouettes in assets/silhouettes/")

    cw, ch   = CANVAS_SIZES.get(canvas_size, CANVAS_SIZES["portrett"])
    template = LAYOUT_TEMPLATE_H if cw >= ch else LAYOUT_TEMPLATE
    shuffled = silhouettes[:3]
    random.shuffle(shuffled)

    cats   = []
    placed = []

    for zone_idx, sil_path in enumerate(shuffled):
        with Image.open(sil_path) as img:
            orig_w, orig_h = img.size

        scale = CAT_SCALE_OVERRIDE.get(sil_path.stem, CAT_SCALE)
        new_w = int(cw * scale)
        new_h = int(orig_h * (new_w / orig_w))
        flip  = random.random() < 0.5

        cx_rel = template[zone_idx][0] + random.uniform(-LAYOUT_JITTER, LAYOUT_JITTER)
        cy_rel = template[zone_idx][1] + random.uniform(-LAYOUT_JITTER, LAYOUT_JITTER)
        x = int(cw * cx_rel) - new_w // 2
        y = int(ch * cy_rel) - new_h // 2
        x, y = _push_apart(x, y, new_w, new_h, placed)
        x = max(-new_w // 2, min(x, cw - new_w // 2))
        y = max(-new_h // 2, min(y, ch - new_h // 2))

        placed.append((x, y, new_w, new_h))
        cats.append({
            "silhouette": sil_path,
            "x": x, "y": y,
            "w": new_w, "h": new_h,
            "flip": flip,
        })

    return {
        "width":  cw,
        "height": ch,
        "cats":   cats,
    }
