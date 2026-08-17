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

// ── Types ──────────────────────────────────────────────────────────────────────
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

// ── Helpers ────────────────────────────────────────────────────────────────────
function fileTypeBadge(filename: string): string {
  return filename.split(".").pop()?.toUpperCase() ?? "FILE";
}

function formatBytes(bytes: number): string {
  if (bytes < 1024)        return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileIconBg(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  if (ext === "pdf")                                      return "#ef4444";
  if (["docx", "doc"].includes(ext))                      return "#1e40af";
  if (["xlsx", "xls", "csv"].includes(ext))               return "#16a34a";
  if (["jpg", "jpeg", "png", "gif", "webp"].includes(ext)) return "#0891b2";
  if (ext === "pptx")                                      return "#ea580c";
  if (ext === "txt")                                       return "#64748b";
  return "#7c3aed";
}

// ── Icon components ────────────────────────────────────────────────────────────
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
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13"/>
      <polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  );
}

function XIcon({ size = 11 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"/>
      <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  );
}

function Spinner({ size = 14, color = "#fff" }: { size?: number; color?: string }) {
  return (
    <span style={{
      display: "inline-block", width: size, height: size,
      border: `2px solid ${color}33`, borderTopColor: color,
      borderRadius: "50%", animation: "ec-spin 0.7s linear infinite", flexShrink: 0,
    }} />
  );
}

function StepBadge({ n }: { n: number }) {
  return (
    <div style={{
      width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
      background: "linear-gradient(135deg,#7c3aed,#a855f7)",
      display: "flex", alignItems: "center", justifyContent: "center",
      color: "#fff", fontSize: 13, fontWeight: 800,
    }}>
      {n}
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
      style={{
        width: 44, height: 24, borderRadius: 12, cursor: "pointer", flexShrink: 0,
        background: checked ? "#3b82f6" : "var(--card-border)",
        position: "relative", transition: "background 0.2s",
      }}>
      <div style={{
        position: "absolute", top: 2, left: checked ? 22 : 2,
        width: 20, height: 20, borderRadius: "50%",
        background: "#fff", transition: "left 0.2s",
        boxShadow: "0 1px 3px rgba(0,0,0,0.25)",
      }} />
    </div>
  );
}

function CheckIcon({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7 10 12 15 17 10"/>
      <line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
  );
}

function ExternalIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
      <polyline points="15 3 21 3 21 9"/>
      <line x1="10" y1="14" x2="21" y2="3"/>
    </svg>
  );
}

function FullscreenIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 3 21 3 21 9"/>
      <polyline points="9 21 3 21 3 15"/>
      <line x1="21" y1="3" x2="14" y2="10"/>
      <line x1="3" y1="21" x2="10" y2="14"/>
    </svg>
  );
}

function ExitFullscreenIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 14 10 14 10 20"/>
      <polyline points="20 10 14 10 14 4"/>
      <line x1="10" y1="14" x2="3" y2="21"/>
      <line x1="21" y1="3" x2="14" y2="10"/>
    </svg>
  );
}

function FileDocIcon({ color }: { color: string }) {
  return (
    <svg width="30" height="36" viewBox="0 0 30 36" fill="none" style={{ flexShrink: 0 }}>
      <path d="M0 4C0 1.8 1.8 0 4 0H18L30 12V32C30 34.2 28.2 36 26 36H4C1.8 36 0 34.2 0 32V4Z" fill={color} />
      <path d="M18 0L30 12H22C19.8 12 18 10.2 18 8V0Z" fill="rgba(255,255,255,0.3)" />
    </svg>
  );
}

