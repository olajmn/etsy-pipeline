"""
pipeline/mockup/calibrate.py — Frame calibration web app.

Click two corners to place, then drag each corner independently (skew).
Saves per-template corner coords to pipeline/mockup/calibration.json.

Run from project root:
    python3 pipeline/mockup/calibrate.py
Then open http://localhost:5001
"""
import json
import shutil
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

TEMPLATES_DIR = Path("assets/mockup-templates")
PRODUCTS_DIR  = Path("products")
CALIB_FILE    = Path("pipeline/mockup/calibration.json")

app = Flask(__name__, template_folder="html_interface")

_bounds_cache = {}


def _load_calibration() -> dict:
    return json.loads(CALIB_FILE.read_text()) if CALIB_FILE.exists() else {}


def _save_calibration(data: dict):
    CALIB_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _get_bounds(slug: str, psd_path: Path) -> list[dict]:
    """Return bounds for each smart object in the PSD. Cached by slug."""
    if slug in _bounds_cache:
        return _bounds_cache[slug]
    try:
        from psd_tools import PSDImage
        psd   = PSDImage.open(str(psd_path))
        smart = [l for l in psd if l.kind == "smartobject"]
        if smart:
            result = [{"top": f.top, "left": f.left, "bottom": f.bottom, "right": f.right,
                       "psd_w": psd.width, "psd_h": psd.height} for f in smart]
            _bounds_cache[slug] = result
            return result
    except Exception as e:
        print(f"  bounds error {psd_path.name}: {e}")
    _bounds_cache[slug] = []
    return []


def _get_png_size(slug: str) -> tuple[int, int]:
    """Get dimensions of the flat PNG template."""
    from PIL import Image as PilImage
    flat_png = TEMPLATES_DIR / "all_mockuptemplates" / f"{slug}.png"
    if flat_png.exists():
        with PilImage.open(flat_png) as im:
            return im.size
    return (1000, 1000)


def _get_templates() -> list[dict]:
    calib     = _load_calibration()
    templates = []
    for jf in [TEMPLATES_DIR / "all_segments.json"]:
        try:
            for entry in json.loads(jf.read_text()):
                n_frames = entry.get("frames", 1)
                slug     = entry["template"]
                psd_path = TEMPLATES_DIR / entry["path"]
                flat_png = TEMPLATES_DIR / "all_mockuptemplates" / f"{slug}.png"
                png_path = flat_png if flat_png.exists() else psd_path.with_suffix(".png")
                if png_path.exists():
                    cal = calib.get(slug, {})
                    if n_frames == 1:
                        frames_done   = 1 if "tl" in cal else 0
                        is_calibrated = frames_done == 1
                    else:
                        cal_frames    = cal.get("frames", [])
                        frames_done   = sum(1 for f in cal_frames if f and "tl" in f)
                        is_calibrated = frames_done == n_frames
                    templates.append({
                        "slug":        slug,
                        "path":        entry["path"],
                        "set":         entry.get("set", slug),
                        "frames":      n_frames,
                        "frames_done": frames_done,
                        "cal_frames":  cal.get("frames", []) if n_frames > 1 else [],
                        "calibrated":  is_calibrated,
                        "active":      entry.get("active", True),
                        "flagged":     entry.get("flagged", False),
                        "not_sure":    entry.get("not_sure", False),
                        "has_fg":      entry.get("has_fg", False),
                        "skipped":     entry.get("skipped", False),
                    })
        except Exception:
            pass
    return templates


@app.route("/")
def index():
    return render_template("calibrate.html")


@app.route("/api/templates")
def api_templates():
    return jsonify(_get_templates())


@app.route("/api/template/<slug>/image")
def api_image(slug):
    for jf in sorted(TEMPLATES_DIR.rglob("*.json")):
        try:
            for entry in json.loads(jf.read_text()):
                if entry.get("template") == slug:
                    flat_png = TEMPLATES_DIR / "all_mockuptemplates" / f"{slug}.png"
                    png = flat_png if flat_png.exists() else (TEMPLATES_DIR / entry["path"]).with_suffix(".png")
                    if png.exists():
                        return send_file(png.resolve(), mimetype="image/png")
        except Exception:
            pass
    return "Not found", 404


