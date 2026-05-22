/**
 * CampaignOS — Complete React UI
 * Live campaign pipeline with streaming agent output,
 * asset cards, and human approval gates.
 */
import { useState } from "react";
import "./App.css";
import { usePipeline } from "./hooks/usePipeline";
import type {
  AssetReadyEvent,
  HumanGateEvent,
  AgentName,
  KVConcept,
} from "./types/pipeline";

// ── Agent colours ───────────────────────────────────────────
const AGENT_COLORS: Record<AgentName | string, string> = {
  briefing_agent:    "#3b82f6",
  strategy_agent:    "#8b5cf6",
  kv_agent:          "#f59e0b",
  content_agent:     "#10b981",
  execution_agent:   "#ef4444",
  performance_agent: "#06b6d4",
  pipeline:          "#6b7280",
};

const AGENT_LABELS: Record<string, string> = {
  briefing_agent:    "Briefing Agent",
  strategy_agent:    "Strategy Agent",
  kv_agent:          "KV Agent",
  content_agent:     "Content Agent",
  execution_agent:   "Execution Agent",
  performance_agent: "Performance Agent",
};

// ── Wizard data ─────────────────────────────────────────────
type GoalId = "launch" | "sales" | "community" | "reengagement" | "expansion" | "custom";

const GOALS = [
  { id: "launch"       as GoalId, icon: "🚀", label: "Launch Awareness", desc: "Introduce a new product" },
  { id: "sales"        as GoalId, icon: "📈", label: "Drive Sales",       desc: "Increase transactions & ROAS" },
  { id: "community"    as GoalId, icon: "👥", label: "Build Community",   desc: "Grow brand advocates" },
  { id: "reengagement" as GoalId, icon: "🎯", label: "Re-engagement",     desc: "Win back lapsed customers" },
  { id: "expansion"    as GoalId, icon: "🌍", label: "Market Expansion",  desc: "Enter new territories" },
  { id: "custom"       as GoalId, icon: "✏️", label: "Custom",            desc: "Write your own goal" },
];

const MCD_PRODUCTS = [
  "McSpicy", "McSpicy Deluxe", "Big Mac", "McDouble", "McVeggie",
  "Happy Meal", "McFlurry", "McCafé", "Chicken McNuggets", "McValue Menu",
];

const FAN_TRUTHS = [
  "McDonald's fans love the ritual of the first bite of something new",
  "Friday nights belong to McDonald's",
  "Nostalgia is the most powerful flavour",
  "McDonald's is the social glue between friends",
  "McDonald's is the reward after a long day",
];

const AGE_GROUPS    = ["13–17", "18–24", "25–34", "35–44", "45–54", "55+"];
const INTERESTS     = ["Spicy food lovers", "Families", "Students", "Deal hunters", "Night owls", "Health-conscious", "Gamers", "Sports fans"];
const REGIONS       = ["Australia", "New Zealand", "United States", "United Kingdom", "SEA", "Global"];

const CHANNELS_LIST = [
  { id: "instagram", icon: "📸", label: "Instagram" },
  { id: "tiktok",    icon: "🎵", label: "TikTok" },
  { id: "youtube",   icon: "▶️", label: "YouTube" },
  { id: "email",     icon: "✉️", label: "Email" },
  { id: "google_ads",icon: "🎯", label: "Google Ads" },
  { id: "meta_ads",  icon: "📘", label: "Meta Ads" },
];

const KPI_OPTIONS = [
  { id: "reach",       label: "5M Reach" },
  { id: "ctr",         label: "2% CTR" },
  { id: "roas",        label: "3x ROAS" },
  { id: "conversions", label: "+10% Conv." },
  { id: "engagement",  label: "4% Engagement" },
  { id: "views",       label: "10M Views" },
];

const BUDGETS = [
  { value: 50000,   label: "$50K",  desc: "Pilot" },
  { value: 100000,  label: "$100K", desc: "Regional" },
  { value: 250000,  label: "$250K", desc: "Multi-channel" },
  { value: 500000,  label: "$500K", desc: "Full campaign" },
  { value: 1000000, label: "$1M",   desc: "Flagship" },
  { value: -1,      label: "Custom",desc: "Enter amount" },
];

interface WizardData {
  goal: GoalId | "";
  goalCustom: string;
  product: string;
  productCustom: string;
  fanTruth: string;
  fanTruthCustom: string;
  audienceAge: string[];
  audienceInterests: string[];
  audienceRegions: string[];
  channels: string[];
  kpis: string[];
  budget: number;
  budgetCustom: string;
}

