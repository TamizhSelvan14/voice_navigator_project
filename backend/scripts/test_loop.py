"""Test nemotron-parse in a loop to verify rate limiting fix."""
import fitz
import base64
import json
import time
import requests
import sys

sys.path.insert(0, "/Users/spartan/Desktop/coding/277_hacks/voice_navigator_project/backend")
from app.config import settings

pdf = fitz.open("/Users/spartan/Desktop/coding/277_hacks/voice_navigator_project/backend/data/raw/california_drivers_handbook_2025.pdf")

for i in range(10):
    page = pdf[i]
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
        "model": settings.parse_model,
        "messages": [{"role": "user", "content": content}],
        "tools": [{"type": "function", "function": {"name": "markdown_no_bbox"}}],
        "tool_choice": {"type": "function", "function": {"name": "markdown_no_bbox"}},
        "max_tokens": 8192,
    }

    print(f"Page {i+1}: sending request...")
    for attempt in range(4):
        try:
            resp = requests.post(settings.nvidia_parse_url, headers=headers, json=payload, timeout=120)
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                body = resp.json()
                choices = body.get("choices", [])
                if choices:
                    args = choices[0].get("message", {}).get("tool_calls", [{}])[0].get("function", {}).get("arguments", "")
                    print(f"  OK, args length: {len(args)}")
                break
            elif resp.status_code == 500:
                wait = 5 * (attempt + 1)
                print(f"  500 error, retry {attempt+1}/4, waiting {wait}s...")
                time.sleep(wait)
                continue
            else:
                print(f"  Error: {resp.text[:300]}")
                break
        except (requests.ConnectionError, ConnectionResetError) as e:
            wait = 5 * (attempt + 1)
            print(f"  Connection error, retry {attempt+1}/4, waiting {wait}s... ({type(e).__name__})")
            time.sleep(wait)
            continue
    
    time.sleep(5)

print("Done!")
