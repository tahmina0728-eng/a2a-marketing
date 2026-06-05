import { useState, useMemo, useCallback, Component, type ReactNode, type ErrorInfo } from "react";

// ── Error boundary — shows error instead of blank page ────────
class ErrorBoundary extends Component<{ children: ReactNode }, { error: string | null }> {
  state = { error: null };
  static getDerivedStateFromError(e: Error) { return { error: e.message }; }
  componentDidCatch(e: Error, info: ErrorInfo) { console.error("CampaignOS render error:", e, info); }
  render() {
    if (this.state.error) return (
      <div style={{ padding: 48, fontFamily: "Inter,sans-serif", color: "#1a2332" }}>
        <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8, color: "#dc2626" }}>⚠ Render Error</div>
        <pre style={{ fontSize: 12, background: "#f8fafc", padding: 16, borderRadius: 8, overflowX: "auto" as const }}>{this.state.error}</pre>
        <button onClick={() => this.setState({ error: null })} style={{ marginTop: 16, padding: "8px 20px",
          borderRadius: 8, border: "none", background: "#0055A4", color: "white", cursor: "pointer" }}>
          Dismiss
        </button>
      </div>
    );
    return this.props.children;
  }
}
import "./App.css";
import { usePipeline } from "./hooks/usePipeline";
import type { HarnessBriefRequest, AgentEvent } from "./types/pipeline";

// ── Infosys Aster Logo ───────────────────────────────────────
// Matches the official Infosys Aster design:
//   "Infosys®" — light weight, cobalt blue #007DC3
//   "aster"    — bold, dark navy #1B3E6F
function AsterLogo({ size = 1 }: { size?: number }) {
  return (
    <svg width={140 * size} height={58 * size} viewBox="0 0 140 58"
      xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {/* Infosys® — light weight, cobalt blue */}
      <text x="2" y="20" fontFamily="'Inter','Helvetica Neue',Arial,sans-serif"
        fontWeight="300" fontSize="15" fill="#007DC3" letterSpacing="0.4">Infosys</text>
      <text x="77" y="16" fontFamily="'Inter','Helvetica Neue',Arial,sans-serif"
        fontWeight="300" fontSize="9" fill="#007DC3">®</text>
      {/* aster — bold, dark navy */}
      <text x="1" y="52" fontFamily="'Inter','Helvetica Neue',Arial,sans-serif"
        fontWeight="800" fontSize="34" fill="#1B3E6F" letterSpacing="-0.8">aster</text>
    </svg>
  );
}

// ── Powered by Infosys badge ─────────────────────────────────
function PoweredByInfosys({ dark = false }: { dark?: boolean }) {
  const textColor = dark ? "#ffffff" : "#64748b";
  const brandColor = dark ? "#7ab8e0" : "#007DC3";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 10,
      fontFamily: "'Inter','Helvetica Neue',sans-serif", color: textColor, letterSpacing: "0.04em" }}>
      <span style={{ fontWeight: 400 }}>Powered by</span>
      <span style={{ fontWeight: 700, color: brandColor, fontSize: 11 }}>Infosys</span>
      <span style={{ color: brandColor, fontSize: 8, fontWeight: 300, position: "relative" as const, top: -2 }}>®</span>
    </div>
  );
}

// ── Wizard constants ─────────────────────────────────────────

type GoalId = "launch" | "sales" | "community" | "reengagement" | "expansion" | "custom";

const GOALS = [
  { id: "launch"       as GoalId, icon: "🚀", label: "Launch Awareness",  desc: "Introduce a new product" },
  { id: "sales"        as GoalId, icon: "📈", label: "Drive Sales",        desc: "Increase transactions & ROAS" },
  { id: "community"    as GoalId, icon: "👥", label: "Build Community",    desc: "Grow brand advocates" },
  { id: "reengagement" as GoalId, icon: "🎯", label: "Re-engagement",      desc: "Win back lapsed customers" },
  { id: "expansion"    as GoalId, icon: "🌍", label: "Market Expansion",   desc: "Enter new territories" },
  { id: "custom"       as GoalId, icon: "✏️", label: "Custom",             desc: "Write your own goal" },
];

const BRANDS = [
  { id: "Rnorr",     label: "Rnorr",      emoji: "🥣" },
  { id: "Sunglow",   label: "Sunglow",    emoji: "✨" },
  { id: "Boozt",     label: "Boozt",      emoji: "💨" },
];

const BRAND_PRODUCTS: Record<string, string[]> = {
  Rnorr:     ["Chicken Stock Cubes", "Beef Stock Cubes", "Vegetable Stock Cubes",
              "Stock Pots", "Bouillon Powder", "Concentrated Liquid Stock",
              "Soup Range", "Gravy Granules", "Seasoning Sachets"],
  Sunglow:   ["Moisture Shampoo", "Moisture Conditioner", "Deep Repair Treatment",
              "Scalp Nourish Oil", "Define & Glow Serum", "Leave-In Conditioner",
              "Curl Refresh Spray", "Edge Control", "Protective Style Serum"],
  Boozt:     ["Root Lift Spray", "Volumising Mousse", "Thickening Shampoo",
              "Thickening Conditioner", "Texturising Powder", "Volume Setting Spray"],
};

const BRAND_CATEGORY: Record<string, string> = {
  Rnorr:     "Dry Cook-In Sauces",
  Sunglow:   "Hair Care",
  Boozt:     "Hair Styling & Volume",
};

const BRAND_FAN_TRUTHS: Record<string, string[]> = {
  Rnorr: [
    "That moment when a weeknight dinner smells like it took all day",
    "Real flavour shouldn't take real time",
    "The shortcut that feels like cheating — but isn't",
    "Home cooking is how you say 'I care' without saying it",
    "A stock cube is the secret ingredient every great cook pretends isn't there",
  ],
  Sunglow: [
    "The first look in the mirror after wash day — that's your glow",
    "Your crown is not a problem to manage, it's a conversation to have",
    "Good hair day isn't luck — it's science built for you from the start",
    "Hair that glows because it's healthy, not because it's hidden",
    "When your hair does exactly what it wants to — and you let it",
  ],
  Boozt: [
    "Flat hair is a choice. So is not having it.",
    "Volume isn't vanity — it's the energy you walk in with",
    "The five seconds that change your whole morning",
    "Your roots called. They want their lift back.",
    "When your hair has more energy than you do",
  ],
};

const AGE_GROUPS  = ["13–17", "18–24", "25–34", "35–44", "45–54", "55+"];
const INTERESTS: Record<string, string[]> = {
  Rnorr:     ["Home cooks", "Families", "Students", "Budget shoppers", "Food lovers", "Meal preppers", "Time-poor professionals"],
  Sunglow:   ["Natural hair community", "Protective styles", "Wash day routines", "Scalp health", "Curl definition", "Black hair care", "Beauty enthusiasts"],
  Boozt:     ["Fine hair", "Volume seekers", "On-the-go styling", "Beauty enthusiasts", "Festival-goers", "Bridal & occasion"],
  default:   ["Families", "Students", "Young professionals", "Beauty lovers", "Lifestyle"],
};
const REGIONS     = ["United Kingdom", "Australia", "United States", "New Zealand", "SEA", "Global"];
const SEASONS     = ["Spring", "Summer", "Autumn", "Winter", "All Year"];
const MOMENT_TYPES = ["Day-to-Day", "Brand Moment", "Partnership Moment"];

const CHANNELS_LIST = [
  { id: "Instagram",  icon: "📸", label: "Instagram" },
  { id: "TikTok",     icon: "🎵", label: "TikTok" },
  { id: "YouTube",    icon: "▶️", label: "YouTube" },
  { id: "OOH",        icon: "🏙️", label: "OOH" },
  { id: "Google Ads", icon: "🎯", label: "Google Ads" },
  { id: "Meta Ads",   icon: "📘", label: "Meta Ads" },
];

const KPI_OPTIONS = [
  { id: "reach",       label: "5M Reach" },
  { id: "ctr",         label: "2.5% CTR" },
  { id: "roas",        label: "3x ROAS" },
  { id: "conversions", label: "+10% Conv." },
  { id: "engagement",  label: "4% Engagement" },
  { id: "views",       label: "10M Views" },
];

const BUDGETS = [
  { value: "£50,000",   label: "£50K",  desc: "Pilot" },
  { value: "£100,000",  label: "£100K", desc: "Regional" },
  { value: "£250,000",  label: "£250K", desc: "Multi-channel" },
  { value: "£500,000",  label: "£500K", desc: "Full campaign" },
  { value: "£1,000,000",label: "£1M",   desc: "Flagship" },
  { value: "custom",    label: "Custom", desc: "Enter amount" },
];

interface WizardData {
  campaignName: string;
  brand: string;
  goal: GoalId | "";
  goalCustom: string;
  product: string;
  productCustom: string;
  fanTruth: string;
  fanTruthCustom: string;
  audienceAge: string[];
  audienceInterests: string[];
  audienceRegions: string[];
  season: string;
  momentType: string;
  channels: string[];
  kpis: string[];
  budget: string;
  budgetCustom: string;
}

// ── Harness pipeline agents (for loading display) ────────────
// Order matches actual backend execution
const HARNESS_STAGES = [
  { key: "briefing", icon: "📋", label: "Briefing Agent",    desc: "Validating brief & Fan Truth score" },
  { key: "strategy", icon: "💡", label: "Creative Director", desc: "Building big idea & strategy" },
  { key: "copy",     icon: "✍️", label: "Copy Agent",        desc: "Writing campaign copy variants" },
  { key: "culture",  icon: "🌍", label: "Culture Analyst",   desc: "Researching cultural intelligence" },
  { key: "kv",       icon: "🎨", label: "KV Generator",      desc: "Generating key visual with Imagen 4" },
  { key: "channel",  icon: "📡", label: "Channel Adapter",   desc: "Publishing to Instagram, TikTok & more" },
];

