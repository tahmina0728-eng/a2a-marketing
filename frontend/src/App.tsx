import { useState, useMemo, useCallback, useEffect, Component, Fragment, type ReactNode, type ErrorInfo } from "react";

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

// ── Infosys Aster logo — top-left header (small, with "Powered by") ──
function AsterLogo({ size = 1 }: { size?: number }) {
  const w = 90 * size, h = 53 * size;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, userSelect: "none" as const }}>
      <span style={{ fontSize: 10 * size, color: "#94a3b8", fontWeight: 400,
        fontFamily: "'Inter',sans-serif", letterSpacing: "0.05em",
        textTransform: "uppercase" as const, whiteSpace: "nowrap" as const }}>
        Powered by
      </span>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 499.39 292.79"
        width={w} height={h} style={{ display: "block", flexShrink: 0 }}>
        <defs><style>{`.al1{fill:#004a85}.al2{fill:#221f1f}.al3,.al4{fill:#0c7ec2}.al4{fill-rule:evenodd}.al5{fill:#231f20}`}</style></defs>
        <path className="al2" d="M438.29,120.34l1.13-2.09s.04-.08.07-.13l-1.2,2.22"/>
        <g>
          <path className="al3" d="M444.83,32.23s0,0,0,0h0c.08.18.13.33.18.41l-.18-.43v.02"/>
          <polyline className="al4" points="132.5 12.96 132.5 .36 145.01 .36 145.01 104.33 132.5 104.33 132.5 12.96"/>
          <path className="al5" d="M372.98,119.68l1.11-2.04s.04-.08.07-.13l-1.17,2.17"/>
          <path className="al3" d="M363.11,43.19s0,0,0,0h0c.08.18.13.33.18.41l-.18-.43v.02"/>
          <path className="al3" d="M436.59,60.35c-13.67-6.78-18.31-8.21-18.18-15.96,0-10.32,8.44-13.44,15.45-13.44,7.99,0,13.03,2.96,20.07,8.08v-12.06c-5.72-1.99-10.49-2.78-16.93-2.75-12.98-.03-24.77,4.71-27.72,15.7l-16.11,39.82-1.66,5.01-1.47-5.01-12.75-31.02-4.21-10.33c-.03-.08-.07-.15-.1-.23h0c-.15-.35-.3-.74-.43-1.07l-4.16-10.25c-1.5-.41-3.34-.84-5.28-1.28h0s0,0,0,0c-4-.87-8.58-1.63-12.13-1.58-.53,0-1.12,0-1.68,0-15.02-.02-29.47,6.3-29.47,21.24,0,.87.05,1.68.1,2.48-6.02-14.3-19-24.2-34.06-24.2h-.44c-1.65.03-3.28.18-4.92.43h-42.3c-1.73-10.71,3.24-16.8,10.73-16.8,9.43,0,13.49,2.8,17.57,6.58,0,0,.28,0,.41.03,0,0,0-.49.02-1.25V2.12C264.26.9,259.57,0,251.07,0,237.94,0,228.49,8.64,227.16,23.94h-10.1v7.57h9.97v60.2c0,.23,0,.43-.03.63v11.98h11.32V31.52h25.44c-9.41,7.62-15.53,20.01-15.53,34.01,0,23.05,16.61,41.76,37.18,42.02h0c.15,0,.31,0,.44,0,20.77,0,37.6-18.81,37.6-42.02,0-2.75-.25-5.45-.71-8.08,3.75,6.02,10.89,8.95,20.5,13.1,11.34,4.8,17.69,8.97,17.69,16.12,0,8.59-8.11,13.03-17.21,12.98-8.9,0-15.86-3.62-23.61-10.66v13.49c4.71,3.04,12.05,4.79,19.96,4.79,6.12-.02,16.14-1.37,23.02-7.19h0,0c4.36-3.7,7.45-9.18,7.45-17.23-.03-6.66-2.98-11.3-7.45-14.89h0s0,0,0,0c-3.92-3.19-8.97-5.56-14.22-7.85-13.66-6.78-18.87-8.18-18.72-15.96,0-10.33,8.97-13.44,15.99-13.44,3.05,0,5.68.43,8.16,1.28,4.62,1.73,6.15,5.17,7.77,8.89.49,1.15.82,1.89,1.02,2.32v-.02s-.27-.64-.27-.64l.27.61h0s0,0,0,0h0s0,0,0,0c.18.43.39.9.18.46l9.69,23.38,11.65,28.12c-3.6,8.21-7.62,16.8-10.41,22.26l-.07.15-.07.13c-.41.77-.77,1.49-1.11,2.12-.43.84-.83,1.56-1.14,2.09l-2.63,4.89h11.1c4.84-10.7,25.39-60.75,29.8-71.51,2.9,7.75,10.02,10.86,20.85,15.55,11.35,4.79,17.7,8.97,17.7,16.14,0,8.56-8.11,13.02-17.22,12.95-9.25,0-16.42-3.91-24.5-11.48l-.74-.58v13.72c4.53,3.77,12.69,5.97,21.59,5.97,9.97-.02,30.47-3.62,30.47-24.43-.05-12.47-10.43-17.85-21.67-22.72M286,100.23h-.58c-13.93-.18-25.37-15.12-25.7-33.76-.34-18.92,10.91-34.45,25.12-34.68.2-.03.41-.03.58,0,13.94.15,25.4,15.12,25.7,33.76.33,18.89-10.91,34.43-25.12,34.68Z"/>
          <path className="al4" d="M168.37,24.71l.13,9.1v.61h.12c.13-.38.33-.71.51-.94,4.62-4.94,10.4-9.82,24.17-9.82s21.69,11.2,22.05,18.23v49.82s0,12.62,0,12.62h-11.29v-57.29c0-8.77-7.71-15.12-17.17-15.12-7.82,0-17.92,7.06-18.25,14.2v45.61l.03.34v12.26h-11.32l.03-12.59-.03-56.55.03-10.48h10.99"/>
          <path className="al1" d="M305.92,274.48h2.15s0,16.62,0,16.62h-.96c-31.77.02-56.86-25.22-56.86-56.88v-94.99h16.28v41.56h41.53v16.54h-41.53v34.86c0,28.68,21.99,42.4,39.39,42.29"/>
          <path className="al1" d="M96.83,234.71c.11-20.29-14.44-40.63-40.14-40.73-23.13-.09-39.8,18.24-40.27,39.49-.45,20.48,15.05,40.8,39.97,41.01,22.85.19,40.32-17.46,40.44-39.76M0,234.4c-.01-30.66,24.28-56.85,56.58-57,14.94-.07,29.72,6,40.48,16.66v-12.86h16.28v108.39h-16.28v-15.05c-10.45,10.4-24.86,16.57-40.19,16.58C23.02,291.12.02,263.69,0,234.4Z"/>
          <path className="al1" d="M337.27,244.85c4.68,17.93,18.9,29.42,35.46,29.42,12.67,0,24.55-6.63,30.79-18.12h20.27c-8.38,22.21-28.64,36.63-51.83,36.63-30.4,0-54.95-26.89-54.95-55.73,0-34.1,25.72-57.87,54.37-57.87,31.76,0,55.92,24.55,55.92,55.54,0,3.31,0,6.43-.58,10.13h-89.44ZM407.03,229.26c-1.56-18.32-17.73-31.57-35.07-31.57s-33.13,13.06-34.69,31.57h69.76Z"/>
          <path className="al1" d="M443.53,288.88v-111.31h16.55v11.91h.34c4.27-7.3,26.51-10.83,38.97-11.62v19.9c-15.35.59-38.11-.12-38.11,29.78v61.34h-17.74Z"/>
          <path className="al1" d="M166.97,225.99h-6.88c-8.84,0-16.07-7.23-16.07-16.07h0c0-8.84,7.23-16.07,16.07-16.07h43.53c8.84,0,16.07,7.23,16.07,16.07h0s15.78-.19,15.78-.19v-2.94c0-15.61-12.77-28.39-28.39-28.39h-50.44c-15.61,0-28.39,12.77-28.39,28.39v6.26c0,15.61,12.77,28.39,28.39,28.39h8.6l5.08-.05h33.3c8.84,0,16.07,7.23,16.07,16.07h0c0,8.84-7.23,16.07-16.07,16.07h-43.53c-8.84,0-16.07-7.23-16.07-16.07h0l-15.78.19v2.94c0,15.61,12.77,28.39,28.39,28.39h50.44c15.61,0,28.39-12.77,28.39-28.39v-6.26c0-15.61-12.77-28.39-28.39-28.39h-35.92l-4.18.05Z"/>
        </g>
      </svg>
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
  { id: "Rnorr",   label: "Rnorr",   emoji: "🥣", logo: "/brands/rnorr-logo.png"   },
  { id: "Sunglow", label: "Sunglow", emoji: "✨", logo: "/brands/sunglow-logo.png" },
  { id: "Boozt",   label: "Boozt",   emoji: "💨", logo: "/brands/boozt-logo.png"   },
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
  { id: "Google Ads", icon: "🔍", label: "Google Ads" },
  { id: "Meta Ads",   icon: "📘", label: "Meta Ads" },
  { id: "Website",    icon: "🌐", label: "Website" },
  { id: "Email",      icon: "📧", label: "Email" },
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

// ── A2A orb gradient — matches the brand logo PNG ─────────────
// White glass highlight top-right, hot pink/magenta centre, lavender-purple edges
const ORB_BG = [
  "radial-gradient(circle at 71% 26%, rgba(255,255,255,0.88) 0%, rgba(255,255,255,0) 42%)",
  "radial-gradient(circle at 36% 54%, #f028cc 0%, #cc3cf2 26%, #8840e0 52%, #b898f8 80%, #ddd6fe 100%)",
].join(", ");


// ── Harness pipeline agents (for loading display) ────────────
// Order matches actual backend execution
const HARNESS_STAGES = [
  { key: "briefing", icon: "📋", label: "Logos",    desc: "Validating brief & Fan Truth score" },
  { key: "strategy", icon: "💡", label: "Helia",    desc: "Building big idea & strategy" },
  { key: "copy",     icon: "✍️", label: "Ideon",    desc: "Writing campaign copy variants" },
  { key: "culture",  icon: "🌍", label: "Aether",   desc: "Researching cultural intelligence" },
  { key: "kv",       icon: "🎨", label: "Morphis",  desc: "Generating key visual with Gemini 3 Pro Image" },
  { key: "reel",     icon: "🎬", label: "Kinetik",  desc: "Generating 6s campaign reel with Veo" },
  { key: "channel",  icon: "📡", label: "Poly",     desc: "Publishing to Instagram, TikTok & more" },
];

