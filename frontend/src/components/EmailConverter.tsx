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
  file_count:  number;
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

const ACCEPTED_TYPES = ".docx,.doc,.pdf,.xlsx,.xls,.csv,.txt,.pptx,.jpg,.jpeg,.png,.gif,.webp";
const ACCEPTED_LABEL = "Word · PDF · Excel · CSV · TXT · PPTX · JPG · PNG";

// ── File type helpers ──────────────────────────────────────────────────────────
function fileTypeIcon(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  if (["jpg", "jpeg", "png", "gif", "webp"].includes(ext)) return "🖼";
  if (["xlsx", "xls", "csv"].includes(ext))                 return "📊";
  if (["docx", "doc"].includes(ext))                        return "📄";
  if (ext === "pdf")                                         return "📋";
  if (ext === "pptx")                                        return "📺";
  if (ext === "txt")                                         return "📝";
  return "📁";
}

function fileTypeBadge(filename: string): string {
  const ext = filename.split(".").pop()?.toUpperCase() ?? "FILE";
  return ext;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024)       return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ── Icons ──────────────────────────────────────────────────────────────────────
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

function XIcon({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"/>
      <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19"/>
      <line x1="5" y1="12" x2="19" y2="12"/>
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

  const handleSend    = () => doSend();
  const handleSendNow = () => { setForm(f => ({ ...f, schedule_time: "" })); doSend({ schedule_time: "" }); };

  const inputSt: React.CSSProperties = {
    width: "100%", padding: "9px 12px", borderRadius: 8,
    border: "1px solid var(--card-border)",
    background: "var(--page-bg)", color: "var(--text-primary)",
    fontFamily: "inherit", fontSize: 13, boxSizing: "border-box" as const, outline: "none",
  };
  const lbl = (txt: string, required = false) => (
    <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)",
      display: "block", marginBottom: 6 }}>
      {txt}{required && <span style={{ color: "#ef4444", marginLeft: 3 }}>*</span>}
    </label>
  );

  const canSend = !!form.list_id && !!form.subject.trim() && !!form.reply_to.trim();

  return (
    <>
      <div onClick={onClose} style={{
        position: "fixed" as const, inset: 0, zIndex: 200,
        background: "rgba(0,0,0,0.55)", backdropFilter: "blur(4px)",
      }} />
      <div style={{
        position: "fixed" as const, inset: 0, zIndex: 201,
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 24, pointerEvents: "none" as const,
      }}>
        <div onClick={e => e.stopPropagation()} style={{
          width: "100%", maxWidth: 520, borderRadius: 18,
          background: "var(--card-bg)", border: "1px solid var(--card-border)",
          boxShadow: "0 24px 64px rgba(0,0,0,0.35)",
          pointerEvents: "auto" as const, overflow: "hidden",
        }}>
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
                  Combined HTML email will be sent as a campaign
                </div>
              </div>
            </div>
            <button onClick={onClose} style={{ background: "none", border: "none",
              cursor: "pointer", color: "var(--text-tertiary)", padding: 4,
              borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 18, lineHeight: 1 }}>×</button>
          </div>

          {sendSuccess ? (
            <div style={{ padding: "40px 28px", textAlign: "center" }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", marginBottom: 8 }}>
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
                color: "#fff", fontFamily: "inherit", fontSize: 14, fontWeight: 700, cursor: "pointer" }}>
                Done
              </button>
            </div>
          ) : (
            <div style={{ padding: "24px 28px", display: "flex", flexDirection: "column", gap: 18 }}>
              <div>
                {lbl("Mailchimp Audience", true)}
                {audiencesLoading ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 8,
                    padding: "9px 12px", borderRadius: 8, border: "1px solid var(--card-border)",
                    background: "var(--page-bg)", color: "var(--text-tertiary)", fontSize: 13 }}>
                    <Spinner size={13} color="var(--text-tertiary)" />Loading audiences…
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

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>
                  {lbl("Subject Line", true)}
                  <input type="text" value={form.subject}
                    onChange={e => setForm(f => ({ ...f, subject: e.target.value }))}
                    placeholder="Email subject" style={inputSt} />
                </div>
                <div>
                  {lbl("Preheader Text")}
                  <input type="text" value={form.preview_text}
                    onChange={e => setForm(f => ({ ...f, preview_text: e.target.value }))}
                    placeholder="Preview text…" style={inputSt} />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>
                  {lbl("From Name")}
                  <input type="text" value={form.from_name}
                    onChange={e => setForm(f => ({ ...f, from_name: e.target.value }))}
                    placeholder="e.g. Barclays" style={inputSt} />
                </div>
                <div>
                  {lbl("Reply-to Email", true)}
                  <input type="email" value={form.reply_to}
                    onChange={e => setForm(f => ({ ...f, reply_to: e.target.value }))}
                    placeholder="verified@yourdomain.com" style={inputSt} />
                </div>
              </div>

              <div>
                {lbl("Schedule Send (optional — leave blank to send now)")}
                <input type="datetime-local" value={form.schedule_time}
                  onChange={e => setForm(f => ({ ...f, schedule_time: e.target.value ? new Date(e.target.value).toISOString() : "" }))}
                  style={inputSt} />
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 5 }}>
                  Leave empty to send immediately. Reply-to must be verified in Mailchimp.
                </div>
              </div>

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
                        background: "#7c3aed", color: "#fff", fontFamily: "inherit",
                        fontSize: 12, fontWeight: 700, cursor: "pointer",
                        display: "flex", alignItems: "center", gap: 6 }}>
                      <SendIcon />Send immediately instead
                    </button>
                  )}
                </div>
              )}

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
                    padding: "9px 22px", borderRadius: 9,
                    cursor: canSend && !sending ? "pointer" : "not-allowed",
                    fontFamily: "inherit", fontSize: 13, fontWeight: 700, border: "none",
                    background: canSend && !sending
                      ? "linear-gradient(135deg,#7c3aed,#a855f7)" : "var(--card-border)",
                    color: canSend && !sending ? "#fff" : "var(--text-tertiary)",
                    display: "flex", alignItems: "center", gap: 8,
                    boxShadow: canSend && !sending ? "0 2px 10px rgba(124,58,237,0.3)" : "none",
                    transition: "all 0.15s",
                  }}>
                  {sending
                    ? <><Spinner />{form.schedule_time ? "Scheduling…" : "Sending…"}</>
                    : <><SendIcon />{form.schedule_time ? "Schedule Campaign" : "Send Now"}</>}
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
  const [files,      setFiles]      = useState<File[]>([]);
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

  const addFiles = useCallback((incoming: FileList | null) => {
    if (!incoming?.length) return;
    const newFiles = Array.from(incoming);
    setFiles(prev => {
      // Deduplicate by name+size
      const existing = new Set(prev.map(f => `${f.name}:${f.size}`));
      const merged   = [...prev, ...newFiles.filter(f => !existing.has(`${f.name}:${f.size}`))];
      return merged;
    });
    setResult(null);
    setError(null);
    // Auto-detect brand from filenames
    for (const f of newFiles) {
      const lower = f.name.toLowerCase();
      for (const p of BRAND_PRESETS) {
        if (lower.includes(p.id.toLowerCase())) {
          setBrandName(p.label);
          setBrandColor(p.color);
          break;
        }
      }
    }
  }, []);

  const removeFile = useCallback((idx: number) => {
    setFiles(prev => prev.filter((_, i) => i !== idx));
    setResult(null);
    setError(null);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    addFiles(e.dataTransfer.files);
  }, [addFiles]);

  const handleConvert = async () => {
    if (!files.length || loading) return;
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      for (const f of files) form.append("files", f);
      form.append("brand_name",  brandName);
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
    a.download = (result.file_count > 1 ? "combined-email" : result.filename.replace(/\.[^.]+$/, "")) + ".html";
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
    fontFamily: "inherit", fontSize: 13, boxSizing: "border-box" as const, outline: "none",
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

  const hasFiles = files.length > 0;

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
              Upload one or more files — all content is merged into a single branded HTML email.
            </p>
          </div>
        </div>
      </div>

      {/* ── Main body ── */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", minHeight: 0 }}>

        {/* ── Left panel ── */}
        <div style={{ width: 320, flexShrink: 0, borderRight: "1px solid var(--card-border)",
          display: "flex", flexDirection: "column", overflowY: "auto" }}>
          <div style={{ padding: "20px 18px", display: "flex", flexDirection: "column", gap: 16 }}>

            {/* ── Dropzone ── */}
            <div
              role="button" tabIndex={0}
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
              onClick={() => fileRef.current?.click()}
              onKeyDown={e => e.key === "Enter" && fileRef.current?.click()}
              style={{
                border: `2px dashed ${isDragging ? "#7c3aed" : hasFiles ? "rgba(124,58,237,0.45)" : "var(--card-border)"}`,
                borderRadius: 14, padding: "22px 16px", textAlign: "center",
                cursor: "pointer", userSelect: "none",
                background: isDragging ? "rgba(124,58,237,0.07)"
                  : hasFiles ? "rgba(124,58,237,0.03)" : "var(--card-bg)",
                transition: "all 0.18s", outline: "none",
              }}>
              <input ref={fileRef} type="file" accept={ACCEPTED_TYPES} multiple
                style={{ display: "none" }} onChange={e => addFiles(e.target.files)} />
              <div style={{ fontSize: 26, marginBottom: 8 }}>
                {hasFiles ? "📎" : "📂"}
              </div>
              {hasFiles ? (
                <>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", marginBottom: 3 }}>
                    {files.length} file{files.length !== 1 ? "s" : ""} ready
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", display: "flex",
                    alignItems: "center", justifyContent: "center", gap: 6 }}>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 4,
                      background: "rgba(124,58,237,0.1)", borderRadius: 99, padding: "2px 9px",
                      border: "1px solid rgba(124,58,237,0.2)", color: "#7c3aed", fontSize: 11, fontWeight: 600 }}>
                      <PlusIcon /> Drop more files
                    </span>
                  </div>
                </>
              ) : (
                <>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                    Drop files here
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 10 }}>
                    or click to browse
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)",
                    background: "rgba(124,58,237,0.08)", borderRadius: 20,
                    padding: "3px 10px", display: "inline-block",
                    border: "1px solid rgba(124,58,237,0.18)", lineHeight: 1.7 }}>
                    {ACCEPTED_LABEL}
                  </div>
                </>
              )}
            </div>

            {/* ── File list ── */}
            {files.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                {files.map((f, i) => (
                  <div key={`${f.name}-${f.size}-${i}`}
                    style={{ display: "flex", alignItems: "center", gap: 10,
                      background: "var(--card-bg)", border: "1px solid var(--card-border)",
                      borderRadius: 10, padding: "9px 12px" }}>
                    <span style={{ fontSize: 20, flexShrink: 0 }}>{fileTypeIcon(f.name)}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)",
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {f.name}
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
                        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: ".06em",
                          textTransform: "uppercase", color: "#7c3aed",
                          background: "rgba(124,58,237,0.1)", borderRadius: 4, padding: "1px 5px" }}>
                          {fileTypeBadge(f.name)}
                        </span>
                        <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                          {formatBytes(f.size)}
                        </span>
                      </div>
                    </div>
                    <button onClick={() => removeFile(i)}
                      title="Remove file"
                      style={{ flexShrink: 0, width: 24, height: 24, borderRadius: 6,
                        border: "none", cursor: "pointer", display: "flex",
                        alignItems: "center", justifyContent: "center",
                        background: "rgba(239,68,68,0.08)", color: "#ef4444",
                        transition: "background 0.15s" }}>
                      <XIcon size={11} />
                    </button>
                  </div>
                ))}

                {files.length > 1 && (
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", textAlign: "center",
                    padding: "4px 0 2px" }}>
                    All {files.length} files will be combined into one email
                  </div>
                )}
              </div>
            )}

            {/* ── Brand settings ── */}
            <div style={{ background: "var(--card-bg)", border: "1px solid var(--card-border)",
              borderRadius: 14, padding: 16 }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: ".07em",
                textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 14 }}>
                Brand settings <span style={{ opacity: 0.5, fontWeight: 400 }}>(optional)</span>
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)",
                  display: "block", marginBottom: 6 }}>Brand name</label>
                <input type="text" value={brandName} placeholder="e.g. Barclays"
                  onChange={e => setBrandName(e.target.value)} style={inputBase} />
              </div>
              <div style={{ marginBottom: 12 }}>
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

            {/* ── Convert button ── */}
            <button onClick={handleConvert} disabled={!hasFiles || loading}
              style={{
                padding: "13px 20px", borderRadius: 12, border: "none",
                background: hasFiles && !loading ? "linear-gradient(135deg,#7c3aed,#a855f7)" : "var(--card-border)",
                color: hasFiles && !loading ? "#fff" : "var(--text-tertiary)",
                fontFamily: "inherit", fontSize: 14, fontWeight: 700,
                cursor: hasFiles && !loading ? "pointer" : "not-allowed",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 9,
                boxShadow: hasFiles && !loading ? "0 4px 18px rgba(124,58,237,0.35)" : "none",
                transition: "all 0.2s",
              }}>
              {loading
                ? <><Spinner /> Converting…</>
                : files.length > 1
                  ? `Combine & Convert (${files.length} files)`
                  : "Convert to HTML Email"}
            </button>

            {error && (
              <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                borderRadius: 10, padding: "12px 14px", fontSize: 13, color: "#ef4444", lineHeight: 1.5 }}>
                {error}
              </div>
            )}

            {/* ── Extracted content summary ── */}
            {result && (
              <div style={{ background: "var(--card-bg)", border: "1px solid var(--card-border)",
                borderRadius: 14, padding: 16 }}>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: ".07em",
                  textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 4 }}>
                  Extracted content
                </div>
                {result.file_count > 1 && (
                  <div style={{ fontSize: 11, color: "#7c3aed", marginBottom: 12, fontWeight: 600 }}>
                    Combined from {result.file_count} files
                  </div>
                )}
                {SLOT_META.map(({ key, label, icon }) => {
                  const val     = result.slots[key];
                  const display = slotValue(key, val);
                  if (!display) return null;
                  return (
                    <div key={key} style={{ marginBottom: 10, paddingBottom: 10,
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
                  <div style={{ marginBottom: 10, paddingBottom: 10, borderBottom: "1px solid var(--card-border)" }}>
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
                flexShrink: 0, background: "var(--card-bg)", flexWrap: "wrap", gap: 10 }}>
                <div style={{ display: "flex", gap: 6,
                  background: "var(--page-bg)", borderRadius: 22, padding: 3,
                  border: "1px solid var(--card-border)" }}>
                  <button onClick={() => setPreviewTab("preview")} style={pill(previewTab === "preview")}>Preview</button>
                  <button onClick={() => setPreviewTab("source")} style={pill(previewTab === "source")}>HTML Source</button>
                </div>
                <div style={{ display: "flex", gap: 9, flexWrap: "wrap" }}>
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
                  display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: ".07em",
                    textTransform: "uppercase", color: "var(--text-tertiary)", flexShrink: 0 }}>Subject</span>
                  <span style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 500 }}>
                    {result.slots.subject}
                  </span>
                  {result.slots.preheader && (
                    <>
                      <span style={{ color: "var(--text-tertiary)", flexShrink: 0 }}>·</span>
                      <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                        {result.slots.preheader}
                      </span>
                    </>
                  )}
                  {result.file_count > 1 && (
                    <span style={{ marginLeft: "auto", fontSize: 11, fontWeight: 700,
                      color: "#7c3aed", background: "rgba(124,58,237,0.1)",
                      borderRadius: 99, padding: "2px 10px",
                      border: "1px solid rgba(124,58,237,0.2)", flexShrink: 0 }}>
                      {result.file_count} sources combined
                    </span>
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
              color: "var(--text-tertiary)", padding: 40 }}>
              <div style={{ fontSize: 72, opacity: 0.12 }}>📧</div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 6 }}>
                  {hasFiles ? "Ready to convert" : "No files uploaded yet"}
                </div>
                <div style={{ fontSize: 13, color: "var(--text-tertiary)", maxWidth: 400, lineHeight: 1.7 }}>
                  {hasFiles
                    ? `${files.length} file${files.length !== 1 ? "s" : ""} selected. Click the button to build the HTML email.`
                    : "Upload any combination of Word docs, PDFs, spreadsheets, images, or text files — all content is merged into one responsive HTML email."}
                </div>

                {/* Format badges */}
                {!hasFiles && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", marginTop: 20 }}>
                    {[
                      ["📄", "DOCX"],["📋", "PDF"],["📊", "XLSX"],["📊", "CSV"],
                      ["🖼", "JPG"],["🖼", "PNG"],["📝", "TXT"],["📺", "PPTX"],
                    ].map(([icon, label]) => (
                      <span key={label} style={{ display: "inline-flex", alignItems: "center", gap: 5,
                        fontSize: 12, fontWeight: 600, padding: "5px 12px", borderRadius: 8,
                        background: "var(--card-bg)", border: "1px solid var(--card-border)",
                        color: "var(--text-secondary)" }}>
                        {icon} {label}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              {hasFiles && !loading && (
                <button onClick={handleConvert}
                  style={{ padding: "12px 28px", borderRadius: 12, border: "none",
                    background: "linear-gradient(135deg,#7c3aed,#a855f7)", color: "#fff",
                    fontFamily: "inherit", fontSize: 14, fontWeight: 700, cursor: "pointer",
                    boxShadow: "0 4px 16px rgba(124,58,237,0.35)" }}>
                  {files.length > 1 ? `Combine & Convert (${files.length} files)` : "Convert to HTML Email"}
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
