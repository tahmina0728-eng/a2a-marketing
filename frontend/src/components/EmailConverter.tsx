import { useState, useCallback, useRef, useEffect } from "react";
import { API_BASE_PUB } from "../services/briefingApi";

// ── Brand presets ──────────────────────────────────────────────────────────────
const BRAND_PRESETS: Array<{ id: string; label: string; color: string }> = [
  { id: "Barclays",    label: "Barclays",    color: "#00AEEF" },
  { id: "UBS Bank",    label: "UBS Bank",    color: "#E60000" },
  { id: "Sunrise",     label: "Sunrise",     color: "#E2001A" },
  { id: "Haleon",      label: "Haleon",      color: "#0A3D52" },
  { id: "Rnorr",       label: "Rnorr",       color: "#C8102E" },
  { id: "Sunglow",     label: "Sunglow",     color: "#F5A623" },
  { id: "Boozt",       label: "Boozt",       color: "#1A1A2E" },
  { id: "Glenfiddich", label: "Glenfiddich", color: "#7B3A10" },
];

type Slots = {
  subject:   string;
  preheader: string;
  headline:  string;
  subline:   string;
  body:      string[];
  cta:       string;
  tables:    Array<{ headers: string[]; rows: string[][] }>;
};

type ConvertResult = {
  html:        string;
  slots:       Slots;
  image_count: number;
  filename:    string;
};

type Audience = { id: string; name: string; member_count: number };

type SendForm = {
  list_id:       string;
  subject:       string;
  preview_text:  string;
  from_name:     string;
  reply_to:      string;
  schedule_time: string;
};

const SLOT_META: Array<{ key: keyof Slots; label: string; icon: string }> = [
  { key: "subject",   label: "Email Subject", icon: "✉" },
  { key: "preheader", label: "Preheader",     icon: "👁" },
  { key: "headline",  label: "Headline",      icon: "H" },
  { key: "subline",   label: "Subline",       icon: "h" },
  { key: "body",      label: "Body Copy",     icon: "¶" },
  { key: "cta",       label: "CTA Button",    icon: "→" },
];

const ACCEPTED_TYPES = ".docx,.pdf,.xlsx,.xls,.csv";
const ACCEPTED_LABEL = "Word · PDF · Excel · CSV";

function FileIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
    </svg>
  );
}

function MailIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
      stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
      <polyline points="22,6 12,13 2,6"/>
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13"/>
      <polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  );
}

function Spinner({ size = 15, color = "#fff" }: { size?: number; color?: string }) {
  return (
    <span style={{
      display: "inline-block", width: size, height: size,
      border: `2px solid ${color}33`, borderTopColor: color,
      borderRadius: "50%", animation: "ec-spin 0.7s linear infinite",
      flexShrink: 0,
    }} />
  );
}

