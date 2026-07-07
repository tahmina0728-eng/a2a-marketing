import { useState } from "react";

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
export default function Campaigns() {
  const [step, setStep]       = useState<1|2|3|4>(1);
  const [brief, setBrief]     = useState("");
  const [brand, setBrand]     = useState("");
  const [goal, setGoal]       = useState("");
  const [audience, setAudience] = useState("");
  const [platform, setPlatform] = useState("");

  const [formats, setFormats] = useState<Set<FormatType>>(new Set());
  const [imgSz, setImgSz]     = useState("16:9");
  const [tvcLen, setTvcLen]   = useState("15");
  const [vidLen, setVidLen]   = useState("30s");

  const [copyRes, setCopyRes] = useState<{headline:string;body:string;cta:string}|null>(null);
  const [copyBusy, setCopyBusy] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [results, setResults] = useState<Partial<Record<FormatType, GeneratedResult>>>({});
  const [tab, setTab]         = useState<FormatType>("image");

  const prompt = [brand&&`Brand: ${brand}`, brief, goal&&`Goal: ${goal}`, audience&&`Audience: ${audience}`, platform&&`Platform: ${platform}`].filter(Boolean).join(". ");
  const anyRes = Object.values(results).some(r => r?.image_b64||r?.video_b64);
  const hasRes = (f: FormatType) => !!(results[f]?.image_b64 || results[f]?.video_b64);

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

      {/* ── Top bar ── */}
      <div style={{ padding:"18px 40px", borderBottom:"1px solid var(--card-border)",
        display:"flex", alignItems:"center", justifyContent:"space-between", flexShrink:0 }}>
        <div>
          <h1 style={{ margin:0, fontSize:22, fontWeight:900, color:"var(--text-primary)", letterSpacing:"-0.03em",
            display:"flex", alignItems:"center", gap:10 }}>
            Create New Campaign
            <span style={{ background:G, WebkitBackgroundClip:"text",
              WebkitTextFillColor:"transparent", backgroundClip:"text" }}>✦</span>
          </h1>
          <p style={{ margin:"3px 0 0", fontSize:12, color:"var(--text-secondary)" }}>
            Describe your idea, and AI will create on-brand content across formats.
          </p>
        </div>
        <div style={{ display:"flex", gap:10 }}>
          <button style={{ padding:"9px 20px", borderRadius:10, fontWeight:600, fontSize:13,
            border:"1.5px solid var(--card-border)", background:"var(--card-bg-soft)",
            color:"var(--text-secondary)", cursor:"pointer" }}>
            Save Draft
          </button>
          {step===1 && (
            <button onClick={()=>brief.trim()&&setStep(2)} disabled={!brief.trim()}
              style={{ padding:"9px 22px", borderRadius:10, fontWeight:700, fontSize:13,
                border:"none", background:G, color:"white", cursor:brief.trim()?"pointer":"not-allowed",
                opacity:brief.trim()?1:0.4, boxShadow:brief.trim()?"0 4px 16px rgba(124,58,237,0.4)":"none" }}>
              Next →
            </button>
          )}
          {step===2 && (
            <button onClick={()=>formats.size>0&&setStep(3)} disabled={formats.size===0}
              style={{ padding:"9px 22px", borderRadius:10, fontWeight:700, fontSize:13,
                border:"none", background:G, color:"white", cursor:formats.size>0?"pointer":"not-allowed",
                opacity:formats.size>0?1:0.4, boxShadow:"0 4px 16px rgba(124,58,237,0.4)" }}>
              Next: Copy Agent →
            </button>
          )}
          {step===3 && (
            <button onClick={()=>setStep(4)}
              style={{ padding:"9px 22px", borderRadius:10, fontWeight:700, fontSize:13,
                border:"none", background:G, color:"white", cursor:"pointer",
                boxShadow:"0 4px 16px rgba(124,58,237,0.4)" }}>
              Next: Generate ✦
            </button>
          )}
          {step===4 && (
            <button onClick={genContent} disabled={generating}
              style={{ padding:"9px 22px", borderRadius:10, fontWeight:700, fontSize:13,
                border:"none", background:G, color:"white", cursor:"pointer",
                boxShadow:"0 4px 16px rgba(124,58,237,0.4)" }}>
              {generating?"Generating…":"✦ Generate Content"}
            </button>
          )}
        </div>
      </div>

      {/* ── Content ── */}
      <div style={{ flex:1, overflowY:"auto", padding:"40px 24px",
        display:"flex", flexDirection:"column" as const, alignItems:"center" }}>
        {/* Centred wrapper — all step content lives here */}
        <div style={{ width:"100%", maxWidth:820 }}>
        <StepProgress current={step} />

        {/* ═══ STEP 1 — Brief ═══ */}
        {step===1 && (
          <div style={{ maxWidth:780 }}>
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
            </div>
          </div>
        )}

        {/* ═══ STEP 2 — Choose Format ═══ */}
        {step===2 && (
          <div style={{ maxWidth:780 }}>
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
              <div style={{ marginTop:20, padding:"14px 18px", borderRadius:12,
                border:"1px solid rgba(124,58,237,0.3)", background:"rgba(124,58,237,0.08)",
                display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                <span style={{ fontSize:13, color:"var(--text-secondary)" }}>
                  {formats.size} format{formats.size>1?"s":""} selected — {brief.slice(0,50)}{brief.length>50?"…":""}
                </span>
                <button onClick={genContent} disabled={generating}
                  style={{ padding:"9px 22px", borderRadius:10, border:"none",
                    background:G, color:"white", fontWeight:700, fontSize:13,
                    cursor:"pointer", boxShadow:"0 4px 16px rgba(124,58,237,0.4)" }}>
                  Next: Copy Agent →
                </button>
              </div>
            )}
          </div>
        )}

        {/* ═══ STEP 3 — Copy Agent (Ideon) ═══ */}
        {step===3 && (
          <div style={{ maxWidth:780 }}>
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
                <div style={{ display:"flex", gap:10 }}>
                  <button onClick={genCopy} disabled={copyBusy}
                    style={{ padding:"8px 18px", borderRadius:8,
                      border:"1.5px solid var(--card-border)", background:"transparent",
                      color:"var(--text-secondary)", fontSize:12, cursor:"pointer" }}>
                    ↻ Regenerate copy
                  </button>
                  <button onClick={()=>setStep(4)}
                    style={{ padding:"8px 22px", borderRadius:8, border:"none",
                      background:G, color:"white", fontWeight:700, fontSize:13,
                      cursor:"pointer", boxShadow:"0 2px 10px rgba(124,58,237,0.3)" }}>
                    Next: Generate Content ✦
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ═══ STEP 4 — Results ═══ */}
        {step===4 && (
          <div style={{ maxWidth:900 }}>
            <div style={{ marginBottom:20, display:"flex", alignItems:"center", gap:12 }}>
              <div style={{ fontSize:16, fontWeight:800, color:"var(--text-primary)" }}>Generated Content</div>
              {(["image","reel","tvc","video"] as FormatType[]).filter(hasRes).map(f=>(
                <button key={f} onClick={()=>setTab(f)}
                  style={{ padding:"6px 16px", borderRadius:99, border:"none", cursor:"pointer",
                    fontSize:12, fontWeight:600,
                    background:tab===f?G:"rgba(255,255,255,0.08)",
                    color:tab===f?"white":"rgba(255,255,255,0.5)",
                    boxShadow:tab===f?"0 2px 10px rgba(124,58,237,0.4)":"none" }}>
                  {f==="image"?"🎨 Image":f==="reel"?"🎬 Reel":f==="tvc"?"📺 TVC":"▶️ Video"}
                </button>
              ))}
            </div>
            {generating ? (
              <div style={{ display:"flex", flexDirection:"column" as const, alignItems:"center",
                gap:16, padding:"60px 0" }}>
                <div style={{ width:48, height:48, borderRadius:"50%",
                  border:"3px solid var(--card-border)", borderTopColor:"#7c3aed",
                  animation:"spin 1s linear infinite" }} />
                <div style={{ fontSize:14, color:"var(--text-secondary)" }}>Generating your campaign content…</div>
              </div>
            ) : anyRes ? (
              <div style={{ display:"flex", flexDirection:"column" as const, gap:16 }}>
                {hasRes(tab) && (
                  <div style={{ borderRadius:20, overflow:"hidden",
                    boxShadow:"0 12px 48px rgba(0,0,0,0.5)" }}>
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
    </div>
  );
}
