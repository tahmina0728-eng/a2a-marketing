// CampaignOS — TypeScript types for harness pipeline

export type AgentName =
  | "briefing_agent"
  | "culture_analyst"
  | "creative_director"
  | "copy_agent"
  | "kv_generator_1"
  | "kv_generator_2"
  | "kv_ranker"
  | "channel_router"
  | "content_agent"
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

// ── Harness API types ────────────────────────────────────────

export interface HarnessAudience {
  segment: string;
  location: string;
  age_range: string;
  gender: string;
  interests?: string;
}

export interface HarnessBriefRequest {
  campaign_name: string;
  brand: string;
  goal: string;
  budget: string;
  kpis: string;
  product: string;
  product_category: string;
  fan_truth: string;
  channels: string[];
  market: string;
  season: string;
  moment_type: string;
  audience: HarnessAudience;
  tone: string;
}

export interface HarnessPipelineResponse {
  status: string;
  campaign_id: string;
  pipeline_output: Record<string, unknown>;
  processing_time_ms: number;
}

// ── Pipeline UI state ────────────────────────────────────────

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
}

export interface PipelineState {
  campaign_id: string | null;
  status: "idle" | "running" | "done" | "error";
  pipeline_output: Record<string, unknown> | null;
  error: string | null;
}
