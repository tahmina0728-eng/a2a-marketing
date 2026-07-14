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

function VoiceSection() {
  const [voices, setVoices] = useState<BrandVoice[]>(() => {
    try {
      const stored = localStorage.getItem(VOICE_STORAGE_KEY);
      return stored ? JSON.parse(stored) : DEFAULT_VOICES;
    } catch { return DEFAULT_VOICES; }
  });
  const [editing, setEditing] = useState<BrandVoice | null>(null);
  const [isNew, setIsNew] = useState(false);

  const persist = (updated: BrandVoice[]) => {
    setVoices(updated);
    localStorage.setItem(VOICE_STORAGE_KEY, JSON.stringify(updated));
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

// ── Shared placeholder for sections not yet built ──────────────
function ComingSoon({ title, description }: { title: string; description: string }) {
  return (
    <div style={{ textAlign: "center" as const, padding: "60px 24px" }}>
      <div style={{ fontSize: 40, marginBottom: 16 }}>🚧</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>
        {title}
      </div>
      <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6, maxWidth: 360, margin: "0 auto" }}>
        {description}
      </div>
    </div>
  );
}

// ── Brand Guidelines — upload section ──────────────────────────

const CHUNK_SIZE = 10 * 1024 * 1024; // 10 MB — stays under Cloud Run's 32 MB limit

function GuidelinesSection({ onAssetsUploaded }: { onAssetsUploaded?: (c: Record<string,number>) => void }) {
  const [brandName, setBrandName]   = useState("");
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
    <div style={{ maxWidth: 520, width: "100%" }}>
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
  guidelines:       { title: "Brand Guidelines",    subtitle: "Upload and manage brand knowledge" },
  voice:            { title: "Brand Voice",          subtitle: "Tone of voice, messaging pillars and personality" },
  "visual-identity":{ title: "Visual Identity",      subtitle: "Logos, colour palette, typography and design tokens" },
  products:         { title: "Products & Services",  subtitle: "Product catalogue, descriptions and imagery" },
  competitors:      { title: "Competitors",           subtitle: "Competitive landscape and positioning analysis" },
  personas:         { title: "Customer Personas",    subtitle: "Target audience profiles and segmentation" },
};

// ── Main BrandHub component ────────────────────────────────────
interface BrandHubProps {
  section?: BrandHubSection;
  onAssetsUploaded?: (counts: Record<string, number>) => void;
}

export default function BrandHub({ section = "guidelines", onAssetsUploaded }: BrandHubProps) {
  const meta = SECTION_META[section];

  const renderSection = () => {
    switch (section) {
      case "guidelines": return <GuidelinesSection onAssetsUploaded={onAssetsUploaded} />;
      case "voice":
        return <VoiceSection />;
      case "visual-identity":
        return <ComingSoon title="Visual Identity" description="Manage logos, colour palettes, typography and visual design tokens used across all campaign outputs. Coming soon." />;
      case "products":
        return <ComingSoon title="Products & Services" description="Upload and manage your product catalogue, descriptions, pricing and imagery for use in campaign generation. Coming soon." />;
      case "competitors":
        return <ComingSoon title="Competitors" description="Map the competitive landscape, positioning gaps and differentiation strategy to inform campaign direction. Coming soon." />;
      case "personas":
        return <ComingSoon title="Customer Personas" description="Define target audience segments, demographics, behaviours and motivations to power personalised campaigns. Coming soon." />;
    }
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" as const,
      alignItems: "center", justifyContent: "center",
      overflowY: "auto", position: "relative" as const, padding: "40px 24px" }}>

      {/* Page header */}
      <div style={{ maxWidth: 520, width: "100%", marginBottom: 28,
        position: "relative" as const, zIndex: 1 }}>
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
      <div style={{ position: "relative" as const, zIndex: 1, width: "100%",
        display: "flex", justifyContent: "center" }}>
        {renderSection()}
      </div>
    </div>
  );
}
