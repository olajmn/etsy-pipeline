#!/usr/bin/env python3
"""
pipeline/generate/reject.py — Move an unwanted set out of production.

Reversible: moves the folder to products/rejected/, it isn't deleted.
Rejected sets are skipped by describe.py, publish.py, and renumbering.

Usage:
  python3 pipeline/generate/reject.py 3       # moves products/set-3 -> products/rejected/set-3
  python3 pipeline/generate/reject.py set-3   # same thing
"""
import sys
from pathlib import Path

PRODUCTS_DIR = Path("products")
REJECTED_DIR = PRODUCTS_DIR / "rejected"


def main():
    if len(sys.argv) < 2:
        print("Usage: ./reject <number or set-N>")
        sys.exit(1)

    arg  = sys.argv[1]
    name = arg if arg.startswith("set-") else f"set-{arg}"
    src  = PRODUCTS_DIR / name

    if not src.exists():
        print(f"Not found: {src}")
        sys.exit(1)

    REJECTED_DIR.mkdir(exist_ok=True)
    dest = REJECTED_DIR / name

    if dest.exists():
        print(f"Already in rejected/: {dest}")
        sys.exit(1)

    src.rename(dest)
    print(f"Moved {src} -> {dest}")


if __name__ == "__main__":
    main()
