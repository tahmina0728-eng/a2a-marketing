import { useState } from "react";
import FormSelect from "./ui/FormSelect";
import type { HarnessBriefRequest } from "../types/pipeline";

/* ── Data ──────────────────────────────────────────────────────── */
const BRANDS = [
  { id: "Rnorr",       label: "Rnorr",            logo: "/brands/rnorr-logo.png" },
  { id: "Sunglow",     label: "Sunglow",            logo: "/brands/sunglow-logo.png" },
  { id: "Boozt",       label: "Boozt",              logo: "/brands/boozt-logo.png" },
  { id: "Glenfiddich", label: "Glenfiddich × AMF1", logo: "/brands/glenfiddich-logo.png" },
  { id: "UBS Bank",    label: "UBS Bank",           logo: "/brands/ubs-bank-logo.png" },
  { id: "sunrise",     label: "Sunrise",            logo: "/brands/sunrise-logo.svg" },
];
const MARKETS  = ["United Kingdom","Australia","United States","New Zealand","SEA","Switzerland","Global"];

const MARKET_LANGUAGES: Record<string, string[]> = {
  "United Kingdom": ["English"],
  "Australia":      ["English"],
  "United States":  ["English"],
  "New Zealand":    ["English"],
  "SEA":            ["English","Bahasa Indonesia","Thai","Vietnamese","Filipino"],
  "Switzerland":    ["German (de-CH)","French (fr-CH)","Italian (it-CH)","English"],
  "Global":         ["English"],
};
const BUDGETS   = ["£50K – £150K","£150K – £500K","£500K – £1M","£1M – £5M","£5M+"];
const CHANNELS  = ["Instagram","TikTok","YouTube","OOH","Google Ads","Meta Ads","Website","Email"];
const SEASONS   = ["Evergreen","Spring","Summer","Autumn","Winter","Christmas","Valentine's Day","Easter","Diwali","New Year"];
const MOMENTS   = ["Day-to-Day","Brand Moment","Partnership Moment"];
const AGES      = ["13–17","18–24","25–34","35–44","45–54","55+"];

// Sunrise-specific — must match Campaigns.tsx exactly
const SUNRISE_AUDIENCES = ["Young Adults 18–35","Families","Business Professionals","SME & Entrepreneurs","Digital Natives 16–24"];

const SUNRISE_PRODUCT_PLANS = [
  { name: "Mobile Unlimited",  amount: "39.90" },
  { name: "Easy Internet",     amount: "39.90" },
  { name: "5G Home Internet",  amount: "29.90" },
  { name: "Business Connect",  amount: "49.90" },
];

const MARKET_CURRENCY_SYMBOL: Record<string, string> = {
  "United Kingdom": "£", "Australia": "A$", "United States": "$",
  "New Zealand": "NZ$", "Switzerland": "CHF", "Germany": "€",
  "Austria": "€", "France": "€", "Global": "CHF", "SEA": "$",
};

const BRAND_FAN_TRUTHS: Record<string, string[]> = {
  sunrise: [
    "Young adventurers need a network that never drops at the moment that matters most — on the summit, mid-ride, or mid-call.",
    "Swiss families feel closest when they can share every moment in real time, wherever life takes them.",
    "Business professionals see dropped connections as dropped deals — they choose Sunrise because reliability is non-negotiable.",
    "Digital natives judge a brand by how invisibly it keeps up with their life — Sunrise earns loyalty by never slowing them down.",
  ],
  Rnorr: [
    "Home cooks feel proud when a simple weeknight meal becomes a moment the family talks about — Rnorr makes that effortless.",
    "Busy parents need shortcuts that don't feel like shortcuts — Rnorr lets them serve love on a plate even on the hardest days.",
    "Food lovers believe real flavour shouldn't require hours — Rnorr proves that bold taste and convenience can be the same thing.",
  ],
  Sunglow: [
    "Women know their hair is the first thing they see each morning — Sunglow makes that moment a confidence boost, not a battle.",
    "Beauty fans believe great hair shouldn't cost a salon visit — Sunglow gives them the result without the price tag.",
    "On-the-go women want one product that actually works — Sunglow earns trust by delivering on that promise every wash.",
  ],
  Boozt: [
    "Young achievers fuel their ambitions relentlessly and need energy that matches their pace without the crash.",
    "Athletes demand more from their energy source — Boozt delivers clean, sustained power exactly when it counts.",
    "Gen Z rejects artificial hype — they want a brand that gives them real performance fuel they can actually trust.",
  ],
  Glenfiddich: [
    "Whisky lovers believe the best experiences deserve the best whisky — Glenfiddich is the standard they share with those who get it.",
    "Ambitious professionals see whisky as an earned reward — Glenfiddich marks the milestones worth remembering.",
    "Collectors want a whisky with a story worth telling — Glenfiddich's 130-year heritage gives them a reason to open a bottle.",
  ],
  "UBS Bank": [
    "High achievers believe their financial choices should be as bold as their ambitions — UBS helps them build a future worthy of their vision.",
    "Entrepreneurs need a financial partner who sees potential, not just risk — UBS backs the person, not just the plan.",
    "Families want financial security without sacrificing their dreams — UBS makes both possible without having to choose.",
  ],
};

