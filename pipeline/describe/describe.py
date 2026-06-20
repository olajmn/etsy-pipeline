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
from config import PRICE_USD

load_dotenv(override=True)

PAIRS_DIR = Path("products")

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
            name = data.get("cat_name", "").strip()
            if name:
                names.append(name)
        except Exception:
            pass
    return sorted(set(names))


def describe_pair(folder: Path, used_names: list[str] = None) -> dict:
    images = sorted(folder.glob("*.png"))
    if len(images) < 2:
        raise ValueError(f"Expected 2 images in {folder.name}, found {len(images)}")

    prompt = PROMPT
    if used_names:
        taken = ", ".join(used_names)
        prompt += f"\n\nIMPORTANT: These names are already taken — do NOT use them: {taken}."

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

    tags = metadata.get("tags", [])
    metadata["tags"] = (tags + ["cat-art"] * 13)[:13]
    metadata["price_usd"] = PRICE_USD

    return metadata


def _find_pair_folders() -> list[Path]:
    folders = sorted(PAIRS_DIR.glob("generation-*"))
    for collection in sorted(PAIRS_DIR.glob("collection-*")):
        folders.extend(sorted(collection.glob("pair-*")))
    return folders


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None

    if target:
        folder = PAIRS_DIR / target
        if not folder.exists():
            print(f"Folder not found: {folder}")
            sys.exit(1)
        pairs = sorted(folder.glob("pair-*"))
        folders = pairs if pairs else [folder]
    else:
        folders = _find_pair_folders()
        if not folders:
            print(f"No pair folders found in {PAIRS_DIR}")
            sys.exit(1)

    todo = [f for f in folders if not (f / "description.json").exists()]
    done = len(folders) - len(todo)

    print(f"\n{len(folders)} pair(s) found — {done} already described, {len(todo)} remaining\n")

    used_names = collect_used_names()

    for folder in todo:
        label = f"{folder.parent.name}/{folder.name}" if folder.parent.name.startswith("collection") else folder.name
        print(f"[{label}] Sending to Claude...")
        try:
            metadata = describe_pair(folder, used_names=used_names)
            out = folder / "description.json"
            out.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
            used_names.append(metadata.get("cat_name", ""))
            print(f"  Cat:    {metadata.get('cat_name', '?')}")
            print(f"  Title:  {metadata['title'][:70]}...")
            print(f"  Price:  ${metadata['price_usd']}")
            print(f"  Tags:   {', '.join(metadata['tags'][:5])}...")
            print(f"  Saved:  {out}\n")
        except Exception as e:
            print(f"  ERROR in {folder.name}: {e}\n")

    print("Done!")


if __name__ == "__main__":
    main()
