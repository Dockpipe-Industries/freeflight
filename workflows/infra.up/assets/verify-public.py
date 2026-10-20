"""Operator-side private HTTPS readiness; never required from hosted CI IPs."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "workflows/site.deploy.receive/assets"))
from receive import probe, require

metadata = json.loads((ROOT / "bin/.local/site-pipeline/deployment.json").read_text())
require(metadata["environment"] == "staging", "Production setup is not supported")
for attempt in range(30):
    try:
        probe(metadata, "https://freeflight.staging.dockpipe.com")
        print("Private staging HTTPS serves the exact qualified assets")
        break
    except Exception:
        if attempt == 29:
            raise
        time.sleep(2)
