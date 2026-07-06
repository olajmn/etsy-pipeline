"""
pipeline/run_all.py — Pipeline steps: generate, describe, publish.

Run from project root:
    python3 pipeline/run_all.py           # generate + describe 1 collection
    python3 pipeline/run_all.py 3         # generate + describe 3 collections
    python3 pipeline/run_all.py publish   # publish all unpublished pairs
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.generate.image_builder import generate_collection
from pipeline.describe.describe import describe_pair, collect_used_names
from pipeline.publish.publish import publish_pair, _refresh_token
from pipeline.generate.color_card import generate_color_card
from pipeline.mockup.mockup import generate_mockup

PRODUCTS_DIR = Path("products")


def generate_and_describe(count: int = 1) -> list[Path]:
    """Generate + describe N collections. Returns list of collection dirs."""
    print(f"\n{'='*50}")
    print(f"  etsy-pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Generating {count} collection(s)")
    print(f"{'='*50}\n")

    collection_dirs = []

    for i in range(count):
        print(f"[Collection {i+1}/{count}]\n")

        # Step 1: Generate
        print("  GENERATE")
        pairs = generate_collection(base_dir=PRODUCTS_DIR)
        collection_dir = pairs[0][0].parent.parent
        print(f"  → {collection_dir.name} ({len(pairs)} pairs)\n")

        # Step 2: Describe
        print("  DESCRIBE")
        used_names = collect_used_names()
        for pair_dir in sorted(collection_dir.glob("pair-*")):
            out = pair_dir / "description.json"
            if out.exists():
                print(f"    {pair_dir.name}: already described, skipping")
                continue
            try:
                meta = describe_pair(pair_dir, used_names=used_names)
                out.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
                used_names.append(meta.get("cat_name", ""))
                print(f"    {pair_dir.name}: {meta.get('cat_name', '?')} — {meta['title'][:50]}...")
            except Exception as e:
                print(f"    {pair_dir.name}: ERROR — {e}")
                return collection_dirs

        # Step 3: Color cards
        print("  COLOR CARDS")
        for pair_dir in sorted(collection_dir.glob("pair-*")):
            try:
                out = generate_color_card(pair_dir)
                if out:
                    print(f"    {pair_dir.name}: → {out.name}")
            except Exception as e:
                print(f"    {pair_dir.name}: ERROR — {e}")

        # Step 4: Mockups
        print("  MOCKUPS")
        try:
            outputs = generate_mockup(collection_dir)
            print(f"    {len(outputs)} mockups generert")
        except Exception as e:
            print(f"    ERROR — {e}")
        print()

        collection_dirs.append(collection_dir)

    print("Done! Send /publish to push to Etsy drafts.")
    return collection_dirs


def publish_unpublished(collection_dir: Path = None) -> list[dict]:
    """Publish all pairs that have description.json but no published.json."""
    _refresh_token()

    if collection_dir:
        folders = sorted(collection_dir.glob("pair-*"))
    else:
        folders = []
        for col in sorted(PRODUCTS_DIR.glob("collection-*")):
            folders.extend(sorted(col.glob("pair-*")))

    todo = [
        f for f in folders
        if (f / "description.json").exists() and not (f / "published.json").exists()
    ]

    if not todo:
        print("No unpublished pairs found.")
        return []

    print(f"\n{len(todo)} pair(s) ready to publish\n")
    results = []

    for pair_dir in todo:
        try:
            result = publish_pair(pair_dir)
            meta = json.loads((pair_dir / "description.json").read_text())
            result["cat_name"] = meta.get("cat_name", "?")
            print(f"  {pair_dir.name}: {result['cat_name']} → {result['url']}")
            results.append(result)
        except requests.HTTPError as e:
            print(f"  {pair_dir.name}: ERROR {e.response.status_code} — {e.response.text}")
        except Exception as e:
            print(f"  {pair_dir.name}: ERROR — {e}")

    return results


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "publish":
        publish_unpublished()
    else:
        count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        generate_and_describe(count)
