import { useState, useRef } from "react";

const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000";

interface AssetCategory {
  label: string;
  icon: React.ReactNode;
  key: string; // matches the key returned by the upload API
}

const ASSET_CATEGORIES: AssetCategory[] = [
  {
    key: "guidelines",
    label: "Brand Guidelines",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
    ),
  },
  {
    key: "logos",
    label: "Logos",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
      </svg>
    ),
  },
  {
    key: "products",
    label: "Product Images",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <circle cx="8.5" cy="8.5" r="1.5"/>
        <polyline points="21 15 16 10 5 21"/>
      </svg>
    ),
  },
  {
    key: "fonts",
    label: "Fonts",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="4 7 4 4 20 4 20 7"/>
        <line x1="9" y1="20" x2="15" y2="20"/>
        <line x1="12" y1="4" x2="12" y2="20"/>
      </svg>
    ),
  },
  {
    key: "colours",
    label: "Color Palette",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/>
        <circle cx="8.5" cy="7.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/>
        <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>
      </svg>
    ),
  },
  {
    key: "assets",
    label: "Brand Assets",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
      </svg>
    ),
  },
];

export default function BrandHub() {
  const [brandName, setBrandName]   = useState("");
  const [file, setFile]             = useState<File | null>(null);
  const [dragging, setDragging]     = useState(false);
  const [status, setStatus]         = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [uploaded, setUploaded]     = useState<Record<string, number>>({});
  const [skipped, setSkipped]       = useState<string[]>([]);
  const [errorMsg, setErrorMsg]     = useState("");
  const fileRef                     = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    if (!brandName.trim() || !file) return;
    setStatus("uploading"); setErrorMsg(""); setUploaded({}); setSkipped([]);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(
        `${API_BASE}/brands/${encodeURIComponent(brandName.trim())}/upload`,
        { method: "POST", body: fd },
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `Upload failed (${res.status})`);
      setUploaded(data.uploaded ?? {});
      setSkipped(data.skipped ?? []);
      setStatus("done");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && f.name.endsWith(".zip")) setFile(f);
  };

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "40px 48px" }}>
      {/* Page header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: "linear-gradient(135deg,#7c3aed,#6366f1)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800,
              color: "var(--text-primary)", letterSpacing: "-0.02em" }}>Brand Hub</h1>
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
              Upload and manage brand knowledge
            </p>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 560 }}>
        {/* Upload section */}
        <div style={{ padding: 24, borderRadius: 16,
          background: "var(--card-bg)", border: "1px solid var(--card-border)",
          boxShadow: "var(--shadow-sm)", marginBottom: 20 }}>

          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)",
            marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <span>📁</span> Upload Brand Guidelines (PDF)
          </div>

          {/* Brand name input */}
          <input
            value={brandName}
            onChange={e => setBrandName(e.target.value)}
            placeholder="Brand name (e.g. Acme Corp)"
            style={{ width: "100%", padding: "10px 14px", borderRadius: 10, fontSize: 13,
              border: "1.5px solid var(--card-border)", background: "var(--page-bg)",
              color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
              boxSizing: "border-box", marginBottom: 12, transition: "border-color 0.15s" }}
            onFocus={e => (e.currentTarget.style.borderColor = "#7c3aed")}
            onBlur={e => (e.currentTarget.style.borderColor = "var(--card-border)")}
          />

          {/* Drop zone */}
          <div
            onClick={() => fileRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            style={{
              padding: "28px 20px", borderRadius: 12, cursor: "pointer",
              border: `2px dashed ${dragging ? "#7c3aed" : "var(--card-border)"}`,
              background: dragging ? "rgba(124,58,237,0.06)" : "var(--card-bg-soft)",
              textAlign: "center", transition: "all 0.15s", marginBottom: 14,
            }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>⬆️</div>
            <div style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 600, marginBottom: 4 }}>
              {file ? file.name : "Drag & drop or browse"}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
              PDF, PNG, JPG up to 50MB — or a .zip with all brand folders
            </div>
            <input ref={fileRef} type="file" accept=".zip,.pdf,.png,.jpg,.jpeg"
              style={{ display: "none" }}
              onChange={e => setFile(e.target.files?.[0] ?? null)} />
          </div>

          <button
            onClick={handleUpload}
            disabled={!brandName.trim() || !file || status === "uploading"}
            style={{ padding: "10px 24px", borderRadius: 10, border: "none",
              fontFamily: "inherit", fontSize: 13, fontWeight: 700, color: "white",
              cursor: !brandName.trim() || !file ? "not-allowed" : "pointer",
              opacity: !brandName.trim() || !file ? 0.4 : 1,
              background: "linear-gradient(135deg,#7c3aed,#6366f1)",
              boxShadow: "0 4px 14px rgba(124,58,237,0.35)" }}>
            {status === "uploading" ? "Uploading & indexing…" : "Upload & index"}
          </button>

          {status === "error" && (
            <div style={{ marginTop: 12, fontSize: 12, color: "#ef4444" }}>⚠ {errorMsg}</div>
          )}
        </div>

        {/* Asset breakdown — shown after upload OR always if brand already has assets */}
        {status === "done" && (
          <div style={{ padding: 24, borderRadius: 16,
            background: "var(--card-bg)", border: "1px solid var(--card-border)",
            boxShadow: "var(--shadow-sm)" }}>

            {ASSET_CATEGORIES.map((cat, i) => {
              const count = uploaded[cat.key] ?? 0;
              if (count === 0 && skipped.includes(cat.key)) return null;
              const label = cat.key === "colours"
                ? `${count} color${count !== 1 ? "s" : ""}`
                : cat.key === "assets"
                ? `${count} file${count !== 1 ? "s" : ""}`
                : `${count} file${count !== 1 ? "s" : ""}`;

              return (
                <div key={cat.key}>
                  {i > 0 && (
                    <div style={{ height: 1, background: "var(--card-border)", margin: "0 0 0 0" }} />
                  )}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "14px 0" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <div style={{ width: 36, height: 36, borderRadius: 8, flexShrink: 0,
                        background: "var(--card-bg-soft)", border: "1px solid var(--card-border)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        color: "var(--text-secondary)" }}>
                        {cat.icon}
                      </div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                          {cat.label}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 1 }}>
                          {label}
                        </div>
                      </div>
                    </div>
                    {count > 0 ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                        style={{ flexShrink: 0 }}>
                        <circle cx="12" cy="12" r="10" fill="rgba(16,185,129,0.15)"
                          stroke="#10b981" strokeWidth="1.5"/>
                        <path d="M8 12l3 3 5-5" stroke="#10b981" strokeWidth="2"
                          strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                        style={{ flexShrink: 0 }}>
                        <circle cx="12" cy="12" r="10" stroke="var(--card-border)" strokeWidth="1.5"/>
                      </svg>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Footer */}
            <div style={{ marginTop: 4, paddingTop: 14, borderTop: "1px solid var(--card-border)",
              display: "flex", alignItems: "center", gap: 8 }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981"
                strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#10b981" }}>
                Brand knowledge is up to date
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