// ── Brief Form (Wizard) ──────────────────────────────────────
function BriefForm({ onStart }: { onStart: (brief: any) => void }) {
  const [step, setStep] = useState(0);
  const [d, setD] = useState<WizardData>({
    goal: "", goalCustom: "",
    product: "", productCustom: "",
    fanTruth: "", fanTruthCustom: "",
    audienceAge: [], audienceInterests: [], audienceRegions: [],
    channels: ["instagram", "tiktok", "youtube", "email"],
    kpis: ["reach", "ctr", "roas"],
    budget: 500000, budgetCustom: "",
  });

  const TOTAL_STEPS = 6;

  function toggle<T>(arr: T[], val: T): T[] {
    return arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val];
  }

  function canProceed(): boolean {
    switch (step) {
      case 0: return !!d.goal && (d.goal !== "custom" || !!d.goalCustom.trim());
      case 1: return !!d.product || !!d.productCustom.trim();
      case 2: return !!d.fanTruth || !!d.fanTruthCustom.trim();
      case 3: return true;
      case 4: return d.channels.length > 0 && d.kpis.length > 0;
      case 5: return d.budget > 0 || !!d.budgetCustom.trim();
      default: return true;
    }
  }

  function handleLaunch() {
    const goal     = d.goal === "custom" ? d.goalCustom : GOALS.find((g) => g.id === d.goal)?.label ?? "";
    const product  = d.product === "custom" ? d.productCustom : d.product;
    const fanTruth = d.fanTruth === "custom" ? d.fanTruthCustom : d.fanTruth;
    const audience = [...d.audienceAge, ...d.audienceInterests, ...d.audienceRegions];
    const kpisLabels = d.kpis.map((k) => KPI_OPTIONS.find((o) => o.id === k)?.label ?? k);
    const budget   = d.budget === -1 ? parseFloat(d.budgetCustom) || 0 : d.budget;
    onStart({
      goal, product,
      fan_truth: fanTruth,
      kpis: kpisLabels,
      channels: d.channels,
      budget,
      audience: audience.length > 0 ? audience.join(", ") : "General audience",
      additional_notes: "",
    });
  }

  const stepContent = () => {
    switch (step) {
      case 0:
        return (
          <>
            <div className="wizard-step-label">Step 1 of 6</div>
            <h2 className="wizard-heading">What's your <span className="gradient-text">campaign goal?</span></h2>
            <p className="wizard-subheading">Choose the primary objective for this campaign</p>
            <div className="goal-grid">
              {GOALS.map((g) => (
                <div key={g.id} className={`goal-tile${d.goal === g.id ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, goal: g.id }))}>
                  <span className="goal-tile-icon">{g.icon}</span>
                  <div className="goal-tile-label">{g.label}</div>
                  <div className="goal-tile-desc">{g.desc}</div>
                </div>
              ))}
            </div>
            {d.goal === "custom" && (
              <textarea className="dark-textarea" rows={3}
                placeholder="Describe your campaign goal..."
                value={d.goalCustom}
                onChange={(e) => setD((p) => ({ ...p, goalCustom: e.target.value }))} />
            )}
          </>
        );

      case 1:
        return (
          <>
            <div className="wizard-step-label">Step 2 of 6</div>
            <h2 className="wizard-heading">What are we <span className="gradient-text">promoting?</span></h2>
            <p className="wizard-subheading">Select a product or enter your own</p>
            <div className="chip-group">
              {MCD_PRODUCTS.map((p) => (
                <button key={p} className={`chip${d.product === p ? " selected" : ""}`}
                  onClick={() => setD((prev) => ({ ...prev, product: prev.product === p ? "" : p, productCustom: "" }))}>
                  {p}
                </button>
              ))}
              <button className={`chip${d.product === "custom" ? " selected" : ""}`}
                onClick={() => setD((p) => ({ ...p, product: "custom", productCustom: "" }))}>
                + Other
              </button>
            </div>
            {d.product === "custom" && (
              <input className="dark-input" placeholder="e.g. New McWrap"
                value={d.productCustom}
                onChange={(e) => setD((p) => ({ ...p, productCustom: e.target.value }))} />
            )}
          </>
        );

      case 2:
        return (
          <>
            <div className="wizard-step-label">Step 3 of 6</div>
            <h2 className="wizard-heading">What <span className="gradient-text">fan truth</span> drives this?</h2>
            <p className="wizard-subheading">Pick a McDonald's fan truth or write your own</p>
            <div className="truth-stack">
              {FAN_TRUTHS.map((ft) => (
                <div key={ft} className={`truth-card${d.fanTruth === ft ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, fanTruth: ft, fanTruthCustom: "" }))}>
                  <span style={{ marginRight: 8, opacity: 0.4 }}>❝</span>{ft}
                </div>
              ))}
              <div className={`truth-card${d.fanTruth === "custom" ? " selected" : ""}`}
                onClick={() => setD((p) => ({ ...p, fanTruth: "custom" }))}>
                <span style={{ marginRight: 8 }}>✏️</span>Write your own...
              </div>
            </div>
            {d.fanTruth === "custom" && (
              <textarea className="dark-textarea" rows={3}
                placeholder="Describe the fan truth behind this campaign..."
                value={d.fanTruthCustom}
                onChange={(e) => setD((p) => ({ ...p, fanTruthCustom: e.target.value }))} />
            )}
          </>
        );

      case 3:
        return (
          <>
            <div className="wizard-step-label">Step 4 of 6</div>
            <h2 className="wizard-heading">Who are you <span className="gradient-text">targeting?</span></h2>
            <p className="wizard-subheading">Select all that apply — this step is optional</p>
            <div className="section-label">Age groups</div>
            <div className="chip-group">
              {AGE_GROUPS.map((a) => (
                <button key={a} className={`chip${d.audienceAge.includes(a) ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, audienceAge: toggle(p.audienceAge, a) }))}>
                  {a}
                </button>
              ))}
            </div>
            <div className="section-label">Interests</div>
            <div className="chip-group">
              {INTERESTS.map((i) => (
                <button key={i} className={`chip${d.audienceInterests.includes(i) ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, audienceInterests: toggle(p.audienceInterests, i) }))}>
                  {i}
                </button>
              ))}
            </div>
            <div className="section-label">Region</div>
            <div className="chip-group">
              {REGIONS.map((r) => (
                <button key={r} className={`chip${d.audienceRegions.includes(r) ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, audienceRegions: toggle(p.audienceRegions, r) }))}>
                  {r}
                </button>
              ))}
            </div>
          </>
        );

      case 4:
        return (
          <>
            <div className="wizard-step-label">Step 5 of 6</div>
            <h2 className="wizard-heading">Channels <span className="gradient-text">&amp; KPIs</span></h2>
            <p className="wizard-subheading">Where will the campaign run and how will we measure success?</p>
            <div className="section-label">Channels</div>
            <div className="channel-grid">
              {CHANNELS_LIST.map((ch) => (
                <div key={ch.id} className={`channel-tile${d.channels.includes(ch.id) ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, channels: toggle(p.channels, ch.id) }))}>
                  <span className="channel-icon">{ch.icon}</span>
                  <span className="channel-label">{ch.label}</span>
                </div>
              ))}
            </div>
            <div className="section-label">Success metrics</div>
            <div className="chip-group">
              {KPI_OPTIONS.map((k) => (
                <button key={k.id} className={`chip${d.kpis.includes(k.id) ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, kpis: toggle(p.kpis, k.id) }))}>
                  {k.label}
                </button>
              ))}
            </div>
          </>
        );

      case 5:
        return (
          <>
            <div className="wizard-step-label">Step 6 of 6</div>
            <h2 className="wizard-heading">What's your <span className="gradient-text">budget?</span></h2>
            <p className="wizard-subheading">Total campaign spend in USD</p>
            <div className="budget-grid">
              {BUDGETS.map((b) => (
                <div key={b.value} className={`budget-card${d.budget === b.value ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, budget: b.value }))}>
                  <div className="budget-amount">{b.label}</div>
                  <div className="budget-desc">{b.desc}</div>
                </div>
              ))}
            </div>
            {d.budget === -1 && (
              <input className="dark-input" type="number" placeholder="Enter budget in USD"
                value={d.budgetCustom}
                onChange={(e) => setD((p) => ({ ...p, budgetCustom: e.target.value }))} />
            )}
          </>
        );

      case 6: {
        const reviewGoal    = d.goal === "custom" ? d.goalCustom : GOALS.find((g) => g.id === d.goal)?.label ?? "";
        const reviewProduct = d.product === "custom" ? d.productCustom : d.product;
        const reviewTruth   = d.fanTruth === "custom" ? d.fanTruthCustom : d.fanTruth;
        const reviewAud     = [...d.audienceAge, ...d.audienceInterests, ...d.audienceRegions];
        const reviewKpis    = d.kpis.map((k) => KPI_OPTIONS.find((o) => o.id === k)?.label ?? k);
        const reviewBudget  = d.budget === -1
          ? `$${parseInt(d.budgetCustom).toLocaleString()}`
          : BUDGETS.find((b) => b.value === d.budget)?.label;
        return (
          <>
            <div className="wizard-step-label">Review</div>
            <h2 className="wizard-heading">Ready to <span className="gradient-text">launch?</span></h2>
            <p className="wizard-subheading">Confirm your campaign brief before the agents start</p>
            <div className="review-grid">
              <div className="review-item review-item-full">
                <div className="review-item-label">Goal</div>
                <div className="review-item-value">{reviewGoal}</div>
              </div>
              <div className="review-item">
                <div className="review-item-label">Product</div>
                <div className="review-item-value">{reviewProduct}</div>
              </div>
              <div className="review-item">
                <div className="review-item-label">Budget</div>
                <div className="review-item-value">{reviewBudget}</div>
              </div>
              <div className="review-item review-item-full">
                <div className="review-item-label">Fan Truth</div>
                <div className="review-item-value" style={{ fontStyle: "italic", opacity: 0.8 }}>"{reviewTruth}"</div>
              </div>
              <div className="review-item">
                <div className="review-item-label">Channels</div>
                <div className="review-item-value">{d.channels.map((ch) => CHANNELS_LIST.find((c) => c.id === ch)?.label).join(", ")}</div>
              </div>
              <div className="review-item">
                <div className="review-item-label">KPIs</div>
                <div className="review-item-value">{reviewKpis.join(", ")}</div>
              </div>
              {reviewAud.length > 0 && (
                <div className="review-item review-item-full">
                  <div className="review-item-label">Audience</div>
                  <div className="review-item-value">{reviewAud.join(", ")}</div>
                </div>
              )}
            </div>
          </>
        );
      }

      default: return null;
    }
  };

  return (
    <div className="wizard-page">
      <div className="wizard-container">
        <div className="wizard-progress">
          <div className="wizard-progress-fill" style={{ width: `${(step / TOTAL_STEPS) * 100}%` }} />
        </div>
        <div className="step-content" key={step}>
          {stepContent()}
        </div>
        <div className="wizard-nav">
          {step > 0
            ? <button className="wizard-back-btn" onClick={() => setStep((s) => s - 1)}>← Back</button>
            : <div />}
          {step < TOTAL_STEPS
            ? <button className="wizard-next-btn" disabled={!canProceed()} onClick={() => setStep((s) => s + 1)}>
                {step === TOTAL_STEPS - 1 ? "Review →" : "Continue →"}
              </button>
            : <button className="wizard-launch-btn" onClick={handleLaunch}>⚡ Launch Campaign</button>}
        </div>
      </div>
    </div>
  );
}

