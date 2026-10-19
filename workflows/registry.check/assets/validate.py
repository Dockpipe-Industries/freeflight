"""Validate official registry metadata; no credentials or publication operations."""
import hashlib
import json
from pathlib import Path
import urllib.request

import jsonschema

SCHEMA_URL = "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"
SCHEMA_SHA256 = "3fba09590c99f61735d234822279f4223fab9e300c0a81e81c91ab62a4114de0"
root = Path(__file__).resolve().parents[3]
cache = root / "bin/.local/registry/server.schema.json"
cache.parent.mkdir(parents=True, exist_ok=True)
if not cache.exists():
    with urllib.request.urlopen(SCHEMA_URL, timeout=30) as response:
        payload = response.read(1024 * 1024)
    if hashlib.sha256(payload).hexdigest() != SCHEMA_SHA256:
        raise RuntimeError("Official registry schema checksum changed; review before updating")
    cache.write_bytes(payload)
payload = cache.read_bytes()
if hashlib.sha256(payload).hexdigest() != SCHEMA_SHA256:
    raise RuntimeError("Cached registry schema checksum mismatch")
metadata = json.loads((root / "server.json").read_text())
jsonschema.validate(metadata, json.loads(payload))
if metadata["version"] != (root / "VERSION").read_text().strip():
    raise RuntimeError("server.json and VERSION disagree")
if not metadata.get("packages") and not metadata.get("remotes"):
    print("Registry metadata schema valid; DRAFT: no qualified installable artifact, publication unavailable")
else:
    print("Registry metadata schema valid; artifact availability and publisher authorization need separate verification")
