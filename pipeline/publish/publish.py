"""
etsy/publish.py — Publishes product pairs to Etsy as draft listings.

Scans products/ for pair folders with description.json but no published.json.
Creates a draft listing, uploads images and digital files.

Run from project root: python3 etsy/publish.py
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import SHOP_ID, CLIENT_ID, SHARED_SECRET, TAXONOMY_ID, WHO_MADE, WHEN_MADE, QUANTITY

load_dotenv(override=True)

PRODUCTS_DIR = Path("products")
BASE_URL     = "https://openapi.etsy.com/v3/application"
ENV_FILE     = Path(".env")

_access_token = os.environ.get("ETSY_ACCESS_TOKEN", "")

if not all([SHOP_ID, _access_token, CLIENT_ID, SHARED_SECRET]):
    missing = [k for k, v in {
        "ETSY_SHOP_ID":        SHOP_ID,
        "ETSY_ACCESS_TOKEN":   _access_token,
        "ETSY_CLIENT_ID":      CLIENT_ID,
        "ETSY_SHARED_SECRET":  SHARED_SECRET,
    }.items() if not v]
    print(f"ERROR: Missing in .env: {', '.join(missing)}")
    sys.exit(1)


def _refresh_token():
    global _access_token
    refresh = os.environ.get("ETSY_REFRESH_TOKEN", "")
    if not refresh:
        print("ERROR: ETSY_REFRESH_TOKEN missing — run oauth.py first")
        sys.exit(1)

    r = requests.post("https://api.etsy.com/v3/public/oauth/token", data={
        "grant_type":    "refresh_token",
        "client_id":     CLIENT_ID,
        "refresh_token": refresh,
    })
    r.raise_for_status()
    tokens = r.json()
    _access_token = tokens["access_token"]

    env = ENV_FILE.read_text()
    env = re.sub(r"ETSY_ACCESS_TOKEN=.*",  f"ETSY_ACCESS_TOKEN='{_access_token}'", env)
    env = re.sub(r"ETSY_REFRESH_TOKEN=.*", f"ETSY_REFRESH_TOKEN='{tokens['refresh_token']}'", env)
    ENV_FILE.write_text(env)
    print("  Token refreshed.")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_access_token}",
        "x-api-key":     f"{CLIENT_ID}:{SHARED_SECRET}",
    }


def _find_pair_folders() -> list[Path]:
    folders = sorted(PRODUCTS_DIR.glob("generation-*"))
    for collection in sorted(PRODUCTS_DIR.glob("collection-*")):
        folders.extend(sorted(collection.glob("pair-*")))
    return folders


def create_listing(meta: dict) -> int:
    resp = requests.post(
        f"{BASE_URL}/shops/{SHOP_ID}/listings",
        headers=_headers(),
        json={
            "quantity":    QUANTITY,
            "title":       meta["title"][:140],
            "description": meta["description"],
            "price":       float(meta["price_usd"]),
            "who_made":    WHO_MADE,
            "when_made":   WHEN_MADE,
            "taxonomy_id": TAXONOMY_ID,
            "type":        "download",
            "is_digital":  True,
            "state":       "draft",
            "tags":        meta["tags"][:13],
        },
    )
    resp.raise_for_status()
    return resp.json()["listing_id"]


def upload_image(listing_id: int, image_path: Path, rank: int):
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/shops/{SHOP_ID}/listings/{listing_id}/images",
            headers=_headers(),
            files={"image": (image_path.name, f, "image/png")},
            data={"rank": rank, "overwrite": "true"},
        )
    resp.raise_for_status()


def upload_file(listing_id: int, file_path: Path, rank: int):
    with open(file_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/shops/{SHOP_ID}/listings/{listing_id}/files",
            headers=_headers(),
            files={"file": (file_path.name, f, "image/png")},
            data={"rank": rank, "name": file_path.name},
        )
    resp.raise_for_status()


def delete_listing(listing_id: int):
    requests.delete(
        f"{BASE_URL}/shops/{SHOP_ID}/listings/{listing_id}",
        headers=_headers(),
    )


def publish_pair(folder: Path):
    meta   = json.loads((folder / "description.json").read_text())
    images = sorted(folder.glob("*.png"))
    in_progress = folder / "publishing.json"

    if len(images) < 2:
        raise ValueError(f"Expected 2 images in {folder.name}, found {len(images)}")

    # Clean up any previous crashed attempt
    if in_progress.exists():
        old = json.loads(in_progress.read_text())
        print(f"  Cleaning up previous crashed attempt (listing {old['listing_id']})...")
        delete_listing(old["listing_id"])
        in_progress.unlink()

    print(f"  Creating draft listing...")
    listing_id = create_listing(meta)
    print(f"  Listing ID: {listing_id}")

    # Save immediately so a crash can be recovered
    in_progress.write_text(json.dumps({"listing_id": listing_id}))

    for i, img in enumerate(images, 1):
        print(f"  Uploading image {i}/2: {img.name}")
        upload_image(listing_id, img, rank=i)

    for i, img in enumerate(images, 1):
        print(f"  Uploading file  {i}/2: {img.name}")
        upload_file(listing_id, img, rank=i)

    result = {
        "listing_id":   listing_id,
        "cat_name":     meta.get("cat_name", ""),
        "state":        "draft",
        "published_at": datetime.now().isoformat(),
        "url":          f"https://www.etsy.com/listing/{listing_id}",
    }
    (folder / "published.json").write_text(json.dumps(result, indent=2))
    in_progress.unlink()
    print(f"  Saved as draft: {result['url']}")
    return result


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None

    if target:
        folder = PRODUCTS_DIR / target
        if not folder.exists():
            print(f"Folder not found: {folder}")
            sys.exit(1)
        pairs = sorted(folder.glob("pair-*"))
        all_folders = pairs if pairs else [folder]
    else:
        all_folders = _find_pair_folders()

    todo = [
        f for f in all_folders
        if (f / "description.json").exists()
        and not (f / "published.json").exists()
    ]

    if not todo:
        print("No unpublished pairs found.")
        sys.exit(0)

    _refresh_token()
    print(f"\n{len(todo)} pair(s) ready to publish as draft\n")

    for folder in todo:
        print(f"[{folder.name}]")
        try:
            publish_pair(folder)
            print()
        except requests.HTTPError as e:
            print(f"  ERROR {e.response.status_code}: {e.response.text}\n")
        except Exception as e:
            print(f"  ERROR: {e}\n")

    print("Done!")


if __name__ == "__main__":
    main()
