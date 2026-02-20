"""
Analytics and After Action Review API endpoints.
"""
import io

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import StreamingResponse
from typing import Optional, List
from api.services.aar_service import AARService
from api.services.game_session_service import GameSessionService
from api.services.report_generator import ReportGenerator
from api.models import AARReport, PerformanceDashboard, AARRequest, GameState
from api.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

# Initialize services
aar_service = AARService()
session_service = GameSessionService()
report_generator = ReportGenerator()


@router.post("/aar/{session_id}", response_model=AARReport)
async def generate_aar(session_id: str, include_alternatives: bool = True):
    """
    Generate an After Action Review for a completed game session.

    Args:
        session_id: The game session ID to analyze
        include_alternatives: Whether to include alternative path suggestions

    Returns:
        AARReport with decision analysis, grades, and recommendations
    """
    try:
        game_state = session_service.get_session(session_id)
        if not game_state:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        if game_state.status == "in-progress":
            raise HTTPException(
                status_code=400,
                detail="Cannot generate AAR for an in-progress session. End the game first."
            )

        report = aar_service.generate_aar(
            game_state=game_state,
            include_alternatives=include_alternatives
        )

        logger.info(
            f"AAR generated for session {session_id}: grade={report.overall_grade}",
            extra={"session_id": session_id, "grade": report.overall_grade}
        )

        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate AAR for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate AAR: {str(e)}")


@router.get("/aar/{session_id}", response_model=AARReport)
async def get_aar(session_id: str):
    """
    Retrieve a previously generated AAR for a session.
    If no AAR exists, generates one on the fly.

    Args:
        session_id: The game session ID

    Returns:
        AARReport
    """
    try:
        game_state = session_service.get_session(session_id)
        if not game_state:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        if game_state.status == "in-progress":
            raise HTTPException(
                status_code=400,
                detail="Cannot retrieve AAR for an in-progress session."
            )

        report = aar_service.generate_aar(game_state=game_state)
        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get AAR for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get AAR: {str(e)}")


@router.get("/metrics/{session_id}")
async def get_session_metrics(session_id: str):
    """
    Get performance metrics for a specific game session.

    Args:
        session_id: The game session ID

    Returns:
        Dictionary of performance metrics
    """
    try:
        game_state = session_service.get_session(session_id)
        if not game_state:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        metrics = aar_service.calculate_metrics(game_state)

        logger.info(
            f"Metrics calculated for session {session_id}",
            extra={"session_id": session_id, "metric_count": len(metrics)}
        )

        return {
            "session_id": session_id,
            "score": game_state.score,
            "time_elapsed": game_state.time_elapsed,
            "status": game_state.status,
            "metrics": {k: v.model_dump() for k, v in metrics.items()}
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metrics for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/dashboard", response_model=PerformanceDashboard)
async def get_dashboard(status: Optional[str] = Query("completed", description="Session status filter")):
    """
    Get aggregated performance dashboard across all completed sessions.

    Args:
        status: Filter sessions by status (default: completed)

    Returns:
        PerformanceDashboard with aggregated metrics and trends
    """
    try:
        sessions_metadata = session_service.list_sessions(status_filter=status)

        # Load full game states for completed sessions
        game_states = []
        for meta in sessions_metadata:
            sid = meta.get("session_id", "")
            state = session_service.get_session(sid)
            if state:
                game_states.append(state)

        dashboard = aar_service.build_dashboard(game_states)

        logger.info(
            f"Dashboard built from {len(game_states)} sessions",
            extra={"session_count": len(game_states)}
        )

        return dashboard

    except Exception as e:
        logger.error(f"Failed to build dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to build dashboard: {str(e)}")


@router.get("/trends")
async def get_trends(
    metric: str = Query("score", description="Metric to trend (score, time_elapsed, objectives_completed)"),
    limit: int = Query(20, ge=1, le=100, description="Number of recent sessions to include")
):
    """
    Get trend data for a specific metric across recent sessions.

    Args:
        metric: Which metric to trend
        limit: How many recent sessions to include

    Returns:
        List of data points for charting
    """
    try:
        sessions_metadata = session_service.list_sessions(status_filter="completed")

        # Sort by most recent and limit
        sessions_metadata = sorted(
            sessions_metadata,
            key=lambda s: s.get("created_at", ""),
            reverse=True
        )[:limit]

        data_points = []
        for meta in sessions_metadata:
            sid = meta.get("session_id", "")
            state = session_service.get_session(sid)
            if state:
                point = {
                    "session_id": sid,
                    "organization": state.organization.name,
                    "player_role": state.player_role,
                    "time_elapsed": state.time_elapsed,
                }

                if metric == "score":
                    point["value"] = state.score
                elif metric == "time_elapsed":
                    point["value"] = state.time_elapsed
                elif metric == "objectives_completed":
                    completed = sum(1 for o in state.objectives if o.status == "completed")
                    point["value"] = completed
                elif metric == "total_cost" and state.business_impact:
                    point["value"] = state.business_impact.total_cost
                else:
                    point["value"] = state.score

                data_points.append(point)

        # Reverse so oldest is first (for charting)
        data_points.reverse()

        return {
            "metric": metric,
            "data_points": data_points,
            "count": len(data_points)
        }

    except Exception as e:
        logger.error(f"Failed to get trends: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get trends: {str(e)}")


@router.get("/export/json/{session_id}")
async def export_session_json(session_id: str):
    """
    Export full game session data as JSON.

    Args:
        session_id: The game session ID

    Returns:
        Complete game state data
    """
    try:
        game_state = session_service.get_session(session_id)
        if not game_state:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        return game_state.model_dump(mode="json")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export: {str(e)}")


@router.get("/export/pdf/{session_id}")
async def export_session_pdf(session_id: str):
    """
    Export AAR as PDF.

    Args:
        session_id: The game session ID

    Returns:
        PDF file as a streaming response
    """
    try:
        game_state = session_service.get_session(session_id)
        if not game_state:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        if game_state.status == "in-progress":
            raise HTTPException(
                status_code=400,
                detail="Cannot export PDF for an in-progress session. End the game first."
            )

        report = aar_service.generate_aar(game_state=game_state)
        report_dict = report.model_dump(mode="json")
        game_state_dict = game_state.model_dump(mode="json")

        pdf_bytes = report_generator.generate_pdf(report_dict, game_state_dict)

        logger.info(
            f"PDF exported for session {session_id}: {len(pdf_bytes)} bytes",
            extra={"session_id": session_id}
        )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="aar_{session_id}.pdf"'
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export PDF for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export PDF: {str(e)}")


@router.get("/export/csv/{session_id}")
async def export_session_csv(session_id: str):
    """
    Export game session timeline as CSV data.

    Args:
        session_id: The game session ID

    Returns:
        CSV-formatted timeline data
    """
    try:
        game_state = session_service.get_session(session_id)
        if not game_state:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Build CSV rows from timeline
        rows = []
        for event in game_state.incident_timeline:
            rows.append({
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type,
                "description": event.description,
                "severity": event.severity,
                "actor": event.actor
            })

        return {
            "session_id": session_id,
            "columns": ["timestamp", "event_type", "description", "severity", "actor"],
            "rows": rows,
            "total_events": len(rows)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export CSV for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export CSV: {str(e)}")
