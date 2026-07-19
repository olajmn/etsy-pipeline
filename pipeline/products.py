"""
pipeline/products.py — Shared helpers for locating product folders under products/.

Used by describe.py, publish.py, and pipeline/*/cli.py so folder-discovery
logic lives in exactly one place.
"""
from pathlib import Path

PRODUCTS_DIR = Path("products")


def find_pair_folders(products_dir: Path = None) -> list[Path]:
    """generation-N/ dirs and collection-N/pair-X/ dirs (the old pair-based production path)."""
    folder = products_dir or PRODUCTS_DIR
    folders = sorted(folder.glob("generation-*"))
    for collection in sorted(folder.glob("collection-*")):
        folders.extend(sorted(collection.glob("pair-*")))
    return folders


def find_set_dirs(products_dir: Path = None) -> list[Path]:
    """set-N/ dirs — the current production path."""
    folder = products_dir or PRODUCTS_DIR
    return sorted(folder.glob("set-*"))
