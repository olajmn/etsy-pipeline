"""
Kopierer alle PSD-filer til assets/mockup-templates/all_mockuptemplates_psd/
med slug-navn (f.eks. 0001_living_room_leather_chairs.psd),
og oppdaterer path-feltet i all_segments.json.

Kjør fra prosjektrot:
    python3 pipeline/mockup/flatten_psds.py
    python3 pipeline/mockup/flatten_psds.py --delete  # slett gamle mapper etterpå
"""
import json
import shutil
import sys
from pathlib import Path

TEMPLATES_DIR = Path("assets/mockup-templates")
ALL_FILE      = TEMPLATES_DIR / "all_segments.json"
OUT_DIR       = TEMPLATES_DIR / "all_mockuptemplates_psd"

OLD_FOLDERS = [
    "Frame Design",
    "Frame Design 2",
    "Frame Mockup 2",
    "Frame Mockup 3",
    "PSD Mockup  (50) 8152025",
    "PSD Mockup 500 Frame Bundle",
]

def main():
    delete = "--delete" in sys.argv
    OUT_DIR.mkdir(exist_ok=True)

    entries = json.loads(ALL_FILE.read_text())
    errors = 0

    for e in entries:
        src = TEMPLATES_DIR / e["path"]
        slug = e["template"]
        dst = OUT_DIR / f"{slug}.psd"

        if not src.exists():
            print(f"MANGLER: {src}")
            errors += 1
            continue

        shutil.copy2(src, dst)
        e["path"] = f"all_mockuptemplates_psd/{slug}.psd"

    ALL_FILE.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    print(f"Ferdig: {len(entries) - errors} PSD-er kopiert, {errors} feil")

    if delete:
        for folder in OLD_FOLDERS:
            p = TEMPLATES_DIR / folder
            if p.exists():
                shutil.rmtree(p)
                print(f"Slettet: {folder}/")

if __name__ == "__main__":
    main()