// ── Send modal ─────────────────────────────────────────────────────────────────
function SendModal({ html, slots, brandName, onClose }: {
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
    setSending(true); setSendError(null);
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

  const handleSendNow = () => { setForm(f => ({ ...f, schedule_time: "" })); doSend({ schedule_time: "" }); };
  const inputSt: React.CSSProperties = {
    width: "100%", padding: "9px 12px", borderRadius: 8,
    border: "1px solid var(--card-border)",
    background: "var(--page-bg)", color: "var(--text-primary)",
    fontFamily: "inherit", fontSize: 13, boxSizing: "border-box", outline: "none",
  };
  const lbl = (txt: string, req = false) => (
    <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
      {txt}{req && <span style={{ color: "#ef4444", marginLeft: 3 }}>*</span>}
    </label>
  );
  const canSend = !!form.list_id && !!form.subject.trim() && !!form.reply_to.trim();

  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 200, background: "rgba(0,0,0,0.55)", backdropFilter: "blur(4px)" }} />
      <div style={{ position: "fixed", inset: 0, zIndex: 201, display: "flex", alignItems: "center", justifyContent: "center", padding: 24, pointerEvents: "none" }}>
        <div onClick={e => e.stopPropagation()} style={{
          width: "100%", maxWidth: 520, borderRadius: 18,
          background: "var(--card-bg)", border: "1px solid var(--card-border)",
          boxShadow: "0 24px 64px rgba(0,0,0,0.35)", pointerEvents: "auto", overflow: "hidden",
        }}>
          <div style={{ padding: "22px 28px 20px", borderBottom: "1px solid var(--card-border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 38, height: 38, borderRadius: 10, flexShrink: 0, background: "linear-gradient(135deg,#7c3aed,#a855f7)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <SendIcon />
              </div>
              <div>
                <div style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>Send via Mailchimp</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 1 }}>Combined HTML email will be sent as a campaign</div>
              </div>
            </div>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", padding: 4, borderRadius: 6, fontSize: 18, lineHeight: 1 }}>×</button>
          </div>

          {sendSuccess ? (
            <div style={{ padding: "40px 28px", textAlign: "center" }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", marginBottom: 8 }}>
                {sendSuccess.status === "scheduled" ? "Campaign Scheduled" : "Campaign Sent!"}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 6 }}>
                Mailchimp campaign ID: <code style={{ fontSize: 12, background: "var(--page-bg)", padding: "2px 6px", borderRadius: 4 }}>{sendSuccess.campaign_id}</code>
              </div>
              <div style={{ fontSize: 13, color: "var(--text-tertiary)", marginBottom: 28 }}>
                {sendSuccess.status === "scheduled" ? `Scheduled for ${form.schedule_time}` : "The email is on its way to your audience."}
              </div>
              <button onClick={onClose} style={{ padding: "10px 28px", borderRadius: 10, border: "none", background: "linear-gradient(135deg,#7c3aed,#a855f7)", color: "#fff", fontFamily: "inherit", fontSize: 14, fontWeight: 700, cursor: "pointer" }}>
                Done
              </button>
            </div>
          ) : (
            <div style={{ padding: "24px 28px", display: "flex", flexDirection: "column", gap: 18 }}>
              <div>
                {lbl("Mailchimp Audience", true)}
                {audiencesLoading ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", borderRadius: 8, border: "1px solid var(--card-border)", background: "var(--page-bg)", color: "var(--text-tertiary)", fontSize: 13 }}>
                    <Spinner size={13} color="var(--text-tertiary)" />Loading audiences…
                  </div>
                ) : audiencesError ? (
                  <div style={{ padding: "9px 12px", borderRadius: 8, fontSize: 13, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)", color: "#ef4444" }}>
                    {audiencesError} — check your MAILCHIMP_API_KEY
                  </div>
                ) : (
                  <select value={form.list_id} onChange={e => setForm(f => ({ ...f, list_id: e.target.value }))}
                    style={{ ...inputSt, appearance: "none", cursor: "pointer" }}>
                    <option value="">Select an audience…</option>
                    {audiences.map(a => <option key={a.id} value={a.id}>{a.name} ({a.member_count.toLocaleString()} contacts)</option>)}
                  </select>
                )}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>{lbl("Subject Line", true)}<input type="text" value={form.subject} onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} placeholder="Email subject" style={inputSt} /></div>
                <div>{lbl("Preheader Text")}<input type="text" value={form.preview_text} onChange={e => setForm(f => ({ ...f, preview_text: e.target.value }))} placeholder="Preview text…" style={inputSt} /></div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>{lbl("From Name")}<input type="text" value={form.from_name} onChange={e => setForm(f => ({ ...f, from_name: e.target.value }))} placeholder="e.g. Barclays" style={inputSt} /></div>
                <div>{lbl("Reply-to Email", true)}<input type="email" value={form.reply_to} onChange={e => setForm(f => ({ ...f, reply_to: e.target.value }))} placeholder="verified@yourdomain.com" style={inputSt} /></div>
              </div>
              <div>
                {lbl("Schedule Send (optional)")}
                <input type="datetime-local" value={form.schedule_time}
                  onChange={e => setForm(f => ({ ...f, schedule_time: e.target.value ? new Date(e.target.value).toISOString() : "" }))}
                  style={inputSt} />
                <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 5 }}>Leave empty to send immediately.</div>
              </div>
              {sendError && (
                <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)", borderRadius: 9, padding: "12px 14px" }}>
                  <div style={{ fontSize: 13, color: "#ef4444", marginBottom: form.schedule_time && /paid|schedule|plan|403/i.test(sendError) ? 10 : 0 }}>{sendError}</div>
                  {form.schedule_time && /paid|schedule|plan|403/i.test(sendError) && (
                    <button onClick={handleSendNow} disabled={sending}
                      style={{ padding: "7px 16px", borderRadius: 8, border: "none", background: "#7c3aed", color: "#fff", fontFamily: "inherit", fontSize: 12, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
                      <SendIcon />Send immediately instead
                    </button>
                  )}
                </div>
              )}
              <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", paddingTop: 4, borderTop: "1px solid var(--card-border)" }}>
                <button onClick={onClose} style={{ padding: "9px 20px", borderRadius: 9, cursor: "pointer", fontFamily: "inherit", fontSize: 13, fontWeight: 600, border: "1px solid var(--card-border)", background: "var(--card-bg)", color: "var(--text-primary)" }}>
                  Cancel
                </button>
                <button onClick={() => doSend()} disabled={!canSend || sending}
                  style={{ padding: "9px 22px", borderRadius: 9, cursor: canSend && !sending ? "pointer" : "not-allowed", fontFamily: "inherit", fontSize: 13, fontWeight: 700, border: "none", background: canSend && !sending ? "linear-gradient(135deg,#7c3aed,#a855f7)" : "var(--card-border)", color: canSend && !sending ? "#fff" : "var(--text-tertiary)", display: "flex", alignItems: "center", gap: 8, boxShadow: canSend && !sending ? "0 2px 10px rgba(124,58,237,0.3)" : "none", transition: "all 0.15s" }}>
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

// ── Step card wrapper ──────────────────────────────────────────────────────────
function StepCard({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: "var(--card-bg)", border: "1px solid var(--card-border)",
      borderRadius: 16, padding: "20px 20px 18px", ...style,
    }}>
      {children}
    </div>
  );
}

