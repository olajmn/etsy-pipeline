"""
pipeline/describe/describe.py — Generates Etsy metadata for each layered pair.

Sends both images in the pair to Claude Vision and writes:
  - title (SEO-optimized, max 140 characters)
  - description (warm tone, 3-4 paragraphs)
  - 13 tags
  - price in USD

Saves the result as description.json in the pair folder.
Skips folders that already have description.json.

Run from project root: python3 pipeline/describe/describe.py
"""
import base64
import io
import json
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import PRICE_USD, SET_PRICE_USD
from pipeline.generate.image_builder import find_set_pairs
from pipeline.products import PRODUCTS_DIR as PAIRS_DIR, find_pair_folders, find_set_dirs

load_dotenv(override=True)

SYSTEM = (
    "You are an Etsy shop assistant writing product listings for a minimalist "
    "Scandinavian cat art print shop. Always respond with valid JSON only — "
    "no markdown fences, no explanation."
)

PROMPT = """These two images feature the SAME cat character in two different print formats:
- Image 1: a layered poster (large format, split background)
- Image 2: a portrait poster (three poses of the same cat, solid background)

It is one cat — one color, one personality — shown across two prints. They are sold together as a bundle.

First, give this cat a unique character name that fits its color and personality — short, memorable, feels like a real pet name. Think of how "Frøya" suits a warm fiery cat without saying "orange", or how "Luna" suits a pale dreamy cat without saying "white". Names can be from any language or origin. Do NOT use names that literally describe the color (not "Rust", "Ginger", "Shadow", "Ash", "Bluebell", or similar).

Write Etsy listing metadata. Return a JSON object with exactly these fields:
- "cat_name": string, the unique name you chose for this cat character
- "title": string, max 140 characters, SEO-rich. Lead with the cat's name and color, include keywords: "cat print", "wall art", "digital download", "Scandinavian"
- "description": string, 3–4 short paragraphs with line breaks (\\n\\n). Introduce the cat by name. Warm, personal tone — like you're introducing a character. Mention it's one cat in two print formats, instant digital download, mention the colors. No links or contact info.
- "tags": array of exactly 13 strings, each max 20 characters, no spaces (use hyphens), mix broad and specific

Keywords to weave in: minimalist, cat, wall art, digital download, home decor, Scandinavian, art print, instant download, cat lover gift."""

SET_PROMPT = """These four images feature TWO DIFFERENT cat characters, sold together as one bundled set:
- Image 1: Cat A — a layered poster (large format, split background)
- Image 2: Cat A — a portrait poster (three poses of the same cat, solid background)
- Image 3: Cat B — a layered poster (large format, split background)
- Image 4: Cat B — a portrait poster (three poses of the same cat, solid background)

Each cat is its own character — one color, one personality — shown across two prints. The two cats together make one bundled set of 4 prints, sold as a single listing.

First, give EACH cat its own unique character name that fits its color and personality — short, memorable, feels like a real pet name. Think of how "Frøya" suits a warm fiery cat without saying "orange", or how "Luna" suits a pale dreamy cat without saying "white". Names can be from any language or origin. Do NOT use names that literally describe the color (not "Rust", "Ginger", "Shadow", "Ash", "Bluebell", or similar). The two names must be different from each other.

Write Etsy listing metadata for this ONE combined listing. Return a JSON object with exactly these fields:
- "cat_name_1": string, the unique name you chose for Cat A
- "cat_name_2": string, the unique name you chose for Cat B
- "title": string, max 140 characters, SEO-rich. Mention both cat names, make clear this is a set of 2, include keywords: "cat print", "wall art", "digital download", "Scandinavian", "set of 2". Etsy only allows the character "&" to appear ONCE in a title — use it at most once (e.g. only between the two cat names, "and" elsewhere), or not at all
- "description": string, 3–5 short paragraphs with line breaks (\\n\\n). Introduce both cats by name as two distinct characters. Warm, personal tone. Mention it's a bundled set of 2 cats (4 prints total), instant digital download, mention the colors of each cat. No links or contact info.
- "tags": array of exactly 13 strings, each max 20 characters, no spaces (use hyphens), mix broad and specific, covering the set as a whole

Keywords to weave in: minimalist, cat, wall art, digital download, home decor, Scandinavian, art print, instant download, cat lover gift, set of 2."""


def _encode(path: Path, max_width: int = 800) -> str:
    img = Image.open(path)
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=85)
    return base64.standard_b64encode(buf.getvalue()).decode()


