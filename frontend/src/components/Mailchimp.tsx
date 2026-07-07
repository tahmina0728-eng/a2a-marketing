import { useState, useEffect } from "react";

const API = (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000";

interface Audience { id: string; name: string; member_count: number; }
interface Report {
  id: string; subject: string; emails_sent: number;
  open_rate: number; click_rate: number; send_time: string;
}

// ── Stat card ─────────────────────────────────────────────────
function Stat({ label, value, sub, color }: { label: string; value: string|number; sub?: string; color?: string }) {
  return (
    <div style={{ padding: "16px 18px", borderRadius: 12,
      background: "var(--card-bg)", border: "1px solid var(--card-border)" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
        textTransform: "uppercase" as const, letterSpacing: ".08em", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 900, color: color ?? "var(--text-primary)" }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────
export default function MailchimpPanel() {
  const [connected, setConnected]   = useState<boolean|null>(null);
  const [accountName, setAccount]   = useState("");
  const [audiences, setAudiences]   = useState<Audience[]>([]);
  const [reports, setReports]       = useState<Report[]>([]);
  const [error, setError]           = useState("");

  // Send form state
  const [listId, setListId]         = useState("");
  const [subject, setSubject]       = useState("");
  const [fromName, setFromName]     = useState("CampaignOS");
  const [replyTo, setReplyTo]       = useState("");
  const [html, setHtml]             = useState("");
  const [preview, setPreview]       = useState("");
  const [scheduleTime, setSchedule] = useState("");
  const [sending, setSending]       = useState(false);
  const [sentResult, setSentResult] = useState<{campaign_id:string;status:string}|null>(null);

  // Check connection on mount
  useEffect(() => {
    fetch(`${API}/mailchimp/ping`)
      .then(r => r.json())
      .then(d => {
        if (d.connected) {
          setConnected(true);
          setAccount(d.account_name);
          // Load audiences + reports in parallel
          Promise.all([
            fetch(`${API}/mailchimp/audiences`).then(r=>r.json()),
            fetch(`${API}/mailchimp/reports?count=5`).then(r=>r.json()),
          ]).then(([a, rpt]) => {
            setAudiences(a.audiences ?? []);
            setReports(rpt.reports ?? []);
          });
        } else {
          setConnected(false);
        }
      })
      .catch(() => setConnected(false));
  }, []);

  const handleSend = async () => {
    if (!listId || !subject || !html || !replyTo) {
      setError("Please fill in Audience, Subject, Reply-to email and HTML content.");
      return;
    }
    setSending(true); setError(""); setSentResult(null);
    try {
      const res = await fetch(`${API}/mailchimp/send`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          list_id: listId, subject, html, from_name: fromName,
          reply_to: replyTo, preview_text: preview, schedule_time: scheduleTime,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Send failed");
      setSentResult(data);
      // Refresh reports
      fetch(`${API}/mailchimp/reports?count=5`).then(r=>r.json()).then(d=>setReports(d.reports??[]));
    } catch (e: any) {
      setError(e.message);
    } finally { setSending(false); }
  };

  const G = "linear-gradient(135deg,#7c3aed,#6366f1)";

  // ── Not connected ─────────────────────────────────────────
  if (connected === false) {
    return (
      <div style={{ padding: "40px 32px", display: "flex", flexDirection: "column" as const,
        alignItems: "center", justifyContent: "center", gap: 16, textAlign: "center" as const }}>
        <div style={{ width: 56, height: 56, borderRadius: 14,
          background: "rgba(255,255,0,0.08)", border: "1px solid rgba(255,220,0,0.2)",
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 26 }}>
          🐵
        </div>
        <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
          Connect Mailchimp
        </div>
        <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6, maxWidth: 360 }}>
          Add your Mailchimp API key to the harness <code>.env</code> file:
        </div>
        <div style={{ padding: "12px 18px", borderRadius: 10,
          background: "var(--card-bg-soft)", border: "1px solid var(--card-border)",
          fontFamily: "monospace", fontSize: 12, color: "var(--text-primary)" }}>
          MAILCHIMP_API_KEY=your-key-us1
        </div>
        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
          Find your key at <strong>mailchimp.com → Account → API Keys</strong>
        </div>
        <button onClick={() => { setConnected(null); window.location.reload(); }}
          style={{ marginTop: 8, padding: "9px 22px", borderRadius: 10, border: "none",
            background: G, color: "white", fontWeight: 700, fontSize: 13, cursor: "pointer" }}>
          Retry connection
        </button>
      </div>
    );
  }

  // ── Loading ───────────────────────────────────────────────
  if (connected === null) {
    return (
      <div style={{ padding: 40, display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ width: 20, height: 20, borderRadius: "50%",
          border: "2.5px solid var(--card-border)", borderTopColor: "#7c3aed",
          animation: "spin 1s linear infinite" }} />
        <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Connecting to Mailchimp…</span>
        <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      </div>
    );
  }

  // ── Connected ─────────────────────────────────────────────
  return (
    <div style={{ padding: 0, display: "flex", flexDirection: "column" as const, gap: 24 }}>

      {/* Connection badge */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ fontSize: 22 }}>🐵</div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 800, color: "var(--text-primary)" }}>
            Mailchimp — {accountName}
          </div>
          <div style={{ fontSize: 11, color: "#10b981", display: "flex", alignItems: "center", gap: 5 }}>
            <span>●</span> Connected
          </div>
        </div>
      </div>

      {/* KPI tiles */}
      {reports.length > 0 && (
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)",
            textTransform: "uppercase" as const, letterSpacing: ".08em", marginBottom: 12 }}>
            Recent Campaign Performance
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 10 }}>
            {reports.slice(0,1).map(r => (
              <>
                <Stat key="sent" label="Emails Sent"   value={r.emails_sent.toLocaleString()} />
                <Stat key="open" label="Open Rate"     value={`${r.open_rate}%`} color="#7c3aed" sub="industry avg ~21%" />
                <Stat key="click" label="Click Rate"   value={`${r.click_rate}%`} color="#10b981" sub="industry avg ~2.3%" />
              </>
            ))}
          </div>

          {/* Campaign history table */}
          <div style={{ marginTop: 16, borderRadius: 12, overflow: "hidden",
            border: "1px solid var(--card-border)" }}>
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr",
              padding: "10px 16px", background: "var(--card-bg-soft)",
              fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
              textTransform: "uppercase" as const, letterSpacing: ".06em" }}>
              <span>Campaign</span><span>Sent</span><span>Opens</span><span>Clicks</span><span>Date</span>
            </div>
            {reports.map((r, i) => (
              <div key={r.id} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr",
                padding: "11px 16px", fontSize: 12, color: "var(--text-primary)",
                borderTop: i > 0 ? "1px solid var(--card-border)" : "none",
                background: "var(--card-bg)" }}>
                <span style={{ fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis",
                  whiteSpace: "nowrap" as const }}>{r.subject}</span>
                <span>{r.emails_sent.toLocaleString()}</span>
                <span style={{ color: "#7c3aed", fontWeight: 600 }}>{r.open_rate}%</span>
                <span style={{ color: "#10b981", fontWeight: 600 }}>{r.click_rate}%</span>
                <span style={{ color: "var(--text-secondary)" }}>
                  {r.send_time ? new Date(r.send_time).toLocaleDateString() : "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Send form */}
      <div>
        <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)", marginBottom: 16 }}>
          Send Campaign via Mailchimp
        </div>

        <div style={{ display: "flex", flexDirection: "column" as const, gap: 14,
          padding: 20, borderRadius: 14, background: "var(--card-bg)",
          border: "1px solid var(--card-border)" }}>

          {/* Audience selector */}
          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)",
              display: "block", marginBottom: 6, textTransform: "uppercase" as const, letterSpacing: ".06em" }}>
              Audience
            </label>
            <select value={listId} onChange={e => setListId(e.target.value)}
              style={{ width: "100%", padding: "9px 12px", borderRadius: 9, fontSize: 13,
                border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                color: "var(--text-primary)", fontFamily: "inherit", outline: "none" }}>
              <option value="">Select audience…</option>
              {audiences.map(a => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.member_count.toLocaleString()} contacts)
                </option>
              ))}
            </select>
          </div>

          {/* Subject + from + reply-to row */}
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 12 }}>
            {[
              { label: "Subject Line", val: subject, set: setSubject, ph: "Your subject line" },
              { label: "From Name",    val: fromName, set: setFromName, ph: "CampaignOS" },
              { label: "Reply-to Email", val: replyTo, set: setReplyTo, ph: "hello@brand.com" },
            ].map(f => (
              <div key={f.label}>
                <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)",
                  display: "block", marginBottom: 6, textTransform: "uppercase" as const, letterSpacing: ".06em" }}>
                  {f.label}
                </label>
                <input value={f.val} onChange={e => f.set(e.target.value)} placeholder={f.ph}
                  style={{ width: "100%", padding: "9px 12px", borderRadius: 9, fontSize: 13,
                    border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                    color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
                    boxSizing: "border-box" as const }} />
              </div>
            ))}
          </div>

          {/* Preview text */}
          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)",
              display: "block", marginBottom: 6, textTransform: "uppercase" as const, letterSpacing: ".06em" }}>
              Preview Text (inbox snippet)
            </label>
            <input value={preview} onChange={e => setPreview(e.target.value)}
              placeholder="Short teaser shown after subject in inbox…"
              style={{ width: "100%", padding: "9px 12px", borderRadius: 9, fontSize: 13,
                border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
                boxSizing: "border-box" as const }} />
          </div>

          {/* HTML content */}
          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)",
              display: "block", marginBottom: 6, textTransform: "uppercase" as const, letterSpacing: ".06em" }}>
              HTML Email Content
            </label>
            <textarea value={html} onChange={e => setHtml(e.target.value)} rows={5}
              placeholder="Paste the HTML email template here, or generate one via Poly agent above…"
              style={{ width: "100%", padding: "12px 14px", borderRadius: 9, fontSize: 12,
                border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                color: "var(--text-primary)", fontFamily: "monospace", outline: "none",
                resize: "vertical" as const, boxSizing: "border-box" as const }} />
          </div>

          {/* Schedule (optional) */}
          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)",
              display: "block", marginBottom: 6, textTransform: "uppercase" as const, letterSpacing: ".06em" }}>
              Schedule (optional — leave blank to send immediately)
            </label>
            <input type="datetime-local" value={scheduleTime}
              onChange={e => setSchedule(e.target.value ? new Date(e.target.value).toISOString() : "")}
              style={{ padding: "9px 12px", borderRadius: 9, fontSize: 13,
                border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                color: "var(--text-primary)", fontFamily: "inherit", outline: "none" }} />
          </div>

          {error && (
            <div style={{ padding: "10px 14px", borderRadius: 8, background: "rgba(239,68,68,0.08)",
              border: "1px solid rgba(239,68,68,0.2)", fontSize: 12, color: "#ef4444" }}>
              ⚠ {error}
            </div>
          )}

          {sentResult && (
            <div style={{ padding: "12px 16px", borderRadius: 10, background: "rgba(16,185,129,0.08)",
              border: "1px solid rgba(16,185,129,0.25)", fontSize: 13, color: "#10b981", fontWeight: 600 }}>
              ✓ Campaign {sentResult.status}! ID: {sentResult.campaign_id}
            </div>
          )}

          <button onClick={handleSend} disabled={sending}
            style={{ alignSelf: "flex-start" as const, padding: "11px 28px", borderRadius: 10,
              border: "none", background: G, color: "white", fontWeight: 700, fontSize: 13,
              cursor: sending ? "not-allowed" : "pointer", opacity: sending ? 0.6 : 1,
              boxShadow: "0 4px 16px rgba(124,58,237,0.3)",
              display: "flex", alignItems: "center", gap: 8 }}>
            🐵 {sending ? "Sending…" : scheduleTime ? "Schedule Campaign" : "Send Campaign Now"}
          </button>
        </div>
      </div>
    </div>
  );
}
