"""Download World Bank indicator data once and save as local JSON files."""
from __future__ import annotations

import json
from pathlib import Path

import httpx

INDICATORS = {
    "gdp": "https://api.worldbank.org/v2/country/WLD/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=1000",
    "co2": "https://api.worldbank.org/v2/country/WLD/indicator/EN.GHG.CO2.AG.MT.CE.AR5?format=json&per_page=1000",
    "agri_land": "https://api.worldbank.org/v2/country/WLD/indicator/AG.LND.AGRI.ZS?format=json&per_page=1000",
}

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "worldbank"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30) as client:
        for key, url in INDICATORS.items():
            print(f"Fetching {key} ...")
            resp = client.get(url)
            resp.raise_for_status()
            payload = resp.json()

            out_path = OUT_DIR / f"{key}.json"
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            count = len(payload[1]) if isinstance(payload, list) and len(payload) >= 2 and payload[1] else 0
            print(f"  Saved {count} records to {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
