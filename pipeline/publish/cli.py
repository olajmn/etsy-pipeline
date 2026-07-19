#!/usr/bin/env python3
"""
pipeline/publish/cli.py — describe (if needed) + publish, in one step.

For every target still missing description.json, describe.py runs first
(Claude writes the listing metadata). Anything that then has description.json
but no published.json gets published as an Etsy draft. Already-published
items are always skipped — nothing is ever published twice.

Usage:
  python3 pipeline/publish/cli.py            # everything not yet published
  python3 pipeline/publish/cli.py set-4      # only set-4
  python3 pipeline/publish/cli.py 4          # same, short form
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.describe.describe import (
    _build_work_items as _describe_work_items,
    describe_pair, describe_set, collect_used_names,
)
from pipeline.publish.publish import (
    _build_work_items as _publish_work_items,
    publish_unit, _refresh_token,
)
from pipeline.products import PRODUCTS_DIR, find_pair_folders, find_set_dirs


def display_name(meta: dict) -> str:
    if "cat_name_1" in meta:
        return f"{meta.get('cat_name_1', '?')} & {meta.get('cat_name_2', '?')}"
    return meta.get("cat_name", "?")


def _resolve_targets(arg: str | None):
    if not arg:
        return find_pair_folders(), find_set_dirs()

    name = arg if arg.startswith(("set-", "collection-", "generation-", "pair-")) else f"set-{arg}"
    folder = PRODUCTS_DIR / name
    if not folder.exists():
        print(f"Folder not found: {folder}")
        sys.exit(1)

    pairs = sorted(folder.glob("pair-*"))
    if pairs:
        return pairs, []
    if folder.name.startswith("set-"):
        return [], [folder]
    return [folder], []


def _run_describe(folders: list[Path], set_dirs: list[Path]) -> None:
    items = _describe_work_items(folders, set_dirs)
    todo = [w for w in items if not w["out_path"].exists()]
    if not todo:
        return

    print(f"\nDESCRIBE — {len(todo)} item(s) need metadata\n")
    used_names = collect_used_names()

    for item in todo:
        print(f"[{item['label']}] Sending to Claude...")
        try:
            if item["kind"] == "set":
                metadata = describe_set(item["pairs"], used_names=used_names)
                used_names.append(metadata.get("cat_name_1", ""))
                used_names.append(metadata.get("cat_name_2", ""))
            else:
                metadata = describe_pair(item["folder"], used_names=used_names)
                used_names.append(metadata.get("cat_name", ""))

            item["out_path"].write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
            print(f"  Cat:   {display_name(metadata)}")
            print(f"  Saved: {item['out_path']}\n")
        except Exception as e:
            print(f"  ERROR in {item['label']}: {e}\n")


def _run_publish(folders: list[Path], set_dirs: list[Path]) -> list[dict]:
    items = _publish_work_items(folders, set_dirs)
    todo = [w for w in items if w["meta_path"].exists() and not w["published_path"].exists()]
    if not todo:
        print("No unpublished items found.")
        return []

    _refresh_token()
    print(f"\nPUBLISH — {len(todo)} item(s) ready\n")

    results = []
    for item in todo:
        print(f"[{item['label']}]")
        try:
            result = publish_unit(item["label"], item["meta_path"], item["listing_images"],
                                   item["download_images"], item["published_path"])
            meta = json.loads(item["meta_path"].read_text())
            result["label"]    = item["label"]
            result["cat_name"] = display_name(meta)
            results.append(result)
        except Exception as e:
            print(f"  ERROR: {e}\n")
    return results


def run(arg: str | None = None) -> list[dict]:
    """Describe (if needed) + publish. Returns the list of publish results (url, cat_name, ...)."""
    folders, set_dirs = _resolve_targets(arg)
    if not folders and not set_dirs:
        return []
    _run_describe(folders, set_dirs)
    return _run_publish(folders, set_dirs)


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    folders, set_dirs = _resolve_targets(arg)

    if not folders and not set_dirs:
        print(f"No pair or set folders found in {PRODUCTS_DIR}")
        sys.exit(1)

    _run_describe(folders, set_dirs)
    _run_publish(folders, set_dirs)
    print("\nDone!")


if __name__ == "__main__":
    main()
