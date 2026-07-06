"""
config.py — Business rules and fixed values for etsy-pipeline.

Things that should never be guessed by AI — set them here.
"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Pricing
PRICE_USD = float(os.environ.get("DEFAULT_PRICE_USD", "12.00"))

# Etsy listing defaults
TAXONOMY_ID = 2078        # Art Prints (etsy.com/developers/documentation/reference/taxonomy)
WHO_MADE    = "i_did"
WHEN_MADE   = "2020_2026"
QUANTITY    = 999         # standard for digital downloads

# Etsy credentials
SHOP_ID       = os.environ.get("ETSY_SHOP_ID", "")
ACCESS_TOKEN  = os.environ.get("ETSY_ACCESS_TOKEN", "")
CLIENT_ID     = os.environ.get("ETSY_CLIENT_ID", "")
SHARED_SECRET = os.environ.get("ETSY_SHARED_SECRET", "")
