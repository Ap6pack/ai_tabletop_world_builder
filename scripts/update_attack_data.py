#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Download and curate MITRE ATT&CK Enterprise data.

Fetches the latest ATT&CK Enterprise dataset from MITRE's GitHub repo
and builds a curated JSON file for the platform.

Usage:
    python scripts/update_attack_data.py
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx required: pip install httpx")
    sys.exit(1)

ATTACK_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "mitre_attack"


def fetch_attack_data() -> dict:
    """Download the ATT&CK Enterprise STIX bundle."""
    print(f"Downloading ATT&CK Enterprise data from {ATTACK_URL}...")
    resp = httpx.get(ATTACK_URL, timeout=60.0)
    resp.raise_for_status()
    return resp.json()


def extract_techniques(stix_bundle: dict) -> list[dict]:
    """Extract and curate technique objects from STIX bundle."""
    techniques = []
    # Build tactic mapping from x-mitre-tactic objects
    tactic_map = {}
    for obj in stix_bundle.get("objects", []):
        if obj.get("type") == "x-mitre-tactic":
            shortname = obj.get("x_mitre_shortname", "")
            ext_refs = obj.get("external_references", [])
            for ref in ext_refs:
                if ref.get("source_name") == "mitre-attack":
                    tactic_map[shortname] = ref.get("external_id", "")

    # Extract attack-pattern objects (techniques)
    for obj in stix_bundle.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue

        ext_refs = obj.get("external_references", [])
        technique_id = ""
        for ref in ext_refs:
            if ref.get("source_name") == "mitre-attack":
                technique_id = ref.get("external_id", "")
                break

        if not technique_id:
            continue

        # Get tactic (first kill chain phase)
        phases = obj.get("kill_chain_phases", [])
        tactic = phases[0]["phase_name"] if phases else "unknown"
        tactic_id = tactic_map.get(tactic, "")

        # Get platforms
        platforms = obj.get("x_mitre_platforms", [])

        # Get data sources
        data_sources = []
        for ds in obj.get("x_mitre_data_sources", []):
            data_sources.append(ds.split(":")[0].strip() if ":" in ds else ds)
        data_sources = list(set(data_sources))

        # Get detection
        detection = obj.get("x_mitre_detection", "")
        if len(detection) > 300:
            detection = detection[:297] + "..."

        is_sub = obj.get("x_mitre_is_subtechnique", False)
        parent_id = None
        if is_sub and "." in technique_id:
            parent_id = technique_id.split(".")[0]

        techniques.append(
            {
                "technique_id": technique_id,
                "name": obj.get("name", ""),
                "tactic": tactic,
                "tactic_id": tactic_id,
                "description": (obj.get("description", "")[:200] + "...")
                if len(obj.get("description", "")) > 200
                else obj.get("description", ""),
                "platforms": platforms,
                "data_sources": data_sources,
                "detection": detection,
                "mitigations": [],  # Would require resolving relationship objects
                "is_subtechnique": is_sub,
                "parent_technique_id": parent_id,
            }
        )

    return sorted(techniques, key=lambda t: t["technique_id"])


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    stix_data = fetch_attack_data()
    techniques = extract_techniques(stix_data)

    output_path = OUTPUT_DIR / "enterprise_attack.json"
    output_path.write_text(json.dumps(techniques, indent=2) + "\n")

    print(f"Extracted {len(techniques)} techniques to {output_path}")
    print(f"Updated at {datetime.now(UTC).isoformat()}")

    # Verify tactic coverage
    tactics = set(t["tactic"] for t in techniques)
    print(f"Tactics covered: {len(tactics)}")
    for tactic in sorted(tactics):
        count = sum(1 for t in techniques if t["tactic"] == tactic)
        print(f"  {tactic}: {count} techniques")


if __name__ == "__main__":
    main()
