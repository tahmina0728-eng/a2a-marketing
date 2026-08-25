"""
agents/infosys/orchestrator.py — CampaignOrchestrator.

Runs the Infosys A2A pipeline:

  [Aether →] Logos → Helia → Ideon → parallel(Morphis, Kinetik)

Each stage receives the previous agent's AgentResponse; the orchestrator
stops early if a stage fails or is blocked and returns a partial result
so the caller always gets something useful.

Usage:
    from app.agents.infosys.orchestrator import CampaignOrchestrator

    orch = CampaignOrchestrator()

    # Full pipeline with visuals
    result = await orch.run_async({
        "campaign_name": "AI Governance Sprint",
        "sub_brand":     "Infosys Topaz",
        "objective":     "180 MQLs from BFSI CIOs in 8 weeks",
        "audience":      "CIOs in European banking",
        "buyer_truth":   "asked to show AI returns before the governance exists",
        "channels":      ["LinkedIn"],
        "market":        "UK",
        "locale":        "en-GB",
    }, run_aether=True, run_visuals=True)
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.agents.infosys.aether import AetherAgent
from app.agents.infosys.logos import LogosAgent
from app.agents.infosys.helia import HeliaAgent
from app.agents.infosys.ideon import IdeonAgent
from app.agents.infosys.morphis import MorphisAgent
from app.agents.infosys.kinetik import KinetikAgent
from app.schemas.common import AgentResponse


class CampaignOrchestrator:
    """
    Full pipeline: [Aether →] Logos → Helia → Ideon → parallel(Morphis, Kinetik).

    - Aether is optional (run_aether=True): prepends market intelligence research
      and merges the top buyer truth + whitespace into the Logos brief.
    - Morphis + Kinetik are optional (run_visuals=True): run in parallel after
      Ideon to produce key-visual specs and motion specs.
    """

    def __init__(self) -> None:
        self.aether  = AetherAgent()
        self.logos   = LogosAgent()
        self.helia   = HeliaAgent()
        self.ideon   = IdeonAgent()
        self.morphis = MorphisAgent()
        self.kinetik = KinetikAgent()

    def run(self, request: dict, run_aether: bool = False, run_visuals: bool = False) -> dict:
        """
        Run the full pipeline synchronously.

        Args:
            request:      brief request dict (campaign_name, sub_brand, objective, …)
            run_aether:   if True, Aether runs first and enriches the brief
            run_visuals:  if True, Morphis + Kinetik run in parallel after Ideon
        """
        aether_content: dict = {}

        # ── Phase 0 (optional): Aether — market intelligence ──────────────────
        if run_aether:
            aether_scope = {
                "campaign_name": request.get("campaign_name", ""),
                "brand":         request.get("brand", "Infosys"),
                "sub_brand":     request.get("sub_brand", ""),
                "segment":       request.get("audience", ""),
                "industry":      request.get("industry", ""),
                "market":        request.get("market", ""),
                "objective":     request.get("objective", ""),
                "timeframe":     request.get("timing", ""),
            }
            aether_result = self.aether.run(aether_scope)

            if aether_result.status == "completed" and aether_result.artifact:
                aether_content = aether_result.artifact.content

                # Merge the top candidate buyer truth + whitespace into the brief
                truths = aether_content.get("candidate_buyer_truths", [])
                if truths and not request.get("buyer_truth"):
                    request = {**request, "buyer_truth": truths[0].get("statement", "")}

                whitespace = (aether_content.get("competitor_context") or {}).get("whitespace", "")
                if whitespace and not request.get("whitespace"):
                    request = {**request, "whitespace": whitespace}

                timing = aether_content.get("right_buyer_right_moment", "")
                if timing and not request.get("timing_note"):
                    request = {**request, "timing_note": timing}

        # ── Phase 1: Logos — validate and score the brief ─────────────────────
        logos_result = self.logos.run(request)

        if logos_result.status == "failed":
            return {
                "status": "failed",
                "stage": "logos",
                "error": logos_result.qa.get("error", "Logos agent failed"),
            }

        brief_content = logos_result.artifact.content if logos_result.artifact else {}

        # Surface any compliance blockers from the brief gate
        gate = brief_content.get("gate", {})
        if gate.get("overall") == "BLOCK":
            return {
                "status": "blocked",
                "stage": "logos",
                "validated_brief": brief_content,
                "blockers": [
                    f for f in gate.get("flags", []) if f.get("status") == "BLOCK"
                ],
            }

        # ── Phase 2: Helia — creative platform ────────────────────────────────
        helia_result = self.helia.run(logos_result)

        if helia_result.status == "failed":
            return {
                "status": "partial",
                "stage": "logos",  # last successful stage
                "validated_brief": brief_content,
                "error": helia_result.qa.get("error", "Helia agent failed"),
            }

        # ── Phase 3: Ideon — copy deck ────────────────────────────────────────
        ideon_result = self.ideon.run({
            "brief": logos_result,
            "creative_platform": helia_result,
        })

        all_flags = (
            logos_result.flags
            + helia_result.flags
            + ideon_result.flags
        )

        morphis_content: dict = {}
        kinetik_content: dict = {}

        # ── Phase 4 (optional): Morphis + Kinetik in parallel ─────────────────
        if run_visuals and ideon_result.status != "failed":
            channels = request.get("channels", ["LinkedIn"])
            visual_ctx = {
                "creative_platform": helia_result,
                "copy_deck": ideon_result,
                "channels": channels,
            }

            def _run_morphis():
                return self.morphis.run(visual_ctx)

            def _run_kinetik():
                return self.kinetik.run(visual_ctx)

            with ThreadPoolExecutor(max_workers=2) as pool:
                morphis_future = pool.submit(_run_morphis)
                kinetik_future = pool.submit(_run_kinetik)
                morphis_result = morphis_future.result()
                kinetik_result = kinetik_future.result()

            if morphis_result.artifact:
                morphis_content = morphis_result.artifact.content
                all_flags += morphis_result.flags
            if kinetik_result.artifact:
                kinetik_content = kinetik_result.artifact.content
                all_flags += kinetik_result.flags

        final_status = "completed" if ideon_result.status != "failed" else "partial"
        final_stage  = "ideon"
        if run_visuals:
            final_stage = "kinetik" if kinetik_content else ("morphis" if morphis_content else "ideon")

        result: dict = {
            "status": final_status,
            "stage": final_stage,
            "validated_brief": brief_content,
            "creative_platform": (
                helia_result.artifact.content if helia_result.artifact else {}
            ),
            "copy_deck": (
                ideon_result.artifact.content if ideon_result.artifact else {}
            ),
            "compliance_flags": [f.model_dump() for f in all_flags],
            "blocker_count": sum(1 for f in all_flags if f.status == "BLOCK"),
        }

        if aether_content:
            result["aether_intelligence"] = aether_content
        if morphis_content:
            result["key_visual_spec"] = morphis_content
        if kinetik_content:
            result["motion_spec"] = kinetik_content

        return result

    async def run_async(
        self,
        request: dict,
        *,
        run_aether: bool = False,
        run_visuals: bool = False,
    ) -> dict:
        """Async wrapper — runs the sync pipeline in a thread so it's safe inside FastAPI."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.run(request, run_aether=run_aether, run_visuals=run_visuals),
        )
