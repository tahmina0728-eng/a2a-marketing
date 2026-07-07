import { useState, useEffect } from "react";
import type { PublishingChannel } from "./PublishingNav";
import MailchimpPanel from "./Mailchimp";

const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000";
const BRANDS = ["Rnorr","Sunglow","Boozt","Glenfiddich","UBS Bank"];

const CHANNEL_META: Record<PublishingChannel, {
  label: string; color: string; desc: string; emoji: string;
}> = {
  instagram: { label:"Instagram", color:"#E1306C", emoji:"📸", desc:"Caption + hashtags for Feed, Stories or Reels" },
  facebook:  { label:"Facebook",  color:"#1877F2", emoji:"📘", desc:"Facebook post copy and engagement hook" },
  linkedin:  { label:"LinkedIn",  color:"#0A66C2", emoji:"💼", desc:"Professional post for brand awareness" },
  tiktok:    { label:"TikTok",    color:"#010101", emoji:"🎵", desc:"Short-form hook and caption" },
  youtube:   { label:"YouTube",   color:"#FF0000", emoji:"▶️", desc:"Video title, description and tags" },
  website:   { label:"Website",   color:"#7c3aed", emoji:"🌐", desc:"Landing page headline and body copy" },
  email:     { label:"Email",     color:"#0369a1", emoji:"📧", desc:"3 email layout variations — pick and send via Mailchimp" },
};

interface EmailLayout { id: string; name: string; layout: string; html: string; }

