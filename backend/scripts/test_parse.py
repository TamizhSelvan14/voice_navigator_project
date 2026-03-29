"""Quick test: nemotron-parse on one PDF page."""
import base64
import json
import sys

import fitz
import requests

from app.config import settings
from app.services.pdf_ingest import _page_to_b64, _call_nemotron_parse


def main():
    print("Embed model:", settings.embedding_model)
    print("Testing nemotron-parse via pdf_ingest helper...")

    doc = fitz.open(str(settings.raw_data_dir / "california_drivers_handbook_2025.pdf"))
    page = doc[5]
    b64, img_bytes = _page_to_b64(page)
    print(f"Image size: {len(img_bytes)} bytes, b64 len: {len(b64)}")

    md = _call_nemotron_parse(b64)
    print(f"\nParse result ({len(md)} chars):")
    print(md[:600])

    # Test multimodal embedding
    print("\n\nTesting multimodal embedding...")
    headers = {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    embed_payload = {
        "model": settings.embedding_model,
        "input": ["What is the speed limit in a school zone?"],
        "encoding_format": "float",
        "input_type": "query",
        "truncate": "END",
    }
    resp2 = requests.post(
        f"{settings.nvidia_base_url}/embeddings",
        headers=headers,
        json=embed_payload,
        timeout=60,
    )
    print("Embed status:", resp2.status_code)
    if resp2.ok:
        data = resp2.json()["data"]
        print(f"Got {len(data)} embeddings, dim={len(data[0]['embedding'])}")
    else:
        print("Embed error:", resp2.text[:500])
    print("Embed model:", settings.embedding_model)
    print("Testing nemotron-parse on a single page...")

    doc = fitz.open(str(settings.raw_data_dir / "california_drivers_handbook_2025.pdf"))
    page = doc[5]
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("jpeg")

    b64 = base64.b64encode(img_bytes).decode("ascii")
    headers = {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    content = f'<img src="data:image/jpeg;base64,{b64}" />'
    payload = {
        "model": "nvidia/nemotron-parse",
        "messages": [{"role": "user", "content": content}],
        "tools": [{"type": "function", "function": {"name": "markdown_no_bbox"}}],
        "tool_choice": {"type": "function", "function": {"name": "markdown_no_bbox"}},
        "max_tokens": 4096,
    }
    resp = requests.post(settings.nvidia_parse_url, headers=headers, json=payload, timeout=120)
    print("Status:", resp.status_code)
    if resp.ok:
        body = resp.json()
        msg = body["choices"][0]["message"]
        tc = msg.get("tool_calls", [])
        if tc:
            raw_args = tc[0]["function"]["arguments"]
            print("Raw args type:", type(raw_args))
            print("Raw args repr[:500]:", repr(raw_args)[:500])
            if isinstance(raw_args, str):
                args = json.loads(raw_args)
            else:
                args = raw_args
            print("Parsed args type:", type(args))
            if isinstance(args, dict):
                md = args.get("markdown", str(args))
            elif isinstance(args, list) and args:
                # check first element
                first = args[0]
                if isinstance(first, dict):
                    md = first.get("markdown", json.dumps(first)[:500])
                else:
                    md = str(first)
            else:
                md = str(args)
            print(f"Parse result ({len(md)} chars, first 500):")
            print(str(md)[:500])
        else:
            print("Content:", msg.get("content", "")[:500])
    else:
        print("Error:", resp.text[:500])

    # Test multimodal embedding
    print("\n\nTesting multimodal embedding...")
    embed_payload = {
        "model": settings.embedding_model,
        "input": ["What is the speed limit in a school zone?"],
        "encoding_format": "float",
        "input_type": "query",
        "truncate": "END",
    }
    resp2 = requests.post(
        f"{settings.nvidia_base_url}/embeddings",
        headers=headers,
        json=embed_payload,
        timeout=60,
    )
    print("Embed status:", resp2.status_code)
    if resp2.ok:
        data = resp2.json()["data"]
        print(f"Got {len(data)} embeddings, dim={len(data[0]['embedding'])}")
    else:
        print("Embed error:", resp2.text[:500])


if __name__ == "__main__":
    main()
