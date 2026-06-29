"""
pipeline/publish/publish_pod.py — Publish cat art to Etsy via Printify POD.

For each unpublished pair:
  1. Upload print image to Printify
  2. Create product with size variants
  3. Publish to connected Etsy store

Run from project root:
    python3 pipeline/publish/publish_pod.py
    python3 pipeline/publish/publish_pod.py products/set-2
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

PRINTIFY_TOKEN   = os.environ.get("PRINTIFY_API_TOKEN", "")
PRINTIFY_SHOP_ID = os.environ.get("PRINTIFY_SHOP_ID", "")
PRODUCTS_DIR     = Path("products")
BASE_URL         = "https://api.printify.com/v1"

# Matte Vertical Posters (blueprint 282) via Printify Choice (provider 99)
BLUEPRINT_ID = 282
PROVIDER_ID  = 99

# Size variants with cost-based pricing (variant_id: retail_price_usd)
VARIANTS = [
    {"id": 43135, "label": '11"×14"',  "price": 2500},   # $25.00
    {"id": 43138, "label": '12"×18"',  "price": 2900},   # $29.00
    {"id": 43141, "label": '16"×20"',  "price": 3500},   # $35.00
    {"id": 43144, "label": '18"×24"',  "price": 4200},   # $42.00
    {"id": 43150, "label": '24"×36"',  "price": 5500},   # $55.00
]

if not all([PRINTIFY_TOKEN, PRINTIFY_SHOP_ID]):
    print("ERROR: PRINTIFY_API_TOKEN or PRINTIFY_SHOP_ID missing from .env")
    sys.exit(1)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {PRINTIFY_TOKEN}",
        "Content-Type": "application/json",
    }


def upload_image(image_path: Path) -> str:
    """Upload image to Printify media library. Returns image ID."""
    print(f"    Uploading {image_path.name}...")
    with open(image_path, "rb") as f:
        data = f.read()

    import base64
    encoded = base64.b64encode(data).decode("utf-8")

    r = requests.post(
        f"{BASE_URL}/uploads/images.json",
        headers=_headers(),
        json={
            "file_name": image_path.name,
            "contents":  encoded,
        },
    )
    r.raise_for_status()
    image_id = r.json()["id"]
    print(f"    → image ID: {image_id}")
    return image_id


def create_product(meta: dict, image_id: str) -> str:
    """Create Printify product with all size variants. Returns product ID."""
    print(f"    Creating product...")

    variants = [
        {
            "id":      v["id"],
            "price":   v["price"],
            "is_enabled": True,
        }
        for v in VARIANTS
    ]

    # Each variant uses the same print image
    print_areas = [
        {
            "variant_ids": [v["id"] for v in VARIANTS],
            "placeholders": [
                {
                    "position": "front",
                    "images": [
                        {
                            "id":       image_id,
                            "x":        0.5,
                            "y":        0.5,
                            "scale":    1.0,
                            "angle":    0,
                        }
                    ],
                }
            ],
        }
    ]

    r = requests.post(
        f"{BASE_URL}/shops/{PRINTIFY_SHOP_ID}/products.json",
        headers=_headers(),
        json={
            "title":        meta["title"][:140],
            "description":  meta["description"],
            "blueprint_id": BLUEPRINT_ID,
            "print_provider_id": PROVIDER_ID,
            "variants":     variants,
            "print_areas":  print_areas,
            "tags":         meta.get("tags", [])[:13],
        },
    )
    r.raise_for_status()
    product_id = r.json()["id"]
    print(f"    → product ID: {product_id}")
    return product_id


def upload_listing_images(product_id: str, image_paths: list[Path]) -> None:
    """Upload mockup/listing images to the Printify product."""
    print(f"    Uploading {len(image_paths)} listing image(s)...")
    images = []
    for path in image_paths:
        with open(path, "rb") as f:
            import base64
            encoded = base64.b64encode(f.read()).decode("utf-8")
        r = requests.post(
            f"{BASE_URL}/uploads/images.json",
            headers=_headers(),
            json={"file_name": path.name, "contents": encoded},
        )
        if r.ok:
            images.append({"id": r.json()["id"], "variant_ids": [], "position": "front", "is_default": len(images) == 0})
        time.sleep(0.5)

    if images:
        requests.put(
            f"{BASE_URL}/shops/{PRINTIFY_SHOP_ID}/products/{product_id}.json",
            headers=_headers(),
            json={"images": images},
        )


def publish_product(product_id: str) -> None:
    """Push product live to Etsy."""
    print(f"    Publishing to Etsy...")
    r = requests.post(
        f"{BASE_URL}/shops/{PRINTIFY_SHOP_ID}/products/{product_id}/publish.json",
        headers=_headers(),
        json={
            "title":       True,
            "description": True,
            "images":      True,
            "variants":    True,
            "tags":        True,
        },
    )
    r.raise_for_status()


def publish_pair(folder: Path) -> dict:
    """Full publish flow for one product folder."""
    meta = json.loads((folder / "description.json").read_text())

    # Pick the main print image (layered portrait preferred)
    prints = sorted(folder.glob("layered_*.png")) or sorted(folder.glob("_print_portrait_*.png"))
    if not prints:
        raise FileNotFoundError(f"No print image found in {folder}")
    print_image = prints[0]

    # Mockup images for listing photos
    mockups = sorted(folder.glob("*.png"))
    mockup_images = [p for p in mockups if p != print_image][:8]

    # Step 1: Upload print file
    image_id = upload_image(print_image)

    # Step 2: Create product
    product_id = create_product(meta, image_id)

    # Step 3: Upload listing images
    if mockup_images:
        upload_listing_images(product_id, mockup_images)

    # Step 4: Publish to Etsy
    publish_product(product_id)

    result = {
        "product_id":   product_id,
        "published_at": datetime.now().isoformat(),
        "url":          f"https://www.etsy.com/shop/FredCatsby",
        "channel":      "printify",
    }
    (folder / "published.json").write_text(json.dumps(result, indent=2))
    return result


def _find_folders() -> list[Path]:
    folders = []
    for col in sorted(PRODUCTS_DIR.glob("collection-*")):
        folders.extend(sorted(col.glob("pair-*")))
    for s in sorted(PRODUCTS_DIR.glob("set-*")):
        folders.append(s)
    return folders


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None

    if target:
        folders = [Path(target)]
    else:
        folders = _find_folders()

    todo = [
        f for f in folders
        if (f / "description.json").exists()
        and not (f / "published.json").exists()
    ]

    if not todo:
        print("No unpublished pairs found.")
        sys.exit(0)

    print(f"\n{len(todo)} pair(s) ready to publish via Printify\n")

    for folder in todo:
        print(f"[{folder.name}]")
        try:
            result = publish_pair(folder)
            print(f"  Done → {result['url']}\n")
        except requests.HTTPError as e:
            print(f"  ERROR {e.response.status_code}: {e.response.text}\n")
        except Exception as e:
            print(f"  ERROR: {e}\n")

    print("All done!")


if __name__ == "__main__":
    main()
