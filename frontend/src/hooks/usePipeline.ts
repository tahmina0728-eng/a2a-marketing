import { useState, useCallback, useRef } from "react";
import type { PipelineState, HarnessBriefRequest, AgentStatus, AgentEvent } from "../types/pipeline";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const INITIAL_STATE: PipelineState = {
  campaign_id:  null,
  status:       "idle",
  pipeline_output: null,
  error:        null,
  agentStatus:  {},
  liveLog:      [],
  milestones:   {},
};

export function usePipeline() {
  const [state, setState] = useState<PipelineState>(INITIAL_STATE);
  const esRef = useRef<EventSource | null>(null);

  // Close any open SSE connection
  const closeSSE = useCallback(() => {
    if (esRef.current) { esRef.current.close(); esRef.current = null; }
  }, []);

  // ── Brief-only endpoint (synchronous, no SSE) ──────────────────────────────
  const startCampaign = useCallback(async (brief: HarnessBriefRequest) => {
    closeSSE();
    setState({ ...INITIAL_STATE, status: "running" });
    try {
      const res = await fetch(`${API_BASE}/brief-full`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(brief),
      });
      if (!res.ok) {
        const text = await res.text();
        let msg = text;
        try {
          const j = JSON.parse(text);
          msg = Array.isArray(j.detail) ? j.detail.map((e: any) => e.msg).join(", ") : j.detail ?? text;
        } catch {}
        setState((s) => ({ ...s, status: "error", error: msg }));
        return;
      }
      const result = await res.json();
      const _rawMB2 = result.machine_brief ?? {};
      let _flatMB2: Record<string,unknown> = typeof _rawMB2 === "string" ? JSON.parse(_rawMB2) : { ..._rawMB2 };
      if (_flatMB2.machine_brief && typeof _flatMB2.machine_brief === "string") {
        try { _flatMB2 = { ..._flatMB2, ...JSON.parse(_flatMB2.machine_brief as string) }; } catch {}
      }
      const output = {
        ..._flatMB2,
        creative_strategy:    result.creative_strategy,
        campaign_copy:        result.campaign_copy,
        audience_insights:    (_flatMB2.audience_insights as string | undefined) ?? result.machine_brief?.audience_insights,
        creative_pipeline:    result.creative_pipeline,
        performance_forecast: result.performance_forecast,
      };
      setState({
        campaign_id:     result.campaign_id ?? null,
        status:          "done",
        pipeline_output: Object.keys(output).length > 0 ? output : result,
        error:           null,
        agentStatus:     {},
        liveLog:         [],
        milestones:      {},
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Connection failed — is the harness running?";
      setState((s) => ({ ...s, status: "error", error: msg }));
    }
  }, [closeSSE]);

  // ── Full campaign with SSE progress streaming ──────────────────────────────
  const startFullCampaign = useCallback(async (brief: HarnessBriefRequest) => {
    closeSSE();
    setState({ ...INITIAL_STATE, status: "running" });

    try {
      // 1. POST /campaign → get campaign_id immediately
      const res = await fetch(`${API_BASE}/campaign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(brief),
      });
      if (!res.ok) {
        const text = await res.text();
        let msg = text;
        try {
          const j = JSON.parse(text);
          msg = Array.isArray(j.detail) ? j.detail.map((e: any) => e.msg).join(", ") : j.detail ?? text;
        } catch {}
        setState((s) => ({ ...s, status: "error", error: msg }));
        return;
      }
      const { campaign_id } = await res.json();
      setState((s) => ({ ...s, campaign_id }));

      // 2. Open SSE stream for live progress
      const es = new EventSource(`${API_BASE}/events/${campaign_id}`);
      esRef.current = es;

      es.onmessage = (e) => {
        const ev: AgentEvent = JSON.parse(e.data);

        if (ev.agent === "__done__") {
          es.close();
          esRef.current = null;
          const result = JSON.parse(ev.message);
          // machine_brief may be flat (Groq) or { machine_brief: json_string } (ADK output_key)
          const _rawMB = result.machine_brief ?? {};
          let _flatMB: Record<string,unknown> = typeof _rawMB === "string" ? JSON.parse(_rawMB) : { ..._rawMB };
          if (_flatMB.machine_brief && typeof _flatMB.machine_brief === "string") {
            try { _flatMB = { ..._flatMB, ...JSON.parse(_flatMB.machine_brief as string) }; } catch {}
          }
          const output = {
            ..._flatMB,
            creative_strategy:    result.creative_strategy,
            campaign_copy:        result.campaign_copy,
            audience_insights:    (_flatMB.audience_insights as string | undefined) ?? (result.audience_insights as string | undefined) ?? result.machine_brief?.audience_insights,
            creative_pipeline:    result.creative_pipeline,
            performance_forecast: result.performance_forecast,
          };
          setState((s) => ({
            ...s,
            status:          "done",
            pipeline_output: Object.keys(output).length > 0 ? output : result,
          }));
          return;
        }

        if (ev.agent === "__error__") {
          es.close();
          esRef.current = null;
          setState((s) => ({ ...s, status: "error", error: ev.message }));
          return;
        }

        // Milestone — merge into agent's milestone (don't replace, to preserve done-event data)
        if (ev.status === "milestone") {
          try {
            const payload = JSON.parse(ev.message);
            setState((s) => {
              const next: typeof s.milestones = {
                ...s.milestones,
                [ev.agent]: { ...(s.milestones[ev.agent] ?? {}), ...payload },
              };
              // Option 2: propagate culture brief into briefing milestone so
              // BriefingAgentDashboard can surface cultural signals live
              if (ev.agent === "culture" && payload.brief) {
                next["briefing"] = { ...(next["briefing"] ?? {}), culture_brief: payload.brief };
              }
              return { ...s, milestones: next };
            });
          } catch {}
          return;
        }

        // Step data — merge into agent's milestone (used by KV pipeline steps)
        if (ev.status === "step_data") {
          try {
            const payload = JSON.parse(ev.message);
            setState((s) => ({
              ...s,
              milestones: {
                ...s.milestones,
                [ev.agent]: { ...(s.milestones[ev.agent] ?? {}), ...payload },
              },
            }));
          } catch {}
          return;
        }

        // For "done" events: message may be JSON with "_text" + milestone data embedded
        let displayMsg = ev.message;
        if (ev.status === "done") {
          try {
            const parsed = JSON.parse(ev.message);
            if (parsed && typeof parsed === "object" && parsed._text) {
              displayMsg = parsed._text;
              // Extract milestone data from the done event (minus _text)
              const { _text, ...milestoneData } = parsed;
              if (Object.keys(milestoneData).length > 0) {
                setState((s) => {
                  const next: typeof s.milestones = {
                    ...s.milestones,
                    [ev.agent]: milestoneData,
                  };
                  // Option 2: propagate culture brief from done event into briefing milestone
                  if (ev.agent === "culture" && milestoneData.brief) {
                    next["briefing"] = { ...(next["briefing"] ?? {}), culture_brief: milestoneData.brief };
                  }
                  return { ...s, milestones: next };
                });
              }
            }
          } catch {}
        }

        // Regular progress event — update agentStatus + liveLog
        setState((s) => ({
          ...s,
          agentStatus: {
            ...s.agentStatus,
            [ev.agent]: ev.status as AgentStatus,
          },
          liveLog: [...s.liveLog, { ...ev, message: displayMsg }],
        }));
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        setState((s) =>
          s.status === "running"
            ? { ...s, status: "error", error: "Lost connection to pipeline. Is the harness running?" }
            : s
        );
      };
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Connection failed — is the harness running?";
      setState((s) => ({ ...s, status: "error", error: msg }));
    }
  }, [closeSSE]);

  // ── Infosys A2A pipeline (SSE streaming) ─────────────────────────────────
  const startInfosysCampaign = useCallback(async (brief: HarnessBriefRequest) => {
    closeSSE();
    setState({ ...INITIAL_STATE, status: "running" });

    // Map HarnessBriefRequest → InfosysPipelineRequest body
    const product  = (brief as any).product ?? "";
    const subBrand = product === "Infosys (IT Services & Consulting)" ? "" : product;
    const b = brief as any;
    const body = {
      campaign_name: brief.campaign_name ?? "Infosys Campaign",
      sub_brand:     subBrand,
      objective:     b.objective ?? b.campaign_objective ?? brief.goal ?? "",
      audience:      b.audience_description ?? (typeof b.audience === "string" ? b.audience : (b.audience?.segment ?? "")),
      buyer_truth:   b.buyer_truth ?? b.fan_truth ?? "",
      channels:      brief.channels ?? ["LinkedIn"],
      market:        brief.market ?? "UK",
      locale:        b.locale ?? "en-GB",
      industry:      "enterprise_technology",
      budget:        b.budget_range ?? brief.budget ?? "",
      run_aether:    false,
      run_visuals:   false,
    };

    // Helper: normalise a raw Infosys pipeline result → pipeline_output shape
    const _normalise = (result: any) => {
      const deck   = result.copy_deck ?? {};
      const plat   = result.creative_platform ?? {};
      const vbrief = result.validated_brief ?? {};

      const _recIdx   = typeof deck.recommended_variant === "number" ? deck.recommended_variant : 0;
      const _variants = Array.isArray(deck.variants) ? deck.variants : [];
      const _best     = _variants[_recIdx] ?? _variants[0] ?? null;

      const campaign_copy = {
        short_headline:  _best?.headline
                         ?? deck.banner_copy?.linkedin_1200x627?.heading
                         ?? deck.headlines?.hero_options?.[0] ?? "",
        medium_headline: _best?.subheadline
                         ?? deck.banner_copy?.linkedin_1200x627?.subheading
                         ?? deck.headlines?.hero_options?.[1]
                         ?? deck.headlines?.support_options?.[0] ?? "",
        body:            _best?.body ?? deck.body_copy?.web ?? "",
        cta:             _best?.cta  ?? deck.cta_bank?.[0] ?? "",
        channel_copy: {
          linkedin: deck.social_captions?.linkedin ?? "",
          email:    deck.body_copy?.email ?? "",
          ...(deck.banner_copy?.linkedin_1200x627
            ? { linkedin_banner: `${deck.banner_copy.linkedin_1200x627.heading} — ${deck.banner_copy.linkedin_1200x627.subheading}` }
            : {}),
        },
      };

      const _bigIdea     = typeof plat.big_idea === "string" ? plat.big_idea : (plat.big_idea?.statement ?? "");
      const _buyerTruth  = typeof vbrief.buyer_truth === "string" ? vbrief.buyer_truth : (vbrief.buyer_truth?.statement ?? "");
      const _recTerrName = plat.recommended_territory ?? plat.territory_name ?? "";
      const _recTerr     = (plat.territories ?? []).find((t: any) => t.name === _recTerrName) ?? (plat.territories ?? [])[0] ?? null;

      const creative_strategy = {
        hero_message:       _bigIdea || plat.hero_message?.hero_line || "",
        brand_territory:    _recTerrName,
        creative_direction: (_recTerr?.visual_cues?.[0]) ?? plat.visual_world ?? "",
        tone_of_voice:      _recTerr?.verbal_tone ?? plat.tone_of_voice ?? "",
        audience_insight:   _buyerTruth || vbrief.audience || "",
      };

      const machine_brief = {
        ...vbrief,
        brand:         vbrief.brand ?? "",
        campaign_name: vbrief.campaign_name ?? "",
        market:        vbrief.market ?? "",
        fan_truth:     _buyerTruth,
        buyer_truth:   _buyerTruth,
        audience:      vbrief.audience ?? "",
        objective:     vbrief.objective ?? vbrief.campaign_goal ?? "",
        kpi:           vbrief.kpi ?? "",
        channels:      vbrief.channels ?? [],
        budget:        vbrief.budget ?? "",
        timing:        vbrief.timing ?? "",
        sub_brand:     vbrief.sub_brand ?? "",
      };

      return {
        pipeline_output: {
          campaign_copy,
          creative_strategy,
          machine_brief,
          validated_brief:   vbrief,
          creative_platform: plat,
          copy_deck:         deck,
          infosys_pipeline:  true,
          compliance_flags:  result.compliance_flags ?? [],
        },
        copy_milestone: {
          short_headline:      campaign_copy.short_headline,
          medium_headline:     campaign_copy.medium_headline,
          body:                campaign_copy.body,
          cta:                 campaign_copy.cta,
          variants:            _variants,
          recommended_variant: _recIdx,
        },
      };
    };

    try {
      // 1. POST /infosys/campaign → get campaign_id (non-blocking)
      const res = await fetch(`${API_BASE}/infosys/campaign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const text = await res.text();
        let msg = text;
        try {
          const j = JSON.parse(text);
          msg = Array.isArray(j.detail) ? j.detail.map((e: any) => e.msg).join(", ") : j.detail ?? text;
        } catch {}
        setState((s) => ({ ...s, status: "error", error: msg }));
        return;
      }
      const { campaign_id } = await res.json();
      setState((s) => ({ ...s, campaign_id }));

      // 2. Open SSE stream — same /events/{id} endpoint as regular pipeline
      const es = new EventSource(`${API_BASE}/events/${campaign_id}`);
      esRef.current = es;

      es.onmessage = (e) => {
        const ev: AgentEvent = JSON.parse(e.data);

        // ── Pipeline complete ──────────────────────────────────────────────
        if (ev.agent === "__done__") {
          es.close();
          esRef.current = null;
          const result = JSON.parse(ev.message);
          const { pipeline_output, copy_milestone } = _normalise(result);
          setState((s) => ({
            ...s,
            status:          "done",
            pipeline_output,
            milestones: {
              ...s.milestones,
              copy:     copy_milestone,
              strategy: result.creative_platform ?? s.milestones["strategy"],
              briefing: result.validated_brief   ?? s.milestones["briefing"],
            },
          }));
          return;
        }

        if (ev.agent === "__error__") {
          es.close();
          esRef.current = null;
          setState((s) => ({ ...s, status: "error", error: ev.message }));
          return;
        }

        // ── Milestone data (per-agent live output) ─────────────────────────
        if (ev.status === "milestone") {
          try {
            const payload = JSON.parse(ev.message);
            setState((s) => ({
              ...s,
              milestones: {
                ...s.milestones,
                [ev.agent]: { ...(s.milestones[ev.agent] ?? {}), ...payload },
              },
            }));
          } catch {}
          return;
        }

        // ── Regular progress event ─────────────────────────────────────────
        let displayMsg = ev.message;
        if (ev.status === "done") {
          try {
            const parsed = JSON.parse(ev.message);
            if (parsed && typeof parsed === "object" && parsed._text) {
              displayMsg = parsed._text;
              // Merge done-event data into milestones (same pattern as startFullCampaign)
              const { _text, ...milestoneData } = parsed;
              if (Object.keys(milestoneData).length > 0) {
                setState((s) => ({
                  ...s,
                  milestones: {
                    ...s.milestones,
                    [ev.agent]: { ...(s.milestones[ev.agent] ?? {}), ...milestoneData },
                  },
                }));
              }
            }
          } catch {}
        }
        setState((s) => ({
          ...s,
          agentStatus: { ...s.agentStatus, [ev.agent]: ev.status as AgentStatus },
          liveLog:     [...s.liveLog, { ...ev, message: displayMsg }],
        }));
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        setState((s) =>
          s.status === "running"
            ? { ...s, status: "error", error: "Lost connection to pipeline. Is the harness running?" }
            : s
        );
      };
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Connection failed — is the harness running?";
      setState((s) => ({ ...s, status: "error", error: msg }));
    }
  }, [closeSSE]);

  const reset = useCallback(() => { closeSSE(); setState(INITIAL_STATE); }, [closeSSE]);

  return { state, startCampaign, startFullCampaign, startInfosysCampaign, reset };
}
