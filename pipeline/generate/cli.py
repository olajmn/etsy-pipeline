#!/usr/bin/env python3
"""
pipeline/generate/cli.py — Non-interactive set generator.

Usage:
  python3 pipeline/generate/cli.py        # generates 1 set
  python3 pipeline/generate/cli.py 3      # generates 3 sets

Always the "Set" production path (see run.py for other experimental modes).
"""
import sys
from pathlib import Path

from image_builder import generate_set

PRODUCTS_DIR = Path("products")


def generate(count: int = 1) -> list[Path]:
    """Generate `count` sets, returns the created set-N dirs."""
    created = []
    for i in range(count):
        print(f"[{i+1}/{count}]")
        created.append(generate_set(out_dir=PRODUCTS_DIR))
    return created


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"\nGenerating {count} set(s) → products/\n")
    generate(count)
    print("\nDone!")


if __name__ == "__main__":
    main()