@app.route("/api/template/<slug>/bounds")
def api_bounds(slug):
    frame_idx = request.args.get("frame_idx", None, type=int)
    calib     = _load_calibration()
    for jf in sorted(TEMPLATES_DIR.rglob("*.json")):
        try:
            for entry in json.loads(jf.read_text()):
                if entry.get("template") != slug:
                    continue
                n_frames     = entry.get("frames", 1)
                bounds_list  = _get_bounds(slug, TEMPLATES_DIR / entry["path"])

                if frame_idx is None or n_frames == 1:
                    b = bounds_list[0] if bounds_list else None
                    if not b:
                        psd_w, psd_h = _get_png_size(slug)
                        b = {"left": 0, "top": 0, "right": psd_w, "bottom": psd_h,
                             "psd_w": psd_w, "psd_h": psd_h}
                    cal = calib.get(slug, {})
                    if "tl" in cal:
                        corners = cal
                    elif cal:
                        corners = {
                            "tl": [b["left"]  + cal.get("left", 0),  b["top"]    + cal.get("top", 0)],
                            "tr": [b["right"] - cal.get("right", 0), b["top"]    + cal.get("top", 0)],
                            "bl": [b["left"]  + cal.get("left", 0),  b["bottom"] - cal.get("bottom", 0)],
                            "br": [b["right"] - cal.get("right", 0), b["bottom"] - cal.get("bottom", 0)],
                        }
                    else:
                        corners = {"tl": [b["left"], b["top"]], "tr": [b["right"], b["top"]],
                                   "bl": [b["left"], b["bottom"]], "br": [b["right"], b["bottom"]]}
                    return jsonify({**b, "corners": corners})
                else:
                    # Multi-frame: return bounds for the specific frame
                    b = bounds_list[frame_idx] if frame_idx < len(bounds_list) else None
                    if b:
                        psd_w, psd_h = b["psd_w"], b["psd_h"]
                        base = b
                    else:
                        psd_w, psd_h = _get_png_size(slug)
                        fw   = psd_w // n_frames
                        x0   = frame_idx * fw
                        base = {"left": x0, "top": 0, "right": x0 + fw, "bottom": psd_h,
                                "psd_w": psd_w, "psd_h": psd_h}

                    cal        = calib.get(slug, {})
                    cal_frames = cal.get("frames", [])
                    if frame_idx < len(cal_frames) and cal_frames[frame_idx] and "tl" in cal_frames[frame_idx]:
                        corners = cal_frames[frame_idx]
                    else:
                        corners = {"tl": [base["left"],  base["top"]],
                                   "tr": [base["right"], base["top"]],
                                   "bl": [base["left"],  base["bottom"]],
                                   "br": [base["right"], base["bottom"]]}
                    return jsonify({**base, "corners": corners})
        except Exception:
            pass
    return jsonify({"error": "not found"}), 404


@app.route("/api/sample-print")
def api_sample_print():
    for p in sorted(PRODUCTS_DIR.rglob("layered_*.png")):
        return send_file(p.resolve(), mimetype="image/png")
    return "Not found", 404


@app.route("/api/template/<slug>/calibrate", methods=["POST"])
def api_calibrate(slug):
    data        = request.json
    frame_idx   = data.pop("frame_idx", None)
    frame_count = data.pop("frame_count", 1)
    calib       = _load_calibration()

    if frame_idx is not None:
        # Multi-frame: save corners for one frame at a time
        entry = calib.get(slug, {})
        if "frames" not in entry:
            entry = {"frames": [None] * frame_count}
        while len(entry["frames"]) < frame_count:
            entry["frames"].append(None)
        entry["frames"][frame_idx] = data
        calib[slug]  = entry
        fully_done   = all(f and "tl" in f for f in entry["frames"])
    else:
        # Single-frame
        calib[slug] = data
        fully_done  = True

    _save_calibration(calib)

    if fully_done:
        src = TEMPLATES_DIR / "all_mockuptemplates" / f"{slug}.png"
        dst = TEMPLATES_DIR / "mockuptemplates_calibrated" / "general" / f"{slug}.png"
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    return jsonify({"ok": True, "fully_done": fully_done})


@app.route("/api/template/<slug>/skip", methods=["POST"])
def api_skip(slug):
    all_file = TEMPLATES_DIR / "all_segments.json"
    entries  = json.loads(all_file.read_text())
    for e in entries:
        if e["template"] == slug:
            e["skipped"] = True
    all_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    return jsonify({"ok": True})


@app.route("/api/template/<slug>/not_sure", methods=["POST"])
def api_not_sure(slug):
    all_file = TEMPLATES_DIR / "all_segments.json"
    entries  = json.loads(all_file.read_text())
    for e in entries:
        if e["template"] == slug:
            e["not_sure"] = not e.get("not_sure", False)
    all_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    not_sure = next(e.get("not_sure", False) for e in entries if e["template"] == slug)
    return jsonify({"ok": True, "not_sure": not_sure})


