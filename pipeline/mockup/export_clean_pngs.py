"""
pipeline/mockup/export_clean_pngs.py

Re-eksporterer alle PSD-er som PNG uten smart object-lag (placeholder-innhold).
Resultatet er en ren bakgrunn med skygger og ramme, men uten eksisterende kunstverk.

Run from project root:
    python3 pipeline/mockup/export_clean_pngs.py
    python3 pipeline/mockup/export_clean_pngs.py --resume   # hopp over eksisterende
"""
import json
import sys
from pathlib import Path

TEMPLATES_DIR = Path("assets/mockup-templates")
ALL_FILE      = TEMPLATES_DIR / "all_segments.json"


def export_clean(psd_path: Path) -> bool:
    try:
        from psd_tools import PSDImage
        psd = PSDImage.open(str(psd_path))

        # Skjul alle smart object-lag midlertidig
        smart_layers = [l for l in psd if l.kind == "smartobject"]
        for l in smart_layers:
            l.visible = False

        img = psd.composite()

        # Gjenopprett visibility (ikke nødvendig siden vi ikke lagrer PSD)
        for l in smart_layers:
            l.visible = True

        out = psd_path.with_suffix(".png")
        img.convert("RGB").save(str(out))
        return True
    except Exception as e:
        print(f"    FEIL: {e}")
        return False


def main():
    resume = "--resume" in sys.argv

    entries = json.loads(ALL_FILE.read_text())
    total = done = skipped = errors = 0

    for entry in entries:
        psd_path = TEMPLATES_DIR / entry["path"]
        png_path = psd_path.with_suffix(".png")
        total += 1

        if resume and png_path.exists():
            skipped += 1
            continue

        if not psd_path.exists():
            errors += 1
            continue

        print(f"[{total}] {entry['template']} ... ", end="", flush=True)
        if export_clean(psd_path):
            done += 1
            print("✓")
        else:
            errors += 1
            print("feil")

    print(f"\nFerdig: {done} eksportert, {skipped} hoppet over, {errors} feil")


if __name__ == "__main__":
    main()
