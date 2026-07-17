#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
AI Game Master service for generating dynamic narrative and responding to player actions.
"""
from typing import Optional, Dict, Any, List
from api.models import GameState, GameResponse, IncidentEvent
from api.providers import LLMProviderFactory
from api.services import ContentPolicyService
from datetime import datetime
import json


class GameMasterService:
    """
    AI Game Master that narrates incidents and responds to player actions.

    This service acts as the "dungeon master" for cybersecurity war games,
    creating dynamic narratives based on player actions and game state.
    """

    def __init__(self, llm_provider=None, content_policy=None):
        """Initialize the game master service."""
        self._llm_provider = llm_provider
        self.content_policy = content_policy or ContentPolicyService.get_policy("educational")

    @property
    def llm_provider(self):
        """Lazily instantiate the LLM provider so construction needs no API key."""
        if self._llm_provider is None:
            self._llm_provider = LLMProviderFactory.create_provider()
        return self._llm_provider

    @llm_provider.setter
    def llm_provider(self, value):
        self._llm_provider = value

    async def start_game(self, game_state: GameState) -> str:
        """
        Generate the initial game narrative.

        Args:
            game_state: Current game state

        Returns:
            Opening narrative text
        """
        prompt = self._build_start_prompt(game_state)

        system_message = self._build_system_message(game_state)

        result = await self.llm_provider.complete(
            prompt=prompt,
            system_message=system_message,
            temperature=0.8,
            max_tokens=500
        )

        return result["content"].strip()

    async def process_action(
        self,
        action: str,
        game_state: GameState
    ) -> Dict[str, Any]:
        """
        Process a player action and generate response.

        Args:
            action: Player's action description
            game_state: Current game state

        Returns:
            Dict with narrative, consequences, and game state updates
        """
        prompt = self._build_action_prompt(action, game_state)

        system_message = self._build_system_message(game_state)

        result = await self.llm_provider.complete(
            prompt=prompt,
            system_message=system_message,
            temperature=0.7,
            max_tokens=800
        )

        response_text = result["content"].strip()

        # Parse the response to extract structured data
        parsed = self._parse_game_master_response(response_text, game_state)

        return parsed

    def _build_system_message(self, game_state: GameState) -> str:
        """Build system message for the game master."""

        org = game_state.organization

        system_message = f"""You are an AI Game Master running a cybersecurity incident response training simulation.

SCENARIO CONTEXT:
- Organization: {org.name} ({org.industry})
- Security Posture: {org.security_posture}
- Player Role: {game_state.player_role}
- Scenario Type: {game_state.current_scenario}

GAME MASTER RESPONSIBILITIES:
1. Narrate realistic cybersecurity incidents in 2-3 sentences
2. Respond to player actions with realistic consequences
3. Simulate threat actor behavior
4. Track what the player discovers and what remains hidden
5. Be educational but challenging
6. Maintain tension and realism

NARRATIVE STYLE:
- Write in second person ("You...", "Your team...")
- Be concise (2-3 sentences per response)
- Focus on what the player observes and discovers
- Use proper cybersecurity terminology
- Show consequences of actions (good and bad)

REALISM RULES:
- Tools take time to run
- Some actions require privileges the player may not have
- Investigation reveals clues gradually
- Threat actors react to defensive actions
- Systems have realistic limitations

EDUCATIONAL FOCUS:
- Guide players toward good security practices
- Don't give away answers
- Provide hints through observations
- Reward thorough investigation
- Penalize reckless actions

Content Policy: {self.content_policy.level}"""

        return system_message

    def _build_start_prompt(self, game_state: GameState) -> str:
        """Build prompt for game start."""

        org = game_state.organization

        # Get a threat actor if available
        threat_actor = org.threat_actors[0] if org.threat_actors else None

        # Get a vulnerable system if available
        vulnerable_system = None
        if org.departments:
            for dept in org.departments:
                if dept.systems:
                    for system in dept.systems:
                        if system.vulnerabilities:
                            vulnerable_system = system
                            break
                    if vulnerable_system:
                        break

        prompt = f"""You are starting a cybersecurity incident response training simulation.

SCENARIO SETUP:
- Organization: {org.name}
- Your Role: {game_state.player_role}
- Time: 09:45 AM (Monday)
- Current Status: Normal operations

BACKGROUND:
{org.description if hasattr(org, 'description') else f"{org.name} is a {org.size} {org.industry} organization with a {org.security_posture} security posture."}

INITIAL SITUATION:
You've just arrived at your desk. Your SIEM dashboard shows a new HIGH severity alert that was triggered 5 minutes ago.

Generate the OPENING SCENE for this incident:
1. Describe the alert that appears on their screen (be specific)
2. What system or department is affected
3. What the initial indicators are
4. Create a sense of urgency but not panic

