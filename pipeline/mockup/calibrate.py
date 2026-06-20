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

from flask import Flask, Response, jsonify, request, send_file

PRODUCTS_DIR = Path("products")

TEMPLATES_DIR = Path("assets/mockup-templates")
PRODUCTS_DIR  = Path("products")
CALIB_FILE    = Path("pipeline/mockup/calibration.json")

app = Flask(__name__)

_bounds_cache = {}


def _load_calibration() -> dict:
    return json.loads(CALIB_FILE.read_text()) if CALIB_FILE.exists() else {}


def _save_calibration(data: dict):
    CALIB_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _get_bounds(slug: str, psd_path: Path) -> dict | None:
    if slug in _bounds_cache:
        return _bounds_cache[slug]
    try:
        from psd_tools import PSDImage
        psd   = PSDImage.open(str(psd_path))
        smart = [l for l in psd if l.kind == "smartobject"]
        if smart:
            f = smart[0]
            b = {"top": f.top, "left": f.left, "bottom": f.bottom, "right": f.right,
                 "psd_w": psd.width, "psd_h": psd.height}
            _bounds_cache[slug] = b
            return b
    except Exception as e:
        print(f"  bounds error {psd_path.name}: {e}")
    return None


def _get_templates() -> list[dict]:
    calib     = _load_calibration()
    templates = []
    for jf in [TEMPLATES_DIR / "all_segments.json"]:
        try:
            for entry in json.loads(jf.read_text()):
                if entry.get("frames") != 1:
                    continue
                slug     = entry["template"]
                psd_path = TEMPLATES_DIR / entry["path"]
                flat_png = TEMPLATES_DIR / "all_mockuptemplates" / f"{slug}.png"
                png_path = flat_png if flat_png.exists() else psd_path.with_suffix(".png")
                if png_path.exists():
                    templates.append({
                        "slug":       slug,
                        "path":       entry["path"],
                        "set":        entry.get("set", slug),
                        "calibrated": slug in calib,
                        "active":     entry.get("active", True),
                        "flagged":    entry.get("flagged", False),
                        "skipped":    entry.get("skipped", False),
                    })
        except Exception:
            pass
    return templates


@app.route("/")
def index():
    return Response(HTML, mimetype="text/html")


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
    calib = _load_calibration()
    for jf in sorted(TEMPLATES_DIR.rglob("*.json")):
        try:
            for entry in json.loads(jf.read_text()):
                if entry.get("template") == slug:
                    psd = TEMPLATES_DIR / entry["path"]
                    b   = _get_bounds(slug, psd)
                    if b:
                        cal = calib.get(slug, {})
                        if "tl" in cal:
                            corners = cal
                        elif cal:
                            # convert old offset format → corners
                            corners = {
                                "tl": [b["left"]  + cal.get("left", 0),  b["top"]    + cal.get("top", 0)],
                                "tr": [b["right"] - cal.get("right", 0), b["top"]    + cal.get("top", 0)],
                                "bl": [b["left"]  + cal.get("left", 0),  b["bottom"] - cal.get("bottom", 0)],
                                "br": [b["right"] - cal.get("right", 0), b["bottom"] - cal.get("bottom", 0)],
                            }
                        else:
                            corners = {
                                "tl": [b["left"],  b["top"]],
                                "tr": [b["right"], b["top"]],
                                "bl": [b["left"],  b["bottom"]],
                                "br": [b["right"], b["bottom"]],
                            }
                        return jsonify({**b, "corners": corners})
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
    data  = request.json  # {tl:[x,y], tr:[x,y], bl:[x,y], br:[x,y]}
    calib = _load_calibration()
    calib[slug] = data
    _save_calibration(calib)
    src = TEMPLATES_DIR / "all_mockuptemplates" / f"{slug}.png"
    dst = TEMPLATES_DIR / "mockuptemplates_calibrated" / f"{slug}.png"
    if src.exists():
        shutil.copy2(src, dst)
    return jsonify({"ok": True})