def collect_used_names(base_dir: Path = None) -> list[str]:
    base = base_dir or PAIRS_DIR
    names = []
    for desc in base.rglob("description.json"):
        try:
            data = json.loads(desc.read_text())
            for key in ("cat_name", "cat_name_1", "cat_name_2"):
                name = data.get(key, "").strip()
                if name:
                    names.append(name)
        except Exception:
            pass
    return sorted(set(names))


def _ask_claude(images: list[Path], prompt: str) -> dict:
    content = []
    for img_path in images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": _encode(img_path)},
        })
    content.append({"type": "text", "text": prompt})

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": content}],
    )

    text = next(b.text for b in response.content if b.type == "text").strip()
    metadata = json.loads(text)
    metadata["tags"] = metadata.get("tags", [])[:13]
    return metadata


def describe_pair(folder: Path, used_names: list[str] = None) -> dict:
    images = sorted(folder.glob("*.png"))
    if len(images) < 2:
        raise ValueError(f"Expected 2 images in {folder.name}, found {len(images)}")

    prompt = PROMPT
    if used_names:
        taken = ", ".join(used_names)
        prompt += f"\n\nIMPORTANT: These names are already taken — do NOT use them: {taken}."

    metadata = _ask_claude(images, prompt)
    metadata["price_usd"] = PRICE_USD
    return metadata


def describe_set(pairs: dict, used_names: list[str] = None) -> dict:
    """One combined description for a set-N dir's 2 cats (katt1 + katt2)."""
    images = [
        pairs["katt1"]["portrait"], pairs["katt1"]["composition"],
        pairs["katt2"]["portrait"], pairs["katt2"]["composition"],
    ]

    prompt = SET_PROMPT
    if used_names:
        taken = ", ".join(used_names)
        prompt += f"\n\nIMPORTANT: These names are already taken — do NOT use them: {taken}."

    metadata = _ask_claude(images, prompt)
    metadata["price_usd"] = SET_PRICE_USD
    return metadata


def _build_work_items(folders: list[Path], set_dirs: list[Path]) -> list[dict]:
    """Flatten pair-folders and set-N dirs into one work list. Each set-N dir
    becomes ONE combined listing (both cats, 4 prints)."""
    items = []
    for folder in folders:
        label = f"{folder.parent.name}/{folder.name}" if folder.parent.name.startswith("collection") else folder.name
        items.append({"label": label, "kind": "pair", "folder": folder, "out_path": folder / "description.json"})
    for set_dir in set_dirs:
        pairs = find_set_pairs(set_dir)
        if "katt1" not in pairs or "katt2" not in pairs:
            continue
        items.append({
            "label":    set_dir.name,
            "kind":     "set",
            "folder":   set_dir,
            "pairs":    pairs,
            "out_path": set_dir / "description.json",
        })
    return items


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None

    if target:
        folder = PAIRS_DIR / target
        if not folder.exists():
            print(f"Folder not found: {folder}")
            sys.exit(1)
        pairs = sorted(folder.glob("pair-*"))
        if pairs:
            folders, set_dirs = pairs, []
        elif folder.name.startswith("set-"):
            folders, set_dirs = [], [folder]
        else:
            folders, set_dirs = [folder], []
    else:
        folders  = find_pair_folders()
        set_dirs = find_set_dirs()
        if not folders and not set_dirs:
            print(f"No pair or set folders found in {PAIRS_DIR}")
            sys.exit(1)

    work_items = _build_work_items(folders, set_dirs)
    todo = [w for w in work_items if not w["out_path"].exists()]
    done = len(work_items) - len(todo)

    print(f"\n{len(work_items)} pair(s) found — {done} already described, {len(todo)} remaining\n")

    used_names = collect_used_names()

    for item in todo:
        print(f"[{item['label']}] Sending to Claude...")
        try:
            if item["kind"] == "set":
                metadata = describe_set(item["pairs"], used_names=used_names)
                cat_label = f"{metadata.get('cat_name_1', '?')} & {metadata.get('cat_name_2', '?')}"
                used_names.append(metadata.get("cat_name_1", ""))
                used_names.append(metadata.get("cat_name_2", ""))
            else:
                metadata = describe_pair(item["folder"], used_names=used_names)
                cat_label = metadata.get("cat_name", "?")
                used_names.append(metadata.get("cat_name", ""))

            item["out_path"].write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
            print(f"  Cat:    {cat_label}")
            print(f"  Title:  {metadata['title'][:70]}...")
            print(f"  Price:  ${metadata['price_usd']}")
            print(f"  Tags:   {', '.join(metadata['tags'][:5])}...")
            print(f"  Saved:  {item['out_path']}\n")
        except Exception as e:
            print(f"  ERROR in {item['label']}: {e}\n")

    print("Done!")


if __name__ == "__main__":
    main()