// ── Brief Form (6-step wizard) ───────────────────────────────
function BriefForm({ onFullCampaign }: {
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
                  <div className="goal-tile-icon">
                    <img src={b.logo} alt={b.label}
                      style={{ height: 40, maxWidth: "100%", objectFit: "contain", display: "block" }} />
                  </div>
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
    <div style={{ flex: 1, overflowY: "auto" as const }}>
    <div style={{ minHeight: "100%", display: "flex", alignItems: "center",
      justifyContent: "center", padding: "48px" }}>
      <div style={{ maxWidth: 640, width: "100%" }}>
        <div key={step} className="step-content">{stepContent()}</div>
        <div className="wizard-nav">
          {step > 0
            ? <button className="wizard-back-btn" onClick={() => setStep((s) => s - 1)}>← Back</button>
            : <div />}
          {step < TOTAL_STEPS
            ? <button className="wizard-next-btn" disabled={!canProceed()} onClick={() => setStep((s) => s + 1)}>
                {step === TOTAL_STEPS - 1 ? "Review →" : "Continue →"}
              </button>
            : <button className="wizard-launch-btn" disabled={!canProceed()} onClick={handleFullLaunch}>
                🚀 Generate AI Campaign
              </button>}
        </div>
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

      {/* Channel-specific copy — dynamic from whatever was selected */}
      {(() => {
        const channelCopy = m.channel_copy as Record<string, string> | null | undefined;
        if (!channelCopy || Object.keys(channelCopy).length === 0) return null;
        const COPY_CFG: Record<string, { icon: string; color: string; bg: string; border: string; label: string }> = {
          instagram_caption: { icon: "📸", color: "#7c3aed", bg: "#fdf4ff", border: "#e9d5ff", label: "Instagram" },
          tiktok_hook:       { icon: "🎵", color: "#be185d", bg: "#fff0f6", border: "#ffd6e7", label: "TikTok Hook" },
          youtube_script:    { icon: "▶️", color: "#dc2626", bg: "#fff1f2", border: "#fecdd3", label: "YouTube" },
          google_headline:   { icon: "🔍", color: "#1967d2", bg: "#eff6ff", border: "#bfdbfe", label: "Google Ads" },
          meta_caption:      { icon: "📘", color: "#1877f2", bg: "#eff6ff", border: "#dbeafe", label: "Meta Ads" },
          ooh_headline:      { icon: "🏙️", color: "#d97706", bg: "#fffbeb", border: "#fde68a", label: "OOH" },
          web_headline:      { icon: "🌐", color: "#059669", bg: "#f0fdf4", border: "#86efac", label: "Website" },
          email_subject:     { icon: "📧", color: "#0369a1", bg: "#f0f9ff", border: "#bae6fd", label: "Email" },
        };
        const entries = Object.entries(m.channel_copy as Record<string, string>);
        return (
          <div style={{ display: "grid", gridTemplateColumns: entries.length > 1 ? "1fr 1fr" : "1fr", gap: 8 }}>
            {entries.map(([key, val]) => {
              const cfg = COPY_CFG[key] ?? { icon: "📢", color: "#64748b", bg: "#f8fafc", border: "#e2e8f0", label: key };
              return (
                <div key={key} style={{ padding: "9px 11px", borderRadius: 10, background: cfg.bg, border: `1px solid ${cfg.border}` }}>
                  <div style={{ fontSize: 9, fontWeight: 700, color: cfg.color, textTransform: "uppercase" as const, letterSpacing: "0.1em", marginBottom: 4 }}>
                    {cfg.icon} {cfg.label}
                  </div>
                  <div style={{ fontSize: 11, color: cfg.color, lineHeight: 1.4 }}>
                    {val.slice(0, 90)}{val.length > 90 ? "…" : ""}
                  </div>
                </div>
              );
            })}
          </div>
        );
      })()}
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
  const raw = String(m?.brief ?? "");
  if (!raw) return null;
  // Strip markdown: **bold**, ## headers, leading bullets
  const clean = raw
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/^#+\s*/gm, "")
    .replace(/^[-*]\s*/gm, "")
    .trim();
  // Split on sentence boundaries, filter out short/empty fragments
  const sentences = clean
    .split(/(?<=[.!?])\s+/)
    .map(s => s.trim())
    .filter(s => s.length > 25)
    .slice(0, 4);
  if (sentences.length === 0) return null;
  return (
    <div style={{ width: "100%" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "#0d9488", letterSpacing: "0.09em",
        textTransform: "uppercase" as const, marginBottom: 10 }}>Cultural Intelligence Brief</div>
      {sentences.map((s, i) => (
        <div key={i} style={{ display: "flex", gap: 10, marginBottom: 10, padding: "10px 12px",
          borderRadius: 10, background: i === 0 ? "#f0fdfa" : "#f8fafc",
          border: `1px solid ${i === 0 ? "#99f6e4" : "#e2e8f0"}` }}>
          <span style={{ fontSize: 14, flexShrink: 0 }}>{["🌍", "💫", "🎯", "⚡"][i]}</span>
          <span style={{ fontSize: 12, color: "#1a2332", lineHeight: 1.5 }}>
            {s}{s.slice(-1).match(/[.!?]/) ? "" : "."}
          </span>
        </div>
      ))}
    </div>
  );
}

function KVPanel({ m, liveMsg, reelMilestone }: { m?: Record<string,unknown>; liveMsg: string|null; reelMilestone?: Record<string,unknown> }) {
  const [selectedImg, setSelectedImg] = useState(0);
  const brandLocks  = m?.brand_locks  ? String(m.brand_locks)  : "";
  const bigIdea     = m?.big_idea     ? String(m.big_idea)     : "";
  const imagePrompt = m?.image_prompt ? String(m.image_prompt) : "";
  const imageB64    = m?.image_b64    ? String(m.image_b64)    : "";
  const imagesB64   = m?.images_b64   ? (m.images_b64 as string[]) : imageB64 ? [imageB64] : [];
  const videoB64    = reelMilestone?.video_b64 ? String(reelMilestone.video_b64) : "";

  const activeStep = imagesB64.length > 0 ? 4 : imagePrompt ? 3 : bigIdea ? 2 : brandLocks ? 1 : 0;
  const isGeneratingImg = imagesB64.length === 0 && (liveMsg?.toLowerCase().includes("imagen") || !!imagePrompt);

  const KV_STEPS = [
    {
      icon: "🔒",
      labelWaiting:  "Brand Locks",
      labelActive:   "Brand Locks Extracting...",
      labelDone:     "Brand Locks Extracted",
      content: brandLocks,
    },
    {
      icon: "💡",
      labelWaiting:  "Big Idea",
      labelActive:   "Big Idea Developing...",
      labelDone:     "Big Idea Developed",
      content: bigIdea,
    },
    {
      icon: "🖼️",
      labelWaiting:  "Image Prompt",
      labelActive:   "Image Prompt Crafting...",
      labelDone:     "Image Prompt Crafted",
      content: imagePrompt,
    },
    {
      icon: "✨",
      labelWaiting:  "Key Visual",
      labelActive:   "Key Visual Generating...",
      labelDone:     imagesB64.length > 1 ? `${imagesB64.length} Variations Generated` : "Key Visual Generated",
      content: imagesB64.length > 0 ? imagesB64[0] : "",
    },
  ];

  return (
    <div style={{ width: "100%" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "#7c3aed", letterSpacing: "0.09em",
        textTransform: "uppercase" as const, marginBottom: 12 }}>Image Generation Pipeline</div>

      {/* 2×2 card grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        {KV_STEPS.map((step, i) => {
          const isDone   = i < activeStep || (i === 3 && imagesB64.length > 0);
          const isActive = !isDone && (i === activeStep || (i === 3 && isGeneratingImg));
          const label    = isDone ? step.labelDone : isActive ? step.labelActive : step.labelWaiting;

          return (
            <div key={i} className={isDone || isActive ? "msg-fade" : ""} style={{
              borderRadius: 12,
              background: isDone ? "white" : isActive ? "#faf5ff" : "#f8fafc",
              border: `1.5px solid ${isDone ? "#ede9fe" : isActive ? "#ddd6fe" : "#e2e8f0"}`,
              padding: "14px 14px",
              display: "flex", flexDirection: "column" as const, gap: 8,
            }}>
              {/* Card header */}
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 20, flexShrink: 0 }}>{step.icon}</span>
                <span style={{ fontSize: 12, fontWeight: isDone || isActive ? 700 : 500, flex: 1,
                  color: isDone ? "#7c3aed" : isActive ? "#7c3aed" : "#94a3b8", lineHeight: 1.3 }}>
                  {label}
                </span>
                {isDone && (
                  <span style={{ color: "#7c3aed", fontWeight: 800, fontSize: 14, flexShrink: 0 }}>✓</span>
                )}
                {isActive && (
                  <div style={{ display: "flex", gap: 3, flexShrink: 0 }}>
                    {[0,1,2].map(d => (
                      <span key={d} className="source-dot"
                        style={{ animationDelay: `${d * 0.2}s`, background: "#7c3aed" }} />
                    ))}
                  </div>
                )}
              </div>

              {/* Card content — only shown when done */}
              {isDone && step.content && (
                <div style={{ marginTop: 2 }}>
                  {i === 3 && imagesB64.length > 0 ? (
                    <div>
                      <img src={`data:image/jpeg;base64,${imagesB64[selectedImg]}`} alt="Key visual"
                        style={{ width: "100%", borderRadius: 8, display: "block",
                          marginBottom: imagesB64.length > 1 ? 6 : 0 }} />
                      {imagesB64.length > 1 && (
                        <>
                          <div style={{ display: "flex", gap: 4 }}>
                            {imagesB64.map((img, idx) => (
                              <div key={idx} onClick={() => setSelectedImg(idx)}
                                style={{ flex: 1, cursor: "pointer", borderRadius: 4, overflow: "hidden",
                                  border: `2px solid ${idx === selectedImg ? "#7c3aed" : "transparent"}`,
                                  opacity: idx === selectedImg ? 1 : 0.55, transition: "all 0.2s" }}>
                                <img src={`data:image/jpeg;base64,${img}`} alt={`v${idx + 1}`}
                                  style={{ width: "100%", display: "block" }} />
                              </div>
                            ))}
                          </div>
                          <div style={{ fontSize: 10, color: "#7c3aed", fontWeight: 600, marginTop: 4,
                            textAlign: "center" as const }}>
                            Variation {selectedImg + 1} / {imagesB64.length} · click to select
                          </div>
                        </>
                      )}
                    </div>
                  ) : (
                    <div style={{ fontSize: 11, color: "#374151", lineHeight: 1.6,
                      display: "-webkit-box", WebkitLineClamp: 3,
                      WebkitBoxOrient: "vertical" as any, overflow: "hidden" }}>
                      {step.content.replace(/\*\*/g, "").replace(/^#+\s*/gm, "").slice(0, 160)}
                      {step.content.length > 160 ? "…" : ""}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

    {/* Campaign Reel video player */}
    {videoB64 && (
      <div style={{ marginTop: 16, padding: "14px 16px", background: "#0f172a", borderRadius: 12 }}>
        <div style={{ fontSize: 11, fontWeight: 800, color: "#f59e0b", letterSpacing: "0.1em",
          textTransform: "uppercase" as const, marginBottom: 10 }}>🎬 Campaign Reel · 6s</div>
        <video controls autoPlay loop muted playsInline
          style={{ width: "100%", borderRadius: 8, display: "block" }}
          src={`data:video/mp4;base64,${videoB64}`} />
        <a href={`data:video/mp4;base64,${videoB64}`} download={`campaign-reel.mp4`}
          style={{ display: "inline-block", marginTop: 10, fontSize: 11, fontWeight: 700,
            color: "#f59e0b", textDecoration: "none" }}>
          ⬇ Download Reel
        </a>
      </div>
    )}
    </div>
  );
}

// ── Running view (pipeline in progress) ─────────────────────
function RunningView({
  agentStatus,
  liveLog,
  milestones,
  compact = false,
}: {
  agentStatus: Record<string, string>;
  liveLog: AgentEvent[];
  milestones: Record<string, Record<string, unknown>>;
  compact?: boolean;
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
    <div style={{ display: "flex", height: compact ? "100%" : "100vh", overflow: "hidden", fontFamily: "Inter,sans-serif" }}>

      {/* ── LEFT: step sidebar — hidden in compact/3-panel mode ── */}
      <div style={{ width: 340, flexShrink: 0, background: "#fff", borderRight: "1px solid #e2e8f0",
        display: compact ? "none" : "flex", flexDirection: "column", padding: "28px 20px", overflowY: "auto" as const }}>

        {/* Logo */}
        <div style={{ marginBottom: 28 }}><AsterLogo /></div>

        {/* Progress bar */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", letterSpacing: "0.09em",
            textTransform: "uppercase" as const, marginBottom: 6 }}>Agents Activating</div>
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
          // Phase 1: agent running, no milestone data yet → large pulsing orb
          (displayMode === "running" && !milestones[displayKey ?? ""]) ? (
            <div key={`orb-${displayKey}`} style={{
              position: "relative" as const, zIndex: 2,
              display: "flex", flexDirection: "column" as const,
              alignItems: "center", justifyContent: "center", gap: 28,
            }}>
              <div style={{
                width: 90, height: 90, borderRadius: "50%",
                background: ORB_BG,
                boxShadow: "0 8px 32px rgba(200,40,200,0.32)",
                display: "flex", alignItems: "center", justifyContent: "center",
                animation: "icon-breathe 2.5s ease-in-out infinite",
              }}>
                <svg width={34} height={34} viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L13.8 10.2L22 12L13.8 13.8L12 22L10.2 13.8L2 12L10.2 10.2Z" fill="white" />
                </svg>
              </div>
              <div style={{ textAlign: "center" as const }}>
                <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.12em",
                  color: v.g1, textTransform: "uppercase" as const, marginBottom: 8 }}>
                  {stage?.label ?? "Agent"} · Running
                </div>
                <div style={{ fontSize: 20, fontWeight: 600, color: "#374151", letterSpacing: "-0.01em" }}>
                  Generating ...
                </div>
              </div>
            </div>
          ) : (
          // Phase 2/3: milestone present or agent done → spotlight card with results
          <div key={displayKey ?? "idle"} className="spotlight-card" style={{
            position: "relative" as const, zIndex: 2,
            background: "rgba(255,255,255,0.82)",
            backdropFilter: "blur(28px)", WebkitBackdropFilter: "blur(28px)",
            border: `1.5px solid ${v.g1}28`,
            borderRadius: 24, padding: "28px 30px",
            width: displayKey === "kv" ? "min(680px, 92%)" : "min(580px, 92%)",
            maxHeight: "80vh", overflowY: "auto" as const,
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
              {displayKey === "strategy" && <StrategyPanel m={milestones.strategy} />}
              {displayKey === "copy" && <CopyPanel m={milestones.copy} />}
              {displayKey === "culture" && <CulturePanel m={milestones.culture} />}
              {displayKey === "kv" && <KVPanel m={milestones.kv} liveMsg={liveMsg} reelMilestone={milestones.reel as Record<string,unknown> | undefined} />}
              {displayKey === "channel" && <ChannelPanel m={milestones.channel} liveMsg={liveMsg} />}
            </div>
          </div>
          )
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
                Agents Activating...
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

const PUBLISH_CHANNEL_CFG: Record<string, { icon: string; color: string; bg: string; border: string; desc: string; publishKey: string }> = {
  "Instagram":  { icon: "📸", color: "#c026d3", bg: "#fdf4ff", border: "#e9d5ff", desc: "Feed + Stories post",   publishKey: "instagram" },
  "TikTok":     { icon: "🎵", color: "#0f172a", bg: "#f1f5f9", border: "#cbd5e1", desc: "Short-form video",       publishKey: "tiktok"    },
  "YouTube":    { icon: "▶️", color: "#dc2626", bg: "#fff1f2", border: "#fecdd3", desc: "Pre-roll ad",            publishKey: "youtube"   },
  "OOH":        { icon: "🏙️", color: "#d97706", bg: "#fffbeb", border: "#fde68a", desc: "Digital billboard",     publishKey: "ooh"       },
  "Google Ads": { icon: "🔍", color: "#1967d2", bg: "#eff6ff", border: "#bfdbfe", desc: "Responsive Search Ad",  publishKey: "google_ads"},
  "Meta Ads":   { icon: "📘", color: "#1877f2", bg: "#eff6ff", border: "#dbeafe", desc: "FB + Instagram Ad",     publishKey: "meta_ads"  },
  "Website":    { icon: "🌐", color: "#059669", bg: "#f0fdf4", border: "#86efac", desc: "Opens brand website",   publishKey: "landing_page"},
  "Email":      { icon: "📧", color: "#0369a1", bg: "#f0f9ff", border: "#bae6fd", desc: "Branded email blast",   publishKey: "email"     },
};

function DistributePanel({ output, campaignId, selectedImageB64 }: {
  output: Record<string, unknown> | null; campaignId: string | null; selectedImageB64?: string;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [email,    setEmail]    = useState("d.hendon17@gmail.com");
  const [loading,  setLoading]  = useState(false);
  const [published, setPublished] = useState(false);
  const [results,  setResults]  = useState<Record<string, any> | null>(null);
  const [error,    setError]    = useState("");
  const [landingUrl, setLandingUrl] = useState<string>(() => {
    // Restore persisted landing URL for this campaign on mount
    return campaignId ? localStorage.getItem(`landing_url_${campaignId}`) ?? "" : "";
  });

  const cp       = (output as any)?.creative_pipeline;
  const strategy = (output as any)?.creative_strategy;
  const copy     = (output as any)?.campaign_copy;
  const brief    = (output as any)?.machine_brief ?? output as any;
  const brandFromId = campaignId ? campaignId.replace(/^campaign-/, "").split("-")[0].replace(/^(.)/, (c: string) => c.toUpperCase()) : "";
  const brand    = String((output as any)?.brand ?? brandFromId ?? "");

  // Channels from brief — try multiple locations in the output tree
  const _rawCh = brief?.channels
    ?? (output as any)?.channels
    ?? (brief as any)?.structured_brief?.channels;
  const wizardChannels: string[] = Array.isArray(_rawCh)
    ? _rawCh
    : typeof _rawCh === "string"
      ? (() => { try { const p = JSON.parse(_rawCh); return Array.isArray(p) ? p : [_rawCh]; } catch { return []; } })()
      : [];
  // Always show all channels — fall back to full list if brief data is absent
  const displayChannels: string[] = wizardChannels.length > 0
    ? wizardChannels
    : Object.keys(PUBLISH_CHANNEL_CFG);

  const toggle = (key: string) => setSelected(s => { const n = new Set(s); n.has(key) ? n.delete(key) : n.add(key); return n; });

  const handlePublish = useCallback(async () => {
    if (selected.size === 0) return;
    if (!campaignId) { setError("No campaign ID"); return; }
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
          // Email-channel specific copy from copy agent
          email_subject:   (copy as any)?.channel_copy?.email_subject ?? copy?.short?.headline ?? "",
          // Product name for email footer / product spotlight
          product_name:    String((output as any)?.product_name ?? brief?.structured_brief?.product ?? ""),
          // KV image — use explicitly selected variation first
          image_b64:       selectedImageB64 ?? cp?.images_b64?.[0] ?? cp?.image_b64 ?? "",
          to_email:        selected.has("email") ? email : "",
          channels:        Array.from(selected),
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? "Publish failed");
      setResults(json.results); setPublished(true);
      // Persist landing page URL so it survives navigation / page reload
      const _lpResult = json.results?.landing_page;
      if (_lpResult?.url && campaignId) {
        const _fullUrl = `${API_BASE_PUB}${_lpResult.url}`;
        localStorage.setItem(`landing_url_${campaignId}`, _fullUrl);
        setLandingUrl(_fullUrl);
      }
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [campaignId, brand, strategy, copy, cp, email, selected, selectedImageB64]);

  if (!strategy && !cp?.culture_brief) return null;

  const publishedCount = results ? Object.values(results).filter((r: any) => r.status !== "skipped" && r.status !== "error").length : 0;

  return (
    <div style={{ borderRadius: 20, overflow: "hidden", border: "1px solid #ede9fe",
      boxShadow: "0 4px 24px rgba(124,58,237,0.10)" }}>
      {/* Purple/white header */}
      <div style={{ background: "linear-gradient(135deg, #faf5ff 0%, #f5f3ff 60%, #ede9fe 100%)",
        padding: "32px 36px 28px", position: "relative", overflow: "hidden",
        borderBottom: "1px solid #ede9fe" }}>
        {/* Decorative orb shapes */}
        <div style={{ position: "absolute", top: -50, right: -50, width: 200, height: 200,
          borderRadius: "50%", background: "rgba(167,139,250,0.12)", pointerEvents: "none" as const }} />
        <div style={{ position: "absolute", bottom: -30, left: -30, width: 140, height: 140,
          borderRadius: "50%", background: "rgba(196,132,252,0.08)", pointerEvents: "none" as const }} />

        <div style={{ position: "relative", zIndex: 1 }}>
          <div style={{ fontSize: 10, fontWeight: 800, color: "#7c3aed", letterSpacing: "0.18em",
            textTransform: "uppercase" as const, marginBottom: 8 }}>
            Final Step
          </div>
          <div style={{ fontSize: 26, fontWeight: 900, color: "#3b0764", lineHeight: 1.2, marginBottom: 6 }}>
            {published ? `✅ Live on ${publishedCount} channel${publishedCount !== 1 ? "s" : ""}` : "🚀 Launch Campaign"}
          </div>
          <div style={{ fontSize: 13, color: "#6b7280", marginBottom: published ? 0 : 24 }}>
            {published ? "Your campaign is now live. Track performance in your dashboards." : `Select channels to activate — ${displayChannels.length} available`}
          </div>

          {/* Channel selection chips */}
          {!published && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" as const }}>
              {displayChannels.map(ch => {
                const cfg = PUBLISH_CHANNEL_CFG[ch];
                if (!cfg) return null;
                const isOn = selected.has(cfg.publishKey);
                return (
                  <div key={ch} onClick={() => toggle(cfg.publishKey)}
                    style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 16px",
                      borderRadius: 12, cursor: "pointer", transition: "all 0.2s",
                      background: isOn ? "#7c3aed" : "white",
                      border: `1.5px solid ${isOn ? "#7c3aed" : "#ede9fe"}`,
                      boxShadow: isOn ? "0 0 0 3px rgba(124,58,237,0.12)" : "0 1px 4px rgba(0,0,0,0.05)" }}>
                    <span style={{ fontSize: 18 }}>{cfg.icon}</span>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: isOn ? "white" : "#374151" }}>{ch}</div>
                      <div style={{ fontSize: 9, color: isOn ? "rgba(255,255,255,0.65)" : "#9ca3af" }}>{cfg.desc}</div>
                    </div>
                    <div style={{ width: 18, height: 18, borderRadius: "50%", marginLeft: 4, flexShrink: 0,
                      background: isOn ? "rgba(255,255,255,0.25)" : "#f5f3ff",
                      border: `2px solid ${isOn ? "rgba(255,255,255,0.5)" : "#ddd6fe"}`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 10, color: isOn ? "white" : "#9ca3af", fontWeight: 800 }}>
                      {isOn ? "✓" : ""}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Action bar */}
      {!published && (
        <div style={{ padding: "16px 36px", background: "white", display: "flex",
          alignItems: "center", gap: 16, borderTop: "1px solid #f3f4f6" }}>
          {/* Selected image thumbnail */}
          {selectedImageB64 && (
            <div style={{ flexShrink: 0, position: "relative" as const }}>
              <img src={`data:image/jpeg;base64,${selectedImageB64}`} alt="Selected key visual"
                style={{ width: 48, height: 48, objectFit: "cover" as const, borderRadius: 8,
                  border: "2px solid #ede9fe", display: "block" }} />
              <div style={{ position: "absolute" as const, top: -4, right: -4, width: 15, height: 15,
                borderRadius: "50%", background: "#7c3aed", border: "2px solid white",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 8, color: "white", fontWeight: 800, lineHeight: 1 }}>✓</div>
            </div>
          )}
          {selected.has("email") && (
            <input type="email" placeholder="Recipient email address" value={email} onChange={e => setEmail(e.target.value)}
              style={{ flex: 1, padding: "10px 14px", borderRadius: 10, border: "1.5px solid #ddd6fe",
                background: "#faf5ff", color: "#374151", fontSize: 13, fontFamily: "inherit", outline: "none" }} />
          )}
          {selected.size === 0 ? (
            <div style={{ flex: 1, fontSize: 13, color: "#9ca3af", fontStyle: "italic" }}>
              Select channels above to enable launch
            </div>
          ) : (
            <div style={{ flex: 1, fontSize: 13, color: "#7c3aed", fontWeight: 500 }}>
              {selected.size} channel{selected.size > 1 ? "s" : ""} selected
            </div>
          )}
          <button onClick={handlePublish} disabled={loading || selected.size === 0}
            style={{ padding: "12px 28px", borderRadius: 12, border: "none",
              cursor: selected.size === 0 ? "not-allowed" : "pointer",
              background: selected.size === 0
                ? "#f5f3ff"
                : ORB_BG,
              color: selected.size === 0 ? "#9ca3af" : "white",
              fontSize: 13, fontWeight: 800, letterSpacing: "0.02em", transition: "all 0.2s",
              boxShadow: selected.size > 0 ? "0 4px 20px rgba(124,58,237,0.35)" : "none" }}>
            {loading ? "Launching…" : selected.size === 0 ? "Select Channels" : `🚀 Launch to ${selected.size} Channel${selected.size > 1 ? "s" : ""}`}
          </button>
        </div>
      )}

      {/* Published results */}
      {/* Persistent landing page URL banner — always visible once created */}
      {landingUrl && (
        <div style={{ padding: "16px 40px", background: "linear-gradient(90deg,#ecfdf5,#f0fdf4)", borderTop: "1.5px solid #86efac", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 20 }}>🌐</span>
            <div>
              <div style={{ fontSize: 12, fontWeight: 800, color: "#065f46", letterSpacing: "0.08em", textTransform: "uppercase" }}>Landing Page Live</div>
              <div style={{ fontSize: 12, color: "#475569", marginTop: 2, wordBreak: "break-all" }}>{landingUrl}</div>
            </div>
          </div>
          <a href={landingUrl} target="_blank" rel="noreferrer"
            style={{ background: "#059669", color: "white", padding: "10px 24px", borderRadius: 99, fontWeight: 700, fontSize: 13, whiteSpace: "nowrap", textDecoration: "none" }}>
            Open Website →
          </a>
        </div>
      )}

      {published && results && (
        <div style={{ padding: "24px 40px", background: "#f0fdf4", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
          {Object.entries(results).map(([key, r]: [string, any]) => {
            const isDone = r.status !== "skipped" && r.status !== "error";
            return (
              <div key={key} style={{ padding: "14px 16px", borderRadius: 12, background: isDone ? "white" : "#f8fafc",
                border: `1.5px solid ${isDone ? "#86efac" : "#e2e8f0"}` }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: isDone ? "#065f46" : "#94a3b8", marginBottom: 4 }}>
                  {isDone ? "✅" : "⏭"} {key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
                </div>
                {key === "email" && r.to && <div style={{ fontSize: 10, color: "#64748b" }}>Sent to {r.to}</div>}
                {r.ad_id && <div style={{ fontSize: 10, color: "#64748b" }}>ID: {r.ad_id}</div>}
              </div>
            );
          })}
        </div>
      )}

      {error && (
        <div style={{ padding: "12px 40px", background: "#fef2f2", fontSize: 12, color: "#991b1b",
          borderTop: "1px solid #fecaca" }}>{error}</div>
      )}
    </div>
  );
}
// ── Results view ─────────────────────────────────────────────
function ResultsView({ output, campaignId }: {
  output: Record<string, unknown> | null;
  campaignId: string | null;
}) {
  const [expanded, setExpanded] = useState(false);
  const [selectedKV, setSelectedKV] = useState(0);
  const brief    = output as any;
  const strategy = output?.creative_strategy as any;
  const copy     = output?.campaign_copy as any;
  const cp       = (output as any)?.creative_pipeline;
  // CDP audience insights
  const cdpLines = output?.audience_insights
    ? String(output.audience_insights).split("\n").filter((l: string) => l.trim())
    : [];

  const imagesB64: string[] = cp?.images_b64 ?? (cp?.image_b64 ? [cp.image_b64] : []);
  const videoB64: string = cp?.video_b64 ? String(cp.video_b64) : "";
  const adaptations = cp?.channel_adaptations as Record<string, {label: string; image_b64: string; ratio: string}> | undefined;

  const CHANNEL_ICONS: Record<string, string> = {
    instagram_feed: "📸", instagram_stories: "📱", tiktok: "🎵",
    youtube: "▶️", google_ads: "🔍", meta_ads: "📘",
    email: "📧", ooh: "🏙️", website: "🌐",
  };

  // Timeline entry wrapper
  const TL = ({ step, label, children }: { step: number; icon?: string; color?: string; label: string; children: React.ReactNode }) => (
    <div style={{ display: "flex", gap: 20, marginBottom: 32 }}>
      {/* Left: A2A orb + connector */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
        <div style={{ width: 44, height: 44, borderRadius: "50%", flexShrink: 0,
          background: ORB_BG,
          boxShadow: "0 4px 14px rgba(124,58,237,0.35), 0 0 0 4px rgba(124,58,237,0.1)",
          display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg width={18} height={18} viewBox="0 0 24 24" fill="none">
            <path d="M12 2L13.8 10.2L22 12L13.8 13.8L12 22L10.2 13.8L2 12L10.2 10.2Z" fill="white" />
          </svg>
        </div>
        <div style={{ width: 2, flex: 1, minHeight: 24,
          background: "linear-gradient(rgba(124,58,237,0.25), transparent)", margin: "6px 0" }} />
      </div>
      {/* Right: content */}
      <div style={{ flex: 1, paddingBottom: 8 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#7c3aed", letterSpacing: "0.12em",
          textTransform: "uppercase", marginBottom: 10 }}>Step {step} — {label}</div>
        {children}
      </div>
    </div>
  );

  return (
    <div style={{ ...styles.resultsPage,
      background: "linear-gradient(180deg, #faf5ff 0%, #f5f3ff 80px, #ffffff 260px)" }}>
      {/* Slim campaign ID banner */}
      {campaignId && (
        <div style={{ padding: "10px 28px", borderBottom: "1px solid #ede9fe",
          display: "flex", alignItems: "center", gap: 10, background: "rgba(250,245,255,0.9)", flexShrink: 0 }}>
          <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 12px", borderRadius: 99,
            background: "#f5f3ff", border: "1px solid #ddd6fe", color: "#7c3aed" }}>
            ✅ Campaign Ready
          </span>
          <span style={{ fontSize: 11, color: "#9ca3af", fontFamily: "monospace", letterSpacing: "0.04em" }}>
            #{campaignId}
          </span>
        </div>
      )}

      {/* Timeline */}
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "40px 24px 24px" }}>

        {/* Step 1: Brief Validation */}
        {brief && (
          <TL step={1} icon="📋" color="#7c3aed" label="Brief Validation">
            <div style={{ background: "white", borderRadius: 16, border: "1px solid #e9d5ff",
              overflow: "hidden", boxShadow: "0 2px 12px rgba(124,58,237,0.08)" }}>
              {brief.fan_truth && (
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #f3e8ff" }}>
                  <ScoreGauge score={brief.fan_truth.overall ?? 0} verdict={brief.fan_truth.verdict ?? "FAIL"} />
                  {brief.fan_truth.statement && (
                    <div style={{ padding: "10px 14px", borderRadius: 10, background: "#fdf4ff", border: "1px solid #e9d5ff", fontSize: 14, color: "#1a2332", fontStyle: "italic" }}>
                      "{brief.fan_truth.statement}"
                    </div>
                  )}
                </div>
              )}
              {brief.kpis?.length > 0 && (
                <div style={{ padding: "14px 20px", borderBottom: brief.validation_notes ? "1px solid #f3e8ff" : "none" }}>
                  {brief.kpis.slice(0, 4).map((k: any, i: number) => (
                    <KPIRow key={i} metric={k.metric} target={k.target} flag={k.flag} />
                  ))}
                </div>
              )}
              {brief.validation_notes && (
                <div style={{ padding: "12px 20px", fontSize: 12, color: "#64748b", lineHeight: 1.6, borderBottom: cdpLines.length > 0 ? "1px solid #f3e8ff" : "none" }}>
                  {brief.validation_notes}
                </div>
              )}
              {/* CDP Audience Intelligence */}
              {cdpLines.length > 0 && (() => {
                const g = (k: string) => { const l = cdpLines.find((x: string) => x.toLowerCase().includes(k)); return l ? l.split(":").slice(1).join(":").trim() : null; };
                const cnt  = cdpLines.find((l: string) => l.includes("profiles"))?.match(/(\d[\d,]+)\s+\w+\s+profiles/)?.[1] ?? null;
                const match = cdpLines.find((l: string) => l.includes("matched"));
                const income = g("household income"); const channels = g("top channels");
                const crmIdx = cdpLines.findIndex((l: string) => l.includes("CRM notes"));
                const crm = crmIdx >= 0 ? cdpLines.slice(crmIdx + 1).join(" ").slice(0, 160) : null;
                return (
                  <div style={{ padding: "14px 20px", background: "#faf5ff" }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#7c3aed", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10, display: "flex", justifyContent: "space-between" }}>
                      <span>👥 CDP Audience Intelligence</span>
                      <span style={{ fontSize: 9, padding: "2px 8px", borderRadius: 99, background: "#ede9fe", color: "#7c3aed" }}>KAGGLE CDP</span>
                    </div>
                    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: crm ? 10 : 0 }}>
                      {cnt && <div style={{ padding: "8px 12px", borderRadius: 10, background: "white", border: "1px solid #ede9fe", textAlign: "center" }}>
                        <div style={{ fontSize: 20, fontWeight: 900, color: "#7c3aed" }}>{cnt}</div>
                        <div style={{ fontSize: 9, color: "#64748b" }}>profiles matched</div>
                      </div>}
                      {income && <div style={{ flex: 1, padding: "8px 12px", borderRadius: 10, background: "white", border: "1px solid #ede9fe" }}>
                        <div style={{ fontSize: 9, color: "#64748b", fontWeight: 600, textTransform: "uppercase", marginBottom: 3 }}>Avg Income</div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: "#7c3aed" }}>{income}</div>
                      </div>}
                      {channels && <div style={{ flex: 2, padding: "8px 12px", borderRadius: 10, background: "white", border: "1px solid #ede9fe" }}>
                        <div style={{ fontSize: 9, color: "#64748b", fontWeight: 600, textTransform: "uppercase", marginBottom: 3 }}>Top Channels</div>
                        <div style={{ fontSize: 12, color: "#7c3aed" }}>{channels}</div>
                      </div>}
                    </div>
                    {match && <div style={{ fontSize: 11, color: "#475569", marginBottom: crm ? 6 : 0 }}>{match}</div>}
                    {crm && <div style={{ fontSize: 11, color: "#64748b", fontStyle: "italic", lineHeight: 1.5 }}>"{crm}…"</div>}
                  </div>
                );
              })()}
            </div>
          </TL>
        )}

        {/* Step 2: Creative Strategy */}
        {strategy?.hero_message && (
          <TL step={2} icon="💡" color="#7c3aed" label="Creative Strategy">
            <div style={{ background: "white", borderRadius: 16, border: "1px solid #ede9fe",
              overflow: "hidden", boxShadow: "0 2px 12px rgba(124,58,237,0.08)" }}>
              <div style={{ background: "linear-gradient(135deg, #7c3aed, #6d28d9)", padding: "20px 24px" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "rgba(255,255,255,0.6)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 6 }}>
                  {strategy.big_idea || "Campaign Concept"}
                </div>
                <div style={{ fontSize: 22, fontWeight: 900, color: "white", lineHeight: 1.25 }}>
                  "{strategy.hero_message}"
                </div>
                {strategy.tagline && <div style={{ fontSize: 12, color: "rgba(255,255,255,0.75)", marginTop: 6 }}>{strategy.tagline}</div>}
              </div>
              {strategy.strategic_framework && (
                <div style={{ padding: "14px 20px", fontSize: 13, color: "#374151", lineHeight: 1.6, background: "#faf5ff" }}>
                  {strategy.strategic_framework.slice(0, 280)}{strategy.strategic_framework.length > 280 ? "…" : ""}
                </div>
              )}
              {strategy.messaging_pillars?.length > 0 && (
                <div style={{ padding: "10px 20px", borderTop: "1px solid #ede9fe", display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {strategy.messaging_pillars.slice(0, 3).map((p: string, i: number) => (
                    <span key={i} style={{ fontSize: 11, padding: "3px 12px", borderRadius: 99, background: "#f5f3ff", border: "1px solid #ddd6fe", color: "#7c3aed", fontWeight: 600 }}>
                      {String(p).slice(0, 40)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </TL>
        )}

        {/* Step 3: Campaign Copy */}
        {copy?.short?.headline && (
          <TL step={3} icon="✍️" color="#7c3aed" label="Campaign Copy">
            <div style={{ background: "white", borderRadius: 16, border: "1px solid #ede9fe",
              overflow: "hidden", boxShadow: "0 2px 12px rgba(124,58,237,0.08)" }}>
              <div style={{ background: "linear-gradient(135deg, #7c3aed, #6d28d9)", padding: "16px 24px", textAlign: "center" }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: "rgba(255,255,255,0.55)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 6 }}>Short Headline</div>
                <div style={{ fontSize: 24, fontWeight: 900, color: "white" }}>"{copy.short.headline}"</div>
              </div>
              {copy.cta && (
                <div style={{ background: "#6d28d9", padding: "8px", textAlign: "center" }}>
                  <span style={{ display: "inline-block", padding: "5px 20px", borderRadius: 99, background: "white", color: "#7c3aed", fontSize: 12, fontWeight: 800 }}>{copy.cta}</span>
                </div>
              )}
              {copy.medium?.headline && (
                <div style={{ padding: "12px 20px", borderBottom: "1px solid #ede9fe" }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "#7c3aed", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>Medium</div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a" }}>"{copy.medium.headline}"</div>
                </div>
              )}
              {copy.long?.body && (
                <div style={{ padding: "12px 20px", borderBottom: "1px solid #ede9fe", fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                  {copy.long.body.slice(0, 150)}…
                </div>
              )}
              {/* Channel-specific copy */}
              {copy.channel_copy && Object.keys(copy.channel_copy as object).length > 0 && (() => {
                const COPY_CH: Record<string, { icon: string; label: string; color: string; bg: string; border: string }> = {
                  instagram_caption: { icon: "📸", label: "Instagram", color: "#7c3aed", bg: "#fdf4ff", border: "#e9d5ff" },
                  tiktok_hook:       { icon: "🎵", label: "TikTok",    color: "#be185d", bg: "#fff0f6", border: "#ffd6e7" },
                  youtube_script:    { icon: "▶️", label: "YouTube",   color: "#dc2626", bg: "#fff1f2", border: "#fecdd3" },
                  google_headline:   { icon: "🔍", label: "Google",    color: "#1967d2", bg: "#eff6ff", border: "#bfdbfe" },
                  meta_caption:      { icon: "📘", label: "Meta",      color: "#1877f2", bg: "#eff6ff", border: "#dbeafe" },
                  ooh_headline:      { icon: "🏙️", label: "OOH",      color: "#d97706", bg: "#fffbeb", border: "#fde68a" },
                  web_headline:      { icon: "🌐", label: "Website",   color: "#059669", bg: "#f0fdf4", border: "#86efac" },
                  email_subject:     { icon: "📧", label: "Email",     color: "#0369a1", bg: "#f0f9ff", border: "#bae6fd" },
                };
                const entries = Object.entries(copy.channel_copy as Record<string, string>);
                return (
                  <div style={{ padding: "12px 20px", display: "grid", gridTemplateColumns: entries.length > 2 ? "1fr 1fr" : "1fr", gap: 8 }}>
                    {entries.map(([key, val]) => {
                      const cfg = COPY_CH[key] ?? { icon: "📢", label: key, color: "#64748b", bg: "#f8fafc", border: "#e2e8f0" };
                      return (
                        <div key={key} style={{ padding: "9px 12px", borderRadius: 10, background: cfg.bg, border: `1px solid ${cfg.border}` }}>
                          <div style={{ fontSize: 9, fontWeight: 700, color: cfg.color, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 3 }}>{cfg.icon} {cfg.label}</div>
                          <div style={{ fontSize: 12, color: cfg.color, lineHeight: 1.4 }}>{val.slice(0, 90)}{val.length > 90 ? "…" : ""}</div>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}
            </div>
          </TL>
        )}

        {/* Step 4: Cultural Intelligence */}
        {cp?.culture_brief && (
          <TL step={4} icon="🌍" color="#7c3aed" label="Cultural Intelligence">
            <div style={{ background: "white", borderRadius: 16, border: "1px solid #99f6e4",
              padding: "16px 20px", boxShadow: "0 2px 12px rgba(13,148,136,0.08)" }}>
              {cp.culture_brief.replace(/\*\*([^*]+)\*\*/g, "$1").replace(/^#+\s*/gm, "").split(/(?<=[.!?])\s+/).filter((s: string) => s.length > 25).slice(0, 4).map((s: string, i: number) => (
                <div key={i} style={{ display: "flex", gap: 10, marginBottom: 10, padding: "10px 12px", borderRadius: 10, background: i === 0 ? "#f0fdfa" : "#f8fafc", border: `1px solid ${i === 0 ? "#99f6e4" : "#e2e8f0"}` }}>
                  <span style={{ fontSize: 16, flexShrink: 0 }}>{["🌍", "💫", "🎯", "⚡"][i]}</span>
                  <span style={{ fontSize: 13, color: "#1a2332", lineHeight: 1.5 }}>{s}</span>
                </div>
              ))}
            </div>
          </TL>
        )}

        {/* Step 5: Key Visual */}
        {imagesB64.length > 0 && (
          <TL step={5} icon="🎨" color="#7c3aed" label={`Key Visual${imagesB64.length > 1 ? ` — ${imagesB64.length} Variations` : ""}`}>
            <div style={{ background: "white", borderRadius: 16, border: "1px solid #fecdd3",
              overflow: "hidden", boxShadow: "0 2px 12px rgba(190,18,60,0.1)" }}>
              <img src={`data:image/jpeg;base64,${imagesB64[selectedKV]}`} alt="Key visual"
                style={{ width: "100%", display: "block" }} />
              {imagesB64.length > 1 && (
                <div style={{ padding: "12px 16px", borderTop: "1px solid #fecdd3", background: "#fff8f8" }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "#be123c", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>
                    Pick Your Variation
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    {imagesB64.map((img, idx) => (
                      <div key={idx} onClick={() => setSelectedKV(idx)}
                        style={{ flex: 1, cursor: "pointer", borderRadius: 8, overflow: "hidden",
                          border: `3px solid ${idx === selectedKV ? "#be123c" : "transparent"}`,
                          opacity: idx === selectedKV ? 1 : 0.55, transition: "all 0.2s",
                          boxShadow: idx === selectedKV ? "0 0 0 2px rgba(190,18,60,0.2)" : "none" }}>
                        <img src={`data:image/jpeg;base64,${img}`} alt={`V${idx + 1}`}
                          style={{ width: "100%", display: "block" }} />
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {cp?.image_prompt && (
                <div style={{ padding: "10px 16px", borderTop: "1px solid #fecdd3", fontSize: 10, color: "#94a3b8", lineHeight: 1.5, fontFamily: "monospace", background: "#fff8f8" }}>
                  {cp.image_prompt.slice(0, 200)}…
                </div>
              )}
            </div>
          </TL>
        )}

        {/* Step 6: Campaign Reel */}
        {videoB64 && (
          <TL step={6} icon="🎬" color="#7c3aed" label="Campaign Reel — 6s Veo">
            <div style={{ background: "#0f172a", borderRadius: 12, overflow: "hidden" }}>
              <video controls autoPlay loop muted playsInline
                style={{ width: "100%", display: "block" }}
                src={`data:video/mp4;base64,${videoB64}`} />
              <div style={{ padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 11, color: "#94a3b8" }}>6s · 16:9 · Veo 3</span>
                <a href={`data:video/mp4;base64,${videoB64}`} download="campaign-reel.mp4"
                  style={{ fontSize: 11, fontWeight: 700, color: "#f59e0b", textDecoration: "none" }}>
                  ⬇ Download mp4
                </a>
              </div>
            </div>
          </TL>
        )}

        {/* Step 7: Channel Adaptations */}
        {adaptations && Object.keys(adaptations).length > 0 && (
          <TL step={6} icon="📐" color="#7c3aed" label={`Channel Adaptations — ${Object.keys(adaptations).length} formats`}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 }}>
              {Object.entries(adaptations).map(([key, val]) => (
                <div key={key} style={{ borderRadius: 12, overflow: "hidden", border: "1px solid #e0e7ff", boxShadow: "0 2px 8px rgba(67,56,202,0.08)" }}>
                  <div style={{ background: "#eef2ff", padding: "6px 12px", display: "flex", alignItems: "center", gap: 6, borderBottom: "1px solid #e0e7ff" }}>
                    <span style={{ fontSize: 13 }}>{CHANNEL_ICONS[key] ?? "📺"}</span>
                    <span style={{ fontSize: 11, fontWeight: 700, color: "#4338ca" }}>{val.label}</span>
                    <span style={{ marginLeft: "auto", fontSize: 9, color: "#94a3b8", fontFamily: "monospace" }}>{val.ratio}</span>
                  </div>
                  <img src={`data:image/jpeg;base64,${val.image_b64}`} alt={val.label} style={{ width: "100%", display: "block" }} />
                </div>
              ))}
            </div>
          </TL>
        )}

        {/* Step 7: Launch */}
        <TL step={7} icon="🚀" color="#7c3aed" label="Launch Campaign">
          <DistributePanel output={output} campaignId={campaignId}
            selectedImageB64={imagesB64[selectedKV] ?? undefined} />
        </TL>

        {/* Raw output toggle */}
        {output && (
          <div style={{ marginTop: 16, padding: "12px 16px", borderRadius: 12, background: "#f8fafc", border: "1px solid #e2e8f0" }}>
            <button style={styles.expandBtn} onClick={() => setExpanded(e => !e)}>
              {expanded ? "▲ Hide" : "▼ Show"} full pipeline output (JSON)
            </button>
            {expanded && <pre style={styles.jsonPre}>{JSON.stringify(output, null, 2)}</pre>}
          </div>
        )}
      </div>

      <div style={{ height: 60 }} />
    </div>
  );
}
// ── Agent network wakeup screen (shown before Logos starts) ───
const AGENT_COLORS = ["#7c3aed","#06b6d4","#10b981","#f59e0b","#ec4899","#6366f1","#14b8a6"];
const AGENT_DESCS  = [
  "Understands your goals, audience, product and campaign objectives",
  "Crafts big ideas and messaging territories that inspire",
  "Writes compelling headlines, copy, scripts and captions",
  "Analyzes cultural trends, insights and audience behaviors",
  "Creates striking key visuals, ad designs and imagery",
  "Produces engaging short videos and reels visually",
  "Adapts content for every platform and channel",
];
// Light bg hex (no #) fed to DiceBear to tint each agent's avatar
const AGENT_AVATAR_BG = ["e9d5ff","cffafe","d1fae5","fef3c7","fce7f3","e0e7ff","ccfbf1"];
// DiceBear personas — illustrated human avatars, unique per agent name
const avatarUrl = (label: string, bg: string) =>
  `https://api.dicebear.com/7.x/personas/svg?seed=${encodeURIComponent(label)}&backgroundColor=${bg}&radius=50&scale=115`;

// [left, top] offset of info card relative to node centre
const CARD_OFF: [number, number][] = [
  [ 32, -40],  // 0 top
  [ 32, -40],  // 1 top-right
  [ 32, -22],  // 2 right
  [ 32,  10],  // 3 bottom-right
  [-158,  10], // 4 bottom-left
  [-158, -22], // 5 left
  [-158, -40], // 6 top-left
];

function AgentNetworkWakeUp() {
  const W = 680, H = 400, cx = W / 2, cy = H / 2, R = 152;

  const nodes = HARNESS_STAGES.map((s, i) => {
    const a = (i / HARNESS_STAGES.length) * 2 * Math.PI - Math.PI / 2;
    return { ...s, x: cx + Math.cos(a) * R, y: cy + Math.sin(a) * R,
      num: String(i + 1).padStart(2, "0"), color: AGENT_COLORS[i], desc: AGENT_DESCS[i],
      co: CARD_OFF[i], avatar: avatarUrl(s.label, AGENT_AVATAR_BG[i]) };
  });

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" as const,
      background: "linear-gradient(145deg, #faf5ff 0%, #f5f3ff 40%, #ede9fe 100%)",
      overflow: "hidden", position: "relative" as const }}>

      {/* Subtle grid */}
      <div style={{ position: "absolute" as const, inset: 0, opacity: 0.03,
        backgroundImage: "linear-gradient(#7c3aed 1px,transparent 1px),linear-gradient(90deg,#7c3aed 1px,transparent 1px)",
        backgroundSize: "44px 44px", pointerEvents: "none" as const }} />

      {/* Title */}
      <div style={{ textAlign: "center" as const, padding: "24px 24px 0", position: "relative", zIndex: 10 }}>
        <h2 style={{ fontSize: 24, fontWeight: 800, color: "#1a0040",
          letterSpacing: "-0.02em", marginBottom: 6, lineHeight: 1.3 }}>
          Seven AI Agents.{" "}
          <span style={{ background: ORB_BG, WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
            One Powerful Campaign.
          </span>
        </h2>
        <p style={{ fontSize: 12, color: "#6b7280", lineHeight: 1.6, maxWidth: 460, margin: "0 auto" }}>
          From strategy to content, visuals to videos, and channel-optimised publishing —
          our AI agents collaborate to launch campaigns that perform.
        </p>
      </div>

      {/* Network diagram */}
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "relative" as const, width: W, height: H, overflow: "visible" }}>

          {/* SVG: rings + connecting lines + travelling dots */}
          <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H}
            style={{ position: "absolute" as const, inset: 0, overflow: "visible" }}>
            {[42, 72, 108].map((r, ri) => (
              <circle key={ri} cx={cx} cy={cy} r={r} fill="none"
                stroke="rgba(124,58,237,0.12)" strokeWidth="1.2"
                style={{ animation: `ring-out ${2.5 + ri * 0.8}s ${ri * 0.4}s ease-out infinite` }} />
            ))}
            {nodes.map((n, i) => (
              <line key={n.key} x1={cx} y1={cy} x2={n.x} y2={n.y}
                stroke={n.color} strokeOpacity="0.25" strokeWidth="1.5"
                strokeDasharray="6 5"
                style={{ animation: `dash-move 2s ${i * 0.22}s linear infinite` }} />
            ))}
            {/* Travelling dot on each line */}
            {nodes.map((n, i) => {
              const t = 0.52;
              return <circle key={`d${i}`}
                cx={cx + (n.x - cx) * t} cy={cy + (n.y - cy) * t} r={3}
                fill={n.color}
                style={{ animation: `wave-dot 1.8s ${i * 0.25}s ease-in-out infinite` }} />;
            })}
          </svg>

          {/* Central hub */}
          <div style={{ position: "absolute" as const, left: cx, top: cy,
            transform: "translate(-50%,-50%)", zIndex: 4,
            animation: "hub-beat 2s ease-in-out infinite" }}>
            <GradientOrb size={78} />
          </div>

          {/* Agent nodes + badges + info cards */}
          {nodes.map((n, i) => (
            <div key={n.key} style={{ position: "absolute" as const, left: n.x, top: n.y,
              transform: "translate(-50%,-50%)", zIndex: 3,
              animation: `node-in 0.5s ${0.15 + i * 0.12}s cubic-bezier(0.22,1,0.36,1) both` }}>

              {/* Node circle with avatar */}
              <div style={{ width: 54, height: 54, borderRadius: "50%", position: "relative" as const,
                border: `2.5px solid ${n.color}70`,
                boxShadow: `0 0 20px ${n.color}35, 0 2px 8px rgba(0,0,0,0.1)`,
                overflow: "hidden",
                animation: `node-glow 2.4s ${i * 0.35}s ease-in-out infinite` }}>
                <img src={n.avatar} alt={n.label}
                  style={{ width: "100%", height: "100%", display: "block", objectFit: "cover" }} />
                {/* Number badge */}
                <div style={{ position: "absolute" as const, top: -7, right: n.co[0] < 0 ? undefined : -7,
                  left: n.co[0] < 0 ? -7 : undefined,
                  width: 19, height: 19, borderRadius: "50%",
                  background: n.color, border: "2px solid white",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 8, fontWeight: 800, color: "white",
                  boxShadow: `0 0 6px ${n.color}80` }}>{n.num}</div>
              </div>

              {/* Info card */}
              <div style={{ position: "absolute" as const,
                left: n.co[0], top: n.co[1],
                width: 140, padding: "9px 11px",
                background: "rgba(255,255,255,0.88)",
                backdropFilter: "blur(10px)",
                border: `1px solid ${n.color}30`,
                borderRadius: 10,
                boxShadow: `0 2px 16px rgba(0,0,0,0.06), 0 0 10px ${n.color}15`,
                textAlign: n.co[0] < 0 ? "right" as const : "left" as const }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: n.color, marginBottom: 3 }}>
                  {n.label}
                </div>
                <div style={{ fontSize: 9.5, color: "#6b7280", lineHeight: 1.5 }}>{n.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Working Together strip */}
      <div style={{ padding: "8px 24px 12px",
        borderTop: "1px solid rgba(124,58,237,0.12)",
        display: "flex", alignItems: "center", gap: 6, flexShrink: 0,
        background: "rgba(255,255,255,0.5)" }}>
        <div style={{ fontSize: 10, fontWeight: 800, color: "#7c3aed",
          letterSpacing: "0.04em", marginRight: 8, lineHeight: 1.4,
          whiteSpace: "nowrap" as const }}>Working<br/>Together</div>
        {HARNESS_STAGES.map((s, i) => (
          <Fragment key={s.key}>
            <div style={{ display: "flex", alignItems: "center", gap: 4,
              padding: "3px 9px", borderRadius: 6,
              background: "rgba(124,58,237,0.07)",
              border: "1px solid rgba(124,58,237,0.15)" }}>
              <span style={{ fontSize: 10 }}>{s.icon}</span>
              <span style={{ fontSize: 9.5, color: "#6d28d9", fontWeight: 600,
                whiteSpace: "nowrap" as const }}>{s.label}</span>
            </div>
            {i < HARNESS_STAGES.length - 1 && (
              <span style={{ color: "#a78bfa", fontSize: 10, flexShrink: 0 }}>→</span>
            )}
          </Fragment>
        ))}
      </div>
    </div>
  );
}

// ── Briefing agent orb header ─────────────────────────────────
function OrbHeader({ done }: { done: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 28 }}>
      <div style={{
        width: 52, height: 52, borderRadius: "50%", flexShrink: 0,
        background: ORB_BG,
        boxShadow: "0 4px 20px rgba(200,40,200,0.3)",
        display: "flex", alignItems: "center", justifyContent: "center",
        animation: done ? "none" : "icon-breathe 2.5s ease-in-out infinite",
      }}>
        <svg width={20} height={20} viewBox="0 0 24 24" fill="none">
          <path d="M12 2L13.8 10.2L22 12L13.8 13.8L12 22L10.2 13.8L2 12L10.2 10.2Z" fill="white" />
        </svg>
      </div>
      <div>
        <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.12em",
          color: "#7c3aed", textTransform: "uppercase" as const, marginBottom: 3 }}>
          LOGOS · {done ? "COMPLETE ✓" : "RUNNING"}
        </div>
        <div style={{ fontSize: 17, fontWeight: 700, color: "#111827" }}>Validating Brief</div>
      </div>
    </div>
  );
}

// ── Brief Intake view — 3-phase A2A style ────────────────────
// Phase 1: "Generating..." orb (agent not yet active)
// Phase 2: Data sources streaming in (agent running, data flowing)
// Phase 3: Brief summary cards (agent done)
// All phases share the same purple/violet color identity.
const BRIEF_DATA_SOURCES = [
  { id: "brand",    icon: "📚", label: "Brand Guidelines",     from: "GCS Bucket",        delay: 0    },
  { id: "fantruth", icon: "💡", label: "Fan Truth Library",    from: "Vertex AI Search",  delay: 600  },
  { id: "history",  icon: "📈", label: "Historical Campaigns", from: "BigQuery",           delay: 1200 },
  { id: "cdp",      icon: "👥", label: "CDP / Sephora",        from: "Kaggle · BigQuery", delay: 1800 },
];
function BriefIntakeView({
  brief,
  milestone,
  liveMsg,
  agentDone,
}: {
  brief: import("./types/pipeline").HarnessBriefRequest | null;
  milestone: Record<string, unknown> | undefined;
  liveMsg: string | null;
  agentDone: boolean;
}) {
  const ft   = (milestone?.fan_truth ?? {}) as any;
  const aud  = (milestone?.audience  ?? {}) as any;
  const kpis = (milestone?.kpis      ?? []) as any[];

  // Phase logic
  const hasData = !!milestone || !!liveMsg;
  // phase 1: nothing yet, phase 2: data flowing, phase 3: done
  const phase: 1 | 2 | 3 = agentDone ? 3 : hasData ? 2 : 1;

  // ── Phase 1: Generating spinner ─────────────────────────────
  if (phase === 1) {
    return (
      <div style={{ flex: 1, display: "flex", flexDirection: "column" as const,
        alignItems: "center", justifyContent: "center", gap: 28 }}>
        <div style={{
          width: 90, height: 90, borderRadius: "50%",
          background: ORB_BG,
          boxShadow: "0 8px 32px rgba(200,40,200,0.32)",
          display: "flex", alignItems: "center", justifyContent: "center",
          animation: "icon-breathe 2.5s ease-in-out infinite",
        }}>
          <svg width={34} height={34} viewBox="0 0 24 24" fill="none">
            <path d="M12 2L13.8 10.2L22 12L13.8 13.8L12 22L10.2 13.8L2 12L10.2 10.2Z" fill="white" />
          </svg>
        </div>
        <div style={{ fontSize: 20, fontWeight: 600, color: "#374151", letterSpacing: "-0.01em" }}>
          Generating ...
        </div>
      </div>
    );
  }

  // ── Phase 2: Data sources streaming ─────────────────────────
  if (phase === 2) {
    const hasAllSources = !!milestone?.fan_truth;
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
        padding: "40px 48px", overflowY: "auto" as const,
        background: "linear-gradient(135deg, #faf5ff 0%, #f5f3ff 50%, #faf5ff 100%)" }}>
        <div style={{ width: "100%", maxWidth: 680 }}>
          <OrbHeader done={false} />

          {/* Data sources */}
          <div style={{ fontSize: 11, fontWeight: 800, color: "#7c3aed", letterSpacing: "0.12em",
            textTransform: "uppercase" as const, marginBottom: 16 }}>
            Querying Data Sources
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 24 }}>
            {BRIEF_DATA_SOURCES.map((src, idx) => {
              const done = hasAllSources || (milestone && idx === 0);
              return (
                <div key={src.id} style={{
                  display: "flex", alignItems: "center", gap: 16,
                  padding: "20px 22px", borderRadius: 16,
                  background: done ? "rgba(124,58,237,0.06)" : "white",
                  border: `1.5px solid ${done ? "rgba(124,58,237,0.3)" : "#e5e7eb"}`,
                  boxShadow: done ? "0 2px 12px rgba(124,58,237,0.08)" : "0 1px 6px rgba(0,0,0,0.04)",
                  transition: "all 0.4s ease",
                }}>
                  <div style={{ width: 48, height: 48, borderRadius: 12, flexShrink: 0,
                    background: done ? "rgba(124,58,237,0.12)" : "#f9fafb",
                    display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22 }}>
                    {src.icon}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#111827", marginBottom: 3 }}>
                      {src.label}
                    </div>
                    <div style={{ fontSize: 12, color: "#9ca3af" }}>← {src.from}</div>
                  </div>
                  {done
                    ? <span style={{ fontSize: 16, color: "#7c3aed", fontWeight: 800, flexShrink: 0 }}>✓</span>
                    : <div style={{ display: "flex", gap: 3, flexShrink: 0 }}>
                        {[0,1,2].map(d => (
                          <div key={d} style={{ width: 5, height: 5, borderRadius: "50%",
                            background: "#cc3cf2",
                            animation: `wave-dot 1.2s ${idx * 0.15 + d * 0.2}s ease-in-out infinite` }} />
                        ))}
                      </div>}
                </div>
              );
            })}
          </div>

          {/* Live message */}
          {liveMsg && (
            <div style={{ fontSize: 13, color: "#7c3aed", fontStyle: "italic",
              padding: "10px 14px", borderRadius: 10,
              background: "rgba(124,58,237,0.06)", border: "1px solid rgba(124,58,237,0.15)" }}>
              {liveMsg}
            </div>
          )}

          {/* Fan Truth preview when it arrives */}
          {ft?.overall !== undefined && (
            <div style={{ marginTop: 16, padding: "16px 18px", borderRadius: 12,
              background: "white", border: "1.5px solid rgba(124,58,237,0.2)" }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: "#7c3aed",
                letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 10 }}>
                Fan Truth Score
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 32, fontWeight: 900,
                  color: ft.overall >= 70 ? "#10b981" : ft.overall >= 50 ? "#f59e0b" : "#ef4444" }}>
                  {ft.overall}/100
                </span>
                <span style={{ fontSize: 11, fontWeight: 800, padding: "3px 12px", borderRadius: 99,
                  background: ft.verdict === "PASS" ? "#dcfce7" : "#fee2e2",
                  color: ft.verdict === "PASS" ? "#065f46" : "#991b1b" }}>
                  {ft.verdict}
                </span>
              </div>
              {ft.statement && (
                <div style={{ marginTop: 8, fontSize: 12, color: "#6b7280", fontStyle: "italic" }}>
                  "{String(ft.statement).slice(0, 110)}…"
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Phase 3: Brief summary cards ────────────────────────────
  const Card = ({ title, children, full }: { title: string; children: React.ReactNode; full?: boolean }) => (
    <div style={{
      background: "white", border: "1px solid #ede9fe", borderRadius: 14,
      padding: "22px 24px", gridColumn: full ? "1 / -1" : undefined,
      boxShadow: "0 1px 8px rgba(124,58,237,0.06)",
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#7c3aed", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );

  const scoreColor = ft?.overall >= 70 ? "#10b981" : ft?.overall >= 50 ? "#f59e0b" : "#ef4444";
  const interestTags = [
    ...(brief?.audience?.age_range ? [brief.audience.age_range] : []),
    ...(brief?.audience?.interests ? brief.audience.interests.split(", ").filter(Boolean) : []),
  ];

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "linear-gradient(180deg, #faf5ff 0%, #ffffff 200px)" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <OrbHeader done={true} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

        {/* Brand */}
        <Card title="Brand">
          <div style={{ fontSize: 26, fontWeight: 800, color: "#111827", lineHeight: 1.1, marginBottom: 6 }}>
            {brief?.brand ?? "—"}
          </div>
          <div style={{ fontSize: 14, color: "#6b7280" }}>{brief?.product ?? ""}</div>
        </Card>

        {/* Objective */}
        <Card title="Objective">
          <div style={{ fontSize: 15, color: "#111827", lineHeight: 1.6 }}>
            {brief?.goal ?? "—"}
          </div>
        </Card>

        {/* Target Audience */}
        <Card title="Target Audience">
          <div style={{ fontSize: 22, fontWeight: 700, color: "#111827", marginBottom: 4 }}>
            {brief?.audience?.segment || "General Audience"}
          </div>
          {brief?.audience?.age_range && (
            <div style={{ fontSize: 14, color: "#6b7280", marginBottom: 10 }}>
              {brief.audience.age_range}
            </div>
          )}
          <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 6 }}>
            {interestTags.map((t, i) => (
              <span key={i} style={{ fontSize: 12, padding: "3px 10px", borderRadius: 99,
                background: "#f9fafb", border: "1px solid #e5e7eb", color: "#374151" }}>
                {t}
              </span>
            ))}
            {brief?.market && (
              <span style={{ fontSize: 12, padding: "3px 10px", borderRadius: 99,
                background: "#f5f3ff", border: "1px solid #ddd6fe", color: "#7c3aed" }}>
                {brief.market}
              </span>
            )}
          </div>
        </Card>

        {/* Channels */}
        <Card title="Channels">
          <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
            {(brief?.channels ?? []).map((ch, i) => (
              <span key={i} style={{ fontSize: 13, padding: "5px 14px", borderRadius: 99,
                background: "#f5f3ff", border: "1px solid #ddd6fe", color: "#7c3aed", fontWeight: 500 }}>
                {ch}
              </span>
            ))}
          </div>
        </Card>

        {/* KPIs */}
        <Card title="KPIs">
          {kpis.length > 0 ? (
            kpis.slice(0, 4).map((k: any, i: number) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8,
                marginBottom: 8, fontSize: 14, color: "#111827" }}>
                <span style={{ color: "#7c3aed", fontWeight: 700 }}>→</span>
                <span style={{ fontWeight: 600 }}>{k.metric}</span>
                {k.target && <span style={{ color: "#6b7280" }}>— {k.target}</span>}
              </div>
            ))
          ) : (brief?.kpis ? brief.kpis.split(", ").map((k, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8,
              marginBottom: 8, fontSize: 14, color: "#111827" }}>
              <span style={{ color: "#7c3aed", fontWeight: 700 }}>→</span> {k}
            </div>
          )) : null)}
        </Card>

        {/* Fan Truth */}
        <Card title="Fan Truth Score">
          {ft?.overall !== undefined ? (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
                <span style={{ fontSize: 28, fontWeight: 800, color: scoreColor }}>
                  {ft.overall}/100
                </span>
                <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 99,
                  background: ft.verdict === "PASS" ? "#dcfce7" : "#fee2e2",
                  color: ft.verdict === "PASS" ? "#065f46" : "#991b1b" }}>
                  {ft.verdict}
                </span>
              </div>
              {ft.statement && (
                <div style={{ fontSize: 13, color: "#6b7280", fontStyle: "italic", lineHeight: 1.5 }}>
                  "{String(ft.statement).slice(0, 100)}{String(ft.statement).length > 100 ? "…" : ""}"
                </div>
              )}
              {aud?.count && (
                <div style={{ marginTop: 8, fontSize: 12, color: "#7c3aed" }}>
                  👥 {String(aud.count).replace(/\D.*/, "")} profiles matched
                  {aud.income ? ` · ${aud.income}` : ""}
                </div>
              )}
            </div>
          ) : (
            <div style={{ fontSize: 14, color: "#9ca3af" }}>Awaiting score…</div>
          )}
        </Card>

        {/* Tone of Voice — full width */}
        <Card title="Tone of Voice" full>
          <div style={{ fontSize: 22, fontWeight: 700, color: "#111827", fontStyle: "italic" }}>
            "{brief?.tone || "Bold, warm, unapologetically confident"}"
          </div>
        </Card>

        </div>{/* grid */}
      </div>
    </div>
  );
}

// ── Shared agent intake helpers ──────────────────────────────
function AgentIntakeHeader({ label, title, done }: {
  label: string; title: string; done: boolean;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 28 }}>
      {/* Always the same A2A purple orb */}
      <div style={{
        width: 52, height: 52, borderRadius: "50%", flexShrink: 0,
        background: ORB_BG,
        boxShadow: "0 4px 20px rgba(200,40,200,0.3)",
        display: "flex", alignItems: "center", justifyContent: "center",
        animation: done ? "none" : "icon-breathe 2.5s ease-in-out infinite",
      }}>
        <svg width={22} height={22} viewBox="0 0 24 24" fill="none">
          <path d="M12 2L13.8 10.2L22 12L13.8 13.8L12 22L10.2 13.8L2 12L10.2 10.2Z" fill="white" />
        </svg>
      </div>
      <div>
        <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.12em",
          color: "#7c3aed", textTransform: "uppercase" as const, marginBottom: 3 }}>
          {label} · {done ? "COMPLETE ✓" : "RUNNING"}
        </div>
        <div style={{ fontSize: 17, fontWeight: 700, color: "#111827" }}>{title}</div>
      </div>
    </div>
  );
}

function AgentGeneratingView({ liveMsg }: { liveMsg?: string | null }) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" as const,
      alignItems: "center", justifyContent: "center", gap: 24 }}>
      <div style={{
        width: 90, height: 90, borderRadius: "50%",
        background: ORB_BG,
        boxShadow: "0 8px 32px rgba(200,40,200,0.32)",
        display: "flex", alignItems: "center", justifyContent: "center",
        animation: "icon-breathe 2.5s ease-in-out infinite",
      }}>
        <svg width={34} height={34} viewBox="0 0 24 24" fill="none">
          <path d="M12 2L13.8 10.2L22 12L13.8 13.8L12 22L10.2 13.8L2 12L10.2 10.2Z" fill="white" />
        </svg>
      </div>
      <div style={{ fontSize: 20, fontWeight: 600, color: "#374151", letterSpacing: "-0.01em" }}>
        Generating ...
      </div>
      {liveMsg && (
        <div style={{ fontSize: 12, color: "#9ca3af", fontStyle: "italic", maxWidth: 340,
          textAlign: "center" as const, lineHeight: 1.5, padding: "0 24px" }}>
          {liveMsg}
        </div>
      )}
    </div>
  );
}

// ── Strategy / Content Creator intake view ────────────────────
function StrategyIntakeView({ milestone, liveMsg }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
}) {
  const m = (milestone ?? {}) as any;

  // Stay on orb until real milestone data arrives
  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  const SCard = ({ title, children, full }: { title: string; children: React.ReactNode; full?: boolean }) => (
    <div style={{ background: "white", border: "1px solid #ede9fe", borderRadius: 14,
      padding: "22px 24px", gridColumn: full ? "1 / -1" : undefined,
      boxShadow: "0 1px 8px rgba(124,58,237,0.06)" }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#7c3aed", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "linear-gradient(180deg, #faf5ff 0%, #ffffff 180px)" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <AgentIntakeHeader label="HELIA" title="Creative Strategy" done={true} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {m.big_idea && (
            <SCard title="Big Idea" full>
              <div style={{ fontSize: 22, fontWeight: 800, fontStyle: "italic",
                color: "#7c3aed", lineHeight: 1.3 }}>"{m.big_idea}"</div>
            </SCard>
          )}
          {m.hero_message && (
            <SCard title="Hero Message" full>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#111827", lineHeight: 1.4 }}>
                "{m.hero_message}"
              </div>
              {m.tagline && (
                <div style={{ marginTop: 8, fontSize: 14, color: "#6b7280", fontStyle: "italic" }}>
                  {m.tagline}
                </div>
              )}
            </SCard>
          )}
          {m.strategic_framework && (
            <SCard title="Strategic Framework">
              <div style={{ fontSize: 13, color: "#374151", lineHeight: 1.7 }}>
                {String(m.strategic_framework).slice(0, 260)}
                {String(m.strategic_framework).length > 260 ? "…" : ""}
              </div>
            </SCard>
          )}
          {(m.messaging_pillars as string[])?.length > 0 && (
            <SCard title="Messaging Pillars">
              <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
                {(m.messaging_pillars as string[]).slice(0, 4).map((p: string, i: number) => (
                  <span key={i} style={{ fontSize: 12, padding: "5px 12px", borderRadius: 99,
                    background: "#f5f3ff", border: "1px solid #ddd6fe", color: "#7c3aed", fontWeight: 600 }}>
                    {String(p).slice(0, 40)}
                  </span>
                ))}
              </div>
            </SCard>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Copy Agent intake view ────────────────────────────────────
function CopyIntakeView({ milestone, liveMsg }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
}) {
  const g1 = "#7c3aed", g2 = "#6d28d9";
  const m = (milestone ?? {}) as any;

  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  const CCard = ({ title, children, full }: { title: string; children: React.ReactNode; full?: boolean }) => (
    <div style={{ background: "white", border: "1px solid #ede9fe", borderRadius: 14,
      padding: "22px 24px", gridColumn: full ? "1 / -1" : undefined,
      boxShadow: "0 1px 8px rgba(124,58,237,0.06)" }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#7c3aed", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );

  const channelCopy = m.channel_copy as Record<string, string> | undefined;
  const COPY_CFG: Record<string, { icon: string; label: string; color: string; bg: string }> = {
    instagram_caption: { icon: "📸", label: "Instagram", color: "#7c3aed", bg: "#fdf4ff" },
    tiktok_hook:       { icon: "🎵", label: "TikTok",    color: "#be185d", bg: "#fff0f6" },
    youtube_script:    { icon: "▶️", label: "YouTube",   color: "#dc2626", bg: "#fff1f2" },
    google_headline:   { icon: "🔍", label: "Google",    color: "#1967d2", bg: "#eff6ff" },
    meta_caption:      { icon: "📘", label: "Meta",      color: "#1877f2", bg: "#eff6ff" },
    ooh_headline:      { icon: "🏙️", label: "OOH",      color: "#d97706", bg: "#fffbeb" },
    web_headline:      { icon: "🌐", label: "Website",   color: "#059669", bg: "#f0fdf4" },
    email_subject:     { icon: "📧", label: "Email",     color: "#0369a1", bg: "#f0f9ff" },
  };

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "linear-gradient(180deg, #faf5ff 0%, #ffffff 180px)" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <AgentIntakeHeader label="IDEON" title="Campaign Copy" done={true} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {/* Billboard hero */}
          {m.short_headline && (
            <CCard title="Short Headline" full>
              <div style={{ background: `linear-gradient(135deg, ${g1}, ${g2})`,
                borderRadius: 10, padding: "20px 24px", textAlign: "center" as const, marginBottom: 8 }}>
                <div style={{ fontSize: 22, fontWeight: 900, color: "white", lineHeight: 1.2 }}>
                  "{m.short_headline}"
                </div>
                {m.cta && (
                  <div style={{ marginTop: 12, display: "inline-block", padding: "6px 20px",
                    borderRadius: 99, background: "white", color: g1, fontSize: 12, fontWeight: 800 }}>
                    {m.cta}
                  </div>
                )}
              </div>
            </CCard>
          )}
          {m.medium_headline && (
            <CCard title="Medium Headline">
              <div style={{ fontSize: 16, fontWeight: 700, color: "#111827", lineHeight: 1.4 }}>
                "{m.medium_headline}"
              </div>
            </CCard>
          )}
          {m.body && (
            <CCard title="Body Copy">
              <div style={{ fontSize: 13, color: "#374151", lineHeight: 1.7 }}>
                {String(m.body).slice(0, 200)}{String(m.body).length > 200 ? "…" : ""}
              </div>
            </CCard>
          )}
          {channelCopy && Object.keys(channelCopy).length > 0 && (
            <CCard title="Channel Copy" full>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {Object.entries(channelCopy).map(([key, val]) => {
                  const cfg = COPY_CFG[key] ?? { icon: "📢", label: key, color: "#64748b", bg: "#f8fafc" };
                  return (
                    <div key={key} style={{ padding: "10px 12px", borderRadius: 10,
                      background: cfg.bg, border: `1px solid ${cfg.color}20` }}>
                      <div style={{ fontSize: 10, fontWeight: 700, color: cfg.color,
                        textTransform: "uppercase" as const, letterSpacing: "0.1em", marginBottom: 5 }}>
                        {cfg.icon} {cfg.label}
                      </div>
                      <div style={{ fontSize: 12, color: cfg.color, lineHeight: 1.4 }}>
                        {val.slice(0, 90)}{val.length > 90 ? "…" : ""}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CCard>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Culture / Cultural Research intake view ───────────────────
function CultureIntakeView({ milestone, liveMsg }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
}) {
  const raw = milestone?.brief ? String(milestone.brief) : "";

  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  const sentences = raw
    .replace(/\*\*([^*]+)\*\*/g, "$1").replace(/^#+\s*/gm, "").replace(/^[-*]\s*/gm, "")
    .split(/(?<=[.!?])\s+/).map(s => s.trim()).filter(s => s.length > 25).slice(0, 6);

  const ICONS = ["🌍", "💫", "🎯", "⚡", "🔥", "✨"];

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "linear-gradient(180deg, #faf5ff 0%, #ffffff 180px)" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <AgentIntakeHeader label="AETHER" title="Cultural Intelligence" done={true} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          {sentences.map((s, i) => (
            <div key={i} style={{ display: "flex", gap: 14, padding: "18px 20px",
              borderRadius: 14, background: "white",
              border: `1px solid ${i === 0 ? "rgba(124,58,237,0.25)" : "#e5e7eb"}`,
              boxShadow: `0 1px 8px rgba(124,58,237,${i === 0 ? "0.08" : "0.03"})`,
              gridColumn: i === 0 ? "1 / -1" : undefined }}>
              <span style={{ fontSize: 22, flexShrink: 0, marginTop: 2 }}>{ICONS[i]}</span>
              <span style={{ fontSize: i === 0 ? 15 : 13, color: "#1a2332", lineHeight: 1.6,
                fontWeight: i === 0 ? 600 : 400 }}>
                {s}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── KV Generator intake view ─────────────────────────────────
function KVIntakeView({ milestone, liveMsg, reelMilestone }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
  reelMilestone: Record<string,unknown> | undefined;
}) {
  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  return (
    <div style={{ flex: 1, overflowY: "auto" as const,
      background: "linear-gradient(180deg, #faf5ff 0%, #ffffff 180px)" }}>
      <div style={{ minHeight: "100%", display: "flex", flexDirection: "column" as const,
        justifyContent: "center", padding: "32px 36px" }}>
        <div style={{ maxWidth: 800, margin: "0 auto", width: "100%" }}>
          <AgentIntakeHeader label="MORPHIS" title="Key Visual" done={true} />
          <KVPanel m={milestone} liveMsg={liveMsg} reelMilestone={reelMilestone} />
        </div>
      </div>
    </div>
  );
}

// ── Reel Generator intake view ────────────────────────────────
function ReelIntakeView({ milestone, liveMsg }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
}) {
  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  const videoB64 = milestone.video_b64 ? String(milestone.video_b64) : "";

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "linear-gradient(180deg, #faf5ff 0%, #ffffff 180px)" }}>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <AgentIntakeHeader label="KINETIK" title="Campaign Reel" done={true} />
        {videoB64 ? (
          <div style={{ background: "#0f172a", borderRadius: 16, padding: "20px 24px" }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: "#f59e0b",
              letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 12 }}>
              🎬 Campaign Reel · 6s
            </div>
            <video controls autoPlay loop muted playsInline
              style={{ width: "100%", borderRadius: 10, display: "block" }}
              src={`data:video/mp4;base64,${videoB64}`} />
            <a href={`data:video/mp4;base64,${videoB64}`} download="campaign-reel.mp4"
              style={{ display: "inline-block", marginTop: 12, fontSize: 12, fontWeight: 700,
                color: "#f59e0b", textDecoration: "none" }}>
              ⬇ Download Reel
            </a>
          </div>
        ) : (
          <AgentGeneratingView liveMsg={liveMsg} />
        )}
      </div>
    </div>
  );
}

// ── Channel Adapter intake view ───────────────────────────────
function ChannelAdapterIntakeView({ milestone, liveMsg }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
}) {
  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "linear-gradient(180deg, #faf5ff 0%, #ffffff 180px)" }}>
      <div style={{ maxWidth: 860, margin: "0 auto" }}>
        <AgentIntakeHeader label="POLY" title="Publishing to Channels" done={true} />
        <ChannelPanel m={milestone} liveMsg={liveMsg} />
      </div>
    </div>
  );
}

// ── Gradient Orb (A2A logo style) ────────────────────────────
function GradientOrb({ size = 40 }: { size?: number }) {
  const u = `orb${size}`;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100"
      style={{ display: "block", flexShrink: 0,
        filter: `drop-shadow(0 ${size*0.07}px ${size*0.28}px rgba(200,40,200,0.38)) drop-shadow(0 0 ${size*0.08}px rgba(255,255,255,0.5))` }}>
      <defs>
        {/* Base: hot magenta-pink centre → deep purple-lavender edge */}
        <radialGradient id={`${u}a`} cx="36%" cy="54%" r="80%">
          <stop offset="0%"   stopColor="#f028cc"/>
          <stop offset="22%"  stopColor="#cc3cf2"/>
          <stop offset="50%"  stopColor="#8840e0"/>
          <stop offset="78%"  stopColor="#b898f8"/>
          <stop offset="100%" stopColor="#ddd6fe"/>
        </radialGradient>
        {/* Warm coral-peach bloom on right — matches logo warmth */}
        <radialGradient id={`${u}b`} cx="76%" cy="54%" r="42%">
          <stop offset="0%"   stopColor="#ffaacc" stopOpacity="0.75"/>
          <stop offset="100%" stopColor="#ffaacc" stopOpacity="0"/>
        </radialGradient>
        {/* Bright glass specular highlight — top-RIGHT (as in logo) */}
        <radialGradient id={`${u}c`} cx="70%" cy="24%" r="32%">
          <stop offset="0%"   stopColor="#ffffff" stopOpacity="0.9"/>
          <stop offset="60%"  stopColor="#ffffff" stopOpacity="0.25"/>
          <stop offset="100%" stopColor="#ffffff" stopOpacity="0"/>
        </radialGradient>
        {/* Soft bottom depth shadow */}
        <radialGradient id={`${u}d`} cx="50%" cy="90%" r="36%">
          <stop offset="0%"   stopColor="#300060" stopOpacity="0.4"/>
          <stop offset="100%" stopColor="#300060" stopOpacity="0"/>
        </radialGradient>
        <clipPath id={`${u}clip`}><circle cx="50" cy="50" r="49"/></clipPath>
      </defs>

      {/* Layered sphere */}
      <circle cx="50" cy="50" r="49" fill={`url(#${u}a)`}/>
      <circle cx="50" cy="50" r="49" fill={`url(#${u}b)`}/>
      <circle cx="50" cy="50" r="49" fill={`url(#${u}c)`}/>
      <circle cx="50" cy="50" r="49" fill={`url(#${u}d)`}/>

      {/* 4-point sparkle star — large and luminous */}
      <path clipPath={`url(#${u}clip)`}
        d="M50 18 Q51.8 35 59 42 Q76 48 80 50 Q76 52 59 58 Q51.8 65 50 82 Q48.2 65 41 58 Q24 52 20 50 Q24 48 41 42 Q48.2 35 50 18 Z"
        fill="white"/>

      {/* Soft white rim */}
      <circle cx="50" cy="50" r="48.5" fill="none"
        stroke="rgba(255,255,255,0.3)" strokeWidth="1.5"/>
    </svg>
  );
}

// ── Home screen ───────────────────────────────────────────────
function HomeScreen({ onStart }: { onStart: () => void }) {
  const [input, setInput] = useState("");
  return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "0 32px" }}>
      <div style={{ maxWidth: 680, width: "100%", textAlign: "center" as const }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 32 }}>
          <GradientOrb size={80} />
        </div>
        <h1 style={{ fontSize: 40, fontWeight: 800, color: "#111827", lineHeight: 1.2,
          marginBottom: 20, letterSpacing: "-0.03em", fontFamily: "inherit" }}>
          Campaign Intelligence,{" "}
          <span style={{
            background: ORB_BG,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
          }}>Creative Excellence</span>
        </h1>
        <p style={{ fontSize: 15, color: "#6b7280", lineHeight: 1.8, marginBottom: 40,
          maxWidth: 560, margin: "0 auto 40px" }}>
          Deploy a coordinated team of AI agents that analyze culture, develop strategy, generate creative assets,
          and prepare content for every marketing channel — all from a single campaign brief.
        </p>

        <div style={{ background: "white", border: "1.5px solid #e5e7eb", borderRadius: 16,
          padding: "20px 24px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", textAlign: "left" as const }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
            <span style={{ fontSize: 15, marginTop: 3, color: "#9ca3af" }}>✦</span>
            <textarea
              style={{ flex: 1, border: "none", outline: "none", fontSize: 15, color: "#111827",
                resize: "none" as const, background: "transparent", minHeight: 56,
                fontFamily: "inherit", lineHeight: 1.6 }}
              placeholder="e.g. Summer hair care campaign for Gen Z UK audience..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onStart(); }}}
            />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
            <div style={{ fontSize: 12, color: "#9ca3af" }}>Press → or Enter to start</div>
            <button onClick={onStart} style={{
              width: 42, height: 42, borderRadius: "50%",
              background: ORB_BG,
              border: "none", cursor: "pointer", color: "white", fontSize: 18,
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 4px 12px rgba(124,58,237,0.4)",
            }}>→</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────

function SidebarBtn({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick?: () => void }) {
  const [hov, setHov] = useState(false);
  return (
    <button onClick={onClick}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{ width: "100%", display: "flex", alignItems: "center", gap: 9, padding: "7px 10px",
        borderRadius: 8, border: "none", background: hov ? "#f3f4f6" : "none", cursor: "pointer",
        fontSize: 13, color: "#374151", fontFamily: "inherit", textAlign: "left" as const,
        transition: "background 0.15s" }}>
      <span style={{ width: 16, display: "flex", alignItems: "center", justifyContent: "center",
        color: "#6b7280", flexShrink: 0 }}>{icon}</span>
      {label}
    </button>
  );
}

function Sidebar({ history, onNew }: {
  history: Array<{ id: string; name: string }>;
  onNew: () => void;
}) {
  return (
    <div style={{ width: 270, flexShrink: 0, height: "100vh", background: "#fafafa",
      borderRight: "1px solid #e5e7eb", display: "flex", flexDirection: "column" as const }}>

      {/* Logo */}
      <div style={{ padding: "18px 18px 12px", display: "flex", alignItems: "center", gap: 10 }}>
        <GradientOrb size={36} />
        <div style={{ display: "flex", flexDirection: "column" as const, lineHeight: 1.25 }}>
          {/* A2A — large gradient wordmark */}
          <span style={{
            fontSize: 20, fontWeight: 900, letterSpacing: "-0.04em",
            fontFamily: "'Inter', system-ui, sans-serif",
            background: "linear-gradient(110deg, #7c3aed 0%, #c026d3 45%, #f97316 100%)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
          }}>A2A</span>
          {/* Tagline — small caps, shimmer gradient */}
          <span style={{
            fontSize: 8.5, fontWeight: 700, letterSpacing: "0.12em",
            textTransform: "uppercase" as const,
            background: "linear-gradient(110deg, #9b59b6 0%, #e91e8c 50%, #f97316 100%)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
          }}>Marketing · Advertising · Media</span>
        </div>
      </div>

      {/* Nav actions */}
      <div style={{ padding: "2px 8px 10px" }}>
        <SidebarBtn onClick={onNew} icon={
          <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2}>
            <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
        } label="Create New" />
        <SidebarBtn icon={
          <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2}>
            <circle cx={11} cy={11} r={8}/><path d="M21 21l-4.35-4.35"/>
          </svg>
        } label="Search" />
      </div>

      {/* History */}
      <div style={{ flex: 1, overflowY: "auto" as const, padding: "4px 18px 8px",
        borderTop: "1px solid #f3f4f6", marginTop: 4 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: "#9ca3af", letterSpacing: "0.06em",
          textTransform: "uppercase" as const, marginBottom: 4, paddingLeft: 2, paddingTop: 8 }}>
          History
        </div>
        {history.length === 0 ? (
          <div style={{ fontSize: 12, color: "#d1d5db", padding: "4px 10px" }}>No campaigns yet</div>
        ) : (
          history.slice(0, 8).map(h => (
            <div key={h.id} style={{ display: "flex", alignItems: "center", gap: 9, padding: "6px 10px",
              borderRadius: 8, cursor: "pointer" }}
              onMouseEnter={e => (e.currentTarget.style.background = "#f3f4f6")}
              onMouseLeave={e => (e.currentTarget.style.background = "none")}>
              <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth={1.8}
                style={{ flexShrink: 0 }}>
                <circle cx={12} cy={12} r={10}/><polyline points="12 6 12 12 16 14"/>
              </svg>
              <span style={{ fontSize: 12, color: "#6b7280", overflow: "hidden",
                textOverflow: "ellipsis", whiteSpace: "nowrap" as const }}>
                {h.name}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Powered by Infosys Aster — always visible at sidebar bottom */}
      <div style={{ padding: "14px 18px", borderTop: "1px solid #f3f4f6", flexShrink: 0 }}>
        <AsterLogo size={0.65} />
      </div>
    </div>
  );
}

// ── Steps panel ───────────────────────────────────────────────
// All 7 agents mapped to their workflow stage
const WORKFLOW_STAGES = [
  { id: "brief",    label: "Brief Intake",        agents: ["briefing"] },
  { id: "creative", label: "Creative Direction",  agents: ["culture", "strategy", "copy", "kv", "reel"] },
  { id: "channel",  label: "Channel Adoption",    agents: ["channel"] },
  { id: "activate", label: "Activation",          agents: [] as string[] },
  { id: "perform",  label: "Performance",         agents: [] as string[] },
];

function StepsPanel({ campaignName, activeStageId, agentStatus, liveLog, onEditName }: {
  campaignName: string;
  activeStageId: string | null;
  agentStatus: Record<string, string>;
  liveLog: AgentEvent[];
  onEditName: () => void;
}) {
  const [editing, setEditing]   = useState(false);
  const [nameVal, setNameVal]   = useState(campaignName);
  const [request, setRequest]   = useState("");
  const activeIdx = WORKFLOW_STAGES.findIndex(s => s.id === activeStageId);

  useEffect(() => { setNameVal(campaignName); }, [campaignName]);

  // Latest message for a given agent key
  const agentMsg = (key: string) =>
    [...liveLog].reverse().find(e => e.agent === key && e.status === "running")?.message ?? null;

  return (
    <div style={{ width: 260, flexShrink: 0, height: "100vh", background: "white",
      borderRight: "1px solid #e5e7eb", display: "flex", flexDirection: "column" as const }}>

      {/* Campaign name header */}
      <div style={{ padding: "18px 18px 14px", borderBottom: "1px solid #f3f4f6",
        display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 26, height: 26, borderRadius: 6, background: "#f3f4f6", flexShrink: 0,
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13 }}>□</div>
        {editing ? (
          <input autoFocus value={nameVal} onChange={e => setNameVal(e.target.value)}
            onBlur={() => { onEditName(); setEditing(false); }}
            onKeyDown={e => { if (e.key === "Enter") { onEditName(); setEditing(false); }}}
            style={{ flex: 1, fontSize: 13, fontWeight: 600, border: "none",
              outline: "1.5px solid #7c3aed", borderRadius: 6, padding: "2px 6px", fontFamily: "inherit" }} />
        ) : (
          <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: "#111827",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const }}>
            {campaignName}
          </span>
        )}
        <button onClick={() => setEditing(true)}
          style={{ background: "none", border: "none", cursor: "pointer",
            color: "#9ca3af", fontSize: 13, padding: 2, flexShrink: 0 }}>✎</button>
      </div>

      {/* Workflow stages — timeline layout */}
      <div style={{ flex: 1, overflowY: "auto" as const, padding: "20px 0 8px" }}>
        {WORKFLOW_STAGES.map((stage, idx) => {
          const isActive    = stage.id === activeStageId;
          const isDone      = activeIdx > idx;
          const isLast      = idx === WORKFLOW_STAGES.length - 1;
          const stageAgents = HARNESS_STAGES.filter(s => stage.agents.includes(s.key));

          return (
            <div key={stage.id} style={{ display: "flex", paddingLeft: 18 }}>
              {/* Left rail: circle + connector line */}
              <div style={{ display: "flex", flexDirection: "column" as const,
                alignItems: "center", width: 26, flexShrink: 0 }}>
                {/* Step circle — A2A gradient for done/active, grey for future */}
                <div style={{
                  width: 24, height: 24, borderRadius: "50%", flexShrink: 0, zIndex: 1,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 10, fontWeight: 700,
                  background: (isDone || isActive)
                    ? ORB_BG
                    : "white",
                  color: (isDone || isActive) ? "white" : "#9ca3af",
                  border: (isDone || isActive) ? "none" : "1.5px solid #d1d5db",
                  boxShadow: isActive ? "0 0 0 4px rgba(124,58,237,0.15)" : "none",
                  transition: "all 0.3s",
                }}>
                  {isDone ? "✓" : idx + 1}
                </div>
                {/* Connector line */}
                {!isLast && (
                  <div style={{
                    width: 1.5, flex: 1, minHeight: 20, marginTop: 2,
                    background: isDone
                      ? "linear-gradient(rgba(167,139,250,0.6), rgba(196,132,252,0.3))"
                      : "#e5e7eb",
                    transition: "background 0.4s",
                  }} />
                )}
              </div>

              {/* Right content */}
              <div style={{ flex: 1, paddingLeft: 12, paddingBottom: isLast ? 0 : 20, paddingRight: 18 }}>
                {/* Stage label */}
                <div style={{
                  fontSize: 13, fontWeight: isActive ? 700 : 500, paddingTop: 3,
                  color: isActive ? "#111827" : isDone ? "#374151" : "#9ca3af",
                  marginBottom: (isDone || isActive) && stageAgents.length > 0 ? 10 : 0,
                }}>
                  {stage.label}
                </div>

                {/* Agents — active/done stage */}
                {stageAgents.length > 0 && (isDone || isActive) && (
                  <div style={{ display: "flex", flexDirection: "column" as const, gap: 2 }}>
                    {stageAgents.map(s => {
                      const st      = agentStatus[s.key];
                      const isRun   = st === "running";
                      const isDoneA = st === "done";
                      const msg     = isRun ? agentMsg(s.key) : null;
                      return (
                        <div key={s.key} style={{ marginBottom: isRun && msg ? 6 : 2 }}>
                          {/* Agent row */}
                          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "3px 0" }}>
                            <span style={{
                              fontSize: 11, width: 14, textAlign: "center" as const, flexShrink: 0,
                              color: isDoneA ? "#7c3aed" : isRun ? "#7c3aed" : "#d1d5db",
                              fontWeight: 700,
                            }}>✦</span>
                            <span style={{
                              fontSize: 12, flex: 1, lineHeight: 1.3,
                              fontWeight: isRun ? 600 : 400,
                              color: isDoneA ? "#6b7280" : isRun ? "#7c3aed" : "#9ca3af",
                            }}>
                              {s.label}
                            </span>
                            {isDoneA && (
                              <span style={{ fontSize: 11, color: "#10b981", fontWeight: 700, flexShrink: 0 }}>✓</span>
                            )}
                            {isRun && (
                              <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
                                {[0,1,2].map(d => (
                                  <div key={d} style={{ width: 3, height: 3, borderRadius: "50%",
                                    background: "#7c3aed",
                                    animation: `wave-dot 1.2s ${d * 0.2}s ease-in-out infinite` }} />
                                ))}
                              </div>
                            )}
                          </div>
                          {/* Live message — shown below running agent */}
                          {isRun && msg && (
                            <div style={{
                              marginTop: 4, marginLeft: 20, fontSize: 11,
                              color: "#6b7280", lineHeight: 1.55,
                              display: "-webkit-box", WebkitLineClamp: 3,
                              WebkitBoxOrient: "vertical" as const, overflow: "hidden",
                            }}>
                              {msg}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Agents — future/inactive stage */}
                {stageAgents.length > 0 && !isDone && !isActive && (
                  <div style={{ display: "flex", flexDirection: "column" as const, gap: 2 }}>
                    {stageAgents.map(s => (
                      <div key={s.key} style={{ display: "flex", alignItems: "center", gap: 6, padding: "3px 0" }}>
                        <span style={{ fontSize: 11, width: 14, textAlign: "center" as const,
                          color: "#e5e7eb", fontWeight: 700, flexShrink: 0 }}>✦</span>
                        <span style={{ fontSize: 12, color: "#d1d5db" }}>{s.label}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Request input */}
      <div style={{ padding: "12px 14px", borderTop: "1px solid #f3f4f6" }}>
        <div style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 12, padding: "10px 12px" }}>
          <textarea placeholder="Describe your request..." value={request}
            onChange={e => setRequest(e.target.value)}
            style={{ width: "100%", border: "none", outline: "none", background: "transparent",
              fontSize: 12, color: "#374151", resize: "none" as const,
              fontFamily: "inherit", lineHeight: 1.5, minHeight: 36, maxHeight: 72 }} />
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
            <div style={{ width: 24, height: 24, borderRadius: "50%", border: "1.5px solid #e5e7eb",
              background: "white", display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 13, cursor: "pointer", color: "#9ca3af" }}>+</div>
            <button style={{
              width: 30, height: 30, borderRadius: "50%",
              background: request.trim() ? "#7c3aed" : "#e5e7eb",
              border: "none", cursor: request.trim() ? "pointer" : "default",
              color: "white", fontSize: 14,
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "background 0.2s",
            }}>→</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────
export default function App() {
  const { state, startFullCampaign, reset } = usePipeline();

  const [wizardStarted, setWizardStarted]   = useState(false);
  const [campaignName,  setCampaignName]    = useState("New Campaign");
  const [briefData,     setBriefData]       = useState<import("./types/pipeline").HarnessBriefRequest | null>(null);
  const [history,       setHistory]         = useState<Array<{ id: string; name: string }>>([]);

  // Add to history when pipeline completes
  useEffect(() => {
    if (state.status === "done" && state.campaign_id) {
      setHistory(h => [
        { id: state.campaign_id!, name: campaignName },
        ...h.filter(x => x.id !== state.campaign_id).slice(0, 5),
      ]);
    }
  }, [state.status, state.campaign_id]);

  const handleReset = () => {
    reset();
    setWizardStarted(false);
    setCampaignName("New Campaign");
  };

  const handleLaunch = (brief: import("./types/pipeline").HarnessBriefRequest) => {
    if (brief.campaign_name?.trim()) setCampaignName(brief.campaign_name.trim());
    setBriefData(brief);
    startFullCampaign(brief);
  };

  // Derive which workflow stage is currently active
  const activeStageId = (() => {
    if (state.status === "idle") return wizardStarted ? "brief" : null;
    if (state.status === "running") {
      const as = state.agentStatus;
      if (["channel"].some(k => as[k] === "running" || as[k] === "done")) return "channel";
      if (["culture","strategy","copy","kv","reel"].some(k => as[k] === "running" || as[k] === "done")) return "creative";
      return "brief";
    }
    if (state.status === "done") return "activate";
    return null;
  })();

  return (
    <ErrorBoundary>
      <div style={{ display: "flex", height: "100vh", overflow: "hidden",
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif" }}>

        {/* Left: Sidebar */}
        <Sidebar history={history} onNew={handleReset} />

        {/* Middle: Steps panel — hidden during wakeup (before any agent starts) */}
        {(state.status === "running" || state.status === "done") &&
          !(state.status === "running" && !state.agentStatus["briefing"]) && (
          <StepsPanel
            campaignName={campaignName}
            activeStageId={activeStageId}
            agentStatus={state.agentStatus}
            liveLog={state.liveLog}
            onEditName={() => {}}
          />
        )}

        {/* Right: Content area */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column" as const,
          overflow: "hidden", background: "#ffffff" }}>

          {/* Top bar — sidebar toggle on home, breadcrumb during pipeline */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "12px 20px", borderBottom: "1px solid #f3f4f6", flexShrink: 0, minHeight: 52 }}>
            {/* Left: sidebar toggle icon */}
            <button style={{ width: 32, height: 32, borderRadius: 8, border: "1px solid #e5e7eb",
              background: "white", cursor: "pointer", display: "flex", alignItems: "center",
              justifyContent: "center", color: "#6b7280", flexShrink: 0 }}>
              <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <rect x={3} y={3} width={7} height={18} rx={1}/><rect x={14} y={3} width={7} height={18} rx={1}/>
              </svg>
            </button>

            {/* Right: pipeline title + action buttons — hidden on wakeup screen */}
            {(state.status === "running" || state.status === "done") &&
              !(state.status === "running" && !state.agentStatus["briefing"]) && (
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                {/* <h2 style={{ fontSize: 15, fontWeight: 600, color: "#111827", margin: 0 }}>
                  {state.status === "running"
                    ? (WORKFLOW_STAGES.find(s => s.id === activeStageId)?.label ?? "Running")
                    : "Campaign Ready ✅"}
                </h2> */}
                {/* <div style={{ display: "flex", gap: 10 }}>
                    {state.status === "done" && (
                      <button style={{ display: "flex", alignItems: "center", gap: 6,
                        padding: "7px 16px", borderRadius: 8, border: "none", cursor: "pointer",
                        background: "linear-gradient(135deg, #7c3aed, #a855f7)",
                        color: "white", fontSize: 13, fontWeight: 700, fontFamily: "inherit" }}>
                        ✓ Accept
                      </button>
                    )}
                    <button onClick={handleReset}
                      style={{ padding: "7px 16px", borderRadius: 8, border: "1.5px solid #e5e7eb",
                        cursor: "pointer", background: "white", color: "#374151",
                        fontSize: 13, fontWeight: 600, fontFamily: "inherit" }}>
                      Cancel
                    </button>
                  </div> */}
              </div>
            )}
          </div>

          {/* Content */}
          <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" as const }}>
            {state.status === "idle" && !wizardStarted && (
              <HomeScreen onStart={() => setWizardStarted(true)} />
            )}

            {state.status === "idle" && wizardStarted && (
              <BriefForm onFullCampaign={handleLaunch} />
            )}

            {/* Agent network wakeup — shown immediately after launch, before Logos starts */}
            {state.status === "running" && activeStageId === "brief" &&
              !state.agentStatus["briefing"] && (
              <AgentNetworkWakeUp />
            )}

            {/* Logos (briefing agent) intake view */}
            {state.status === "running" && activeStageId === "brief" &&
              !!state.agentStatus["briefing"] && (
              <BriefIntakeView
                brief={briefData}
                milestone={state.milestones["briefing"]}
                liveMsg={[...state.liveLog].reverse().find(e => e.agent === "briefing" && e.status === "running")?.message ?? null}
                agentDone={state.agentStatus["briefing"] === "done"}
              />
            )}

            {state.status === "running" && activeStageId !== "brief" && (() => {
              // Prioritise agentStatus so we get the right agent the instant it
              // starts, even before any liveLog entries have arrived for it.
              const focusKey =
                HARNESS_STAGES.find(s => state.agentStatus[s.key] === "running")?.key
                ?? [...state.liveLog].reverse().find(e => e.status === "running")?.agent
                ?? [...state.liveLog].reverse().find(e => e.status === "done")?.agent
                ?? null;
              const liveMsg = (key: string) =>
                [...state.liveLog].reverse().find(e => e.agent === key && e.status === "running")?.message ?? null;

              if (focusKey === "strategy") return (
                <StrategyIntakeView
                  milestone={state.milestones["strategy"]}
                  liveMsg={liveMsg("strategy")}
                />
              );
              if (focusKey === "copy") return (
                <CopyIntakeView
                  milestone={state.milestones["copy"]}
                  liveMsg={liveMsg("copy")}
                />
              );
              if (focusKey === "culture") return (
                <CultureIntakeView
                  milestone={state.milestones["culture"]}
                  liveMsg={liveMsg("culture")}
                />
              );
              if (focusKey === "kv") return (
                <KVIntakeView
                  milestone={state.milestones["kv"]}
                  liveMsg={liveMsg("kv")}
                  reelMilestone={state.milestones["reel"]}
                />
              );
              if (focusKey === "reel") return (
                <ReelIntakeView
                  milestone={state.milestones["reel"]}
                  liveMsg={liveMsg("reel")}
                />
              );
              if (focusKey === "channel") return (
                <ChannelAdapterIntakeView
                  milestone={state.milestones["channel"]}
                  liveMsg={liveMsg("channel")}
                />
              );
              // fallback (focusKey null)
              return (
                <RunningView
                  agentStatus={state.agentStatus}
                  liveLog={state.liveLog}
                  milestones={state.milestones}
                  compact={true}
                />
              );
            })()}

            {state.status === "error" && (() => {
              const isAuth = state.error?.includes("credentials") || state.error?.includes("auth");
              return (
                <div style={styles.errorPage}>
                  <div style={styles.errorCard}>
                    <div style={styles.errorTitle}>⚠️ Pipeline Error</div>
                    <div style={styles.errorMsg}>{state.error}</div>
                    {isAuth && (
                      <div style={styles.authHint}>
                        <strong>Fix:</strong> Run this in your terminal, then restart the harness:
                        <pre style={styles.authCmd}>gcloud auth application-default login</pre>
                      </div>
                    )}
                    <button className="reset-btn" onClick={handleReset} style={{ marginTop: 20 }}>Try Again</button>
                  </div>
                </div>
              );
            })()}

            {state.status === "done" && (
              <ResultsView
                output={state.pipeline_output}
                campaignId={state.campaign_id}
              />
            )}
          </div>
        </div>
      </div>
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
