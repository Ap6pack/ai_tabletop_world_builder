"""
Business Impact Service for calculating and tracking business costs of security incidents.

This service calculates:
- Downtime costs (hourly rate × hours × industry multiplier × criticality)
- Data loss costs (records × value per record × classification multiplier)
- Compliance penalties (framework-specific fines)
- Reputation damage (customer churn + brand recovery costs)
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from api.models import (
    GameState,
    BusinessImpact,
    ImpactEvent,
    Organization,
    System,
    SystemState,
)


class BusinessImpactService:
    """
    Service for calculating and tracking business impact during incidents.
    """

    # Industry-specific hourly downtime costs (base rates in USD)
    INDUSTRY_DOWNTIME_RATES = {
        "financial": 500000.0,      # $500K/hour for financial services
        "healthcare": 350000.0,     # $350K/hour for healthcare
        "technology": 300000.0,     # $300K/hour for tech companies
        "retail": 200000.0,         # $200K/hour for retail
        "manufacturing": 250000.0,  # $250K/hour for manufacturing
        "energy": 400000.0,         # $400K/hour for energy/utilities
        "default": 150000.0,        # $150K/hour default
    }

    # Industry multipliers for downtime severity
    INDUSTRY_MULTIPLIERS = {
        "financial": 3.0,      # Finance has highest impact
        "healthcare": 2.5,     # Healthcare critical services
        "technology": 2.0,     # Tech company reputation
        "retail": 1.8,         # E-commerce downtime
        "manufacturing": 1.5,  # Production line impact
        "energy": 2.2,         # Utility service disruption
        "default": 1.0,
    }

    # System criticality multipliers
    CRITICALITY_MULTIPLIERS = {
        "critical": 5.0,   # Critical systems 5x impact
        "high": 3.0,       # High priority 3x impact
        "medium": 1.5,     # Medium priority 1.5x impact
        "low": 1.0,        # Low priority 1x impact
    }

    # Data classification value per record (USD)
    DATA_VALUE_PER_RECORD = {
        "restricted": 500.0,      # Highly sensitive (PII, financial, health)
        "confidential": 250.0,    # Business confidential
        "internal": 50.0,         # Internal use only
        "public": 0.0,            # Public data
    }

    # Compliance framework penalties (USD)
    COMPLIANCE_PENALTIES = {
        "GDPR": {
            "base": 50000.0,
            "per_record": 100.0,
            "max": 20000000.0,  # €20M or 4% of revenue
        },
        "HIPAA": {
            "base": 25000.0,
            "per_record": 50.0,
            "max": 1500000.0,  # $1.5M per violation
        },
        "PCI-DSS": {
            "base": 100000.0,
            "per_record": 150.0,
            "max": 500000.0,  # Plus card brand fines
        },
        "SOX": {
            "base": 500000.0,
            "per_record": 0.0,
            "max": 5000000.0,  # Plus potential criminal charges
        },
    }

    # Reputation damage factors
    REPUTATION_BASE_COST = 100000.0  # Base reputation damage
    CUSTOMER_CHURN_COST_PER_RECORD = 50.0  # Lost customer value
    BRAND_RECOVERY_MULTIPLIER = 2.0  # PR/marketing recovery costs

    def __init__(self):
        """Initialize the business impact service."""
        pass

    def initialize_business_impact(self, organization: Organization) -> BusinessImpact:
        """
        Initialize a new BusinessImpact object for a game session.

        Args:
            organization: The organization/scenario

        Returns:
            Initialized BusinessImpact object
        """
        return BusinessImpact(
            downtime_cost=0.0,
            downtime_hours=0.0,
            data_loss_cost=0.0,
            records_compromised=0,
            compliance_penalties={},
            reputation_damage=0.0,
            total_cost=0.0,
            impact_description="Incident in progress. No significant business impact yet.",
            last_updated=datetime.utcnow(),
        )

    def calculate_downtime_cost(
        self,
        organization: Organization,
        system: System,
        hours: float,
    ) -> Tuple[float, str]:
        """
        Calculate downtime cost for a system being offline.

        Formula: Base Rate × Hours × Industry Multiplier × Criticality Multiplier

        Args:
            organization: Organization details
            system: The affected system
            hours: Hours of downtime

        Returns:
            Tuple of (cost, description)
        """
        # Get industry-specific rate
        industry = organization.industry.lower()
        base_rate = self.INDUSTRY_DOWNTIME_RATES.get(
            industry,
            self.INDUSTRY_DOWNTIME_RATES["default"]
        )

        # Get industry multiplier
        industry_multiplier = self.INDUSTRY_MULTIPLIERS.get(
            industry,
            self.INDUSTRY_MULTIPLIERS["default"]
        )

        # Get criticality multiplier
        criticality_multiplier = self.CRITICALITY_MULTIPLIERS.get(
            system.criticality,
            1.0
        )

        # Calculate cost
        cost = base_rate * hours * industry_multiplier * criticality_multiplier

        description = (
            f"Downtime: {system.name} ({system.criticality}) offline for {hours:.2f} hours. "
            f"Industry: {organization.industry} (${base_rate:,.0f}/hr × {industry_multiplier}x multiplier). "
            f"Cost: ${cost:,.2f}"
        )

        return cost, description

    def calculate_data_loss_cost(
        self,
        organization: Organization,
        department_name: str,
        records_compromised: int,
    ) -> Tuple[float, str]:
        """
        Calculate data loss/breach cost.

        Formula: Records × Value per Record × Classification Multiplier

        Args:
            organization: Organization details
            department_name: Name of the affected department
            records_compromised: Number of records compromised

        Returns:
            Tuple of (cost, description)
        """
        # Find the department
        department = None
        for dept in organization.departments:
            if dept.name.lower() == department_name.lower():
                department = dept
                break

        if not department:
            # Default to confidential if department not found
            classification = "confidential"
        else:
            classification = department.data_classification

        # Get value per record
        value_per_record = self.DATA_VALUE_PER_RECORD.get(
            classification,
            self.DATA_VALUE_PER_RECORD["confidential"]
        )

        # Calculate cost
        cost = records_compromised * value_per_record

        description = (
            f"Data Breach: {records_compromised:,} {classification} records from {department_name}. "
            f"Value: ${value_per_record:,.2f}/record. Cost: ${cost:,.2f}"
        )

        return cost, description

    def calculate_compliance_penalties(
        self,
        organization: Organization,
        records_compromised: int,
        frameworks: Optional[List[str]] = None,
    ) -> Tuple[Dict[str, float], str]:
        """
        Calculate compliance penalties for data breaches.

        Args:
            organization: Organization details
            records_compromised: Number of records compromised
            frameworks: Optional list of specific frameworks to check (uses org's if None)

        Returns:
            Tuple of (penalties dict, description)
        """
        penalties = {}
        descriptions = []

        # Use organization's compliance frameworks if not specified
        if frameworks is None:
            frameworks = organization.compliance_frameworks

        for framework in frameworks:
            if framework in self.COMPLIANCE_PENALTIES:
                penalty_info = self.COMPLIANCE_PENALTIES[framework]

                # Calculate penalty: base + (per_record × records)
                penalty = penalty_info["base"] + (
                    penalty_info["per_record"] * records_compromised
                )

                # Cap at maximum
                penalty = min(penalty, penalty_info["max"])

                penalties[framework] = penalty
                descriptions.append(
                    f"{framework}: ${penalty:,.2f} (base ${penalty_info['base']:,.0f} + "
                    f"{records_compromised:,} records)"
                )

        total_penalties = sum(penalties.values())
        description = f"Compliance Penalties: ${total_penalties:,.2f}. " + "; ".join(descriptions)

        return penalties, description

    def calculate_reputation_damage(
        self,
        organization: Organization,
        records_compromised: int,
        severity: str,
    ) -> Tuple[float, str]:
        """
        Calculate reputation/brand damage costs.

        Formula: Base Cost + (Records × Churn Cost) × Severity Multiplier × Brand Recovery

        Args:
            organization: Organization details
            records_compromised: Number of records compromised
            severity: Severity of the incident ("low", "medium", "high", "critical")

        Returns:
            Tuple of (cost, description)
        """
        # Severity multipliers
        severity_multipliers = {
            "low": 0.5,
            "medium": 1.0,
            "high": 2.0,
            "critical": 3.0,
        }
        severity_multiplier = severity_multipliers.get(severity.lower(), 1.0)

        # Calculate customer churn cost
        churn_cost = records_compromised * self.CUSTOMER_CHURN_COST_PER_RECORD

        # Calculate total reputation damage
        cost = (
            self.REPUTATION_BASE_COST + churn_cost
        ) * severity_multiplier * self.BRAND_RECOVERY_MULTIPLIER

        description = (
            f"Reputation Damage ({severity}): {records_compromised:,} customers affected. "
            f"Churn cost: ${churn_cost:,.2f}, Recovery multiplier: {self.BRAND_RECOVERY_MULTIPLIER}x. "
            f"Total: ${cost:,.2f}"
        )

        return cost, description

    def update_impact(
        self,
        game_state: GameState,
        organization: Organization,
        event_type: str,
        system_id: Optional[str] = None,
        hours: Optional[float] = None,
        records: Optional[int] = None,
        department: Optional[str] = None,
        severity: str = "medium",
    ) -> GameState:
        """
        Update business impact based on a new event.

        Args:
            game_state: Current game state
            organization: Organization details
            event_type: Type of impact event ("downtime", "data_loss", "compliance", "reputation")
            system_id: System ID for downtime events
            hours: Hours of downtime
            records: Number of records compromised
            department: Department name for data loss
            severity: Severity level

        Returns:
            Updated game state
        """
        # Initialize business impact if needed
        if game_state.business_impact is None:
            game_state.business_impact = self.initialize_business_impact(organization)

        cost = 0.0
        description = ""

        # Calculate cost based on event type
        if event_type == "downtime" and system_id and hours:
            # Find the system
            system = self._find_system(organization, system_id)
            if system:
                cost, description = self.calculate_downtime_cost(
                    organization, system, hours
                )
                game_state.business_impact.downtime_cost += cost
                game_state.business_impact.downtime_hours += hours

        elif event_type == "data_loss" and records and department:
            cost, description = self.calculate_data_loss_cost(
                organization, department, records
            )
            game_state.business_impact.data_loss_cost += cost
            game_state.business_impact.records_compromised += records

        elif event_type == "compliance" and records:
            penalties, description = self.calculate_compliance_penalties(
                organization, records
            )
            for framework, penalty in penalties.items():
                current = game_state.business_impact.compliance_penalties.get(framework, 0.0)
                game_state.business_impact.compliance_penalties[framework] = current + penalty
            cost = sum(penalties.values())

        elif event_type == "reputation" and records:
            cost, description = self.calculate_reputation_damage(
                organization, records, severity
            )
            game_state.business_impact.reputation_damage += cost

        # Create impact event
        impact_event = ImpactEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            system_id=system_id,
            cost=cost,
            description=description,
            severity=severity,
        )
        game_state.impact_events.append(impact_event)

        # Update total cost
        game_state.business_impact.total_cost = (
            game_state.business_impact.downtime_cost +
            game_state.business_impact.data_loss_cost +
            sum(game_state.business_impact.compliance_penalties.values()) +
            game_state.business_impact.reputation_damage
        )

        # Update description
        game_state.business_impact.impact_description = self.get_impact_summary(
            game_state.business_impact
        )
        game_state.business_impact.last_updated = datetime.utcnow()

        return game_state

    def get_impact_summary(self, business_impact: BusinessImpact) -> str:
        """
        Generate a human-readable summary of business impact.

        Args:
            business_impact: BusinessImpact object

        Returns:
            Summary string
        """
        if business_impact.total_cost == 0:
            return "No significant business impact yet."

        parts = []

        if business_impact.downtime_cost > 0:
            parts.append(
                f"Downtime: {business_impact.downtime_hours:.1f} hours, "
                f"${business_impact.downtime_cost:,.0f}"
            )

        if business_impact.data_loss_cost > 0:
            parts.append(
                f"Data Loss: {business_impact.records_compromised:,} records, "
                f"${business_impact.data_loss_cost:,.0f}"
            )

        if business_impact.compliance_penalties:
            total_penalties = sum(business_impact.compliance_penalties.values())
            frameworks = ", ".join(business_impact.compliance_penalties.keys())
            parts.append(f"Compliance: {frameworks}, ${total_penalties:,.0f}")

        if business_impact.reputation_damage > 0:
            parts.append(f"Reputation: ${business_impact.reputation_damage:,.0f}")

        summary = ". ".join(parts) + f". Total: ${business_impact.total_cost:,.0f}"
        return summary

    def _find_system(self, organization: Organization, system_id: str) -> Optional[System]:
        """
        Find a system by ID in the organization.

        Args:
            organization: Organization to search
            system_id: System ID to find

        Returns:
            System or None if not found
        """
        for department in organization.departments:
            for system in department.systems:
                if system.id == system_id:
                    return system
        return None

    def calculate_system_downtime_impact(
        self,
        game_state: GameState,
        organization: Organization,
        system_id: str,
    ) -> GameState:
        """
        Calculate and apply downtime impact for a compromised or offline system.

        This is called automatically when a system goes offline/compromised.

        Args:
            game_state: Current game state
            organization: Organization details
            system_id: ID of affected system

        Returns:
            Updated game state
        """
        # Find system state
        system_state = game_state.system_states.get(system_id)
        if not system_state:
            return game_state

        # Only calculate for offline/compromised systems
        if system_state.status not in ["offline", "compromised"]:
            return game_state

        # Calculate hours based on time elapsed
        # Assuming each turn is approximately 5 minutes
        hours_elapsed = game_state.time_elapsed / 60.0

        # Calculate downtime (assuming system was down for a portion of time)
        # This is a simplified model - in reality you'd track when it went down
        downtime_hours = 0.25  # Default to 15 minutes per check

        return self.update_impact(
            game_state=game_state,
            organization=organization,
            event_type="downtime",
            system_id=system_id,
            hours=downtime_hours,
            severity=system_state.status,
        )
