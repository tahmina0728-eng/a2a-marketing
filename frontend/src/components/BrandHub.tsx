import { useState, useRef, useEffect } from "react";
import type { BrandHubSection } from "./BrandHubNav";
import { DEFAULT_VOICES, VOICE_STORAGE_KEY } from "../constants/brandVoices";
import type { BrandVoice } from "../constants/brandVoices";

const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000";

// ── Brand Voice ────────────────────────────────────────────────

const TRAIT_COLOURS = ["#7c3aed","#6366f1","#0ea5e9","#10b981","#f59e0b","#ef4444","#ec4899"];

function TraitChip({ label, index }: { label: string; index: number }) {
  const color = TRAIT_COLOURS[index % TRAIT_COLOURS.length];
  return (
    <span style={{ display:"inline-block", padding:"3px 10px", borderRadius:99,
      background:`${color}18`, color, fontSize:11, fontWeight:700, letterSpacing:".02em" }}>
      {label}
    </span>
  );
}

function VoiceCard({ voice, onClick }: { voice: BrandVoice; onClick: () => void }) {
  return (
    <div onClick={onClick} style={{ padding:"20px 22px", borderRadius:14,
      border:"1.5px solid var(--card-border)", background:"var(--card-bg)",
      cursor:"pointer", transition:"box-shadow 0.15s, border-color 0.15s",
      display:"flex", flexDirection:"column" as const, gap:10 }}
      onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor="#7c3aed"; (e.currentTarget as HTMLDivElement).style.boxShadow="0 4px 20px rgba(124,58,237,0.12)"; }}
      onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor="var(--card-border)"; (e.currentTarget as HTMLDivElement).style.boxShadow="none"; }}>
      <div style={{ fontSize:15, fontWeight:800, color:"var(--text-primary)", lineHeight:1.3 }}>{voice.name}</div>
      <div style={{ fontSize:12, color:"var(--text-secondary)", lineHeight:1.6,
        overflow:"hidden", display:"-webkit-box", WebkitLineClamp:2, WebkitBoxOrient:"vertical" as const }}>
        {voice.description}
      </div>
      <div style={{ display:"flex", gap:6, flexWrap:"wrap" as const }}>
        {voice.traits.slice(0,4).map((t,i) => <TraitChip key={t} label={t} index={i} />)}
      </div>
      {voice.exampleSnippet && (
        <div>
          <div style={{ fontSize:10, fontWeight:700, color:"var(--text-tertiary)",
            textTransform:"uppercase" as const, letterSpacing:".08em", marginBottom:4 }}>
            Example Snippet
          </div>
          <div style={{ fontSize:12, color:"var(--text-secondary)", fontStyle:"italic",
            lineHeight:1.55, overflow:"hidden", display:"-webkit-box",
            WebkitLineClamp:2, WebkitBoxOrient:"vertical" as const }}>
            "{voice.exampleSnippet}"
          </div>
        </div>
      )}
    </div>
  );
}

