#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""Generate a CycloneDX SBOM from requirements.txt."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path


def parse_requirements(req_path: Path) -> list[dict]:
    """Parse requirements.txt into a list of component dicts."""
    components = []
    pattern = re.compile(r"^([A-Za-z0-9_.-]+)\s*(?:==|>=|~=)\s*([A-Za-z0-9_.+-]+)")

    for line in req_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = pattern.match(line)
        if match:
            name, version = match.group(1), match.group(2)
            components.append({
                "type": "library",
                "name": name,
                "version": version,
                "purl": f"pkg:pypi/{name.lower()}@{version}",
            })
    return components


def generate_sbom(project_root: Path) -> dict:
    """Build a minimal CycloneDX 1.5 JSON SBOM."""
    req_path = project_root / "requirements.txt"
    if not req_path.exists():
        raise FileNotFoundError(f"requirements.txt not found at {req_path}")

    components = parse_requirements(req_path)
    now = datetime.now(timezone.utc).isoformat()

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": now,
            "tools": [{"name": "generate_sbom.py", "version": "1.0.0"}],
            "component": {
                "type": "application",
                "name": "ai-tabletop-world-builder",
            },
        },
        "components": components,
    }


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    sbom = generate_sbom(project_root)
    output_path = project_root / "sbom.json"
    output_path.write_text(json.dumps(sbom, indent=2) + "\n")
    print(f"SBOM generated: {output_path}")
    print(f"Components: {len(sbom['components'])}")


if __name__ == "__main__":
    main()
