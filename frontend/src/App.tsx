import { useState } from "react";
import "./App.css";
import { usePipeline } from "./hooks/usePipeline";
import type { HarnessBriefRequest } from "./types/pipeline";

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
  { id: "McDonalds", label: "McDonald's", emoji: "🍔" },
  { id: "Rnorr",     label: "Rnorr",      emoji: "🥣" },
  { id: "Sunglow",   label: "Sunglow",    emoji: "✨" },
  { id: "Boozt",     label: "Boozt",      emoji: "💨" },
];

const BRAND_PRODUCTS: Record<string, string[]> = {
  McDonalds: ["McSpicy", "McSpicy Deluxe", "Big Mac", "McDouble", "McVeggie",
              "Happy Meal", "McFlurry", "McCafé", "Chicken McNuggets", "McValue Menu"],
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
  McDonalds: "Burgers & Chicken",
  Rnorr:     "Dry Cook-In Sauces",
  Sunglow:   "Hair Care",
  Boozt:     "Hair Styling & Volume",
};

const BRAND_FAN_TRUTHS: Record<string, string[]> = {
  McDonalds: [
    "McDonald's fans love the ritual of the first bite of something new",
    "Friday nights belong to McDonald's",
    "Nostalgia is the most powerful flavour",
    "McDonald's is the social glue between friends",
    "McDonald's is the reward after a long day",
  ],
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
  McDonalds: ["Spicy food lovers", "Families", "Students", "Deal hunters", "Night owls", "Gamers", "Sports fans"],
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
const HARNESS_STAGES = [
  { key: "briefing",  icon: "📋", label: "Briefing Agent",    desc: "Validating campaign brief & fan truth" },
  { key: "culture",   icon: "🌍", label: "Culture Analyst",   desc: "Researching cultural trends" },
  { key: "strategy",  icon: "💡", label: "Creative Director", desc: "Building big idea & strategy" },
  { key: "copy",      icon: "✍️", label: "Copy Agent",        desc: "Writing copy variants" },
  { key: "kv",        icon: "🎨", label: "KV Generator",      desc: "Creating key visuals" },
  { key: "channel",   icon: "📡", label: "Channel Adapter",   desc: "Adapting assets for channels" },
];

// ── Brief Form (6-step wizard) ───────────────────────────────
function BriefForm({ onStart }: { onStart: (brief: HarnessBriefRequest) => void }) {
  const [step, setStep] = useState(0);
  const [d, setD] = useState<WizardData>({
    campaignName: "",
    brand: "McDonalds",
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

  const stepContent = () => {
    switch (step) {
      case 0:
        return (
          <>
            <div className="wizard-step-label">Step 1 of 7</div>
            <h2 className="wizard-heading">Select your <span className="gradient-text">brand</span></h2>
            <p className="wizard-subheading">Which brand is this campaign for?</p>
            <div className="goal-grid" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
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
            <input className="dark-input" placeholder="Campaign name (e.g. McSpicy Summer 2026)"
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
            : <button className="wizard-launch-btn" disabled={!canProceed()} onClick={handleLaunch}>
                ⚡ Launch Campaign
              </button>}
        </div>
      </div>
    </div>
  );
}

// ── Running view (pipeline in progress) ─────────────────────
function RunningView() {
  return (
    <div style={styles.runningPage}>
      <div style={styles.runningCard}>
        <div style={styles.runningTitle}>🤖 Agents are working…</div>
        <p style={styles.runningSubtitle}>
          The pipeline is generating your campaign. This typically takes 2–5 minutes.
        </p>
        <div style={styles.stageList}>
          {HARNESS_STAGES.map((s, i) => (
            <div key={s.key} className="stage-row" style={{ animationDelay: `${i * 0.8}s` }}>
              <span style={styles.stageIcon}>{s.icon}</span>
              <div style={styles.stageInfo}>
                <div style={styles.stageName}>{s.label}</div>
                <div style={styles.stageDesc}>{s.desc}</div>
              </div>
              <div className="stage-pulse" style={{ animationDelay: `${i * 0.8}s` }} />
            </div>
          ))}
        </div>
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
        <circle cx="44" cy="44" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
        <circle cx="44" cy="44" r={r} fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
          transform="rotate(-90 44 44)" style={{ transition: "stroke-dasharray 1s ease" }} />
        <text x="44" y="41" textAnchor="middle" fill={color} fontSize="18" fontWeight="700" fontFamily="Inter,sans-serif">{score}</text>
        <text x="44" y="56" textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="10" fontFamily="Inter,sans-serif">/100</text>
      </svg>
      <div>
        <div style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", textTransform: "uppercase" as const, letterSpacing: "0.08em", marginBottom: 4 }}>Fan Truth Score</div>
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
        <span style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>{metric}</span>
        <span style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", marginLeft: 6 }}>— {target}</span>
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, color: c.color, padding: "2px 8px",
        background: `${c.color}18`, borderRadius: 12 }}>{flag}</span>
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
  const statusColor = isReady ? "#10b981" : brief?.status === "INCOMPLETE" ? "#ef4444" : "#f59e0b";

  // Parse CDP insights into readable lines
  const cdpLines = output?.audience_insights
    ? String(output.audience_insights).split("\n").filter(l => l.trim())
    : [];

  return (
    <div style={styles.resultsPage}>
      {/* Header */}
      <div style={styles.resultsHero}>
        <div style={styles.resultsHeroInner}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 12, background: "rgba(16,185,129,0.15)",
              border: "1px solid rgba(16,185,129,0.3)", display: "flex", alignItems: "center",
              justifyContent: "center", fontSize: 20 }}>✅</div>
            <div>
              <div style={styles.resultsTitle}>Campaign Brief Validated</div>
              {campaignId && <div style={styles.campaignIdTag}>#{campaignId}</div>}
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ padding: "6px 16px", borderRadius: 20, fontSize: 12, fontWeight: 700,
              background: `${statusColor}18`, color: statusColor,
              border: `1px solid ${statusColor}30`, letterSpacing: "0.05em" }}>
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
                <div style={{ fontSize: 14, color: "#e2e8f0", fontStyle: "italic", lineHeight: 1.6 }}>
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
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.35)", fontWeight: 600,
                  letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 8 }}>KPIs</div>
                {brief.kpis.map((k: any, i: number) => (
                  <KPIRow key={i} metric={k.metric} target={k.target} flag={k.flag} note={k.note} />
                ))}
              </div>
            )}

            {/* Summary */}
            {(brief.validation_notes || brief.brief_summary) && (
              <p style={{ fontSize: 13, color: "#64748b", lineHeight: 1.7, margin: 0, paddingTop: 12,
                borderTop: "1px solid rgba(255,255,255,0.06)" }}>
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

          const stat = (label: string, val: string | null, accent = "#7c3aed") => val ? (
            <div style={{ flex: 1, minWidth: 100, padding: "10px 12px", borderRadius: 10,
              background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
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
                  background: "rgba(124,58,237,0.15)", color: "#a78bfa",
                  border: "1px solid rgba(124,58,237,0.25)", letterSpacing: "0.06em" }}>
                  KAGGLE CDP
                </span>
              </div>

              {/* Profile count */}
              <div style={{ marginBottom: 12, padding: "10px 14px", borderRadius: 10,
                background: "linear-gradient(135deg, rgba(124,58,237,0.1), rgba(37,99,235,0.08))",
                border: "1px solid rgba(124,58,237,0.2)" }}>
                <div style={{ fontSize: 20, fontWeight: 800, color: "#a78bfa" }}>{profileCount}</div>
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
                        background: "rgba(59,130,246,0.12)", color: "#60a5fa",
                        border: "1px solid rgba(59,130,246,0.25)", fontWeight: 600 }}>
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
                borderBottom: i < arr.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none" }}>
                <span style={{ fontSize: 11, color: "#475569", fontWeight: 600,
                  textTransform: "uppercase" as const, letterSpacing: "0.07em", flexShrink: 0, paddingRight: 12 }}>
                  {row.label}
                </span>
                <span style={{ fontSize: 12, color: "#cbd5e1", textAlign: "right" as const }}>
                  {String(row.value)}
                </span>
              </div>
            ))}

            {/* Brief summary */}
            {brief.brief_summary && (
              <div style={{ marginTop: 14, padding: "10px 12px", borderRadius: 8,
                background: "rgba(255,255,255,0.03)", borderLeft: "2px solid #3b82f6" }}>
                <div style={{ fontSize: 10, color: "#3b82f6", fontWeight: 600,
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

        {/* ── Creative Strategy ── */}
        {strategy && (strategy.hero_message || strategy.big_idea || strategy.strategic_framework) && (
          <div style={{ ...styles.resultCard, gridColumn: "1 / -1",
            background: "linear-gradient(135deg, rgba(124,58,237,0.08), rgba(37,99,235,0.05))",
            border: "1px solid rgba(124,58,237,0.2)" }}>
            <div style={styles.cardHeader}>💡 Creative Strategy</div>
            {/* Hero message / Big Idea */}
            <div style={{ fontSize: 22, fontWeight: 800, color: "#a78bfa",
              fontStyle: "italic", lineHeight: 1.4, marginBottom: 20,
              borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: 16 }}>
              "{strategy.big_idea || strategy.hero_message}"
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
              {strategy.strategic_framework && (
                <div style={{ padding: "12px 14px", borderRadius: 10, background: "rgba(255,255,255,0.03)" }}>
                  <div style={styles.cardLabel}>Strategic Framework</div>
                  <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.6, marginTop: 6 }}>{strategy.strategic_framework}</div>
                </div>
              )}
              {strategy.culture_context && (
                <div style={{ padding: "12px 14px", borderRadius: 10, background: "rgba(255,255,255,0.03)" }}>
                  <div style={styles.cardLabel}>Cultural Context</div>
                  <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.6, marginTop: 6 }}>{strategy.culture_context}</div>
                </div>
              )}
              {strategy.handoff_message && (
                <div style={{ padding: "12px 14px", borderRadius: 10, background: "rgba(255,255,255,0.03)" }}>
                  <div style={styles.cardLabel}>Creative Brief</div>
                  <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.6, marginTop: 6 }}>{strategy.handoff_message}</div>
                </div>
              )}
            </div>
            {strategy.messaging_pillars?.length > 0 && (
              <div style={{ marginTop: 16, display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
                {strategy.messaging_pillars.map((p: string, i: number) => (
                  <span key={i} style={{ fontSize: 12, padding: "5px 12px", borderRadius: 20,
                    background: "rgba(124,58,237,0.12)", color: "#a78bfa",
                    border: "1px solid rgba(124,58,237,0.25)" }}>{p}</span>
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
                  <div style={{ fontSize: 20, fontWeight: 800, color: "#f1f5f9", lineHeight: 1.3 }}>
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
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#f1f5f9", lineHeight: 1.4 }}>
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
                  <div style={{ fontSize: 15, fontWeight: 700, color: "#f1f5f9", lineHeight: 1.4 }}>
                    {copy.long?.headline || copy.long_copy}
                  </div>
                  {copy.long?.body && <div style={{ fontSize: 13, color: "#94a3b8", marginTop: 8, lineHeight: 1.7 }}>{copy.long.body}</div>}
                </div>
              )}
            </div>
            {/* CTA + Platform copy */}
            {(copy.cta || copy.instagram_caption || copy.tiktok_hook) && (
              <div style={{ marginTop: 16, display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
                {copy.cta && (
                  <div style={{ padding: "10px 14px", borderRadius: 10, background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.06)", textAlign: "center" as const }}>
                    <div style={styles.cardLabel}>CTA</div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: "#e2e8f0", marginTop: 4 }}>{copy.cta}</div>
                  </div>
                )}
                {copy.instagram_caption && (
                  <div style={{ padding: "10px 14px", borderRadius: 10, background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.06)" }}>
                    <div style={styles.cardLabel}>Instagram Caption</div>
                    <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4, lineHeight: 1.5 }}>{copy.instagram_caption}</div>
                  </div>
                )}
                {copy.tiktok_hook && (
                  <div style={{ padding: "10px 14px", borderRadius: 10, background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.06)" }}>
                    <div style={styles.cardLabel}>TikTok Hook (3s)</div>
                    <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4, lineHeight: 1.5 }}>{copy.tiktok_hook}</div>
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
      </div>
    </div>
  );
}

// ── Main App ─────────────────────────────────────────────────
export default function App() {
  const { state, startCampaign, reset } = usePipeline();

  if (state.status === "idle") {
    return <BriefForm onStart={startCampaign} />;
  }

  if (state.status === "running") {
    return <RunningView />;
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
    <ResultsView
      output={state.pipeline_output}
      campaignId={state.campaign_id}
      onReset={reset}
    />
  );
}

// ── Styles ───────────────────────────────────────────────────
const styles: Record<string, React.CSSProperties> = {
  // Running
  runningPage: {
    minHeight: "100vh", display: "flex", alignItems: "center",
    justifyContent: "center", background: "#0a0a0f", padding: 24,
  },
  runningCard: {
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 20, padding: "40px 48px", maxWidth: 560, width: "100%",
    backdropFilter: "blur(12px)",
  },
  runningTitle: {
    fontSize: 24, fontWeight: 700, color: "#f1f5f9", marginBottom: 8,
  },
  runningSubtitle: {
    fontSize: 14, color: "#94a3b8", marginBottom: 32, lineHeight: 1.6,
  },
  stageList: { display: "flex", flexDirection: "column", gap: 16 },
  stageIcon: { fontSize: 22, width: 32, flexShrink: 0 },
  stageInfo: { flex: 1 },
  stageName: { fontSize: 14, fontWeight: 600, color: "#e2e8f0" },
  stageDesc: { fontSize: 12, color: "#64748b", marginTop: 2 },

  // Results
  resultsPage: {
    minHeight: "100vh", background: "#0a0a0f",
  },
  resultsHero: {
    background: "linear-gradient(180deg, rgba(124,58,237,0.08) 0%, transparent 100%)",
    borderBottom: "1px solid rgba(255,255,255,0.06)",
    padding: "24px 32px",
  },
  resultsHeroInner: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    maxWidth: 1200, margin: "0 auto",
  },
  resultsTitle: { fontSize: 20, fontWeight: 700, color: "#f1f5f9" },
  campaignIdTag: {
    fontSize: 11, color: "#475569", marginTop: 3, fontFamily: "monospace",
    letterSpacing: "0.05em",
  },
  resultsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 20,
    maxWidth: 1200,
    margin: "28px auto",
    padding: "0 32px",
  },
  resultCard: {
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 16, padding: 24,
  },
  cardHeader: { fontSize: 15, fontWeight: 700, color: "#e2e8f0", marginBottom: 16 },
  cardRow: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  cardLabel: { fontSize: 12, color: "#64748b", fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "0.04em" },
  cardValue: { fontSize: 13, color: "#cbd5e1" },
  cardText: { fontSize: 13, color: "#94a3b8", lineHeight: 1.6, marginTop: 12 },
  badge: {
    fontSize: 11, fontWeight: 700, padding: "3px 10px",
    borderRadius: 20, textTransform: "uppercase" as const,
  },
  bigIdea: {
    fontSize: 18, fontWeight: 600, color: "#a78bfa",
    fontStyle: "italic", lineHeight: 1.5, marginBottom: 16,
  },
  copyGrid: { display: "flex", flexDirection: "column" as const, gap: 16 },
  copyBlock: {},
  copyLabel: { fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase" as const, marginBottom: 6 },
  copyText: { fontSize: 14, color: "#cbd5e1", lineHeight: 1.6 },
  expandBtn: {
    background: "none", border: "none", color: "#64748b", fontSize: 13,
    cursor: "pointer", padding: 0, marginBottom: 12,
  },
  jsonPre: {
    fontSize: 11, color: "#64748b", background: "rgba(0,0,0,0.3)",
    borderRadius: 8, padding: 16, overflowX: "auto" as const,
    whiteSpace: "pre-wrap" as const, maxHeight: 400, overflowY: "auto" as const,
  },

  // Error
  errorPage: {
    minHeight: "100vh", display: "flex", alignItems: "center",
    justifyContent: "center", background: "#0a0a0f",
  },
  errorCard: {
    background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
    borderRadius: 20, padding: 40, maxWidth: 480, textAlign: "center" as const,
  },
  errorTitle: { fontSize: 20, fontWeight: 700, color: "#fca5a5", marginBottom: 12 },
  errorMsg: { fontSize: 14, color: "#f87171", lineHeight: 1.6 },
  authHint: { marginTop: 16, fontSize: 13, color: "#94a3b8", lineHeight: 1.6, textAlign: "left" as const },
  authCmd: { marginTop: 8, background: "rgba(0,0,0,0.4)", padding: "10px 14px", borderRadius: 8, fontSize: 12, color: "#7dd3fc", fontFamily: "monospace" },
};