@app.route("/api/template/<slug>/skip", methods=["POST"])
def api_skip(slug):
    all_file = TEMPLATES_DIR / "all_segments.json"
    entries  = json.loads(all_file.read_text())
    for e in entries:
        if e["template"] == slug:
            e["skipped"] = True
    all_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    return jsonify({"ok": True})


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

        # Find a test print to use
        products_dir = Path("products")
        print_path = next(
            (p for col in sorted(products_dir.iterdir()) if col.is_dir()
             for pair in sorted(col.iterdir()) if pair.is_dir()
             for p in sorted(pair.glob("*.png")) if "description" not in p.name),
            None
        )
        if not print_path:
            return jsonify({"error": "no test print found"}), 404

        out_dir = Path("pipeline/mockup/previews")
        out_dir.mkdir(exist_ok=True)

        calib = json.loads((Path("pipeline/mockup/calibration.json")).read_text())
        if slug not in calib:
            return jsonify({"error": "Ikke kalibrert — kalibrere hjørnene først"}), 400

        results = mockup._generate_psd_single(print_path, psd_path, out_dir)
        if not results:
            return jsonify({"error": "generation failed"}), 500

        import subprocess
        subprocess.Popen(["open", str(results[0])])
        return jsonify({"ok": True, "file": str(results[0])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Mockup Calibrator</title>
<style>
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:-apple-system,sans-serif; background:#111; color:#eee;
       display:flex; height:100vh; overflow:hidden; }

#sidebar { width:210px; min-width:210px; background:#1c1c1c;
  display:flex; flex-direction:column; overflow:hidden; }
#sidebar-header { padding:12px 12px 8px; border-bottom:1px solid #2a2a2a; }
#sidebar-header h1 { font-size:12px; font-weight:700; color:#fff; margin-bottom:3px; }
#progress { font-size:10px; color:#666; }
#search { width:100%; margin-top:6px; padding:4px 6px; background:#2a2a2a;
  border:1px solid #3a3a3a; border-radius:4px; color:#eee; font-size:10px; outline:none; }
#search::placeholder { color:#555; }
#tpl-list { flex:1; overflow-y:auto; padding:4px; }
.tpl-item { padding:4px 8px; border-radius:4px; cursor:pointer;
  font-size:10px; color:#999; margin-bottom:1px;
  display:flex; align-items:center; gap:4px; }
.tpl-item:hover { background:#252525; color:#ccc; }
.tpl-item.active { background:#2a1f0a; color:#f90; }
.tpl-item.deactivated { opacity:0.4; }
.tpl-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1; }
.tpl-status { flex-shrink:0; font-size:9px; }

#main { flex:1; display:flex; flex-direction:column;
  align-items:center; justify-content:center; gap:10px; padding:14px; overflow:hidden; }

#hint { font-size:11px; color:#777; min-height:16px; }
#hint.placing { color:#f80; }

#canvas-wrap { position:relative; display:inline-block; cursor:crosshair; }
#template-img { display:block; max-width:calc(100vw - 220px); max-height:95vh;
  object-fit:contain; user-select:none; pointer-events:none; }

#ref-overlay { position:absolute; border:1px dashed rgba(255,255,255,0.18);
  pointer-events:none; display:none; }
#ovl-canvas  { position:absolute; top:0; left:0; pointer-events:none; }

.ch { position:absolute; width:40px; height:40px;
  transform:translate(-50%,-50%); cursor:crosshair; display:none;
  border-radius:50%; background:rgba(255,160,0,0.07); }
.ch::before,.ch::after { content:""; position:absolute; background:rgba(255,160,0,0.9); }
.ch::before { top:50%; left:0; right:0; height:0.5px; margin-top:-0.25px; }
.ch::after  { left:50%; top:0; bottom:0; width:0.5px; margin-left:-0.25px; }

