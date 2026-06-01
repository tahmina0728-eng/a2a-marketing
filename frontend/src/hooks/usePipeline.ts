import { useState, useCallback } from "react";
import type { PipelineState, HarnessBriefRequest } from "../types/pipeline";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const INITIAL_STATE: PipelineState = {
  campaign_id: null,
  status: "idle",
  pipeline_output: null,
  error: null,
};

export function usePipeline() {
  const [state, setState] = useState<PipelineState>(INITIAL_STATE);

  const startCampaign = useCallback(async (brief: HarnessBriefRequest) => {
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
          const json = JSON.parse(text);
          if (json.detail && Array.isArray(json.detail)) {
            msg = json.detail.map((e: any) => e.msg).join(", ");
          } else if (json.detail) {
            msg = json.detail;
          }
        } catch {}
        setState((s) => ({ ...s, status: "error", error: msg }));
        return;
      }

      const result = await res.json();
      // Merge all stages into pipeline_output for the UI
      const output = {
        ...(result.machine_brief ?? {}),
        creative_strategy: result.creative_strategy,
        campaign_copy:     result.campaign_copy,
        audience_insights: result.machine_brief?.audience_insights,
      };
      setState({
        campaign_id: result.campaign_id ?? null,
        status: "done",
        pipeline_output: Object.keys(output).length > 0 ? output : result,
        error: null,
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Connection failed — is the harness running?";
      setState((s) => ({ ...s, status: "error", error: msg }));
    }
  }, []);

  const reset = useCallback(() => setState(INITIAL_STATE), []);

  return { state, startCampaign, reset };
}