export default function Publishing({ channel }: { channel: PublishingChannel }) {
  const meta = CHANNEL_META[channel];

  // Brief state
  const [brief,  setBrief]  = useState("");
  const [brand,  setBrand]  = useState("");

  // Poly generation
  const [busy,   setBusy]   = useState(false);
  const [result, setResult] = useState<Record<string,string> | null>(null);

  // Email layout state
  const [layouts,  setLayouts]  = useState<EmailLayout[]>([]);
  const [layoutBusy, setLayoutBusy] = useState(false);
  const [selected, setSelected] = useState<EmailLayout | null>(null);
  const [editSubject, setEditSubject] = useState("");
  const [editHtml,    setEditHtml]    = useState("");
  const [mcSending,   setMcSending]   = useState(false);
  const [mcResult,    setMcResult]    = useState<any>(null);
  const [audiences,   setAudiences]   = useState<{id:string;name:string;member_count:number}[]>([]);
  const [mcListId,    setMcListId]    = useState("");

  // Reset when channel changes
  useEffect(() => {
    setResult(null); setLayouts([]); setSelected(null);
    setMcResult(null); setBusy(false); setLayoutBusy(false);
  }, [channel]);

  // Load Mailchimp audiences once for email
  useEffect(() => {
    if (channel === "email") {
      fetch(`${API_BASE}/mailchimp/audiences`)
        .then(r => r.json()).then(d => setAudiences(d.audiences ?? [])).catch(()=>{});
    }
  }, [channel]);

  const G = "linear-gradient(135deg,#7c3aed,#a855f7,#6366f1)";
  const col = meta.color;

  // ── Run Poly for non-email channels ──────────────────────────
  const runPoly = async () => {
    if (!brief.trim()) return;
    setBusy(true); setResult(null);
    const fullPrompt = [brand && `Brand: ${brand}`, brief].filter(Boolean).join(". ");
    try {
      const res = await fetch(`${API_BASE}/agents/channel/run`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: fullPrompt }),
      });
      const data = await res.json();
      setResult(data);
    } catch { } finally { setBusy(false); }
  };

  // ── Generate 3 email layouts ──────────────────────────────────
  const runEmailLayouts = async () => {
    if (!brief.trim()) return;
    setLayoutBusy(true); setLayouts([]); setSelected(null); setMcResult(null);
    const fullPrompt = [brand && `Brand: ${brand}`, brief].filter(Boolean).join(". ");
    try {
      const res = await fetch(`${API_BASE}/mailchimp/email-templates`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: fullPrompt, brand: brand || "" }),
      });
      const data = await res.json();
      if (data.templates) {
        setLayouts(data.templates);
        setEditSubject(data.subject ?? "");
      }
    } catch { } finally { setLayoutBusy(false); }
  };

  // ── Channel copy map (what Poly returns per channel) ──────────
  const CHANNEL_KEY: Record<PublishingChannel, string> = {
    instagram: "instagram", facebook: "instagram",
    linkedin: "instagram", tiktok: "tiktok",
    youtube: "ooh", website: "landing_headline", email: "email_subject",
  };

  const channelCopy = result?.[CHANNEL_KEY[channel]] ?? "";


  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "28px 32px" }}>
      {/* Page header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, flexShrink: 0,
          background: `${col}18`, border: `1.5px solid ${col}40`,
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>
          {meta.emoji}
        </div>
        <div>
          <h1 style={{ margin: 0, fontSize: 18, fontWeight: 800,
            color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
            {meta.label}
          </h1>
          <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>{meta.desc}</p>
        </div>
      </div>

      {/* Brief input — inlined (never a nested component function, that causes remount on keystroke) */}
      <div style={{ padding: 20, borderRadius: 16, background: "var(--card-bg)",
        border: "1px solid var(--card-border)", marginBottom: 20,
        boxShadow: "0 2px 16px rgba(0,0,0,0.05)" }}>
        <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
              textTransform: "uppercase" as const, letterSpacing: ".08em", marginBottom: 5 }}>Brand</div>
            <select value={brand} onChange={e => setBrand(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", borderRadius: 8, fontSize: 13,
                border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                color: "var(--text-primary)", fontFamily: "inherit", outline: "none" }}>
              <option value="">Select brand…</option>
              {BRANDS.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
        </div>
        <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
          textTransform: "uppercase" as const, letterSpacing: ".08em", marginBottom: 5 }}>
          Campaign Brief
        </div>
        <textarea value={brief} onChange={e => setBrief(e.target.value)}
          placeholder={`Describe your campaign — e.g. "Christmas festive campaign for UK families, warm and family-focused"`}
          rows={3}
          style={{ width: "100%", padding: "10px 14px", borderRadius: 10, resize: "none" as const,
            border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
            color: "var(--text-primary)", fontFamily: "inherit", fontSize: 13,
            lineHeight: 1.6, outline: "none", boxSizing: "border-box" as const,
            marginBottom: 12 }}
          onFocus={e => (e.currentTarget.style.borderColor = col)}
          onBlur={e => (e.currentTarget.style.borderColor = "var(--card-border)")} />
        <button
          onClick={channel === "email" ? runEmailLayouts : runPoly}
          disabled={!brief.trim() || busy || layoutBusy}
          style={{ padding: "10px 24px", borderRadius: 10, border: "none", fontFamily: "inherit",
            fontSize: 13, fontWeight: 700, color: "white", cursor: brief.trim() ? "pointer" : "not-allowed",
            opacity: brief.trim() ? 1 : 0.45, background: G,
            boxShadow: brief.trim() ? "0 4px 16px rgba(124,58,237,0.35)" : "none",
            display: "inline-flex", alignItems: "center", gap: 8 }}>
          {(busy || layoutBusy) ? (
            <>
              <span style={{ width: 14, height: 14, borderRadius: "50%",
                border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "white",
                animation: "spin 1s linear infinite", display: "inline-block" }} />
              Generating…
            </>
          ) : channel === "email"
            ? "✦ Generate 3 Email Layouts"
            : `✦ Generate ${meta.label} Content`}
        </button>
      </div>

      {/* ── EMAIL: 3 layout cards → select → edit → send ── */}
      {channel === "email" && (
        <>
          {/* Step 1: pick layout */}
          {layouts.length > 0 && !selected && (
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: col,
                letterSpacing: ".08em", textTransform: "uppercase" as const, marginBottom: 14 }}>
                Step 1 — Pick a layout
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
                {layouts.map(tpl => (
                  <div key={tpl.id}
                    onClick={() => { setSelected(tpl); setEditHtml(tpl.html); }}
                    style={{ borderRadius: 14, overflow: "hidden", cursor: "pointer",
                      border: `2px solid ${col}20`, transition: "all 0.15s",
                      boxShadow: `0 2px 12px ${col}10` }}
                    onMouseEnter={e => (e.currentTarget.style.border = `2px solid ${col}`)}
                    onMouseLeave={e => (e.currentTarget.style.border = `2px solid ${col}20`)}>
                    <div style={{ padding: "9px 12px", background: `${col}08`,
                      borderBottom: `1px solid ${col}15` }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: col }}>{tpl.name}</div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>{tpl.layout}</div>
                    </div>
                    <div style={{ height: 180, overflow: "hidden", background: "#f8fafc",
                      position: "relative" as const }}>
                      <iframe srcDoc={tpl.html} title={tpl.name}
                        style={{ width: "200%", height: "200%", border: "none",
                          transform: "scale(0.5)", transformOrigin: "top left",
                          pointerEvents: "none" as const }} />
                    </div>
                    <div style={{ padding: "9px", textAlign: "center" as const,
                      fontSize: 12, fontWeight: 700, color: col, background: `${col}06` }}>
                      Select →
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: edit & send */}
          {selected && (
            <div style={{ display: "flex", flexDirection: "column" as const, gap: 14 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: col,
                  letterSpacing: ".08em", textTransform: "uppercase" as const }}>
                  Step 2 — Edit & Send · {selected.name}
                </div>
                <button onClick={() => { setSelected(null); setMcResult(null); }}
                  style={{ fontSize: 11, color: "var(--text-secondary)", background: "none",
                    border: "none", cursor: "pointer" }}>← Back to layouts</button>
              </div>

              {/* Live preview */}
              <div style={{ borderRadius: 14, overflow: "hidden",
                border: "1px solid var(--card-border)", boxShadow: "0 4px 20px rgba(0,0,0,0.08)" }}>
                <iframe srcDoc={editHtml} title="Preview"
                  style={{ width: "100%", height: 340, border: "none", display: "block" }} />
              </div>

              {/* Editable fields */}
              <div style={{ padding: 16, borderRadius: 12, background: "var(--card-bg)",
                border: "1px solid var(--card-border)",
                display: "flex", flexDirection: "column" as const, gap: 12 }}>
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                    textTransform: "uppercase" as const, letterSpacing: ".08em", marginBottom: 5 }}>Subject Line</div>
                  <input value={editSubject} onChange={e => setEditSubject(e.target.value)}
                    style={{ width: "100%", padding: "9px 12px", borderRadius: 8, fontSize: 13,
                      border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                      color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
                      boxSizing: "border-box" as const }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                    textTransform: "uppercase" as const, letterSpacing: ".08em", marginBottom: 5 }}>
                    Edit HTML
                  </div>
                  <textarea value={editHtml} onChange={e => setEditHtml(e.target.value)} rows={5}
                    style={{ width: "100%", padding: "9px 12px", borderRadius: 8, fontSize: 11,
                      border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                      color: "var(--text-primary)", fontFamily: "monospace", outline: "none",
                      resize: "vertical" as const, boxSizing: "border-box" as const }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                    textTransform: "uppercase" as const, letterSpacing: ".08em", marginBottom: 5 }}>
                    Mailchimp Audience
                  </div>
                  <select value={mcListId} onChange={e => setMcListId(e.target.value)}
                    style={{ width: "100%", padding: "9px 12px", borderRadius: 8, fontSize: 13,
                      border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                      color: "var(--text-primary)", fontFamily: "inherit", outline: "none" }}>
                    <option value="">Select audience…</option>
                    {audiences.map(a => (
                      <option key={a.id} value={a.id}>{a.name} ({a.member_count} contacts)</option>
                    ))}
                  </select>
                </div>
              </div>

              {mcResult && (
                <div style={{ padding: "10px 14px", borderRadius: 8, fontSize: 12, fontWeight: 600,
                  background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.25)",
                  color: "#10b981" }}>
                  ✓ Campaign {mcResult.status}! ID: {mcResult.campaign_id}
                </div>
              )}

              <div style={{ display: "flex", gap: 10 }}>
                <a href={`data:text/html;charset=utf-8,${encodeURIComponent(editHtml)}`}
                  target="_blank" rel="noreferrer"
                  style={{ padding: "9px 18px", borderRadius: 9, border: `1.5px solid ${col}40`,
                    fontSize: 12, fontWeight: 700, color: col, textDecoration: "none",
                    background: `${col}08` }}>
                  Preview ↗
                </a>
                <button disabled={!mcListId || mcSending}
                  onClick={async () => {
                    setMcSending(true); setMcResult(null);
                    try {
                      const r = await fetch(`${API_BASE}/mailchimp/send`, {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ list_id: mcListId, subject: editSubject,
                          html: editHtml, from_name: "CampaignOS", reply_to: "" }),
                      });
                      const d = await r.json();
                      if (!r.ok) throw new Error(d.detail);
                      setMcResult(d);
                    } catch (e: any) { alert(e.message); }
                    finally { setMcSending(false); }
                  }}
                  style={{ flex: 1, padding: "10px 22px", borderRadius: 9, border: "none",
                    fontSize: 13, fontWeight: 700, color: "white",
                    cursor: mcListId ? "pointer" : "not-allowed", opacity: mcListId ? 1 : 0.4,
                    background: G, boxShadow: mcListId ? "0 4px 16px rgba(124,58,237,0.35)" : "none" }}>
                  🐵 {mcSending ? "Sending via Mailchimp…" : "Send Campaign via Mailchimp"}
                </button>
              </div>
            </div>
          )}

          {/* Mailchimp connect/status for empty state */}
          {layouts.length === 0 && !layoutBusy && <MailchimpPanel />}
        </>
      )}

      {/* ── NON-EMAIL: show Poly-generated copy ── */}
      {channel !== "email" && result && channelCopy && (
        <div style={{ padding: 20, borderRadius: 14, background: "var(--card-bg)",
          border: `1.5px solid ${col}30`, boxShadow: `0 4px 20px ${col}10` }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: col,
            textTransform: "uppercase" as const, letterSpacing: ".08em", marginBottom: 10 }}>
            {meta.emoji} Generated {meta.label} Copy
          </div>
          <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.7,
            whiteSpace: "pre-wrap" as const }}>
            {channelCopy}
          </div>
          <button onClick={() => navigator.clipboard?.writeText(channelCopy)}
            style={{ marginTop: 14, padding: "7px 16px", borderRadius: 8,
              border: `1.5px solid ${col}40`, background: `${col}08`,
              color: col, fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
            📋 Copy to clipboard
          </button>
        </div>
      )}

      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