#corner-dot { position:absolute; width:10px; height:10px;
  border:1px solid #f55; border-radius:50%;
  transform:translate(-50%,-50%); display:none; pointer-events:none; }
#corner-dot::before,#corner-dot::after { content:""; position:absolute; background:#f55; }
#corner-dot::before { top:50%; left:-5px; right:-5px; height:1px; margin-top:-0.5px; }
#corner-dot::after  { left:50%; top:-5px; bottom:-5px; width:1px; margin-left:-0.5px; }

#live-rect { position:absolute; border:1px dashed rgba(255,80,80,0.65);
  pointer-events:none; display:none; }

#controls { display:flex; gap:8px; }
button { padding:7px 16px; border:none; border-radius:6px;
  font-size:13px; font-weight:600; cursor:pointer; }
#btn-save  { background:#f80; color:#000; }
#btn-save:hover  { background:#fa0; }
#btn-skip  { background:#252525; color:#aaa; }
#btn-skip:hover  { background:#333; }
#btn-reset { background:#252525; color:#777; }
#btn-reset:hover { background:#333; }

#info    { font-size:12px; color:#666; }
#offsets { font-size:10px; color:#444; font-family:monospace; }
</style>
</head>
<body>
<div id="sidebar">
  <div id="sidebar-header">
    <h1>Mockup Calibrator</h1>
    <div id="progress">Laster...</div>
    <input id="search" type="text" placeholder="Søk..." autocomplete="off">
  </div>
  <div id="tpl-list"></div>
</div>

<div id="main">
  <div id="hint">Laster...</div>
  <div id="canvas-wrap">
    <img id="template-img" src="" alt="">
    <div id="ref-overlay"></div>
    <canvas id="ovl-canvas"></canvas>
    <div id="h-tl" class="ch"></div>
    <div id="h-tr" class="ch"></div>
    <div id="h-bl" class="ch"></div>
    <div id="h-br" class="ch"></div>
    <div id="corner-dot"></div>
    <div id="live-rect"></div>
  </div>
  <div id="controls">
    <button id="btn-reset">Reset</button>
    <button id="btn-undo">Angre</button>
    <button id="btn-skip">Skip</button>
    <button id="btn-save">Lagre</button>
    <button id="btn-next">Neste</button>
    <button id="btn-gen">Generer mockup</button>
    <button id="btn-flag">⚑ Flagg</button>
    <button id="btn-deactivate">Deaktiver</button>
  </div>
  <div id="info">Laster...</div>
  <div id="offsets"></div>
</div>

<script>
let templates = [], idx = 0, bounds = null;
let corners = {tl:{x:0,y:0}, tr:{x:0,y:0}, bl:{x:0,y:0}, br:{x:0,y:0}};
let savedCorners = null;
let activeDrag = null;
let placing = false;
let corner1 = null;

const img       = document.getElementById("template-img");
const refOvl    = document.getElementById("ref-overlay");
const ovlCanvas = document.getElementById("ovl-canvas");
const cornerDot = document.getElementById("corner-dot");
const liveRect  = document.getElementById("live-rect");
const wrap      = document.getElementById("canvas-wrap");
const info      = document.getElementById("info");
const offsets   = document.getElementById("offsets");
const tplList   = document.getElementById("tpl-list");
const progress  = document.getElementById("progress");
const hint      = document.getElementById("hint");
const handles   = {
  tl: document.getElementById("h-tl"),
  tr: document.getElementById("h-tr"),
  bl: document.getElementById("h-bl"),
  br: document.getElementById("h-br"),
};

function clientToPsd(cx, cy) {
  const r = img.getBoundingClientRect();
  return { x: (cx-r.left)*(bounds.psd_w/img.clientWidth),
           y: (cy-r.top) *(bounds.psd_h/img.clientHeight) };
}
function psdToWrap(x, y) {
  return { x: x*(img.clientWidth /bounds.psd_w),
           y: y*(img.clientHeight/bounds.psd_h) };
}