@app.route("/api/template/<slug>/set_frames", methods=["POST"])
def api_set_frames(slug):
    n        = request.json.get("frames", 1)
    n        = max(1, int(n))
    all_file = TEMPLATES_DIR / "all_segments.json"
    entries  = json.loads(all_file.read_text())
    for e in entries:
        if e["template"] == slug:
            e["frames"] = n
    all_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    return jsonify({"ok": True, "frames": n})


@app.route("/api/template/<slug>/fg", methods=["POST"])
def api_fg(slug):
    all_file = TEMPLATES_DIR / "all_segments.json"
    entries  = json.loads(all_file.read_text())
    for e in entries:
        if e["template"] == slug:
            e["has_fg"] = not e.get("has_fg", False)
    all_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    has_fg = next(e.get("has_fg", False) for e in entries if e["template"] == slug)
    return jsonify({"ok": True, "has_fg": has_fg})


@app.route("/api/template/<slug>/flag", methods=["POST"])
def api_flag(slug):
    all_file = TEMPLATES_DIR / "all_segments.json"
    entries  = json.loads(all_file.read_text())
    for e in entries:
        if e["template"] == slug:
            e["flagged"] = not e.get("flagged", False)
    all_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    flagged = next(e.get("flagged", False) for e in entries if e["template"] == slug)
    return jsonify({"ok": True, "flagged": flagged})


@app.route("/api/template/<slug>/deactivate", methods=["POST"])
def api_deactivate(slug):
    all_file = TEMPLATES_DIR / "all_segments.json"
    entries  = json.loads(all_file.read_text())
    for e in entries:
        if e["template"] == slug:
            e["active"] = False
    all_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False))

    # Move calibrated PNG to deactivated/ subfolder
    calibrated_dir  = TEMPLATES_DIR / "mockuptemplates_calibrated"
    deactivated_dir = calibrated_dir / "deactivated"
    deactivated_dir.mkdir(parents=True, exist_ok=True)
    for png in calibrated_dir.rglob(f"{slug}.png"):
        if "deactivated" not in png.parts:
            shutil.move(str(png), str(deactivated_dir / png.name))

    deleted = 0
    for mockup_file in PRODUCTS_DIR.rglob(f"*{slug}*.png"):
        mockup_file.unlink()
        deleted += 1

    return jsonify({"ok": True, "deleted": deleted})


@app.route("/api/template/<slug>/generate", methods=["POST"])
def api_generate(slug):
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        import importlib
        import mockup
        importlib.reload(mockup)

        # Find the PSD path for this slug
        all_segs = json.loads((TEMPLATES_DIR / "all_segments.json").read_text())
        entry = next((e for e in all_segs if e["template"] == slug), None)
        if not entry:
            return jsonify({"error": "template not found"}), 404

        psd_path = TEMPLATES_DIR / entry["path"]

        # Find a test print to use from set-* dirs
        products_dir = Path("products")
        print_path = next(
            (p for col in sorted(products_dir.iterdir()) if col.is_dir()
             for p in sorted(col.glob("_print_portrait_*.png"))),
            None
        )
        if not print_path:
            return jsonify({"error": "no test print found"}), 404

        out_dir = Path("products/previews")
        out_dir.mkdir(exist_ok=True)

        calib     = json.loads((Path("pipeline/mockup/calibration.json")).read_text())
        cal_entry = calib.get(slug, {})
        if not cal_entry:
            return jsonify({"error": "Ikke kalibrert — kalibrere hjørnene først"}), 400

        n_frames = entry.get("frames", 1)
        if n_frames > 1:
            cal_frames = cal_entry.get("frames", [])
            if len(cal_frames) < n_frames or not all(f and "tl" in f for f in cal_frames):
                done = sum(1 for f in cal_frames if f and "tl" in f)
                return jsonify({"error": f"Kalibrér alle rammer først ({done}/{n_frames} ferdig)"}), 400
            results = mockup._generate_psd_multi(
                Path("products"), psd_path, out_dir,
                prints=[print_path] * n_frames,
            )
        else:
            results = mockup._generate_psd_single(print_path, psd_path, out_dir)
        if not results:
            return jsonify({"error": "generation failed"}), 500

        import subprocess
        subprocess.Popen(["open", str(results[0])])
        return jsonify({"ok": True, "file": str(results[0])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\nMockup Calibrator -> http://localhost:5001\n")
    app.run(port=5001, debug=False)
