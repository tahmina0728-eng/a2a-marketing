/**
 * CampaignOS — usePipeline hook
 * Manages SSE connection, pipeline state, and approval submissions.
 * This single hook drives the entire live campaign UI.
 */
import { useState, useRef, useCallback } from "react";
import type {
  PipelineState,
  PipelineEvent,
  AssetReadyEvent,
  HumanGateEvent,
  AgentName,
  CampaignBrief,
} from "../types/pipeline";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const INITIAL_STATE: PipelineState = {
  campaign_id: null,
  status: "idle",
  current_agent: null,
  events: [],
  assets: [],
  pending_gate: null,
  live_tokens: {} as Record<AgentName, string>,
  error: null,
};

export function usePipeline() {
  const [state, setState] = useState<PipelineState>(INITIAL_STATE);
  const esRef = useRef<EventSource | null>(null);

  // ── Start a new campaign ──────────────────────────────────
  const startCampaign = useCallback(async (brief: CampaignBrief) => {
    // Reset state
    setState({ ...INITIAL_STATE, status: "running" });
    esRef.current?.close();

    // POST to start pipeline
    const res = await fetch(`${API_BASE}/campaign/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(brief),
    });
    if (!res.ok) throw new Error(`Failed to start campaign: ${res.statusText}`);
    const { campaign_id } = await res.json();

    setState((s) => ({ ...s, campaign_id }));

    // Connect SSE stream
    const es = new EventSource(`${API_BASE}/campaign/${campaign_id}/stream`);
    esRef.current = es;

    es.onmessage = (e) => {
      const event = JSON.parse(e.data) as PipelineEvent;
      handleEvent(event, campaign_id);
    };

    es.onerror = () => {
      setState((s) => ({
        ...s,
        status: "error",
        error: "Lost connection to pipeline. Check backend.",
      }));
      es.close();
    };
  }, []);

  // ── Handle each SSE event ─────────────────────────────────
  const handleEvent = useCallback(
    (event: PipelineEvent, _campaign_id: string) => {
      setState((s) => {
        const next = { ...s, events: [...s.events, event] };

        switch (event.type) {
          case "agent_start":
            next.current_agent = event.agent;
            // Clear token buffer for this agent
            next.live_tokens = { ...s.live_tokens, [event.agent]: "" };
            break;

          case "token":
            // Accumulate streaming tokens per agent
            next.live_tokens = {
              ...s.live_tokens,
              [event.agent]: (s.live_tokens[event.agent] || "") + event.text,
            };
            break;

          case "agent_done":
            // Clear token buffer when agent finishes
            next.live_tokens = { ...s.live_tokens, [event.agent]: "" };
            break;

          case "asset_ready":
            next.assets = [...s.assets, event as AssetReadyEvent];
            break;

          case "human_gate":
            next.status = "waiting_for_approval";
            next.pending_gate = event as HumanGateEvent;
            // Close SSE — pipeline is paused
            esRef.current?.close();
            break;

          case "gate_resumed":
            next.status = "running";
            next.pending_gate = null;
            break;

          case "error":
            if (!event.recoverable) {
              next.status = "error";
              next.error = event.message;
            }
            break;

          case "done":
            next.status = "done";
            next.current_agent = null;
            esRef.current?.close();
            break;
        }

        return next;
      });
    },
    []
  );

  // ── Submit approval decision ──────────────────────────────
  const approve = useCallback(
    async (decision: string, notes?: string, selected_index?: number) => {
      const { campaign_id, pending_gate } = state;
      if (!campaign_id || !pending_gate) return;

      await fetch(`${API_BASE}/campaign/${campaign_id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gate: pending_gate.gate,
          decision,
          notes,
          selected_index,
        }),
      });

      // Reconnect SSE — pipeline will resume within 5s
      setState((s) => ({ ...s, status: "running", pending_gate: null }));
      const es = new EventSource(
        `${API_BASE}/campaign/${campaign_id}/stream`
      );
      esRef.current = es;
      es.onmessage = (e) => {
        const event = JSON.parse(e.data) as PipelineEvent;
        handleEvent(event, campaign_id);
      };
    },
    [state, handleEvent]
  );

  // ── Reset ─────────────────────────────────────────────────
  const reset = useCallback(() => {
    esRef.current?.close();
    setState(INITIAL_STATE);
  }, []);

  return { state, startCampaign, approve, reset };
}