async function init() {
  const r = await fetch("/api/templates");
  templates = await r.json();
  renderList();
  if (templates.length) load(0);
}

function renderList(scroll=true) {
  const cal = templates.filter(t => t.calibrated && !t.dirty).length;
  progress.textContent = `${cal} / ${templates.length} kalibrert`;
  const q = (document.getElementById("search")?.value || "").toLowerCase();
  tplList.innerHTML = templates.map((t,i) => {
    if (q && !t.slug.toLowerCase().includes(q) && !t.set.toLowerCase().includes(q)) return "";
    const deact = t.active === false ? "deactivated" : "";
    const cls = t.dirty ? "dirty" : (t.calibrated ? "calibrated" : "");
    const num = t.slug.split("_")[0];
    const icon = t.active === false ? `<span class="tpl-status" style="color:#c33">✕</span>`
               : t.flagged          ? `<span class="tpl-status" style="color:#f80">⚑</span>`
               : t.dirty            ? `<span class="tpl-status" style="color:#cc0">✓</span>`
               : t.calibrated       ? `<span class="tpl-status" style="color:#4a4">✓</span>`
               : t.skipped          ? `<span class="tpl-status" style="color:#555">✓</span>`
               : `<span class="tpl-status"></span>`;
    return `<div class="tpl-item ${deact} ${i===idx?"active":""}" onclick="load(${i})">
      <span class="tpl-name">${num}. ${t.set}</span>${icon}</div>`;
  }).join("");
  if (scroll) tplList.querySelector(".active")?.scrollIntoView({block:"nearest"});
}

async function load(i) {
  idx = i;
  const t = templates[i];
  clearCanvas();
  Object.values(handles).forEach(h => h.style.display="none");
  refOvl.style.display = "none";
  img.src = `/api/template/${t.slug}/image?_=${Date.now()}`;
  info.textContent = `${i+1} / ${templates.length} — ${t.set}`;
  offsets.textContent = "";
  hint.textContent = "Laster..."; hint.className = "";

  const r = await fetch(`/api/template/${t.slug}/bounds`);
  const d = await r.json();
  if (d.error) { hint.textContent = "(ingen bounds)"; return; }

  bounds = d;
  const c = d.corners;
  corners = { tl:{x:c.tl[0],y:c.tl[1]}, tr:{x:c.tr[0],y:c.tr[1]},
              bl:{x:c.bl[0],y:c.bl[1]}, br:{x:c.br[0],y:c.br[1]} };
  savedCorners = JSON.parse(JSON.stringify(corners));

  const show = () => requestAnimationFrame(() => {
    updateRefOverlay();
    drawQuad();
    Object.values(handles).forEach(h => h.style.display="block");
    hint.textContent = "Klikk bildet for plassering, eller dra hjørner direkte";
  });
  if (img.complete && img.naturalWidth) show();
  else img.onload = show;
  renderList();
}

function clearCanvas() {
  placing = false; corner1 = null;
  cornerDot.style.display = "none";
  liveRect.style.display  = "none";
  const ctx = ovlCanvas.getContext("2d");
  ctx.clearRect(0, 0, ovlCanvas.width, ovlCanvas.height);
}

// ── two-click placement ────────────────────────────────────────────────────
wrap.addEventListener("dblclick", e => e.preventDefault());
wrap.addEventListener("click", e => {
  if (e.detail > 1) return;
  if (!bounds || activeDrag) return;
  if (Object.values(handles).some(h => h===e.target || h.contains(e.target))) return;

  const p = clientToPsd(e.clientX, e.clientY);

  if (!placing) {
    placing = true; corner1 = p;
    const c = psdToWrap(p.x, p.y);
    cornerDot.style.left=c.x+"px"; cornerDot.style.top=c.y+"px";
    cornerDot.style.display="block"; liveRect.style.display="block";
    hint.textContent = "Klikk det diagonale hjornet..."; hint.className="placing";
  } else {
    const tl_x=Math.min(corner1.x,p.x), tl_y=Math.min(corner1.y,p.y);
    const br_x=Math.max(corner1.x,p.x), br_y=Math.max(corner1.y,p.y);
    corners = { tl:{x:tl_x,y:tl_y}, tr:{x:br_x,y:tl_y},
                bl:{x:tl_x,y:br_y}, br:{x:br_x,y:br_y} };
    cornerDot.style.display="none"; liveRect.style.display="none";
    refOvl.style.display="none";
    drawQuad();
    placing=false; corner1=null;
    hint.textContent="Dra hjorner for skew/finjustering  |  Hold Shift for finmodus"; hint.className="";
  }
});

