import { useState, useEffect } from "react";
import { saveToContentHub } from "../hooks/useContentHub";
import { DEFAULT_VOICES, VOICE_STORAGE_KEY } from "../constants/brandVoices";
import type { BrandVoice } from "../constants/brandVoices";

const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000";

type FormatType = "image" | "reel" | "tvc" | "video";

interface GeneratedResult {
  image_b64?: string;
  video_b64?: string;
  headline?:  string;
  body?:      string;
  tagline?:   string;
}

const BRANDS    = ["Rnorr","Sunglow","Boozt","Glenfiddich","UBS Bank"];
const GOALS     = ["Brand Awareness","Drive Sales","Lead Generation","Product Launch","Engagement"];
const AUDIENCES = ["Women 18–35","Men 25–45","Gen Z 16–24","Professionals 30–50","Families"];
const PLATFORMS = ["Instagram","TikTok","YouTube","LinkedIn","Facebook","Instagram, Facebook"];

const BRAND_ICONS: Record<string, string> = {
  "Rnorr": "/brands/rnorr-logo.png",
  "Sunglow": "/brands/sunglow-logo.png",
  "Boozt": "/brands/boozt-logo.png",
  "Glenfiddich": "/brands/glenfiddich-logo.png",
  "UBS Bank": "/brands/ubs-bank-logo.png",
};

const G = "linear-gradient(135deg,#7c3aed,#a855f7,#6366f1)";

// ── Horizontal Step Progress ───────────────────────────────────
function StepProgress({ current }: { current: 1|2|3|4 }) {
  const steps = [
    { n: 1, label: "Campaign Brief",  sub: "Tell us what you want" },
    { n: 2, label: "Choose Format",   sub: "Image, Video or Reel" },
    { n: 3, label: "Copy Agent",      sub: "Ideon writes your copy" },
    { n: 4, label: "Generate & Review", sub: "AI creates content" },
  ];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 32 }}>
      {steps.map((s, i) => (
        <div key={s.n} style={{ display: "flex", alignItems: "center", flex: i < 3 ? 1 : "none" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
            <div style={{
              width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 13, fontWeight: 800,
              background: current === s.n ? G : current > s.n ? "#10b981" : "var(--card-bg-soft)",
              color: current >= s.n ? "white" : "var(--text-secondary)",
              boxShadow: current === s.n ? "0 4px 14px rgba(124,58,237,0.5)" : "none",
              border: current < s.n ? "1.5px solid var(--card-border)" : "none",
            }}>
              {current > s.n ? "✓" : s.n}
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700,
                color: current >= s.n ? "var(--text-primary)" : "var(--text-secondary)" }}>
                {s.label}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 1, opacity: 0.7 }}>
                {s.sub}
              </div>
            </div>
          </div>
          {i < 3 && (
            <div style={{ flex: 1, height: 1, margin: "0 20px",
              background: current > s.n ? "#10b981" : "var(--card-border)" }} />
          )}
        </div>
      ))}
    </div>
  );
}

