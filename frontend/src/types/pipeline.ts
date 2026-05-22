// CampaignOS — TypeScript types for all pipeline events and assets

export type AgentName =
  | "briefing_agent"
  | "strategy_agent"
  | "kv_agent"
  | "content_agent"
  | "execution_agent"
  | "performance_agent"
  | "pipeline";

export type AssetType =
  | "machine_brief"
  | "strategy_doc"
  | "kv_concept"
  | "content_package"
  | "copy"
  | "image"
  | "execution_report"
  | "performance_report";

export type GateName =
  | "approve_brief"
  | "approve_strategy"
  | "select_kv"
  | "approve_content";

// ── SSE Event types ─────────────────────────────────────────

export interface PipelineStartEvent {
  type: "pipeline_start";
  campaign_id: string;
  brief: Record<string, unknown>;
  ts: string;
}

export interface AgentStartEvent {
  type: "agent_start";
  agent: AgentName;
  description: string;
  ts: string;
}

export interface AgentDoneEvent {
  type: "agent_done";
  agent: AgentName;
  ts: string;
}

export interface TokenEvent {
  type: "token";
  agent: AgentName;
  text: string;
  ts: string;
}

export interface ThinkingEvent {
  type: "thinking";
  agent: AgentName;
  thought: string;
  ts: string;
}

export interface AssetGeneratingEvent {
  type: "asset_generating";
  agent: AgentName;
  asset_type: AssetType;
  label: string;
  ts: string;
}

export interface AssetReadyEvent {
  type: "asset_ready";
  agent: AgentName;
  asset_type: AssetType;
  label: string;
  payload: unknown;
  url?: string;
  ts: string;
}

export interface HumanGateEvent {
  type: "human_gate";
  gate: GateName;
  data: Record<string, unknown>;
  options: string[];
  ts: string;
}

export interface GateResumedEvent {
  type: "gate_resumed";
  gate: GateName;
  decision: string;
  ts: string;
}

export interface ErrorEvent {
  type: "error";
  agent: AgentName;
  message: string;
  recoverable: boolean;
  ts: string;
}

export interface DoneEvent {
  type: "done";
  campaign_id: string;
  report: Record<string, unknown>;
  ts: string;
}

export type PipelineEvent =
  | PipelineStartEvent
  | AgentStartEvent
  | AgentDoneEvent
  | TokenEvent
  | ThinkingEvent
  | AssetGeneratingEvent
  | AssetReadyEvent
  | HumanGateEvent
  | GateResumedEvent
  | ErrorEvent
  | DoneEvent;

// ── Domain types ────────────────────────────────────────────

export interface CampaignBrief {
  goal: string;
  product: string;
  fan_truth: string;
  kpis: string[];
  channels: string[];
  budget: number;
  audience: string;
  timing?: { start_date?: string; end_date?: string };
  additional_notes?: string;
}

export interface KVConcept {
  concept_id: "A" | "B" | "C";
  concept_name: string;
  logline: string;
  tone: string;
  visual_direction: {
    hero_description: string;
    colour_palette: {
      primary: string;
      secondary: string;
      accent: string;
      background: string;
    };
    typography: { hero_font: string; body_font: string };
    photography_style: string;
    motion_style: string;
  };
  reel_script_10s: {
    scenes: Array<{
      scene_number: number;
      duration: string;
      visual: string;
      action: string;
      text_on_screen: string;
      vo_line: string;
    }>;
    music_cue: string;
    vo_direction: string;
    end_frame: { super: string; cta: string };
  };
}

export interface PipelineState {
  campaign_id: string | null;
  status:
    | "idle"
    | "running"
    | "waiting_for_approval"
    | "done"
    | "error";
  current_agent: AgentName | null;
  events: PipelineEvent[];
  assets: AssetReadyEvent[];
  pending_gate: HumanGateEvent | null;
  live_tokens: Record<AgentName, string>;
  error: string | null;
}