wrap.addEventListener("mousemove", e => {
  if (!placing || !corner1 || !bounds) return;
  const p=clientToPsd(e.clientX,e.clientY);
  const c1=psdToWrap(corner1.x,corner1.y), c2=psdToWrap(p.x,p.y);
  liveRect.style.left  =Math.min(c1.x,c2.x)+"px";
  liveRect.style.top   =Math.min(c1.y,c2.y)+"px";
  liveRect.style.width =Math.abs(c2.x-c1.x)+"px";
  liveRect.style.height=Math.abs(c2.y-c1.y)+"px";
});

// ── independent corner dragging ────────────────────────────────────────────
Object.entries(handles).forEach(([key,el]) => {
  el.addEventListener("mousedown", e => {
    e.stopPropagation(); e.preventDefault();
    activeDrag = {key, startX:e.clientX, startY:e.clientY, startC:{...corners[key]},
                  imgW:img.clientWidth, imgH:img.clientHeight};
  });
});
document.addEventListener("mousemove", e => {
  if (!activeDrag || !bounds) return;
  const {key,startX,startY,startC,imgW,imgH} = activeDrag;
  const speed = e.shiftKey ? 0.1 : 1.0;
  const dx = (e.clientX-startX)*(bounds.psd_w/imgW)*speed;
  const dy = (e.clientY-startY)*(bounds.psd_h/imgH)*speed;
  corners[key] = {x:Math.round(startC.x+dx), y:Math.round(startC.y+dy)};
  hint.textContent = e.shiftKey
    ? `Finmodus (Shift) — 1 skjerm-px = 0.1 PSD-px`
    : "Dra hjorner for skew/finjustering  |  Hold Shift for finmodus";
  drawQuad();
});
document.addEventListener("mouseup", () => {
  if (activeDrag && templates[idx]) { templates[idx].dirty = true; renderList(false); }
  activeDrag = null;
});

// ── canvas drawing ─────────────────────────────────────────────────────────
function drawQuad() {
  if (!bounds || !img.clientWidth || !img.clientHeight) return;
  ovlCanvas.width  = img.clientWidth;
  ovlCanvas.height = img.clientHeight;
  const ctx = ovlCanvas.getContext("2d");
  ctx.clearRect(0, 0, ovlCanvas.width, ovlCanvas.height);

  const pts = ["tl","tr","br","bl"].map(k => psdToWrap(corners[k].x, corners[k].y));

  Object.entries(handles).forEach(([key,el]) => {
    const {x,y} = psdToWrap(corners[key].x, corners[key].y);
    el.style.left=x+"px"; el.style.top=y+"px";
  });

  offsets.textContent =
    `tl(${Math.round(corners.tl.x)},${Math.round(corners.tl.y)})  ` +
    `tr(${Math.round(corners.tr.x)},${Math.round(corners.tr.y)})  ` +
    `bl(${Math.round(corners.bl.x)},${Math.round(corners.bl.y)})  ` +
    `br(${Math.round(corners.br.x)},${Math.round(corners.br.y)})`;
}