// ── Brief Form (6-step wizard) ───────────────────────────────
function BriefForm({ onStart, onFullCampaign }: {
  onStart: (brief: HarnessBriefRequest) => void;
  onFullCampaign: (brief: HarnessBriefRequest) => void;
}) {
  const [step, setStep] = useState(0);
  const [d, setD] = useState<WizardData>({
    campaignName: "",
    brand: "Rnorr",
    goal: "", goalCustom: "",
    product: "", productCustom: "",
    fanTruth: "", fanTruthCustom: "",
    audienceAge: [], audienceInterests: [], audienceRegions: [],
    season: "Summer", momentType: "Day-to-Day",
    channels: ["Instagram", "TikTok"],
    kpis: ["reach", "ctr", "roas"],
    budget: "£500,000", budgetCustom: "",
  });

  const TOTAL_STEPS = 7;

  function toggle<T>(arr: T[], val: T): T[] {
    return arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val];
  }

  function canProceed(): boolean {
    switch (step) {
      case 0: return !!d.brand;
      case 1: return !!d.goal && (d.goal !== "custom" || !!d.goalCustom.trim());
      case 2: return !!d.product || !!d.productCustom.trim();
      case 3: return !!d.fanTruth || !!d.fanTruthCustom.trim();
      case 4: return true;
      case 5: return d.channels.length > 0 && d.kpis.length > 0;
      case 6: return d.budget !== "" || !!d.budgetCustom.trim();
      case 7: return d.campaignName.trim().length >= 3;
      default: return true;
    }
  }

  function handleLaunch() {
    const goal       = d.goal === "custom" ? d.goalCustom : GOALS.find((g) => g.id === d.goal)?.label ?? "";
    const product    = d.product === "custom" ? d.productCustom : d.product;
    const fanTruth   = d.fanTruth === "custom" ? d.fanTruthCustom : d.fanTruth;
    const kpisStr    = d.kpis.map((k) => KPI_OPTIONS.find((o) => o.id === k)?.label ?? k).join(", ");
    const budget     = d.budget === "custom" ? `£${d.budgetCustom}` : d.budget;
    const ageRange   = d.audienceAge.length > 0 ? d.audienceAge[0].replace("–", "-") : "All ages";
    const market     = d.audienceRegions[0] ?? "UK";
    const category   = BRAND_CATEGORY[d.brand] ?? "Food & Beverage";

    const brief: HarnessBriefRequest = {
      campaign_name:    d.campaignName.trim(),
      brand:            d.brand,
      goal,
      budget,
      kpis:             kpisStr,
      product,
      product_category: category,
      fan_truth:        fanTruth,
      channels:         d.channels,
      market,
      season:           d.season,
      moment_type:      d.momentType,
      audience: {
        segment:  d.audienceInterests.join(", ") || "General audience",
        location: market,
        age_range: ageRange,
        gender:   "All genders",
        interests: d.audienceInterests.join(", ") || undefined,
      },
      tone: "Warm & friendly",
    };

    onStart(brief);
  }

  function handleFullLaunch() {
    const goal       = d.goal === "custom" ? d.goalCustom : GOALS.find((g) => g.id === d.goal)?.label ?? "";
    const product    = d.product === "custom" ? d.productCustom : d.product;
    const fanTruth   = d.fanTruth === "custom" ? d.fanTruthCustom : d.fanTruth;
    const kpisStr    = d.kpis.map((k) => KPI_OPTIONS.find((o) => o.id === k)?.label ?? k).join(", ");
    const budget     = d.budget === "custom" ? `£${d.budgetCustom}` : d.budget;
    const ageRange   = d.audienceAge.length > 0 ? d.audienceAge[0].replace("–", "-") : "All ages";
    const market     = d.audienceRegions[0] ?? "UK";
    const category   = BRAND_CATEGORY[d.brand] ?? "Food & Beverage";

    const brief: HarnessBriefRequest = {
      campaign_name:    d.campaignName.trim(),
      brand:            d.brand,
      goal, budget, kpis: kpisStr, product,
      product_category: category,
      fan_truth:        fanTruth,
      channels:         d.channels,
      market, season: d.season, moment_type: d.momentType,
      audience: {
        segment:  d.audienceInterests.join(", ") || "General audience",
        location: market, age_range: ageRange, gender: "All genders",
        interests: d.audienceInterests.join(", ") || undefined,
      },
      tone: "Warm & friendly",
    };
    onFullCampaign(brief);
  }

  const stepContent = () => {
    switch (step) {
      case 0:
        return (
          <>
            <div className="wizard-step-label">Step 1 of 7</div>
            <h2 className="wizard-heading">Select your <span className="gradient-text">brand</span></h2>
            <p className="wizard-subheading">Which brand is this campaign for?</p>
            <div className="goal-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
              {BRANDS.map((b) => (
                <div key={b.id} className={`goal-tile${d.brand === b.id ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, brand: b.id, product: "", productCustom: "" }))}>
                  <span className="goal-tile-icon">{b.emoji}</span>
                  <div className="goal-tile-label">{b.label}</div>
                </div>
              ))}
            </div>
          </>
        );

      case 1:
        return (
          <>
            <div className="wizard-step-label">Step 2 of 7</div>
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

      case 2:
        return (
          <>
            <div className="wizard-step-label">Step 3 of 7</div>
            <h2 className="wizard-heading">What are we <span className="gradient-text">promoting?</span></h2>
            <p className="wizard-subheading">Select a product or enter your own</p>
            <div className="chip-group">
              {(BRAND_PRODUCTS[d.brand] ?? []).map((p: string) => (
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

      case 3:
        return (
          <>
            <div className="wizard-step-label">Step 4 of 7</div>
            <h2 className="wizard-heading">What <span className="gradient-text">fan truth</span> drives this?</h2>
            <p className="wizard-subheading">Pick a {d.brand} fan truth or write your own</p>
            <div className="truth-stack">
              {(BRAND_FAN_TRUTHS[d.brand] ?? []).map((ft) => (
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

      case 4:
        return (
          <>
            <div className="wizard-step-label">Step 5 of 7</div>
            <h2 className="wizard-heading">Who are you <span className="gradient-text">targeting?</span></h2>
            <p className="wizard-subheading">Select all that apply</p>
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
              {(INTERESTS[d.brand as keyof typeof INTERESTS] ?? INTERESTS.default).map((i: string) => (
                <button key={i} className={`chip${d.audienceInterests.includes(i) ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, audienceInterests: toggle(p.audienceInterests, i) }))}>
                  {i}
                </button>
              ))}
            </div>
            <div className="section-label">Market / Region</div>
            <div className="chip-group">
              {REGIONS.map((r) => (
                <button key={r} className={`chip${d.audienceRegions.includes(r) ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, audienceRegions: toggle(p.audienceRegions, r) }))}>
                  {r}
                </button>
              ))}
            </div>
            <div className="section-label">Season</div>
            <div className="chip-group">
              {SEASONS.map((s) => (
                <button key={s} className={`chip${d.season === s ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, season: s }))}>
                  {s}
                </button>
              ))}
            </div>
          </>
        );

      case 5:
        return (
          <>
            <div className="wizard-step-label">Step 6 of 7</div>
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
            <div className="section-label">Campaign moment</div>
            <div className="chip-group">
              {MOMENT_TYPES.map((m) => (
                <button key={m} className={`chip${d.momentType === m ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, momentType: m }))}>
                  {m}
                </button>
              ))}
            </div>
          </>
        );

      case 6:
        return (
          <>
            <div className="wizard-step-label">Step 7 of 7</div>
            <h2 className="wizard-heading">What's your <span className="gradient-text">budget?</span></h2>
            <p className="wizard-subheading">Total campaign spend</p>
            <div className="budget-grid">
              {BUDGETS.map((b) => (
                <div key={b.value} className={`budget-card${d.budget === b.value ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, budget: b.value }))}>
                  <div className="budget-amount">{b.label}</div>
                  <div className="budget-desc">{b.desc}</div>
                </div>
              ))}
            </div>
            {d.budget === "custom" && (
              <input className="dark-input" placeholder="Enter budget (e.g. £750,000)"
                value={d.budgetCustom}
                onChange={(e) => setD((p) => ({ ...p, budgetCustom: e.target.value }))} />
            )}
          </>
        );

      case 7: {
        const reviewGoal    = d.goal === "custom" ? d.goalCustom : GOALS.find((g) => g.id === d.goal)?.label ?? "";
        const reviewProduct = d.product === "custom" ? d.productCustom : d.product;
        const reviewTruth   = d.fanTruth === "custom" ? d.fanTruthCustom : d.fanTruth;
        const reviewAud     = [...d.audienceAge, ...d.audienceInterests, ...d.audienceRegions];
        const reviewKpis    = d.kpis.map((k) => KPI_OPTIONS.find((o) => o.id === k)?.label ?? k);
        const reviewBudget  = d.budget === "custom" ? `£${d.budgetCustom}` : d.budget;
        return (
          <>
            <div className="wizard-step-label">Review</div>
            <h2 className="wizard-heading">Ready to <span className="gradient-text">launch?</span></h2>
            <p className="wizard-subheading">Name your campaign then send it to the agents</p>
            <input className="dark-input" placeholder="Campaign name (e.g. Summer Awareness 2026)"
              value={d.campaignName}
              onChange={(e) => setD((p) => ({ ...p, campaignName: e.target.value }))}
              style={{ marginBottom: 4, fontSize: 16 }} />
            {d.campaignName.trim().length < 3 && (
              <p style={{ fontSize: 12, color: "#f59e0b", marginBottom: 16, marginTop: 0 }}>
                ⚠ Campaign name must be at least 3 characters
              </p>
            )}
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
                <div className="review-item-value">{d.channels.join(", ")}</div>
              </div>
              <div className="review-item">
                <div className="review-item-label">KPIs</div>
                <div className="review-item-value">{reviewKpis.join(", ")}</div>
              </div>
              <div className="review-item">
                <div className="review-item-label">Season</div>
                <div className="review-item-value">{d.season} · {d.momentType}</div>
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
      {/* Infosys Aster Header */}
      <div className="aster-header">
        <AsterLogo />
        <div style={{ display: "flex", flexDirection: "column" as const, gap: 2 }}>
          <span className="aster-tagline">The AI-Amplified Marketing Suite</span>
          <PoweredByInfosys />
        </div>
      </div>
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
            : <div style={{ display: "flex", gap: 10, flexDirection: "column" as const, alignItems: "flex-end" }}>
                <button className="wizard-launch-btn" disabled={!canProceed()} onClick={handleLaunch}>
                  ⚡ Validate Brief
                </button>
                <button
                  disabled={!canProceed()}
                  onClick={handleFullLaunch}
                  style={{ padding: "10px 24px", borderRadius: 8, border: "2px solid #0055A4",
                    background: "transparent", color: "#0055A4", fontSize: 13, fontWeight: 700,
                    cursor: canProceed() ? "pointer" : "not-allowed", fontFamily: "inherit",
                    opacity: canProceed() ? 1 : 0.35 }}>
                  🎬 Full Campaign (Images + 6 Channels)
                </button>
              </div>}
        </div>
      </div>
    </div>
  );
}

// ── Agent visual themes ───────────────────────────────────────
const AGENT_VISUALS: Record<string, { g1: string; g2: string; blob1: string; blob2: string; title: string }> = {
  briefing: { g1: "#7c3aed", g2: "#4f46e5", blob1: "#a78bfa", blob2: "#818cf8", title: "Validating Brief" },
  culture:  { g1: "#0d9488", g2: "#0891b2", blob1: "#2dd4bf", blob2: "#22d3ee", title: "Cultural Research" },
  strategy: { g1: "#d97706", g2: "#ea580c", blob1: "#fbbf24", blob2: "#fb923c", title: "Creative Strategy" },
  copy:     { g1: "#0055A4", g2: "#0369a1", blob1: "#3b82f6", blob2: "#06b6d4", title: "Writing Copy" },
  kv:       { g1: "#be123c", g2: "#c2410c", blob1: "#fb7185", blob2: "#fb923c", title: "Key Visual" },
  channel:  { g1: "#4338ca", g2: "#0e7490", blob1: "#818cf8", blob2: "#22d3ee", title: "Channel Adaptation" },
};
const DEFAULT_VISUAL = { g1: "#1e293b", g2: "#334155", blob1: "#475569", blob2: "#64748b", title: "Starting…" };

// ── Agent content panels ──────────────────────────────────────
const DATA_SOURCES = [
  { id: "brand",    icon: "📚", label: "Brand Guidelines", from: "GCS Bucket",           delay: 0   },
  { id: "fantruth", icon: "💡", label: "Fan Truth Library", from: "Vertex AI Search",    delay: 800 },
  { id: "history",  icon: "📈", label: "Historical Campaigns", from: "BigQuery",         delay: 1600 },
  { id: "cdp",      icon: "👥", label: "CDP / Sephora",    from: "Kaggle · BigQuery",    delay: 2400 },
];

