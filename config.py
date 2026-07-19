"""
config.py — Business rules and fixed values for etsy-pipeline.

Things that should never be guessed by AI — set them here.
"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Pricing
PRICE_USD     = float(os.environ.get("DEFAULT_PRICE_USD", "12.00"))
SET_PRICE_USD = float(os.environ.get("SET_PRICE_USD", "7.00"))   # bundled set-N listing (2 cats, 4 prints)

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
