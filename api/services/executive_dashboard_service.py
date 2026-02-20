# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
"""
Executive Dashboard Service for calculating executive-level business impact metrics.

This service provides C-suite and board-level incident impact analysis based on
Ponemon Institute breach cost data. It wraps the existing BusinessImpactService
and adds higher-level calculations including:

- Stock price impact estimation
- Customer churn rate projection
- Regulatory risk assessment
- Media exposure level determination
- Recovery timeline estimation
- Notification obligation tracking (GDPR, HIPAA, PCI-DSS, SEC, state laws)
- Board and SEC disclosure requirements
- Executive-ready board report generation
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from api.models.schemas import (
    BusinessImpact,
    ExecutiveMetrics,
    GameState,
    Organization,
)
from api.utils.logger import setup_logger

logger = setup_logger(__name__)


class ExecutiveDashboardService:
    """
    Service for calculating executive-level business impact metrics.

    Provides C-suite visibility into incident costs, regulatory exposure,
    and recovery timelines based on Ponemon Institute breach cost research.
    """

    # Average stock price decline percentage after a data breach by industry
    STOCK_IMPACT_BY_INDUSTRY: Dict[str, float] = {
        "financial": 5.5,
        "healthcare": 4.2,
        "technology": 3.8,
        "energy": 4.0,
        "retail": 3.0,
        "manufacturing": 2.8,
        "government": 0.0,
        "default": 3.5,
    }

    # Average customer churn rate after breach by industry
    CHURN_RATE_BY_INDUSTRY: Dict[str, float] = {
        "financial": 5.7,
        "healthcare": 6.7,
        "technology": 4.5,
        "energy": 3.8,
        "retail": 3.2,
        "manufacturing": 2.5,
        "default": 3.8,
    }

    # Base recovery time in days by industry
    RECOVERY_TIME_BASE_DAYS: Dict[str, int] = {
        "financial": 45,
        "healthcare": 55,
        "technology": 35,
        "energy": 50,
        "retail": 40,
        "manufacturing": 42,
        "default": 46,
    }

    # Notification rules defining when regulatory notification is required
    NOTIFICATION_RULES: List[Dict[str, Any]] = [
        {
            "framework": "GDPR",
            "min_records": 0,
            "requires_payment_data": False,
            "min_total_cost": 0,
            "deadline": "72 hours",
            "scope": "EU data subjects",
        },
        {
            "framework": "HIPAA",
            "min_records": 500,
            "requires_payment_data": False,
            "min_total_cost": 0,
            "deadline": "60 days",
            "scope": "HHS and affected individuals",
        },
        {
            "framework": "PCI_DSS",
            "min_records": 0,
            "requires_payment_data": True,
            "min_total_cost": 0,
            "deadline": "immediate to card brands",
            "scope": "Card brands and acquiring bank",
        },
        {
            "framework": "SEC",
            "min_records": 0,
            "requires_payment_data": False,
            "min_total_cost": 1_000_000,
            "deadline": "4 business days",
            "scope": "SEC Form 8-K filing",
        },
        {
            "framework": "State breach laws",
            "min_records": 500,
            "requires_payment_data": False,
            "min_total_cost": 0,
            "deadline": "varies by state (30-90 days)",
            "scope": "Affected individuals",
        },
    ]

    def __init__(self) -> None:
        """Initialize the executive dashboard service."""
        logger.info("ExecutiveDashboardService initialized")

    def calculate_stock_impact(
        self,
        business_impact: BusinessImpact,
        organization: Organization,
    ) -> float:
        """
        Calculate estimated stock price impact as a negative percentage.

        Based on Ponemon Institute data, scales the base industry impact
        by breach magnitude, records compromised, and response time.

        Args:
            business_impact: Current business impact state.
            organization: Organization details for industry context.

        Returns:
            Negative percentage representing estimated stock price decline
            (e.g., -5.5 means a 5.5% decline). Capped at -15%.
        """
        industry = organization.industry.lower()
        base_impact = self.STOCK_IMPACT_BY_INDUSTRY.get(
            industry,
            self.STOCK_IMPACT_BY_INDUSTRY["default"],
        )

        # Scale by breach magnitude (total cost thresholds)
        total_cost = business_impact.total_cost
        if total_cost > 100_000_000:
            base_impact *= 2.5
        elif total_cost > 50_000_000:
            base_impact *= 2.0
        elif total_cost > 10_000_000:
            base_impact *= 1.5

        # Scale by records compromised
        records = business_impact.records_compromised
        if records > 10_000_000:
            base_impact += 2.5
        elif records > 1_000_000:
            base_impact += 1.0

        # Scale by response time (downtime as a proxy)
        downtime_hours = business_impact.downtime_hours
        if downtime_hours > 72:
            base_impact += 1.5
        elif downtime_hours > 24:
            base_impact += 0.5

        # Cap at 15%
        base_impact = min(base_impact, 15.0)

        logger.debug(
            "Stock impact calculated: %.2f%% for %s (%s)",
            base_impact,
            organization.name,
            industry,
        )

        return -base_impact

    def calculate_customer_churn(
        self,
        business_impact: BusinessImpact,
        organization: Organization,
    ) -> float:
        """
        Calculate estimated customer churn rate after a breach.

        Based on Ponemon Institute data, scales the base industry churn
        rate by records compromised and data sensitivity.

        Args:
            business_impact: Current business impact state.
            organization: Organization details for industry context.

        Returns:
            Churn rate as a positive percentage (e.g., 6.7). Capped at 20%.
        """
        industry = organization.industry.lower()
        churn_rate = self.CHURN_RATE_BY_INDUSTRY.get(
            industry,
            self.CHURN_RATE_BY_INDUSTRY["default"],
        )

        # Scale by records compromised
        records = business_impact.records_compromised
        if records > 1_000_000:
            churn_rate *= 1.8
        elif records > 100_000:
            churn_rate *= 1.3

        # Scale by data sensitivity: HIPAA presence or health data implies
        # highly sensitive personal information was exposed
        compliance_frameworks = business_impact.compliance_penalties
        has_hipaa = "HIPAA" in compliance_frameworks
        has_health_data = any(
            "health" in framework.lower() or "hipaa" in framework.lower()
            for framework in compliance_frameworks
        )
        if has_hipaa or has_health_data:
            churn_rate *= 1.5

        # Cap at 20%
        churn_rate = min(churn_rate, 20.0)

        logger.debug(
            "Customer churn calculated: %.2f%% for %s (%s)",
            churn_rate,
            organization.name,
            industry,
        )

        return round(churn_rate, 2)

    def assess_regulatory_risk(
        self,
        game_state: GameState,
    ) -> Literal["low", "medium", "high", "critical"]:
        """
        Assess the overall regulatory risk level based on the current game state.

        Risk escalates based on records compromised, compliance penalty amounts,
        and the number of compliance frameworks violated.

        Args:
            game_state: Current game state with business impact data.

        Returns:
            Risk level: "low", "medium", "high", or "critical".
        """
        if game_state.business_impact is None:
            return "low"

        impact = game_state.business_impact
        records = impact.records_compromised
        penalties = impact.compliance_penalties
        total_penalties = sum(penalties.values())
        frameworks_violated = len(penalties)

        risk_level: Literal["low", "medium", "high", "critical"] = "low"

        # Bump to "medium" if any records were compromised
        if records > 0:
            risk_level = "medium"

        # Bump to "high" if records exceed 1000 OR penalties exceed $100K
        if records > 1000 or total_penalties > 100_000:
            risk_level = "high"

        # Bump to "critical" if records exceed 100K OR penalties exceed $1M
        # OR multiple compliance frameworks are violated
        if (
            records > 100_000
            or total_penalties > 1_000_000
            or frameworks_violated >= 2
        ):
            risk_level = "critical"

        logger.debug(
            "Regulatory risk assessed: %s (records=%d, penalties=$%.2f, frameworks=%d)",
            risk_level,
            records,
            total_penalties,
            frameworks_violated,
        )

        return risk_level

    def assess_media_exposure(
        self,
        business_impact: BusinessImpact,
        organization: Organization,
    ) -> Literal["none", "local", "national", "international"]:
        """
        Assess likely media exposure level based on breach severity.

        Higher costs and more records compromised lead to broader media coverage.

        Args:
            business_impact: Current business impact state.
            organization: Organization details for context.

        Returns:
            Media exposure level: "none", "local", "national", or "international".
        """
        total_cost = business_impact.total_cost
        records = business_impact.records_compromised

        # Determine media exposure level based on thresholds
        if total_cost >= 10_000_000 or records >= 100_000:
            level: Literal["none", "local", "national", "international"] = (
                "international"
            )
        elif total_cost >= 500_000 or records >= 1_000:
            level = "national"
        elif total_cost >= 50_000 or records >= 100:
            level = "local"
        else:
            level = "none"

        logger.debug(
            "Media exposure assessed: %s for %s (cost=$%.2f, records=%d)",
            level,
            organization.name,
            total_cost,
            records,
        )

        return level

    def calculate_recovery_time(
        self,
        business_impact: BusinessImpact,
        organization: Organization,
    ) -> int:
        """
        Estimate recovery time in days based on industry and breach severity.

        Base recovery time varies by industry. Additional days are added based
        on total cost and number of compliance frameworks with penalties.

        Args:
            business_impact: Current business impact state.
            organization: Organization details for industry context.

        Returns:
            Estimated recovery time in days (integer).
        """
        industry = organization.industry.lower()
        base_days = self.RECOVERY_TIME_BASE_DAYS.get(
            industry,
            self.RECOVERY_TIME_BASE_DAYS["default"],
        )

        # Add 10 days per $1M in total cost, capped at 60 additional days
        cost_millions = business_impact.total_cost / 1_000_000.0
        additional_cost_days = min(int(cost_millions * 10), 60)

        # Add 5 days if multiple compliance frameworks have penalties
        compliance_penalty_count = len(business_impact.compliance_penalties)
        additional_compliance_days = 5 if compliance_penalty_count >= 2 else 0

        total_days = base_days + additional_cost_days + additional_compliance_days

        logger.debug(
            "Recovery time calculated: %d days for %s "
            "(base=%d, cost_add=%d, compliance_add=%d)",
            total_days,
            organization.name,
            base_days,
            additional_cost_days,
            additional_compliance_days,
        )

        return total_days

    def determine_notification_obligations(
        self,
        game_state: GameState,
    ) -> List[str]:
        """
        Determine which regulatory notification obligations apply.

        Checks each notification rule against the current game state to
        identify required notifications with their deadlines and scope.

        Args:
            game_state: Current game state with business impact data.

        Returns:
            List of formatted notification obligation strings.
        """
        if game_state.business_impact is None:
            return []

        impact = game_state.business_impact
        records = impact.records_compromised
        total_cost = impact.total_cost
        obligations: List[str] = []

        # Check if payment data is involved by looking at compliance penalties
        # or organization compliance frameworks
        has_payment_data = "PCI-DSS" in impact.compliance_penalties or any(
            "pci" in fw.lower()
            for fw in game_state.organization.compliance_frameworks
        )

        for rule in self.NOTIFICATION_RULES:
            framework = rule["framework"]
            min_records = rule["min_records"]
            requires_payment = rule["requires_payment_data"]
            min_cost = rule["min_total_cost"]
            deadline = rule["deadline"]
            scope = rule["scope"]

            # Check records threshold
            if records < min_records:
                continue

            # Check payment data requirement
            if requires_payment and not has_payment_data:
                continue

            # Check total cost threshold
            if min_cost > 0 and total_cost < min_cost:
                continue

            # All conditions met; notification is required
            obligations.append(
                f"{framework}: Notify within {deadline} ({scope})"
            )

        logger.debug(
            "Notification obligations determined: %d obligations",
            len(obligations),
        )

        return obligations

    def check_sec_disclosure(self, business_impact: BusinessImpact) -> bool:
        """
        Check whether SEC Form 8-K disclosure is required.

        SEC materiality threshold requires disclosure for incidents with
        total cost exceeding $1M.

        Args:
            business_impact: Current business impact state.

        Returns:
            True if SEC disclosure is required.
        """
        required = business_impact.total_cost > 1_000_000
        if required:
            logger.info(
                "SEC disclosure required: total cost $%.2f exceeds $1M threshold",
                business_impact.total_cost,
            )
        return required

    def check_board_notification(
        self,
        business_impact: BusinessImpact,
        organization: Organization,
        regulatory_risk: Optional[Literal["low", "medium", "high", "critical"]] = None,
    ) -> bool:
        """
        Check whether the board of directors should be notified.

        Board notification is required when total cost exceeds $500K,
        records compromised exceed 10K, or regulatory risk is critical.

        Args:
            business_impact: Current business impact state.
            organization: Organization details.
            regulatory_risk: Pre-calculated regulatory risk level. If None,
                this check only considers cost and records thresholds.

        Returns:
            True if board notification is required.
        """
        if business_impact.total_cost > 500_000:
            logger.info(
                "Board notification required: total cost $%.2f exceeds $500K",
                business_impact.total_cost,
            )
            return True

        if business_impact.records_compromised > 10_000:
            logger.info(
                "Board notification required: %d records exceeds 10K threshold",
                business_impact.records_compromised,
            )
            return True

        if regulatory_risk == "critical":
            logger.info("Board notification required: regulatory risk is critical")
            return True

        return False

    def calculate_executive_metrics(
        self,
        game_state: GameState,
    ) -> ExecutiveMetrics:
        """
        Calculate all executive-level metrics for the current game state.

        This is the main entry point that aggregates all individual metric
        calculations into a single ExecutiveMetrics instance.

        Args:
            game_state: Current game state with business impact and organization data.

        Returns:
            Populated ExecutiveMetrics instance.
        """
        logger.info(
            "Calculating executive metrics for session %s",
            game_state.session_id,
        )

        # Handle case where business_impact is None
        if game_state.business_impact is None:
            logger.info("No business impact data; returning default ExecutiveMetrics")
            return ExecutiveMetrics()

        impact = game_state.business_impact
        org = game_state.organization

        # Calculate individual metrics
        stock_impact = self.calculate_stock_impact(impact, org)
        churn_rate = self.calculate_customer_churn(impact, org)
        regulatory_risk = self.assess_regulatory_risk(game_state)
        media_exposure = self.assess_media_exposure(impact, org)
        recovery_days = self.calculate_recovery_time(impact, org)
        notifications = self.determine_notification_obligations(game_state)
        sec_required = self.check_sec_disclosure(impact)
        board_required = self.check_board_notification(
            impact, org, regulatory_risk=regulatory_risk
        )

        metrics = ExecutiveMetrics(
            stock_price_impact_pct=round(stock_impact, 2),
            customer_churn_rate=churn_rate,
            regulatory_risk_level=regulatory_risk,
            media_exposure_level=media_exposure,
            estimated_recovery_time_days=recovery_days,
            board_notification_required=board_required,
            sec_disclosure_required=sec_required,
            notification_obligations=notifications,
        )

        logger.info(
            "Executive metrics calculated: stock=%.2f%%, churn=%.2f%%, "
            "risk=%s, media=%s, recovery=%dd, board=%s, sec=%s",
            metrics.stock_price_impact_pct,
            metrics.customer_churn_rate,
            metrics.regulatory_risk_level,
            metrics.media_exposure_level,
            metrics.estimated_recovery_time_days,
            metrics.board_notification_required,
            metrics.sec_disclosure_required,
        )

        return metrics

    def generate_board_report(
        self,
        game_state: GameState,
    ) -> Dict[str, Any]:
        """
        Generate an executive board-ready incident report.

        Produces a structured report suitable for board of directors review,
        including incident summary, financial impact breakdown, customer impact,
        regulatory status, recovery timeline, and actionable recommendations.

        Args:
            game_state: Current game state with business impact and organization data.

        Returns:
            Dictionary containing the board report sections.
        """
        logger.info(
            "Generating board report for session %s", game_state.session_id
        )

        metrics = self.calculate_executive_metrics(game_state)
        impact = game_state.business_impact
        org = game_state.organization

        # Build incident summary
        if impact is None:
            incident_summary = (
                f"An incident has been detected at {org.name}. "
                "No significant business impact has been recorded at this time. "
                "Monitoring is ongoing."
            )
        else:
            incident_summary = (
                f"A security incident at {org.name} ({org.industry} sector) "
                f"has resulted in an estimated total cost of "
                f"${impact.total_cost:,.2f}. "
                f"{impact.records_compromised:,} records have been compromised "
                f"with {impact.downtime_hours:.1f} hours of system downtime."
            )

        # Build financial impact breakdown
        if impact is not None:
            compliance_total = sum(impact.compliance_penalties.values())
            financial_impact = {
                "total_cost": impact.total_cost,
                "downtime_cost": impact.downtime_cost,
                "data_loss_cost": impact.data_loss_cost,
                "compliance_penalties": impact.compliance_penalties,
                "compliance_penalties_total": compliance_total,
                "reputation_damage": impact.reputation_damage,
                "estimated_stock_impact_pct": metrics.stock_price_impact_pct,
            }
        else:
            financial_impact = {
                "total_cost": 0.0,
                "downtime_cost": 0.0,
                "data_loss_cost": 0.0,
                "compliance_penalties": {},
                "compliance_penalties_total": 0.0,
                "reputation_damage": 0.0,
                "estimated_stock_impact_pct": 0.0,
            }

        # Build customer impact
        customer_impact = {
            "churn_rate_pct": metrics.customer_churn_rate,
            "records_compromised": (
                impact.records_compromised if impact else 0
            ),
            "media_exposure": metrics.media_exposure_level,
        }

        # Build regulatory status
        regulatory_status = {
            "risk_level": metrics.regulatory_risk_level,
            "notification_obligations": metrics.notification_obligations,
            "sec_disclosure_required": metrics.sec_disclosure_required,
            "board_notification_required": metrics.board_notification_required,
        }

        # Build recovery timeline
        recovery_timeline = {
            "estimated_days": metrics.estimated_recovery_time_days,
            "current_downtime_hours": (
                impact.downtime_hours if impact else 0.0
            ),
        }

        # Generate recommendations based on current state
        recommendations = self._generate_recommendations(
            game_state, metrics
        )

        report = {
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "organization": org.name,
            "industry": org.industry,
            "incident_summary": incident_summary,
            "financial_impact": financial_impact,
            "customer_impact": customer_impact,
            "regulatory_status": regulatory_status,
            "recovery_timeline": recovery_timeline,
            "recommendations": recommendations,
        }

        logger.info("Board report generated with %d recommendations", len(recommendations))

        return report

    def _generate_recommendations(
        self,
        game_state: GameState,
        metrics: ExecutiveMetrics,
    ) -> List[str]:
        """
        Generate actionable recommendations based on current incident state.

        Produces 3-5 prioritized recommendations for the executive team
        based on the current metrics and game state.

        Args:
            game_state: Current game state.
            metrics: Calculated executive metrics.

        Returns:
            List of 3-5 recommendation strings.
        """
        recommendations: List[str] = []
        impact = game_state.business_impact

        # Always recommend incident response activation
        recommendations.append(
            "Activate the incident response plan and establish an executive "
            "war room for coordinated decision-making."
        )

        # Regulatory notification recommendation
        if metrics.notification_obligations:
            frameworks = ", ".join(
                obligation.split(":")[0]
                for obligation in metrics.notification_obligations
            )
            recommendations.append(
                f"Engage legal counsel immediately to begin regulatory "
                f"notifications for: {frameworks}."
            )

        # SEC disclosure recommendation
        if metrics.sec_disclosure_required:
            recommendations.append(
                "Prepare SEC Form 8-K disclosure with legal and finance teams. "
                "Filing deadline is 4 business days from materiality determination."
            )

        # Customer communication recommendation
        if metrics.customer_churn_rate > 5.0:
            recommendations.append(
                "Launch proactive customer communication and offer credit "
                "monitoring services to affected individuals to mitigate churn."
            )

        # Recovery and containment recommendation
        if impact is not None and impact.downtime_hours > 24:
            recommendations.append(
                "Prioritize system recovery and engage third-party forensics "
                "to accelerate containment and reduce ongoing downtime costs."
            )

        # Stock impact recommendation
        if metrics.stock_price_impact_pct < -5.0:
            recommendations.append(
                "Coordinate with investor relations to prepare public "
                "statements and manage shareholder communications."
            )

        # Ensure we have at least 3 recommendations
        if len(recommendations) < 3:
            recommendations.append(
                "Conduct a thorough post-incident review to identify root "
                "causes and implement preventive controls."
            )

        if len(recommendations) < 3:
            recommendations.append(
                "Review and update the organization's cybersecurity insurance "
                "coverage based on the current incident scope."
            )

        # Cap at 5 recommendations
        return recommendations[:5]