Write the opening scene in 2-3 sentences. Make it realistic and engaging.

OPENING SCENE:"""

        return prompt

    def _build_action_prompt(self, action: str, game_state: GameState) -> str:
        """Build prompt for processing player action."""

        org = game_state.organization
        recent_events = game_state.incident_timeline[-5:] if game_state.incident_timeline else []

        # Build context from recent events
        timeline_context = "\n".join([
            f"- [{event.timestamp.strftime('%H:%M')}] {event.description}"
            for event in recent_events
        ])

        # Available tools
        tools_list = ", ".join(game_state.inventory.tools.keys())
        access_list = ", ".join(game_state.inventory.access_levels)

        prompt = f"""CURRENT SITUATION:
Organization: {org.name}
Time Elapsed: {game_state.time_elapsed} minutes
Player Role: {game_state.player_role}

RECENT EVENTS:
{timeline_context if timeline_context else "- Game just started"}

PLAYER'S AVAILABLE TOOLS:
{tools_list}

PLAYER'S ACCESS LEVELS:
{access_list}

PLAYER ACTION:
"{action}"

INSTRUCTIONS:
1. Evaluate if the action is realistic given the player's role and tools
2. Determine what the player would discover or accomplish
3. Describe the outcome in 2-3 sentences
4. Include any new information they learn
5. If the action is not possible, explain why briefly

After your narrative response, provide structured data in this format:

STRUCTURED_DATA:
{{
    "action_valid": true/false,
    "consequences": "brief description of what happened",
    "discoveries": ["list", "of", "new", "findings"],
    "inventory_changes": {{"tool_name": +1 or -1}},
    "score_change": {{\"points\": 0, \"reason\": \"why\"}},
    "new_events": [
        {{
            "type": "detection/action/consequence/escalation",
            "description": "event description",
            "severity": "critical/high/medium/low/info",
            "actor": "player/threat_actor/system"
        }}
    ],
    "hints": ["helpful", "suggestions"]
}}

NARRATIVE RESPONSE:"""

        return prompt

    def _parse_game_master_response(self, response_text: str, game_state: GameState) -> Dict[str, Any]:
        """Parse game master response to extract structured data."""

        # Split narrative from structured data
        if "STRUCTURED_DATA:" in response_text:
            parts = response_text.split("STRUCTURED_DATA:")
            narrative = parts[0].strip()

            try:
                # Try to parse JSON
                json_text = parts[1].strip()
                if json_text.startswith("```"):
                    json_text = json_text.split("```")[1]
                    if json_text.startswith("json"):
                        json_text = json_text[4:]
                    json_text = json_text.strip()

                structured = json.loads(json_text)
            except:
                # If parsing fails, use defaults
                structured = {
                    "action_valid": True,
                    "consequences": "Action completed",
                    "discoveries": [],
                    "inventory_changes": {},
                    "score_change": {"points": 0, "reason": ""},
                    "new_events": [],
                    "hints": []
                }
        else:
            # No structured data found, use narrative only
            narrative = response_text
            structured = {
                "action_valid": True,
                "consequences": "Action completed",
                "discoveries": [],
                "inventory_changes": {},
                "score_change": {"points": 0, "reason": ""},
                "new_events": [],
                "hints": []
            }

        # Convert new_events to IncidentEvent objects
        events = []
        for event_data in structured.get("new_events", []):
            events.append(IncidentEvent(
                timestamp=datetime.now(),
                event_type=event_data.get("type", "action"),
                description=event_data.get("description", ""),
                severity=event_data.get("severity", "info"),
                actor=event_data.get("actor", "system")
            ))

        return {
            "narrative": narrative,
            "action_valid": structured.get("action_valid", True),
            "consequences": structured.get("consequences", ""),
            "discoveries": structured.get("discoveries", []),
            "inventory_changes": structured.get("inventory_changes", {}),
            "score_change": structured.get("score_change", {"points": 0, "reason": ""}),
            "new_events": events,
            "hints": structured.get("hints", [])
        }

    async def generate_hint(self, game_state: GameState) -> str:
        """
        Generate a helpful hint for the player.

        Args:
            game_state: Current game state

        Returns:
            Hint text
        """
        recent_actions = [
            event.description
            for event in game_state.incident_timeline[-3:]
            if event.actor == "player"
        ]

        prompt = f"""The player seems stuck. Recent actions: {', '.join(recent_actions) if recent_actions else 'None yet'}

Provide a subtle hint about what they should investigate next. Don't give away the answer, just guide them in the right direction.

One sentence hint:"""

        system_message = self._build_system_message(game_state)

        result = await self.llm_provider.complete(
            prompt=prompt,
            system_message=system_message,
            temperature=0.7,
            max_tokens=100
        )

        return result["content"].strip()