// ── Agent Activity Sidebar ──────────────────────────────────
function ActivitySidebar({
  events,
  liveTokens,
  currentAgent,
}: {
  events: any[];
  liveTokens: Record<string, string>;
  currentAgent: string | null;
}) {
  // Group by agent activity
  const activities = events.filter((e) =>
    ["agent_start", "thinking", "agent_done", "error", "gate_resumed",
     "pipeline_start", "done"].includes(e.type)
  );

  return (
    <div style={styles.sidebar}>
      <div style={styles.sidebarHeader}>Agent Activity</div>
      <div style={styles.activityList}>
        {activities.map((ev, i) => (
          <div key={i} className="activity-item-enter" style={styles.activityItem}>
            {ev.type === "agent_start" && (
              <div>
                <div
                  style={{
                    ...styles.agentDot,
                    background: AGENT_COLORS[ev.agent] || "#6b7280",
                  }}
                />
                <span style={styles.agentName}>
                  {AGENT_LABELS[ev.agent] || ev.agent}
                </span>
                <div style={styles.activityDesc}>{ev.description}</div>
              </div>
            )}
            {ev.type === "agent_done" && (
              <div style={{ color: "#10b981", fontSize: 11 }}>
                ✓ {AGENT_LABELS[ev.agent]} complete
              </div>
            )}
            {ev.type === "thinking" && (
              <div style={styles.thoughtBubble}>{ev.thought}</div>
            )}
            {ev.type === "error" && (
              <div style={{ color: "#ef4444", fontSize: 11 }}>
                ⚠ {ev.message}
              </div>
            )}
            {ev.type === "done" && (
              <div style={{ color: "#10b981", fontSize: 12, fontWeight: 500 }}>
                🎉 Campaign is live!
              </div>
            )}
          </div>
        ))}

        {/* Live token stream */}
        {currentAgent && liveTokens[currentAgent] && (
          <div style={styles.liveTokens}>
            <div style={styles.liveIndicator}>
              <span className="pulse-dot" />
              {AGENT_LABELS[currentAgent]} thinking...
            </div>
            <div style={styles.tokenText}>
              {liveTokens[currentAgent].slice(-300)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Asset Cards ─────────────────────────────────────────────
function AssetCard({ asset }: { asset: AssetReadyEvent }) {
  const color = AGENT_COLORS[asset.agent] || "#6b7280";
  const payload = asset.payload as any;

  return (
    <div className="asset-card-enter" style={{ ...styles.assetCard, borderColor: color + "40" }}>
      <div style={{ ...styles.assetHeader, color }}>
        <span style={styles.assetType}>{asset.asset_type.replace("_", " ")}</span>
        <span style={styles.assetLabel}>{asset.label}</span>
      </div>

      {asset.url && (
        <img
          src={asset.url}
          alt={asset.label}
          style={styles.assetImage}
        />
      )}

      {asset.asset_type === "kv_concept" && payload && (
        <KVConceptCard concept={payload as KVConcept} />
      )}

      {asset.asset_type === "machine_brief" && payload && (
        <BriefCard brief={payload} />
      )}

      {asset.asset_type === "copy" && payload && (
        <CopyCard copy={payload} />
      )}

      {!asset.url &&
        asset.asset_type !== "kv_concept" &&
        asset.asset_type !== "machine_brief" &&
        asset.asset_type !== "copy" && (
          <pre style={styles.jsonPre}>
            {JSON.stringify(payload, null, 2).slice(0, 800)}
            {JSON.stringify(payload, null, 2).length > 800 ? "\n..." : ""}
          </pre>
        )}
    </div>
  );
}

function BriefCard({ brief }: { brief: any }) {
  const ft = brief.fan_truth || {};
  return (
    <div>
      <div style={styles.briefRow}>
        <span style={styles.briefLabel}>Status</span>
        <span
          style={{
            ...styles.statusBadge,
            background: brief.validation_status === "approved" ? "#d1fae5" : "#fef3c7",
            color: brief.validation_status === "approved" ? "#065f46" : "#92400e",
          }}
        >
          {brief.validation_status}
        </span>
      </div>
      {ft.statement && (
        <div style={styles.briefRow}>
          <span style={styles.briefLabel}>Fan Truth</span>
          <span style={styles.briefValue}>{ft.statement}</span>
        </div>
      )}
      {ft.total !== undefined && (
        <div style={styles.briefRow}>
          <span style={styles.briefLabel}>FT Score</span>
          <span style={{ ...styles.briefValue, fontWeight: 600 }}>
            {ft.total}/30 {ft.passed ? "✓ Passed" : "✗ Below threshold"}
          </span>
        </div>
      )}
      {brief.revision_notes && (
        <div style={styles.revisionNote}>{brief.revision_notes}</div>
      )}
    </div>
  );
}

function KVConceptCard({ concept }: { concept: KVConcept }) {
  const palette = concept.visual_direction?.colour_palette;
  return (
    <div>
      <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 14 }}>
        Concept {concept.concept_id}: {concept.concept_name}
      </div>
      <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 8 }}>
        {concept.logline}
      </div>
      {palette && (
        <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
          {Object.values(palette)
            .filter((v) => typeof v === "string" && v.startsWith("#"))
            .map((color, i) => (
              <div
                key={i}
                title={color as string}
                style={{
                  width: 24, height: 24, borderRadius: 6,
                  background: color as string,
                  border: "1px solid rgba(0,0,0,0.1)",
                }}
              />
            ))}
        </div>
      )}
      <div style={{ fontSize: 11, color: "#6b7280" }}>
        {concept.visual_direction?.photography_style}
      </div>
      {concept.reel_script_10s?.music_cue && (
        <div style={styles.musicCue}>
          🎵 {concept.reel_script_10s.music_cue}
        </div>
      )}
    </div>
  );
}

function CopyCard({ copy }: { copy: any }) {
  const entries = Object.entries(copy).filter(
    ([k]) => !["campaign_id", "generated_at"].includes(k)
  );
  return (
    <div>
      {entries.slice(0, 4).map(([key, val]) => (
        <div key={key} style={styles.copyRow}>
          <div style={styles.copyKey}>{key.replace(/_/g, " ")}</div>
          <div style={styles.copyVal}>
            {typeof val === "string" ? val : JSON.stringify(val)}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Human Gate Modal ────────────────────────────────────────
function GateModal({
  gate,
  onDecide,
}: {
  gate: HumanGateEvent;
  onDecide: (decision: string, notes?: string, idx?: number) => void;
}) {
  const [notes, setNotes] = useState("");
  const [selectedKV, setSelectedKV] = useState<string | null>(null);
  const data = gate.data as any;
  const isKVSelect = gate.gate === "select_kv";
  const concepts: KVConcept[] = isKVSelect ? data.concepts || [] : [];

  return (
    <div style={styles.modalOverlay}>
      <div className="modal-enter" style={styles.modal}>
        <div style={styles.modalHeader}>
          <div style={styles.modalIcon}>👤</div>
          <div>
            <div style={styles.modalTitle}>{data.title || "Review required"}</div>
            <div style={styles.modalSub}>Human approval gate</div>
          </div>
        </div>

        {data.warning && (
          <div style={styles.modalWarning}>{data.warning}</div>
        )}

        {/* KV Concept selection */}
        {isKVSelect && concepts.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={styles.modalSectionLabel}>Select a concept:</div>
            <div style={{ display: "flex", gap: 10 }}>
              {concepts.map((c: KVConcept) => (
                <div
                  key={c.concept_id}
                  onClick={() => setSelectedKV(c.concept_id)}
                  className="kv-option"
                  style={{
                    borderColor:
                      selectedKV === c.concept_id ? "#3b82f6" : "#e5e7eb",
                    background:
                      selectedKV === c.concept_id ? "#eff6ff" : "#fff",
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: 13 }}>
                    {c.concept_id}: {c.concept_name}
                  </div>
                  <div style={{ fontSize: 11, color: "#6b7280", marginTop: 4 }}>
                    {c.logline}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Fan truth score for brief gate */}
        {gate.gate === "approve_brief" && data.fan_truth_score && (
          <div style={styles.scoreBox}>
            Fan Truth Score: <strong>{data.fan_truth_score}/30</strong>
            {data.validation_status && (
              <span
                style={{
                  ...styles.statusBadge,
                  marginLeft: 8,
                  background: data.validation_status === "approved" ? "#d1fae5" : "#fef3c7",
                  color: data.validation_status === "approved" ? "#065f46" : "#92400e",
                }}
              >
                {data.validation_status}
              </span>
            )}
          </div>
        )}

        <textarea
          placeholder="Notes or revision instructions (optional)..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          style={styles.notesInput}
        />

        <div style={styles.gateButtons}>
          {gate.options.map((opt) => {
            const isApprove = opt === "approve" || opt.startsWith("select_");
            const isReject = opt === "reject";
            const label = isKVSelect && opt.startsWith("select_")
              ? `Select ${opt.replace("select_", "").toUpperCase()}`
              : opt.charAt(0).toUpperCase() + opt.slice(1);

            return (
              <button
                key={opt}
                onClick={() =>
                  onDecide(
                    isKVSelect && selectedKV ? `select_${selectedKV.toLowerCase()}` : opt,
                    notes
                  )
                }
                disabled={isKVSelect && opt.startsWith("select_") && !selectedKV}
                className="gate-btn"
                style={{
                  background: isApprove ? "#10b981" : isReject ? "#ef4444" : "#6b7280",
                }}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Agent Pipeline Progress Bar ─────────────────────────────
const AGENT_PIPELINE: AgentName[] = [
  "briefing_agent",
  "strategy_agent",
  "kv_agent",
  "content_agent",
  "execution_agent",
  "performance_agent",
];

function AgentPipelineBar({
  currentAgent,
  status,
}: {
  currentAgent: string | null;
  status: string;
}) {
  const currentIdx = currentAgent
    ? AGENT_PIPELINE.indexOf(currentAgent as AgentName)
    : -1;

  return (
    <div className="pipeline-bar">
      {AGENT_PIPELINE.map((agent, i) => {
        const isDone = status === "done" || (currentIdx !== -1 && i < currentIdx);
        const isActive = agent === currentAgent;
        const color = AGENT_COLORS[agent];
        const connectorFilled = status === "done" || (currentIdx !== -1 && i < currentIdx);

        return (
          <div key={agent} className="pipeline-step">
            <div
              className={`pipeline-dot${isActive ? " is-active" : ""}`}
              title={AGENT_LABELS[agent]}
              style={{
                background: isDone || isActive ? color : "transparent",
                borderColor: isDone || isActive ? color : "#334155",
                color,
              }}
            />
            {i < AGENT_PIPELINE.length - 1 && (
              <div
                className="pipeline-connector"
                style={{ background: connectorFilled ? color : "#334155" }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────
export default function App() {
  const { state, startCampaign, approve, reset } = usePipeline();

  if (state.status === "idle") {
    return <BriefForm onStart={startCampaign} />;
  }

  return (
    <div style={styles.app}>
      {/* Top bar */}
      <div style={styles.topBar}>
        <div style={styles.topBarLeft}>
          <span style={styles.logo}>🍔</span>
          <span style={styles.topBarTitle}>CampaignOS</span>
          {state.campaign_id && (
            <span style={styles.campaignId}>#{state.campaign_id}</span>
          )}
        </div>
        <AgentPipelineBar
          currentAgent={state.current_agent}
          status={state.status}
        />
        <div style={styles.topBarRight}>
          <div
            style={{
              ...styles.statusPill,
              background:
                state.status === "done" ? "#d1fae5" :
                state.status === "error" ? "#fee2e2" :
                state.status === "waiting_for_approval" ? "#fef3c7" :
                "#dbeafe",
              color:
                state.status === "done" ? "#065f46" :
                state.status === "error" ? "#991b1b" :
                state.status === "waiting_for_approval" ? "#92400e" :
                "#1e40af",
            }}
          >
            {state.status === "running" && "⚡ Running"}
            {state.status === "waiting_for_approval" && "⏸ Awaiting approval"}
            {state.status === "done" && "✓ Live"}
            {state.status === "error" && "✗ Error"}
          </div>
          <button onClick={reset} className="reset-btn">
            New Campaign
          </button>
        </div>
      </div>

      {/* Main content */}
      <div style={styles.content}>
        {/* Left: Activity sidebar */}
        <ActivitySidebar
          events={state.events}
          liveTokens={state.live_tokens}
          currentAgent={state.current_agent}
        />

        {/* Centre: Assets feed */}
        <div style={styles.assetsFeed}>
          <div style={styles.assetsFeedHeader}>
            Assets ({state.assets.length})
          </div>
          {state.assets.length === 0 && state.status === "running" && (
            <div style={styles.waitingMsg}>
              <div className="spinner" />
              Waiting for first asset...
            </div>
          )}
          <div style={styles.assetsGrid}>
            {state.assets.map((asset, i) => (
              <AssetCard key={i} asset={asset} />
            ))}
          </div>
          {state.error && (
            <div style={styles.errorBox}>{state.error}</div>
          )}
        </div>
      </div>

      {/* Human gate modal */}
      {state.pending_gate && (
        <GateModal gate={state.pending_gate} onDecide={approve} />
      )}
    </div>
  );
}

// ── Styles ──────────────────────────────────────────────────
const styles: Record<string, React.CSSProperties> = {
  formHeader: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginBottom: 24,
  },
  logo: { fontSize: 32 },
  formTitle: { fontSize: 22, fontWeight: 700, margin: 0 },
  formSub: { fontSize: 13, color: "#6b7280", margin: 0 },
  label: {
    display: "block",
    fontSize: 12,
    fontWeight: 600,
    color: "#374151",
    marginBottom: 4,
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  app: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    background: "#0f172a",
    color: "#e2e8f0",
  },
  topBar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "12px 20px",
    background: "#1e293b",
    borderBottom: "1px solid #334155",
    flexShrink: 0,
  },
  topBarLeft: { display: "flex", alignItems: "center", gap: 10 },
  topBarTitle: { fontSize: 16, fontWeight: 700 },
  campaignId: {
    fontSize: 12,
    color: "#64748b",
    background: "#0f172a",
    padding: "2px 8px",
    borderRadius: 100,
  },
  topBarRight: { display: "flex", alignItems: "center", gap: 10 },
  statusPill: {
    fontSize: 12,
    fontWeight: 500,
    padding: "4px 10px",
    borderRadius: 100,
  },
  content: {
    display: "flex",
    flex: 1,
    overflow: "hidden",
  },
  sidebar: {
    width: 280,
    borderRight: "1px solid #1e293b",
    display: "flex",
    flexDirection: "column",
    flexShrink: 0,
  },
  sidebarHeader: {
    padding: "12px 16px",
    fontSize: 11,
    fontWeight: 600,
    color: "#64748b",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    borderBottom: "1px solid #1e293b",
  },
  activityList: {
    flex: 1,
    overflowY: "auto",
    padding: 12,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  activityItem: {
    fontSize: 12,
  },
  agentDot: {
    display: "inline-block",
    width: 8,
    height: 8,
    borderRadius: "50%",
    marginRight: 6,
  },
  agentName: { fontWeight: 600, fontSize: 12 },
  activityDesc: { color: "#64748b", fontSize: 11, marginTop: 2, marginLeft: 14 },
  thoughtBubble: {
    fontSize: 11,
    color: "#94a3b8",
    background: "#1e293b",
    borderRadius: 6,
    padding: "4px 8px",
    borderLeft: "2px solid #334155",
    marginLeft: 14,
  },
  liveTokens: {
    background: "#1e293b",
    borderRadius: 8,
    padding: 10,
    marginTop: 8,
  },
  liveIndicator: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontSize: 10,
    color: "#64748b",
    marginBottom: 6,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  tokenText: {
    fontSize: 10,
    color: "#94a3b8",
    fontFamily: "monospace",
    lineHeight: 1.5,
    overflowWrap: "break-word",
  },
  assetsFeed: {
    flex: 1,
    overflowY: "auto",
    padding: 20,
  },
  assetsFeedHeader: {
    fontSize: 11,
    fontWeight: 600,
    color: "#64748b",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    marginBottom: 16,
  },
  assetsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
    gap: 16,
  },
  assetCard: {
    background: "#1e293b",
    borderRadius: 12,
    border: "1px solid",
    padding: 16,
  },
  assetHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  assetType: {
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    fontWeight: 700,
  },
  assetLabel: { fontSize: 12, color: "#94a3b8" },
  assetImage: {
    width: "100%",
    borderRadius: 8,
    marginBottom: 12,
  },
  jsonPre: {
    fontSize: 10,
    color: "#94a3b8",
    fontFamily: "monospace",
    overflowX: "auto",
    whiteSpace: "pre-wrap",
    wordBreak: "break-all",
    lineHeight: 1.5,
    margin: 0,
  },
  briefRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 8,
    gap: 8,
  },
  briefLabel: { fontSize: 10, color: "#64748b", flexShrink: 0, paddingTop: 2 },
  briefValue: { fontSize: 12, textAlign: "right" as const },
  statusBadge: {
    fontSize: 10,
    padding: "2px 8px",
    borderRadius: 100,
    fontWeight: 600,
  },
  revisionNote: {
    fontSize: 11,
    color: "#fbbf24",
    background: "#451a03",
    borderRadius: 6,
    padding: "6px 8px",
    marginTop: 8,
  },
  scoreBox: {
    background: "#0f172a",
    borderRadius: 8,
    padding: "8px 12px",
    fontSize: 13,
    marginBottom: 12,
  },
  musicCue: {
    fontSize: 11,
    color: "#a78bfa",
    marginTop: 8,
    background: "#1e1b4b",
    borderRadius: 6,
    padding: "4px 8px",
  },
  copyRow: { marginBottom: 8 },
  copyKey: {
    fontSize: 10,
    color: "#64748b",
    textTransform: "capitalize" as const,
    marginBottom: 2,
  },
  copyVal: { fontSize: 12, lineHeight: 1.5 },
  waitingMsg: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    color: "#64748b",
    fontSize: 13,
    padding: 20,
  },
  errorBox: {
    background: "#450a0a",
    border: "1px solid #991b1b",
    borderRadius: 8,
    padding: 12,
    color: "#fca5a5",
    fontSize: 13,
    marginTop: 16,
  },
  modalOverlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.7)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
    padding: 20,
  },
  modal: {
    background: "#1e293b",
    borderRadius: 16,
    border: "1px solid #334155",
    padding: 24,
    width: "100%",
    maxWidth: 600,
    maxHeight: "80vh",
    overflowY: "auto",
  },
  modalHeader: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginBottom: 16,
  },
  modalIcon: { fontSize: 24 },
  modalTitle: { fontSize: 16, fontWeight: 700 },
  modalSub: { fontSize: 12, color: "#64748b" },
  modalWarning: {
    background: "#450a0a",
    border: "1px solid #991b1b",
    borderRadius: 8,
    padding: "8px 12px",
    fontSize: 12,
    color: "#fca5a5",
    marginBottom: 16,
  },
  modalSectionLabel: {
    fontSize: 11,
    color: "#64748b",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    marginBottom: 8,
  },
  notesInput: {
    width: "100%",
    background: "#0f172a",
    border: "1px solid #334155",
    borderRadius: 8,
    padding: "8px 12px",
    color: "#e2e8f0",
    fontSize: 13,
    fontFamily: "inherit",
    resize: "vertical" as const,
    boxSizing: "border-box",
    marginBottom: 16,
  },
  gateButtons: {
    display: "flex",
    gap: 10,
  },
};
