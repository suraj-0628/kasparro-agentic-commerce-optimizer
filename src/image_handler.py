"""
image_handler.py
Validates uploaded product images and pushes approved ones to Shopify.

Validation checks:
  - Format: must be JPG, PNG, or WEBP
  - Minimum size: 800x800px
  - Maximum file size: 20MB
  - Basic relevance: filename should not suggest wrong category
  - Aspect ratio: warns if not square or close to square
"""

import os
import io
import json
import base64
import requests
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

STORE = os.getenv("SHOPIFY_STORE")
TOKEN = os.getenv("SHOPIFY_TOKEN")
API_VERSION = "2026-04"

ALLOWED_FORMATS  = {"JPEG", "PNG", "WEBP"}
MIN_DIMENSION    = 800      # px
MAX_FILE_SIZE_MB = 20
IDEAL_RATIO_MIN  = 0.8      # width/height — warn outside this range
IDEAL_RATIO_MAX  = 1.25


# ── Validation ────────────────────────────────────────────────────────────────

def validate_image(file_bytes: bytes, filename: str, product_title: str = "") -> dict:
    """
    Validates image bytes. Returns:
    {
        "valid": bool,
        "errors": [...],
        "warnings": [...],
        "info": { format, width, height, size_mb, ratio }
    }
    """
    errors   = []
    warnings = []
    info     = {}

    # File size check
    size_mb = len(file_bytes) / (1024 * 1024)
    info["size_mb"] = round(size_mb, 2)
    if size_mb > MAX_FILE_SIZE_MB:
        errors.append(f"File too large: {size_mb:.1f}MB. Maximum allowed is {MAX_FILE_SIZE_MB}MB.")

    # Open with Pillow
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
        img = Image.open(io.BytesIO(file_bytes))  # re-open after verify
    except Exception as e:
        errors.append(f"Cannot read image file: {str(e)}. Make sure it is a valid image.")
        return {"valid": False, "errors": errors, "warnings": warnings, "info": info}

    # Format check
    fmt = img.format
    info["format"] = fmt
    if fmt not in ALLOWED_FORMATS:
        errors.append(
            f"Unsupported format: {fmt}. "
            f"Please upload a JPG, PNG, or WEBP file. "
            f"To convert: open in Paint → Save As → select JPEG."
        )

    # Dimension check
    width, height = img.size
    info["width"]  = width
    info["height"] = height
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        errors.append(
            f"Image too small: {width}x{height}px. "
            f"Shopify requires at least {MIN_DIMENSION}x{MIN_DIMENSION}px for quality display. "
            f"Please upload a higher resolution image."
        )

    # Aspect ratio check
    ratio = width / height if height > 0 else 0
    info["ratio"] = round(ratio, 2)
    if ratio < IDEAL_RATIO_MIN or ratio > IDEAL_RATIO_MAX:
        warnings.append(
            f"Image ratio is {ratio:.2f} (width/height). "
            f"Shopify product images look best when close to square (1:1). "
            f"Consider cropping to square before uploading."
        )

    # Relevance check — basic filename heuristic
    irrelevant_words = [
        "screenshot", "screen shot", "meme", "wallpaper", "logo",
        "banner", "ad", "flyer", "invoice", "receipt", "document",
        "scan", "selfie", "profile"
    ]
    fname_lower = filename.lower()
    found_irrelevant = [w for w in irrelevant_words if w in fname_lower]
    if found_irrelevant:
        warnings.append(
            f"Filename '{filename}' suggests this may not be a product photo "
            f"(contains: {', '.join(found_irrelevant)}). "
            f"Please make sure you are uploading the correct product image."
        )

    # Mode check — convert RGBA warning
    if img.mode == "RGBA":
        warnings.append(
            "Image has a transparent background (RGBA). "
            "Shopify will display it on white. "
            "Consider saving as JPG with a white background for consistency."
        )

    return {
        "valid":    len(errors) == 0,
        "errors":   errors,
        "warnings": warnings,
        "info":     info,
    }


# ── Shopify image uploader ────────────────────────────────────────────────────

def upload_image_to_shopify(product_id: str, file_bytes: bytes,
                             filename: str, alt_text: str = "") -> dict:
    """
    Uploads a validated image to a Shopify product via Admin API.
    product_id should be the numeric ID (not the gid:// format).
    """
    # Extract numeric ID from gid if needed
    numeric_id = product_id.split("/")[-1] if "/" in product_id else product_id

    endpoint = (
        f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}"
        f"/products/{numeric_id}/images.json"
    )

    # Encode to base64
    encoded = base64.b64encode(file_bytes).decode("utf-8")

    payload = {
        "image": {
            "attachment": encoded,
            "filename":   filename,
            "alt":        alt_text or filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " "),
        }
    }

    response = requests.post(
        endpoint,
        headers={
            "Content-Type":           "application/json",
            "X-Shopify-Access-Token": TOKEN,
        },
        json=payload,
        timeout=60,
    )

    if response.status_code in (200, 201):
        image_data = response.json().get("image", {})
        return {
            "success":  True,
            "imageId":  image_data.get("id"),
            "src":      image_data.get("src"),
            "alt":      image_data.get("alt"),
        }
    else:
        return {
            "success": False,
            "error":   f"Shopify API error {response.status_code}: {response.text[:200]}",
        }


# ── Combined validate + upload ────────────────────────────────────────────────

def handle_image_upload(product_id: str, product_title: str,
                         file_bytes: bytes, filename: str) -> dict:
    """
    Full pipeline: validate → if valid, upload to Shopify.
    Returns a structured result the Flask app can return as JSON.
    """
    validation = validate_image(file_bytes, filename, product_title)

    if not validation["valid"]:
        return {
            "success":   False,
            "stage":     "validation",
            "errors":    validation["errors"],
            "warnings":  validation["warnings"],
            "info":      validation["info"],
            "message":   "Image did not pass validation. Please fix the issues and try again.",
        }

    # Upload to Shopify
    alt_text = product_title
    upload   = upload_image_to_shopify(product_id, file_bytes, filename, alt_text)

    if upload["success"]:
        return {
            "success":  True,
            "stage":    "uploaded",
            "errors":   [],
            "warnings": validation["warnings"],
            "info":     validation["info"],
            "image":    upload,
            "message":  f"Image uploaded successfully to '{product_title}'.",
        }
    else:
        return {
            "success":  False,
            "stage":    "upload_failed",
            "errors":   [upload["error"]],
            "warnings": validation["warnings"],
            "info":     validation["info"],
            "message":  "Image passed validation but failed to upload to Shopify.",
        }


if __name__ == "__main__":
    # Quick validation test with a dummy file
    test_bytes = b"not a real image"
    result = validate_image(test_bytes, "test_screenshot.png", "Cotton Kurta")
    print(json.dumps(result, indent=2))