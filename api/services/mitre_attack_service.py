#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
MITRE ATT&CK service for technique mapping, lookup, and coverage analysis.

Provides functionality to:
- Load and index the curated ATT&CK Enterprise technique dataset
- Map free-text TTPs to ATT&CK technique objects
- Analyze game session coverage against the ATT&CK framework
- Generate threat actor ATT&CK profiles
- Provide detection guidance for specific techniques
"""

import json
from pathlib import Path

from api.models.attack_models import ATTCKCoverageReport, ATTCKTactic, ATTCKTechnique
from api.models.schemas import GameState, ThreatActor
from api.utils.logger import setup_logger

logger = setup_logger(__name__)

# Project root is two levels up from this service file
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data" / "mitre_attack"

# Common aliases that map informal terms to technique keywords.
# Each alias key maps to one or more keywords that appear in technique
# names or descriptions so the keyword index can match them.
_KEYWORD_ALIASES: dict[str, list[str]] = {
    "rdp": ["remote", "desktop", "protocol"],
    "smb": ["smb", "admin", "shares"],
    "ssh": ["ssh"],
    "c2": ["command", "control"],
    "c&c": ["command", "control"],
    "ransomware": ["data", "encrypted", "impact"],
    "mimikatz": ["credential", "dumping", "lsass"],
    "credential-harvesting": ["credential", "dumping"],
    "credential-theft": ["credential", "dumping"],
    "pass-the-hash": ["alternate", "authentication"],
    "pass-the-ticket": ["kerberos", "tickets"],
    "kerberoasting": ["kerberos", "tickets"],
    "watering-hole": ["compromise", "infrastructure"],
    "drive-by": ["exploit", "client", "execution"],
    "webshell": ["web", "shell"],
    "web-shell": ["web", "shell"],
    "privilege-escalation": ["privilege", "escalation"],
    "privesc": ["privilege", "escalation"],
    "mfa-fatigue": ["multi-factor", "authentication", "request"],
    "mfa-bombing": ["multi-factor", "authentication", "request"],
    "data-theft": ["data", "exfiltration"],
    "data-exfil": ["data", "exfiltration"],
    "living-off-the-land": ["system", "binary", "proxy"],
    "lotl": ["system", "binary", "proxy"],
    "lolbin": ["system", "binary", "proxy"],
    "dns-tunneling": ["protocol", "tunneling", "dns"],
    "log-clearing": ["indicator", "removal", "event", "logs"],
    "arp-spoofing": ["adversary", "middle"],
    "mitm": ["adversary", "middle"],
    "man-in-the-middle": ["adversary", "middle"],
    "ddos": ["network", "denial", "service"],
    "dos": ["network", "denial", "service"],
    "supply-chain": ["supply", "chain", "compromise"],
    "wmi": ["windows", "management", "instrumentation"],
    "zero-day": ["exploitation", "privilege"],
    "spearphish": ["spearphishing"],
    "brute-force": ["brute", "force"],
    "password-spray": ["brute", "force"],
    "token-theft": ["access", "token", "manipulation"],
}


class MITREAttackService:
    """
    Service for MITRE ATT&CK technique mapping and analysis.

    Loads a curated subset of ATT&CK Enterprise techniques and provides
    methods for free-text TTP mapping, session coverage analysis, and
    threat actor profiling against the ATT&CK framework.
    """

    def __init__(
        self,
        techniques_path: Path | None = None,
        tactics_path: Path | None = None,
    ) -> None:
        """
        Load ATT&CK data files and build lookup indexes.

        Args:
            techniques_path: Override path to enterprise_attack.json.
            tactics_path: Override path to attack_tactics.json.
        """
        self._techniques: dict[str, ATTCKTechnique] = {}
        self._tactics: dict[str, ATTCKTactic] = {}
        self._tactic_index: dict[str, list[str]] = {}
        self._keyword_index: dict[str, list[str]] = {}

        techniques_file = techniques_path or (_DATA_DIR / "enterprise_attack.json")
        tactics_file = tactics_path or (_DATA_DIR / "attack_tactics.json")

        self._load_tactics(tactics_file)
        self._load_techniques(techniques_file)
        self._build_keyword_index()

        logger.info(
            "MITREAttackService initialized: %d techniques, %d tactics, %d keywords",
            len(self._techniques),
            len(self._tactics),
            len(self._keyword_index),
        )

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_tactics(self, path: Path) -> None:
        """Load tactics from JSON and build tactic lookup."""
        try:
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
            for entry in raw:
                tactic = ATTCKTactic(**entry)
                self._tactics[tactic.shortname] = tactic
                self._tactics[tactic.tactic_id] = tactic
                # Initialise the tactic index bucket
                if tactic.shortname not in self._tactic_index:
                    self._tactic_index[tactic.shortname] = []
            logger.info("Loaded %d tactics from %s", len(raw), path)
        except FileNotFoundError:
            logger.error("Tactics file not found: %s", path)
            raise
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in tactics file %s: %s", path, exc)
            raise

    def _load_techniques(self, path: Path) -> None:
        """Load techniques from JSON and populate technique + tactic indexes."""
        try:
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
            for entry in raw:
                technique = ATTCKTechnique(**entry)
                self._techniques[technique.technique_id] = technique
                # Add to tactic index
                tactic_key = technique.tactic
                if tactic_key not in self._tactic_index:
                    self._tactic_index[tactic_key] = []
                self._tactic_index[tactic_key].append(technique.technique_id)
            logger.info("Loaded %d techniques from %s", len(raw), path)
        except FileNotFoundError:
            logger.error("Techniques file not found: %s", path)
            raise
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in techniques file %s: %s", path, exc)
            raise

    def _build_keyword_index(self) -> None:
        """
        Build a keyword index from technique names and descriptions.

        Each word in a technique name becomes a keyword pointing to that
        technique.  Common aliases from ``_KEYWORD_ALIASES`` are also
        indexed so that informal terms (e.g. "rdp", "ransomware") resolve
        correctly.
        """
        for tid, technique in self._techniques.items():
            # Index words from the technique name
            name_words = technique.name.lower().replace("/", " ").replace("-", " ").split()
            for word in name_words:
                word = word.strip("()")
                if len(word) < 2:
                    continue
                self._keyword_index.setdefault(word, [])
                if tid not in self._keyword_index[word]:
                    self._keyword_index[word].append(tid)

        # Add alias mappings: for each alias, find techniques whose
        # keyword set overlaps with the alias target words.
        for alias, target_words in _KEYWORD_ALIASES.items():
            matching_ids: list[str] = []
            for tid, technique in self._techniques.items():
                name_lower = technique.name.lower()
                # Technique matches if ALL target words appear in name
                if all(tw in name_lower for tw in target_words) and tid not in matching_ids:
                    matching_ids.append(tid)
            if matching_ids:
                self._keyword_index.setdefault(alias, [])
                for mid in matching_ids:
                    if mid not in self._keyword_index[alias]:
                        self._keyword_index[alias].append(mid)

        logger.debug("Keyword index contains %d unique keywords", len(self._keyword_index))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def map_ttp_to_attack(self, ttp_text: str) -> list[ATTCKTechnique]:
        """
        Map free-text TTP descriptions to ATT&CK techniques.

        The algorithm attempts, in order:
        1. Exact technique_id match (input starts with "T").
        2. Tactic shortname match (returns all techniques in that tactic).
        3. Keyword search against the keyword index.

        Args:
            ttp_text: Free-text TTP string such as "phishing",
                      "lateral-movement", "T1566", or "credential-harvesting".

        Returns:
            A deduplicated list of matching ATTCKTechnique objects, max 5.
        """
        if not ttp_text or not ttp_text.strip():
            return []

        text = ttp_text.strip()
        results: list[ATTCKTechnique] = []
        seen_ids: set = set()

        def _add(technique: ATTCKTechnique) -> None:
            if technique.technique_id not in seen_ids:
                seen_ids.add(technique.technique_id)
                results.append(technique)

        # 1. Exact technique_id match
        if text.upper().startswith("T"):
            technique = self._techniques.get(text.upper())
            if technique:
                _add(technique)
                return results[:5]

        # 2. Tactic shortname match
        normalised = text.lower().strip()
        if normalised in self._tactic_index:
            for tid in self._tactic_index[normalised]:
                tech = self._techniques.get(tid)
                if tech:
                    _add(tech)
                if len(results) >= 5:
                    return results[:5]
            if results:
                return results[:5]

        # 3. Keyword search
        search_terms = normalised.replace("-", " ").replace("_", " ").split()
        # Also try the full normalised string as a single alias lookup
        search_keys = [normalised] + search_terms

        candidate_scores: dict[str, int] = {}
        for term in search_keys:
            term_clean = term.strip()
            if term_clean in self._keyword_index:
                for tid in self._keyword_index[term_clean]:
                    candidate_scores[tid] = candidate_scores.get(tid, 0) + 1

        # Sort by match score (descending), then by technique_id for stability
        sorted_candidates = sorted(
            candidate_scores.items(),
            key=lambda x: (-x[1], x[0]),
        )

        for tid, _score in sorted_candidates:
            tech = self._techniques.get(tid)
            if tech:
                _add(tech)
            if len(results) >= 5:
                break

        return results[:5]

    def get_technique(self, technique_id: str) -> ATTCKTechnique | None:
        """
        Look up a single technique by its ATT&CK ID.

        Args:
            technique_id: ATT&CK technique ID (e.g., "T1566").

        Returns:
            The matching ATTCKTechnique or None if not found.
        """
        return self._techniques.get(technique_id.upper())

    def get_techniques_by_tactic(self, tactic: str) -> list[ATTCKTechnique]:
        """
        Return all techniques belonging to a given tactic.

        Accepts both tactic shortnames (e.g., "initial-access") and
        tactic IDs (e.g., "TA0001").

        Args:
            tactic: Tactic shortname or tactic ID.

        Returns:
            List of ATTCKTechnique objects for that tactic.
        """
        # Resolve tactic_id to shortname if needed
        lookup_key = tactic
        if tactic.upper().startswith("TA"):
            tactic_obj = self._tactics.get(tactic.upper())
            if tactic_obj:
                lookup_key = tactic_obj.shortname

        technique_ids = self._tactic_index.get(lookup_key, [])
        return [self._techniques[tid] for tid in technique_ids if tid in self._techniques]

    def analyze_session_coverage(self, game_state: GameState) -> ATTCKCoverageReport:
        """
        Analyze ATT&CK technique coverage for a game session.

        Collects all active, detected, and mitigated techniques from the
        threat actor states in the game, then computes per-tactic breakdown
        and overall detection coverage.

        Args:
            game_state: The current GameState containing threat_states.

        Returns:
            An ATTCKCoverageReport with coverage statistics.
        """
        exercised: set = set()
        detected: set = set()
        mitigated: set = set()

        for _threat_id, threat_state in game_state.threat_states.items():
            for tid in threat_state.active_techniques:
                exercised.add(tid)
            for tid in threat_state.detected_techniques:
                detected.add(tid)
            for tid in threat_state.mitigated_techniques:
                mitigated.add(tid)

        # Build per-tactic coverage
        coverage_by_tactic: dict[str, dict[str, int]] = {}
        for tactic_shortname, technique_ids in self._tactic_index.items():
            # Only include tactics that have a proper tactic object (skip IDs)
            if tactic_shortname.upper().startswith("TA"):
                continue

            tactic_exercised = [tid for tid in technique_ids if tid in exercised]
            tactic_detected = [tid for tid in technique_ids if tid in detected]
            tactic_mitigated = [tid for tid in technique_ids if tid in mitigated]

            if tactic_exercised:
                coverage_by_tactic[tactic_shortname] = {
                    "total": len(tactic_exercised),
                    "detected": len(tactic_detected),
                    "mitigated": len(tactic_mitigated),
                }

        # Calculate overall coverage percentage
        coverage_pct = 0.0
        if exercised:
            coverage_pct = (len(detected) / len(exercised)) * 100.0

        # Identify gaps (exercised but not detected)
        gaps = sorted(exercised - detected)

        report = ATTCKCoverageReport(
            techniques_exercised=sorted(exercised),
            techniques_detected=sorted(detected),
            techniques_mitigated=sorted(mitigated),
            coverage_by_tactic=coverage_by_tactic,
            coverage_percentage=round(coverage_pct, 1),
            gaps=gaps,
        )

        logger.info(
            "Session %s coverage: %.1f%% (%d/%d techniques detected, %d gaps)",
            game_state.session_id,
            coverage_pct,
            len(detected),
            len(exercised),
            len(gaps),
        )

        return report

    def get_threat_actor_attack_profile(self, threat_actor: ThreatActor) -> list[ATTCKTechnique]:
        """
        Build an ATT&CK technique profile for a threat actor.

        If the threat actor has explicit ``attack_techniques`` IDs, those
        are resolved directly.  Otherwise, the actor's ``ttps`` list is
        mapped via ``map_ttp_to_attack``.

        Args:
            threat_actor: A ThreatActor model instance.

        Returns:
            List of ATTCKTechnique objects associated with this actor.
        """
        seen_ids: set = set()
        results: list[ATTCKTechnique] = []

        # Prefer explicit ATT&CK technique IDs
        if threat_actor.attack_techniques:
            for tid in threat_actor.attack_techniques:
                technique = self.get_technique(tid)
                if technique and technique.technique_id not in seen_ids:
                    seen_ids.add(technique.technique_id)
                    results.append(technique)
            if results:
                logger.debug(
                    "Resolved %d explicit ATT&CK techniques for actor '%s'",
                    len(results),
                    threat_actor.name,
                )
                return results

        # Fall back to TTP text mapping
        for ttp in threat_actor.ttps:
            mapped = self.map_ttp_to_attack(ttp)
            for technique in mapped:
                if technique.technique_id not in seen_ids:
                    seen_ids.add(technique.technique_id)
                    results.append(technique)

        logger.debug(
            "Mapped %d TTPs to %d ATT&CK techniques for actor '%s'",
            len(threat_actor.ttps),
            len(results),
            threat_actor.name,
        )

        return results

    def suggest_detection_for_technique(self, technique_id: str) -> str:
        """
        Return detection guidance for a given technique.

        Args:
            technique_id: ATT&CK technique ID (e.g., "T1566").

        Returns:
            Detection guidance string, or a message indicating the
            technique was not found.
        """
        technique = self.get_technique(technique_id)
        if technique:
            return technique.detection
        return f"Technique {technique_id} not found in the ATT&CK dataset."

    def resolve_ttps_to_attack(self, ttps: list[str]) -> list[str]:
        """
        Resolve a list of free-text TTPs to deduplicated ATT&CK technique IDs.

        Args:
            ttps: List of free-text TTP strings.

        Returns:
            Deduplicated list of ATT&CK technique IDs.
        """
        seen: set = set()
        result: list[str] = []

        for ttp in ttps:
            techniques = self.map_ttp_to_attack(ttp)
            for technique in techniques:
                if technique.technique_id not in seen:
                    seen.add(technique.technique_id)
                    result.append(technique.technique_id)

        logger.debug("Resolved %d TTPs to %d unique ATT&CK IDs", len(ttps), len(result))
        return result
