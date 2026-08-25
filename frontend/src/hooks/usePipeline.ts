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

  // ── Infosys A2A pipeline ───────────────────────────────────────────────────
  const startInfosysCampaign = useCallback(async (brief: HarnessBriefRequest) => {
    closeSSE();
    setState({ ...INITIAL_STATE, status: "running" });

    // Map HarnessBriefRequest → InfosysPipelineRequest
    const product = (brief as any).product ?? "";
    const subBrand = product === "Infosys (IT Services & Consulting)" ? "" : product;

    const b = brief as any;
    const body = {
      campaign_name: brief.campaign_name ?? "Infosys Campaign",
      sub_brand:     subBrand,
      objective:     b.objective ?? b.campaign_objective ?? brief.goal ?? "",
      audience:      b.audience_description ?? b.audience ?? "",
      buyer_truth:   b.buyer_truth ?? b.fan_truth ?? "",
      channels:      brief.channels ?? ["LinkedIn"],
      market:        brief.market ?? "UK",
      locale:        b.locale ?? "en-GB",
      industry:      "enterprise_technology",
      budget:        b.budget_range ?? brief.budget ?? "",
      run_aether:    false,
      run_visuals:   false,
    };

    try {
      const res = await fetch(`${API_BASE}/infosys/pipeline`, {
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

      const result = await res.json();

      // Logos gate blocked the brief — surface feedback as a structured pipeline output
      if (result.status === "blocked") {
        const vb = result.validated_brief ?? {};
        const blockers: string[] = (result.blockers ?? []).map((b: any) => `${b.element}: ${b.rule}`);
        const missing = [
          vb.kpi?.startsWith?.("MISSING") ? "KPI (e.g. 150 MQLs over 8 weeks)" : null,
          vb.buyer_truth?.statement?.startsWith?.("MISSING") ? "Buyer truth (the human tension)" : null,
          (vb.formats ?? []).some((f: string) => f?.startsWith?.("MISSING")) ? "Ad formats/specs (e.g. LinkedIn 1200×627)" : null,
          vb.budget === "MISSING" ? "Budget" : null,
          vb.timing === "MISSING" ? "Flight dates" : null,
        ].filter(Boolean);
        setState({
          campaign_id:     null,
          status:          "done",
          pipeline_output: {
            campaign_copy: {
              short_headline:  "⚠ Brief Incomplete — Logos Gate",
              medium_headline: `Missing: ${missing.join(" · ")}`,
              body:            vb.display_brief ?? blockers.join("\n"),
              cta:             "Please add the missing fields and regenerate",
            },
            creative_strategy: { hero_message: "Brief blocked at Logos validation gate" },
            validated_brief:   vb,
            infosys_pipeline:  true,
            infosys_blocked:   true,
            compliance_flags:  result.blockers ?? [],
          },
          error:       null,
          agentStatus: { logos: "done" },
          liveLog:     [],
          milestones:  {
            copy: {
              short_headline:  "⚠ Brief Incomplete — Logos Gate",
              medium_headline: `Missing: ${missing.join(" · ")}`,
              body:            vb.display_brief ?? blockers.join("\n"),
              cta:             "Please add the missing fields and regenerate",
            },
          },
        });
        return;
      }

      const deck  = result.copy_deck ?? {};
      const plat  = result.creative_platform ?? {};
      const vbrief = result.validated_brief ?? {};

      // Pick the recommended variant from Ideon's variants[] array.
      // Ideon schema: variants[recommended_variant].{headline,subheadline,body,cta}
      // Fallback chain: banner_copy → old headlines.hero_options (backward compat)
      const _recIdx   = typeof deck.recommended_variant === "number" ? deck.recommended_variant : 0;
      const _variants = Array.isArray(deck.variants) ? deck.variants : [];
      const _best     = _variants[_recIdx] ?? _variants[0] ?? null;

      // Normalise into standard pipeline_output shape so existing panels render
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
          linkedin:      deck.social_captions?.linkedin ?? "",
          email:         deck.body_copy?.email ?? "",
          ...(deck.banner_copy?.linkedin_1200x627
            ? { linkedin_banner: `${deck.banner_copy.linkedin_1200x627.heading} — ${deck.banner_copy.linkedin_1200x627.subheading}` }
            : {}),
        },
      };

      const creative_strategy = {
        hero_message:       plat.big_idea ?? plat.territory_name ?? "",
        brand_territory:    plat.territory_name ?? "",
        creative_direction: plat.visual_world ?? "",
        tone_of_voice:      plat.tone_of_voice ?? "",
        audience_insight:   vbrief.buyer_truth ?? vbrief.audience ?? "",
      };

      setState({
        campaign_id:     null,
        status:          "done",
        pipeline_output: {
          campaign_copy,
          creative_strategy,
          validated_brief:    vbrief,
          creative_platform:  plat,
          copy_deck:          deck,
          infosys_pipeline:   true,
          compliance_flags:   result.compliance_flags ?? [],
        },
        error:       null,
        agentStatus: { logos: "done", helia: "done", ideon: "done" },
        liveLog:     [],
        milestones:  {
          copy: {
            short_headline:  campaign_copy.short_headline,
            medium_headline: campaign_copy.medium_headline,
            body:            campaign_copy.body,
            cta:             campaign_copy.cta,
            // also expose variants so any copy panel can show all options
            variants:        _variants,
            recommended_variant: _recIdx,
          },
        },
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Connection failed — is the harness running?";
      setState((s) => ({ ...s, status: "error", error: msg }));
    }
  }, [closeSSE]);

  const reset = useCallback(() => { closeSSE(); setState(INITIAL_STATE); }, [closeSSE]);

  return { state, startCampaign, startFullCampaign, startInfosysCampaign, reset };
}