interface FD {
  brand: string; objective: string; market: string; language: string; budget: string;
  channels: string[]; age: string[]; season: string; moment: string; campaignName: string;
  fanTruth: string;
  // Sunrise-specific
  sunrisePlan: string;      // "Lifestyle KV" | plan name e.g. "Mobile Unlimited"
  sunriseAudience: string;
}
const INIT: FD = {
  brand:"", objective:"", market:"", language:"", budget:"",
  channels:[], age:[], season:"", moment:"Day-to-Day", campaignName:"",
  fanTruth:"",
  sunrisePlan:"Lifestyle KV", sunriseAudience:"",
};
const toggle = <T,>(arr: T[], v: T): T[] => arr.includes(v) ? arr.filter(x => x !== v) : [...arr, v];

/** Detect a seasonal/festive moment from free-text objective so Kinetik/Morphis can use it. */
function detectSeason(text: string): string {
  const t = text.toLowerCase();
  if (/christmas|xmas|festive|advent/.test(t)) return "Christmas";
  if (/diwali|deepavali/.test(t))             return "Diwali";
  if (/valentine/.test(t))                    return "Valentine's Day";
  if (/easter/.test(t))                       return "Easter";
  if (/new.?year/.test(t))                    return "New Year";
  if (/spring/.test(t))                       return "Spring";
  if (/summer/.test(t))                       return "Summer";
  if (/autumn|fall/.test(t))                  return "Autumn";
  if (/winter/.test(t))                       return "Winter";
  return "";
}

/* ── Brand gradient — matches the A2A logo / sidebar orb ──────── */
const BRAND_GRADIENT = "linear-gradient(135deg, #7c3aed 0%, #a855f7 55%, #6366f1 100%)";
const BRAND_COLOR     = "#7c3aed";

/* ── Shared styles ─────────────────────────────────────────────── */
const F = "'Poppins','Inter',sans-serif";

const label: React.CSSProperties = {
  display: "block", fontFamily: F, fontSize: 11, fontWeight: 600,
  letterSpacing: "0.08em", textTransform: "uppercase", color: "#8c8ca1", marginBottom: 6,
};

const chipBase: React.CSSProperties = {
  fontFamily: F, fontSize: 12, fontWeight: 500,
  padding: "6px 16px", borderRadius: 99, border: "1px solid #d0d0e0",
  cursor: "pointer", background: "rgba(255,255,255,0.85)", color: "#0f0f0f",
  transition: "all 0.15s",
};
const chipOn: React.CSSProperties = {
  ...chipBase, background: BRAND_GRADIENT, color: "#fff", borderColor: "transparent",
  boxShadow: "0 2px 12px rgba(124,58,237,0.35)",
};

const inputStyle: React.CSSProperties = {
  width: "100%", height: 44, borderRadius: 12, border: "1px solid #d0d0e0",
  background: "rgba(255,255,255,0.9)", padding: "0 14px",
  fontSize: 13, fontFamily: F, color: "#0f0f0f", outline: "none",
  boxSizing: "border-box" as const,
};