// ── Send modal ─────────────────────────────────────────────────────────────────
function SendModal({
  html, slots, brandName, onClose,
}: {
  html: string; slots: Slots; brandName: string; onClose: () => void;
}) {
  const [audiences,        setAudiences]        = useState<Audience[]>([]);
  const [audiencesLoading, setAudiencesLoading] = useState(true);
  const [audiencesError,   setAudiencesError]   = useState<string | null>(null);

  const [form, setForm] = useState<SendForm>({
    list_id:       "",
    subject:       slots.subject || slots.headline || "",
    preview_text:  slots.preheader || "",
    from_name:     brandName || "CampaignOS",
    reply_to:      "",
    schedule_time: "",
  });

  const [sending,     setSending]     = useState(false);
  const [sendError,   setSendError]   = useState<string | null>(null);
  const [sendSuccess, setSendSuccess] = useState<{ campaign_id: string; status: string } | null>(null);

  // Load audiences on mount
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE_PUB}/mailchimp/audiences`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const list: Audience[] = data.audiences ?? [];
        setAudiences(list);
        if (list.length === 1) setForm(f => ({ ...f, list_id: list[0].id }));
      } catch (e: unknown) {
        setAudiencesError(e instanceof Error ? e.message : "Could not load audiences");
      } finally {
        setAudiencesLoading(false);
      }
    })();
  }, []);

  const doSend = async (overrideForm?: Partial<SendForm>) => {
    const payload = { ...form, ...overrideForm };
    if (!payload.list_id || !payload.subject || !payload.reply_to) return;
    setSending(true);
    setSendError(null);
    try {
      const res = await fetch(`${API_BASE_PUB}/mailchimp/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, html }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as any).detail ?? `Server error ${res.status}`);
      }
      setSendSuccess(await res.json());
    } catch (e: unknown) {
      setSendError(e instanceof Error ? e.message : "Send failed");
    } finally {
      setSending(false);
    }
  };

  const handleSend = () => doSend();
  const handleSendNow = () => {
    setForm(f => ({ ...f, schedule_time: "" }));
    doSend({ schedule_time: "" });
  };

  const inputSt: React.CSSProperties = {
    width: "100%", padding: "9px 12px", borderRadius: 8,
    border: "1px solid var(--card-border)",
    background: "var(--page-bg)", color: "var(--text-primary)",
    fontFamily: "inherit", fontSize: 13, boxSizing: "border-box" as const,
    outline: "none",
  };
  const label = (txt: string, required = false) => (
    <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)",
      display: "block", marginBottom: 6 }}>
      {txt}{required && <span style={{ color: "#ef4444", marginLeft: 3 }}>*</span>}
    </label>
  );

  const canSend = !!form.list_id && !!form.subject.trim() && !!form.reply_to.trim();

  return (
    <>
      {/* Backdrop */}
      <div onClick={onClose} style={{
        position: "fixed" as const, inset: 0, zIndex: 200,
        background: "rgba(0,0,0,0.55)", backdropFilter: "blur(4px)",
      }} />

      {/* Modal panel */}
      <div style={{
        position: "fixed" as const, inset: 0, zIndex: 201,
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 24, pointerEvents: "none" as const,
      }}>
        <div onClick={e => e.stopPropagation()} style={{
          width: "100%", maxWidth: 520, borderRadius: 18,
          background: "var(--card-bg)", border: "1px solid var(--card-border)",
          boxShadow: "0 24px 64px rgba(0,0,0,0.35)",
          pointerEvents: "auto" as const,
          overflow: "hidden",
        }}>
          {/* Header */}
          <div style={{ padding: "22px 28px 20px",
            borderBottom: "1px solid var(--card-border)",
            display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 38, height: 38, borderRadius: 10, flexShrink: 0,
                background: "linear-gradient(135deg,#7c3aed,#a855f7)",
                display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none"
                  stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"/>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              </div>
              <div>
                <div style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)",
                  letterSpacing: "-0.02em" }}>Send via Mailchimp</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 1 }}>
                  Converted HTML email will be sent as a campaign
                </div>
              </div>
            </div>
            <button onClick={onClose} style={{ background: "none", border: "none",
              cursor: "pointer", color: "var(--text-tertiary)", padding: 4,
              borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 18, lineHeight: 1 }}>×</button>
          </div>

          {sendSuccess ? (
            /* ── Success state ── */
            <div style={{ padding: "40px 28px", textAlign: "center" }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)",
                marginBottom: 8 }}>
                {sendSuccess.status === "scheduled" ? "Campaign Scheduled" : "Campaign Sent!"}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 6 }}>
                Mailchimp campaign ID: <code style={{ fontSize: 12, background: "var(--page-bg)",
                  padding: "2px 6px", borderRadius: 4 }}>{sendSuccess.campaign_id}</code>
              </div>
              <div style={{ fontSize: 13, color: "var(--text-tertiary)", marginBottom: 28 }}>
                {sendSuccess.status === "scheduled"
                  ? `Scheduled for ${form.schedule_time}`
                  : "The email is on its way to your audience."}
              </div>
              <button onClick={onClose} style={{ padding: "10px 28px", borderRadius: 10,
                border: "none", background: "linear-gradient(135deg,#7c3aed,#a855f7)",
                color: "#fff", fontFamily: "inherit", fontSize: 14, fontWeight: 700,
                cursor: "pointer" }}>
                Done
              </button>
            </div>
          ) : (
            /* ── Form ── */
            <div style={{ padding: "24px 28px", display: "flex", flexDirection: "column", gap: 18 }}>

              {/* Audience */}
              <div>
                {label("Mailchimp Audience", true)}
                {audiencesLoading ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 8,
                    padding: "9px 12px", borderRadius: 8, border: "1px solid var(--card-border)",
                    background: "var(--page-bg)", color: "var(--text-tertiary)", fontSize: 13 }}>
                    <Spinner size={13} color="var(--text-tertiary)" />
                    Loading audiences…
                  </div>
                ) : audiencesError ? (
                  <div style={{ padding: "9px 12px", borderRadius: 8, fontSize: 13,
                    background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)",
                    color: "#ef4444" }}>
                    {audiencesError} — check your MAILCHIMP_API_KEY
                  </div>
                ) : (
                  <select value={form.list_id} onChange={e => setForm(f => ({ ...f, list_id: e.target.value }))}
                    style={{ ...inputSt, appearance: "none", cursor: "pointer" }}>
                    <option value="">Select an audience…</option>
                    {audiences.map(a => (
                      <option key={a.id} value={a.id}>
                        {a.name} ({a.member_count.toLocaleString()} contacts)
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Subject + preheader side by side */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>
                  {label("Subject Line", true)}
                  <input type="text" value={form.subject}
                    onChange={e => setForm(f => ({ ...f, subject: e.target.value }))}
                    placeholder="Email subject" style={inputSt} />
                </div>
                <div>
                  {label("Preheader Text")}
                  <input type="text" value={form.preview_text}
                    onChange={e => setForm(f => ({ ...f, preview_text: e.target.value }))}
                    placeholder="Preview text…" style={inputSt} />
                </div>
              </div>

              {/* From name + reply-to */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>
                  {label("From Name")}
                  <input type="text" value={form.from_name}
                    onChange={e => setForm(f => ({ ...f, from_name: e.target.value }))}
                    placeholder="e.g. Barclays" style={inputSt} />
                </div>
                <div>
                  {label("Reply-to Email", true)}
                  <input type="email" value={form.reply_to}
                    onChange={e => setForm(f => ({ ...f, reply_to: e.target.value }))}
                    placeholder="verified@yourdomain.com" style={inputSt} />
                </div>
              </div>

              {/* Schedule (optional) */}
              <div>
                {label("Schedule Send (optional — leave blank to send now)")}
                <input type="datetime-local" value={form.schedule_time}
                  onChange={e => setForm(f => ({ ...f, schedule_time: e.target.value ? new Date(e.target.value).toISOString() : "" }))}
                  style={inputSt} />
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 5 }}>
                  Leave empty to send immediately. Reply-to must be verified in your Mailchimp account.
                </div>
              </div>

              {/* Error */}
              {sendError && (
                <div style={{ background: "rgba(239,68,68,0.08)",
                  border: "1px solid rgba(239,68,68,0.25)", borderRadius: 9,
                  padding: "12px 14px" }}>
                  <div style={{ fontSize: 13, color: "#ef4444",
                    marginBottom: form.schedule_time && /paid|schedule|plan|403/i.test(sendError) ? 10 : 0 }}>
                    {sendError}
                  </div>
                  {form.schedule_time && /paid|schedule|plan|403/i.test(sendError) && (
                    <button onClick={handleSendNow} disabled={sending}
                      style={{ padding: "7px 16px", borderRadius: 8, border: "none",
                        background: "#7c3aed", color: "#fff",
                        fontFamily: "inherit", fontSize: 12, fontWeight: 700,
                        cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
                      <SendIcon />
                      Send immediately instead
                    </button>
                  )}
                </div>
              )}

              {/* Actions */}
              <div style={{ display: "flex", gap: 10, justifyContent: "flex-end",
                paddingTop: 4, borderTop: "1px solid var(--card-border)" }}>
                <button onClick={onClose}
                  style={{ padding: "9px 20px", borderRadius: 9, cursor: "pointer",
                    fontFamily: "inherit", fontSize: 13, fontWeight: 600,
                    border: "1px solid var(--card-border)", background: "var(--card-bg)",
                    color: "var(--text-primary)" }}>
                  Cancel
                </button>
                <button onClick={handleSend} disabled={!canSend || sending}
                  style={{
                    padding: "9px 22px", borderRadius: 9, cursor: canSend && !sending ? "pointer" : "not-allowed",
                    fontFamily: "inherit", fontSize: 13, fontWeight: 700, border: "none",
                    background: canSend && !sending
                      ? "linear-gradient(135deg,#7c3aed,#a855f7)" : "var(--card-border)",
                    color: canSend && !sending ? "#fff" : "var(--text-tertiary)",
                    display: "flex", alignItems: "center", gap: 8,
                    boxShadow: canSend && !sending ? "0 2px 10px rgba(124,58,237,0.3)" : "none",
                    transition: "all 0.15s",
                  }}>
                  {sending ? <><Spinner />{form.schedule_time ? "Scheduling…" : "Sending…"}</> : <><SendIcon />{form.schedule_time ? "Schedule Campaign" : "Send Now"}</>}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}


// ── Main component ─────────────────────────────────────────────────────────────
export default function EmailConverter() {
  const [file,       setFile]       = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [brandName,  setBrandName]  = useState("");
  const [brandColor, setBrandColor] = useState("#0055A4");
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState<string | null>(null);
  const [result,     setResult]     = useState<ConvertResult | null>(null);
  const [copied,     setCopied]     = useState(false);
  const [previewTab, setPreviewTab] = useState<"preview" | "source">("preview");
  const [sendOpen,   setSendOpen]   = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);

  const pickFile = useCallback((files: FileList | null) => {
    if (!files?.length) return;
    const f = files[0];
    setFile(f);
    setResult(null);
    setError(null);
    const lower = f.name.toLowerCase();
    for (const p of BRAND_PRESETS) {
      if (lower.includes(p.id.toLowerCase())) {
        setBrandName(p.label);
        setBrandColor(p.color);
        break;
      }
    }
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    pickFile(e.dataTransfer.files);
  }, [pickFile]);

  const handleConvert = async () => {
    if (!file || loading) return;
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("brand_name", brandName);
      form.append("brand_color", brandColor);
      const res = await fetch(`${API_BASE_PUB}/convert-email`, { method: "POST", body: form });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as any).detail ?? `Server error ${res.status}`);
      }
      setResult(await res.json());
      setPreviewTab("preview");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Conversion failed — please try again");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;
    const blob = new Blob([result.html], { type: "text/html" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = result.filename.replace(/\.[^.]+$/, "") + ".html";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopy = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result.html);
    setCopied(true);
    setTimeout(() => setCopied(false), 2200);
  };

  const inputBase: React.CSSProperties = {
    width: "100%", padding: "9px 12px", borderRadius: 8,
    border: "1px solid var(--card-border)",
    background: "var(--page-bg)", color: "var(--text-primary)",
    fontFamily: "inherit", fontSize: 13, boxSizing: "border-box" as const,
    outline: "none",
  };

  const pill = (active: boolean): React.CSSProperties => ({
    padding: "5px 14px", borderRadius: 20, border: "none", cursor: "pointer",
    fontFamily: "inherit", fontSize: 12, fontWeight: 600,
    background: active ? "#7c3aed" : "var(--card-bg)",
    color: active ? "#fff" : "var(--text-secondary)",
    transition: "all 0.15s",
  });

  const slotValue = (_key: keyof Slots, val: Slots[keyof Slots]): string => {
    if (!val) return "";
    if (Array.isArray(val)) {
      if (val.length === 0) return "";
      const head = val.slice(0, 2).join("  ·  ");
      return val.length > 2 ? `${head}  … +${val.length - 2} more` : head;
    }
    return String(val);
  };

  return (
    <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column",
      background: "var(--page-bg)" }}>

      {/* ── Header ── */}
      <div style={{ padding: "28px 36px 20px", borderBottom: "1px solid var(--card-border)",
        flexShrink: 0, background: "var(--card-bg)", backdropFilter: "blur(12px)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 44, height: 44, borderRadius: 12, flexShrink: 0,
            background: "linear-gradient(135deg,#7c3aed,#a855f7)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 16px rgba(124,58,237,0.35)" }}>
            <MailIcon />
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800, letterSpacing: "-0.03em",
              color: "var(--text-primary)" }}>
              Email Converter
            </h1>
            <p style={{ margin: "3px 0 0", fontSize: 13, color: "var(--text-secondary)" }}>
              Upload a client document — convert to responsive HTML email and send via Mailchimp.
            </p>
          </div>
        </div>
      </div>

      {/* ── Main body ── */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", minHeight: 0 }}>

        {/* ── Left panel: settings ── */}
        <div style={{ width: 300, flexShrink: 0, borderRight: "1px solid var(--card-border)",
          display: "flex", flexDirection: "column", overflowY: "auto" }}>
          <div style={{ padding: "24px 20px", display: "flex", flexDirection: "column", gap: 20 }}>

            {/* Dropzone */}
            <div
              role="button" tabIndex={0}
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
              onClick={() => fileRef.current?.click()}
              onKeyDown={e => e.key === "Enter" && fileRef.current?.click()}
              style={{
                border: `2px dashed ${isDragging ? "#7c3aed" : file ? "rgba(124,58,237,0.45)" : "var(--card-border)"}`,
                borderRadius: 14, padding: "28px 16px", textAlign: "center",
                cursor: "pointer", userSelect: "none",
                background: isDragging ? "rgba(124,58,237,0.07)"
                  : file ? "rgba(124,58,237,0.04)" : "var(--card-bg)",
                transition: "all 0.18s", outline: "none",
              }}>
              <input ref={fileRef} type="file" accept={ACCEPTED_TYPES} style={{ display: "none" }}
                onChange={e => pickFile(e.target.files)} />
              {file ? (
                <>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>📄</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)",
                    marginBottom: 3, wordBreak: "break-word" }}>{file.name}</div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                    {(file.size / 1024).toFixed(1)} KB · click to replace
                  </div>
                </>
              ) : (
                <>
                  <div style={{ color: "var(--text-tertiary)", marginBottom: 10 }}><FileIcon /></div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                    Drop document here
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 10 }}>
                    or click to browse
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)",
                    background: "rgba(124,58,237,0.08)", borderRadius: 20,
                    padding: "3px 10px", display: "inline-block",
                    border: "1px solid rgba(124,58,237,0.18)" }}>
                    {ACCEPTED_LABEL}
                  </div>
                </>
              )}
            </div>

            {/* Brand settings */}
            <div style={{ background: "var(--card-bg)", border: "1px solid var(--card-border)",
              borderRadius: 14, padding: 18 }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: ".07em",
                textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 16 }}>
                Brand settings <span style={{ opacity: 0.5, fontWeight: 400 }}>(optional)</span>
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)",
                  display: "block", marginBottom: 6 }}>Brand name</label>
                <input type="text" value={brandName} placeholder="e.g. Barclays"
                  onChange={e => setBrandName(e.target.value)} style={inputBase} />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)",
                  display: "block", marginBottom: 6 }}>Brand colour</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input type="color" value={brandColor} onChange={e => setBrandColor(e.target.value)}
                    style={{ width: 40, height: 36, borderRadius: 8, cursor: "pointer",
                      border: "1px solid var(--card-border)", padding: 3, flexShrink: 0,
                      background: "none" }} />
                  <input type="text" value={brandColor}
                    onChange={e => { if (/^#[0-9A-Fa-f]{0,6}$/.test(e.target.value)) setBrandColor(e.target.value); }}
                    style={{ ...inputBase, flex: 1, fontFamily: "monospace", width: "auto" }} />
                </div>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
                {BRAND_PRESETS.map(p => (
                  <button key={p.id} title={p.label}
                    onClick={() => { setBrandName(p.label); setBrandColor(p.color); }}
                    style={{ width: 26, height: 26, borderRadius: 7, padding: 0, cursor: "pointer",
                      background: p.color, border: brandColor === p.color
                        ? "3px solid var(--text-primary)" : "2px solid transparent",
                      transition: "border 0.15s" }} />
                ))}
              </div>
            </div>

            {/* Convert button */}
            <button onClick={handleConvert} disabled={!file || loading}
              style={{
                padding: "13px 20px", borderRadius: 12, border: "none",
                background: file && !loading ? "linear-gradient(135deg,#7c3aed,#a855f7)" : "var(--card-border)",
                color: file && !loading ? "#fff" : "var(--text-tertiary)",
                fontFamily: "inherit", fontSize: 14, fontWeight: 700,
                cursor: file && !loading ? "pointer" : "not-allowed",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 9,
                boxShadow: file && !loading ? "0 4px 18px rgba(124,58,237,0.35)" : "none",
                transition: "all 0.2s",
              }}>
              {loading ? <><Spinner /> Converting…</> : "Convert to HTML Email"}
            </button>

            {error && (
              <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                borderRadius: 10, padding: "12px 14px", fontSize: 13, color: "#ef4444", lineHeight: 1.5 }}>
                {error}
              </div>
            )}

            {/* Extracted content summary */}
            {result && (
              <div style={{ background: "var(--card-bg)", border: "1px solid var(--card-border)",
                borderRadius: 14, padding: 18 }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: ".07em",
                  textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 16 }}>
                  Extracted content
                </div>
                {SLOT_META.map(({ key, label, icon }) => {
                  const val = result.slots[key];
                  const display = slotValue(key, val);
                  if (!display) return null;
                  return (
                    <div key={key} style={{ marginBottom: 11, paddingBottom: 11,
                      borderBottom: "1px solid var(--card-border)" }}>
                      <div style={{ fontSize: 10, fontWeight: 800, color: "var(--text-tertiary)",
                        letterSpacing: ".06em", textTransform: "uppercase", marginBottom: 3 }}>
                        {icon} {label}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-primary)", lineHeight: 1.5,
                        overflow: "hidden", textOverflow: "ellipsis",
                        display: "-webkit-box" as any, WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical" as any }}>
                        {display}
                      </div>
                    </div>
                  );
                })}
                {result.slots.tables?.length > 0 && (
                  <div style={{ marginBottom: 11, paddingBottom: 11, borderBottom: "1px solid var(--card-border)" }}>
                    <div style={{ fontSize: 10, fontWeight: 800, color: "var(--text-tertiary)",
                      letterSpacing: ".06em", textTransform: "uppercase", marginBottom: 3 }}>⊞ Tables</div>
                    <div style={{ fontSize: 12, color: "var(--text-primary)" }}>
                      {result.slots.tables.length} table{result.slots.tables.length !== 1 ? "s" : ""} detected
                    </div>
                  </div>
                )}
                {result.image_count > 0 && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 800, color: "var(--text-tertiary)",
                      letterSpacing: ".06em", textTransform: "uppercase", marginBottom: 3 }}>🖼 Images</div>
                    <div style={{ fontSize: 12, color: "var(--text-primary)" }}>
                      {result.image_count} image{result.image_count !== 1 ? "s" : ""} embedded
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Right panel: preview ── */}
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
          {result ? (
            <>
              {/* Toolbar */}
              <div style={{ padding: "12px 24px", borderBottom: "1px solid var(--card-border)",
                display: "flex", alignItems: "center", justifyContent: "space-between",
                flexShrink: 0, background: "var(--card-bg)" }}>
                <div style={{ display: "flex", gap: 6,
                  background: "var(--page-bg)", borderRadius: 22, padding: 3,
                  border: "1px solid var(--card-border)" }}>
                  <button onClick={() => setPreviewTab("preview")} style={pill(previewTab === "preview")}>Preview</button>
                  <button onClick={() => setPreviewTab("source")} style={pill(previewTab === "source")}>HTML Source</button>
                </div>
                <div style={{ display: "flex", gap: 10 }}>
                  <button onClick={handleCopy}
                    style={{ padding: "8px 16px", borderRadius: 9, cursor: "pointer",
                      fontFamily: "inherit", fontSize: 12, fontWeight: 600,
                      border: "1px solid var(--card-border)", background: "var(--card-bg)",
                      color: copied ? "#22c55e" : "var(--text-primary)", transition: "all 0.15s" }}>
                    {copied ? "✓ Copied!" : "Copy HTML"}
                  </button>
                  <button onClick={handleDownload}
                    style={{ padding: "8px 18px", borderRadius: 9, cursor: "pointer",
                      fontFamily: "inherit", fontSize: 12, fontWeight: 700,
                      background: "var(--card-bg)", color: "var(--text-primary)",
                      border: "1px solid var(--card-border)" }}>
                    ↓ Download .html
                  </button>
                  {/* ── Send button ── */}
                  <button onClick={() => setSendOpen(true)}
                    style={{ padding: "8px 18px", borderRadius: 9, cursor: "pointer",
                      fontFamily: "inherit", fontSize: 12, fontWeight: 700, border: "none",
                      background: "linear-gradient(135deg,#7c3aed,#a855f7)", color: "#fff",
                      display: "flex", alignItems: "center", gap: 7,
                      boxShadow: "0 2px 10px rgba(124,58,237,0.3)" }}>
                    <SendIcon />
                    Send via Mailchimp
                  </button>
                </div>
              </div>

              {/* Subject pill */}
              {result.slots.subject && (
                <div style={{ padding: "10px 24px", borderBottom: "1px solid var(--card-border)",
                  background: "var(--card-bg)", flexShrink: 0,
                  display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: ".07em",
                    textTransform: "uppercase", color: "var(--text-tertiary)", flexShrink: 0 }}>Subject</span>
                  <span style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 500,
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {result.slots.subject}
                  </span>
                  {result.slots.preheader && (
                    <>
                      <span style={{ color: "var(--text-tertiary)", flexShrink: 0 }}>·</span>
                      <span style={{ fontSize: 12, color: "var(--text-tertiary)",
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {result.slots.preheader}
                      </span>
                    </>
                  )}
                </div>
              )}

              {/* Preview / source */}
              <div style={{ flex: 1, minHeight: 0, overflow: "hidden",
                background: previewTab === "source" ? "var(--card-bg)" : "#e8e8e8" }}>
                {previewTab === "preview" ? (
                  <iframe srcDoc={result.html} title="Email preview" sandbox="allow-same-origin"
                    style={{ width: "100%", height: "100%", border: "none", display: "block" }} />
                ) : (
                  <pre style={{ margin: 0, padding: "20px 24px", height: "100%",
                    overflowY: "auto", boxSizing: "border-box",
                    fontSize: 11, lineHeight: 1.7, color: "var(--text-secondary)",
                    fontFamily: "monospace", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                    {result.html}
                  </pre>
                )}
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: "flex", alignItems: "center",
              justifyContent: "center", flexDirection: "column", gap: 18,
              color: "var(--text-tertiary)" }}>
              <div style={{ fontSize: 72, opacity: 0.12 }}>📧</div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 6 }}>
                  {file ? "Ready to convert" : "No document uploaded yet"}
                </div>
                <div style={{ fontSize: 13, color: "var(--text-tertiary)", maxWidth: 360, lineHeight: 1.6 }}>
                  {file
                    ? `Click "Convert to HTML Email" to process ${file.name}`
                    : "Upload a Word, PDF, Excel or CSV file — content is extracted faithfully and rendered as a responsive HTML email."}
                </div>
              </div>
              {file && !loading && (
                <button onClick={handleConvert}
                  style={{ padding: "12px 28px", borderRadius: 12, border: "none",
                    background: "linear-gradient(135deg,#7c3aed,#a855f7)", color: "#fff",
                    fontFamily: "inherit", fontSize: 14, fontWeight: 700, cursor: "pointer",
                    boxShadow: "0 4px 16px rgba(124,58,237,0.35)" }}>
                  Convert to HTML Email
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Send modal ── */}
      {sendOpen && result && (
        <SendModal
          html={result.html}
          slots={result.slots}
          brandName={brandName}
          onClose={() => setSendOpen(false)}
        />
      )}

      <style>{`
        @keyframes ec-spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
