"""
Scenario Library Service for browsing, rating, sharing, and forking scenarios.

Provides a community-style library where users can discover pre-built
scenario templates, share their own scenarios, and fork others' work
for customization.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from api.utils.logger import setup_logger

logger = setup_logger(__name__)


class ScenarioLibraryService:
    """Service for managing the scenario library."""

    LIBRARY_DIR = Path("data/library")
    TEMPLATES_DIR = Path("scenarios/templates")

    def __init__(self):
        """Initialize library service and create directories if needed."""
        self.LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        self._initialize_templates()

    def list_scenarios(
        self,
        category: str = None,
        difficulty: str = None,
        sort_by: str = "rating",
    ) -> List[Dict]:
        """List library scenarios with optional filters and sorting."""
        scenarios = []
        for path in self.LIBRARY_DIR.glob("*.json"):
            scenario = self._load_scenario(path.stem)
            if scenario is None:
                continue
            if category and scenario.get("category") != category:
                continue
            if difficulty and scenario.get("difficulty") != difficulty:
                continue
            scenarios.append(scenario)

        reverse = sort_by in ("rating", "rating_count", "created_at")
        scenarios.sort(key=lambda s: s.get(sort_by, 0), reverse=reverse)
        return scenarios

    def get_scenario(self, scenario_id: str) -> Optional[Dict]:
        """Get full scenario data by ID."""
        return self._load_scenario(scenario_id)

    def add_to_library(self, scenario_data: Dict, author: str = "system") -> Dict:
        """Add a scenario to the library with metadata."""
        scenario_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()

        scenario = {
            "id": scenario_id,
            "name": scenario_data.get("name", "Untitled Scenario"),
            "description": scenario_data.get("description", ""),
            "industry": scenario_data.get("industry", "general"),
            "difficulty": scenario_data.get("difficulty", "intermediate"),
            "category": scenario_data.get("category", "incident-response"),
            "author": author,
            "rating": 0.0,
            "rating_count": 0,
            "ratings": {},
            "tags": scenario_data.get("tags", []),
            "visibility": "public",
            "original_id": None,
            "created_at": now,
            "updated_at": now,
            "scenario_data": scenario_data,
        }

        self._save_scenario(scenario)
        logger.info(f"Added scenario to library: {scenario_id} by {author}")
        return scenario

    def rate_scenario(
        self, scenario_id: str, rating: int, user_id: str = "anonymous"
    ) -> Dict:
        """Rate a scenario 1-5, updating the running average."""
        scenario = self._load_scenario(scenario_id)
        if scenario is None:
            return {"error": "Scenario not found"}

        rating = max(1, min(5, rating))
        ratings = scenario.get("ratings", {})
        ratings[user_id] = rating
        scenario["ratings"] = ratings

        total = sum(ratings.values())
        count = len(ratings)
        scenario["rating"] = round(total / count, 2) if count > 0 else 0.0
        scenario["rating_count"] = count
        scenario["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._save_scenario(scenario)
        logger.info(
            f"Scenario {scenario_id} rated {rating} by {user_id} "
            f"(avg: {scenario['rating']})"
        )
        return {
            "scenario_id": scenario_id,
            "rating": scenario["rating"],
            "rating_count": scenario["rating_count"],
        }

    def fork_scenario(
        self, scenario_id: str, user_id: str = "anonymous"
    ) -> Dict:
        """Create a copy of a scenario with a new ID."""
        original = self._load_scenario(scenario_id)
        if original is None:
            return {"error": "Scenario not found"}

        new_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()

        forked = {
            **original,
            "id": new_id,
            "name": f"{original.get('name', 'Scenario')} (fork)",
            "author": user_id,
            "rating": 0.0,
            "rating_count": 0,
            "ratings": {},
            "original_id": scenario_id,
            "created_at": now,
            "updated_at": now,
            "visibility": "private",
        }

        self._save_scenario(forked)
        logger.info(
            f"Scenario {scenario_id} forked to {new_id} by {user_id}"
        )
        return forked

    def share_scenario(
        self, scenario_id: str, visibility: str = "public"
    ) -> Dict:
        """Update scenario visibility (public/private/unlisted)."""
        scenario = self._load_scenario(scenario_id)
        if scenario is None:
            return {"error": "Scenario not found"}

        if visibility not in ("public", "private", "unlisted"):
            return {"error": "Invalid visibility. Use public, private, or unlisted."}

        scenario["visibility"] = visibility
        scenario["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_scenario(scenario)
        logger.info(f"Scenario {scenario_id} visibility set to {visibility}")
        return {"scenario_id": scenario_id, "visibility": visibility}

    def get_templates(self) -> List[Dict]:
        """Return pre-built scenario templates."""
        templates = []
        for path in self.TEMPLATES_DIR.glob("*.json"):
            try:
                with open(path, "r") as f:
                    templates.append(json.load(f))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(f"Failed to load template {path}: {exc}")
        return templates

    def search_scenarios(self, query: str) -> List[Dict]:
        """Search scenarios by name, description, and tags."""
        query_lower = query.lower()
        results = []
        for path in self.LIBRARY_DIR.glob("*.json"):
            scenario = self._load_scenario(path.stem)
            if scenario is None:
                continue
            name = scenario.get("name", "").lower()
            description = scenario.get("description", "").lower()
            tags = [t.lower() for t in scenario.get("tags", [])]
            if (
                query_lower in name
                or query_lower in description
                or any(query_lower in tag for tag in tags)
            ):
                results.append(scenario)
        return results

    def _save_scenario(self, scenario: Dict) -> None:
        """Save a scenario to a JSON file."""
        path = self.LIBRARY_DIR / f"{scenario['id']}.json"
        try:
            with open(path, "w") as f:
                json.dump(scenario, f, indent=2, default=str)
        except OSError as exc:
            logger.error(f"Failed to save scenario {scenario['id']}: {exc}")

    def _load_scenario(self, scenario_id: str) -> Optional[Dict]:
        """Load a scenario from a JSON file."""
        path = self.LIBRARY_DIR / f"{scenario_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"Failed to load scenario {scenario_id}: {exc}")
            return None

    def _initialize_templates(self) -> None:
        """Create pre-built scenario templates if they don't already exist."""
        ts = "2026-01-15T00:00:00+00:00"
        defs = [
            ("ransomware_financial", "Ransomware Attack on Financial Institution",
             "A sophisticated ransomware group has encrypted critical trading "
             "systems at a major bank. Time-sensitive recovery is needed to "
             "prevent massive financial losses.",
             "Financial Services", "advanced", "incident-response", 4.5, 12,
             ["ransomware", "financial", "encryption", "recovery"]),
            ("insider_threat_tech", "Insider Threat at Tech Company",
             "A disgruntled engineer with elevated privileges is exfiltrating "
             "proprietary source code and customer data before their last day.",
             "Technology", "intermediate", "threat-hunting", 4.2, 8,
             ["insider-threat", "data-exfiltration", "privilege-abuse"]),
            ("supply_chain_manufacturing", "Supply Chain Attack on Manufacturer",
             "A compromised firmware update from a trusted vendor has introduced "
             "a backdoor into industrial control systems across multiple plants.",
             "Manufacturing", "expert", "incident-response", 4.7, 6,
             ["supply-chain", "ics", "firmware", "backdoor"]),
            ("apt_government", "APT Targeting Government Agency",
             "A nation-state APT group has established persistent access to "
             "classified networks through a spear-phishing campaign targeting "
             "senior officials.",
             "Government", "expert", "threat-hunting", 4.8, 15,
             ["apt", "nation-state", "spear-phishing", "persistence"]),
            ("data_breach_healthcare", "Data Breach at Healthcare Organization",
             "Protected health information of 500,000 patients has been exposed "
             "through a misconfigured cloud database. HIPAA compliance and "
             "breach notification are critical.",
             "Healthcare", "intermediate", "compliance-drill", 4.3, 10,
             ["data-breach", "hipaa", "cloud", "phi", "compliance"]),
        ]
        for tid, name, desc, ind, diff, cat, rat, rc, tags in defs:
            path = self.TEMPLATES_DIR / f"{tid}.json"
            if path.exists():
                continue
            template = {
                "id": tid, "name": name, "description": desc,
                "industry": ind, "difficulty": diff, "category": cat,
                "author": "system", "rating": rat, "rating_count": rc,
                "tags": tags, "visibility": "public", "created_at": ts,
            }
            try:
                with open(path, "w") as f:
                    json.dump(template, f, indent=2)
                logger.info(f"Created template: {tid}")
            except OSError as exc:
                logger.warning(f"Failed to create template {tid}: {exc}")
