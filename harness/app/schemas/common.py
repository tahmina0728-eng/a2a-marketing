"""
schemas/common.py — shared AgentResponse envelope for all Infosys A2A agents.

Every agent in the pipeline (Logos, Helia, Ideon, Morphis, Kinetik, Director)
wraps its output in AgentResponse so the orchestrator and frontend always see
the same outer shape regardless of which stage produced it.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class AgentInfo(BaseModel):
    name: str
    version: str = "1.0"
    brand: str = "Infosys"


class JobInfo(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_name: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Artifact(BaseModel):
    type: str           # "validated_brief" | "creative_platform" | "copy_deck" | …
    content: dict       # the typed payload — see schemas/validated_brief.py etc.
    format: str = "json"


class ComplianceFlag(BaseModel):
    area: str                          # disclosure | partner | accessibility | people
    status: Literal["PASS", "BLOCK"]
    element: Optional[str] = None      # what triggered the flag
    rule: Optional[str] = None
    token: Optional[str] = None        # [APPROVED_CLIENT_REF] etc.
    routes_to: Optional[str] = None    # "legal" | "brand_team" | …


class Handoff(BaseModel):
    to: str                            # next agent name
    context: dict = Field(default_factory=dict)


class AgentResponse(BaseModel):
    schema_version: str = "1.0"
    agent: AgentInfo
    job: JobInfo
    status: Literal["completed", "needs_input", "blocked", "failed"]
    artifact: Optional[Artifact] = None
    qa: dict = Field(default_factory=dict)
    flags: list[ComplianceFlag] = Field(default_factory=list)
    handoff: Optional[Handoff] = None
