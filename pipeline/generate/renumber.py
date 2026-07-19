#!/usr/bin/env python3
"""
pipeline/generate/renumber.py — Close gaps in set-N numbering.

Run this after a ./reject to keep set-N sequential (1, 2, 3, ...).
Safe on already-published sets too — see renumber_sets() docstring.

Usage:
  python3 pipeline/generate/renumber.py
"""
from pathlib import Path

from image_builder import renumber_sets

PRODUCTS_DIR = Path("products")


def main():
    before = sorted(
        (d.name for d in PRODUCTS_DIR.glob("set-*") if d.is_dir()),
        key=lambda name: int(name.split("-")[1]),
    )
    renamed = renumber_sets(PRODUCTS_DIR)
    after = [d.name for d in renamed]

    if before == after:
        print("Already sequential — nothing to do.")
        return

    print(f"Renumbered: {', '.join(before)}  ->  {', '.join(after)}")


if __name__ == "__main__":
    main()
