#!/usr/bin/env python3
"""
pipeline/generate/run.py — Manual generation tool for etsy-pipeline.

Run from project root: python3 pipeline/generate/run.py

Modes:
  1. Collection   — 3 pairs (warm/cool/soft) → products/  [PRODUCTION]
  2. Layered pair — single pair → products/               [PRODUCTION]
  3. Single cat   — silhouette experiment → generated/
  4. Multi-cat    — 3 silhouettes in one poster
  5. Layered      — single layered image (no portrait)
  6. Pattern      — scattered cats on large canvas
"""
from pathlib import Path
from image_builder import (
    generate_pair, generate_set, generate_collection,
    next_generation_dir,
    OUTPUT_DIR,
)

PRODUCTS_DIR = Path("products")


def ask(question: str, options: list[str]) -> str:
    print(f"\n{question}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        val = input("\nChoose: ").strip()
        if val.isdigit() and 1 <= int(val) <= len(options):
            return options[int(val) - 1]
        print("Invalid choice, try again.")


def main():
    print("\n╔══════════════════════════╗")
    print("║      etsy-pipeline       ║")
    print("╚══════════════════════════╝\n")

    mode = ask("What do you want to generate?", [
        "Set (4 prints + 6 mockups, flat)        ← production",
        "Collection (3 pairs — warm/cool/soft)  ← production",
        "Layered pair (poster + portrait)        ← production",
        "Single cat (experiment)",
        "Multi-cat poster (experiment)",
        "Layered (single image, no portrait)",
        "Pattern (experiment)",
    ])

    if "Pattern" in mode:
        n = input("How many cats? (default 60): ").strip()
        count = int(n) if n.isdigit() else 60
    elif "Collection" in mode or "Single" in mode:
        count = 1
    else:
        n = input("How many? (default 1): ").strip()
        count = int(n) if n.isdigit() else 1

    if "Set" in mode:
        print(f"\nGenerating {count} set(s) → products/\n")
        for i in range(count):
            print(f"[{i+1}/{count}]")
            generate_set(out_dir=PRODUCTS_DIR)

    elif "Collection" in mode:
        print(f"\nGenerating {count} collection(s) → products/\n")
        for i in range(count):
            print(f"[{i+1}/{count}]")
            generate_collection(base_dir=PRODUCTS_DIR)

    elif "Layered pair" in mode:
        print(f"\nGenerating {count} pair(s) → products/\n")
        for i in range(count):
            print(f"[{i+1}/{count}]")
            generate_pair(out_dir=OUTPUT_DIR)

    elif "Single" in mode:
        out = next_generation_dir(OUTPUT_DIR)
        print(f"\n→ {out}/\n")
        generate_colored(out_dir=out)

    elif "Multi" in mode:
        size_map = {
            "plakat (1500×2000)":   "plakat",
            "portrett (1080×1350)": "portrett",
            "kvadrat (1080×1080)":  "kvadrat",
        }
        label = ask("Format?", list(size_map.keys()))
        out = next_generation_dir(MULTI_OUTPUT_DIR)
        print(f"\n→ {out}/\n")
        for i in range(count):
            generate_multi(out_dir=out, canvas_size=size_map[label])

    elif "Layered" in mode and "pair" not in mode:
        out = next_generation_dir(LAYERED_OUTPUT_DIR)
        print(f"\n→ {out}/\n")
        for i in range(count):
            generate_layered(out_dir=out)

    elif "Pattern" in mode:
        out = next_generation_dir(SCATTER_OUTPUT_DIR)
        print(f"\n→ {out}/\n")
        generate_scatter(count=count, out_dir=out)

    print("\nDone!")


if __name__ == "__main__":
    main()
