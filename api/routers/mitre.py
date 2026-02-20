"""MITRE ATT&CK API endpoints."""
from fastapi import APIRouter, HTTPException
from typing import Optional, List

from api.services.mitre_attack_service import MITREAttackService
from api.services.game_session_service import GameSessionService
from api.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/mitre", tags=["mitre-attack"])

attack_service = MITREAttackService()
session_service = GameSessionService()


@router.get("/techniques")
async def list_techniques(
    tactic: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
):
    """List ATT&CK techniques, optionally filtered by tactic or search term."""
    if tactic:
        techniques = attack_service.get_techniques_by_tactic(tactic)
    elif search:
        techniques = attack_service.map_ttp_to_attack(search)
    else:
        techniques = list(attack_service._techniques.values())

    return {
        "techniques": [t.model_dump() for t in techniques[:limit]],
        "total": min(len(techniques), limit),
    }


@router.get("/techniques/{technique_id}")
async def get_technique(technique_id: str):
    """Get details for a specific ATT&CK technique."""
    technique = attack_service.get_technique(technique_id)
    if not technique:
        raise HTTPException(status_code=404, detail=f"Technique {technique_id} not found")
    return technique.model_dump()


@router.get("/tactics")
async def list_tactics():
    """List all ATT&CK tactics."""
    return {"tactics": attack_service._tactics}


@router.get("/coverage/{session_id}")
async def get_session_coverage(session_id: str):
    """Get ATT&CK technique coverage report for a game session."""
    game_state = session_service.get_session(session_id)
    if not game_state:
        raise HTTPException(status_code=404, detail="Session not found")
    report = attack_service.analyze_session_coverage(game_state)
    return report.model_dump()


@router.post("/map")
async def map_ttp(ttp: str):
    """Map a free-text TTP description to ATT&CK technique IDs."""
    techniques = attack_service.map_ttp_to_attack(ttp)
    return {
        "input": ttp,
        "techniques": [
            {"technique_id": t.technique_id, "name": t.name, "tactic": t.tactic}
            for t in techniques
        ],
    }
