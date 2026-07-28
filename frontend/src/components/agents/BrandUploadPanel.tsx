import { useState } from "react";
import { API_BASE_PUB } from "../../services/briefingApi";

export default function BrandUploadPanel() {
  const [brandName, setBrandName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [uploaded, setUploaded] = useState<Record<string, number>>({});
  const [skipped, setSkipped] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [progress, setProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState("");

  const CHUNK_SIZE = 10 * 1024 * 1024; // 10 MB — stays well under Cloud Run's 32 MB limit

  const handleUpload = async () => {
    if (!brandName.trim() || !file) return;
    setStatus("uploading");
    setProgress(0);
    setProgressLabel("Preparing upload…");
    setErrorMsg(""); setUploaded({}); setSkipped([]);

    const brand = encodeURIComponent(brandName.trim());
    const sessionId = crypto.randomUUID();
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

    try {
      // ── 1. Upload chunks ──────────────────────────────────────
      for (let i = 0; i < totalChunks; i++) {
        const slice = file.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE);
        const fd = new FormData();
        fd.append("file", slice, "chunk");
        fd.append("session_id", sessionId);
        fd.append("chunk_index", String(i));
        fd.append("total_chunks", String(totalChunks));
        setProgressLabel(`Uploading part ${i + 1} of ${totalChunks}…`);
        const res = await fetch(`${API_BASE_PUB}/brands/${brand}/upload-chunk`, {
          method: "POST", body: fd,
        });
        if (!res.ok) {
          const d = await res.json().catch(() => ({}));
          throw new Error((d as any)?.detail || `Chunk ${i + 1} failed (${res.status})`);
        }
        setProgress(Math.round(((i + 1) / totalChunks) * 80));
      }

      // ── 2. Finalise (assemble + ingest + reindex) ─────────────
      setProgressLabel("Indexing brand assets…");
      setProgress(85);
      const res = await fetch(`${API_BASE_PUB}/brands/${brand}/finalize-upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, total_chunks: totalChunks }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error((data as any)?.detail || `Finalise failed (${res.status})`);
      setProgress(100);
      setUploaded(data.uploaded ?? {});
      setSkipped(data.skipped ?? []);
      setStatus("done");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  };

  const busy = status === "uploading";

  return (
    <div style={{ marginTop: 12, paddingTop: 16, borderTop: "1px solid var(--card-border)" }}>
      <div style={{ fontSize: 13, fontWeight: 800, color: "var(--text-primary)", marginBottom: 4 }}>
        📁 Onboard a new brand
      </div>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5, margin: "0 0 14px" }}>
        Upload a .zip with <code>Guidelines/</code>, <code>Logos/</code>, <code>Font/</code>,{" "}
        <code>Colours/</code> and <code>Assets/</code> subfolders. Logos will re-index its search
        index so it can immediately retrieve the new brand's guidelines.
      </p>

      <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
        <input value={brandName} onChange={(e) => setBrandName(e.target.value)}
          placeholder="Brand name (e.g. Acme Corp)"
          style={{ flex: 1, padding: "8px 12px", borderRadius: 8, fontSize: 13,
            border: "1px solid var(--card-border)", background: "var(--input-bg)",
            color: "var(--text-primary)", fontFamily: "inherit", outline: "none" }} />
        <label style={{ padding: "8px 14px", borderRadius: 8, fontSize: 13, fontWeight: 600,
          border: "1px solid var(--card-border)", background: "var(--card-bg-soft)",
          color: "var(--text-secondary)", cursor: busy ? "default" : "pointer",
          whiteSpace: "nowrap" as const, opacity: busy ? 0.5 : 1 }}>
          {file
            ? `${file.name.slice(0, 18)} (${(file.size / 1024 / 1024).toFixed(1)} MB)`
            : "Choose .zip"}
          <input type="file" accept=".zip" disabled={busy} style={{ display: "none" }}
            onChange={(e) => { setFile(e.target.files?.[0] ?? null); setStatus("idle"); setErrorMsg(""); setProgress(0); }} />
        </label>
      </div>

      <button onClick={handleUpload} disabled={!brandName.trim() || !file || busy}
        style={{ padding: "9px 18px", borderRadius: 10, border: "none", fontFamily: "inherit",
          fontSize: 13, fontWeight: 700, color: "white",
          cursor: (!brandName.trim() || !file || busy) ? "default" : "pointer",
          opacity: (!brandName.trim() || !file) ? 0.4 : 1,
          background: "linear-gradient(135deg, #7c3aed, #6366f1)" }}>
        {busy ? "Uploading…" : "Upload & index"}
      </button>

      {busy && (
        <div style={{ marginTop: 12 }}>
          <div style={{ height: 4, borderRadius: 4, background: "var(--card-border)", overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${progress}%`, borderRadius: 4,
              background: "linear-gradient(90deg, #7c3aed, #6366f1)",
              transition: "width 0.3s ease" }} />
          </div>
          <div style={{ fontSize: 11, color: "#7c3aed", marginTop: 5, fontWeight: 600 }}>{progressLabel}</div>
        </div>
      )}

      {status === "error" && (
        <div style={{ marginTop: 12, fontSize: 12, lineHeight: 1.5, color: "#ef4444" }}>⚠ {errorMsg}</div>
      )}

      {status === "done" && (
        <div style={{ marginTop: 14, padding: "14px 16px", borderRadius: 12,
          background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.25)" }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#10b981", marginBottom: 6 }}>
            ✓ "{brandName.trim()}" indexed and searchable
          </div>
          <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 6, marginBottom: skipped.length ? 8 : 0 }}>
            {Object.entries(uploaded).map(([cat, n]) => (
              <span key={cat} style={{ fontSize: 11, fontWeight: 600, padding: "3px 9px", borderRadius: 99,
                background: "var(--card-bg-soft)", border: "1px solid var(--card-border)",
                color: "var(--text-secondary)" }}>{n} {cat}</span>
            ))}
          </div>
          {skipped.length > 0 && (
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8 }}>
              {skipped.length} file{skipped.length > 1 ? "s" : ""} skipped (not inside a recognised subfolder):{" "}
              {skipped.slice(0, 3).join(", ")}{skipped.length > 3 ? `, +${skipped.length - 3} more` : ""}
            </div>
          )}
          <div style={{ fontSize: 11.5, color: "var(--text-tertiary)", lineHeight: 1.55,
            borderTop: "1px solid rgba(16,185,129,0.18)", paddingTop: 8 }}>
            Logos can now retrieve this brand's guidelines for brief validation. It's <strong>not yet</strong>{" "}
            selectable in the campaign wizard's brand picker — that list is still a fixed set and needs a
            separate code change (logo asset, product list, fan truths) to add a new brand there.
          </div>
        </div>
      )}
    </div>
  );
}
