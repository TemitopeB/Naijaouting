"""
Daily exchange rates for NaijaOuting's "prices in your currency".

Writes data/fx.json: how much one naira is worth in each visitor currency, with the
date and the source. The site shows conversions as approximate and always keeps the
naira price first. Source: ExchangeRate-API's open endpoint (no key needed; attribution
required, see "credit" below).
"""
import json
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone

CURRENCIES = ["GBP", "USD", "EUR", "CAD", "GHS", "ZAR"]
URL = "https://open.er-api.com/v6/latest/NGN"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "fx.json"


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "NaijaOuting/1.0 (+https://naijaouting-ng.vercel.app)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    if d.get("result") != "success" or d.get("base_code") != "NGN":
        print("Unexpected response:", {k: d.get(k) for k in ("result", "base_code", "error-type")})
        sys.exit(1)
    rates = {c: d["rates"][c] for c in CURRENCIES if c in d.get("rates", {})}
    # sanity check: a naira is worth well under one unit of each of these currencies
    if len(rates) < 4 or any(not (0 < v < 1) for v in rates.values()):
        print("Rates look wrong, not saving:", rates)
        sys.exit(1)
    updated = datetime.fromtimestamp(d.get("time_last_update_unix", 0), tz=timezone.utc).strftime("%Y-%m-%d")
    out = {
        "base": "NGN",
        "date": updated,
        "rates": rates,
        "source": "ExchangeRate-API",
        "credit": "https://www.exchangerate-api.com",
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print("Saved", out)


if __name__ == "__main__":
    main()
