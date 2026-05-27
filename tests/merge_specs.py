#!/usr/bin/env python3
"""Merge per-resource OpenAPI 3.1 specs into a single combined spec.

Run from the mycase-mcp root:
    python tests/merge_specs.py
Produces: tests/openapi-merged.json
"""

import json
from pathlib import Path

SPECS_DIR = Path(__file__).parent.parent / "vendor" / "api-specs"
OUT_FILE = Path(__file__).parent / "openapi-merged.json"

# Strip this prefix from all OpenAPI paths so they match the paths in endpoints.yaml,
# which omit the /v1 version segment (e.g. /v1/cases → /cases).
_PATH_STRIP_PREFIX = "/v1"


def merge_specs(specs_dir: Path) -> dict:
    merged: dict = {
        "openapi": "3.1.0",
        "info": {
            "title": "MyCase API v1 — merged",
            "version": "1.0",
            "description": "Auto-merged from per-resource spec files.",
        },
        "servers": [{"url": "https://external-integrations.mycase.com"}],
        "paths": {},
        "components": {
            "schemas": {},
            "parameters": {},
            "headers": {},
            "responses": {},
        },
    }

    for spec_file in sorted(specs_dir.glob("*.json")):
        spec = json.loads(spec_file.read_text())

        for path, methods in spec.get("paths", {}).items():
            stripped = path.removeprefix(_PATH_STRIP_PREFIX) or "/"
            if stripped not in merged["paths"]:
                merged["paths"][stripped] = {}
            merged["paths"][stripped].update(methods)

        comp = spec.get("components", {})
        for section in ("schemas", "parameters", "headers", "responses"):
            for name, value in comp.get(section, {}).items():
                merged["components"][section].setdefault(name, value)

    return merged


if __name__ == "__main__":
    if not SPECS_DIR.exists():
        print(f"Specs dir not found: {SPECS_DIR}")
        raise SystemExit(1)
    merged = merge_specs(SPECS_DIR)
    OUT_FILE.write_text(json.dumps(merged, indent=2))
    print(f"Merged {len(merged['paths'])} paths → {OUT_FILE}")
