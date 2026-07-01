import { useState } from "react";
import FormSelect from "./ui/FormSelect";
import PromptCard from "./ui/PromptCard";
import type { HarnessBriefRequest } from "../types/pipeline";

/* ── Data ──────────────────────────────────────────────────────── */
const BRANDS = [
  { id: "Rnorr",       label: "Rnorr",            logo: "/brands/rnorr-logo.png" },
  { id: "Sunglow",     label: "Sunglow",            logo: "/brands/sunglow-logo.png" },
  { id: "Boozt",       label: "Boozt",              logo: "/brands/boozt-logo.png" },
  { id: "Glenfiddich", label: "Glenfiddich × AMF1", logo: "/brands/glenfiddich-logo.png" },
  { id: "UBS Bank",    label: "UBS Bank",           logo: "/brands/ubs-bank-logo.png" },
];
const MARKETS  = ["United Kingdom","Australia","United States","New Zealand","SEA","Global"];
const BUDGETS  = ["£50K – £150K","£150K – £500K","£500K – £1M","£1M – £5M","£5M+"];
const CHANNELS = ["Instagram","TikTok","YouTube","OOH","Google Ads","Meta Ads","Website","Email"];
const SEASONS  = ["Evergreen","Spring","Summer","Autumn","Winter","Christmas","Valentine's Day","Easter","Diwali","New Year"];
const MOMENTS  = ["Day-to-Day","Brand Moment","Partnership Moment"];
const AGES     = ["13–17","18–24","25–34","35–44","45–54","55+"];

interface FD {
  brand: string; objective: string; market: string; budget: string;
  channels: string[]; age: string[]; season: string; moment: string; campaignName: string;
}
const INIT: FD = { brand:"", objective:"", market:"", budget:"", channels:[], age:[], season:"", moment:"Day-to-Day", campaignName:"" };
const toggle = <T,>(arr: T[], v: T): T[] => arr.includes(v) ? arr.filter(x => x !== v) : [...arr, v];

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

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.82)", backdropFilter: "blur(16px)",
      WebkitBackdropFilter: "blur(16px)", borderRadius: 20,
      border: "1px solid rgba(255,255,255,0.6)",
      boxShadow: "0 8px 32px rgba(0,0,0,0.08)", padding: 28,
      display: "flex", flexDirection: "column", gap: 20,
    }}>
      {children}
    </div>
  );
}

