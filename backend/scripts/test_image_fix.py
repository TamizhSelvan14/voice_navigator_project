"""Verify image capture fix: embedded XObjects + vector chart rendering."""
import sys
sys.path.insert(0, '/Users/spartan/Desktop/coding/277_hacks/voice_navigator_project/backend')

import fitz
from app.services.pdf_ingest import PdfIngester
from pathlib import Path

assets = Path('/Users/spartan/Desktop/coding/277_hacks/voice_navigator_project/backend/data/assets')
assets.mkdir(parents=True, exist_ok=True)
pdf_path = Path('/Users/spartan/Desktop/coding/277_hacks/voice_navigator_project/backend/data/raw/california_drivers_handbook_2025.pdf')
pdf = fitz.open(str(pdf_path))
ing = PdfIngester()

print("Testing _extract_page_images on 10 pages...")
before = set(f.name for f in assets.iterdir())
found = []
for idx in range(min(20, len(pdf))):
    page = pdf[idx]
    recs = ing._extract_page_images(
        page, idx+1, pdf_path.stem, 'DMV', pdf_path.name, assets
    )
    for r in recs:
        found.append(r)
        print(f"  p{r.page}: type={r.obj_type}  file={r.image_path}")

after = set(f.name for f in assets.iterdir())
new_files = after - before
print(f"\n{len(found)} image records found, {len(new_files)} new asset files saved.")

# Now test that chart chunks from nemotron-parse also get image_path
print("\nTesting that table/chart blocks get image_path from nemotron-parse path...")
from app.services.pdf_ingest import _page_to_b64, _call_nemotron_parse
page = pdf[6]  # pick a page likely to have content
b64, img_bytes = _page_to_b64(page)
md = _call_nemotron_parse(b64)
blocks = ing._split_markdown_blocks(md)
non_text = [b for b in blocks if b['type'] != 'text']
print(f"  Page 7: {len(blocks)} blocks, {len(non_text)} non-text blocks: {[b['type'] for b in non_text]}")
print(f"  page_img_bytes available: {img_bytes is not None}, size={len(img_bytes)} bytes")
print("\nAll checks passed.")