/* ── Page 1 ────────────────────────────────────────────────────── */
function Page1({ data, onChange, onNext }: {
  data: FD; onChange: (k: keyof FD, v: string) => void; onNext: () => void;
}) {
  const langs = data.market ? (MARKET_LANGUAGES[data.market] ?? ["English"]) : [];
  const ok = data.brand && data.objective.trim() && data.market && data.language && data.budget;

  const brandOptions = BRANDS.map(b => ({
    value: b.id,
    label: b.label,
    icon: <img src={b.logo} alt="" style={{ height: 20, width: 20, objectFit: "contain" }} />,
  }));

  return (
    <div style={{ flex:1, overflowY:"auto", display:"flex", flexDirection:"column",
      alignItems:"center", justifyContent:"center", padding:"40px 40px 60px" }}>
      <div style={{ width:"100%", maxWidth:620, display:"flex", flexDirection:"column", gap:20 }}>

        <div>
          <h3 style={{ fontFamily:F, fontSize:22, fontWeight:800, lineHeight:1.3, margin:"0 0 6px", color:"var(--text-primary,#0f172a)" }}>
            <span style={{ background:`linear-gradient(135deg,${BRAND_COLOR},#6366f1)`,
              WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent", backgroundClip:"text" }}>Hello!</span>
            {" "}What campaign should I set up?
          </h3>
          <p style={{ fontFamily:F, fontSize:13, color:"var(--text-secondary,#475569)", margin:0, lineHeight:1.5 }}>
            Fill in the details below and we'll build your AI-powered campaign.
          </p>
        </div>

        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
          <div>
            <span style={label}>Brand</span>
            <FormSelect value={data.brand} onChange={v => onChange("brand", v)}
              placeholder="Select brand" options={brandOptions} />
          </div>

          <div>
            <span style={label}>Campaign Objective</span>
            <textarea
              value={data.objective}
              onChange={e => onChange("objective", e.target.value)}
              placeholder="Describe your brand, market, and campaign direction — I'll help you move it forward"
              rows={3}
              style={{
                width: "100%", borderRadius: 12, padding: "14px 16px",
                border: "1px solid var(--card-border,rgba(15,23,42,0.08))",
                background: "var(--card-bg,#ffffff)",
                fontFamily: F, fontSize: 13, lineHeight: 1.6,
                color: "var(--text-primary,#0f172a)", resize: "none", outline: "none",
                boxSizing: "border-box" as const, transition: "border-color 0.15s",
              }}
              onFocus={e => e.currentTarget.style.borderColor = BRAND_COLOR}
              onBlur={e => e.currentTarget.style.borderColor = "var(--card-border,rgba(15,23,42,0.08))"}
            />
          </div>

          <div style={{ display:"grid", gridTemplateColumns: langs.length > 1 ? "1fr 1fr 1fr" : "1fr 1fr", gap:16 }}>
            <div>
              <span style={label}>Market</span>
              <FormSelect value={data.market} onChange={v => {
                  const defaultLang = (MARKET_LANGUAGES[v] ?? ["English"])[0];
                  onChange("market", v);
                  onChange("language", defaultLang);
                }}
                placeholder="Select market" options={MARKETS} />
            </div>
            {langs.length > 1 && (
              <div>
                <span style={label}>Language</span>
                <FormSelect value={data.language} onChange={v => onChange("language", v)}
                  placeholder="Select language" options={langs} />
              </div>
            )}
            <div>
              <span style={label}>Budget Range</span>
              <FormSelect value={data.budget} onChange={v => onChange("budget", v)}
                placeholder="Select budget" options={BUDGETS} />
            </div>
          </div>
        </div>

        <button onClick={onNext} disabled={!ok}
          style={{ alignSelf:"flex-start", height:44, padding:"0 28px", borderRadius:12, border:"none",
            fontFamily:F, fontWeight:600, fontSize:14, display:"flex", alignItems:"center",
            gap:8, cursor: ok ? "pointer" : "not-allowed",
            background: ok ? BRAND_GRADIENT : "rgba(124,58,237,0.15)",
            color: ok ? "#fff" : "rgba(124,58,237,0.4)",
            boxShadow: ok ? "0 4px 16px rgba(124,58,237,0.3)" : "none",
            transition:"all 0.2s" }}>
          Next: Campaign Brief
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </button>
      </div>
    </div>
  );
}

/* ── Page 2 ────────────────────────────────────────────────────── */
function Page2({ data, onChange, onToggle, onBack, onLaunch }: {
  data: FD; onChange: (k: keyof FD, v: string) => void;
  onToggle: (k: "channels"|"age", v: string) => void;
  onBack: () => void; onLaunch: () => void;
}) {
  const isSunrise = data.brand === "sunrise";

  const ok = isSunrise
    ? data.campaignName.trim().length > 0 && data.sunriseAudience.length > 0
    : data.channels.length > 0 && data.campaignName.trim().length > 0;

  return (
    <div style={{ flex:1, overflowY:"auto", display:"flex", flexDirection:"column",
      alignItems:"center", justifyContent:"center", padding:"40px 40px 60px" }}>
      <div style={{ width:"100%", maxWidth:620, display:"flex", flexDirection:"column", gap:20 }}>

        <div>
          <h3 style={{ fontFamily:F, fontSize:22, fontWeight:800, lineHeight:1.3, margin:"0 0 6px", color:"var(--text-primary,#0f172a)" }}>
            <span style={{ background:`linear-gradient(135deg,${BRAND_COLOR},#6366f1)`,
              WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent", backgroundClip:"text" }}>Almost there!</span>
            {" "}Campaign Brief
          </h3>
          <p style={{ fontFamily:F, fontSize:13, color:"var(--text-secondary,#475569)", margin:0, lineHeight:1.5 }}>
            {isSunrise
              ? "Choose your Sunrise mode, target audience and give your campaign a name."
              : "Choose your channels, audience and give your campaign a name."}
          </p>
        </div>

        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

          {/* ── Channels (all brands) ── */}
          <div>
            <span style={label}>Channels</span>
            <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
              {CHANNELS.map(c => (
                <button key={c} onClick={() => onToggle("channels", c)}
                  style={data.channels.includes(c) ? chipOn : chipBase}>{c}</button>
              ))}
            </div>
          </div>

          {isSunrise ? (
            <>
              {/* ── Sunrise Mode — single dropdown matching Campaigns section ── */}
              {(() => {
                const sym  = MARKET_CURRENCY_SYMBOL[data.market] ?? "CHF";
                const opts = [
                  "Lifestyle KV",
                  ...SUNRISE_PRODUCT_PLANS.map(p => `${p.name} – ${sym} ${p.amount}/mth`),
                ];
                const selPlan = SUNRISE_PRODUCT_PLANS.find(p => p.name === data.sunrisePlan);
                const chipVal = selPlan ? `${selPlan.name} – ${sym} ${selPlan.amount}/mth` : "Lifestyle KV";
                return (
                  <div>
                    <span style={label}>Sunrise Mode</span>
                    <FormSelect value={chipVal} onChange={v => {
                        if (v === "Lifestyle KV") { onChange("sunrisePlan", "Lifestyle KV"); return; }
                        const plan = SUNRISE_PRODUCT_PLANS.find(p => `${p.name} – ${sym} ${p.amount}/mth` === v);
                        onChange("sunrisePlan", plan ? plan.name : "Lifestyle KV");
                      }}
                      placeholder="Select mode" options={opts} />
                  </div>
                );
              })()}

              {/* ── Sunrise Target Audience ── */}
              <div>
                <span style={label}>Target Audience</span>
                <FormSelect value={data.sunriseAudience} onChange={v => onChange("sunriseAudience", v)}
                  placeholder="Select audience" options={SUNRISE_AUDIENCES} />
              </div>
            </>
          ) : (
            /* ── Generic: Target Age Groups ── */
            <div>
              <span style={label}>Target Age Groups</span>
              <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
                {AGES.map(a => (
                  <button key={a} onClick={() => onToggle("age", a)}
                    style={data.age.includes(a) ? chipOn : chipBase}>{a}</button>
                ))}
              </div>
            </div>
          )}

          {/* ── Fan Truth ── */}
          {(BRAND_FAN_TRUTHS[data.brand] ?? []).length > 0 && (
            <div>
              <span style={label}>Fan Truth</span>
              <FormSelect
                value={data.fanTruth}
                onChange={v => onChange("fanTruth", v)}
                placeholder="Select a fan truth (optional)"
                options={BRAND_FAN_TRUTHS[data.brand] ?? []}
              />
            </div>
          )}

          {/* ── Season / Moment (all brands) ── */}
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            <div>
              <span style={label}>Season / Occasion</span>
              <FormSelect value={data.season} onChange={v => onChange("season", v)}
                placeholder="Select season" options={SEASONS} />
            </div>
            <div>
              <span style={label}>Campaign Moment</span>
              <FormSelect value={data.moment} onChange={v => onChange("moment", v)}
                placeholder="Select moment" options={MOMENTS} />
            </div>
          </div>

          {/* ── Campaign Name (all brands) ── */}
          <div>
            <span style={label}>Campaign Name</span>
            <input value={data.campaignName} onChange={e => onChange("campaignName", e.target.value)}
              placeholder="Give your campaign a name"
              style={inputStyle} />
          </div>
        </div>

        <div style={{ display:"flex", gap:10 }}>
          <button onClick={onBack}
            style={{ height:44, padding:"0 20px", borderRadius:12,
              border:`1.5px solid ${BRAND_COLOR}`, background:"transparent",
              color: BRAND_COLOR, fontFamily:F, fontWeight:600, fontSize:13,
              cursor:"pointer", display:"flex", alignItems:"center", gap:6 }}>
            ← Back
          </button>
          <button onClick={onLaunch} disabled={!ok}
            style={{ height:44, padding:"0 28px", borderRadius:12, border:"none", fontFamily:F,
              fontWeight:600, fontSize:14, display:"flex", alignItems:"center",
              gap:8, cursor: ok ? "pointer" : "not-allowed",
              background: ok ? BRAND_GRADIENT : "rgba(124,58,237,0.15)",
              color: ok ? "#fff" : "rgba(124,58,237,0.4)",
              boxShadow: ok ? "0 4px 16px rgba(124,58,237,0.3)" : "none",
              transition:"all 0.2s" }}>
            ✨ Launch Campaign
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Export ────────────────────────────────────────────────────── */
export default function CampaignForm({ onFullCampaign }: {
  onFullCampaign: (brief: HarnessBriefRequest) => void;
}) {
  const [page, setPage] = useState<1|2>(1);
  const [data, setData] = useState<FD>(INIT);

  const onChange = (k: keyof FD, v: string) => setData(d => ({...d, [k]:v}));
  const onToggle = (k: "channels"|"age", v: string) =>
    setData(d => ({...d, [k]: toggle(d[k] as string[], v)}));

  const handleLaunch = () => {
    const resolvedSeason = data.season || detectSeason(data.objective) || "Evergreen";
    const brandLabel = BRANDS.find(b => b.id === data.brand)?.label ?? data.brand;
    const isSunrise  = data.brand === "sunrise";

    // Build product string for Sunrise:
    // Offer plan  → "Mobile Unlimited CHF 39.90" — runner.py regex splits price from label
    // Lifestyle KV → "" (empty → runner.py lifestyle render path)
    let product = "";
    let audienceSegment = data.age.join(", ") || "General audience";

    if (isSunrise) {
      audienceSegment = data.sunriseAudience || "General audience";
      const plan = SUNRISE_PRODUCT_PLANS.find(p => p.name === data.sunrisePlan);
      if (plan) {
        const sym = MARKET_CURRENCY_SYMBOL[data.market] ?? "CHF";
        product = `${plan.name} ${sym} ${plan.amount}`;
      }
    }

    // Fan truth: user-selected takes priority; fall back to auto-generated
    let fanTruth: string = data.fanTruth.trim();
    if (!fanTruth) {
      if (isSunrise && data.sunrisePlan === "Business Connect") {
        const audience = data.sunriseAudience || "business professionals";
        fanTruth = `${audience} in ${data.market} need uninterrupted, always-on connectivity to run their business with confidence — they choose Sunrise Business Connect because downtime is not an option.`;
      } else if (isSunrise && data.sunrisePlan) {
        const audience = data.sunriseAudience || "customers";
        fanTruth = `${audience} in ${data.market} want the freedom to stay connected without limits or hidden costs — they trust Sunrise ${data.sunrisePlan} because it gives them exactly what they pay for.`;
      } else if (isSunrise) {
        const audience = data.sunriseAudience || "customers";
        fanTruth = `${audience} in ${data.market} seek a brand that genuinely reflects their lifestyle — Sunrise earns their loyalty by showing up authentically in the moments that matter most to them.`;
      } else {
        fanTruth = `${brandLabel} fans in ${data.market} reward brands that understand the specific moments of their lives`
          + (resolvedSeason !== "Evergreen" ? ` — especially during ${resolvedSeason}` : "")
          + `, not just their demographic profile.`;
      }
    }

    onFullCampaign({
      campaign_name:    data.campaignName.trim(),
      brand:            data.brand,
      goal:             data.objective,
      budget:           data.budget,
      kpis:             "reach, ctr, roas",
      product:          product,
      product_category: brandLabel,
      fan_truth:        fanTruth,
      channels:         data.channels,
      market:           data.market,
      language:         data.language || undefined,
      season:           resolvedSeason,
      moment_type:      data.moment as any,
      audience: {
        segment:   audienceSegment,
        location:  data.market,
        age_range: isSunrise ? audienceSegment : (data.age[0]?.replace("–","-") ?? "All ages"),
        gender:    "All genders",
      },
      tone: "Warm & friendly",
      mode: "new",
      uploaded_assets: [],
    });
  };

  return (
    <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>
      {page === 1
        ? <Page1 data={data} onChange={onChange} onNext={() => setPage(2)} />
        : <Page2 data={data} onChange={onChange} onToggle={onToggle}
            onBack={() => setPage(1)} onLaunch={handleLaunch} />}
    </div>
  );
}
