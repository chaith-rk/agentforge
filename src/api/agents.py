"""Agent configuration API endpoints.

Provides REST endpoints for inspecting loaded agent configs: listing
all available agents and retrieving full details for a specific agent.
All data is derived at runtime from the YAML configs loaded at startup.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _get_call_manager():
    """Lazy import to avoid circular dependency at module load time."""
    from src.main import call_manager

    return call_manager


# --- Response Models ---


class AgentSummary(BaseModel):
    """Brief summary of a loaded agent configuration."""

    agent_id: str
    agent_name: str
    version: str
    description: str
    field_count: int
    state_count: int
    status: str  # "active" always for now


class AgentDetailResponse(BaseModel):
    """Full details for a single agent configuration."""

    agent_id: str
    agent_name: str
    version: str
    description: str
    status: str
    form_fields: list[dict]  # data_schema entries where is_candidate_input=True
    all_fields: list[dict]  # full data_schema serialized
    states: list[dict]  # [{name, description, is_terminal}]
    compliance_rules: list[str]
    voice_config: dict


# --- Endpoints ---


@router.get("", response_model=list[AgentSummary])
async def list_agents() -> list[AgentSummary]:
    """List all loaded agent configurations.

    Returns a summary of every agent whose YAML config was successfully
    loaded at startup. Always returns status="active" since inactive
    agents are simply not loaded.
    """
    cm = _get_call_manager()
    return [
        AgentSummary(
            agent_id=config.agent_id,
            agent_name=config.agent_name,
            version=config.version,
            description=config.description,
            field_count=len(config.data_schema),
            state_count=len(config.states),
            status="active",
        )
        for config in cm._agent_configs.values()
    ]


@router.get("/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(agent_id: str) -> AgentDetailResponse:
    """Get full configuration details for a specific agent.

    Args:
        agent_id: The unique agent identifier (e.g. employment_verification_v1).

    Raises:
        HTTPException 404: If no agent with the given ID is loaded.
    """
    cm = _get_call_manager()
    config = cm._agent_configs.get(agent_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    form_fields = [f.model_dump() for f in config.data_schema if f.is_candidate_input]
    all_fields = [f.model_dump() for f in config.data_schema]
    states = [
        {
            "name": s.name,
            "description": s.description,
            "is_terminal": s.is_terminal,
        }
        for s in config.states.values()
    ]
    compliance_rules = [c.name for c in config.compliance_checkpoints]

    return AgentDetailResponse(
        agent_id=config.agent_id,
        agent_name=config.agent_name,
        version=config.version,
        description=config.description,
        status="active",
        form_fields=form_fields,
        all_fields=all_fields,
        states=states,
        compliance_rules=compliance_rules,
        voice_config=config.voice_config.model_dump(),
    )