function VoiceModal({ voice, isNew, onSave, onDelete, onClose }: {
  voice: BrandVoice; isNew: boolean;
  onSave: (v: BrandVoice) => void;
  onDelete: (id: string) => void;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState<BrandVoice>({ ...voice });
  const [traitsRaw, setTraitsRaw] = useState(voice.traits.join(", "));

  const handleSave = () => {
    if (!draft.name.trim()) return;
    onSave({ ...draft, traits: traitsRaw.split(",").map(t => t.trim()).filter(Boolean) });
  };

  return (
    <div style={{ position:"fixed" as const, inset:0, zIndex:300,
      background:"rgba(0,0,0,0.45)", display:"flex", alignItems:"center", justifyContent:"center" }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ width:"100%", maxWidth:520, margin:"0 20px", borderRadius:18,
        background:"var(--card-bg)", border:"1.5px solid var(--card-border)",
        boxShadow:"0 24px 60px rgba(0,0,0,0.25)", overflow:"hidden" }}>
        {/* Header */}
        <div style={{ padding:"20px 24px 0", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
          <div style={{ fontSize:16, fontWeight:800, color:"var(--text-primary)" }}>
            {isNew ? "New Brand Voice" : "Edit Brand Voice"}
          </div>
          <button onClick={onClose} style={{ background:"none", border:"none", cursor:"pointer",
            color:"var(--text-tertiary)", fontSize:20, padding:"2px 6px", borderRadius:6 }}>×</button>
        </div>
        {/* Body */}
        <div style={{ padding:"20px 24px", display:"flex", flexDirection:"column" as const, gap:14 }}>
          <div>
            <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)",
              textTransform:"uppercase" as const, letterSpacing:".07em", display:"block", marginBottom:6 }}>
              Voice Name
            </label>
            <input value={draft.name} onChange={e => setDraft(d => ({ ...d, name: e.target.value }))}
              placeholder="e.g. Bold & Confident"
              style={{ width:"100%", padding:"10px 14px", borderRadius:10,
                border:"1.5px solid var(--card-border)", background:"var(--card-bg-soft)",
                color:"var(--text-primary)", fontFamily:"inherit", fontSize:13,
                fontWeight:600, outline:"none", boxSizing:"border-box" as const }} />
          </div>
          <div>
            <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)",
              textTransform:"uppercase" as const, letterSpacing:".07em", display:"block", marginBottom:6 }}>
              Description / Tone
            </label>
            <textarea value={draft.description} onChange={e => setDraft(d => ({ ...d, description: e.target.value }))}
              placeholder="Describe the personality, tone and style..."
              rows={3}
              style={{ width:"100%", padding:"10px 14px", borderRadius:10, resize:"none" as const,
                border:"1.5px solid var(--card-border)", background:"var(--card-bg-soft)",
                color:"var(--text-primary)", fontFamily:"inherit", fontSize:13,
                lineHeight:1.6, outline:"none", boxSizing:"border-box" as const }} />
          </div>
          <div>
            <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)",
              textTransform:"uppercase" as const, letterSpacing:".07em", display:"block", marginBottom:6 }}>
              Traits <span style={{ fontWeight:400, textTransform:"none" as const }}>(comma-separated)</span>
            </label>
            <input value={traitsRaw} onChange={e => setTraitsRaw(e.target.value)}
              placeholder="e.g. Confident, Bold, Inspiring"
              style={{ width:"100%", padding:"10px 14px", borderRadius:10,
                border:"1.5px solid var(--card-border)", background:"var(--card-bg-soft)",
                color:"var(--text-primary)", fontFamily:"inherit", fontSize:13,
                outline:"none", boxSizing:"border-box" as const }} />
          </div>
          <div>
            <label style={{ fontSize:11, fontWeight:700, color:"var(--text-secondary)",
              textTransform:"uppercase" as const, letterSpacing:".07em", display:"block", marginBottom:6 }}>
              Example Snippet
            </label>
            <textarea value={draft.exampleSnippet} onChange={e => setDraft(d => ({ ...d, exampleSnippet: e.target.value }))}
              placeholder="A short example of this voice in action..."
              rows={3}
              style={{ width:"100%", padding:"10px 14px", borderRadius:10, resize:"none" as const,
                border:"1.5px solid var(--card-border)", background:"var(--card-bg-soft)",
                color:"var(--text-primary)", fontFamily:"inherit", fontSize:13,
                lineHeight:1.6, outline:"none", boxSizing:"border-box" as const }} />
          </div>
        </div>
        {/* Footer */}
        <div style={{ padding:"0 24px 22px", display:"flex", gap:10, justifyContent:"space-between" }}>
          {!isNew && (
            <button onClick={() => onDelete(draft.id)}
              style={{ padding:"9px 18px", borderRadius:10, border:"1.5px solid #ef444440",
                background:"transparent", color:"#ef4444", fontSize:13, fontWeight:600,
                cursor:"pointer", fontFamily:"inherit" }}>
              Delete
            </button>
          )}
          <div style={{ display:"flex", gap:10, marginLeft:"auto" }}>
            <button onClick={onClose}
              style={{ padding:"9px 18px", borderRadius:10, border:"1.5px solid var(--card-border)",
                background:"transparent", color:"var(--text-secondary)", fontSize:13, fontWeight:600,
                cursor:"pointer", fontFamily:"inherit" }}>
              Cancel
            </button>
            <button onClick={handleSave} disabled={!draft.name.trim()}
              style={{ padding:"9px 22px", borderRadius:10, border:"none",
                background:"linear-gradient(135deg,#7c3aed,#6366f1)", color:"white",
                fontSize:13, fontWeight:700, cursor:draft.name.trim()?"pointer":"not-allowed",
                opacity:draft.name.trim()?1:0.5, fontFamily:"inherit" }}>
              {isNew ? "Create Voice" : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function VoiceSection({ activeBrand }: { activeBrand?: string }) {
  const storageKey = activeBrand ? `${VOICE_STORAGE_KEY}_${activeBrand}` : VOICE_STORAGE_KEY;

  const load = (): BrandVoice[] => {
    try {
      const stored = localStorage.getItem(storageKey);
      return stored ? JSON.parse(stored) : DEFAULT_VOICES;
    } catch { return DEFAULT_VOICES; }
  };

  const [voices, setVoices] = useState<BrandVoice[]>(load);
  const [editing, setEditing] = useState<BrandVoice | null>(null);
  const [isNew, setIsNew] = useState(false);

  useEffect(() => { setVoices(load()); setEditing(null); }, [storageKey]);

  const persist = (updated: BrandVoice[]) => {
    setVoices(updated);
    localStorage.setItem(storageKey, JSON.stringify(updated));
  };

  const handleSave = (v: BrandVoice) => {
    persist(isNew ? [v, ...voices] : voices.map(x => x.id === v.id ? v : x));
    setEditing(null);
  };

  const handleDelete = (id: string) => {
    persist(voices.filter(v => v.id !== id));
    setEditing(null);
  };

  return (
    <div style={{ display:"flex", flexDirection:"column" as const, gap:20 }}>
      {/* Toolbar */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
        <div style={{ fontSize:13, color:"var(--text-secondary)", lineHeight:1.5 }}>
          {voices.length} voice{voices.length !== 1 ? "s" : ""} defined — used to shape AI-generated campaign copy
        </div>
        <button onClick={() => { setIsNew(true); setEditing({ id:`v_${Date.now()}`, name:"", description:"", traits:[], exampleSnippet:"" }); }}
          style={{ display:"flex", alignItems:"center", gap:8, padding:"9px 18px",
            borderRadius:10, border:"none", background:"linear-gradient(135deg,#7c3aed,#6366f1)",
            color:"white", fontSize:13, fontWeight:700, cursor:"pointer", fontFamily:"inherit" }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          New Voice
        </button>
      </div>

      {/* Grid */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(260px,1fr))", gap:16 }}>
        {voices.map(v => (
          <VoiceCard key={v.id} voice={v} onClick={() => { setIsNew(false); setEditing(v); }} />
        ))}
        {voices.length === 0 && (
          <div style={{ gridColumn:"1/-1", textAlign:"center" as const, padding:"48px 24px",
            color:"var(--text-tertiary)", fontSize:13 }}>
            No voices yet — click <strong>New Voice</strong> to get started.
          </div>
        )}
      </div>

      {/* Modal */}
      {editing && (
        <VoiceModal voice={editing} isNew={isNew}
          onSave={handleSave} onDelete={handleDelete} onClose={() => setEditing(null)} />
      )}
    </div>
  );
}

// ── Logos section ──────────────────────────────────────────────
function LogosSection({ activeBrand }: { activeBrand?: string }) {
  const [logos, setLogos] = useState<{ name: string; url: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeBrand) { setLoading(false); return; }
    setLoading(true);
    fetch(`${API_BASE}/brands/${encodeURIComponent(activeBrand)}/list-logos`)
      .then(r => r.json())
      .then(d => setLogos((d.logos ?? []).filter((l: any) => !l.name.toLowerCase().endsWith(".html"))))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [activeBrand]);

  if (loading) return (
    <div style={{ textAlign: "center" as const, padding: "40px 0", color: "var(--text-secondary)", fontSize: 13 }}>
      Loading logos…
    </div>
  );
  if (logos.length === 0) return (
    <ComingSoon title="Logos" description="No logo files found. Upload a brand package from Brand Assets to add logos." />
  );

  return (
    <div>
      <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 16 }}>
        {logos.length} logo file{logos.length !== 1 ? "s" : ""}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 16 }}>
        {logos.map(logo => (
          <div key={logo.name} style={{ borderRadius: 14,
            border: "1.5px solid var(--card-border)", background: "var(--card-bg)",
            padding: "20px 16px", display: "flex", flexDirection: "column" as const,
            alignItems: "center", gap: 10 }}>
            <div style={{
              width: "100%", height: 100, borderRadius: 8,
              background: "repeating-conic-gradient(rgba(128,128,128,0.08) 0% 25%, transparent 0% 50%) 0 0 / 14px 14px",
              display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
              <img src={`${API_BASE}${logo.url}`} alt={logo.name}
                style={{ maxWidth: "90%", maxHeight: "90%", objectFit: "contain" }} />
            </div>
            <div style={{ fontSize: 10, color: "var(--text-secondary)", textAlign: "center" as const,
              wordBreak: "break-all" as const, lineHeight: 1.4 }}>
              {logo.name}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Fonts section ───────────────────────────────────────────────
function FontsSection({ activeBrand }: { activeBrand?: string }) {
  const [fonts, setFonts] = useState<{ name: string; url: string; stem: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeBrand) { setLoading(false); return; }
    setLoading(true);
    fetch(`${API_BASE}/brands/${encodeURIComponent(activeBrand)}/list-fonts`)
      .then(r => r.json())
      .then(d => {
        const list = (d.fonts ?? []).filter((f: any) => !f.name.toLowerCase().endsWith(".html"));
        setFonts(list);
        list.forEach((font: { name: string; url: string; stem: string }) => {
          const family = `bh-${font.stem}`;
          if (!document.querySelector(`style[data-font="${family}"]`)) {
            const s = document.createElement("style");
            s.setAttribute("data-font", family);
            s.textContent = `@font-face { font-family: "${family}"; src: url("${API_BASE}${font.url}"); }`;
            document.head.appendChild(s);
          }
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [activeBrand]);

  if (loading) return (
    <div style={{ textAlign: "center" as const, padding: "40px 0", color: "var(--text-secondary)", fontSize: 13 }}>
      Loading fonts…
    </div>
  );
  if (fonts.length === 0) return (
    <ComingSoon title="Fonts" description="No font files found. Upload a brand package from Brand Assets to add fonts." />
  );

  return (
    <div style={{ display: "flex", flexDirection: "column" as const, gap: 14 }}>
      <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
        {fonts.length} font file{fonts.length !== 1 ? "s" : ""}
      </div>
      {fonts.map(font => {
        const family = `bh-${font.stem}`;
        const displayName = font.stem.replace(/[-_]/g, " ");
        return (
          <div key={font.name} style={{ borderRadius: 14,
            border: "1.5px solid var(--card-border)", background: "var(--card-bg)",
            padding: "20px 24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between",
              alignItems: "flex-start", marginBottom: 14 }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                  {displayName}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>
                  {font.name}
                </div>
              </div>
              <a href={`${API_BASE}${font.url}`} download={font.name}
                style={{ padding: "5px 12px", borderRadius: 8,
                  border: "1.5px solid var(--card-border)", background: "transparent",
                  color: "var(--text-secondary)", fontSize: 11, fontWeight: 600,
                  cursor: "pointer", textDecoration: "none" }}>
                ↓ Download
              </a>
            </div>
            <div style={{ fontFamily: `"${family}", sans-serif`, fontSize: 30,
              color: "var(--text-primary)", lineHeight: 1.2, marginBottom: 6 }}>
              Aa Bb Cc Dd Ee
            </div>
            <div style={{ fontFamily: `"${family}", sans-serif`, fontSize: 13,
              color: "var(--text-secondary)", lineHeight: 1.8 }}>
              ABCDEFGHIJKLMNOPQRSTUVWXYZ
            </div>
            <div style={{ fontFamily: `"${family}", sans-serif`, fontSize: 13,
              color: "var(--text-secondary)", lineHeight: 1.8 }}>
              abcdefghijklmnopqrstuvwxyz&nbsp;&nbsp;0 1 2 3 4 5 6 7 8 9
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Visual Identity section ────────────────────────────────────
type ColourEntry = { name: string; hex: string; rgb: string; role: string };
type Palette = Record<string, ColourEntry[] | { name: string; from: string; to: string; role: string }>;

function VisualIdentitySection({ activeBrand }: { activeBrand?: string }) {
  const [mode, setMode] = useState<"json" | "images" | null>(null);
  const [palette, setPalette] = useState<Palette>({});
  const [swatches, setSwatches] = useState<{ name: string; url: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeBrand) { setLoading(false); return; }
    setLoading(true);
    fetch(`${API_BASE}/brands/${encodeURIComponent(activeBrand)}/list-colours`)
      .then(r => r.json())
      .then(d => {
        setMode(d.mode);
        if (d.mode === "json") setPalette(d.palette ?? {});
        else setSwatches(d.swatches ?? []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [activeBrand]);

  if (loading) return <div style={{ textAlign: "center" as const, padding: "40px 0", color: "var(--text-secondary)", fontSize: 13 }}>Loading…</div>;

  if (mode === "json" && Object.keys(palette).length > 0) {
    const groupLabel: Record<string, string> = {
      primary: "Primary Colours", secondary: "Secondary", neutral: "Neutrals",
      tertiary: "Tertiary", functional: "Functional", gradient: "Gradient",
    };
    return (
      <div style={{ display: "flex", flexDirection: "column" as const, gap: 28 }}>
        {Object.entries(palette).map(([group, entries]) => {
          const label = groupLabel[group] ?? group.charAt(0).toUpperCase() + group.slice(1);
          const isGrad = !Array.isArray(entries);
          return (
            <div key={group}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
                textTransform: "uppercase" as const, color: "var(--text-secondary)",
                marginBottom: 12, opacity: 0.7 }}>
                {label}
              </div>
              {isGrad ? (
                <div style={{ borderRadius: 14, border: "1.5px solid var(--card-border)",
                  background: "var(--card-bg)", padding: "16px 20px",
                  display: "flex", alignItems: "center", gap: 16 }}>
                  <div style={{ width: 64, height: 40, borderRadius: 8, flexShrink: 0,
                    background: `linear-gradient(90deg, ${(entries as any).from}, ${(entries as any).to})` }} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{(entries as any).name}</div>
                    <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>{(entries as any).from} → {(entries as any).to}</div>
                    <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>{(entries as any).role}</div>
                  </div>
                </div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 }}>
                  {(entries as ColourEntry[]).map(c => (
                    <div key={c.hex} style={{ borderRadius: 14, border: "1.5px solid var(--card-border)",
                      background: "var(--card-bg)", overflow: "hidden" }}>
                      <div style={{ height: 56, background: c.hex }} />
                      <div style={{ padding: "10px 14px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>{c.name}</span>
                          <code style={{ fontSize: 10, fontWeight: 600, color: "var(--text-secondary)",
                            background: "var(--card-bg-soft)", padding: "2px 6px", borderRadius: 4 }}>{c.hex}</code>
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.4 }}>{c.role}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  if (mode === "images" && swatches.length > 0) {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 12 }}>
        {swatches.map(s => (
          <div key={s.name} style={{ borderRadius: 12, border: "1.5px solid var(--card-border)",
            background: "var(--card-bg)", overflow: "hidden" }}>
            <img src={`${API_BASE}${s.url}`} alt={s.name} style={{ width: "100%", height: 80, objectFit: "cover" }} />
            <div style={{ padding: "8px 12px", fontSize: 11, color: "var(--text-secondary)" }}>{s.name}</div>
          </div>
        ))}
      </div>
    );
  }

  return <ComingSoon title="Visual Identity" description="No colour palette found. Upload a brand package from Brand Assets." />;
}

// ── Products & Services section ────────────────────────────────
function ProductsSection({ activeBrand }: { activeBrand?: string }) {
  const [products, setProducts] = useState<{ name: string; url: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeBrand) { setLoading(false); return; }
    setLoading(true);
    fetch(`${API_BASE}/brands/${encodeURIComponent(activeBrand)}/list-products`)
      .then(r => r.json())
      .then(d => setProducts(d.products ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [activeBrand]);

  if (loading) return <div style={{ textAlign: "center" as const, padding: "40px 0", color: "var(--text-secondary)", fontSize: 13 }}>Loading…</div>;
  if (products.length === 0) return <ComingSoon title="Products & Services" description="No product images found. Upload a brand package from Brand Assets." />;

  return (
    <div>
      <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 16 }}>
        {products.length} product{products.length !== 1 ? "s" : ""}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 14 }}>
        {products.map(p => (
          <div key={p.name} style={{ borderRadius: 14, border: "1.5px solid var(--card-border)",
            background: "var(--card-bg)", overflow: "hidden" }}>
            <div style={{ height: 140, background: "var(--card-bg-soft)",
              display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
              <img src={`${API_BASE}${p.url}`} alt={p.name}
                style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain", padding: 8 }} />
            </div>
            <div style={{ padding: "8px 12px", fontSize: 11, color: "var(--text-secondary)",
              wordBreak: "break-all" as const }}>
              {p.name.replace(/\.[^.]+$/, "")}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Documents section ──────────────────────────────────────────
const DOC_ICONS: Record<string, string> = {
  md: "📝", txt: "📄", pdf: "📕", json: "🗂", html: "🌐", docx: "📘", pptx: "📊",
};

function DocumentsSection({ activeBrand }: { activeBrand?: string }) {
  const [docs, setDocs] = useState<{ name: string; category: string; url: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeBrand) { setLoading(false); return; }
    setLoading(true);
    fetch(`${API_BASE}/brands/${encodeURIComponent(activeBrand)}/list-documents`)
      .then(r => r.json())
      .then(d => setDocs(d.documents ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [activeBrand]);

  if (loading) return <div style={{ textAlign: "center" as const, padding: "40px 0", color: "var(--text-secondary)", fontSize: 13 }}>Loading…</div>;
  if (docs.length === 0) return <ComingSoon title="Documents" description="No documents found. Upload a brand package from Brand Assets." />;

  const grouped = docs.reduce<Record<string, typeof docs>>((acc, d) => {
    (acc[d.category] = acc[d.category] || []).push(d); return acc;
  }, {});

  return (
    <div style={{ display: "flex", flexDirection: "column" as const, gap: 24 }}>
      {Object.entries(grouped).map(([cat, files]) => (
        <div key={cat}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
            textTransform: "uppercase" as const, color: "var(--text-secondary)",
            marginBottom: 10, opacity: 0.7 }}>
            {cat}
          </div>
          <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
            {files.map(doc => {
              const ext = doc.name.split(".").pop()?.toLowerCase() ?? "";
              const icon = DOC_ICONS[ext] ?? "📎";
              return (
                <div key={doc.name} style={{ borderRadius: 12,
                  border: "1.5px solid var(--card-border)", background: "var(--card-bg)",
                  padding: "12px 16px", display: "flex", alignItems: "center",
                  justifyContent: "space-between", gap: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 18 }}>{icon}</span>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{doc.name}</div>
                      <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 1 }}>{ext.toUpperCase()}</div>
                    </div>
                  </div>
                  <a href={`${API_BASE}${doc.url}`} download={doc.name}
                    style={{ padding: "5px 12px", borderRadius: 8,
                      border: "1.5px solid var(--card-border)", background: "transparent",
                      color: "var(--text-secondary)", fontSize: 11, fontWeight: 600,
                      cursor: "pointer", textDecoration: "none", flexShrink: 0 }}>
                    ↓ Download
                  </a>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Competitors section ────────────────────────────────────────
interface Competitor { id: string; name: string; positioning: string; strengths: string; weaknesses: string; }

function CompetitorsSection({ activeBrand }: { activeBrand?: string }) {
  const storageKey = `brandHub_competitors_${activeBrand ?? ""}`;
  const [items, setItems] = useState<Competitor[]>(() => {
    try { return JSON.parse(localStorage.getItem(storageKey) ?? "[]"); } catch { return []; }
  });
  const [editing, setEditing] = useState<Competitor | null>(null);
  const [isNew, setIsNew] = useState(false);

  useEffect(() => {
    try { setItems(JSON.parse(localStorage.getItem(storageKey) ?? "[]")); } catch { setItems([]); }
  }, [storageKey]);

  const persist = (updated: Competitor[]) => {
    setItems(updated);
    localStorage.setItem(storageKey, JSON.stringify(updated));
  };
  const save = (v: Competitor) => { persist(isNew ? [v, ...items] : items.map(x => x.id === v.id ? v : x)); setEditing(null); };
  const del  = (id: string)    => { persist(items.filter(x => x.id !== id)); setEditing(null); };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{items.length} competitor{items.length !== 1 ? "s" : ""} tracked</div>
        <button onClick={() => { setIsNew(true); setEditing({ id: `c_${Date.now()}`, name: "", positioning: "", strengths: "", weaknesses: "" }); }}
          style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 18px", borderRadius: 10, border: "none",
            background: "linear-gradient(135deg,#7c3aed,#6366f1)", color: "white", fontSize: 13, fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Add Competitor
        </button>
      </div>
      {items.length === 0 && <ComingSoon title="Competitors" description="Track your competitive landscape — add positioning notes, strengths and weaknesses for each competitor." />}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
        {items.map(c => (
          <div key={c.id} onClick={() => { setIsNew(false); setEditing(c); }}
            style={{ borderRadius: 14, border: "1.5px solid var(--card-border)", background: "var(--card-bg)",
              padding: "18px 20px", cursor: "pointer", transition: "border-color 0.15s, box-shadow 0.15s" }}
            onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = "#7c3aed"; (e.currentTarget as HTMLDivElement).style.boxShadow = "0 4px 20px rgba(124,58,237,0.12)"; }}
            onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = "var(--card-border)"; (e.currentTarget as HTMLDivElement).style.boxShadow = "none"; }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: "var(--text-primary)", marginBottom: 8 }}>{c.name}</div>
            {c.positioning && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 10, lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as const, overflow: "hidden" }}>{c.positioning}</div>}
            <div style={{ display: "flex", gap: 8 }}>
              {c.strengths  && <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 99, background: "rgba(16,185,129,0.12)", color: "#10b981", fontWeight: 700 }}>💪 Strengths</span>}
              {c.weaknesses && <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 99, background: "rgba(239,68,68,0.10)",  color: "#ef4444", fontWeight: 700 }}>⚠ Weaknesses</span>}
            </div>
          </div>
        ))}
      </div>
      {editing && (
        <CompetitorModal competitor={editing} isNew={isNew} onSave={save} onDelete={del} onClose={() => setEditing(null)} />
      )}
    </div>
  );
}

function CompetitorModal({ competitor, isNew, onSave, onDelete, onClose }: {
  competitor: Competitor; isNew: boolean;
  onSave: (v: Competitor) => void; onDelete: (id: string) => void; onClose: () => void;
}) {
  const [d, setD] = useState({ ...competitor });
  const field = (label: string, key: keyof Competitor, rows?: number) => (
    <div>
      <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" as const, letterSpacing: ".07em", display: "block", marginBottom: 6 }}>{label}</label>
      {rows ? (
        <textarea value={d[key] as string} onChange={e => setD(x => ({ ...x, [key]: e.target.value }))} rows={rows}
          style={{ width: "100%", padding: "10px 14px", borderRadius: 10, resize: "none" as const, border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)", color: "var(--text-primary)", fontFamily: "inherit", fontSize: 13, lineHeight: 1.6, outline: "none", boxSizing: "border-box" as const }} />
      ) : (
        <input value={d[key] as string} onChange={e => setD(x => ({ ...x, [key]: e.target.value }))}
          style={{ width: "100%", padding: "10px 14px", borderRadius: 10, border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)", color: "var(--text-primary)", fontFamily: "inherit", fontSize: 13, fontWeight: 600, outline: "none", boxSizing: "border-box" as const }} />
      )}
    </div>
  );
  return (
    <div style={{ position: "fixed" as const, inset: 0, zIndex: 300, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ width: "100%", maxWidth: 500, margin: "0 20px", borderRadius: 18, background: "var(--card-bg)", border: "1.5px solid var(--card-border)", boxShadow: "0 24px 60px rgba(0,0,0,0.25)", overflow: "hidden" }}>
        <div style={{ padding: "20px 24px 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)" }}>{isNew ? "Add Competitor" : "Edit Competitor"}</div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", fontSize: 20, padding: "2px 6px" }}>×</button>
        </div>
        <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column" as const, gap: 14 }}>
          {field("Competitor Name", "name")}
          {field("Positioning / Market Focus", "positioning", 2)}
          {field("Key Strengths", "strengths", 2)}
          {field("Key Weaknesses", "weaknesses", 2)}
        </div>
        <div style={{ padding: "0 24px 22px", display: "flex", justifyContent: "space-between" }}>
          {!isNew && <button onClick={() => onDelete(d.id)} style={{ padding: "9px 18px", borderRadius: 10, border: "1.5px solid #ef444440", background: "transparent", color: "#ef4444", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>Delete</button>}
          <div style={{ display: "flex", gap: 10, marginLeft: "auto" }}>
            <button onClick={onClose} style={{ padding: "9px 18px", borderRadius: 10, border: "1.5px solid var(--card-border)", background: "transparent", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>Cancel</button>
            <button onClick={() => d.name.trim() && onSave(d)} disabled={!d.name.trim()}
              style={{ padding: "9px 22px", borderRadius: 10, border: "none", background: "linear-gradient(135deg,#7c3aed,#6366f1)", color: "white", fontSize: 13, fontWeight: 700, cursor: d.name.trim() ? "pointer" : "not-allowed", opacity: d.name.trim() ? 1 : 0.5, fontFamily: "inherit" }}>
              {isNew ? "Add" : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Customer Personas section ──────────────────────────────────
interface Persona { id: string; name: string; segment: string; age: string; channels: string; motivation: string; painPoint: string; }

function PersonasSection({ activeBrand }: { activeBrand?: string }) {
  const storageKey = `brandHub_personas_${activeBrand ?? ""}`;
  const [items, setItems] = useState<Persona[]>(() => {
    try { return JSON.parse(localStorage.getItem(storageKey) ?? "[]"); } catch { return []; }
  });
  const [editing, setEditing] = useState<Persona | null>(null);
  const [isNew, setIsNew] = useState(false);

  useEffect(() => {
    try { setItems(JSON.parse(localStorage.getItem(storageKey) ?? "[]")); } catch { setItems([]); }
  }, [storageKey]);

  const persist = (updated: Persona[]) => { setItems(updated); localStorage.setItem(storageKey, JSON.stringify(updated)); };
  const save = (v: Persona) => { persist(isNew ? [v, ...items] : items.map(x => x.id === v.id ? v : x)); setEditing(null); };
  const del  = (id: string) => { persist(items.filter(x => x.id !== id)); setEditing(null); };

  const AVATAR_COLORS = ["#7c3aed","#6366f1","#0ea5e9","#10b981","#f59e0b","#ef4444","#ec4899"];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{items.length} persona{items.length !== 1 ? "s" : ""} defined</div>
        <button onClick={() => { setIsNew(true); setEditing({ id: `p_${Date.now()}`, name: "", segment: "", age: "", channels: "", motivation: "", painPoint: "" }); }}
          style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 18px", borderRadius: 10, border: "none",
            background: "linear-gradient(135deg,#7c3aed,#6366f1)", color: "white", fontSize: 13, fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          New Persona
        </button>
      </div>
      {items.length === 0 && <ComingSoon title="Customer Personas" description="Define target audience segments — age, motivation, channels and pain points used to power personalised campaign briefs." />}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
        {items.map((p, i) => {
          const color = AVATAR_COLORS[i % AVATAR_COLORS.length];
          const initials = p.name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
          return (
            <div key={p.id} onClick={() => { setIsNew(false); setEditing(p); }}
              style={{ borderRadius: 14, border: "1.5px solid var(--card-border)", background: "var(--card-bg)",
                padding: "18px 20px", cursor: "pointer", transition: "border-color 0.15s, box-shadow 0.15s" }}
              onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = color; (e.currentTarget as HTMLDivElement).style.boxShadow = `0 4px 20px ${color}20`; }}
              onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = "var(--card-border)"; (e.currentTarget as HTMLDivElement).style.boxShadow = "none"; }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
                <div style={{ width: 40, height: 40, borderRadius: "50%", background: `${color}22`, border: `2px solid ${color}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 800, color, flexShrink: 0 }}>{initials || "?"}</div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>{p.name || "Unnamed Persona"}</div>
                  {p.segment && <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 1 }}>{p.segment}</div>}
                </div>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 6 }}>
                {p.age      && <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 99, background: `${color}18`, color, fontWeight: 700 }}>Age: {p.age}</span>}
                {p.channels && <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 99, background: "var(--card-bg-soft)", color: "var(--text-secondary)", fontWeight: 600 }}>{p.channels}</span>}
              </div>
              {p.motivation && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 10, lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as const, overflow: "hidden" }}>💡 {p.motivation}</div>}
            </div>
          );
        })}
      </div>
      {editing && <PersonaModal persona={editing} isNew={isNew} onSave={save} onDelete={del} onClose={() => setEditing(null)} />}
    </div>
  );
}

function PersonaModal({ persona, isNew, onSave, onDelete, onClose }: {
  persona: Persona; isNew: boolean;
  onSave: (v: Persona) => void; onDelete: (id: string) => void; onClose: () => void;
}) {
  const [d, setD] = useState({ ...persona });
  const field = (label: string, key: keyof Persona, placeholder: string, rows?: number) => (
    <div>
      <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" as const, letterSpacing: ".07em", display: "block", marginBottom: 6 }}>{label}</label>
      {rows ? (
        <textarea value={d[key] as string} onChange={e => setD(x => ({ ...x, [key]: e.target.value }))} rows={rows} placeholder={placeholder}
          style={{ width: "100%", padding: "10px 14px", borderRadius: 10, resize: "none" as const, border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)", color: "var(--text-primary)", fontFamily: "inherit", fontSize: 13, lineHeight: 1.6, outline: "none", boxSizing: "border-box" as const }} />
      ) : (
        <input value={d[key] as string} onChange={e => setD(x => ({ ...x, [key]: e.target.value }))} placeholder={placeholder}
          style={{ width: "100%", padding: "10px 14px", borderRadius: 10, border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)", color: "var(--text-primary)", fontFamily: "inherit", fontSize: 13, fontWeight: 600, outline: "none", boxSizing: "border-box" as const }} />
      )}
    </div>
  );
  return (
    <div style={{ position: "fixed" as const, inset: 0, zIndex: 300, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ width: "100%", maxWidth: 520, margin: "0 20px", borderRadius: 18, background: "var(--card-bg)", border: "1.5px solid var(--card-border)", boxShadow: "0 24px 60px rgba(0,0,0,0.25)", overflow: "hidden", maxHeight: "90vh", overflowY: "auto" as const }}>
        <div style={{ padding: "20px 24px 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)" }}>{isNew ? "New Persona" : "Edit Persona"}</div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", fontSize: 20, padding: "2px 6px" }}>×</button>
        </div>
        <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column" as const, gap: 14 }}>
          {field("Persona Name", "name", "e.g. Urban Health-Seeker")}
          {field("Segment", "segment", "e.g. Women 30–45, mid-income, health-conscious")}
          {field("Age Range", "age", "e.g. 30–45")}
          {field("Primary Channels", "channels", "e.g. Instagram, YouTube, email")}
          {field("Core Motivation", "motivation", "What drives them to choose this brand?", 2)}
          {field("Pain Point", "painPoint", "What problem are they trying to solve?", 2)}
        </div>
        <div style={{ padding: "0 24px 22px", display: "flex", justifyContent: "space-between" }}>
          {!isNew && <button onClick={() => onDelete(d.id)} style={{ padding: "9px 18px", borderRadius: 10, border: "1.5px solid #ef444440", background: "transparent", color: "#ef4444", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>Delete</button>}
          <div style={{ display: "flex", gap: 10, marginLeft: "auto" }}>
            <button onClick={onClose} style={{ padding: "9px 18px", borderRadius: 10, border: "1.5px solid var(--card-border)", background: "transparent", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>Cancel</button>
            <button onClick={() => d.name.trim() && onSave(d)} disabled={!d.name.trim()}
              style={{ padding: "9px 22px", borderRadius: 10, border: "none", background: "linear-gradient(135deg,#7c3aed,#6366f1)", color: "white", fontSize: 13, fontWeight: 700, cursor: d.name.trim() ? "pointer" : "not-allowed", opacity: d.name.trim() ? 1 : 0.5, fontFamily: "inherit" }}>
              {isNew ? "Create" : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Overview section ───────────────────────────────────────────
const BRANDS_META: Record<string, { emoji: string; label: string }> = {
  Rnorr:       { emoji: "🎯", label: "Rnorr" },
  Sunglow:     { emoji: "✨", label: "Sunglow" },
  Boozt:       { emoji: "👗", label: "Boozt" },
  Glenfiddich: { emoji: "🥃", label: "Glenfiddich × AMF1" },
  "UBS Bank":  { emoji: "🏦", label: "UBS Bank" },
  sunrise:     { emoji: "🌅", label: "Sunrise" },
  Haleon:      { emoji: "💊", label: "Haleon" },
};

const QUICK_LINKS: { id: BrandHubSection; label: string; icon: string }[] = [
  { id: "logos",           label: "Logos",           icon: "🖼" },
  { id: "fonts",           label: "Fonts",           icon: "Aa" },
  { id: "visual-identity", label: "Colours",         icon: "🎨" },
  { id: "brand-voice",     label: "Brand Voice",     icon: "💬" },
  { id: "products",        label: "Products",        icon: "📦" },
  { id: "competitors",     label: "Competitors",     icon: "⚔" },
  { id: "personas",        label: "Personas",        icon: "👤" },
  { id: "documents",       label: "Documents",       icon: "📄" },
];

interface OverviewSectionProps { activeBrand?: string; onNavigate?: (s: BrandHubSection) => void; }

function OverviewSection({ activeBrand, onNavigate }: OverviewSectionProps) {
  const brand = activeBrand ?? "";
  const meta  = BRANDS_META[brand] ?? { emoji: "🏷", label: brand };

  const [logo, setLogo]   = useState<string | null>(null);
  const [palette, setPalette] = useState<{ hex: string; name: string }[]>([]);
  const [traits,  setTraits]  = useState<string[]>([]);

  useEffect(() => {
    if (!brand) return;
    const enc = encodeURIComponent(brand);

    fetch(`${API_BASE}/brands/${enc}/list-logos`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.logos?.length) setLogo(API_BASE + d.logos[0].url); })
      .catch(() => {});

    fetch(`${API_BASE}/brands/${enc}/list-colours`)
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (!d) return;
        if (d.mode === "json" && d.palette) {
          const swatches: { hex: string; name: string }[] = [];
          for (const entries of Object.values(d.palette)) {
            if (Array.isArray(entries)) {
              for (const e of entries as { hex: string; name: string }[]) {
                swatches.push({ hex: e.hex, name: e.name });
                if (swatches.length >= 8) break;
              }
            }
            if (swatches.length >= 8) break;
          }
          setPalette(swatches);
        }
      })
      .catch(() => {});

    try {
      const voiceKey = brand ? `${VOICE_STORAGE_KEY}_${brand}` : VOICE_STORAGE_KEY;
      const voices: BrandVoice[] = JSON.parse(localStorage.getItem(voiceKey) ?? "null") ?? DEFAULT_VOICES;
      setTraits(voices.flatMap(v => v.traits).slice(0, 6));
    } catch { /* ignore */ }
  }, [brand]);

  const messagingKey = `brandHub_messaging_${brand}`;
  let tagline = "";
  try { tagline = JSON.parse(localStorage.getItem(messagingKey) ?? "{}").tagline ?? ""; } catch { /* ignore */ }

  return (
    <div style={{ display: "flex", flexDirection: "column" as const, gap: 24 }}>
      {/* Hero row */}
      <div style={{ display: "flex", alignItems: "center", gap: 20, padding: "24px 28px", borderRadius: 16,
        border: "1.5px solid var(--card-border)", background: "var(--card-bg)" }}>
        {logo ? (
          <div style={{ width: 72, height: 72, borderRadius: 14, overflow: "hidden", flexShrink: 0,
            background: "repeating-conic-gradient(#80808018 0% 25%, transparent 0% 50%) 0 0 / 12px 12px",
            display: "flex", alignItems: "center", justifyContent: "center" }}>
            <img src={logo} alt={meta.label} style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }} />
          </div>
        ) : (
          <div style={{ width: 72, height: 72, borderRadius: 14, flexShrink: 0, fontSize: 34,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: "linear-gradient(135deg,rgba(124,58,237,.12),rgba(99,102,241,.12))" }}>
            {meta.emoji}
          </div>
        )}
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 22, fontWeight: 900, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>{meta.label}</div>
          {tagline
            ? <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4, fontStyle: "italic" }}>"{tagline}"</div>
            : <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 4 }}>No tagline set — add one in Messaging</div>}
        </div>
      </div>

      {/* Colour palette strip */}
      {palette.length > 0 && (
        <div style={{ padding: "20px 24px", borderRadius: 16, border: "1.5px solid var(--card-border)", background: "var(--card-bg)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: ".08em",
            color: "var(--text-secondary)", marginBottom: 14 }}>Brand Colours</div>
          <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 10 }}>
            {palette.map((sw, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 28, height: 28, borderRadius: 8, background: sw.hex, border: "1.5px solid rgba(0,0,0,0.08)", flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.2 }}>{sw.name}</div>
                  <div style={{ fontSize: 9, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{sw.hex}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Voice traits */}
      {traits.length > 0 && (
        <div style={{ padding: "20px 24px", borderRadius: 16, border: "1.5px solid var(--card-border)", background: "var(--card-bg)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: ".08em",
            color: "var(--text-secondary)", marginBottom: 12 }}>Brand Voice Traits</div>
          <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
            {traits.map((t, i) => (
              <TraitChip key={i} label={t} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* Quick nav */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: ".08em",
          color: "var(--text-secondary)", marginBottom: 12 }}>Explore</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 10 }}>
          {QUICK_LINKS.map(link => (
            <button key={link.id} onClick={() => onNavigate?.(link.id)}
              style={{ display: "flex", flexDirection: "column" as const, alignItems: "center", justifyContent: "center",
                gap: 8, padding: "16px 12px", borderRadius: 14, border: "1.5px solid var(--card-border)",
                background: "var(--card-bg)", cursor: "pointer", fontFamily: "inherit", transition: "border-color 0.15s, box-shadow 0.15s" }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = "#7c3aed"; (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 4px 16px rgba(124,58,237,.12)"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--card-border)"; (e.currentTarget as HTMLButtonElement).style.boxShadow = "none"; }}>
              <span style={{ fontSize: 22 }}>{link.icon}</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>{link.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Messaging section ──────────────────────────────────────────
interface MessagingData { tagline: string; brandPromise: string; keyMessages: string[]; toneNotes: string; }
const MESSAGING_DEFAULT: MessagingData = { tagline: "", brandPromise: "", keyMessages: [""], toneNotes: "" };

function MessagingSection({ activeBrand }: { activeBrand?: string }) {
  const storageKey = `brandHub_messaging_${activeBrand ?? ""}`;
  const load = (): MessagingData => {
    try { return { ...MESSAGING_DEFAULT, ...JSON.parse(localStorage.getItem(storageKey) ?? "{}") }; } catch { return MESSAGING_DEFAULT; }
  };
  const [data,    setData]    = useState<MessagingData>(load);
  const [editing, setEditing] = useState(false);
  const [draft,   setDraft]   = useState<MessagingData>(load);

  useEffect(() => { const d = load(); setData(d); setDraft(d); }, [storageKey]);

  const save = () => {
    localStorage.setItem(storageKey, JSON.stringify(draft));
    setData(draft);
    setEditing(false);
  };
  const cancel = () => { setDraft(data); setEditing(false); };

  const addMsg  = () => setDraft(d => ({ ...d, keyMessages: [...d.keyMessages, ""] }));
  const delMsg  = (i: number) => setDraft(d => ({ ...d, keyMessages: d.keyMessages.filter((_, j) => j !== i) }));
  const editMsg = (i: number, v: string) => setDraft(d => ({ ...d, keyMessages: d.keyMessages.map((m, j) => j === i ? v : m) }));

  const isEmpty = !data.tagline && !data.brandPromise && !data.keyMessages.filter(Boolean).length && !data.toneNotes;

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "10px 14px", borderRadius: 10, border: "1.5px solid var(--card-border)",
    background: "var(--card-bg-soft)", color: "var(--text-primary)", fontFamily: "inherit",
    fontSize: 13, fontWeight: 600, outline: "none", boxSizing: "border-box",
  };
  const taStyle: React.CSSProperties = { ...inputStyle, fontWeight: 400, resize: "none", lineHeight: 1.6 };
  const label = (text: string) => (
    <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: ".07em", color: "var(--text-secondary)", marginBottom: 6 }}>{text}</div>
  );

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20 }}>
        {editing ? (
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={cancel} style={{ padding: "9px 18px", borderRadius: 10, border: "1.5px solid var(--card-border)", background: "transparent", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>Cancel</button>
            <button onClick={save}   style={{ padding: "9px 22px", borderRadius: 10, border: "none", background: "linear-gradient(135deg,#7c3aed,#6366f1)", color: "white", fontSize: 13, fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>Save</button>
          </div>
        ) : (
          <button onClick={() => { setDraft(data); setEditing(true); }}
            style={{ padding: "9px 20px", borderRadius: 10, border: "1.5px solid var(--card-border)", background: "transparent", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
            {isEmpty ? "+ Fill in Messaging" : "Edit"}
          </button>
        )}
      </div>

      {isEmpty && !editing && <ComingSoon title="Messaging" description="Define your brand tagline, promise, key messages and tone guidance used across all campaign briefs." />}

      {(!isEmpty || editing) && (
        <div style={{ display: "flex", flexDirection: "column" as const, gap: 24 }}>

          {/* Tagline */}
          <div style={{ padding: "20px 24px", borderRadius: 16, border: "1.5px solid var(--card-border)", background: "var(--card-bg)" }}>
            {label("Tagline")}
            {editing
              ? <input value={draft.tagline} onChange={e => setDraft(d => ({ ...d, tagline: e.target.value }))} placeholder="e.g. Built for what matters" style={inputStyle} />
              : <div style={{ fontSize: 20, fontWeight: 800, color: "var(--text-primary)", fontStyle: "italic" }}>
                  {data.tagline || <span style={{ color: "var(--text-tertiary)", fontSize: 14, fontStyle: "normal", fontWeight: 400 }}>Not set</span>}
                </div>}
          </div>

          {/* Brand promise */}
          <div style={{ padding: "20px 24px", borderRadius: 16, border: "1.5px solid var(--card-border)", background: "var(--card-bg)" }}>
            {label("Brand Promise")}
            {editing
              ? <textarea value={draft.brandPromise} onChange={e => setDraft(d => ({ ...d, brandPromise: e.target.value }))} rows={3} placeholder="The core promise your brand makes to its customers…" style={taStyle} />
              : <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.7, whiteSpace: "pre-wrap" as const }}>
                  {data.brandPromise || <span style={{ color: "var(--text-tertiary)" }}>Not set</span>}
                </div>}
          </div>

          {/* Key messages */}
          <div style={{ padding: "20px 24px", borderRadius: 16, border: "1.5px solid var(--card-border)", background: "var(--card-bg)" }}>
            {label("Key Messages")}
            <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
              {(editing ? draft.keyMessages : data.keyMessages.filter(Boolean)).map((msg, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#7c3aed", flexShrink: 0, marginTop: 6 }} />
                  {editing ? (
                    <>
                      <input value={msg} onChange={e => editMsg(i, e.target.value)} placeholder={`Key message ${i + 1}…`} style={{ ...inputStyle, flex: 1 }} />
                      {draft.keyMessages.length > 1 && (
                        <button onClick={() => delMsg(i)} style={{ background: "none", border: "none", color: "var(--text-tertiary)", cursor: "pointer", fontSize: 18, padding: "4px", lineHeight: 1 }}>×</button>
                      )}
                    </>
                  ) : (
                    <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.6 }}>{msg}</div>
                  )}
                </div>
              ))}
              {editing && (
                <button onClick={addMsg} style={{ alignSelf: "flex-start", background: "none", border: "none", color: "#7c3aed", fontSize: 13, fontWeight: 600, cursor: "pointer", padding: "4px 0", fontFamily: "inherit" }}>+ Add message</button>
              )}
            </div>
          </div>

          {/* Tone notes */}
          <div style={{ padding: "20px 24px", borderRadius: 16, border: "1.5px solid var(--card-border)", background: "var(--card-bg)" }}>
            {label("Tone & Style Notes")}
            {editing
              ? <textarea value={draft.toneNotes} onChange={e => setDraft(d => ({ ...d, toneNotes: e.target.value }))} rows={4} placeholder="Guidance on how to write for this brand — word choices, style rules, what to avoid…" style={taStyle} />
              : <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.7, whiteSpace: "pre-wrap" as const }}>
                  {data.toneNotes || <span style={{ color: "var(--text-tertiary)" }}>Not set</span>}
                </div>}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Legal & Compliance section ─────────────────────────────────
interface LegalData { disclaimer: string; usageRules: string; restrictedUses: string; approvalProcess: string; }
const LEGAL_DEFAULT: LegalData = { disclaimer: "", usageRules: "", restrictedUses: "", approvalProcess: "" };

function LegalSection({ activeBrand }: { activeBrand?: string }) {
  const storageKey = `brandHub_legal_${activeBrand ?? ""}`;
  const load = (): LegalData => {
    try { return { ...LEGAL_DEFAULT, ...JSON.parse(localStorage.getItem(storageKey) ?? "{}") }; } catch { return LEGAL_DEFAULT; }
  };
  const [data,    setData]    = useState<LegalData>(load);
  const [editing, setEditing] = useState(false);
  const [draft,   setDraft]   = useState<LegalData>(load);

  useEffect(() => { const d = load(); setData(d); setDraft(d); }, [storageKey]);

  const save = () => { localStorage.setItem(storageKey, JSON.stringify(draft)); setData(draft); setEditing(false); };
  const cancel = () => { setDraft(data); setEditing(false); };
  const isEmpty = !data.disclaimer && !data.usageRules && !data.restrictedUses && !data.approvalProcess;

  const taStyle: React.CSSProperties = {
    width: "100%", padding: "10px 14px", borderRadius: 10, border: "1.5px solid var(--card-border)",
    background: "var(--card-bg-soft)", color: "var(--text-primary)", fontFamily: "inherit",
    fontSize: 13, lineHeight: 1.6, outline: "none", boxSizing: "border-box", resize: "none",
  };
  const label = (text: string, sub?: string) => (
    <div style={{ marginBottom: 8 }}>
      <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: ".07em", color: "var(--text-secondary)" }}>{text}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{sub}</div>}
    </div>
  );

  const Field = ({ lbl, sub, field, rows }: { lbl: string; sub?: string; field: keyof LegalData; rows: number }) => (
    <div style={{ padding: "20px 24px", borderRadius: 16, border: "1.5px solid var(--card-border)", background: "var(--card-bg)" }}>
      {label(lbl, sub)}
      {editing
        ? <textarea value={draft[field]} onChange={e => setDraft(d => ({ ...d, [field]: e.target.value }))} rows={rows} style={taStyle} />
        : <div style={{ fontSize: 13, color: data[field] ? "var(--text-primary)" : "var(--text-tertiary)", lineHeight: 1.7, whiteSpace: "pre-wrap" as const }}>
            {data[field] || "Not set"}
          </div>}
    </div>
  );

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20 }}>
        {editing ? (
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={cancel} style={{ padding: "9px 18px", borderRadius: 10, border: "1.5px solid var(--card-border)", background: "transparent", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>Cancel</button>
            <button onClick={save}   style={{ padding: "9px 22px", borderRadius: 10, border: "none", background: "linear-gradient(135deg,#7c3aed,#6366f1)", color: "white", fontSize: 13, fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>Save</button>
          </div>
        ) : (
          <button onClick={() => { setDraft(data); setEditing(true); }}
            style={{ padding: "9px 20px", borderRadius: 10, border: "1.5px solid var(--card-border)", background: "transparent", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
            {isEmpty ? "+ Add Legal Content" : "Edit"}
          </button>
        )}
      </div>

      {isEmpty && !editing && <ComingSoon title="Legal & Compliance" description="Document brand usage rules, standard disclaimers, restricted uses and the approval process for this brand." />}

      {(!isEmpty || editing) && (
        <div style={{ display: "flex", flexDirection: "column" as const, gap: 16 }}>
          <Field lbl="Standard Disclaimer" sub="Used in campaigns, ads and external communications" field="disclaimer" rows={4} />
          <Field lbl="Usage Rules" sub="How the brand should and should not be represented" field="usageRules" rows={4} />
          <Field lbl="Restricted Uses" sub="What is explicitly prohibited or requires approval" field="restrictedUses" rows={3} />
          <Field lbl="Approval Process" sub="Steps required before publishing brand content" field="approvalProcess" rows={3} />
        </div>
      )}
    </div>
  );
}

// ── Campaign History section ───────────────────────────────────
interface HistoricalCampaign {
  brand: string; product_category: string; market: string; season: string;
  channels: string[]; reach: number; ctr_pct: number; roas: number;
  engagement_pct: number; budget_gbp: number; notes: string;
}
interface MachineBrief {
  campaign_id: string; campaign_name: string; brand: string; market: string;
  product_category: string; season: string; channels: string; moment_type: string;
  validation_score: number; validation_status: string; fan_truth_score: number;
  fan_truth_verdict: string; flag_count: number; created_at: string;
}
interface CampaignHistoryData {
  historical: HistoricalCampaign[]; briefs: MachineBrief[];
  historical_error?: string; briefs_error?: string;
}

function CampaignHistorySection({ activeBrand, onLaunchCampaign, onViewCampaign }: {
  activeBrand?: string;
  onLaunchCampaign?: (brief: Record<string, unknown>) => void;
  onViewCampaign?: (campaignId: string) => void;
}) {
  const [data,      setData]      = useState<CampaignHistoryData | null>(null);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState("");
  const [tab,       setTab]       = useState<"historical" | "briefs">("briefs");
  const [launching, setLaunching] = useState<string | null>(null);

  useEffect(() => {
    if (!activeBrand) return;
    setLoading(true); setError(""); setData(null);
    fetch(`${API_BASE}/brands/${encodeURIComponent(activeBrand)}/campaign-history`)
      .then(r => r.ok ? r.json() : r.json().then((e: { detail?: string }) => { throw new Error(e.detail ?? `HTTP ${r.status}`); }))
      .then(d => setData(d))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [activeBrand]);

  const handleRunCampaign = async (campaignId: string, fallback: MachineBrief) => {
    if (!onLaunchCampaign) return;
    setLaunching(campaignId);
    try {
      const res = await fetch(`${API_BASE}/campaign/${encodeURIComponent(campaignId)}/brief`);
      const row = res.ok ? await res.json() : null;
      const parsed = row?.brief_parsed ?? {};
      const channels = row?.channels
        ? String(row.channels).split(",").map((c: string) => c.trim()).filter(Boolean)
        : [];
      const brief: Record<string, unknown> = {
        campaign_name:    row?.campaign_name   ?? fallback.campaign_name ?? "Untitled Campaign",
        brand:            row?.brand           ?? fallback.brand         ?? activeBrand ?? "",
        market:           row?.market          ?? fallback.market        ?? "",
        product_category: row?.product_category ?? fallback.product_category ?? "",
        product:          parsed.product       ?? row?.product_category  ?? "",
        season:           row?.season          ?? fallback.season        ?? "",
        channels,
        moment_type:      row?.moment_type     ?? fallback.moment_type   ?? "",
        goal:             parsed.goal          ?? "",
        fan_truth:        parsed.fan_truth     ?? "",
        audience:         parsed.audience ?? {
          segment: "", location: row?.market ?? "", age_range: "", gender: "",
        },
        tone:   parsed.tone   ?? "",
        budget: parsed.budget ?? "",
        kpis:   parsed.kpis   ?? "",
      };
      onLaunchCampaign(brief);
    } catch {
      onLaunchCampaign({
        campaign_name: fallback.campaign_name ?? "Untitled Campaign",
        brand: fallback.brand ?? activeBrand ?? "",
        market: fallback.market ?? "", product_category: fallback.product_category ?? "",
        season: fallback.season ?? "", channels: [],
        moment_type: fallback.moment_type ?? "",
        goal: "", fan_truth: "", tone: "", budget: "", kpis: "",
        audience: { segment: "", location: "", age_range: "", gender: "" },
      });
    } finally {
      setLaunching(null);
    }
  };

  const fmt = (n: number | null | undefined, decimals = 1) =>
    n == null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

  const statusColor = (s: string) =>
    s === "approved" ? "#10b981" : s === "flagged" ? "#ef4444" : s === "needs_review" ? "#f59e0b" : "#6366f1";

  const Tab = ({ id, label, count }: { id: "historical" | "briefs"; label: string; count: number }) => (
    <button onClick={() => setTab(id)}
      style={{ padding: "8px 18px", borderRadius: 10, cursor: "pointer",
        fontFamily: "inherit", fontSize: 13, fontWeight: tab === id ? 700 : 500,
        background: tab === id ? "linear-gradient(135deg,#7c3aed,#6366f1)" : "var(--card-bg)",
        color: tab === id ? "white" : "var(--text-secondary)",
        border: tab === id ? "none" : "1.5px solid var(--card-border)" }}>
      {label} {count > 0 && <span style={{ opacity: 0.75, fontSize: 11 }}>({count})</span>}
    </button>
  );

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "60px 0", gap: 12, color: "var(--text-secondary)" }}>
      <div style={{ width: 20, height: 20, border: "2.5px solid var(--card-border)", borderTopColor: "#7c3aed", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
      Loading campaign history…
    </div>
  );

  if (error) return (
    <div style={{ padding: "32px 24px", borderRadius: 16, border: "1.5px solid #ef444430", background: "rgba(239,68,68,0.06)", textAlign: "center" }}>
      <div style={{ fontSize: 28, marginBottom: 10 }}>⚠</div>
      <div style={{ fontSize: 14, fontWeight: 700, color: "#ef4444", marginBottom: 6 }}>Could not load campaign history</div>
      <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{error}</div>
    </div>
  );

  if (!data) return <ComingSoon title="Campaign History" description="Historical campaigns and generated briefs for this brand will appear here once BigQuery is connected." />;

  const historical = data.historical ?? [];
  const briefs     = data.briefs ?? [];
  const noData     = historical.length === 0 && briefs.length === 0;

  if (noData) return <ComingSoon title="Campaign History" description={`No campaign records found for ${activeBrand ?? "this brand"} in BigQuery yet.`} />;

  return (
    <div>
      <div style={{ display: "flex", gap: 10, marginBottom: 24 }}>
        <Tab id="briefs"     label="Generated Briefs"      count={briefs.length} />
        <Tab id="historical" label="Historical Campaigns"  count={historical.length} />
      </div>

      {/* Generated Briefs tab */}
      {tab === "briefs" && (
        briefs.length === 0
          ? <ComingSoon title="Generated Briefs" description={data.briefs_error ? `BigQuery error: ${data.briefs_error}` : "No generated briefs found for this brand yet. Run a campaign brief to get started."} />
          : <div style={{ display: "flex", flexDirection: "column" as const, gap: 12 }}>
              {briefs.map(b => {
                const isLaunching = launching === b.campaign_id;
                const canView = !!onViewCampaign;
                return (
                  <div
                    key={b.campaign_id}
                    onClick={canView ? () => onViewCampaign(b.campaign_id) : undefined}
                    style={{
                      padding: "18px 22px", borderRadius: 14,
                      border: "1.5px solid var(--card-border)", background: "var(--card-bg)",
                      cursor: canView ? "pointer" : "default",
                      transition: "box-shadow 0.15s, border-color 0.15s",
                    }}
                    onMouseEnter={canView ? e => {
                      (e.currentTarget as HTMLDivElement).style.boxShadow = "0 4px 20px rgba(124,58,237,0.12)";
                      (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(124,58,237,0.35)";
                    } : undefined}
                    onMouseLeave={canView ? e => {
                      (e.currentTarget as HTMLDivElement).style.boxShadow = "";
                      (e.currentTarget as HTMLDivElement).style.borderColor = "";
                    } : undefined}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 10 }}>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)", marginBottom: 3 }}>
                          {b.campaign_name || b.campaign_id}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                          {b.market} · {b.product_category} · {b.season}
                          {b.created_at && ` · ${new Date(b.created_at).toLocaleDateString("en-GB", { day:"numeric", month:"short", year:"numeric" })}`}
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                        <span style={{ padding: "3px 10px", borderRadius: 99, fontSize: 10, fontWeight: 700,
                          background: `${statusColor(b.validation_status)}18`, color: statusColor(b.validation_status) }}>
                          {b.validation_status?.replace(/_/g, " ") ?? "unknown"}
                        </span>
                        {onLaunchCampaign && (
                          <button
                            onClick={e => { e.stopPropagation(); handleRunCampaign(b.campaign_id, b); }}
                            disabled={isLaunching}
                            title="Re-run the full pipeline with this brief"
                            style={{
                              display: "flex", alignItems: "center", gap: 5,
                              padding: "4px 10px", borderRadius: 8, fontSize: 11, fontWeight: 700,
                              border: "1px solid rgba(124,58,237,0.30)",
                              cursor: isLaunching ? "default" : "pointer",
                              fontFamily: "inherit",
                              background: isLaunching ? "var(--card-bg-soft)" : "rgba(124,58,237,0.08)",
                              color: isLaunching ? "var(--text-tertiary)" : "#7c3aed",
                              opacity: isLaunching ? 0.7 : 1,
                              transition: "background 0.15s",
                            }}
                          >
                            {isLaunching ? (
                              <>
                                <div style={{ width: 10, height: 10, border: "2px solid currentColor",
                                  borderTopColor: "transparent", borderRadius: "50%",
                                  animation: "spin 0.7s linear infinite" }} />
                                Launching…
                              </>
                            ) : <>&#9654; Re-run</>}
                          </button>
                        )}
                        {canView && (
                          <div style={{ fontSize: 11, color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 4 }}>
                            View results →
                          </div>
                        )}
                      </div>
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 10 }}>
                      {b.channels && <Chip label={`📺 ${b.channels}`} />}
                      {b.moment_type && <Chip label={`⚡ ${b.moment_type}`} />}
                      {b.validation_score != null && <Chip label={`✅ Score ${fmt(b.validation_score * 100, 0)}%`} />}
                      {b.fan_truth_score != null && <Chip label={`🎯 Fan truth ${fmt(b.fan_truth_score * 100, 0)}%`} />}
                      {b.flag_count != null && b.flag_count > 0 && <Chip label={`🚩 ${b.flag_count} flag${b.flag_count > 1 ? "s" : ""}`} red />}
                    </div>
                  </div>
                );
              })}
            </div>
      )}

      {/* Historical campaigns tab */}
      {tab === "historical" && (
        historical.length === 0
          ? <ComingSoon title="Historical Campaigns" description={data.historical_error ? `BigQuery error: ${data.historical_error}` : "No historical campaign benchmarks found for this brand yet."} />
          : <div style={{ display: "flex", flexDirection: "column" as const, gap: 12 }}>
              {historical.map((c, i) => (
                <div key={i} style={{ padding: "18px 22px", borderRadius: 14,
                  border: "1.5px solid var(--card-border)", background: "var(--card-bg)" }}>
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 13, fontWeight: 800, color: "var(--text-primary)", marginBottom: 3 }}>
                      {c.product_category} — {c.market}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                      {c.season}
                      {Array.isArray(c.channels) && c.channels.length > 0 && ` · ${c.channels.join(", ")}`}
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(110px, 1fr))", gap: 8, marginBottom: c.notes ? 12 : 0 }}>
                    <MetricTile label="ROAS"       value={c.roas != null ? `${fmt(c.roas)}×` : "—"} />
                    <MetricTile label="CTR"        value={c.ctr_pct != null ? `${fmt(c.ctr_pct)}%` : "—"} />
                    <MetricTile label="Engagement" value={c.engagement_pct != null ? `${fmt(c.engagement_pct)}%` : "—"} />
                    <MetricTile label="Reach"      value={c.reach != null ? c.reach.toLocaleString() : "—"} />
                    <MetricTile label="Budget"     value={c.budget_gbp != null ? `£${Math.round(c.budget_gbp).toLocaleString()}` : "—"} />
                  </div>
                  {c.notes && <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6, paddingTop: 10,
                    borderTop: "1px solid var(--card-border)" }}>{c.notes}</div>}
                </div>
              ))}
            </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function Chip({ label, red }: { label: string; red?: boolean }) {
  return (
    <span style={{ fontSize: 11, padding: "3px 9px", borderRadius: 99, fontWeight: 600,
      background: red ? "rgba(239,68,68,0.10)" : "var(--card-bg-soft)",
      color: red ? "#ef4444" : "var(--text-secondary)" }}>
      {label}
    </span>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ padding: "10px 12px", borderRadius: 10, background: "var(--card-bg-soft)",
      border: "1px solid var(--card-border)" }}>
      <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase" as const,
        letterSpacing: ".06em", color: "var(--text-tertiary)", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)", fontVariantNumeric: "tabular-nums" }}>{value}</div>
    </div>
  );
}

// ── Market Research section ────────────────────────────────────
interface MarketResearchData {
  marketSize: string;
  targetAudience: string;
  keyTrends: string;
  opportunities: string;
  threats: string;
  notes: string;
}
const MR_DEFAULT: MarketResearchData = { marketSize: "", targetAudience: "", keyTrends: "", opportunities: "", threats: "", notes: "" };

function MarketResearchSection({ activeBrand }: { activeBrand?: string }) {
  const brand = activeBrand ?? "";
  const storageKey = `brandHub_marketResearch_${brand}`;

  const load = (): MarketResearchData => {
    try { return { ...MR_DEFAULT, ...JSON.parse(localStorage.getItem(storageKey) ?? "{}") }; }
    catch { return MR_DEFAULT; }
  };

  const [data,    setData]    = useState<MarketResearchData>(load);
  const [editing, setEditing] = useState(false);
  const [draft,   setDraft]   = useState<MarketResearchData>(load);
  const [assets,  setAssets]  = useState<{ name: string; url: string }[]>([]);

  useEffect(() => { const d = load(); setData(d); setDraft(d); }, [storageKey]);

  useEffect(() => {
    if (!brand) return;
    const folder = brand === "UBS Bank" ? "UBS" : brand;
    fetch(`${API_BASE}/brands/${encodeURIComponent(folder)}/list-products`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.products) setAssets(d.products.map((p: any) => ({ ...p, url: API_BASE + p.url }))); })
      .catch(() => {});
  }, [brand]);

  const save   = () => { localStorage.setItem(storageKey, JSON.stringify(draft)); setData(draft); setEditing(false); };
  const cancel = () => { setDraft(data); setEditing(false); };
  const isEmpty = Object.values(data).every(v => !v);

  const taStyle: React.CSSProperties = {
    width: "100%", padding: "10px 14px", borderRadius: 10, border: "1.5px solid var(--card-border)",
    background: "var(--card-bg-soft)", color: "var(--text-primary)", fontFamily: "inherit",
    fontSize: 13, lineHeight: 1.6, outline: "none", boxSizing: "border-box", resize: "none",
  };

  const Card = ({ lbl, icon, field, rows = 3 }: { lbl: string; icon: string; field: keyof MarketResearchData; rows?: number }) => (
    <div style={{ padding: "18px 22px", borderRadius: 14, border: "1.5px solid var(--card-border)", background: "var(--card-bg)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <span style={{ fontSize: 16 }}>{icon}</span>
        <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: ".07em", color: "var(--text-secondary)" }}>{lbl}</span>
      </div>
      {editing
        ? <textarea value={draft[field]} onChange={e => setDraft(d => ({ ...d, [field]: e.target.value }))} rows={rows} style={taStyle} />
        : <div style={{ fontSize: 13, color: data[field] ? "var(--text-primary)" : "var(--text-tertiary)", lineHeight: 1.7, whiteSpace: "pre-wrap" as const }}>
            {data[field] || "Not set"}
          </div>}
    </div>
  );

  return (
    <div>
      {/* Edit toolbar */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20 }}>
        {editing ? (
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={cancel} style={{ padding: "9px 18px", borderRadius: 10, border: "1.5px solid var(--card-border)", background: "transparent", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>Cancel</button>
            <button onClick={save}   style={{ padding: "9px 22px", borderRadius: 10, border: "none", background: "linear-gradient(135deg,#7c3aed,#6366f1)", color: "white", fontSize: 13, fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>Save</button>
          </div>
        ) : (
          <button onClick={() => { setDraft(data); setEditing(true); }}
            style={{ padding: "9px 20px", borderRadius: 10, border: "1.5px solid var(--card-border)", background: "transparent", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
            {isEmpty ? "+ Add Research" : "Edit"}
          </button>
        )}
      </div>

      {/* Intel cards — always visible when not empty, or when editing */}
      {(!isEmpty || editing) && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(290px, 1fr))", gap: 14, marginBottom: 28 }}>
          <Card lbl="Market Size & Value"    icon="📊" field="marketSize"     rows={3} />
          <Card lbl="Target Audience"        icon="🎯" field="targetAudience" rows={3} />
          <Card lbl="Key Trends"             icon="📈" field="keyTrends"      rows={3} />
          <Card lbl="Opportunities"          icon="💡" field="opportunities"  rows={3} />
          <Card lbl="Threats & Risks"        icon="⚠"  field="threats"        rows={3} />
          <Card lbl="Additional Notes"       icon="📝" field="notes"          rows={3} />
        </div>
      )}

      {isEmpty && !editing && (
        <div style={{ marginBottom: 28 }}>
          <ComingSoon title="Market Research" description="Document market size, audience insights, key trends, opportunities and threats for this brand." />
        </div>
      )}

      {/* Campaign visuals from Assets/ */}
      {assets.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: ".08em", color: "var(--text-secondary)", marginBottom: 14 }}>
            Campaign Visuals
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 10 }}>
            {assets.map((a, i) => (
              <div key={i} style={{ borderRadius: 10, overflow: "hidden", border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)", aspectRatio: "16/9" }}>
                <img src={a.url} alt={a.name}
                  onError={e => { (e.currentTarget.parentElement as HTMLElement).style.display = "none"; }}
                  style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Shared placeholder for sections not yet built ──────────────
function ComingSoon({ title, description }: { title: string; description: string }) {
  return (
    <div style={{ padding: "32px 0" }}>
      <div style={{ borderRadius: 16, border: "1.5px dashed var(--card-border)",
        background: "var(--card-bg)", padding: "48px 32px", textAlign: "center" as const }}>
        <div style={{ fontSize: 36, marginBottom: 14 }}>🚧</div>
        <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>
          {title} — Coming Soon
        </div>
        <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6,
          maxWidth: 380, margin: "0 auto" }}>
          {description}
        </div>
      </div>
    </div>
  );
}

// ── Brand Guidelines — upload section ──────────────────────────

const CHUNK_SIZE = 10 * 1024 * 1024; // 10 MB — stays under Cloud Run's 32 MB limit

function GuidelinesSection({ onAssetsUploaded, activeBrand: propBrand }: {
  onAssetsUploaded?: (c: Record<string,number>) => void;
  activeBrand?: string;
}) {
  const [brandName, setBrandName]   = useState(() => propBrand || localStorage.getItem("brandHub_activeBrand") || "");
  const [file, setFile]             = useState<File | null>(null);
  const [dragging, setDragging]     = useState(false);
  const [status, setStatus]         = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [, setUploaded]             = useState<Record<string, number>>({});
  const [, setSkipped]              = useState<string[]>([]);
  const [errorMsg, setErrorMsg]     = useState("");
  const [progress, setProgress]     = useState(0);
  const [progressLabel, setProgressLabel] = useState("");
  const [brands, setBrands]         = useState<string[]>([]);
  const [loadingBrand, setLoadingBrand] = useState(false);
  const fileRef                     = useRef<HTMLInputElement>(null);

  // Fetch existing brands on mount + restore last active brand from localStorage
  useEffect(() => {
    fetch(`${API_BASE}/brands`)
      .then(r => r.json())
      .then(d => {
        const list: string[] = d.brands ?? [];
        setBrands(list);
        // Auto-load the last active brand so sidebar counts persist across reloads
        const last = localStorage.getItem("brandHub_activeBrand");
        if (last && list.includes(last)) {
          setBrandName(last);
          loadBrandAssets(last);
        }
      })
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadBrandAssets = async (name: string) => {
    if (!name) return;
    setLoadingBrand(true);
    try {
      const res = await fetch(`${API_BASE}/brands/${encodeURIComponent(name)}/assets`);
      const data = await res.json();
      const counts: Record<string, number> = data.assets ?? {};
      setUploaded(counts);
      setSkipped([]);
      setStatus("done");
      localStorage.setItem("brandHub_activeBrand", name);
      localStorage.setItem("brandHub_assetCounts", JSON.stringify(counts));
      onAssetsUploaded?.(counts);
    } catch {
      // ignore
    } finally {
      setLoadingBrand(false);
    }
  };

  const handleUpload = async () => {
    if (!brandName.trim() || !file) return;
    setStatus("uploading"); setProgress(0); setProgressLabel("Preparing upload…");
    setErrorMsg(""); setUploaded({}); setSkipped([]);

    const brand = encodeURIComponent(brandName.trim());
    const sessionId = crypto.randomUUID();
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

    try {
      // Upload chunks
      for (let i = 0; i < totalChunks; i++) {
        const slice = file.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE);
        const fd = new FormData();
        fd.append("file", slice, "chunk");
        fd.append("session_id", sessionId);
        fd.append("chunk_index", String(i));
        fd.append("total_chunks", String(totalChunks));
        setProgressLabel(`Uploading part ${i + 1} of ${totalChunks}…`);
        const res = await fetch(`${API_BASE}/brands/${brand}/upload-chunk`, { method: "POST", body: fd });
        if (!res.ok) {
          const d = await res.json().catch(() => ({}));
          throw new Error((d as any)?.detail || `Chunk ${i + 1} failed (${res.status})`);
        }
        setProgress(Math.round(((i + 1) / totalChunks) * 80));
      }

      // Finalise
      setProgressLabel("Indexing brand assets…");
      setProgress(85);
      const res = await fetch(`${API_BASE}/brands/${brand}/finalize-upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, total_chunks: totalChunks }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error((data as any)?.detail || `Finalise failed (${res.status})`);

      setProgress(100);
      // Normalise PascalCase → lowercase; "font" → "fonts"
      const raw: Record<string, number> = data.uploaded ?? {};
      const normalized: Record<string, number> = {};
      Object.entries(raw).forEach(([k, v]) => {
        const key = k.toLowerCase() === "font" ? "fonts" : k.toLowerCase();
        normalized[key] = (normalized[key] ?? 0) + Number(v);
      });
      setUploaded(normalized); setSkipped(data.skipped ?? []); setStatus("done");
      localStorage.setItem("brandHub_activeBrand", brandName.trim());
      localStorage.setItem("brandHub_assetCounts", JSON.stringify(normalized));
      onAssetsUploaded?.(normalized);
    } catch (e) { setErrorMsg(e instanceof Error ? e.message : String(e)); setStatus("error"); }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && f.name.endsWith(".zip")) setFile(f);
  };

  return (
    <div style={{ width: "100%" }}>
      <div style={{ padding: 24, borderRadius: 16,
        background: "var(--card-bg)", border: "1px solid var(--card-border)",
        boxShadow: "var(--shadow-sm)", marginBottom: 20 }}>

        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)",
          marginBottom: 4, display: "flex", alignItems: "center", gap: 8 }}>
          <span>📁</span> Upload Brand Package (.zip)
        </div>
        <p style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.6,
          marginBottom: 14 }}>
          Create a <strong>.zip</strong> file containing these subfolders:
          {" "}<code style={{ fontSize: 10, background: "var(--card-bg-soft)",
            padding: "1px 5px", borderRadius: 4 }}>Guidelines/</code>
          {" "}<code style={{ fontSize: 10, background: "var(--card-bg-soft)",
            padding: "1px 5px", borderRadius: 4 }}>Logos/</code>
          {" "}<code style={{ fontSize: 10, background: "var(--card-bg-soft)",
            padding: "1px 5px", borderRadius: 4 }}>Font/</code>
          {" "}<code style={{ fontSize: 10, background: "var(--card-bg-soft)",
            padding: "1px 5px", borderRadius: 4 }}>Colours/</code>
          {" "}<code style={{ fontSize: 10, background: "var(--card-bg-soft)",
            padding: "1px 5px", borderRadius: 4 }}>Assets/</code>
        </p>

        {/* Existing brands — load without re-uploading */}
        {brands.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)",
              marginBottom: 6 }}>Select existing brand</div>
            <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 6 }}>
              {brands.map(b => (
                <button key={b} onClick={() => { setBrandName(b); loadBrandAssets(b); }}
                  disabled={loadingBrand}
                  style={{ padding: "5px 14px", borderRadius: 99, fontSize: 12, fontWeight: 600,
                    cursor: "pointer", border: "1.5px solid var(--card-border)",
                    background: brandName === b ? "rgba(124,58,237,0.12)" : "var(--card-bg-soft)",
                    color: brandName === b ? "#7c3aed" : "var(--text-secondary)",
                    borderColor: brandName === b ? "#7c3aed" : "var(--card-border)" }}>
                  {loadingBrand && brandName === b ? "Loading…" : b}
                </button>
              ))}
            </div>
            <div style={{ height: 1, background: "var(--card-border)", margin: "14px 0 12px",
              display: "flex", alignItems: "center" }}>
              <span style={{ fontSize: 10, color: "var(--text-secondary)",
                background: "var(--card-bg)", padding: "0 8px" }}>or upload new</span>
            </div>
          </div>
        )}

        <input value={brandName} onChange={e => setBrandName(e.target.value)}
          placeholder="Brand name (e.g. Acme Corp)"
          style={{ width: "100%", padding: "10px 14px", borderRadius: 10, fontSize: 13,
            border: "1.5px solid var(--card-border)", background: "var(--page-bg)",
            color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
            boxSizing: "border-box" as const, marginBottom: 12 }}
          onFocus={e => (e.currentTarget.style.borderColor = "#7c3aed")}
          onBlur={e => (e.currentTarget.style.borderColor = "var(--card-border)")} />

        <div onClick={() => fileRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          style={{ padding: "28px 20px", borderRadius: 12, cursor: "pointer",
            border: `2px dashed ${dragging ? "#7c3aed" : "var(--card-border)"}`,
            background: dragging ? "rgba(124,58,237,0.06)" : "var(--card-bg-soft)",
            textAlign: "center" as const, transition: "all 0.15s", marginBottom: 14 }}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>⬆️</div>
          <div style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 600, marginBottom: 4 }}>
            {file ? file.name : "Drag & drop or browse"}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
            Only <strong>.zip</strong> files accepted
          </div>
          <input ref={fileRef} type="file" accept=".zip"
            style={{ display: "none" }} onChange={e => setFile(e.target.files?.[0] ?? null)} />
        </div>

        <button onClick={handleUpload}
          disabled={!brandName.trim() || !file || status === "uploading"}
          style={{ padding: "10px 24px", borderRadius: 10, border: "none",
            fontFamily: "inherit", fontSize: 13, fontWeight: 700, color: "white",
            cursor: !brandName.trim() || !file || status === "uploading" ? "not-allowed" : "pointer",
            opacity: !brandName.trim() || !file ? 0.4 : 1,
            background: "linear-gradient(135deg,#7c3aed,#6366f1)" }}>
          {status === "uploading" ? "Uploading…" : "Upload & index"}
        </button>

        {status === "uploading" && (
          <div style={{ marginTop: 12 }}>
            <div style={{ height: 4, borderRadius: 4, background: "var(--card-border)", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${progress}%`, borderRadius: 4,
                background: "linear-gradient(90deg,#7c3aed,#6366f1)", transition: "width 0.3s ease" }} />
            </div>
            <div style={{ fontSize: 11, color: "#7c3aed", marginTop: 5, fontWeight: 600 }}>{progressLabel}</div>
          </div>
        )}

        {status === "error" && (
          <div style={{ marginTop: 12, fontSize: 12, color: "#ef4444" }}>⚠ {errorMsg}</div>
        )}
      </div>

      {/* After upload/load: show compact brand status — full breakdown is in the sidebar */}
      {status === "done" && (
        <div style={{ padding: "16px 20px", borderRadius: 14,
          background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.25)",
          display: "flex", alignItems: "center", gap: 12 }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="rgba(16,185,129,0.2)" stroke="#10b981" strokeWidth="1.5"/>
            <path d="M8 12l3 3 5-5" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
              {brandName} — brand knowledge is up to date
            </div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>
              Asset breakdown visible in the sidebar under Brand Guidelines
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Section content map ────────────────────────────────────────
const SECTION_META: Record<BrandHubSection, { title: string; subtitle: string }> = {
  overview:           { title: "Overview",             subtitle: "Brand summary and key information" },
  logos:              { title: "Logos",                subtitle: "Brand logo files and usage guidelines" },
  fonts:              { title: "Fonts",                subtitle: "Typography and font family specifications" },
  "brand-assets":     { title: "Brand Assets",         subtitle: "Upload and manage brand knowledge and assets" },
  "brand-voice":      { title: "Brand Voice",          subtitle: "Tone of voice, messaging pillars and personality" },
  "visual-identity":  { title: "Visual Identity",      subtitle: "Colour palette, typography and design tokens" },
  products:           { title: "Products & Services",  subtitle: "Product catalogue, descriptions and imagery" },
  competitors:        { title: "Competitors",          subtitle: "Competitive landscape and positioning analysis" },
  personas:           { title: "Customer Personas",    subtitle: "Target audience profiles and segmentation" },
  messaging:          { title: "Messaging",            subtitle: "Key messages, taglines and campaign narratives" },
  legal:              { title: "Legal & Compliance",   subtitle: "Brand usage rules, disclaimers and compliance notes" },
  "campaign-history": { title: "Campaign History",     subtitle: "Past campaigns, performance and learnings" },
  "market-research":  { title: "Market Research",      subtitle: "Market insights, trends and consumer data" },
  documents:          { title: "Documents",            subtitle: "Brand documents, briefs and reference materials" },
};

// ── Main BrandHub component ────────────────────────────────────
interface BrandHubProps {
  section?: BrandHubSection;
  activeBrand?: string;
  onAssetsUploaded?: (counts: Record<string, number>) => void;
  onNavigate?: (s: BrandHubSection) => void;
  onLaunchCampaign?: (brief: Record<string, unknown>) => void;
  onViewCampaign?: (campaignId: string) => void;
}

export default function BrandHub({ section = "overview", activeBrand, onAssetsUploaded, onNavigate, onLaunchCampaign, onViewCampaign }: BrandHubProps) {
  const meta = SECTION_META[section] ?? SECTION_META["overview"];

  const renderSection = () => {
    switch (section) {
      case "overview":         return <OverviewSection activeBrand={activeBrand} onNavigate={onNavigate} />;
      case "logos":            return <LogosSection activeBrand={activeBrand} />;
      case "fonts":            return <FontsSection activeBrand={activeBrand} />;
      case "visual-identity":  return <VisualIdentitySection activeBrand={activeBrand} />;
      case "products":         return <ProductsSection activeBrand={activeBrand} />;
      case "documents":        return <DocumentsSection activeBrand={activeBrand} />;
      case "brand-assets":
        return <GuidelinesSection key={activeBrand} onAssetsUploaded={onAssetsUploaded} activeBrand={activeBrand} />;
      case "brand-voice":
        return <VoiceSection activeBrand={activeBrand} />;
      case "competitors":      return <CompetitorsSection activeBrand={activeBrand} />;
      case "personas":         return <PersonasSection activeBrand={activeBrand} />;
      case "messaging":         return <MessagingSection activeBrand={activeBrand} />;
      case "legal":             return <LegalSection activeBrand={activeBrand} />;
      case "campaign-history":  return <CampaignHistorySection activeBrand={activeBrand} onLaunchCampaign={onLaunchCampaign} onViewCampaign={onViewCampaign} />;
      case "market-research":   return <MarketResearchSection activeBrand={activeBrand} />;
      default:
        return <ComingSoon title={meta.title} description={`${meta.subtitle}. Coming soon.`} />;
    }
  };

  return (
    <div style={{ flex: 1, overflowY: "auto" as const }}>
      {/* minHeight:100% + flex column center = centered when short, scrollable when tall */}
      <div style={{ minHeight: "100%", display: "flex", flexDirection: "column" as const,
        alignItems: "center", justifyContent: "center", padding: "40px 32px" }}>
        <div style={{ width: "100%", maxWidth: 680 }}>

          {/* Page header */}
          <div style={{ marginBottom: 28 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10,
                background: "linear-gradient(135deg,#7c3aed,#6366f1)",
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white"
                  strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                </svg>
              </div>
              <div>
                <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800,
                  color: "var(--text-primary)", letterSpacing: "-0.02em" }}>{meta.title}</h1>
                <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>{meta.subtitle}</p>
              </div>
            </div>
          </div>

          {/* Section content */}
          {renderSection()}
        </div>
      </div>
    </div>
  );
}
