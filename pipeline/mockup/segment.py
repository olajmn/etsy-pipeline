"""
pipeline/mockup/segment.py — Auto-tag mockup templates using Claude Vision.

Each bundle folder gets its own segments.json.

Run from project root:
    python3 pipeline/mockup/segment.py "PSD Mockup 500 Frame Bundle"
    python3 pipeline/mockup/segment.py "My New Bundle" --resume
"""
import base64
import json
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)

import anthropic

TEMPLATES_DIR = Path("assets/mockup-templates")

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are tagging mockup template images for an art print Etsy shop.
For each image return ONLY a JSON object with these exact fields:
- set: snake_case scene name (e.g. "kitchen_green_cabinets", "bedroom_guitar_window") — same room/scene = same set name, be specific
- frame: frame material/color — one of: "dark_wood", "light_wood", "black", "white", "golden", "silver", "none"
- frames: integer — number of BLANK/EMPTY frames that could hold artwork (ignore fixed decorative paintings)
- style: overall aesthetic — one of: "minimal_light", "minimal_dark", "cozy", "bohemian", "rustic", "retro", "modern", "kids"
- warmth: color temperature of the scene — one of: "warm", "cool", "neutral"
- tags: array of 6-10 lowercase strings covering ALL of these aspects:
    * room type (e.g. "kitchen", "bedroom", "living room", "office", "bathroom", "hallway")
    * wall color (e.g. "white wall", "teal wall", "dark wall", "beige wall")
    * floor type (e.g. "wooden floor", "tiles", "rug", "concrete")
    * props (e.g. "guitar", "wine bottle", "books", "plants", "lamp", "cutting board", "coffee cup")
    * lighting (e.g. "natural light", "warm light", "moody", "bright", "side light")

Return ONLY valid JSON. No explanation, no markdown."""


def _slug(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "_", path.stem.lower()).strip("_")


def _tag_image(png_path: Path) -> dict:
    data = base64.standard_b64encode(png_path.read_bytes()).decode()
    for attempt in range(3):
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/png", "data": data},
                        },
                        {"type": "text", "text": "Tag this mockup."},
                    ],
                }],
            )
            text = msg.content[0].text.strip()
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
            return json.loads(text)
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def _sort_key(p: Path) -> int:
    m = re.search(r"\d+", p.stem)
    return int(m.group()) if m else 0


def _collect_pngs(bundle_dir: Path) -> list[Path]:
    pngs = []
    for sub in sorted(bundle_dir.iterdir()):
        if not sub.is_dir():
            continue
        for png in sorted(sub.glob("*.png"), key=_sort_key):
            if png.with_suffix(".psd").exists():
                pngs.append(png)
    for png in sorted(bundle_dir.glob("*.png"), key=_sort_key):
        if png.with_suffix(".psd").exists():
            pngs.append(png)
    return pngs


def main():
    resume = "--resume" in sys.argv
    args   = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print("Usage: python3 pipeline/mockup/segment.py <bundle folder name> [--resume]")
        print("       python3 pipeline/mockup/segment.py --merge")
        sys.exit(1)

    bundle_dir    = TEMPLATES_DIR / args[0]
    segments_file = bundle_dir / f"{bundle_dir.name}.json"

    if not bundle_dir.exists():
        print(f"Not found: {bundle_dir}")
        sys.exit(1)

    existing = {}
    if resume and segments_file.exists():
        for entry in json.loads(segments_file.read_text()):
            existing[entry["template"]] = entry

    pngs = _collect_pngs(bundle_dir)
    print(f"Found {len(pngs)} templates in '{args[0]}'\n")

    results    = list(existing.values()) if resume else []
    done_slugs = set(existing.keys())    if resume else set()

    for i, png in enumerate(pngs):
        s = _slug(png)
        if s in done_slugs:
            print(f"  [{i+1}/{len(pngs)}] {png.name} — skip")
            continue

        try:
            tagged = _tag_image(png)
            entry  = {
                "template": s,
                "path":     str(png.with_suffix(".psd").relative_to(TEMPLATES_DIR)),
                "set":      tagged.get("set", "unknown"),
                "frames":   tagged.get("frames", 1),
                "frame":    tagged.get("frame", "wooden"),
                "style":    tagged.get("style", "modern"),
                "warmth":   tagged.get("warmth", "neutral"),
                "tags":     tagged.get("tags", []),
                "active":   tagged.get("frames", 1) == 1,
            }
            results.append(entry)
            done_slugs.add(s)
            print(f"  [{i+1}/{len(pngs)}] {png.name} → {entry['set']} ({entry['frames']} frame(s))")
        except Exception as e:
            print(f"  [{i+1}/{len(pngs)}] {png.name} ERROR: {e}")

        if (i + 1) % 10 == 0:
            segments_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))

        time.sleep(0.05)

    segments_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    active = sum(1 for r in results if r["active"])
    print(f"\nFerdig. {len(results)} templates tagget, {active} aktive → {segments_file}")


if __name__ == "__main__":
    main()