function updateRefOverlay() {
  if (!bounds || !img.clientWidth) return;
  const sx=img.clientWidth/bounds.psd_w, sy=img.clientHeight/bounds.psd_h;
  refOvl.style.display="block";
  refOvl.style.left  =(bounds.left  *sx)+"px"; refOvl.style.top   =(bounds.top   *sy)+"px";
  refOvl.style.width =((bounds.right -bounds.left  )*sx)+"px";
  refOvl.style.height=((bounds.bottom-bounds.top)*sy)+"px";
}

// ── buttons ────────────────────────────────────────────────────────────────
async function saveCurrentCorners() {
  const t = templates[idx];
  await fetch(`/api/template/${t.slug}/calibrate`, {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({
      tl:[corners.tl.x,corners.tl.y], tr:[corners.tr.x,corners.tr.y],
      bl:[corners.bl.x,corners.bl.y], br:[corners.br.x,corners.br.y],
    }),
  });
  templates[idx].calibrated = true;
  templates[idx].dirty = false;
  savedCorners = JSON.parse(JSON.stringify(corners));
  renderList();
  hint.textContent = "Lagret ✓";
}
document.getElementById("btn-save").addEventListener("click", saveCurrentCorners);
document.getElementById("btn-next").addEventListener("click", () => {
  if (idx+1 < templates.length) load(idx+1);
  else info.textContent = "Siste template!";
});
document.getElementById("btn-undo").addEventListener("click", () => {
  if (!savedCorners) return;
  corners = JSON.parse(JSON.stringify(savedCorners));
  templates[idx].dirty = false;
  drawQuad(); renderList();
  hint.textContent = "Tilbakestilt til siste lagring";
});
document.getElementById("btn-skip").addEventListener("click", async () => {
  if (templates[idx]) {
    templates[idx].skipped = true;
    await fetch(`/api/template/${templates[idx].slug}/skip`, {method:"POST"});
    renderList(false);
  }
  if (idx+1 < templates.length) load(idx+1);
});
document.getElementById("btn-flag").addEventListener("click", async () => {
  const t = templates[idx];
  if (!t) return;
  const r = await fetch(`/api/template/${t.slug}/flag`, {method:"POST"});
  const j = await r.json();
  templates[idx].flagged = j.flagged;
  hint.textContent = j.flagged ? "⚑ Flagget for oppfølging" : "Flagg fjernet";
  renderList(false);
});
document.getElementById("btn-deactivate").addEventListener("click", async () => {
  if (!confirm(`Deaktiver "${templates[idx].set}"?`)) return;
  await fetch(`/api/template/${templates[idx].slug}/deactivate`, {method:"POST"});
  templates[idx].active = false;
  hint.textContent = "Deaktivert";
  if (idx+1 < templates.length) load(idx+1);
});
document.getElementById("btn-gen").addEventListener("click", async () => {
  const t = templates[idx];
  if (!t) return;
  const btn = document.getElementById("btn-gen");
  btn.textContent = "Genererer..."; btn.disabled = true;
  const r = await fetch(`/api/template/${t.slug}/generate`, {method:"POST"});
  const j = await r.json();
  btn.textContent = "Generer mockup"; btn.disabled = false;
  if (j.error) { hint.textContent = "⚠ " + j.error; alert(j.error); }
  else hint.textContent = "Åpnet: " + j.file.split("/").pop();
});
document.getElementById("btn-reset").addEventListener("click", () => {
  if (!bounds) return;
  corners = { tl:{x:bounds.left, y:bounds.top},   tr:{x:bounds.right, y:bounds.top},
              bl:{x:bounds.left, y:bounds.bottom}, br:{x:bounds.right, y:bounds.bottom} };
  drawQuad(); updateRefOverlay();
  hint.textContent="Reset til PSD-bounds";
});

window.addEventListener("resize", () => { drawQuad(); updateRefOverlay(); });
document.getElementById("search").addEventListener("input", () => renderList(false));
init();
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("\nMockup Calibrator -> http://localhost:5001\n")
    app.run(port=5001, debug=False)
