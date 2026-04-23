"""
Test end-to-end del flusso demo Rooting Future.

Uso:
    python scripts/test_demo.py                        # testa HF Space di produzione
    python scripts/test_demo.py --local                # testa localhost:5000
    python scripts/test_demo.py --url http://...       # URL custom

Output: scarica i 3 documenti in scripts/output/
"""

import argparse
import time
import sys
from pathlib import Path
import urllib.request
import urllib.error
import json

DEFAULT_URL = "https://mtornani-rooting-future.hf.space"
LOCAL_URL   = "http://localhost:5000"
POLL_INTERVAL = 3   # secondi tra un poll e l'altro
TIMEOUT       = 300 # secondi massimi di attesa


def get(url: str) -> dict:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def post(url: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def download(url: str, dest: Path):
    urllib.request.urlretrieve(url, dest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--url", default=None)
    args = parser.parse_args()

    base = args.url or (LOCAL_URL if args.local else DEFAULT_URL)
    out  = Path(__file__).parent / "output"
    out.mkdir(exist_ok=True)

    print(f"\n🧪 Test Demo — {base}")
    print("=" * 60)

    # 1. Trigger generazione
    print("\n[1/4] POST /api/demo/generate ...", end=" ", flush=True)
    try:
        resp = post(f"{base}/api/demo/generate", {})
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"FAIL ({e.code})\n{body}")
        sys.exit(1)
    except Exception as e:
        print(f"FAIL — {e}")
        sys.exit(1)

    if not resp.get("success"):
        print(f"FAIL — {resp}")
        sys.exit(1)

    project_id = resp["project_id"]
    questionnaires = resp.get("questionnaires_found", [])
    print(f"OK — project_id={project_id}")
    print(f"     Questionari trovati: {questionnaires}")

    # 2. Polling status
    print("\n[2/4] Polling generazione (max {}s) ...".format(TIMEOUT))
    plan_id = None
    elapsed = 0
    while elapsed < TIMEOUT:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        try:
            status = get(f"{base}/api/generation-status/{project_id}")
        except Exception as e:
            print(f"  [{elapsed:>3}s] poll error: {e}")
            continue

        pct     = status.get("progress", 0)
        msg     = status.get("message", "...")
        state   = status.get("status", "?")
        print(f"  [{elapsed:>3}s] {state:12} {pct:>3}%  {msg[:60]}")

        if state == "completed":
            plan_id = (status.get("data") or {}).get("plan_id")
            break
        if state == "error":
            print(f"\n❌ Errore: {msg}")
            sys.exit(1)

    if not plan_id:
        print(f"\n❌ Timeout dopo {TIMEOUT}s — piano non completato")
        sys.exit(1)

    print(f"\n  ✅ Piano generato — plan_id={plan_id}")

    # 3. Scarica i 3 documenti
    print("\n[3/4] Download documenti ...")
    docs = [
        ("executive", f"{base}/api/export/{plan_id}/executive", out / "report_esecutivo.html"),
        ("html",      f"{base}/api/export/{plan_id}/html",      out / "piano_completo.html"),
        ("onepager",  f"{base}/api/export/{plan_id}/onepager",  out / "one_pager.html"),
    ]
    for name, url, dest in docs:
        try:
            download(url, dest)
            size = dest.stat().st_size
            print(f"  ✅ {name:12} → {dest.name} ({size/1024:.0f} KB)")
        except Exception as e:
            print(f"  ❌ {name:12} → FAIL: {e}")

    # 4. Riepilogo
    print("\n[4/4] Output salvato in:")
    for f in out.glob("*.html"):
        print(f"  {f}")
    print("\n✅ Test completato.\n")


if __name__ == "__main__":
    main()