// ── Select dropdown ────────────────────────────────────────────────────────────
function SelectField({ label, value, onChange, options }: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <div>
      <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
        {label}
      </label>
      <div style={{ position: "relative" }}>
        <select
          value={value}
          onChange={e => onChange(e.target.value)}
          style={{
            width: "100%", padding: "9px 32px 9px 11px", borderRadius: 9,
            border: "1px solid var(--card-border)",
            background: "var(--page-bg)", color: "var(--text-primary)",
            fontFamily: "inherit", fontSize: 13, appearance: "none",
            cursor: "pointer", outline: "none",
          }}>
          {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <div style={{
          position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)",
          pointerEvents: "none", color: "var(--text-tertiary)",
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function EmailConverter() {
  const [files,        setFiles]        = useState<File[]>([]);
  const [isDragging,   setIsDragging]   = useState(false);
  const [brandName,    setBrandName]    = useState("");
  const [brandColor,   setBrandColor]   = useState("#0055A4");
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState<string | null>(null);
  const [result,       setResult]       = useState<ConvertResult | null>(null);
  const [sendOpen,     setSendOpen]     = useState(false);
  const [editedSlots,  setEditedSlots]  = useState<Slots | null>(null);
  const [regen,        setRegen]        = useState(false);
  const [templateMode, setTemplateMode] = useState("auto");
  const [imageHandling, setImageHandling] = useState("smart");
  const [useRag,       setUseRag]       = useState(true);
  const [fullscreen,   setFullscreen]   = useState(false);
  const [editOpen,     setEditOpen]     = useState(false);

  const fileRef      = useRef<HTMLInputElement>(null);
  const colorInputRef = useRef<HTMLInputElement>(null);

  const totalSize = files.reduce((s, f) => s + f.size, 0);

  const addFiles = useCallback((incoming: FileList | null) => {
    if (!incoming?.length) return;
    const newFiles = Array.from(incoming);
    setFiles(prev => {
      const existing = new Set(prev.map(f => `${f.name}:${f.size}`));
      return [...prev, ...newFiles.filter(f => !existing.has(`${f.name}:${f.size}`))];
    });
    setResult(null); setError(null); setEditedSlots(null);
    for (const f of newFiles) {
      const lower = f.name.toLowerCase();
      for (const p of BRAND_PRESETS) {
        if (lower.includes(p.id.toLowerCase())) { setBrandName(p.label); setBrandColor(p.color); break; }
      }
    }
  }, []);

  const removeFile = useCallback((idx: number) => {
    setFiles(prev => prev.filter((_, i) => i !== idx));
    setResult(null); setError(null); setEditedSlots(null);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setIsDragging(false); addFiles(e.dataTransfer.files);
  }, [addFiles]);

  const handleConvert = async () => {
    if (!files.length || loading) return;
    setLoading(true); setError(null);
    try {
      const form = new FormData();
      for (const f of files) form.append("files", f);
      form.append("brand_name",    brandName);
      form.append("brand_color",   brandColor);
      form.append("use_rag",       String(useRag));
      form.append("use_vision",    String(imageHandling === "smart"));
      const res = await fetch(`${API_BASE_PUB}/convert-email`, { method: "POST", body: form });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as any).detail ?? `Server error ${res.status}`);
      }
      const data = await res.json();
      setResult(data);
      setEditedSlots({ ...data.slots });
      setEditOpen(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Conversion failed — please try again");
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async () => {
    if (!editedSlots || regen) return;
    setRegen(true); setError(null);
    try {
      const res = await fetch(`${API_BASE_PUB}/render-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slots: editedSlots, brand_name: brandName, brand_color: brandColor }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as any).detail ?? `Server error ${res.status}`);
      }
      const { html } = await res.json();
      setResult(prev => prev ? { ...prev, html, slots: editedSlots! } : prev);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Regeneration failed");
    } finally {
      setRegen(false);
    }
  };

  const updateSlot = (key: keyof Slots, value: string) => {
    setEditedSlots(prev => {
      if (!prev) return prev;
      if (key === "body") return { ...prev, body: value.split("\n").filter(s => s.trim()) };
      return { ...prev, [key]: value };
    });
  };

  const handleDownload = () => {
    if (!result) return;
    const blob = new Blob([result.html], { type: "text/html" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url;
    a.download = (result.file_count > 1 ? "combined-email" : result.filename.replace(/\.[^.]+$/, "")) + ".html";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePreviewNewTab = () => {
    if (!result) return;
    const blob = new Blob([result.html], { type: "text/html" });
    const url  = URL.createObjectURL(blob);
    window.open(url, "_blank", "noopener");
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  };

  const hasFiles  = files.length > 0;
  const inputBase: React.CSSProperties = {
    width: "100%", padding: "9px 11px", borderRadius: 9,
    border: "1px solid var(--card-border)",
    background: "var(--page-bg)", color: "var(--text-primary)",
    fontFamily: "inherit", fontSize: 13, boxSizing: "border-box", outline: "none",
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--page-bg)" }}>

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div style={{
        padding: "16px 28px", borderBottom: "1px solid var(--card-border)",
        flexShrink: 0, background: "var(--card-bg)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 11, flexShrink: 0,
            background: "linear-gradient(135deg,#7c3aed,#a855f7)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 14px rgba(124,58,237,0.35)",
          }}>
            <MailIcon />
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: 18, fontWeight: 800, letterSpacing: "-0.03em", color: "var(--text-primary)" }}>
              Email Converter
            </h1>
            <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
              Upload one or more files — all content is merged into a single branded HTML email.
            </p>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button style={{
            padding: "7px 14px", borderRadius: 8, cursor: "pointer",
            fontFamily: "inherit", fontSize: 12, fontWeight: 600,
            border: "1px solid var(--card-border)", background: "var(--card-bg)",
            color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 6,
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            Help
          </button>
          <button style={{
            padding: "7px 14px", borderRadius: 8, cursor: "pointer",
            fontFamily: "inherit", fontSize: 12, fontWeight: 600,
            border: "1px solid var(--card-border)", background: "var(--card-bg)",
            color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 6,
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            Conversion History
          </button>
        </div>
      </div>

      {/* ── Two-panel body ───────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden", minHeight: 0 }}>

        {/* ── Left panel: steps ─────────────────────────────────────────────── */}
        <div style={{
          width: 420, flexShrink: 0, borderRight: "1px solid var(--card-border)",
          overflowY: "auto", display: "flex", flexDirection: "column", gap: 0,
        }}>
          <div style={{ padding: "20px 20px 0", display: "flex", flexDirection: "column", gap: 14 }}>

            {/* ── Step 1: Upload Files ─────────────────────────────────────── */}
            <StepCard>
              {/* Header */}
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                <StepBadge n={1} />
                <span style={{ flex: 1, fontSize: 15, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
                  Upload Files
                </span>
                {hasFiles && (
                  <button
                    onClick={() => fileRef.current?.click()}
                    style={{
                      padding: "5px 12px", borderRadius: 7, cursor: "pointer",
                      fontFamily: "inherit", fontSize: 12, fontWeight: 600,
                      border: "1px solid var(--card-border)", background: "var(--page-bg)",
                      color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 5,
                    }}>
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                    </svg>
                    Add more files
                  </button>
                )}
              </div>
              <input ref={fileRef} type="file" accept={ACCEPTED_TYPES} multiple
                style={{ display: "none" }} onChange={e => addFiles(e.target.files)} />

              {/* Drop zone (when empty) */}
              {!hasFiles && (
                <div
                  role="button" tabIndex={0}
                  onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={onDrop}
                  onClick={() => fileRef.current?.click()}
                  onKeyDown={e => e.key === "Enter" && fileRef.current?.click()}
                  style={{
                    border: `2px dashed ${isDragging ? "#7c3aed" : "var(--card-border)"}`,
                    borderRadius: 12, padding: "28px 16px", textAlign: "center",
                    cursor: "pointer", userSelect: "none",
                    background: isDragging ? "rgba(124,58,237,0.06)" : "var(--page-bg)",
                    transition: "all 0.18s", outline: "none",
                  }}>
                  <div style={{ fontSize: 28, marginBottom: 10, opacity: 0.5 }}>📂</div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                    Drop files here
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 12 }}>
                    or click to browse
                  </div>
                  <div style={{ fontSize: 11, color: "#7c3aed", background: "rgba(124,58,237,0.08)",
                    borderRadius: 20, padding: "3px 12px", display: "inline-block",
                    border: "1px solid rgba(124,58,237,0.2)" }}>
                    Word · PDF · Excel · CSV · TXT · PPTX · JPG · PNG
                  </div>
                </div>
              )}

              {/* Drop overlay when dragging onto file list */}
              {hasFiles && isDragging && (
                <div
                  onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={onDrop}
                  style={{
                    border: "2px dashed #7c3aed", borderRadius: 10,
                    padding: "12px", textAlign: "center",
                    background: "rgba(124,58,237,0.06)", fontSize: 13,
                    color: "#7c3aed", fontWeight: 600, marginBottom: 10,
                  }}>
                  Drop to add files
                </div>
              )}

              {/* File list */}
              {hasFiles && (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {files.map((f, i) => (
                    <div key={`${f.name}-${f.size}-${i}`}
                      style={{
                        display: "flex", alignItems: "center", gap: 12,
                        padding: "10px 12px", borderRadius: 10,
                        background: "var(--page-bg)", border: "1px solid var(--card-border)",
                      }}>
                      <FileDocIcon color={fileIconBg(f.name)} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)",
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {f.name}
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 3 }}>
                          <span style={{
                            fontSize: 10, fontWeight: 700, letterSpacing: ".05em",
                            textTransform: "uppercase", color: "var(--text-primary)",
                            background: "var(--card-border)", borderRadius: 4, padding: "1px 5px",
                          }}>
                            {fileTypeBadge(f.name)}
                          </span>
                          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                            {formatBytes(f.size)}
                          </span>
                        </div>
                      </div>
                      <button onClick={() => removeFile(i)}
                        style={{ flexShrink: 0, width: 24, height: 24, borderRadius: 6, border: "none",
                          cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                          background: "rgba(239,68,68,0.08)", color: "#ef4444" }}>
                        <XIcon />
                      </button>
                    </div>
                  ))}

                  {/* Status bar */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "8px 4px 2px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#22c55e", fontWeight: 600 }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                      </svg>
                      {files.length} file{files.length !== 1 ? "s" : ""} uploaded successfully
                    </div>
                    <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                      Total size: {formatBytes(totalSize)}
                    </span>
                  </div>
                </div>
              )}
            </StepCard>

            {/* ── Step 2: Brand Settings ───────────────────────────────────── */}
            <StepCard>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18 }}>
                <StepBadge n={2} />
                <span style={{ flex: 1, fontSize: 15, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
                  Brand Settings
                </span>
                <span style={{ fontSize: 11, color: "var(--text-tertiary)", background: "var(--page-bg)",
                  border: "1px solid var(--card-border)", borderRadius: 99, padding: "2px 9px", fontWeight: 500 }}>
                  Optional
                </span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 16 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
                    Brand name
                  </label>
                  <input type="text" value={brandName} placeholder="e.g. Barclays"
                    onChange={e => setBrandName(e.target.value)} style={inputBase} />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
                    Brand colour
                  </label>
                  <div style={{ display: "flex", gap: 8 }}>
                    <div style={{
                      width: 38, height: 38, borderRadius: 8, cursor: "pointer",
                      background: brandColor, border: "1px solid var(--card-border)", flexShrink: 0,
                      position: "relative", overflow: "hidden",
                    }} onClick={() => colorInputRef.current?.click()}>
                      <input ref={colorInputRef} type="color" value={brandColor}
                        onChange={e => setBrandColor(e.target.value)}
                        style={{ position: "absolute", inset: 0, opacity: 0, width: "100%", height: "100%", cursor: "pointer" }} />
                    </div>
                    <input type="text" value={brandColor}
                      onChange={e => { if (/^#[0-9A-Fa-f]{0,6}$/.test(e.target.value)) setBrandColor(e.target.value); }}
                      style={{ ...inputBase, fontFamily: "monospace", width: "auto", flex: 1 }} />
                  </div>
                </div>
              </div>

              {/* Colour swatches */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {BRAND_PRESETS.map(p => (
                  <button key={p.id} title={p.label}
                    onClick={() => { setBrandName(p.label); setBrandColor(p.color); }}
                    style={{
                      width: 28, height: 28, borderRadius: "50%", padding: 0, cursor: "pointer",
                      background: p.color, border: brandColor === p.color
                        ? "2.5px solid var(--text-primary)" : "2px solid transparent",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      transition: "border 0.15s",
                    }}>
                    {brandColor === p.color && <CheckIcon size={11} />}
                  </button>
                ))}
                <button title="Custom colour" onClick={() => colorInputRef.current?.click()}
                  style={{
                    width: 28, height: 28, borderRadius: "50%", padding: 0, cursor: "pointer",
                    background: "var(--page-bg)", border: "1.5px dashed var(--card-border)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: "var(--text-tertiary)", fontSize: 16, fontWeight: 400,
                  }}>
                  +
                </button>
              </div>
            </StepCard>

            {/* ── Step 3: Conversion Options ───────────────────────────────── */}
            <StepCard>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18 }}>
                <StepBadge n={3} />
                <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
                  Conversion Options
                </span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 16 }}>
                <SelectField
                  label="Preferred template"
                  value={templateMode}
                  onChange={setTemplateMode}
                  options={[
                    { value: "auto",       label: "Auto select (recommended)" },
                    { value: "hero",       label: "Hero (image-led)" },
                    { value: "text_first", label: "Text First" },
                    { value: "product",    label: "Product / E-commerce" },
                  ]}
                />
                <SelectField
                  label="Image text handling"
                  value={imageHandling}
                  onChange={setImageHandling}
                  options={[
                    { value: "smart", label: "Smart (recommended)" },
                    { value: "basic", label: "Basic" },
                  ]}
                />
              </div>

              {/* RAG toggle */}
              <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "12px 14px", borderRadius: 10,
                background: "var(--page-bg)", border: "1px solid var(--card-border)",
              }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                    Use brand &amp; campaign knowledge (RAG)
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                    Enhances output with brand guidelines and past campaign insights
                  </div>
                </div>
                <Toggle checked={useRag} onChange={setUseRag} />
              </div>
            </StepCard>

            {/* ── Convert button ───────────────────────────────────────────── */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {error && (
                <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)",
                  borderRadius: 10, padding: "11px 14px", fontSize: 13, color: "#ef4444", lineHeight: 1.5 }}>
                  {error}
                </div>
              )}
              <button onClick={handleConvert} disabled={!hasFiles || loading}
                style={{
                  padding: "14px 20px", borderRadius: 12, border: "none",
                  background: hasFiles && !loading
                    ? "linear-gradient(135deg,#7c3aed,#a855f7)" : "var(--card-border)",
                  color: hasFiles && !loading ? "#fff" : "var(--text-tertiary)",
                  fontFamily: "inherit", fontSize: 14, fontWeight: 700,
                  cursor: hasFiles && !loading ? "pointer" : "not-allowed",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: 9,
                  boxShadow: hasFiles && !loading ? "0 4px 20px rgba(124,58,237,0.4)" : "none",
                  transition: "all 0.2s",
                }}>
                {loading ? (
                  <><Spinner /> Converting…</>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                    </svg>
                    {files.length > 1 ? `Convert to HTML Email (${files.length} files)` : "Convert to HTML Email"}
                  </>
                )}
              </button>
              {!loading && (
                <div style={{ textAlign: "center", fontSize: 12, color: "var(--text-tertiary)", display: "flex", alignItems: "center", justifyContent: "center", gap: 5 }}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                  </svg>
                  Conversion usually takes 15–30 seconds
                </div>
              )}
            </div>

            {/* ── Edit Content (after conversion) ─────────────────────────── */}
            {result && editedSlots && (
              <StepCard style={{ marginBottom: 20 }}>
                <button
                  onClick={() => setEditOpen(o => !o)}
                  style={{
                    width: "100%", background: "none", border: "none", cursor: "pointer",
                    display: "flex", alignItems: "center", gap: 10, padding: 0,
                  }}>
                  <div style={{ width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                    background: "linear-gradient(135deg,#0ea5e9,#38bdf8)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: "#fff", fontSize: 13, fontWeight: 800 }}>✎</div>
                  <span style={{ flex: 1, fontSize: 15, fontWeight: 700, color: "var(--text-primary)",
                    letterSpacing: "-0.02em", textAlign: "left" }}>
                    Edit &amp; Refine Content
                  </span>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                    style={{ transform: editOpen ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}>
                    <polyline points="6 9 12 15 18 9"/>
                  </svg>
                </button>

                {editOpen && (
                  <div style={{ marginTop: 18 }}>
                    {SLOT_META.map(({ key, label, icon }) => {
                      const isBody    = key === "body";
                      const currentVal = isBody
                        ? (editedSlots.body ?? []).join("\n")
                        : String(editedSlots[key] ?? "");
                      return (
                        <div key={key} style={{ marginBottom: 12 }}>
                          <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)",
                            letterSpacing: ".06em", textTransform: "uppercase", display: "block", marginBottom: 5 }}>
                            {icon} {label}
                          </label>
                          {isBody ? (
                            <textarea
                              value={currentVal}
                              onChange={e => updateSlot("body", e.target.value)}
                              rows={Math.max(3, (editedSlots.body ?? []).length + 1)}
                              placeholder="One bullet per line…"
                              style={{ width: "100%", boxSizing: "border-box", padding: "8px 10px",
                                borderRadius: 8, resize: "vertical", border: "1px solid var(--card-border)",
                                background: "var(--page-bg)", color: "var(--text-primary)",
                                fontFamily: "inherit", fontSize: 12, lineHeight: 1.5, outline: "none" }}
                            />
                          ) : (
                            <input type="text" value={currentVal}
                              onChange={e => updateSlot(key as keyof Slots, e.target.value)}
                              style={{ width: "100%", boxSizing: "border-box", padding: "8px 10px",
                                borderRadius: 8, border: "1px solid var(--card-border)",
                                background: "var(--page-bg)", color: "var(--text-primary)",
                                fontFamily: "inherit", fontSize: 12, outline: "none" }}
                            />
                          )}
                        </div>
                      );
                    })}

                    <button onClick={handleRegenerate} disabled={regen}
                      style={{
                        width: "100%", marginTop: 6, padding: "10px 16px", borderRadius: 10, border: "none",
                        background: regen ? "var(--card-border)" : "linear-gradient(135deg,#0ea5e9,#38bdf8)",
                        color: regen ? "var(--text-tertiary)" : "#fff",
                        fontFamily: "inherit", fontSize: 13, fontWeight: 700,
                        cursor: regen ? "not-allowed" : "pointer",
                        display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                        boxShadow: regen ? "none" : "0 2px 10px rgba(14,165,233,0.3)", transition: "all 0.15s",
                      }}>
                      {regen ? <><Spinner color={regen ? "var(--text-tertiary)" : "#fff"} />Regenerating…</> : "↺ Regenerate Email"}
                    </button>
                  </div>
                )}
              </StepCard>
            )}

          </div>
        </div>

        {/* ── Right panel: Preview ──────────────────────────────────────────── */}
        <div style={{
          flex: 1, minWidth: 0, display: "flex", flexDirection: "column",
          ...(fullscreen ? {
            position: "fixed", inset: 0, zIndex: 300,
            background: "var(--page-bg)",
          } : {}),
        }}>

          {/* Preview header */}
          <div style={{
            padding: "14px 24px", borderBottom: "1px solid var(--card-border)",
            flexShrink: 0, background: "var(--card-bg)",
            display: "flex", alignItems: "center", justifyContent: "space-between",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <StepBadge n={4} />
              <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
                Preview
              </span>
              {result && (
                <span style={{
                  display: "inline-flex", alignItems: "center", gap: 5,
                  fontSize: 11, fontWeight: 700, color: "#16a34a",
                  background: "rgba(22,163,74,0.1)", borderRadius: 99, padding: "3px 10px",
                  border: "1px solid rgba(22,163,74,0.25)",
                }}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                  Ready
                </span>
              )}
            </div>
            {result && (
              <button
                onClick={() => setFullscreen(f => !f)}
                style={{
                  padding: "6px 12px", borderRadius: 8, cursor: "pointer",
                  fontFamily: "inherit", fontSize: 12, fontWeight: 600,
                  border: "1px solid var(--card-border)", background: "var(--card-bg)",
                  color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 6,
                }}>
                {fullscreen ? <ExitFullscreenIcon /> : <FullscreenIcon />}
                {fullscreen ? "Exit Fullscreen" : "Fullscreen"}
              </button>
            )}
          </div>

          {result ? (
            <>
              {/* Subject / Preheader bar */}
              {(result.slots.subject || result.slots.preheader) && (
                <div style={{
                  padding: "10px 24px", borderBottom: "1px solid var(--card-border)",
                  flexShrink: 0, background: "var(--card-bg)",
                  display: "flex", flexDirection: "column", gap: 3,
                }}>
                  {result.slots.subject && (
                    <div style={{ display: "flex", alignItems: "baseline", gap: 7, fontSize: 13 }}>
                      <span style={{ fontWeight: 700, color: "var(--text-secondary)", flexShrink: 0 }}>Subject:</span>
                      <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{result.slots.subject}</span>
                    </div>
                  )}
                  {result.slots.preheader && (
                    <div style={{ display: "flex", alignItems: "baseline", gap: 7, fontSize: 12 }}>
                      <span style={{ fontWeight: 600, color: "var(--text-tertiary)", flexShrink: 0 }}>Preheader:</span>
                      <span style={{ color: "var(--text-secondary)" }}>{result.slots.preheader}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Iframe preview */}
              <div style={{ flex: 1, minHeight: 0, overflow: "hidden", background: "#e8e8e8" }}>
                <iframe
                  srcDoc={result.html}
                  title="Email preview"
                  sandbox="allow-same-origin"
                  style={{ width: "100%", height: "100%", border: "none", display: "block" }}
                />
              </div>

              {/* Action bar */}
              <div style={{
                padding: "14px 24px", borderTop: "1px solid var(--card-border)",
                flexShrink: 0, background: "var(--card-bg)",
                display: "flex", gap: 10, alignItems: "center",
              }}>
                <button onClick={handleDownload}
                  style={{
                    padding: "9px 18px", borderRadius: 9, cursor: "pointer",
                    fontFamily: "inherit", fontSize: 13, fontWeight: 600,
                    border: "1px solid var(--card-border)", background: "var(--card-bg)",
                    color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 7,
                  }}>
                  <DownloadIcon /> Download HTML
                </button>
                <button onClick={handlePreviewNewTab}
                  style={{
                    padding: "9px 18px", borderRadius: 9, cursor: "pointer",
                    fontFamily: "inherit", fontSize: 13, fontWeight: 600,
                    border: "1px solid var(--card-border)", background: "var(--card-bg)",
                    color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 7,
                  }}>
                  <ExternalIcon /> Preview in new tab
                </button>
                <button onClick={() => setSendOpen(true)}
                  style={{
                    padding: "9px 20px", borderRadius: 9, cursor: "pointer",
                    fontFamily: "inherit", fontSize: 13, fontWeight: 700, border: "none",
                    background: "linear-gradient(135deg,#7c3aed,#a855f7)", color: "#fff",
                    display: "flex", alignItems: "center", gap: 7,
                    boxShadow: "0 2px 10px rgba(124,58,237,0.3)",
                  }}>
                  <SendIcon /> Send to Mailchimp
                </button>
              </div>
            </>
          ) : (
            /* Empty state */
            <div style={{
              flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
              flexDirection: "column", gap: 16, color: "var(--text-tertiary)", padding: 48,
            }}>
              <div style={{ fontSize: 80, opacity: 0.1 }}>📧</div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 8 }}>
                  {hasFiles ? "Ready to convert" : "No files uploaded yet"}
                </div>
                <div style={{ fontSize: 13, color: "var(--text-tertiary)", maxWidth: 380, lineHeight: 1.7 }}>
                  {hasFiles
                    ? `${files.length} file${files.length !== 1 ? "s" : ""} selected. Click "Convert to HTML Email" to build your email.`
                    : "Upload any combination of Word docs, PDFs, spreadsheets, images, or text files — all content is merged into one responsive HTML email."}
                </div>
                {!hasFiles && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", marginTop: 20 }}>
                    {[["📄","DOCX"],["📋","PDF"],["📊","XLSX"],["📊","CSV"],["🖼","JPG"],["🖼","PNG"],["📝","TXT"],["📺","PPTX"]].map(([icon, label]) => (
                      <span key={label} style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12, fontWeight: 600, padding: "5px 12px", borderRadius: 8, background: "var(--card-bg)", border: "1px solid var(--card-border)", color: "var(--text-secondary)" }}>
                        {icon} {label}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Send modal ── */}
      {sendOpen && result && (
        <SendModal html={result.html} slots={result.slots} brandName={brandName} onClose={() => setSendOpen(false)} />
      )}

      <style>{`@keyframes ec-spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
