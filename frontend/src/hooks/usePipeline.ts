import { useState, useCallback, useRef } from "react";
import type { PipelineState, HarnessBriefRequest, AgentStatus, AgentEvent } from "../types/pipeline";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
      const output = {
        ...(result.machine_brief ?? {}),
        creative_strategy: result.creative_strategy,
        campaign_copy:     result.campaign_copy,
        audience_insights: result.machine_brief?.audience_insights,
        creative_pipeline: result.creative_pipeline,
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
          const output = {
            ...(result.machine_brief ?? {}),
            creative_strategy: result.creative_strategy,
            campaign_copy:     result.campaign_copy,
            audience_insights: result.machine_brief?.audience_insights,
            creative_pipeline: result.creative_pipeline,
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

        // Milestone — replace agent's milestone data
        if (ev.status === "milestone") {
          try {
            const payload = JSON.parse(ev.message);
            setState((s) => ({
              ...s,
              milestones: { ...s.milestones, [ev.agent]: payload },
            }));
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
                setState((s) => ({
                  ...s,
                  milestones: { ...s.milestones, [ev.agent]: milestoneData },
                }));
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

  const reset = useCallback(() => { closeSSE(); setState(INITIAL_STATE); }, [closeSSE]);

  return { state, startCampaign, startFullCampaign, reset };
}
