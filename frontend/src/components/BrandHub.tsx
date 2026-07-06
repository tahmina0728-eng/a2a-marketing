import { useState, useRef, useEffect } from "react";
import type { BrandHubSection } from "./BrandHubNav";

const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000";

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

function GuidelinesSection({ onAssetsUploaded }: { onAssetsUploaded?: (c: Record<string,number>) => void }) {
  const [brandName, setBrandName]   = useState("");
  const [file, setFile]             = useState<File | null>(null);
  const [dragging, setDragging]     = useState(false);
  const [status, setStatus]         = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [, setUploaded]     = useState<Record<string, number>>({});
  const [, setSkipped]       = useState<string[]>([]);
  const [errorMsg, setErrorMsg]     = useState("");
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
    setStatus("uploading"); setErrorMsg(""); setUploaded({}); setSkipped([]);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API_BASE}/brands/${encodeURIComponent(brandName.trim())}/upload`,
        { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `Upload failed (${res.status})`);
      // API returns PascalCase folder names (Guidelines, Logos, Font…).
      // Normalize to lowercase and map "font" → "fonts" to match ASSET_CATEGORIES keys.
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
            Only <strong>.zip</strong> files accepted — up to 50MB
          </div>
          <input ref={fileRef} type="file" accept=".zip"
            style={{ display: "none" }} onChange={e => setFile(e.target.files?.[0] ?? null)} />
        </div>

        <button onClick={handleUpload}
          disabled={!brandName.trim() || !file || status === "uploading"}
          style={{ padding: "10px 24px", borderRadius: 10, border: "none",
            fontFamily: "inherit", fontSize: 13, fontWeight: 700, color: "white",
            cursor: !brandName.trim() || !file ? "not-allowed" : "pointer",
            opacity: !brandName.trim() || !file ? 0.4 : 1,
            background: "linear-gradient(135deg,#7c3aed,#6366f1)" }}>
          {status === "uploading" ? "Uploading & indexing…" : "Upload & index"}
        </button>

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
        return <ComingSoon title="Brand Voice" description="Define your brand's tone of voice, messaging pillars, writing style and personality traits. Coming soon." />;
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
