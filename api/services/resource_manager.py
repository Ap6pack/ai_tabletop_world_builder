"""
Resource Manager Service for managing player resources and action costs.

This service manages:
- Action points (limited actions per turn)
- Budget constraints (financial costs)
- Tool cooldowns (preventing spam)
- Staff availability (concurrent action limits)
"""
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from api.models import GameState, ResourcePool, ActionCost


class ResourceManager:
    """
    Service for managing player resources during incidents.
    """

    # Default action costs by type
    DEFAULT_ACTION_COSTS = {
        # Investigation actions (low cost)
        "investigate": ActionCost(points=1, budget=0, cooldown_seconds=0, requires_staff=1),
        "analyze": ActionCost(points=1, budget=0, cooldown_seconds=0, requires_staff=1),
        "check_logs": ActionCost(points=1, budget=0, cooldown_seconds=0, requires_staff=1),

        # Detection actions (low-medium cost)
        "scan": ActionCost(points=2, budget=500, cooldown_seconds=300, requires_staff=1),
        "monitor": ActionCost(points=1, budget=0, cooldown_seconds=0, requires_staff=1),

        # Containment actions (medium cost)
        "isolate": ActionCost(points=3, budget=0, cooldown_seconds=600, requires_staff=2),
        "block": ActionCost(points=2, budget=0, cooldown_seconds=300, requires_staff=1),
        "quarantine": ActionCost(points=3, budget=1000, cooldown_seconds=600, requires_staff=2),

        # Mitigation actions (high cost)
        "patch": ActionCost(points=4, budget=5000, cooldown_seconds=1800, requires_staff=3),
        "restore": ActionCost(points=5, budget=10000, cooldown_seconds=3600, requires_staff=3),
        "rebuild": ActionCost(points=6, budget=25000, cooldown_seconds=3600, requires_staff=4),

        # External help (very high cost, no cooldown)
        "call_vendor": ActionCost(points=2, budget=50000, cooldown_seconds=0, requires_staff=1),
        "hire_consultant": ActionCost(points=2, budget=75000, cooldown_seconds=0, requires_staff=0),

        # Communication actions (free)
        "notify": ActionCost(points=1, budget=0, cooldown_seconds=0, requires_staff=1),
        "report": ActionCost(points=1, budget=0, cooldown_seconds=0, requires_staff=1),
        "escalate": ActionCost(points=1, budget=0, cooldown_seconds=0, requires_staff=1),
    }

    # Resource pool defaults by difficulty
    DIFFICULTY_DEFAULTS = {
        "beginner": {
            "action_points": 15,
            "max_action_points": 15,
            "points_per_minute": 0.75,
            "budget_remaining": 150000.0,
            "budget_total": 150000.0,
            "staff_available": 7,
        },
        "intermediate": {
            "action_points": 10,
            "max_action_points": 10,
            "points_per_minute": 0.5,
            "budget_remaining": 100000.0,
            "budget_total": 100000.0,
            "staff_available": 5,
        },
        "advanced": {
            "action_points": 7,
            "max_action_points": 7,
            "points_per_minute": 0.33,
            "budget_remaining": 75000.0,
            "budget_total": 75000.0,
            "staff_available": 4,
        },
        "expert": {
            "action_points": 5,
            "max_action_points": 5,
            "points_per_minute": 0.25,
            "budget_remaining": 50000.0,
            "budget_total": 50000.0,
            "staff_available": 3,
        },
    }

    def __init__(self):
        """Initialize the resource manager."""
        pass

    def initialize_resource_pool(self, difficulty: str = "intermediate") -> ResourcePool:
        """
        Initialize a resource pool based on difficulty.

        Args:
            difficulty: Difficulty level

        Returns:
            Initialized ResourcePool
        """
        defaults = self.DIFFICULTY_DEFAULTS.get(difficulty, self.DIFFICULTY_DEFAULTS["intermediate"])

        return ResourcePool(
            action_points=defaults["action_points"],
            max_action_points=defaults["max_action_points"],
            points_per_minute=defaults["points_per_minute"],
            budget_remaining=defaults["budget_remaining"],
            budget_total=defaults["budget_total"],
            staff_available=defaults["staff_available"],
            tools_on_cooldown={},
            last_regeneration=datetime.utcnow(),
        )

    def get_action_cost(self, action_description: str) -> ActionCost:
        """
        Determine the cost of an action based on its description.

        Args:
            action_description: Description of the action

        Returns:
            ActionCost for the action
        """
        action_lower = action_description.lower()

        # Check each action type
        for action_type, cost in self.DEFAULT_ACTION_COSTS.items():
            if action_type in action_lower:
                return cost

        # Default cost for unknown actions (investigation-level)
        return self.DEFAULT_ACTION_COSTS["investigate"]

    def can_afford_action(
        self,
        resource_pool: ResourcePool,
        action_cost: ActionCost,
        tool_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if the player can afford an action.

        Args:
            resource_pool: Current resource pool
            action_cost: Cost of the action
            tool_name: Optional tool name for cooldown checking

        Returns:
            Tuple of (can_afford: bool, reason: str)
        """
        # Check action points
        if resource_pool.action_points < action_cost.points:
            return False, f"Not enough action points (need {action_cost.points}, have {resource_pool.action_points})"

        # Check budget
        if resource_pool.budget_remaining < action_cost.budget:
            return False, f"Insufficient budget (need ${action_cost.budget:,.0f}, have ${resource_pool.budget_remaining:,.0f})"

        # Check staff availability
        if resource_pool.staff_available < action_cost.requires_staff:
            return False, f"Not enough staff available (need {action_cost.requires_staff}, have {resource_pool.staff_available})"

        # Check tool cooldown
        if tool_name and tool_name in resource_pool.tools_on_cooldown:
            cooldown_until = resource_pool.tools_on_cooldown[tool_name]
            if datetime.utcnow() < cooldown_until:
                remaining = (cooldown_until - datetime.utcnow()).total_seconds()
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                return False, f"Tool on cooldown ({minutes}m {seconds}s remaining)"

        return True, None

    def spend_resources(
        self,
        resource_pool: ResourcePool,
        action_cost: ActionCost,
        tool_name: Optional[str] = None,
    ) -> ResourcePool:
        """
        Spend resources for an action.

        Args:
            resource_pool: Current resource pool
            action_cost: Cost of the action
            tool_name: Optional tool name for cooldown

        Returns:
            Updated resource pool
        """
        # Deduct action points
        resource_pool.action_points -= action_cost.points

        # Deduct budget
        resource_pool.budget_remaining -= action_cost.budget

        # Set tool cooldown if applicable
        if tool_name and action_cost.cooldown_seconds > 0:
            cooldown_until = datetime.utcnow() + timedelta(seconds=action_cost.cooldown_seconds)
            resource_pool.tools_on_cooldown[tool_name] = cooldown_until

        return resource_pool

    def regenerate_action_points(
        self,
        resource_pool: ResourcePool,
        minutes_elapsed: int,
    ) -> Tuple[ResourcePool, int]:
        """
        Regenerate action points based on time elapsed.

        Args:
            resource_pool: Current resource pool
            minutes_elapsed: Total game time elapsed

        Returns:
            Tuple of (updated resource pool, points regenerated)
        """
        # Calculate time since last regeneration
        time_since_last = (datetime.utcnow() - resource_pool.last_regeneration).total_seconds() / 60.0

        # Calculate points to regenerate
        points_to_add = int(time_since_last * resource_pool.points_per_minute)

        if points_to_add > 0:
            old_points = resource_pool.action_points
            resource_pool.action_points = min(
                resource_pool.max_action_points,
                resource_pool.action_points + points_to_add
            )
            resource_pool.last_regeneration = datetime.utcnow()
            points_added = resource_pool.action_points - old_points
            return resource_pool, points_added

        return resource_pool, 0

    def clear_expired_cooldowns(self, resource_pool: ResourcePool) -> ResourcePool:
        """
        Remove expired cooldowns from the resource pool.

        Args:
            resource_pool: Current resource pool

        Returns:
            Updated resource pool
        """
        now = datetime.utcnow()
        expired_tools = [
            tool for tool, cooldown_until in resource_pool.tools_on_cooldown.items()
            if now >= cooldown_until
        ]

        for tool in expired_tools:
            del resource_pool.tools_on_cooldown[tool]

        return resource_pool

    def get_resource_status(self, resource_pool: ResourcePool) -> Dict[str, any]:
        """
        Get a human-readable status of resources.

        Args:
            resource_pool: Current resource pool

        Returns:
            Status dictionary
        """
        # Action points status
        ap_percentage = (resource_pool.action_points / resource_pool.max_action_points) * 100
        if ap_percentage > 75:
            ap_status = "good"
        elif ap_percentage > 25:
            ap_status = "low"
        else:
            ap_status = "critical"

        # Budget status
        budget_percentage = (resource_pool.budget_remaining / resource_pool.budget_total) * 100
        if budget_percentage > 75:
            budget_status = "good"
        elif budget_percentage > 25:
            budget_status = "low"
        else:
            budget_status = "critical"

        # Staff status
        if resource_pool.staff_available >= 5:
            staff_status = "good"
        elif resource_pool.staff_available >= 2:
            staff_status = "moderate"
        else:
            staff_status = "limited"

        # Cooldowns
        active_cooldowns = len(resource_pool.tools_on_cooldown)

        return {
            "action_points": {
                "current": resource_pool.action_points,
                "max": resource_pool.max_action_points,
                "percentage": ap_percentage,
                "status": ap_status,
                "regen_rate": resource_pool.points_per_minute,
            },
            "budget": {
                "remaining": resource_pool.budget_remaining,
                "total": resource_pool.budget_total,
                "spent": resource_pool.budget_total - resource_pool.budget_remaining,
                "percentage": budget_percentage,
                "status": budget_status,
            },
            "staff": {
                "available": resource_pool.staff_available,
                "status": staff_status,
            },
            "cooldowns": {
                "active": active_cooldowns,
                "tools": list(resource_pool.tools_on_cooldown.keys()),
            },
        }

    def adjust_budget(self, resource_pool: ResourcePool, amount: float, reason: str = "") -> ResourcePool:
        """
        Adjust budget (add or subtract).

        Args:
            resource_pool: Current resource pool
            amount: Amount to adjust (positive = add, negative = subtract)
            reason: Reason for adjustment

        Returns:
            Updated resource pool
        """
        resource_pool.budget_remaining = max(0, resource_pool.budget_remaining + amount)
        return resource_pool

    def adjust_staff(self, resource_pool: ResourcePool, amount: int, reason: str = "") -> ResourcePool:
        """
        Adjust staff availability.

        Args:
            resource_pool: Current resource pool
            amount: Amount to adjust (positive = add, negative = subtract)
            reason: Reason for adjustment

        Returns:
            Updated resource pool
        """
        resource_pool.staff_available = max(0, resource_pool.staff_available + amount)
        return resource_pool

    def get_affordable_actions(self, resource_pool: ResourcePool) -> list:
        """
        Get list of actions the player can currently afford.

        Args:
            resource_pool: Current resource pool

        Returns:
            List of affordable action types
        """
        affordable = []

        for action_type, cost in self.DEFAULT_ACTION_COSTS.items():
            can_afford, _ = self.can_afford_action(resource_pool, cost)
            if can_afford:
                affordable.append({
                    "action": action_type,
                    "cost": {
                        "points": cost.points,
                        "budget": cost.budget,
                        "staff": cost.requires_staff,
                        "cooldown": cost.cooldown_seconds,
                    }
                })

        return affordable

    def estimate_action_duration(self, action_cost: ActionCost) -> int:
        """
        Estimate how long an action will take (in minutes).

        Args:
            action_cost: Cost of the action

        Returns:
            Estimated duration in minutes
        """
        # More expensive/complex actions take longer
        base_time = action_cost.points * 2  # 2 minutes per action point
        staff_factor = action_cost.requires_staff  # More staff = more time to coordinate

        return base_time + staff_factor
