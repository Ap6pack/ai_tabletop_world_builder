#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
System State Manager Service - Tracks and updates system status during gameplay.
"""

import logging
from datetime import datetime

from api.models import GameState, Organization, System, SystemState

logger = logging.getLogger(__name__)


class SystemStateManager:
    """
    Manages system states during war gaming sessions.
    Tracks system health, status changes, and affected services.
    """

    def __init__(self):
        """Initialize the system state manager."""
        pass

    def initialize_system_states(self, organization: Organization) -> dict[str, SystemState]:
        """
        Initialize system states for all systems in the organization.
        All systems start in 'online' status with 100% health.

        Args:
            organization: The organization with systems to initialize

        Returns:
            Dictionary mapping system_id to SystemState
        """
        system_states = {}

        for dept in organization.departments:
            for system in dept.systems:
                system_states[system.id] = SystemState(
                    system_id=system.id,
                    status="online",
                    health=100,
                    last_update=datetime.now(),
                    affected_services=[],
                    notes="System initialized and operational",
                )

        logger.info(f"Initialized {len(system_states)} system states for organization {organization.name}")
        return system_states

    def update_system_state(
        self,
        game_state: GameState,
        system_id: str,
        new_status: str,
        health_change: int = 0,
        affected_services: list[str] | None = None,
        reason: str = "",
    ) -> SystemState:
        """
        Update the state of a specific system.

        Args:
            game_state: Current game state
            system_id: ID of the system to update
            new_status: New status (online, offline, compromised, recovering, patched)
            health_change: Change in health (-100 to +100)
            affected_services: List of services affected by this state change
            reason: Reason for the state change

        Returns:
            Updated SystemState
        """
        # Get or create system state
        if system_id not in game_state.system_states:
            # Find the system in the organization
            system = self._find_system(game_state.organization, system_id)
            if not system:
                logger.warning(f"System {system_id} not found in organization")
                raise ValueError(f"System {system_id} not found")

            # Initialize it
            game_state.system_states[system_id] = SystemState(
                system_id=system_id, status="online", health=100, last_update=datetime.now(), affected_services=[]
            )

        system_state = game_state.system_states[system_id]

        # Update status
        old_status = system_state.status
        system_state.status = new_status

        # Update health
        new_health = max(0, min(100, system_state.health + health_change))
        system_state.health = new_health

        # Update affected services
        if affected_services is not None:
            system_state.affected_services = affected_services

        # Update timestamp and notes
        system_state.last_update = datetime.now()
        system_state.notes = reason if reason else f"Status changed from {old_status} to {new_status}"

        logger.info(f"Updated system {system_id}: {old_status} → {new_status}, health: {new_health}%")

        return system_state

    def get_affected_systems(self, action: str, game_state: GameState) -> list[str]:
        """
        Determine which systems might be affected by a player action.
        Uses keyword matching to identify relevant systems.

        Args:
            action: Player's action description
            game_state: Current game state

        Returns:
            List of system IDs that might be affected
        """
        action_lower = action.lower()
        affected_systems = []

        # Keywords that suggest system targeting
        action_keywords = {
            "isolate": ["server", "workstation", "database", "network"],
            "patch": ["server", "workstation", "application"],
            "reboot": ["server", "workstation"],
            "shutdown": ["server", "workstation", "application"],
            "scan": ["network", "server", "workstation", "database"],
            "block": ["firewall", "network"],
            "restore": ["server", "database", "backup"],
        }

        for dept in game_state.organization.departments:
            for system in dept.systems:
                # Check if system name or type is mentioned
                if system.name.lower() in action_lower or system.type in action_lower:
                    affected_systems.append(system.id)
                    continue

                # Check for action-type matches
                for action_word, system_types in action_keywords.items():
                    if action_word in action_lower and system.type in system_types:
                        affected_systems.append(system.id)
                        break

        return affected_systems

    def calculate_system_health(self, system: System, game_state: GameState) -> int:
        """
        Calculate overall system health based on current state and timeline events.

        Args:
            system: The system to calculate health for
            game_state: Current game state

        Returns:
            Health percentage (0-100)
        """
        if system.id not in game_state.system_states:
            return 100  # Not yet tracked, assume healthy

        system_state = game_state.system_states[system.id]

        # Base health from state
        health = system_state.health

        # Adjust based on status
        status_modifiers = {"online": 0, "recovering": -10, "patched": 0, "compromised": -30, "offline": -50}

        health += status_modifiers.get(system_state.status, 0)

        # Ensure bounds
        return max(0, min(100, health))

    def check_system_availability(self, system_id: str, game_state: GameState) -> bool:
        """
        Check if a system is available for use.

        Args:
            system_id: ID of the system to check
            game_state: Current game state

        Returns:
            True if system is available, False otherwise
        """
        if system_id not in game_state.system_states:
            return True  # Not tracked, assume available

        system_state = game_state.system_states[system_id]

        # Systems are unavailable if offline
        if system_state.status == "offline":
            return False

        # Systems with very low health are unavailable
        return not system_state.health < 10

    def get_compromised_systems(self, game_state: GameState) -> list[str]:
        """
        Get list of all compromised system IDs.

        Args:
            game_state: Current game state

        Returns:
            List of system IDs that are compromised
        """
        compromised = []
        for system_id, state in game_state.system_states.items():
            if state.status == "compromised":
                compromised.append(system_id)

        return compromised

    def get_critical_systems_at_risk(self, game_state: GameState) -> list[str]:
        """
        Get list of critical systems that are compromised or offline.

        Args:
            game_state: Current game state

        Returns:
            List of system IDs for critical systems at risk
        """
        at_risk = []

        for dept in game_state.organization.departments:
            for system in dept.systems:
                if system.criticality in ["critical", "high"] and system.id in game_state.system_states:
                    state = game_state.system_states[system.id]
                    if state.status in ["compromised", "offline"] or state.health < 50:
                        at_risk.append(system.id)

        return at_risk

    def apply_compromise(self, game_state: GameState, system_id: str, severity: str = "high") -> SystemState:
        """
        Mark a system as compromised and adjust health based on severity.

        Args:
            game_state: Current game state
            system_id: ID of system to compromise
            severity: Severity of compromise (low, medium, high, critical)

        Returns:
            Updated SystemState
        """
        # Health impact based on severity
        health_impact = {"low": -20, "medium": -35, "high": -50, "critical": -70}

        impact = health_impact.get(severity, -50)

        return self.update_system_state(
            game_state=game_state,
            system_id=system_id,
            new_status="compromised",
            health_change=impact,
            reason=f"System compromised ({severity} severity)",
        )

    def apply_recovery(self, game_state: GameState, system_id: str, recovery_level: str = "partial") -> SystemState:
        """
        Apply recovery actions to a system.

        Args:
            game_state: Current game state
            system_id: ID of system to recover
            recovery_level: Level of recovery (partial, full)

        Returns:
            Updated SystemState
        """
        if recovery_level == "full":
            return self.update_system_state(
                game_state=game_state,
                system_id=system_id,
                new_status="online",
                health_change=100,  # Set to full health
                reason="System fully recovered and restored",
            )
        else:
            return self.update_system_state(
                game_state=game_state,
                system_id=system_id,
                new_status="recovering",
                health_change=30,
                reason="System partially recovered, still being restored",
            )

    def _find_system(self, organization: Organization, system_id: str) -> System | None:
        """Find a system by ID in the organization."""
        for dept in organization.departments:
            for system in dept.systems:
                if system.id == system_id:
                    return system
        return None

    def get_system_status_summary(self, game_state: GameState) -> dict[str, int]:
        """
        Get a summary of system statuses.

        Args:
            game_state: Current game state

        Returns:
            Dictionary with counts of systems in each status
        """
        summary = {"online": 0, "offline": 0, "compromised": 0, "recovering": 0, "patched": 0, "total": 0}

        # Count all systems
        for dept in game_state.organization.departments:
            summary["total"] += len(dept.systems)

        # Count by status
        for state in game_state.system_states.values():
            summary[state.status] = summary.get(state.status, 0) + 1

        # Untracked systems are assumed online
        untracked = summary["total"] - len(game_state.system_states)
        summary["online"] += untracked

        return summary