// ── Chip Selector ──────────────────────────────────────────────
function ChipSel({ icon, label, value, onChange, opts }: {
  icon: React.ReactNode; label: string; value: string;
  onChange: (v: string) => void; opts: string[];
}) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ position: "relative" as const, flexShrink: 0 }}>
      <button onClick={() => setOpen(o => !o)} style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 14px",
        borderRadius: 99, border: `1.5px solid ${value ? "#7c3aed" : "var(--card-border)"}`,
        background: value ? "rgba(124,58,237,0.08)" : "var(--card-bg-soft)",
        cursor: "pointer", fontFamily: "inherit", color: "var(--text-primary)", fontSize: 13,
        fontWeight: 600, transition: "all 0.15s", whiteSpace: "nowrap" as const,
      }}>
        <span style={{ opacity: 0.6, color: "var(--text-secondary)" }}>{icon}</span>
        <span style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 500 }}>{label}</span>
        <span style={{ color: value ? "#7c3aed" : "var(--text-secondary)", fontWeight: value ? 700 : 400 }}>
          {value || "Select…"}
        </span>
        <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
          <path d="M1 1l4 4 4-4" stroke="var(--text-secondary)" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      </button>
      {open && (
        <div style={{ position: "absolute" as const, top: "calc(100% + 6px)", left: 0, zIndex: 100,
          background: "var(--card-bg)", border: "1px solid var(--card-border)",
          borderRadius: 12, boxShadow: "0 16px 40px rgba(0,0,0,0.15)",
          minWidth: 180, overflow: "hidden" }}>
          {opts.map(o => (
            <button key={o} onClick={() => { onChange(o); setOpen(false); }}
              style={{ display: "block", width: "100%", padding: "10px 16px", border: "none",
                background: value === o ? "rgba(124,58,237,0.08)" : "transparent",
                color: value === o ? "#7c3aed" : "var(--text-primary)",
                textAlign: "left" as const, cursor: "pointer", fontFamily: "inherit",
                fontSize: 13, fontWeight: value === o ? 600 : 400 }}>
              {o}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Format Cards (Step 2) ──────────────────────────────────────
function FormatCard({ label, desc, icon, selected, onClick, sizes, selSize, onSize }: {
  type?: FormatType; label: string; desc: string; icon: React.ReactNode;
  selected: boolean; onClick: () => void;
  sizes: string[]; selSize: string; onSize: (s: string) => void;
}) {
  return (
    <div onClick={onClick} style={{
      padding: "20px", borderRadius: 16, cursor: "pointer",
      border: `2px solid ${selected ? "#7c3aed" : "var(--card-border)"}`,
      background: selected ? "rgba(124,58,237,0.08)" : "var(--card-bg)",
      transition: "all 0.2s", position: "relative" as const,
      boxShadow: selected ? "0 0 0 4px rgba(124,58,237,0.12), 0 4px 20px rgba(124,58,237,0.15)" : "0 2px 8px rgba(0,0,0,0.06)",
    }}>
      {selected && (
        <div style={{ position: "absolute" as const, top: 14, right: 14,
          width: 22, height: 22, borderRadius: "50%", background: G,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 11, color: "white", fontWeight: 800 }}>✓</div>
      )}
      <div style={{ width: 44, height: 44, borderRadius: 12, marginBottom: 14,
        background: selected ? "rgba(124,58,237,0.15)" : "var(--card-bg-soft)",
        display: "flex", alignItems: "center", justifyContent: "center",
        color: selected ? "#7c3aed" : "var(--text-secondary)", transition: "all 0.2s" }}>
        {icon}
      </div>
      <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: selected ? 14 : 0 }}>{desc}</div>
      {selected && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" as const }}>
          {sizes.map(s => (
            <button key={s} onClick={e => { e.stopPropagation(); onSize(s); }}
              style={{ padding: "4px 12px", borderRadius: 99, border: "none", cursor: "pointer",
                fontSize: 11, fontWeight: 600,
                background: selSize === s ? "#7c3aed" : "var(--card-bg-soft)",
                color: selSize === s ? "white" : "var(--text-secondary)",
                boxShadow: selSize === s ? "0 2px 8px rgba(124,58,237,0.4)" : "none" }}>
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────
export default function Campaigns({ initialName, initialBrand, initialResults, onSaved, onPublish }: { initialName?: string; initialBrand?: string; initialResults?: Partial<Record<FormatType, GeneratedResult>>; onSaved?: () => void; onPublish?: (data: { brand: string; brief: string; headline?: string; body?: string; image_b64?: string; contentType: "image" | "video" }) => void } = {}) {
  const [step, setStep]         = useState<1|2|3|4>(initialResults ? 4 : 1);
  const [campaignName, setCampaignName] = useState(initialName ?? "");
  const [brief, setBrief]       = useState("");
  const [brand, setBrand]       = useState(initialBrand ?? "");
  const [goal, setGoal]       = useState("");
  const [audience, setAudience] = useState("");
  const [platform, setPlatform] = useState("");
  const [voiceName, setVoiceName] = useState("");
  const [voices] = useState<BrandVoice[]>(() => {
    try {
      const stored = localStorage.getItem(VOICE_STORAGE_KEY);
      if (stored) return JSON.parse(stored);
      localStorage.setItem(VOICE_STORAGE_KEY, JSON.stringify(DEFAULT_VOICES));
      return DEFAULT_VOICES;
    } catch { return DEFAULT_VOICES; }
  });

  const [formats, setFormats] = useState<Set<FormatType>>(new Set());
  const [imgSz, setImgSz]     = useState("16:9");
  const [tvcLen, setTvcLen]   = useState("15");
  const [vidLen, setVidLen]   = useState("30s");

  const [copyRes, setCopyRes] = useState<{headline:string;body:string;cta:string}|null>(null);
  const [copyBusy, setCopyBusy] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [results, setResults] = useState<Partial<Record<FormatType, GeneratedResult>>>(initialResults ?? {});
  const [tab, setTab]         = useState<FormatType>(initialResults?.image ? "image" : initialResults?.reel ? "reel" : "image");
  const [saveState, setSaveState] = useState<Record<string, "idle"|"saving"|"saved">>({});
  const [modifyOpen, setModifyOpen] = useState(false);
  const [modifyText, setModifyText] = useState("");
  const [preModifyResults, setPreModifyResults] = useState<Partial<Record<FormatType, GeneratedResult>>>({});
  const [figmaState, setFigmaState] = useState<"idle"|"loading"|"ready">("idle");

  const saveAsset = async (fmt: FormatType) => {
    const r = results[fmt];
    if (!r) return;
    setSaveState(s => ({ ...s, [fmt]: "saving" }));
    try {
      const isVideo = fmt === "reel" || fmt === "tvc" || fmt === "video";
      await saveToContentHub({
        kind:         isVideo ? "reel" : "kv",
        brand:        brand || "",
        campaignName: brief.slice(0, 40),
        campaignId:   "",
        headline:     r.headline || r.tagline || brief.slice(0, 60),
        assetDataUrl: isVideo
          ? `data:video/mp4;base64,${r.video_b64}`
          : `data:image/jpeg;base64,${r.image_b64}`,
      });
      setSaveState(s => ({ ...s, [fmt]: "saved" }));
      setTimeout(() => setSaveState(s => ({ ...s, [fmt]: "idle" })), 2500);
    } catch {
      setSaveState(s => ({ ...s, [fmt]: "idle" }));
    }
  };

  const selectedVoice = voices.find(v => v.name === voiceName);
  const prompt = [
    brand && `Brand: ${brand}`,
    selectedVoice && `Tone of voice: ${selectedVoice.description}. Traits: ${selectedVoice.traits.join(", ")}`,
    brief,
    goal && `Goal: ${goal}`,
    audience && `Audience: ${audience}`,
    platform && `Platform: ${platform}`,
  ].filter(Boolean).join(". ");
  const anyRes = Object.values(results).some(r => r?.image_b64||r?.video_b64);
  const hasRes = (f: FormatType) => !!(results[f]?.image_b64 || results[f]?.video_b64);

  // Save campaign name + results to localStorage once generation is done
  useEffect(() => {
    if (!anyRes) return;
    const name = campaignName.trim() || brand || "Untitled Campaign";
    const stored: {id:string;name:string;brand:string}[] = (() => {
      try { return JSON.parse(localStorage.getItem("a2a_campaigns") ?? "[]"); } catch { return []; }
    })();
    const existingId = stored.find(c => c.name === name)?.id;
    const id = existingId ?? `c_${Date.now()}`;
    if (!existingId) {
      const updated = [{ id, name, brand }, ...stored.filter(c => c.name !== name)].slice(0, 10);
      localStorage.setItem("a2a_campaigns", JSON.stringify(updated));
      onSaved?.();
    }
    // Persist results (image only — keep localStorage size manageable)
    try {
      const toSave: Partial<Record<FormatType, GeneratedResult>> = {};
      if (results.image) toSave.image = { image_b64: results.image.image_b64, headline: results.image.headline, tagline: results.image.tagline };
      localStorage.setItem(`a2a_results_${id}`, JSON.stringify(toSave));
    } catch {}
  }, [anyRes, campaignName, brief, brand, onSaved, results]);

  const [modifyBusy, setModifyBusy] = useState(false);

  const handleModifySubmit = async () => {
    if (!modifyText.trim() || modifyBusy) return;
    setModifyBusy(true);
    try {
      const modifiedPrompt = `${prompt}. Modification request: ${modifyText}`;
      const r = await fetch(`${API_BASE}/agents/kv/run`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: modifiedPrompt }),
      });
      const d = await r.json();
      setResults(prev => ({ ...prev, image: d }));
      setTab("image");
      setModifyText("");
    } catch {}
    setModifyBusy(false);
  };

  const handleFigmaMcp = async () => {
    const img = results.image?.image_b64;
    if (!img) return;
    setFigmaState("loading");
    try {
      const res = await fetch(`${API_BASE}/figma/prepare`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_b64: img, campaign_name: brief.slice(0, 40) || "Campaign" }),
      });
      const data = await res.json();
      setFigmaState("ready");
      window.open(data.figma_url || "https://www.figma.com/new", "_blank");
    } catch {
      setFigmaState("idle");
    }
  };

  const toggleFmt = (f: FormatType) => {
    setFormats(prev => { const n = new Set(prev); n.has(f)?n.delete(f):n.add(f); return n; });
  };

  const genCopy = async () => {
    setCopyBusy(true);
    try {
      const r = await fetch(`${API_BASE}/agents/copy/run`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ prompt }),
      });
      const d = await r.json();
      setCopyRes({ headline:d.short?.headline||d.headline||"", body:d.long?.body||d.body||"", cta:d.cta||"Learn More" });
    } catch {} finally { setCopyBusy(false); }
  };

  const genContent = async () => {
    if (!brief.trim()||formats.size===0) return;
    setGenerating(true);
    for (const fmt of Array.from(formats)) {
      try {
        const body: Record<string,unknown> = { prompt };
        if (fmt==="tvc") body.duration = parseInt(tvcLen);
        const key = fmt==="image"?"kv":fmt==="tvc"?"tvc":"reel";
        const r = await fetch(`${API_BASE}/agents/${key}/run`, {
          method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body),
        });
        const d = await r.json();
        setResults(prev => ({ ...prev, [fmt]: d }));
        setTab(fmt);
      } catch {}
    }
    setGenerating(false);
    setStep(4);
  };

  const fmtDefs = [
    { type:"image" as FormatType, label:"Image", desc:"Key visuals, hero banners & social posts.",
      sizes:["1:1","4:5","16:9","9:16"], selSize:imgSz, onSize:setImgSz,
      icon:<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg> },
    { type:"reel" as FormatType, label:"Reel", desc:"6-second Veo reels for social platforms.",
      sizes:["9:16","16:9"], selSize:"9:16", onSize:()=>{},
      icon:<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg> },
    { type:"tvc" as FormatType, label:"TVC", desc:"TV commercials via Veo — 15s or 30s.",
      sizes:["15s","30s"], selSize:tvcLen+"s", onSize:(s:string)=>setTvcLen(s.replace("s","")),
      icon:<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="2" y="7" width="20" height="15" rx="2"/><polyline points="17 2 12 7 7 2"/></svg> },
    { type:"video" as FormatType, label:"Video Ad", desc:"Longer video ads up to 60s.",
      sizes:["15s","30s","45s","60s"], selSize:vidLen, onSize:(s:string)=>setVidLen(s),
      icon:<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg> },
  ];

  return (
    <div style={{ flex:1, display:"flex", flexDirection:"column" as const,
      height:"100vh", overflow:"hidden",
      background:"var(--page-bg)" }}>

      {/* ── Content — centred vertically + horizontally ── */}
      <div style={{ flex:1, overflowY:"auto", padding:"32px 24px",
        display:"flex", flexDirection:"column" as const,
        alignItems:"center", justifyContent:"center" }}>
        {/* Centred wrapper — title + steps + content all here */}
        <div style={{ width:"100%", maxWidth:820 }}>

          {/* Title — just above the step bar with a small gap */}
          <div style={{ textAlign:"center" as const, marginBottom:28, position:"relative" as const }}>
            <div style={{ position:"absolute" as const, top:-20, left:"50%", transform:"translateX(-50%)",
              width:300, height:80, borderRadius:"50%", pointerEvents:"none" as const,
              background:"radial-gradient(ellipse, rgba(124,58,237,0.08) 0%, transparent 70%)" }} />
            <h1 style={{ margin:"0 0 4px", fontSize:26, fontWeight:900, letterSpacing:"-0.03em",
              color:"var(--text-primary)", display:"inline-flex", alignItems:"center", gap:10 }}>
              {campaignName.trim() || "Create New Campaign"}
              <span style={{ background:G, WebkitBackgroundClip:"text",
                WebkitTextFillColor:"transparent", backgroundClip:"text" }}>✦</span>
            </h1>
            <p style={{ margin:0, fontSize:12, color:"var(--text-secondary)" }}>
              {initialName
                ? `${initialBrand ? initialBrand + " · " : ""}AI-generated campaign`
                : "Describe your idea — AI agents will generate on-brand content across every format."}
            </p>
          </div>

        <StepProgress current={step} />

        {/* ═══ STEP 1 — Brief ═══ */}
        {step===1 && (
          <div style={{ width:"100%" }}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 }}>
              <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                <span style={{ fontSize:16, fontWeight:800, color:"var(--text-primary)" }}>Campaign Brief</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              </div>
              <button onClick={genCopy} disabled={!brief.trim()||copyBusy}
                style={{ display:"flex", alignItems:"center", gap:6, padding:"7px 14px",
                  borderRadius:8, border:"1.5px solid rgba(124,58,237,0.4)",
                  background:"rgba(124,58,237,0.12)", color:"#a78bfa",
                  fontSize:12, fontWeight:600, cursor:brief.trim()?"pointer":"not-allowed",
                  opacity:brief.trim()?1:0.5 }}>
                <span style={{ background:G, WebkitBackgroundClip:"text",
                  WebkitTextFillColor:"transparent", backgroundClip:"text" }}>✦</span>
                {copyBusy?"Improving…":"Improve with AI"}
              </button>
            </div>

            {/* Campaign name input */}
            <input
              value={campaignName} onChange={e => setCampaignName(e.target.value)}
              placeholder="Campaign name (e.g. Wash Day Glow)"
              maxLength={60}
              style={{ width:"100%", marginBottom:10, padding:"12px 16px",
                borderRadius:10, border:"1.5px solid var(--card-border)",
                background:"var(--card-bg)", color:"var(--text-primary)",
                fontFamily:"inherit", fontSize:14, fontWeight:600, outline:"none",
                boxSizing:"border-box" as const }} />

            {/* Textarea card */}
            <div style={{ borderRadius:16, border:"1.5px solid var(--card-border)",
              background:"var(--card-bg)", overflow:"hidden",
              boxShadow:"0 2px 16px rgba(0,0,0,0.06)" }}>
              <textarea value={brief} onChange={e=>setBrief(e.target.value)}
                maxLength={2000}
                placeholder="e.g. Create a Christmas campaign for Rnorr stock cubes targeting UK families. Warm, festive, family-focused — show the joy of cooking together."
                rows={7}
                style={{ width:"100%", padding:"20px 22px", border:"none", resize:"none" as const,
                  background:"transparent", color:"var(--text-primary)", fontFamily:"inherit",
                  fontSize:14, lineHeight:1.75, outline:"none", boxSizing:"border-box" as const }} />
              <div style={{ padding:"10px 22px 14px", display:"flex", justifyContent:"flex-end" }}>
                <span style={{ fontSize:11, color:"var(--text-secondary)" }}>
                  {brief.length} / 2000
                </span>
              </div>
            </div>

            {/* Copy improvement result */}
            {copyRes && (
              <div style={{ marginTop:12, padding:"14px 18px", borderRadius:12,
                border:"1px solid rgba(124,58,237,0.3)", background:"rgba(124,58,237,0.08)" }}>
                <div style={{ fontSize:11, fontWeight:700, color:"#a78bfa", marginBottom:6, textTransform:"uppercase" as const, letterSpacing:".06em" }}>AI Suggestion</div>
                <div style={{ fontSize:13, color:"var(--text-secondary)", lineHeight:1.6, cursor:"pointer" }}
                  onClick={() => setBrief(copyRes.headline + " " + copyRes.body)}>
                  {copyRes.headline} {copyRes.body}
                  <span style={{ marginLeft:8, fontSize:11, color:"#a78bfa" }}>(click to apply)</span>
                </div>
              </div>
            )}

            {/* Chip selectors */}
            <div style={{ display:"flex", gap:10, marginTop:16, flexWrap:"wrap" as const }}>
              <ChipSel label="Brand" value={brand} onChange={setBrand} opts={BRANDS}
                icon={brand&&BRAND_ICONS[brand]
                  ? <img src={BRAND_ICONS[brand]} style={{ width:14, height:14, objectFit:"contain" as const }} alt="" />
                  : <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>} />
              <ChipSel label="Campaign Goal" value={goal} onChange={setGoal} opts={GOALS}
                icon={<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="4"/></svg>} />
              <ChipSel label="Target Audience" value={audience} onChange={setAudience} opts={AUDIENCES}
                icon={<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>} />
              <ChipSel label="Platform" value={platform} onChange={setPlatform} opts={PLATFORMS}
                icon={<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>} />
              {voices.length > 0 && (
                <ChipSel label="Brand Voice" value={voiceName} onChange={setVoiceName}
                  opts={voices.map((v: BrandVoice) => v.name)}
                  icon={<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>} />
              )}
            </div>

            {/* Action buttons — right-aligned to match card edge */}
            <div style={{ display:"flex", gap:10, marginTop:20, justifyContent:"flex-end" as const }}>
              <button style={{ padding:"10px 22px", borderRadius:10, fontWeight:600, fontSize:13,
                border:"1.5px solid var(--card-border)", background:"transparent",
                color:"var(--text-secondary)", cursor:"pointer" }}>
                Save Draft
              </button>
              <button onClick={()=>brief.trim()&&setStep(2)} disabled={!brief.trim()}
                style={{ padding:"10px 28px", borderRadius:10, fontWeight:700, fontSize:13,
                  border:"none", background:G, color:"white",
                  cursor:brief.trim()?"pointer":"not-allowed",
                  opacity:brief.trim()?1:0.4,
                  boxShadow:brief.trim()?"0 4px 20px rgba(124,58,237,0.45)":"none" }}>
                Next: Choose Format →
              </button>
            </div>
          </div>
        )}

        {/* ═══ STEP 2 — Choose Format ═══ */}
        {step===2 && (
          <div style={{ width:"100%" }}>
            <div style={{ marginBottom:20 }}>
              <div style={{ fontSize:16, fontWeight:800, color:"var(--text-primary)", marginBottom:4 }}>Choose Your Content Format</div>
              <div style={{ fontSize:13, color:"var(--text-secondary)" }}>Select the type of content you want to generate. You can choose one or multiple formats.</div>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
              {fmtDefs.map(f => (
                <FormatCard key={f.type} {...f}
                  selected={formats.has(f.type)}
                  onClick={()=>toggleFmt(f.type)} />
              ))}
            </div>
            {formats.size>0 && (
              <div style={{ marginTop:14, fontSize:12, color:"var(--text-secondary)" }}>
                {formats.size} format{formats.size>1?"s":""} selected
              </div>
            )}

            {/* Step 2 buttons */}
            <div style={{ display:"flex", gap:10, marginTop:20, justifyContent:"flex-end" as const }}>
              <button onClick={()=>setStep(1)}
                style={{ padding:"10px 20px", borderRadius:10, fontWeight:600, fontSize:13,
                  border:"1.5px solid var(--card-border)", background:"transparent",
                  color:"var(--text-secondary)", cursor:"pointer" }}>← Back</button>
              <button onClick={()=>formats.size>0&&setStep(3)} disabled={formats.size===0}
                style={{ padding:"10px 32px", borderRadius:10, fontWeight:700, fontSize:14,
                  border:"none", background:G, color:"white",
                  cursor:formats.size>0?"pointer":"not-allowed", opacity:formats.size>0?1:0.4,
                  boxShadow:"0 4px 20px rgba(124,58,237,0.45)" }}>
                Next: Copy Agent →
              </button>
            </div>
          </div>
        )}

        {/* ═══ STEP 3 — Copy Agent (Ideon) ═══ */}
        {step===3 && (
          <div style={{ width:"100%" }}>
            <div style={{ marginBottom:20 }}>
              <div style={{ fontSize:16, fontWeight:800, color:"var(--text-primary)", marginBottom:4,
                display:"flex", alignItems:"center", gap:10 }}>
                ✍️ Copy Agent — Ideon
              </div>
              <div style={{ fontSize:13, color:"var(--text-secondary)" }}>
                Ideon writes your campaign headline, body copy and call-to-action.
              </div>
            </div>

            {!copyRes ? (
              <div style={{ padding:28, borderRadius:16, background:"var(--card-bg)",
                border:"1.5px solid var(--card-border)", textAlign:"center" as const,
                boxShadow:"0 2px 16px rgba(0,0,0,0.06)" }}>
                <div style={{ fontSize:36, marginBottom:14 }}>✍️</div>
                <div style={{ fontSize:15, fontWeight:700, color:"var(--text-primary)", marginBottom:6 }}>
                  Ready to generate copy
                </div>
                <div style={{ fontSize:13, color:"var(--text-secondary)", marginBottom:20, lineHeight:1.6 }}>
                  Based on your brief: <em>"{brief.slice(0,80)}{brief.length>80?"…":""}"</em>
                </div>
                <button onClick={genCopy} disabled={copyBusy}
                  style={{ padding:"12px 32px", borderRadius:12, border:"none",
                    background:G, color:"white", fontWeight:700, fontSize:14,
                    cursor:"pointer", boxShadow:"0 4px 16px rgba(124,58,237,0.35)",
                    display:"inline-flex", alignItems:"center", gap:8 }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                    <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                  </svg>
                  {copyBusy ? "Writing copy…" : "Generate Copy with Ideon"}
                </button>
              </div>
            ) : (
              <div style={{ display:"flex", flexDirection:"column" as const, gap:14 }}>
                {[
                  { key:"Headline", val:copyRes.headline, large:true },
                  { key:"Body Copy", val:copyRes.body, large:false },
                  { key:"Call to Action", val:copyRes.cta, large:false },
                ].map(f => (
                  <div key={f.key} style={{ padding:"16px 20px", borderRadius:14,
                    background:"var(--card-bg)", border:"1.5px solid var(--card-border)",
                    boxShadow:"0 2px 10px rgba(0,0,0,0.05)" }}>
                    <div style={{ fontSize:10, fontWeight:700, color:"var(--text-secondary)",
                      textTransform:"uppercase" as const, letterSpacing:".08em", marginBottom:8 }}>
                      {f.key}
                    </div>
                    <div style={{ fontSize:f.large?17:13, fontWeight:f.large?800:400,
                      color:"var(--text-primary)", lineHeight:1.6 }}>
                      {f.val}
                    </div>
                  </div>
                ))}
                <button onClick={genCopy} disabled={copyBusy}
                  style={{ padding:"8px 18px", borderRadius:8,
                    border:"1.5px solid var(--card-border)", background:"transparent",
                    color:"var(--text-secondary)", fontSize:12, cursor:"pointer" }}>
                  ↻ Regenerate copy
                </button>
              </div>
            )}

            {/* Step 3 buttons */}
            <div style={{ display:"flex", gap:10, marginTop:20, justifyContent:"flex-end" as const }}>
              <button onClick={()=>setStep(2)}
                style={{ padding:"10px 20px", borderRadius:10, fontWeight:600, fontSize:13,
                  border:"1.5px solid var(--card-border)", background:"transparent",
                  color:"var(--text-secondary)", cursor:"pointer" }}>← Back</button>
              <button onClick={()=>setStep(4)}
                style={{ padding:"10px 32px", borderRadius:10, fontWeight:700, fontSize:14,
                  border:"none", background:G, color:"white", cursor:"pointer",
                  boxShadow:"0 4px 20px rgba(124,58,237,0.45)" }}>
                Next: Generate Content ✦
              </button>
            </div>
          </div>
        )}

        {/* ═══ STEP 4 — Results ═══ */}
        {step===4 && (
          <div style={{ width:"100%" }}>

            {/* Status banner — changes between idle / generating / generated */}
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
              marginBottom:20 }}>
              <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                {generating ? (
                  <>
                    <div style={{ width:18, height:18, borderRadius:"50%", flexShrink:0,
                      border:"2.5px solid rgba(124,58,237,0.25)", borderTopColor:"#7c3aed",
                      animation:"spin 0.8s linear infinite" }} />
                    <span style={{ fontSize:16, fontWeight:700, color:"#7c3aed" }}>
                      Generating content…
                    </span>
                  </>
                ) : anyRes ? (
                  <>
                    <div style={{ width:22, height:22, borderRadius:"50%", background:"#10b981",
                      display:"flex", alignItems:"center", justifyContent:"center",
                      fontSize:12, color:"white", fontWeight:800, flexShrink:0 }}>✓</div>
                    <span style={{ fontSize:16, fontWeight:700, color:"#10b981" }}>
                      Generated
                    </span>
                  </>
                ) : (
                  <span style={{ fontSize:16, fontWeight:800, color:"var(--text-primary)" }}>
                    Generate &amp; Review
                  </span>
                )}
              </div>

              {/* Format tabs — visible only when content is ready */}
              {anyRes && (
                <div style={{ display:"flex", gap:8 }}>
                  {(["image","reel","tvc","video"] as FormatType[]).filter(hasRes).map(f=>(
                    <button key={f} onClick={()=>setTab(f)}
                      style={{ padding:"6px 14px", borderRadius:99, border:"none", cursor:"pointer",
                        fontSize:12, fontWeight:600,
                        background:tab===f?G:"var(--card-bg-soft)",
                        color:tab===f?"white":"var(--text-secondary)",
                        boxShadow:tab===f?"0 2px 10px rgba(124,58,237,0.4)":"none" }}>
                      {f==="image"?"🎨 Image":f==="reel"?"🎬 Reel":f==="tvc"?"📺 TVC":"▶️ Video"}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Generate button — shown when no results yet and not generating */}
            {!anyRes && !generating && (
              <div style={{ display:"flex", gap:10, marginBottom:24, justifyContent:"flex-end" as const }}>
                <button onClick={()=>setStep(3)}
                  style={{ padding:"10px 20px", borderRadius:10, fontWeight:600, fontSize:13,
                    border:"1.5px solid var(--card-border)", background:"transparent",
                    color:"var(--text-secondary)", cursor:"pointer" }}>← Back</button>
                <button onClick={genContent} disabled={formats.size===0||!brief.trim()}
                  style={{ padding:"10px 32px", borderRadius:10, fontWeight:700, fontSize:14,
                    border:"none", background:G, color:"white",
                    cursor:formats.size>0&&brief.trim()?"pointer":"not-allowed",
                    opacity:formats.size>0&&brief.trim()?1:0.4,
                    boxShadow:"0 4px 20px rgba(124,58,237,0.45)" }}>
                  ✦ Generate Content
                </button>
              </div>
            )}

            {generating ? (
              <div style={{ display:"flex", flexDirection:"column" as const, alignItems:"center",
                gap:20, padding:"60px 0" }}>
                <div style={{ position:"relative" as const, width:64, height:64 }}>
                  <div style={{ position:"absolute" as const, inset:0, borderRadius:"50%",
                    border:"3px solid var(--card-border)", borderTopColor:"#7c3aed",
                    animation:"spin 0.9s linear infinite" }} />
                  <div style={{ position:"absolute" as const, inset:8, borderRadius:"50%",
                    border:"2px solid var(--card-border)", borderBottomColor:"#a855f7",
                    animation:"spin 1.4s linear infinite reverse" }} />
                </div>
                <div>
                  <div style={{ fontSize:16, fontWeight:700, color:"var(--text-primary)",
                    textAlign:"center" as const, marginBottom:4 }}>
                    Generating content…
                  </div>
                  <div style={{ fontSize:12, color:"var(--text-secondary)", textAlign:"center" as const }}>
                    {Array.from(formats).map(f=>
                      f==="image"?"Morphis (Image)":f==="reel"?"Kinetik (Reel)":
                      f==="tvc"?`Director (TVC ${tvcLen}s)`:"Video Ad"
                    ).join(" · ")}
                  </div>
                </div>
              </div>
            ) : anyRes ? (
              <div style={{ display:"flex", flexDirection:"column" as const, gap:16 }}>
                {hasRes(tab) && (
                  <div>
                    <div style={{ borderRadius:16, overflow:"hidden",
                      boxShadow:"0 8px 32px rgba(0,0,0,0.12)", marginBottom:12 }}>
                      {tab==="image"&&results.image?.image_b64&&(
                        <img src={`data:image/jpeg;base64,${results.image.image_b64}`}
                          style={{ width:"100%", display:"block" }} alt="" />
                      )}
                      {(tab==="reel"||tab==="tvc"||tab==="video")&&results[tab]?.video_b64&&(
                        <video controls autoPlay loop muted playsInline
                          src={`data:video/mp4;base64,${results[tab]!.video_b64}`}
                          style={{ width:"100%", display:"block" }} />
                      )}
                    </div>

                    {/* ── Action row: Figma MCP + Modify | Save ── */}
                    <div style={{ display:"flex", alignItems:"center",
                      justifyContent:"space-between", marginTop:4 }}>
                      {/* Left: Figma MCP + Modify */}
                      <div style={{ display:"flex", gap:8 }}>
                        {tab==="image" && (
                          <button onClick={handleFigmaMcp} disabled={figmaState==="loading"}
                            style={{ display:"flex", alignItems:"center", gap:7,
                              padding:"9px 18px", borderRadius:10, cursor:"pointer",
                              fontFamily:"inherit", fontSize:13, fontWeight:600,
                              border:"1.5px solid var(--card-border)",
                              background:"var(--card-bg)",
                              color:"var(--text-primary)", transition:"all 0.2s",
                              opacity: figmaState==="loading" ? 0.6 : 1 }}>
                            {/* Figma F icon */}
                            <svg width="14" height="14" viewBox="0 0 38 57" fill="none">
                              <path d="M19 28.5a9.5 9.5 0 1 1 19 0 9.5 9.5 0 0 1-19 0z" fill="#1ABCFE"/>
                              <path d="M0 47.5A9.5 9.5 0 0 1 9.5 38H19v9.5a9.5 9.5 0 0 1-19 0z" fill="#0ACF83"/>
                              <path d="M19 0v19h9.5a9.5 9.5 0 0 0 0-19H19z" fill="#FF7262"/>
                              <path d="M0 9.5A9.5 9.5 0 0 0 9.5 19H19V0H9.5A9.5 9.5 0 0 0 0 9.5z" fill="#F24E1E"/>
                              <path d="M0 28.5A9.5 9.5 0 0 0 9.5 38H19V19H9.5A9.5 9.5 0 0 0 0 28.5z" fill="#FF7262"/>
                            </svg>
                            {figmaState==="loading" ? "Opening…" : figmaState==="ready" ? "Figma MCP ✓" : "Figma MCP"}
                          </button>
                        )}
                        <button onClick={() => { setPreModifyResults(results); setModifyOpen(true); }}
                          style={{ display:"flex", alignItems:"center", gap:7,
                            padding:"9px 18px", borderRadius:10, border:"none",
                            cursor:"pointer", fontFamily:"inherit", fontSize:13, fontWeight:700,
                            background:"linear-gradient(135deg,#7c3aed,#6366f1)",
                            color:"white", boxShadow:"0 4px 14px rgba(124,58,237,0.35)",
                            transition:"all 0.2s" }}>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                            <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                          </svg>
                          Modify
                        </button>
                      </div>
                      {/* Right: Publish + Save */}
                      <div style={{ display:"flex", gap:8 }}>
                      {onPublish && (
                        <button onClick={() => onPublish({
                          brand,
                          brief,
                          headline: copyRes?.headline ?? results.image?.headline,
                          body: results.image?.body,
                          image_b64: results.image?.image_b64,
                          contentType: tab === "image" ? "image" : "video",
                        })}
                          style={{ display:"flex", alignItems:"center", gap:7,
                            padding:"9px 18px", borderRadius:10, cursor:"pointer",
                            fontFamily:"inherit", fontSize:13, fontWeight:600,
                            border:"1.5px solid var(--card-border)",
                            background:"var(--card-bg)", color:"var(--text-primary)",
                            transition:"all 0.2s" }}>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13"/>
                          </svg>
                          Publish
                        </button>
                      )}
                      <button onClick={() => saveAsset(tab)} disabled={saveState[tab]==="saving"}
                        style={{ display:"flex", alignItems:"center", gap:8,
                          padding:"9px 20px", borderRadius:10, border:"none",
                          cursor:saveState[tab]==="saving"?"not-allowed":"pointer",
                          fontFamily:"inherit", fontSize:13, fontWeight:700,
                          background: saveState[tab]==="saved"
                            ? "rgba(16,185,129,0.12)"
                            : "linear-gradient(135deg,#7c3aed,#6366f1)",
                          color: saveState[tab]==="saved" ? "#10b981" : "white",
                          boxShadow: saveState[tab]==="saved" ? "none"
                            : "0 4px 14px rgba(124,58,237,0.35)",
                          transition:"all 0.2s" }}>
                        {saveState[tab]==="saving" ? (
                          <>
                            <div style={{ width:14, height:14, borderRadius:"50%",
                              border:"2px solid rgba(255,255,255,0.3)", borderTopColor:"white",
                              animation:"spin 0.8s linear infinite" }} />
                            Saving…
                          </>
                        ) : saveState[tab]==="saved" ? <>✓ Saved to Content Studio</> : (
                          <>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                              <polyline points="17 21 17 13 7 13 7 21"/>
                              <polyline points="7 3 7 8 15 8"/>
                            </svg>
                            Save to Content Studio
                          </>
                        )}
                      </button>
                      </div>
                    </div>
                  </div>
                )}
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:12 }}>
                  {[
                    { icon:"🏆", label:"Best Format", val:formats.has("reel")?"Reel":"Image", sub:"92% higher engagement" },
                    { icon:"📱", label:"Top Platform", val:platform||"Instagram", sub:"76% of your audience" },
                    { icon:"⏰", label:"Best Time", val:"7:00 PM", sub:"Peak engagement" },
                  ].map(i=>(
                    <div key={i.label} style={{ padding:16, borderRadius:14,
                      background:"var(--card-bg-soft)", border:"1px solid var(--card-border)" }}>
                      <div style={{ fontSize:20, marginBottom:8 }}>{i.icon}</div>
                      <div style={{ fontSize:10, fontWeight:700, color:"var(--text-secondary)",
                        textTransform:"uppercase" as const, letterSpacing:".06em", marginBottom:4 }}>{i.label}</div>
                      <div style={{ fontSize:14, fontWeight:800, color:"var(--text-primary)", marginBottom:2 }}>{i.val}</div>
                      <div style={{ fontSize:10, color:"var(--text-secondary)" }}>{i.sub}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ padding:"60px 0", textAlign:"center" as const }}>
                <div style={{ fontSize:14, color:"var(--text-secondary)" }}>
                  Click "Generate Content" to start
                </div>
              </div>
            )}
          </div>
        )}
        </div>{/* end centred wrapper */}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      {/* ── Modify panel ── full-screen overlay */}
      {modifyOpen && (
        <div style={{ position:"fixed" as const, inset:0, zIndex:200,
          display:"flex", flexDirection:"column" as const,
          background:"var(--page-bg)", fontFamily:"inherit" }}>

          {/* Top bar */}
          <div style={{ height:56, borderBottom:"1px solid var(--card-border)",
            display:"flex", alignItems:"center", justifyContent:"space-between",
            padding:"0 24px", flexShrink:0 }}>
            <div style={{ fontSize:17, fontWeight:700, color:"var(--text-primary)" }}>Modify</div>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <button onClick={() => setModifyOpen(false)}
                style={{ padding:"8px 20px", borderRadius:10, border:"none",
                background:"linear-gradient(135deg,#7c3aed,#6366f1)", color:"white",
                fontSize:13, fontWeight:700, cursor:"pointer", fontFamily:"inherit",
                display:"flex", alignItems:"center", gap:6 }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  strokeWidth="2.5" strokeLinecap="round">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                  <polyline points="17 21 17 13 7 13 7 21"/>
                </svg>
                Save
              </button>
              <button onClick={() => { setResults(preModifyResults); setModifyOpen(false); }}
                style={{ padding:"8px 18px", borderRadius:10,
                  border:"1.5px solid var(--card-border)", background:"transparent",
                  color:"var(--text-secondary)", fontSize:13, fontWeight:600,
                  cursor:"pointer", fontFamily:"inherit" }}>Cancel</button>
              <button onClick={() => { setResults(preModifyResults); setModifyOpen(false); }}
                style={{ background:"none", border:"none", cursor:"pointer",
                  color:"var(--text-tertiary)", fontSize:20, lineHeight:1,
                  padding:"4px 6px", borderRadius:6 }}>×</button>
            </div>
          </div>

          {/* Body */}
          <div style={{ flex:1, display:"flex", overflow:"hidden" }}>

            {/* Left panel */}
            <div style={{ width:320, flexShrink:0, borderRight:"1px solid var(--card-border)",
              display:"flex", flexDirection:"column" as const, padding:"20px 16px", gap:16,
              overflowY:"auto" as const }}>

              {/* Agent selector */}
              <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                <div style={{ flex:1, display:"flex", alignItems:"center", gap:8,
                  padding:"8px 14px", borderRadius:10, border:"1.5px solid var(--card-border)",
                  background:"var(--card-bg)", cursor:"pointer" }}>
                  <span style={{ fontSize:13, fontWeight:600, color:"var(--text-primary)" }}>Kinetik</span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                    strokeWidth="2.5" strokeLinecap="round" style={{ marginLeft:"auto" }}>
                    <path d="M6 9l6 6 6-6"/>
                  </svg>
                </div>
                <button style={{ width:36, height:36, borderRadius:10, border:"1.5px solid var(--card-border)",
                  background:"var(--card-bg)", cursor:"pointer", display:"flex",
                  alignItems:"center", justifyContent:"center", color:"var(--text-secondary)" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                    strokeWidth="2" strokeLinecap="round">
                    <circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/>
                  </svg>
                </button>
              </div>

              {/* Heading */}
              <div style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)", marginTop:4 }}>
                What changes would you like to make?
              </div>

              {/* Quick options */}
              {[
                { label:"Change Typography",   icon:"T", action: () => setModifyText("Change the typography — use a more elegant, modern font style for the headline and body text.") },
                { label:"Connect to Figma",    icon:"F", action: handleFigmaMcp },
                { label:"Adjust Color Palette", icon:"◉", action: () => setModifyText("Adjust the color palette — make it more vibrant and on-brand while keeping the overall composition the same.") },
              ].map(opt => (
                <button key={opt.label} onClick={opt.action}
                  style={{ display:"flex", alignItems:"center", gap:10,
                    padding:"10px 14px", borderRadius:10,
                    border:"1.5px solid var(--card-border)", background:"var(--card-bg)",
                    color:"var(--text-primary)", fontSize:13, fontWeight:500,
                    cursor:"pointer", fontFamily:"inherit", textAlign:"left" as const,
                    width:"100%", transition:"border-color 0.15s" }}>
                  <span style={{ fontSize:14, color:"var(--text-secondary)", width:18,
                    textAlign:"center" as const, flexShrink:0 }}>{opt.icon}</span>
                  {opt.label}
                </button>
              ))}

              {/* Free-text input */}
              <div style={{ marginTop:"auto", border:"1.5px solid var(--card-border)",
                borderRadius:12, background:"var(--card-bg)", padding:"10px 12px" }}>
                <input value={modifyText} onChange={e => setModifyText(e.target.value)}
                  placeholder="Describe your request…"
                  style={{ width:"100%", border:"none", background:"transparent",
                    fontSize:13, color:"var(--text-primary)", fontFamily:"inherit",
                    outline:"none", marginBottom:8 }} />
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <button style={{ width:28, height:28, borderRadius:8,
                    border:"1.5px solid var(--card-border)", background:"transparent",
                    cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center",
                    color:"var(--text-secondary)", fontSize:18, lineHeight:1 }}>+</button>
                  <button onClick={handleModifySubmit} disabled={!modifyText.trim() || modifyBusy}
                    style={{ width:28, height:28, borderRadius:8, border:"none",
                    background:"linear-gradient(135deg,#7c3aed,#6366f1)",
                    cursor: modifyText.trim() && !modifyBusy ? "pointer" : "not-allowed",
                    opacity: modifyText.trim() && !modifyBusy ? 1 : 0.4,
                    display:"flex", alignItems:"center", justifyContent:"center" }}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                      stroke="white" strokeWidth="2.5" strokeLinecap="round">
                      <line x1="22" y1="2" x2="11" y2="13"/>
                      <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            {/* Right panel — image preview */}
            <div style={{ flex:1, display:"flex", flexDirection:"column" as const,
              alignItems:"center", justifyContent:"center", padding:32, gap:16,
              overflowY:"auto" as const }}>
              {tab==="image" && results.image?.image_b64 ? (
                <img src={`data:image/jpeg;base64,${results.image.image_b64}`}
                  style={{ maxWidth:"100%", maxHeight:"70vh", borderRadius:16,
                    boxShadow:"0 16px 48px rgba(0,0,0,0.18)", display:"block" }} alt="" />
              ) : results[tab]?.video_b64 ? (
                <video controls autoPlay loop muted playsInline
                  src={`data:video/mp4;base64,${results[tab]!.video_b64}`}
                  style={{ maxWidth:"100%", maxHeight:"70vh", borderRadius:16,
                    boxShadow:"0 16px 48px rgba(0,0,0,0.18)", display:"block" }} />
              ) : null}
              <p style={{ fontSize:13, color:"var(--text-secondary)", textAlign:"center" as const,
                maxWidth:520, lineHeight:1.6, margin:0 }}>
                This creative is fully editable. You can rearrange the typography and logo,
                change the image, and modify the text. You can also ask the agent to make
                these changes for you.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