/* ── Page 1 ────────────────────────────────────────────────────── */
function Page1({ data, onChange, onNext }: {
  data: FD; onChange: (k: keyof FD, v: string) => void; onNext: () => void;
}) {
  const ok = data.brand && data.objective.trim() && data.market && data.budget;

  const brandOptions = BRANDS.map(b => ({
    value: b.id,
    label: b.label,
    icon: <img src={b.logo} alt="" style={{ height: 20, width: 20, objectFit: "contain" }} />,
  }));

  return (
    <div style={{ flex:1, overflowY:"auto", display:"flex", flexDirection:"column",
      alignItems:"center", justifyContent:"center", padding:"40px 40px 60px" }}>
      <div style={{ width:"100%", maxWidth:620, display:"flex", flexDirection:"column", gap:24 }}>

        <div>
          <h1 style={{ fontFamily:F, fontSize:38, fontWeight:600, lineHeight:1.2,
            letterSpacing:"-0.02em", margin:0, color:"#0f0f0f" }}>
            <span style={{ backgroundImage:"linear-gradient(175deg,#3343FF 13%,#FE9136 82%)",
              WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent",
              backgroundClip:"text" }}>Hello!</span>
            {" "}Set Campaign Objective
          </h1>
          <p style={{ fontFamily:F, fontSize:14, color:"#8c8ca1", marginTop:6, lineHeight:1.5 }}>
            Fill in the details below and we'll build your AI-powered campaign.
          </p>
        </div>

        <Card>
          <div>
            <span style={label}>Brand</span>
            <FormSelect value={data.brand} onChange={v => onChange("brand", v)}
              placeholder="Select brand" options={brandOptions} />
          </div>

          <div>
            <span style={label}>Campaign Objective</span>
            <PromptCard value={data.objective} onChange={v => onChange("objective", v)}
              placeholder="Drive 30% uplift in consideration among health-conscious women 25–40 in the UK during Spring 2025"
              accentColor={BRAND_COLOR} />
          </div>

          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
            <div>
              <span style={label}>Market</span>
              <FormSelect value={data.market} onChange={v => onChange("market", v)}
                placeholder="Select market" options={MARKETS} />
            </div>
            <div>
              <span style={label}>Budget Range</span>
              <FormSelect value={data.budget} onChange={v => onChange("budget", v)}
                placeholder="Select budget" options={BUDGETS} />
            </div>
          </div>
        </Card>

        <button onClick={onNext} disabled={!ok}
          style={{ width:"100%", height:52, borderRadius:14, border:"none", fontFamily:F,
            fontWeight:600, fontSize:15, display:"flex", alignItems:"center",
            justifyContent:"center", gap:8, cursor: ok ? "pointer" : "default",
            background: ok ? BRAND_GRADIENT : "rgba(255,255,255,0.4)",
            color: ok ? "#fff" : "#8c8ca1",
            boxShadow: ok ? "0 4px 20px rgba(124,58,237,0.3)" : "none",
            transition:"all 0.2s" }}>
          Next: Campaign Brief
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
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
  const ok = data.channels.length > 0 && data.campaignName.trim();

  return (
    <div style={{ flex:1, overflowY:"auto", display:"flex", flexDirection:"column",
      alignItems:"center", justifyContent:"center", padding:"40px 40px 60px" }}>
      <div style={{ width:"100%", maxWidth:620, display:"flex", flexDirection:"column", gap:24 }}>

        <div>
          <h1 style={{ fontFamily:F, fontSize:38, fontWeight:600, lineHeight:1.2,
            letterSpacing:"-0.02em", margin:0, color:"#0f0f0f" }}>
            <span style={{ backgroundImage:"linear-gradient(175deg,#3343FF 13%,#FE9136 82%)",
              WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent",
              backgroundClip:"text" }}>Almost there!</span>
            {" "}Campaign Brief
          </h1>
          <p style={{ fontFamily:F, fontSize:14, color:"#8c8ca1", marginTop:6, lineHeight:1.5 }}>
            Choose your channels, audience and give your campaign a name.
          </p>
        </div>

        <Card>
          <div>
            <span style={label}>Channels</span>
            <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
              {CHANNELS.map(c => (
                <button key={c} onClick={() => onToggle("channels", c)}
                  style={data.channels.includes(c) ? chipOn : chipBase}>{c}</button>
              ))}
            </div>
          </div>

          <div>
            <span style={label}>Target Age Groups</span>
            <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
              {AGES.map(a => (
                <button key={a} onClick={() => onToggle("age", a)}
                  style={data.age.includes(a) ? chipOn : chipBase}>{a}</button>
              ))}
            </div>
          </div>

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

          <div>
            <span style={label}>Campaign Name</span>
            <input value={data.campaignName} onChange={e => onChange("campaignName", e.target.value)}
              placeholder="Give your campaign a name"
              style={{ width:"100%", height:44, borderRadius:12, border:"1px solid #d0d0e0",
                background:"rgba(255,255,255,0.9)", padding:"0 14px",
                fontSize:13, fontFamily:F, color:"#0f0f0f", outline:"none",
                boxSizing:"border-box" as const }} />
          </div>
        </Card>

        <div style={{ display:"flex", gap:12 }}>
          <button onClick={onBack}
            style={{ height:52, paddingLeft:24, paddingRight:24, borderRadius:14,
              border:"1px solid #d0d0e0", background:"rgba(255,255,255,0.7)",
              color: BRAND_COLOR, fontFamily:F, fontWeight:600, fontSize:14,
              cursor:"pointer", display:"flex", alignItems:"center", gap:6 }}>
            ← Back
          </button>
          <button onClick={onLaunch} disabled={!ok}
            style={{ flex:1, height:52, borderRadius:14, border:"none", fontFamily:F,
              fontWeight:600, fontSize:15, display:"flex", alignItems:"center",
              justifyContent:"center", gap:8, cursor: ok ? "pointer" : "default",
              background: ok ? BRAND_GRADIENT : "rgba(255,255,255,0.4)",
              color: ok ? "#fff" : "#8c8ca1",
              boxShadow: ok ? "0 4px 24px rgba(124,58,237,0.35)" : "none",
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
    onFullCampaign({
      campaign_name:    data.campaignName.trim(),
      brand:            data.brand,
      goal:             data.objective,
      budget:           data.budget,
      kpis:             "reach, ctr, roas",
      product:          "",
      product_category: BRANDS.find(b => b.id === data.brand)?.label ?? "",
      fan_truth:        data.objective,
      channels:         data.channels,
      market:           data.market,
      season:           data.season || "Evergreen",
      moment_type:      data.moment as any,
      audience: {
        segment:   data.age.join(", ") || "General audience",
        location:  data.market,
        age_range: data.age[0]?.replace("–","-") ?? "All ages",
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
