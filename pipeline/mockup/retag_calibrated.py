"""
pipeline/mockup/retag_calibrated.py — Add aesthetic + bg_tone tags to calibrated templates.

Updates all_segments.json in-place. Only touches calibrated entries.

Run from project root:
    python3 pipeline/mockup/retag_calibrated.py
    python3 pipeline/mockup/retag_calibrated.py --resume   # skip already-tagged
"""
import base64
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(override=True)

import anthropic

TEMPLATES_DIR = Path("assets/mockup-templates")
CALIB_DIR     = TEMPLATES_DIR / "mockuptemplates_calibrated"
SEG_FILE      = TEMPLATES_DIR / "all_segments.json"

client = anthropic.Anthropic()

AESTHETICS = [
    "scandinavian", "rustic", "mediterranean", "beach", "boho",
    "industrial", "japandi", "maximalist", "cozy", "modern",
    "classic", "eclectic", "retro", "tropical",
]

SYSTEM_PROMPT = f"""You are tagging interior room mockup images for an art print shop.

Return ONLY a JSON object with exactly these two fields:

- aesthetic: array of 1-3 strings from this list ONLY:
  {AESTHETICS}

- bg_tone: one of "light", "dark", "colorful"
  light    = white/cream/beige walls, bright and airy
  dark     = dark walls, moody, low contrast
  colorful = strong wall color (orange, teal, pink, green, etc.)

Return ONLY valid JSON. No explanation."""


def _tag_image(png_path: Path) -> dict:
    data = base64.standard_b64encode(png_path.read_bytes()).decode()
    for attempt in range(3):
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/png", "data": data},
                        },
                        {"type": "text", "text": "Tag this room."},
                    ],
                }],
            )
            import re
            text = msg.content[0].text.strip()
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
            return json.loads(text)
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def main():
    resume = "--resume" in sys.argv

    entries  = json.loads(SEG_FILE.read_text())
    by_slug  = {e["template"]: i for i, e in enumerate(entries)}

    calibrated = [
        e for e in entries
        if e.get("active") and (CALIB_DIR / f"{e['template']}.png").exists()
    ]

    print(f"Kalibrerte entries: {len(calibrated)}")
    if resume:
        already = [e for e in calibrated if "aesthetic" in e]
        print(f"Allerede tagget (skip): {len(already)}")

    updated = 0
    for i, entry in enumerate(calibrated):
        slug = entry["template"]

        if resume and "aesthetic" in entry:
            print(f"  [{i+1}/{len(calibrated)}] {slug} — skip")
            continue

        png_path = CALIB_DIR / f"{slug}.png"
        try:
            result = _tag_image(png_path)

            aesthetic = [a for a in result.get("aesthetic", []) if a in AESTHETICS]
            bg_tone   = result.get("bg_tone", "light")
            if bg_tone not in ("light", "dark", "colorful"):
                bg_tone = "light"

            idx = by_slug[slug]
            entries[idx]["aesthetic"] = aesthetic
            entries[idx]["bg_tone"]   = bg_tone

            print(f"  [{i+1}/{len(calibrated)}] {slug}")
            print(f"    aesthetic: {aesthetic}  |  bg_tone: {bg_tone}")
            updated += 1

        except Exception as e:
            print(f"  [{i+1}/{len(calibrated)}] {slug} ERROR: {e}")

        # Save every 10
        if updated % 10 == 0 and updated > 0:
            SEG_FILE.write_text(json.dumps(entries, indent=2, ensure_ascii=False))

        time.sleep(0.05)

    SEG_FILE.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    print(f"\nFerdig. {updated} entries oppdatert → {SEG_FILE}")


if __name__ == "__main__":
    main()
