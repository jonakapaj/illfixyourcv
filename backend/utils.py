import os
import io
import json
import hashlib
from typing import Optional

try:
    from PIL import Image
    import pytesseract
except Exception:
    Image = None
    pytesseract = None

import fitz

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def make_cache_key(cv_bytes: bytes, *parts: str) -> str:
    h = hashlib.sha256()
    h.update(cv_bytes)
    for part in parts:
        h.update((part or "").encode("utf-8"))
    return h.hexdigest()


def get_cached(key: str) -> Optional[dict]:
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def set_cached(key: str, data: dict) -> None:
    path = os.path.join(CACHE_DIR, f"{key}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def extract_text_from_pdf(content: bytes) -> str:
    """Try fast PDF text extraction with PyMuPDF, fallback to OCR if needed."""
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        pages_text = []
        for page in doc:
            txt = page.get_text()
            if txt:
                pages_text.append(txt)

        raw = "\n".join(pages_text).strip()
        if raw:
            return raw
    except Exception:
        pass

    # Fallback: OCR each page to text if PIL + pytesseract available
    if Image is None or pytesseract is None:
        return ""

    try:
        doc = fitz.open(stream=content, filetype="pdf")
        ocr_text = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes()))
            text = pytesseract.image_to_string(img)
            ocr_text.append(text)
        return "\n".join(ocr_text).strip()
    except Exception:
        return ""
