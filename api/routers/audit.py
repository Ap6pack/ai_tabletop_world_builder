#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Audit log and compliance reporting API endpoints.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from api.models import AuditLog, ComplianceReport
from api.services.audit_log_service import AuditLogService
from api.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/audit", tags=["audit"])

# Initialize audit log service
audit_service = AuditLogService()


@router.get("/logs", response_model=list[AuditLog])
async def get_audit_logs(
    start_date: str | None = Query(None, description="Start date (ISO format)"),
    end_date: str | None = Query(None, description="End date (ISO format)"),
    event_type: str | None = Query(None, description="Event type filter"),
    severity: str | None = Query(None, description="Severity filter"),
    session_id: str | None = Query(None, description="Session ID filter"),
    user_id: str | None = Query(None, description="User ID filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
):
    """
    Retrieve audit logs with optional filters.

    Args:
        start_date: Filter logs after this date (ISO format)
        end_date: Filter logs before this date (ISO format)
        event_type: Filter by event type (policy_check, violation, filter, sanitization)
        severity: Filter by severity (info, warning, error, critical)
        session_id: Filter by session ID
        user_id: Filter by user ID
        limit: Maximum number of logs to return

    Returns:
        List of AuditLog entries
    """
    try:
        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        logs = audit_service.get_logs(
            start_date=start_dt,
            end_date=end_dt,
            event_type=event_type,
            severity=severity,
            session_id=session_id,
            user_id=user_id,
            limit=limit,
        )

        logger.info(
            f"Retrieved {len(logs)} audit logs", extra={"event_type": event_type, "severity": severity, "limit": limit}
        )

        return logs

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}") from e
    except Exception as e:
        logger.error(f"Failed to retrieve audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}") from e


@router.get("/compliance-report", response_model=ComplianceReport)
async def get_compliance_report(
    start_date: str = Query(..., description="Report start date (ISO format)"),
    end_date: str = Query(..., description="Report end date (ISO format)"),
):
    """
    Generate a compliance report for a time period.

    Args:
        start_date: Start of reporting period (ISO format, required)
        end_date: End of reporting period (ISO format, required)

    Returns:
        ComplianceReport with statistics and metrics
    """
    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        if start_dt > end_dt:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

        report = audit_service.generate_compliance_report(start_dt, end_dt)

        logger.info(
            f"Generated compliance report: {report.total_checks} checks, {report.total_violations} violations",
            extra={"period_start": start_date, "period_end": end_date, "violation_rate": report.violation_rate},
        )

        return report

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}") from e
    except Exception as e:
        logger.error(f"Failed to generate compliance report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}") from e


@router.post("/cleanup")
async def cleanup_old_logs(retention_days: int = Query(90, ge=7, le=365, description="Number of days to retain logs")):
    """
    Clean up audit logs older than the retention period.

    Args:
        retention_days: Number of days to retain logs (default: 90)

    Returns:
        Number of log files deleted
    """
    try:
        deleted_count = audit_service.cleanup_old_logs(retention_days)

        logger.info(
            f"Audit log cleanup completed: {deleted_count} files deleted", extra={"retention_days": retention_days}
        )

        return {
            "message": f"Successfully deleted {deleted_count} old log files",
            "retention_days": retention_days,
            "files_deleted": deleted_count,
        }

    except Exception as e:
        logger.error(f"Failed to cleanup logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup logs: {str(e)}") from e


@router.get("/stats")
async def get_audit_stats():
    """
    Get audit log statistics (file count, disk usage, etc.).

    Returns:
        Dictionary with audit statistics
    """
    try:
        log_dir = audit_service.log_dir

        if not log_dir.exists():
            return {"total_log_files": 0, "disk_usage_mb": 0, "oldest_log_date": None, "newest_log_date": None}

        log_files = list(log_dir.glob("audit_*.jsonl"))
        total_size = sum(f.stat().st_size for f in log_files)

        dates = []
        for f in log_files:
            try:
                date_str = f.stem.replace("audit_", "")
                dates.append(datetime.fromisoformat(date_str))
            except ValueError:
                continue

        return {
            "total_log_files": len(log_files),
            "disk_usage_mb": round(total_size / (1024 * 1024), 2),
            "oldest_log_date": min(dates).isoformat() if dates else None,
            "newest_log_date": max(dates).isoformat() if dates else None,
        }

    except Exception as e:
        logger.error(f"Failed to get audit stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}") from e