function BriefingPanel({ m, liveMsg }: { m?: Record<string,unknown>; liveMsg: string|null }) {
  const ft      = (m?.fan_truth ?? {}) as any;
  const aud     = (m?.audience  ?? {}) as any;
  const kpis    = (m?.kpis      ?? []) as any[];
  const hasData = !!ft?.overall;

  const score      = hasData ? (ft.overall ?? 0) : 0;
  const verdict    = hasData ? (ft.verdict ?? "—") : "—";
  const scoreColor = score >= 70 ? "#10b981" : score >= 55 ? "#f59e0b" : "#ef4444";
  const r = 28, circ = 2 * Math.PI * r, dash = circ * Math.min(score, 100) / 100;

  return (
    <div style={{ width: "100%" }}>

      {/* ── Data sources (always visible, loading → ✓) ── */}
      <div style={{ fontSize: 10, fontWeight: 700, color: "#7c3aed", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 8 }}>
        {hasData ? "Data Sources ✓" : "Querying Data Sources"}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 12 }}>
        {DATA_SOURCES.map((src, idx) => (
          <div key={src.id} className="source-card" style={{ animationDelay: `${src.delay}ms`, padding: "8px 10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 30, height: 30, borderRadius: 8, flexShrink: 0,
                background: hasData ? "#f0fdf4" : "#f3f0ff",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>{src.icon}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#1a2332", whiteSpace: "nowrap" as const,
                  overflow: "hidden", textOverflow: "ellipsis" }}>{src.label}</div>
                <div style={{ fontSize: 9, color: "#94a3b8" }}>← {src.from}</div>
              </div>
              {hasData
                ? <span style={{ fontSize: 11, color: "#10b981", fontWeight: 800, flexShrink: 0 }}>✓</span>
                : <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
                    {[0,1,2].map(d => <span key={d} className="source-dot"
                      style={{ animationDelay: `${idx * 0.15 + d * 0.2}s` }} />)}
                  </div>}
            </div>
          </div>
        ))}
      </div>

      {/* ── Live message while loading ── */}
      {!hasData && liveMsg && (
        <div style={{ fontSize: 11, color: "#7c3aed", fontStyle: "italic", marginBottom: 8 }}>{liveMsg}</div>
      )}

      {/* ── Fan Truth gauge + KPIs + CDP — fade in when milestone arrives ── */}
      {hasData && (
        <div className="msg-fade">
          {/* Fan Truth */}
          <div style={{ borderRadius: 14, overflow: "hidden", marginBottom: 10,
            border: `1.5px solid ${scoreColor}30` }}>
            <div style={{ background: `linear-gradient(135deg, ${scoreColor}14, ${scoreColor}05)`,
              padding: "12px 14px", display: "flex", alignItems: "center", gap: 12 }}>
              <svg width="68" height="68" viewBox="0 0 68 68" style={{ flexShrink: 0 }}>
                <circle cx="34" cy="34" r={r} fill="none" stroke="#e2e8f0" strokeWidth="6"/>
                <circle cx="34" cy="34" r={r} fill="none" stroke={scoreColor} strokeWidth="6"
                  strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" transform="rotate(-90 34 34)"
                  style={{ transition: "stroke-dasharray 1.4s ease" }}/>
                <text x="34" y="31" textAnchor="middle" fill={scoreColor} fontSize="15" fontWeight="900">{score}</text>
                <text x="34" y="44" textAnchor="middle" fill="#94a3b8" fontSize="9">/100</text>
              </svg>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 22, fontWeight: 900, color: scoreColor }}>{score}/100</span>
                  <span style={{ fontSize: 10, fontWeight: 800, padding: "2px 10px", borderRadius: 20,
                    background: verdict === "PASS" ? "#dcfce7" : "#fee2e2",
                    color: verdict === "PASS" ? "#065f46" : "#991b1b",
                    border: `1px solid ${verdict === "PASS" ? "#86efac" : "#fca5a5"}` }}>{verdict}</span>
                </div>
                <div style={{ fontSize: 9, color: "#64748b", fontWeight: 700, letterSpacing: "0.08em",
                  textTransform: "uppercase" as const, marginBottom: 3 }}>Fan Truth Score</div>
                {ft.statement && (
                  <div style={{ fontSize: 11, color: "#475569", fontStyle: "italic", lineHeight: 1.4 }}>
                    "{String(ft.statement).slice(0, 80)}{String(ft.statement).length > 80 ? "…" : ""}"
                  </div>
                )}
              </div>
            </div>
            {/* KPI strip */}
            {kpis.length > 0 && (
              <div style={{ display: "flex", borderTop: `1px solid ${scoreColor}18` }}>
                {kpis.slice(0, 3).map((k: any, i: number) => {
                  const fc = k.flag === "OK" ? "#10b981" : k.flag === "AMBITIOUS" ? "#f59e0b" : "#ef4444";
                  return (
                    <div key={i} style={{ flex: 1, padding: "7px 8px",
                      borderRight: i < 2 ? `1px solid ${scoreColor}15` : "none",
                      textAlign: "center" as const, background: `${fc}08` }}>
                      <div style={{ fontSize: 9, color: "#64748b", fontWeight: 600 }}>{k.metric}</div>
                      <div style={{ fontSize: 9, fontWeight: 800, color: fc, marginTop: 1 }}>{k.flag}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* CDP audience */}
          {(aud.count || aud.income) && (
            <div style={{ padding: "9px 12px", borderRadius: 12, background: "#eff6ff", border: "1px solid #bfdbfe" }}>
              <div style={{ fontSize: 9, fontWeight: 700, color: "#0055A4", letterSpacing: "0.09em",
                textTransform: "uppercase" as const, marginBottom: 7 }}>
                Audience Intelligence · Kaggle CDP / Sephora
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" as const, alignItems: "center" }}>
                {aud.count && (
                  <div style={{ textAlign: "center" as const }}>
                    <div style={{ fontSize: 20, fontWeight: 900, color: "#0055A4", lineHeight: 1 }}>
                      {String(aud.count).replace(/\D.*/, "")}
                    </div>
                    <div style={{ fontSize: 9, color: "#64748b" }}>profiles matched</div>
                  </div>
                )}
                <div style={{ flex: 1 }}>
                  {aud.income && (
                    <div style={{ fontSize: 11, fontWeight: 600, color: "#1e40af", marginBottom: 2 }}>
                      💰 {aud.income}
                    </div>
                  )}
                  {aud.channels && (
                    <div style={{ fontSize: 11, color: "#3b82f6" }}>📡 {aud.channels}</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StrategyPanel({ m }: { m?: Record<string,unknown> }) {
  const hero     = String(m?.hero_message ?? "");
  const big      = String(m?.big_idea ?? "");
  const tagline  = String(m?.tagline ?? "");
  const fw       = String(m?.strategic_framework ?? "");
  const pillars  = (m?.messaging_pillars ?? []) as string[];
  const imgB64   = m?.hero_image_b64 ? String(m.hero_image_b64) : "";
  if (!hero) return null;

  return (
    <div style={{ width: "100%", borderRadius: 18, overflow: "hidden", border: "1px solid #fde68a",
      boxShadow: "0 8px 32px rgba(217,119,6,0.15)" }}>
      {/* Hero visual — brand image OR gradient */}
      <div style={{ position: "relative" as const, minHeight: 160, overflow: "hidden" }}>
        {imgB64 ? (
          <img src={`data:image/jpeg;base64,${imgB64}`} alt="brand asset"
            style={{ width: "100%", height: 180, objectFit: "cover", display: "block" }} />
        ) : (
          <div style={{ height: 160, background: "linear-gradient(135deg, #d97706 0%, #ea580c 100%)", position: "relative" as const }}>
            <div style={{ position: "absolute" as const, top: -40, right: -40, width: 160, height: 160,
              borderRadius: "50%", background: "rgba(255,255,255,0.08)" }} />
            <div style={{ position: "absolute" as const, bottom: -30, left: -30, width: 100, height: 100,
              borderRadius: "50%", background: "rgba(255,255,255,0.06)" }} />
          </div>
        )}
        {/* Hero message overlay */}
        <div style={{ position: "absolute" as const, inset: 0,
          background: imgB64 ? "linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.2) 60%, transparent 100%)" : "none",
          display: "flex", flexDirection: "column" as const, justifyContent: "flex-end", padding: "16px 18px" }}>
          <div style={{ fontSize: 9, fontWeight: 700, color: imgB64 ? "rgba(255,255,255,0.7)" : "rgba(255,255,255,0.65)",
            letterSpacing: "0.14em", textTransform: "uppercase" as const, marginBottom: 4 }}>
            {big || "Campaign Concept"}
          </div>
          <div style={{ fontSize: imgB64 ? 18 : 22, fontWeight: 900,
            color: "white", lineHeight: 1.25, textShadow: "0 2px 8px rgba(0,0,0,0.3)" }}>
            "{hero}"
          </div>
          {tagline && <div style={{ fontSize: 11, color: "rgba(255,255,255,0.8)", marginTop: 4, fontStyle: "italic" }}>{tagline}</div>}
        </div>
      </div>

      {/* Strategic framework */}
      {fw && (
        <div style={{ padding: "12px 16px", background: "#fffbeb" }}>
          <div style={{ fontSize: 9, fontWeight: 700, color: "#92400e", letterSpacing: "0.1em",
            textTransform: "uppercase" as const, marginBottom: 5 }}>Strategic Framework</div>
          <div style={{ fontSize: 12, color: "#78350f", lineHeight: 1.6 }}>
            {fw.slice(0, 220)}{fw.length > 220 ? "…" : ""}
          </div>
        </div>
      )}

      {/* Messaging pillars */}
      {pillars.length > 0 && (
        <div style={{ padding: "10px 14px", background: "#fff7ed", borderTop: "1px solid #fed7aa",
          display: "flex", flexWrap: "wrap" as const, gap: 5 }}>
          {pillars.slice(0, 3).map((p, i) => (
            <span key={i} style={{ fontSize: 10, padding: "3px 10px", borderRadius: 99,
              background: "#fef3c7", border: "1px solid #fde68a", color: "#92400e", fontWeight: 600 }}>
              {String(p).slice(0, 42)}{String(p).length > 42 ? "…" : ""}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function CopyPanel({ m }: { m?: Record<string,unknown> }) {
  if (!m?.short_headline) return null;
  return (
    <div style={{ width: "100%" }}>
      {/* Billboard mock */}
      <div style={{ borderRadius: 14, overflow: "hidden", marginBottom: 10, border: "1px solid #bfdbfe" }}>
        <div style={{ background: "linear-gradient(135deg, #0055A4, #0369a1)", padding: "18px 20px", textAlign: "center" as const, position: "relative" as const }}>
          <div style={{ fontSize: 9, fontWeight: 700, color: "rgba(255,255,255,0.6)", letterSpacing: "0.14em", textTransform: "uppercase" as const, marginBottom: 6 }}>Billboard · Short</div>
          <div style={{ fontSize: 22, fontWeight: 900, color: "white", lineHeight: 1.2 }}>"{m.short_headline as string}"</div>
        </div>
        {!!m.cta && <div style={{ background: "#0055A4", padding: "8px", textAlign: "center" as const }}>
          <span style={{ display: "inline-block", padding: "5px 18px", borderRadius: 99, background: "white", color: "#0055A4", fontSize: 11, fontWeight: 800 }}>{String(m.cta)}</span>
        </div>}
      </div>

      {/* Medium + long */}
      {!!m.medium_headline && (
        <div style={{ marginBottom: 8, padding: "10px 12px", borderRadius: 10, background: "#f0f9ff", border: "1px solid #bae6fd" }}>
          <div style={{ fontSize: 9, fontWeight: 700, color: "#0369a1", textTransform: "uppercase" as const, letterSpacing: "0.1em", marginBottom: 4 }}>Digital · Medium</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#0f172a" }}>"{String(m.medium_headline)}"</div>
        </div>
      )}
      {!!m.body && (
        <div style={{ marginBottom: 8, padding: "10px 12px", borderRadius: 10, background: "#f8fafc", border: "1px solid #e2e8f0", fontSize: 12, color: "#475569", lineHeight: 1.6 }}>
          {String(m.body).slice(0, 140)}{String(m.body).length > 140 ? "…" : ""}
        </div>
      )}

      {/* Social row */}
      <div style={{ display: "flex", gap: 8 }}>
        {!!m.instagram && (
          <div style={{ flex: 1, padding: "9px 11px", borderRadius: 10, background: "#fdf4ff", border: "1px solid #e9d5ff" }}>
            <div style={{ fontSize: 9, fontWeight: 700, color: "#7c3aed", textTransform: "uppercase" as const, letterSpacing: "0.1em", marginBottom: 4 }}>📸 Instagram</div>
            <div style={{ fontSize: 11, color: "#6b21a8", lineHeight: 1.4 }}>{String(m.instagram).slice(0, 80)}{String(m.instagram).length > 80 ? "…" : ""}</div>
          </div>
        )}
        {!!m.tiktok_hook && (
          <div style={{ flex: 1, padding: "9px 11px", borderRadius: 10, background: "#fff0f6", border: "1px solid #ffd6e7" }}>
            <div style={{ fontSize: 9, fontWeight: 700, color: "#be185d", textTransform: "uppercase" as const, letterSpacing: "0.1em", marginBottom: 4 }}>🎵 TikTok Hook</div>
            <div style={{ fontSize: 11, color: "#9d174d", lineHeight: 1.4 }}>{String(m.tiktok_hook).slice(0, 80)}{String(m.tiktok_hook).length > 80 ? "…" : ""}</div>
          </div>
        )}
      </div>
    </div>
  );
}

const CHANNEL_CFG: Record<string, { icon: string; color: string; bg: string; border: string }> = {
  instagram: { icon: "📸", color: "#c026d3", bg: "#fdf4ff", border: "#e9d5ff" },
  tiktok:    { icon: "🎵", color: "#0f172a", bg: "#f8fafc", border: "#e2e8f0" },
  google:    { icon: "🔍", color: "#1967d2", bg: "#eff6ff", border: "#bfdbfe" },
  email:     { icon: "📧", color: "#059669", bg: "#f0fdf4", border: "#86efac" },
  ooh:       { icon: "🪧", color: "#d97706", bg: "#fffbeb", border: "#fde68a" },
  youtube:   { icon: "▶️", color: "#dc2626", bg: "#fff1f2", border: "#fecdd3" },
};

function ChannelPanel({ m, liveMsg }: { m?: Record<string,unknown>; liveMsg: string|null }) {
  const hasData = m && Object.keys(m).length > 0;

  if (!hasData) return (
    <div style={{ width: "100%" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "#4338ca", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 12 }}>Adapting for Channels</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {["📸 Instagram", "🎵 TikTok", "🔍 Google Ads", "📧 Email"].map((ch, i) => (
          <div key={i} className="source-card" style={{ animationDelay: `${i * 250}ms`, padding: "12px 14px" }}>
            <div style={{ fontSize: 14, marginBottom: 6 }}>{ch}</div>
            <div style={{ display: "flex", gap: 4 }}>
              {[0,1,2].map(d => <span key={d} className="source-dot" style={{ animationDelay: `${d * 0.2}s` }} />)}
            </div>
          </div>
        ))}
      </div>
      {liveMsg && <div style={{ marginTop: 10, fontSize: 12, color: "#4338ca", fontStyle: "italic" }}>{liveMsg}</div>}
    </div>
  );

  return (
    <div style={{ width: "100%" }} className="msg-fade">
      <div style={{ fontSize: 10, fontWeight: 700, color: "#4338ca", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 12 }}>
        {Object.keys(m!).length} Channels Ready to Publish
      </div>
      <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
        {Object.entries(m!).map(([key, val]) => {
          const ch  = val as any;
          const cfg = CHANNEL_CFG[key] ?? { icon: "📢", color: "#64748b", bg: "#f8fafc", border: "#e2e8f0" };
          return (
            <div key={key} style={{ borderRadius: 12, overflow: "hidden", border: `1px solid ${cfg.border}` }}>
              <div style={{ padding: "7px 12px", background: cfg.bg, borderBottom: `1px solid ${cfg.border}`,
                display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 15 }}>{cfg.icon}</span>
                <span style={{ fontSize: 12, fontWeight: 800, color: cfg.color }}>{ch.platform}</span>
                <span style={{ marginLeft: "auto", fontSize: 9, padding: "2px 8px", borderRadius: 99,
                  background: cfg.border, color: cfg.color, fontWeight: 700 }}>{ch.format}</span>
                <span style={{ fontSize: 10, color: "#10b981", fontWeight: 700 }}>✓ Ready</span>
              </div>
              <div style={{ padding: "8px 12px", background: "white" }}>
                {(ch.headline || ch.hook) && (
                  <div style={{ fontSize: 12, fontWeight: 700, color: "#0f172a", marginBottom: 4 }}>
                    "{String(ch.headline || ch.hook).slice(0, 60)}{String(ch.headline || ch.hook).length > 60 ? "…" : ""}"
                  </div>
                )}
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {ch.cta && <span style={{ fontSize: 10, padding: "2px 10px", borderRadius: 99,
                    background: cfg.color, color: "white", fontWeight: 700 }}>{ch.cta}</span>}
                  {ch.caption && <span style={{ fontSize: 10, color: "#64748b" }}>{String(ch.caption).slice(0, 50)}…</span>}
                  {ch.subject && <span style={{ fontSize: 10, color: "#64748b" }}>Subject: {ch.subject}</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CulturePanel({ m }: { m?: Record<string,unknown> }) {
  const brief = String(m?.brief ?? "");
  if (!brief) return null;
  const sentences = brief.split(/\.\s+/).slice(0, 4);
  return (
    <div style={{ width: "100%" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "#0d9488", letterSpacing: "0.09em", textTransform: "uppercase" as const, marginBottom: 10 }}>Cultural Intelligence Brief</div>
      {sentences.map((s, i) => (
        <div key={i} style={{ display: "flex", gap: 10, marginBottom: 10, padding: "10px 12px", borderRadius: 10, background: i === 0 ? "#f0fdfa" : "#f8fafc", border: `1px solid ${i === 0 ? "#99f6e4" : "#e2e8f0"}` }}>
          <span style={{ fontSize: 14 }}>{["🌍", "💫", "🎯", "⚡"][i]}</span>
          <span style={{ fontSize: 12, color: "#1a2332", lineHeight: 1.5 }}>{s.trim()}{s.trim().slice(-1) !== "." ? "." : ""}</span>
        </div>
      ))}
    </div>
  );
}

function KVPanel({ m, liveMsg }: { m?: Record<string,unknown>; liveMsg: string|null }) {
  const brandLocks  = m?.brand_locks  ? String(m.brand_locks)  : "";
  const bigIdea     = m?.big_idea     ? String(m.big_idea)     : "";
  const imagePrompt = m?.image_prompt ? String(m.image_prompt) : "";
  const imageB64    = m?.image_b64    ? String(m.image_b64)    : "";

  // Derive active step from what data has arrived
  const activeStep = imageB64 ? 3 : imagePrompt ? 3 : bigIdea ? 2 : brandLocks ? 1 : 0;
  const isGenerating = !imageB64 && (liveMsg?.toLowerCase().includes("imagen") || !!imagePrompt);

  const KV_STEPS = [
    { icon: "🔒", label: "Brand locks extracted",  dataKey: "brand_locks",  content: brandLocks },
    { icon: "💡", label: "Big Idea developed",      dataKey: "big_idea",     content: bigIdea },
    { icon: "🖼️", label: "Image prompt crafted",   dataKey: "image_prompt", content: imagePrompt },
    { icon: "✨", label: "Imagen 4 generating",     dataKey: "image_b64",    content: imageB64 },
  ];

  return (
    <div style={{ width: "100%" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "#be123c", letterSpacing: "0.09em",
        textTransform: "uppercase" as const, marginBottom: 10 }}>Image Generation Pipeline</div>

      {KV_STEPS.map((step, i) => {
        const isDone   = i < activeStep || (i === 3 && !!imageB64);
        const isActive = !isDone && (i === activeStep || (i === 3 && isGenerating));
        const showContent = !!step.content;

        return (
          <div key={i} style={{ marginBottom: 8 }}>
            {/* Step header row */}
            <div style={{ display: "flex", alignItems: "center", gap: 10,
              padding: "9px 12px", borderRadius: showContent ? "10px 10px 0 0" : 10,
              background: isDone ? "#f0fdf4" : isActive ? "#fff1f2" : "#f8fafc",
              border: `1px solid ${isDone ? "#86efac" : isActive ? "#fecdd3" : "#e2e8f0"}`,
              borderBottom: showContent ? "none" : undefined }}>
              <span style={{ fontSize: 16 }}>{step.icon}</span>
              <span style={{ fontSize: 12, fontWeight: isDone || isActive ? 700 : 400,
                color: isDone ? "#065f46" : isActive ? "#be123c" : "#94a3b8" }}>{step.label}</span>
              {isDone && <span style={{ marginLeft: "auto", color: "#10b981", fontWeight: 700, fontSize: 13 }}>✓</span>}
              {isActive && !showContent && (
                <div style={{ marginLeft: "auto", display: "flex", gap: 3 }}>
                  {[0,1,2].map(d => <span key={d} className="source-dot" style={{ animationDelay: `${d * 0.2}s`, background: "#be123c" }} />)}
                </div>
              )}
            </div>

            {/* Step content reveal */}
            {showContent && (
              <div className="msg-fade" style={{
                padding: "10px 12px", borderRadius: "0 0 10px 10px",
                background: isDone ? "#f0fdf4" : "#fff8f8",
                border: `1px solid ${isDone ? "#86efac" : "#fecdd3"}`,
                borderTop: "none",
              }}>
                {i === 3 && imageB64 ? (
                  /* Generated image */
                  <img src={`data:image/jpeg;base64,${imageB64}`} alt="Generated key visual"
                    style={{ width: "100%", borderRadius: 8, display: "block" }} />
                ) : (
                  /* Text content — show first few lines */
                  <div style={{ fontSize: 11, color: "#374151", lineHeight: 1.6,
                    maxHeight: 90, overflow: "hidden", position: "relative" as const }}>
                    {step.content.slice(0, 220)}{step.content.length > 220 ? "…" : ""}
                    <div style={{ position: "absolute" as const, bottom: 0, left: 0, right: 0, height: 24,
                      background: `linear-gradient(transparent, ${isDone ? "#f0fdf4" : "#fff8f8"})` }} />
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Running view (pipeline in progress) ─────────────────────
function RunningView({
  agentStatus,
  liveLog,
  milestones,
}: {
  agentStatus: Record<string, string>;
  liveLog: AgentEvent[];
  milestones: Record<string, Record<string, unknown>>;
}) {
  // Most recent running agent
  const activeKey = useMemo(() =>
    [...liveLog].reverse().find(e => e.status === "running")?.agent ?? null,
  [liveLog]);

  // Most recent done agent (to show completion card between agents)
  const lastDoneEvent = useMemo(() =>
    [...liveLog].reverse().find(e => e.status === "done"),
  [liveLog]);

  // What to display on right: running agent takes priority, else last completed
  const displayKey  = activeKey ?? lastDoneEvent?.agent ?? null;
  const displayMode = activeKey ? "running" : lastDoneEvent ? "done" : "idle";

  const liveMsg = useMemo(() => {
    if (!displayKey) return null;
    if (displayMode === "done") {
      return [...liveLog].reverse().find(e => e.agent === displayKey && e.status === "done")?.message ?? null;
    }
    return [...liveLog].reverse().find(e => e.agent === displayKey && e.status === "running")?.message ?? null;
  }, [liveLog, displayKey, displayMode]);

  const v = displayKey ? (AGENT_VISUALS[displayKey] ?? DEFAULT_VISUAL) : DEFAULT_VISUAL;
  const stage = displayKey ? HARNESS_STAGES.find(s => s.key === displayKey) : null;

  const doneCount = HARNESS_STAGES.filter(s => agentStatus[s.key] === "done").length;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", fontFamily: "Inter,sans-serif" }}>

      {/* ── LEFT: step sidebar ───────────────────────────────── */}
      <div style={{ width: 340, flexShrink: 0, background: "#fff", borderRight: "1px solid #e2e8f0",
        display: "flex", flexDirection: "column", padding: "28px 20px", overflowY: "auto" as const }}>

        {/* Logo */}
        <div style={{ marginBottom: 6 }}><AsterLogo /></div>
        <div style={{ marginBottom: 22 }}><PoweredByInfosys /></div>

        {/* Progress bar */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", letterSpacing: "0.09em",
            textTransform: "uppercase" as const, marginBottom: 6 }}>Campaign Pipeline</div>
          <div style={{ height: 6, background: "#e2e8f0", borderRadius: 99, overflow: "hidden" }}>
            <div style={{ height: "100%", borderRadius: 99, transition: "width 0.8s ease",
              background: `linear-gradient(90deg, ${v.g1}, ${v.g2})`,
              width: `${Math.max(4, (doneCount / HARNESS_STAGES.length) * 100)}%` }} />
          </div>
          <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 5 }}>
            {doneCount} of {HARNESS_STAGES.length} complete · 2–5 min
          </div>
        </div>

        {/* Step list */}
        <div style={{ display: "flex", flexDirection: "column" as const, gap: 6, flex: 1 }}>
          {HARNESS_STAGES.map((s, i) => {
            const st    = agentStatus[s.key];
            const isOn  = s.key === activeKey;
            const isDone = st === "done";
            const vis   = AGENT_VISUALS[s.key] ?? DEFAULT_VISUAL;
            return (
              <div key={s.key} style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "11px 14px", borderRadius: 12,
                background: isOn ? `${vis.g1}10` : isDone ? "#f0fdf4" : "#fafafa",
                border: `1.5px solid ${isOn ? vis.g1 + "35" : isDone ? "#bbf7d0" : "#f1f5f9"}`,
                transition: "all 0.35s ease",
              }}>
                {/* Circle */}
                <div style={{
                  width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: isDone ? 13 : 11, fontWeight: 700,
                  background: isOn ? vis.g1 : isDone ? "#10b981" : "#e2e8f0",
                  color: isOn || isDone ? "#fff" : "#94a3b8",
                  boxShadow: isOn ? `0 0 0 4px ${vis.g1}20` : "none",
                  animation: isOn ? "step-ring 1.6s ease-in-out infinite" : "none",
                }}>
                  {isDone ? "✓" : isOn ? "⋯" : i + 1}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 700,
                    color: isOn ? vis.g1 : isDone ? "#065f46" : "#94a3b8" }}>
                    {s.icon} {s.label}
                  </div>
                  <div style={{ fontSize: 11, marginTop: 1,
                    color: isOn ? vis.g1 + "cc" : isDone ? "#6ee7b7" : "#cbd5e1" }}>
                    {isOn ? "Running now" : isDone ? "Complete ✓" : "Waiting"}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── RIGHT: spotlight panel ────────────────────────────── */}
      <div style={{ flex: 1, position: "relative" as const, overflow: "hidden",
        background: `linear-gradient(145deg, ${v.g1}12 0%, ${v.g2}08 50%, #f4f6f9 100%)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        transition: "background 1s ease" }}>

        {/* Animated blobs */}
        <div className="blob blob-1" style={{
          background: `radial-gradient(circle, ${v.blob1}35 0%, transparent 68%)`,
        }} />
        <div className="blob blob-2" style={{
          background: `radial-gradient(circle, ${v.blob2}28 0%, transparent 68%)`,
        }} />

        {/* Grid overlay */}
        <div style={{ position: "absolute" as const, inset: 0, opacity: 0.04,
          backgroundImage: "linear-gradient(#0055A4 1px, transparent 1px), linear-gradient(90deg, #0055A4 1px, transparent 1px)",
          backgroundSize: "40px 40px" }} />

        {/* Spotlight card — re-animates on agent/mode change */}
        {displayMode !== "idle" ? (
          <div key={displayKey ?? "idle"} className="spotlight-card" style={{
            position: "relative" as const, zIndex: 2,
            background: "rgba(255,255,255,0.82)",
            backdropFilter: "blur(28px)", WebkitBackdropFilter: "blur(28px)",
            border: `1.5px solid ${v.g1}28`,
            borderRadius: 24, padding: "28px 30px",
            width: "min(580px, 92%)", maxHeight: "80vh", overflowY: "auto" as const,
            boxShadow: `0 20px 72px ${v.g1}18, 0 4px 20px rgba(0,0,0,0.07)`,
          }}>
            {/* Header row */}
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
              <div style={{ position: "relative" as const, flexShrink: 0 }}>
                {displayMode === "running" && <>
                  <div style={{ position: "absolute" as const, inset: -10, borderRadius: "50%",
                    border: `2px solid ${v.g1}25`, animation: "ring-spin 6s linear infinite" }} />
                  <div style={{ position: "absolute" as const, inset: -20, borderRadius: "50%",
                    border: `1.5px dashed ${v.g1}15`, animation: "ring-spin 10s linear infinite reverse" }} />
                </>}
                {displayMode === "done" && <div style={{ position: "absolute" as const, top: -4, right: -4, zIndex: 1,
                  width: 22, height: 22, borderRadius: "50%", background: "#10b981",
                  border: "2px solid white", display: "flex", alignItems: "center",
                  justifyContent: "center", fontSize: 12, color: "white", fontWeight: 800 }}>✓</div>}
                <div style={{ width: 72, height: 72, borderRadius: "50%",
                  background: `linear-gradient(135deg, ${v.g1}22, ${v.g2}14)`,
                  border: `2px solid ${v.g1}35`, display: "flex", alignItems: "center",
                  justifyContent: "center", fontSize: 36,
                  boxShadow: `0 0 36px ${v.g1}28`,
                  animation: displayMode === "running" ? "icon-breathe 2.5s ease-in-out infinite" : "none",
                }}>{stage?.icon ?? "🤖"}</div>
              </div>
              <div>
                <div style={{ display: "inline-flex", alignItems: "center", gap: 5, marginBottom: 4,
                  padding: "3px 10px", borderRadius: 99,
                  background: displayMode === "done" ? "#dcfce7" : `${v.g1}14`,
                  border: `1px solid ${displayMode === "done" ? "#86efac" : v.g1 + "28"}` }}>
                  {displayMode === "running" && <span style={{ width: 5, height: 5, borderRadius: "50%",
                    background: v.g1, animation: "wave-dot 1.2s ease-in-out infinite", display: "inline-block" }} />}
                  <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.1em",
                    textTransform: "uppercase" as const,
                    color: displayMode === "done" ? "#15803d" : v.g1 }}>
                    {stage?.label ?? "Agent"} · {displayMode === "done" ? "Complete" : "Running"}
                  </span>
                </div>
                <div style={{ fontSize: 20, fontWeight: 800, color: "#0f172a", lineHeight: 1.2 }}>
                  {v.title}{displayMode === "done" ? " ✓" : ""}
                </div>
              </div>
            </div>

            {/* Agent-specific content panel */}
            <div key={displayKey ?? "idle"} className="msg-fade">
              {displayKey === "briefing" && <BriefingPanel m={milestones.briefing} liveMsg={liveMsg} />}
              {displayKey === "strategy" && milestones.strategy
                ? <StrategyPanel m={milestones.strategy} />
                : displayKey === "strategy" && <div style={{ fontSize: 14, color: "#64748b", fontStyle: "italic" }}>{liveMsg ?? "Building creative strategy…"}</div>}
              {displayKey === "copy" && milestones.copy
                ? <CopyPanel m={milestones.copy} />
                : displayKey === "copy" && <div style={{ fontSize: 14, color: "#64748b", fontStyle: "italic" }}>{liveMsg ?? "Writing copy variants…"}</div>}
              {displayKey === "culture" && milestones.culture
                ? <CulturePanel m={milestones.culture} />
                : displayKey === "culture" && <div style={{ fontSize: 14, color: "#64748b", fontStyle: "italic" }}>{liveMsg ?? "Researching cultural trends…"}</div>}
              {displayKey === "kv" && <KVPanel m={milestones.kv} liveMsg={liveMsg} />}
              {displayKey === "channel" && <ChannelPanel m={milestones.channel} liveMsg={liveMsg} />}
            </div>

            {/* Wave dots (running, no rich content yet) */}
            {displayMode === "running" && !milestones[displayKey ?? ""] && displayKey !== "briefing" && displayKey !== "kv" && displayKey !== "channel" && (
              <div style={{ display: "flex", gap: 7, marginTop: 20 }}>
                {[0,1,2,3].map(i => <div key={i} style={{ width: 7, height: 7, borderRadius: "50%",
                  background: v.g1, opacity: 0.7, animation: `wave-dot 1.4s ease-in-out ${i*0.18}s infinite` }} />)}
              </div>
            )}
          </div>
        ) : (
          /* ── Idle: animated agent network ── */
          <div style={{ position: "relative" as const, zIndex: 1, display: "flex",
            flexDirection: "column" as const, alignItems: "center", justifyContent: "center",
            width: "100%", gap: 28 }}>

            {/* Network graph */}
            <div style={{ position: "relative" as const, width: 400, height: 400, flexShrink: 0 }}>

              {/* SVG: rings + connecting lines */}
              <svg viewBox="0 0 400 400" style={{ position: "absolute" as const, inset: 0, width: "100%", height: "100%", overflow: "visible" }}>
                {/* Pulsing rings */}
                {[60, 95, 140].map((r, ri) => (
                  <circle key={ri} cx="200" cy="200" r={r} fill="none"
                    stroke="rgba(0,85,164,0.12)" strokeWidth="1"
                    style={{ animation: `ring-out ${2.5 + ri * 0.8}s ${ri * 0.4}s ease-out infinite` }} />
                ))}
                {/* Connecting lines from center to each agent */}
                {HARNESS_STAGES.map((s, i) => {
                  const a = (i / HARNESS_STAGES.length) * 2 * Math.PI - Math.PI / 2;
                  const x2 = 200 + Math.cos(a) * 158;
                  const y2 = 200 + Math.sin(a) * 158;
                  const vis = AGENT_VISUALS[s.key] ?? DEFAULT_VISUAL;
                  return (
                    <line key={s.key} x1="200" y1="200" x2={x2} y2={y2}
                      stroke={vis.g1} strokeOpacity="0.25" strokeWidth="1.5"
                      strokeDasharray="6 5"
                      style={{ animation: `dash-move 2s ${i * 0.22}s linear infinite` }} />
                  );
                })}
              </svg>

              {/* Central hub */}
              <div style={{
                position: "absolute" as const, left: "50%", top: "50%",
                transform: "translate(-50%,-50%)",
                width: 72, height: 72, borderRadius: "50%", zIndex: 3,
                background: "linear-gradient(135deg, #0055A4, #4f46e5)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 32,
                boxShadow: "0 0 0 8px rgba(0,85,164,0.12), 0 0 40px rgba(0,85,164,0.35)",
                animation: "hub-beat 2s ease-in-out infinite",
              }}>🤖</div>

              {/* Agent nodes */}
              {HARNESS_STAGES.map((s, i) => {
                const a    = (i / HARNESS_STAGES.length) * 2 * Math.PI - Math.PI / 2;
                const r    = 158;
                const cx   = 200 + Math.cos(a) * r;
                const cy   = 200 + Math.sin(a) * r;
                const vis  = AGENT_VISUALS[s.key] ?? DEFAULT_VISUAL;
                // Label offset away from center
                const lx   = Math.cos(a) * 32;
                const ly   = Math.sin(a) * 32;
                return (
                  <div key={s.key} style={{
                    position: "absolute" as const,
                    left: cx, top: cy,
                    transform: "translate(-50%,-50%)",
                    zIndex: 2,
                    animation: `node-in 0.5s ${0.15 + i * 0.12}s cubic-bezier(0.22,1,0.36,1) both`,
                  }}>
                    {/* Node circle */}
                    <div style={{
                      width: 46, height: 46, borderRadius: "50%",
                      background: `linear-gradient(135deg, ${vis.g1}22, ${vis.g2}14)`,
                      border: `2px solid ${vis.g1}45`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 20,
                      boxShadow: `0 0 16px ${vis.g1}28`,
                      animation: `node-glow 2.4s ${i * 0.35}s ease-in-out infinite`,
                    }}>{s.icon}</div>
                    {/* Label */}
                    <div style={{
                      position: "absolute" as const,
                      left: `calc(50% + ${lx}px)`,
                      top: `calc(50% + ${ly}px)`,
                      transform: "translate(-50%,-50%)",
                      fontSize: 9, fontWeight: 700, color: vis.g1,
                      whiteSpace: "nowrap" as const,
                      background: "rgba(255,255,255,0.9)",
                      padding: "2px 6px", borderRadius: 6,
                      border: `1px solid ${vis.g1}25`,
                    }}>{s.label}</div>
                  </div>
                );
              })}
            </div>

            {/* Title */}
            <div style={{ textAlign: "center" as const }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: "#0f172a",
                letterSpacing: "-0.02em", marginBottom: 8 }}>
                Launching AI Campaign Pipeline
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                {[0,1,2].map(d => (
                  <div key={d} style={{ width: 6, height: 6, borderRadius: "50%", background: "#0055A4",
                    opacity: 0.6, animation: `wave-dot 1.4s ${d * 0.2}s ease-in-out infinite` }} />
                ))}
                <span style={{ fontSize: 13, color: "#64748b", marginLeft: 4 }}>
                  {HARNESS_STAGES.length} agents connecting
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Fan Truth Score Gauge ─────────────────────────────────────
function ScoreGauge({ score, verdict }: { score: number; verdict: string }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const pct  = Math.min(score, 100) / 100;
  const dash = circ * pct;
  const color = score >= 75 ? "#10b981" : score >= 60 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
      <svg width="88" height="88" viewBox="0 0 88 88">
        <circle cx="44" cy="44" r={r} fill="none" stroke="#e2e8f0" strokeWidth="8" />
        <circle cx="44" cy="44" r={r} fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
          transform="rotate(-90 44 44)" style={{ transition: "stroke-dasharray 1s ease" }} />
        <text x="44" y="41" textAnchor="middle" fill={color} fontSize="18" fontWeight="700" fontFamily="Inter,sans-serif">{score}</text>
        <text x="44" y="56" textAnchor="middle" fill="#94a3b8" fontSize="10" fontFamily="Inter,sans-serif">/100</text>
      </svg>
      <div>
        <div style={{ fontSize: 12, color: "#64748b", textTransform: "uppercase" as const, letterSpacing: "0.08em", marginBottom: 4 }}>Fan Truth Score</div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 20, fontWeight: 700, color }}>{score}/100</span>
          <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 10px", borderRadius: 20,
            background: verdict === "PASS" ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)",
            color: verdict === "PASS" ? "#10b981" : "#ef4444",
            border: `1px solid ${verdict === "PASS" ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"}` }}>
            {verdict}
          </span>
        </div>
      </div>
    </div>
  );
}

// ── KPI Row ───────────────────────────────────────────────────
function KPIRow({ metric, target, flag }: { metric: string; target: string; flag: string; note?: string }) {
  const cfg: Record<string, { bg: string; color: string; border: string; icon: string }> = {
    OK:          { bg: "rgba(16,185,129,0.1)",  color: "#10b981", border: "rgba(16,185,129,0.25)",  icon: "✓" },
    AMBITIOUS:   { bg: "rgba(245,158,11,0.1)",  color: "#f59e0b", border: "rgba(245,158,11,0.25)",  icon: "↑" },
    UNREALISTIC: { bg: "rgba(239,68,68,0.1)",   color: "#ef4444", border: "rgba(239,68,68,0.25)",   icon: "✗" },
  };
  const c = cfg[flag] ?? cfg.OK;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px",
      borderRadius: 10, background: c.bg, border: `1px solid ${c.border}`, marginBottom: 6 }}>
      <span style={{ fontSize: 16, fontWeight: 700, color: c.color, width: 20, textAlign: "center" as const }}>{c.icon}</span>
      <div style={{ flex: 1 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: "#1a2332" }}>{metric}</span>
        <span style={{ fontSize: 12, color: "#64748b", marginLeft: 6 }}>— {target}</span>
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, color: c.color, padding: "2px 8px",
        background: `${c.color}18`, borderRadius: 12 }}>{flag}</span>
    </div>
  );
}

// ── Distribute Campaign Panel ─────────────────────────────────
const API_BASE_PUB = import.meta.env.VITE_API_URL || "http://localhost:8000";


function DistributePanel({ output, campaignId }: {
  output: Record<string, unknown> | null; campaignId: string | null;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [email,    setEmail]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [results,  setResults]  = useState<Record<string, any> | null>(null);
  const [error,    setError]    = useState("");

  const cp       = (output as any)?.creative_pipeline;
  const strategy = (output as any)?.creative_strategy;
  const copy     = (output as any)?.campaign_copy;
  // brand from machine_brief spread, or extracted from campaign_id (format: campaign-{brand}-xxx)
  const brandFromId = campaignId
    ? campaignId.replace(/^campaign-/, "").split("-")[0]
        .replace(/^(.)/, (c: string) => c.toUpperCase())
    : "";
  const brand = String((output as any)?.brand ?? brandFromId ?? "");

  const toggle = (key: string) => setSelected(s => {
    const n = new Set(s);
    n.has(key) ? n.delete(key) : n.add(key);
    return n;
  });

  const handlePublish = useCallback(async () => {
    if (selected.size === 0) return;
    if (!campaignId) { setError("No campaign ID — run a full campaign first"); return; }
    if (!brand) { setError("Brand not found in campaign output"); return; }
    setLoading(true); setError(""); setResults(null);
    try {
      const res = await fetch(`${API_BASE_PUB}/publish/${campaignId}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand,
          hero_message:    strategy?.hero_message ?? "",
          short_headline:  copy?.short?.headline  ?? "",
          medium_headline: copy?.medium?.headline ?? "",
          body:            copy?.long?.body       ?? "",
          cta:             copy?.cta              ?? "",
          tagline:         strategy?.tagline      ?? "",
          image_b64:       cp?.image_b64          ?? "",
          to_email:        selected.has("email") ? email : "",
          channels:        Array.from(selected),
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? "Publish failed");
      setResults(json.results);
      // Auto-open landing page in new tab if published
      const lp = json.results?.landing_page;
      if (lp?.status === "live" && lp?.url) {
        window.open(`${API_BASE_PUB}${lp.url}`, "_blank");
      }
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [campaignId, brand, strategy, copy, cp, email, selected]);

  if (!strategy && !cp?.culture_brief) return null;

  const CHANNELS = [
    { key: "google_ads",   icon: "🔍", label: "Google Ads",    desc: "Responsive Search Ad" },
    { key: "landing_page", icon: "🌐", label: "Brand Website", desc: `${brand} landing page` },
    { key: "email",        icon: "📧", label: "Email Campaign", desc: "Branded HTML email" },
  ];

  const publishedCount = results
    ? Object.values(results).filter((r: any) => r.status !== "skipped" && r.status !== "error").length
    : 0;

  return (
    <div style={{ gridColumn: "1 / -1", borderRadius: 16, overflow: "hidden",
      border: "1.5px solid rgba(0,85,164,0.2)" }}>

      {/* Header */}
      <div style={{ padding: "16px 24px", background: "#0055A4",
        display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 22 }}>🚀</span>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: "white" }}>Distribute Campaign</div>
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.65)" }}>Select channels and publish</div>
          </div>
        </div>
        {!results && selected.size > 0 && (
          <button onClick={handlePublish} disabled={loading}
            style={{ padding: "9px 24px", borderRadius: 99, border: "2px solid white",
              background: loading ? "transparent" : "white", color: loading ? "white" : "#0055A4",
              fontSize: 13, fontWeight: 800, cursor: "pointer" }}>
            {loading ? "Publishing…" : `🚀 Publish to ${selected.size} channel${selected.size > 1 ? "s" : ""}`}
          </button>
        )}
        {results && (
          <div style={{ fontSize: 12, fontWeight: 700, color: "#86efac" }}>
            ✅ {publishedCount} channel{publishedCount !== 1 ? "s" : ""} published
          </div>
        )}
      </div>

      <div style={{ padding: "20px 24px", background: "linear-gradient(135deg,#eff6ff,#f0f9ff)" }}>

        {/* Channel selector cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12, marginBottom: 16 }}>
          {CHANNELS.map(ch => {
            const r    = results?.[ch.key];
            const done = r?.status === "submitted" || r?.status === "live" || r?.status === "sent";
            const isOn = selected.has(ch.key);
            const canSelect = !results;

            return (
              <div key={ch.key}
                onClick={() => canSelect && toggle(ch.key)}
                style={{
                  padding: "16px", borderRadius: 14, cursor: canSelect ? "pointer" : "default",
                  transition: "all 0.2s",
                  background: done ? "#f0fdf4" : isOn ? "#eff6ff" : "white",
                  border: `2px solid ${done ? "#86efac" : isOn ? "#0055A4" : "#e2e8f0"}`,
                  boxShadow: isOn && !done ? "0 0 0 3px rgba(0,85,164,0.12)" : "none",
                }}>

                {/* Icon + checkbox row */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                  <span style={{ fontSize: 24 }}>{ch.icon}</span>
                  {!results && (
                    <div style={{ width: 20, height: 20, borderRadius: 6,
                      border: `2px solid ${isOn ? "#0055A4" : "#cbd5e1"}`,
                      background: isOn ? "#0055A4" : "white",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 12, color: "white", fontWeight: 800 }}>
                      {isOn ? "✓" : ""}
                    </div>
                  )}
                  {done && <span style={{ fontSize: 14, color: "#10b981", fontWeight: 800 }}>✓</span>}
                </div>

                <div style={{ fontSize: 13, fontWeight: 700,
                  color: done ? "#065f46" : isOn ? "#0055A4" : "#1a2332", marginBottom: 3 }}>
                  {ch.label}
                </div>
                <div style={{ fontSize: 10, color: "#94a3b8" }}>{ch.desc}</div>

                {/* Results per channel */}
                {done && ch.key === "google_ads" && r && (
                  <div style={{ marginTop: 10, padding: "8px 10px", borderRadius: 8,
                    background: "#f0f9ff", border: "1px solid #bfdbfe",
                    fontSize: 10, color: "#1e40af", lineHeight: 1.7 }}>
                    <div>Ad ID: <b>{r.ad_id}</b></div>
                    <div>Est. Reach: <b>{r.est_impressions}</b></div>
                    <div>CPC: <b>{r.est_cpc}</b> · Quality: <b>{r.quality_score}/10</b></div>
                  </div>
                )}
                {done && ch.key === "landing_page" && r && (
                  <div style={{ marginTop: 10 }}>
                    <a href={`${API_BASE_PUB}${r.url}`} target="_blank" rel="noreferrer"
                      style={{ display: "inline-flex", alignItems: "center", gap: 5,
                        padding: "7px 14px", borderRadius: 99, background: "#0055A4",
                        color: "white", fontSize: 11, fontWeight: 700, textDecoration: "none" }}>
                      🔗 Open Landing Page
                    </a>
                  </div>
                )}
                {done && ch.key === "email" && r && (
                  <div style={{ marginTop: 8, fontSize: 10, color: "#065f46" }}>
                    ✉ Sent to <b>{r.to}</b>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Email input — only shown when email channel is selected */}
        {selected.has("email") && !results && (
          <div style={{ marginBottom: 14, display: "flex", alignItems: "center", gap: 10,
            padding: "12px 16px", borderRadius: 12, background: "white", border: "1.5px solid #bfdbfe" }}>
            <span style={{ fontSize: 18 }}>📧</span>
            <input type="email" placeholder="Enter recipient email address"
              value={email} onChange={e => setEmail(e.target.value)}
              style={{ flex: 1, border: "none", outline: "none", fontSize: 13, fontFamily: "inherit", color: "#1a2332" }} />
          </div>
        )}

        {/* No channel selected hint */}
        {!results && selected.size === 0 && (
          <div style={{ fontSize: 12, color: "#94a3b8", textAlign: "center" as const, padding: "8px 0" }}>
            Select one or more channels above to publish your campaign
          </div>
        )}

        {error && (
          <div style={{ padding: "10px 14px", borderRadius: 10, background: "#fee2e2",
            border: "1px solid #fca5a5", fontSize: 12, color: "#991b1b" }}>{error}</div>
        )}
      </div>
    </div>
  );
}

// ── Results view ─────────────────────────────────────────────
function ResultsView({ output, campaignId, onReset }: {
  output: Record<string, unknown> | null;
  campaignId: string | null;
  onReset: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const brief    = (output?.machine_brief ?? (output?.status ? output : null)) as any;
  const strategy = output?.creative_strategy as any;
  const copy     = output?.campaign_copy as any;

  const isReady  = brief?.status === "READY";
  // statusColor kept for potential future use
  // const statusColor = isReady ? "#10b981" : brief?.status === "INCOMPLETE" ? "#ef4444" : "#f59e0b";

  // Parse CDP insights into readable lines
  const cdpLines = output?.audience_insights
    ? String(output.audience_insights).split("\n").filter(l => l.trim())
    : [];

  return (
    <div style={styles.resultsPage}>
      {/* Header */}
      <div style={styles.resultsHero}>
        <div style={styles.resultsHeroInner}>
          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <div>
              <AsterLogo size={0.8} />
              <PoweredByInfosys />
            </div>
            <div style={{ width: 1, height: 36, background: "#e2e8f0" }} />
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: "#d1fae5",
                border: "1px solid #a7f3d0", display: "flex", alignItems: "center",
                justifyContent: "center", fontSize: 16 }}>✅</div>
              <div>
                <div style={styles.resultsTitle}>Campaign Brief Validated</div>
                {campaignId && <div style={styles.campaignIdTag}>#{campaignId}</div>}
              </div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ padding: "6px 16px", borderRadius: 20, fontSize: 12, fontWeight: 700,
              background: isReady ? "#d1fae5" : "#fef3c7",
              color: isReady ? "#065f46" : "#92400e",
              border: `1px solid ${isReady ? "#a7f3d0" : "#fde68a"}`, letterSpacing: "0.05em" }}>
              {brief?.status ?? "—"}
            </div>
            <button className="reset-btn" onClick={onReset}>New Campaign</button>
          </div>
        </div>
      </div>

      <div style={styles.resultsGrid}>
        {/* ── Brief Validation card ── */}
        {brief && (
          <div style={styles.resultCard}>
            <div style={styles.cardHeader}>📋 Brief Validation</div>

            {/* Fan Truth Gauge */}
            {brief.fan_truth && (
              <ScoreGauge score={brief.fan_truth.overall ?? 0} verdict={brief.fan_truth.verdict ?? "FAIL"} />
            )}

            {/* Fan Truth statement */}
            {brief.fan_truth?.statement && (
              <div style={{ padding: "12px 16px", borderRadius: 10, marginBottom: 16,
                background: "rgba(124,58,237,0.08)", border: "1px solid rgba(124,58,237,0.2)" }}>
                <div style={{ fontSize: 11, color: "#7c3aed", fontWeight: 600, letterSpacing: "0.06em",
                  textTransform: "uppercase" as const, marginBottom: 6 }}>Fan Truth</div>
                <div style={{ fontSize: 14, color: "#1a2332", fontStyle: "italic", lineHeight: 1.6 }}>
                  "{brief.fan_truth.statement}"
                </div>
                {brief.fan_truth.notes && (
                  <div style={{ fontSize: 12, color: "#64748b", marginTop: 8, lineHeight: 1.5 }}>
                    {brief.fan_truth.notes}
                  </div>
                )}
              </div>
            )}

            {/* KPIs */}
            {brief.kpis?.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, color: "#64748b", fontWeight: 600,
                  letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 8 }}>KPIs</div>
                {brief.kpis.map((k: any, i: number) => (
                  <KPIRow key={i} metric={k.metric} target={k.target} flag={k.flag} note={k.note} />
                ))}
              </div>
            )}

            {/* Summary */}
            {(brief.validation_notes || brief.brief_summary) && (
              <p style={{ fontSize: 13, color: "#64748b", lineHeight: 1.7, margin: 0, paddingTop: 12,
                borderTop: "1px solid #e2e8f0" }}>
                {brief.validation_notes || brief.brief_summary}
              </p>
            )}
          </div>
        )}

        {/* ── CDP Audience Intelligence ── */}
        {cdpLines.length > 0 && (() => {
          const getText = (key: string) => {
            const l = cdpLines.find(l => l.toLowerCase().includes(key.toLowerCase()));
            return l ? l.split(":").slice(1).join(":").trim() : null;
          };
          const profilesLine = cdpLines.find(l => l.includes("profiles"));
          const profileCount = profilesLine?.match(/(\d[\d,]+)\s+\w+\s+profiles/)?.[1] ?? "—";
          const matchLine    = cdpLines.find(l => l.includes("matched"));
          const income       = getText("household income");
          const meatSpend    = getText("meat/protein spend");
          const deals        = getText("deal purchases");
          const webVisits    = getText("web visits");
          const channelsRaw  = getText("Top channels");
          const channels     = channelsRaw?.split(",").map(c => c.trim()) ?? [];
          const crmIdx       = cdpLines.findIndex(l => l.includes("CRM notes"));
          const crmNote      = crmIdx >= 0 ? cdpLines.slice(crmIdx + 1).join(" ").slice(0, 200) : null;

          const stat = (label: string, val: string | null, accent = "#0055A4") => val ? (
            <div style={{ flex: 1, minWidth: 100, padding: "10px 12px", borderRadius: 10,
              background: "#f8fafc", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: 10, color: "#475569", fontWeight: 600, letterSpacing: "0.08em",
                textTransform: "uppercase" as const, marginBottom: 4 }}>{label}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: accent }}>{val}</div>
            </div>
          ) : null;

          return (
            <div style={styles.resultCard}>
              {/* Header */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <div style={styles.cardHeader}>👥 Audience Intelligence</div>
                <span style={{ fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 12,
                  background: "#e8f0fb", color: "#0055A4",
                  border: "1px solid rgba(0,85,164,0.2)", letterSpacing: "0.06em" }}>
                  KAGGLE CDP
                </span>
              </div>

              {/* Profile count */}
              <div style={{ marginBottom: 12, padding: "10px 14px", borderRadius: 10,
                background: "linear-gradient(135deg, #e8f0fb, #eff6ff)",
                border: "1px solid rgba(0,85,164,0.15)" }}>
                <div style={{ fontSize: 20, fontWeight: 800, color: "#0055A4" }}>{profileCount}</div>
                <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
                  {matchLine?.trim() ?? "customer profiles analysed"}
                </div>
              </div>

              {/* Stats grid */}
              <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 6, marginBottom: 14 }}>
                {stat("Avg Income", income, "#10b981")}
                {stat("Meat Spend/yr", meatSpend, "#10b981")}
                {stat("Deal Purchases", deals, "#f59e0b")}
                {stat("Web Visits/mo", webVisits, "#3b82f6")}
              </div>

              {/* Channels */}
              {channels.length > 0 && (
                <div style={{ marginBottom: 14 }}>
                  <div style={{ fontSize: 10, color: "#475569", fontWeight: 600,
                    letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 6 }}>
                    Top Channels
                  </div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" as const }}>
                    {channels.map((ch, i) => (
                      <span key={i} style={{ fontSize: 11, padding: "3px 10px", borderRadius: 12,
                        background: "#e8f0fb", color: "#0055A4",
                        border: "1px solid rgba(0,85,164,0.2)", fontWeight: 600 }}>
                        {ch}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* CRM Quote */}
              {crmNote && (
                <div style={{ padding: "10px 12px", borderRadius: 8,
                  background: "rgba(0,0,0,0.2)", borderLeft: "2px solid #7c3aed" }}>
                  <div style={{ fontSize: 10, color: "#7c3aed", fontWeight: 600,
                    letterSpacing: "0.08em", marginBottom: 4 }}>CRM NOTE</div>
                  <div style={{ fontSize: 11, color: "#64748b", lineHeight: 1.6, fontStyle: "italic" }}>
                    "{crmNote}..."
                  </div>
                </div>
              )}
            </div>
          );
        })()}

        {/* ── Pipeline Output ── */}
        {brief && (
          <div style={styles.resultCard}>
            <div style={styles.cardHeader}>⚡ Pipeline Output</div>

            {/* Campaign details */}
            {[
              { label: "Campaign",  value: brief.campaign_name },
              { label: "Channels",  value: Array.isArray(brief.channels) ? brief.channels.join(" · ") : brief.channels },
              { label: "Market",    value: brief.market },
              { label: "Season",    value: brief.season },
              { label: "Budget",    value: brief.budget },
              { label: "Moment",    value: brief.moment_type },
              { label: "Audience",  value: brief.audience },
            ].filter(r => r.value).map((row, i, arr) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between",
                alignItems: "flex-start", padding: "8px 0",
                borderBottom: i < arr.length - 1 ? "1px solid #f1f5f9" : "none" }}>
                <span style={{ fontSize: 11, color: "#64748b", fontWeight: 600,
                  textTransform: "uppercase" as const, letterSpacing: "0.07em", flexShrink: 0, paddingRight: 12 }}>
                  {row.label}
                </span>
                <span style={{ fontSize: 12, color: "#1a2332", textAlign: "right" as const }}>
                  {String(row.value)}
                </span>
              </div>
            ))}

            {/* Brief summary */}
            {brief.brief_summary && (
              <div style={{ marginTop: 14, padding: "10px 12px", borderRadius: 8,
                background: "#eff6ff", borderLeft: "2px solid #0055A4" }}>
                <div style={{ fontSize: 10, color: "#0055A4", fontWeight: 600,
                  letterSpacing: "0.08em", marginBottom: 6 }}>BRIEF SUMMARY</div>
                <div style={{ fontSize: 12, color: "#64748b", lineHeight: 1.6 }}>
                  {brief.brief_summary}
                </div>
              </div>
            )}

            {/* Warnings */}
            {brief.brand_warnings?.length > 0 && (
              <div style={{ marginTop: 12 }}>
                {brief.brand_warnings.map((w: string, i: number) => (
                  <div key={i} style={{ fontSize: 12, color: "#f59e0b", display: "flex",
                    gap: 6, padding: "4px 0" }}>
                    <span>⚠</span><span>{w}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Creative Intelligence (from Full Campaign pipeline) ── */}
        {(() => {
          const cp = (output as any)?.creative_pipeline;
          if (!cp?.culture_brief && !cp?.big_idea) return null;
          return (
            <div style={{ ...styles.resultCard, gridColumn: "1 / -1",
              background: "linear-gradient(135deg, #f0f7ff, #eff6ff)",
              border: "1px solid rgba(0,85,164,0.15)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div style={styles.cardHeader}>🌍 Creative Intelligence</div>
                <span style={{ fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 12,
                  background: "#e8f0fb", color: "#0055A4", border: "1px solid rgba(0,85,164,0.2)" }}>
                  FULL CAMPAIGN PIPELINE
                </span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
                {cp.big_idea && (
                  <div style={{ padding: "14px 16px", borderRadius: 10, background: "#ffffff", border: "1px solid #e2e8f0" }}>
                    <div style={styles.cardLabel}>Big Idea</div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: "#0055A4", fontStyle: "italic",
                      lineHeight: 1.5, marginTop: 6 }}>{cp.big_idea.split("\n")[0]}</div>
                  </div>
                )}
                {cp.culture_brief && (
                  <div style={{ padding: "14px 16px", borderRadius: 10, background: "#ffffff", border: "1px solid #e2e8f0" }}>
                    <div style={styles.cardLabel}>Cultural Intelligence</div>
                    <div style={{ fontSize: 12, color: "#4a5568", lineHeight: 1.6, marginTop: 6 }}>
                      {cp.culture_brief.slice(0, 250)}...
                    </div>
                  </div>
                )}
                {cp.brand_summary && (
                  <div style={{ padding: "14px 16px", borderRadius: 10, background: "#ffffff", border: "1px solid #e2e8f0" }}>
                    <div style={styles.cardLabel}>Brand Locks</div>
                    <div style={{ fontSize: 12, color: "#4a5568", lineHeight: 1.6, marginTop: 6 }}>
                      {cp.brand_summary.slice(0, 250)}...
                    </div>
                  </div>
                )}
              </div>
              {!cp.image_b64 && (
                <div style={{ marginTop: 14, padding: "10px 14px", borderRadius: 8,
                  background: "#fef3c7", border: "1px solid #fde68a", fontSize: 12, color: "#92400e" }}>
                  ⚠ Key Visual pending — enable Gemini in Vertex AI Model Garden to generate images
                </div>
              )}
            </div>
          );
        })()}

        {/* ── Key Visual (from Full Campaign pipeline) ── */}
        {(() => {
          const cp = (output as any)?.creative_pipeline;
          if (!cp?.image_b64) return null;
          return (
            <div style={{ ...styles.resultCard, gridColumn: "1 / -1",
              background: "#ffffff", border: "1px solid #e2e8f0" }}>
              <div style={styles.cardHeader}>🎨 Key Visual — Generated by Gemini</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>
                <img
                  src={`data:image/jpeg;base64,${cp.image_b64}`}
                  alt="Generated Key Visual"
                  style={{ width: "100%", borderRadius: 12, border: "1px solid #e2e8f0",
                    boxShadow: "0 4px 16px rgba(0,0,0,0.08)" }}
                />
                <div>
                  {cp.big_idea && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={styles.cardLabel}>Big Idea</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: "#0055A4",
                        fontStyle: "italic", lineHeight: 1.5, marginTop: 6 }}>
                        {cp.big_idea.split("\n")[0]}
                      </div>
                    </div>
                  )}
                  {cp.culture_brief && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={styles.cardLabel}>Cultural Intelligence</div>
                      <div style={{ fontSize: 12, color: "#4a5568", lineHeight: 1.6, marginTop: 6 }}>
                        {cp.culture_brief.slice(0, 300)}...
                      </div>
                    </div>
                  )}
                  {cp.image_prompt && (
                    <div>
                      <div style={styles.cardLabel}>Image Prompt</div>
                      <div style={{ fontSize: 11, color: "#94a3b8", lineHeight: 1.6, marginTop: 6,
                        fontFamily: "monospace", background: "#f8fafc", padding: "8px 10px",
                        borderRadius: 6, border: "1px solid #e2e8f0" }}>
                        {cp.image_prompt.slice(0, 200)}...
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })()}

        {/* ── Creative Strategy ── */}
        {strategy && (strategy.hero_message || strategy.big_idea || strategy.strategic_framework) && (
          <div style={{ ...styles.resultCard, gridColumn: "1 / -1",
            background: "linear-gradient(135deg, #f0f7ff, #eff6ff)",
            border: "1px solid rgba(0,85,164,0.15)" }}>
            <div style={styles.cardHeader}>💡 Creative Strategy</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: "#0055A4",
              fontStyle: "italic", lineHeight: 1.4, marginBottom: 20,
              borderBottom: "1px solid #e2e8f0", paddingBottom: 16 }}>
              "{strategy.big_idea || strategy.hero_message}"
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
              {strategy.strategic_framework && (
                <div style={{ padding: "12px 14px", borderRadius: 10, background: "#ffffff", border: "1px solid #e2e8f0" }}>
                  <div style={styles.cardLabel}>Strategic Framework</div>
                  <div style={{ fontSize: 13, color: "#374151", lineHeight: 1.6, marginTop: 6 }}>{strategy.strategic_framework}</div>
                </div>
              )}
              {strategy.culture_context && (
                <div style={{ padding: "12px 14px", borderRadius: 10, background: "#ffffff", border: "1px solid #e2e8f0" }}>
                  <div style={styles.cardLabel}>Cultural Context</div>
                  <div style={{ fontSize: 13, color: "#374151", lineHeight: 1.6, marginTop: 6 }}>{strategy.culture_context}</div>
                </div>
              )}
              {strategy.handoff_message && (
                <div style={{ padding: "12px 14px", borderRadius: 10, background: "#ffffff", border: "1px solid #e2e8f0" }}>
                  <div style={styles.cardLabel}>Creative Brief</div>
                  <div style={{ fontSize: 13, color: "#374151", lineHeight: 1.6, marginTop: 6 }}>{strategy.handoff_message}</div>
                </div>
              )}
            </div>
            {strategy.messaging_pillars?.length > 0 && (
              <div style={{ marginTop: 16, display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
                {strategy.messaging_pillars.map((p: string, i: number) => (
                  <span key={i} style={{ fontSize: 12, padding: "5px 12px", borderRadius: 20,
                    background: "#e8f0fb", color: "#0055A4",
                    border: "1px solid rgba(0,85,164,0.2)" }}>{p}</span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Campaign Copy ── */}
        {copy && (copy.short || copy.medium || copy.long || copy.short_copy) && (
          <div style={{ ...styles.resultCard, gridColumn: "1 / -1" }}>
            <div style={styles.cardHeader}>✍️ Campaign Copy</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
              {/* Short */}
              {(copy.short?.headline || copy.short_copy) && (
                <div style={{ padding: "14px 16px", borderRadius: 12,
                  background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.15)" }}>
                  <div style={{ fontSize: 10, color: "#10b981", fontWeight: 700,
                    letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 8 }}>SHORT · OOH / KV</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: "#1a2332", lineHeight: 1.3 }}>
                    {copy.short?.headline || copy.short_copy}
                  </div>
                  {copy.short?.subline && <div style={{ fontSize: 13, color: "#64748b", marginTop: 6 }}>{copy.short.subline}</div>}
                </div>
              )}
              {/* Medium */}
              {(copy.medium?.headline || copy.medium_copy) && (
                <div style={{ padding: "14px 16px", borderRadius: 12,
                  background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.15)" }}>
                  <div style={{ fontSize: 10, color: "#3b82f6", fontWeight: 700,
                    letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 8 }}>MEDIUM · SOCIAL / DISPLAY</div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#1a2332", lineHeight: 1.4 }}>
                    {copy.medium?.headline || copy.medium_copy}
                  </div>
                  {copy.medium?.subline && <div style={{ fontSize: 13, color: "#64748b", marginTop: 6 }}>{copy.medium.subline}</div>}
                </div>
              )}
              {/* Long */}
              {(copy.long?.headline || copy.long_copy) && (
                <div style={{ padding: "14px 16px", borderRadius: 12,
                  background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.15)" }}>
                  <div style={{ fontSize: 10, color: "#f59e0b", fontWeight: 700,
                    letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 8 }}>LONG · PRESS / EDITORIAL</div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: "#1a2332", lineHeight: 1.4 }}>
                    {copy.long?.headline || copy.long_copy}
                  </div>
                  {copy.long?.body && <div style={{ fontSize: 13, color: "#4a5568", marginTop: 8, lineHeight: 1.7 }}>{copy.long.body}</div>}
                </div>
              )}
            </div>
            {/* CTA + Platform copy */}
            {(copy.cta || copy.instagram_caption || copy.tiktok_hook) && (
              <div style={{ marginTop: 16, display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
                {copy.cta && (
                  <div style={{ padding: "10px 14px", borderRadius: 10, background: "#f8fafc",
                    border: "1px solid #e2e8f0", textAlign: "center" as const }}>
                    <div style={styles.cardLabel}>CTA</div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: "#173563", marginTop: 4 }}>{copy.cta}</div>
                  </div>
                )}
                {copy.instagram_caption && (
                  <div style={{ padding: "10px 14px", borderRadius: 10, background: "#f8fafc",
                    border: "1px solid #e2e8f0" }}>
                    <div style={styles.cardLabel}>Instagram Caption</div>
                    <div style={{ fontSize: 12, color: "#374151", marginTop: 4, lineHeight: 1.5 }}>{copy.instagram_caption}</div>
                  </div>
                )}
                {copy.tiktok_hook && (
                  <div style={{ padding: "10px 14px", borderRadius: 10, background: "#f8fafc",
                    border: "1px solid #e2e8f0" }}>
                    <div style={styles.cardLabel}>TikTok Hook (3s)</div>
                    <div style={{ fontSize: 12, color: "#374151", marginTop: 4, lineHeight: 1.5 }}>{copy.tiktok_hook}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Raw output ── */}
        {output && (
          <div style={{ ...styles.resultCard, gridColumn: "1 / -1" }}>
            <button style={styles.expandBtn} onClick={() => setExpanded(e => !e)}>
              {expanded ? "▲ Hide" : "▼ Show"} full pipeline output
            </button>
            {expanded && <pre style={styles.jsonPre}>{JSON.stringify(output, null, 2)}</pre>}
          </div>
        )}

        {/* ── Distribute Campaign ── */}
        <DistributePanel output={output} campaignId={campaignId} />

      </div>
    </div>
  );
}

// ── Main App ─────────────────────────────────────────────────
export default function App() {
  const { state, startCampaign, startFullCampaign, reset } = usePipeline();

  if (state.status === "idle") {
    return <BriefForm onStart={startCampaign} onFullCampaign={startFullCampaign} />;
  }

  if (state.status === "running") {
    return <RunningView agentStatus={state.agentStatus} liveLog={state.liveLog} milestones={state.milestones} />;
  }

  if (state.status === "error") {
    const isAuthError = state.error?.includes("credentials") || state.error?.includes("auth");
    return (
      <div style={styles.errorPage}>
        <div style={styles.errorCard}>
          <div style={styles.errorTitle}>⚠️ Pipeline Error</div>
          <div style={styles.errorMsg}>{state.error}</div>
          {isAuthError && (
            <div style={styles.authHint}>
              <strong>Fix:</strong> Run this in your terminal, then restart the harness:
              <pre style={styles.authCmd}>gcloud auth application-default login</pre>
            </div>
          )}
          <button className="reset-btn" onClick={reset} style={{ marginTop: 20 }}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // done
  return (
    <ErrorBoundary>
      <ResultsView
        output={state.pipeline_output}
        campaignId={state.campaign_id}
        onReset={reset}
      />
    </ErrorBoundary>
  );
}

// ── Styles ───────────────────────────────────────────────────
const styles: Record<string, React.CSSProperties> = {
  // Running
  // ── Infosys Aster light theme ──────────────────────────────

  runningPage: {
    minHeight: "100vh", display: "flex", flexDirection: "column" as const,
    alignItems: "center", background: "#f4f6f9", padding: 0,
  },
  runningCard: {
    background: "#ffffff", border: "1px solid #e2e8f0",
    borderRadius: 16, padding: "40px 48px", maxWidth: 560, width: "100%",
    boxShadow: "0 4px 24px rgba(0,0,0,0.08)", marginTop: 40,
  },
  runningTitle: {
    fontSize: 22, fontWeight: 700, color: "#173563", marginBottom: 8,
  },
  runningSubtitle: {
    fontSize: 14, color: "#64748b", marginBottom: 32, lineHeight: 1.6,
  },
  stageList: { display: "flex", flexDirection: "column", gap: 12 },
  stageIcon: { fontSize: 20, width: 32, flexShrink: 0 },
  stageInfo: { flex: 1 },
  stageName: { fontSize: 13, fontWeight: 600, color: "#1a2332" },
  stageDesc: { fontSize: 12, color: "#94a3b8", marginTop: 2 },

  // Results
  resultsPage: {
    minHeight: "100vh", background: "#f4f6f9",
  },
  resultsHero: {
    background: "#ffffff",
    borderBottom: "1px solid #e2e8f0",
    padding: "20px 32px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
  },
  resultsHeroInner: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    maxWidth: 1200, margin: "0 auto",
  },
  resultsTitle: { fontSize: 18, fontWeight: 700, color: "#173563" },
  campaignIdTag: {
    fontSize: 11, color: "#94a3b8", marginTop: 3, fontFamily: "monospace",
    letterSpacing: "0.05em",
  },
  resultsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 20,
    maxWidth: 1200,
    margin: "24px auto",
    padding: "0 32px",
  },
  resultCard: {
    background: "#ffffff", border: "1px solid #e2e8f0",
    borderRadius: 14, padding: 22,
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
  },
  cardHeader: { fontSize: 14, fontWeight: 700, color: "#173563", marginBottom: 14 },
  cardRow: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  cardLabel: { fontSize: 11, color: "#94a3b8", fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "0.06em" },
  cardValue: { fontSize: 13, color: "#1a2332" },
  cardText: { fontSize: 13, color: "#4a5568", lineHeight: 1.6, marginTop: 12 },
  badge: {
    fontSize: 11, fontWeight: 700, padding: "3px 10px",
    borderRadius: 20, textTransform: "uppercase" as const,
  },
  bigIdea: {
    fontSize: 20, fontWeight: 700, color: "#0055A4",
    fontStyle: "italic", lineHeight: 1.5, marginBottom: 16,
  },
  copyGrid: { display: "flex", flexDirection: "column" as const, gap: 16 },
  copyBlock: {},
  copyLabel: { fontSize: 10, fontWeight: 700, color: "#94a3b8", textTransform: "uppercase" as const, marginBottom: 6, letterSpacing: "0.08em" },
  copyText: { fontSize: 14, color: "#1a2332", lineHeight: 1.6 },
  expandBtn: {
    background: "none", border: "none", color: "#94a3b8", fontSize: 12,
    cursor: "pointer", padding: 0, marginBottom: 12,
  },
  jsonPre: {
    fontSize: 11, color: "#4a5568", background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 8, padding: 16, overflowX: "auto" as const,
    whiteSpace: "pre-wrap" as const, maxHeight: 400, overflowY: "auto" as const,
  },

  // Error
  errorPage: {
    minHeight: "100vh", display: "flex", alignItems: "center",
    justifyContent: "center", background: "#f4f6f9",
  },
  errorCard: {
    background: "#ffffff", border: "1px solid #fecaca",
    borderRadius: 16, padding: 40, maxWidth: 480, textAlign: "center" as const,
    boxShadow: "0 4px 24px rgba(239,68,68,0.08)",
  },
  errorTitle: { fontSize: 20, fontWeight: 700, color: "#dc2626", marginBottom: 12 },
  errorMsg: { fontSize: 14, color: "#ef4444", lineHeight: 1.6 },
  authHint: { marginTop: 16, fontSize: 13, color: "#64748b", lineHeight: 1.6, textAlign: "left" as const },
  authCmd: { marginTop: 8, background: "#f1f5f9", border: "1px solid #e2e8f0", padding: "10px 14px", borderRadius: 8, fontSize: 12, color: "#0055A4", fontFamily: "monospace" },
};
