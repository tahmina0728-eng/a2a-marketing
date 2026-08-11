import { useState, useEffect } from "react";
import { API_BASE_PUB } from "../../services/briefingApi";
import { STANDALONE_SUPPORTED, POLY_CHANNEL_CFG } from "../../constants/agents";
import { saveToContentHub } from "../../hooks/useContentHub";
import BriefingAgentDashboard from "../briefing/BriefingAgentDashboard";

export default function AgentRunPanel({ agentKey, agentLabel, color, prompt, onPromptChange, onBriefingDone }: {
  agentKey: string; agentLabel: string; color: string;
  prompt: string; onPromptChange: (v: string) => void;
  onBriefingDone?: () => void;
}) {
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [result, setResult] = useState<Record<string, any> | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [activeChannel, setActiveChannel] = useState<string | null>(null);
  const [channelEmail, setChannelEmail] = useState("");
  const [channelStatus, setChannelStatus] = useState<"idle" | "sending" | "done" | "error">("idle");
  const [channelResult, setChannelResult] = useState<Record<string, any> | null>(null);
  const [kvSaveState, setKvSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const [showStandaloneEmailPreview, setShowStandaloneEmailPreview] = useState(false);
  const [saSubject,  setSaSubject]  = useState("");
  const [saHeadline, setSaHeadline] = useState("");
  const [saBody,     setSaBody]     = useState("");
  const [emailLayouts, setEmailLayouts]       = useState<any[]>([]);
  const [emailLayoutBusy, setEmailLayoutBusy] = useState(false);
  const [selectedLayout, setSelectedLayout]   = useState<any | null>(null);
  const [editSubject,  setEditSubject]  = useState("");
  const [editHtml,     setEditHtml]     = useState("");
  const [mcListId,     setMcListId]     = useState("");
  const [mcAudiences,  setMcAudiences]  = useState<{id:string;name:string;member_count:number}[]>([]);
  const [mcSending,    setMcSending]    = useState(false);
  const [mcResult,     setMcResult]     = useState<{status:string;campaign_id?:string} | null>(null);
  const supported = STANDALONE_SUPPORTED.includes(agentKey);
  const [availableBrands, setAvailableBrands] = useState<string[]>([]);
  const [kvBrand,        setKvBrand]        = useState("");
  const [kvImgSz,        setKvImgSz]        = useState("16:9");
  const [kvCampaignType, setKvCampaignType] = useState("");
  useEffect(() => {
    if (!["briefing", "kv", "reel"].includes(agentKey)) return;
    fetch(`${API_BASE_PUB}/brands`).then(r => r.json()).then(d => {
      if (Array.isArray(d?.brands)) setAvailableBrands(d.brands);
    }).catch(() => {});
  }, [agentKey]);

  const handleSaveKvToHub = async () => {
    if (!result?.image_b64) return;
    setKvSaveState("saving");
    try {
      await saveToContentHub({
        kind: "kv", brand: result.brand ?? "", campaignName: "", campaignId: "",
        headline: result.headline ?? "",
        assetDataUrl: `data:image/jpeg;base64,${result.image_b64}`,
      });
      setKvSaveState("saved");
      setTimeout(() => setKvSaveState("idle"), 2500);
    } catch (e) {
      console.error("standalone_kv_save_failed", e);
      setKvSaveState("idle");
    }
  };

  const [reelSaveState, setReelSaveState] = useState<"idle" | "saving" | "saved">("idle");

  const handleSaveReelToHub = async () => {
    if (!result?.video_b64) return;
    setReelSaveState("saving");
    try {
      await saveToContentHub({
        kind: "reel", brand: result.brand ?? "", campaignName: "", campaignId: "",
        headline: result.headline ?? "",
        assetDataUrl: `data:video/mp4;base64,${result.video_b64}`,
      });
      setReelSaveState("saved");
      setTimeout(() => setReelSaveState("idle"), 2500);
    } catch (e) {
      console.error("standalone_reel_save_failed", e);
      setReelSaveState("idle");
    }
  };

  const runWithPrompt = async (p: string) => {
    setStatus("running"); setErrorMsg(""); setResult(null);
    setKvSaveState("idle"); setReelSaveState("idle");
    setActiveChannel(null); setChannelStatus("idle"); setChannelResult(null);
    try {
      const body: Record<string, any> = { prompt: p, duration: tvcDuration };
      if (agentKey === "kv") {
        if (kvBrand) body.brand = kvBrand;
        body.aspect_ratio = kvImgSz;
        if (kvCampaignType) { body.campaign_type = kvCampaignType; body.campaign_id = kvCampaignType; }
      }
      if (agentKey === "reel" && kvBrand) {
        body.brand = kvBrand;
      }
      const res = await fetch(`${API_BASE_PUB}/agents/${agentKey}/run`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `Run failed (${res.status})`);
      setResult(data);
      setStatus("done");
      if (agentKey === "briefing") onBriefingDone?.();
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  };

  const handleRun = () => { if (prompt.trim()) runWithPrompt(prompt.trim()); };
  const handleRegenerate = (refinedPrompt: string) => runWithPrompt(refinedPrompt);

  const handlePublishChannel = async (channel: string) => {
    if (!result?.landing_page_id) return;
    if (channel === "email" && !channelEmail.trim()) return;
    setChannelStatus("sending"); setChannelResult(null);
    try {
      const res = await fetch(`${API_BASE_PUB}/agents/channel/publish`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          page_id:       result.landing_page_id,
          channel,
          to_email:      channelEmail.trim(),
          email_subject: saSubject  || undefined,
          headline:      saHeadline || undefined,
          body:          saBody     || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `Publish failed (${res.status})`);
      setChannelResult(data);
      setChannelStatus(data?.status === "error" ? "error" : "done");
    } catch (e) {
      setChannelResult({ error: e instanceof Error ? e.message : String(e) });
      setChannelStatus("error");
    }
  };

  const AGENT_AGENDA: Record<string, string> = {
    briefing: "What campaign should I brief and validate?",
    strategy: "What campaign strategy should I build?",
    copy:     "What headlines and copy should I write?",
    culture:  "What cultural insights should I research?",
    kv:       "What key visual should I create?",
    reel:     "What campaign reel should I generate?",
    channel:  "How should I adapt this campaign for channels?",
    tvc:      "What TV commercial should I direct and produce?",
  };

  const AGENT_RUNNING_MSG: Record<string, string> = {
    briefing: "Logos is validating your brief and scoring the Fan Truth…",
    strategy: "Helia is building your campaign strategy and big idea…",
    copy:     "Ideon is writing headlines and copy for your campaign…",
    culture:  "Aether is researching cultural trends and audience insights…",
    kv:       "Morphis is generating your key visual with Gemini 3 Pro Image…",
    reel:     "Kinetik is generating your 6-second reel with Veo — this can take 2-5 minutes…",
    channel:  "Poly is adapting your campaign across channels and building the landing page…",
    tvc:             "Director is writing the script and generating each scene with Veo — this takes 8–15 minutes…",
    email_templates: "Mailer is generating 3 email template variations with brand-matched copy and layouts…",
  };

  const [tvcDuration, setTvcDuration] = useState<15|30>(30);

  return (
    <div style={{ marginTop: 20 }}>
      {status === "running" ? (
        <div style={{ textAlign: "center" as const, padding: "32px 16px" }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>
            {agentLabel} is working…
          </div>
          <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6, maxWidth: 320, margin: "0 auto 20px",
            textShadow: "0 1px 4px rgba(255,255,255,0.2)" }}>
            {AGENT_RUNNING_MSG[agentKey] ?? `${agentLabel} is processing your request…`}
          </div>
          <div style={{ display: "flex", justifyContent: "center", gap: 6 }}>
            {[0, 1, 2].map(i => (
              <div key={i} style={{
                width: 8, height: 8, borderRadius: "50%", background: color,
                animation: `pulse-glow 1.2s ${i * 0.2}s ease-in-out infinite`,
              }} />
            ))}
          </div>
        </div>
      ) : status === "done" && agentKey === "briefing" ? null : (
        <>
          <h3 style={{ fontSize: 20, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 10px", lineHeight: 1.3 }}>
            <span style={{ background: `linear-gradient(135deg, ${color}, #6366f1)`,
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
              Hello!
            </span>{" "}
            {AGENT_AGENDA[agentKey] ?? `What would you like ${agentLabel} to do?`}
          </h3>

          {(agentKey === "kv" || agentKey === "reel") && availableBrands.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 7 }}>
                Brand
              </div>
              <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 6 }}>
                {availableBrands.map((b) => (
                  <button key={b} onClick={() => {
                    setKvBrand(kvBrand === b ? "" : b);
                    if (b !== "Barclays") setKvCampaignType("");
                  }}
                    style={{ padding: "5px 13px", borderRadius: 99, fontSize: 11, fontWeight: 700,
                      cursor: "pointer", fontFamily: "inherit", transition: "all 0.15s",
                      border: `1.5px solid ${kvBrand === b ? color : "var(--card-border)"}`,
                      background: kvBrand === b ? `${color}18` : "var(--card-bg-soft)",
                      color: kvBrand === b ? color : "var(--text-secondary)" }}>
                    {b}
                  </button>
                ))}
              </div>
              {kvBrand === "Barclays" && (
                <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" as const }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                    letterSpacing: "0.08em", textTransform: "uppercase" as const, width: "100%", marginBottom: 3 }}>
                    Campaign
                  </div>
                  {["wimbledon"].map(ct => (
                    <button key={ct} onClick={() => setKvCampaignType(kvCampaignType === ct ? "" : ct)}
                      style={{ padding: "5px 13px", borderRadius: 99, fontSize: 11, fontWeight: 700,
                        cursor: "pointer", fontFamily: "inherit", transition: "all 0.15s",
                        border: `1.5px solid ${kvCampaignType === ct ? color : "var(--card-border)"}`,
                        background: kvCampaignType === ct ? `${color}18` : "var(--card-bg-soft)",
                        color: kvCampaignType === ct ? color : "var(--text-secondary)" }}>
                      {ct.charAt(0).toUpperCase() + ct.slice(1)}
                    </button>
                  ))}
                </div>
              )}
              {agentKey === "kv" && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                    letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 6 }}>
                    Image size
                  </div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" as const }}>
                    {["1:1","4:5","16:9","9:16"].map(sz => (
                      <button key={sz} onClick={() => setKvImgSz(sz)}
                        style={{ padding: "5px 13px", borderRadius: 99, fontSize: 11, fontWeight: 700,
                          cursor: "pointer", fontFamily: "inherit", transition: "all 0.15s",
                          border: `1.5px solid ${kvImgSz === sz ? color : "var(--card-border)"}`,
                          background: kvImgSz === sz ? `${color}18` : "var(--card-bg-soft)",
                          color: kvImgSz === sz ? color : "var(--text-secondary)" }}>
                        {sz}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {agentKey === "briefing" && availableBrands.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 7 }}>
                Pick a brand to brief
              </div>
              <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 6 }}>
                {availableBrands.map((b) => {
                  const active = prompt.toLowerCase().includes(b.toLowerCase());
                  return (
                    <button key={b} onClick={() => {
                      const cleaned = prompt.replace(new RegExp(`^${b}[:\\s—-]*`, "i"), "").trim();
                      onPromptChange(`${b} — ${cleaned}`);
                    }}
                      style={{ padding: "5px 13px", borderRadius: 99, fontSize: 11, fontWeight: 700,
                        cursor: "pointer", fontFamily: "inherit", transition: "all 0.15s",
                        border: `1.5px solid ${active ? color : "var(--card-border)"}`,
                        background: active ? `${color}18` : "var(--card-bg-soft)",
                        color: active ? color : "var(--text-secondary)" }}>
                      {b}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {agentKey === "tvc" && (
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)" }}>TVC Duration:</span>
              {([15, 30] as const).map(d => (
                <button key={d} onClick={() => setTvcDuration(d)}
                  style={{ padding: "6px 18px", borderRadius: 99, fontWeight: 700, fontSize: 12,
                    border: `1.5px solid ${tvcDuration === d ? color : "var(--card-border)"}`,
                    background: tvcDuration === d ? `${color}18` : "transparent",
                    color: tvcDuration === d ? color : "var(--text-secondary)",
                    cursor: "pointer" }}>
                  {d}s {d === 15 ? "(3 scenes)" : "(5 scenes)"}
                </button>
              ))}
              <span style={{ fontSize: 11, color: "var(--text-secondary)", marginLeft: 4 }}>
                {tvcDuration === 15 ? "~5–8 min" : "~8–15 min"}
              </span>
            </div>
          )}

          <div style={{
            borderRadius: 16, border: "1px solid var(--card-border)", background: "var(--card-bg)",
            boxShadow: "var(--shadow-sm)", overflow: "hidden",
          }}>
            <textarea value={prompt} onChange={(e) => onPromptChange(e.target.value)}
              rows={1}
              placeholder={agentKey === "briefing"
                ? "Brand name + market + objective — e.g. \"Haleon UK: winter campaign for Sensodyne, targeting adults with sensitive teeth\""
                : "Describe your brand, market, and campaign direction — I'll help you move it forward"}
              style={{ width: "100%", padding: "18px 16px", border: "none", resize: "none" as const,
                background: "transparent", color: "var(--text-primary)", fontFamily: "inherit",
                fontSize: 13, lineHeight: 1.6, outline: "none", boxSizing: "border-box" as const,
                display: "block", minHeight: 58 }} />

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "8px 12px", borderTop: "1px solid var(--card-border)" }}>
              <button style={{ width: 28, height: 28, borderRadius: "50%", border: "1px solid var(--card-border)",
                background: "var(--card-bg-soft)", color: "var(--text-tertiary)", cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 400 }}>
                +
              </button>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <button style={{ width: 32, height: 32, borderRadius: "50%", border: "1px solid var(--card-border)",
                  background: "var(--card-bg-soft)", color: "var(--text-tertiary)", cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>
                  🎤
                </button>
                <button onClick={handleRun} disabled={!supported || !prompt.trim()}
                  style={{
                    width: 32, height: 32, borderRadius: "50%", border: "none",
                    cursor: (!supported || !prompt.trim()) ? "default" : "pointer",
                    opacity: (!supported || !prompt.trim()) ? 0.4 : 1, fontFamily: "inherit",
                    background: `linear-gradient(135deg, ${color}, #6366f1)`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: "white", fontSize: 14, fontWeight: 700,
                  }}>→</button>
              </div>
            </div>
          </div>
        </>
      )}

      {status === "error" && (
        <div style={{ marginTop: 12, fontSize: 12, lineHeight: 1.5, color: "#ef4444" }}>⚠ {errorMsg}</div>
      )}

      {agentKey === "channel" && status === "done" && result?.landing_page_id && (
        <div style={{ marginTop: 16, paddingLeft: 14, borderLeft: `2px solid ${color}40` }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.06em",
            textTransform: "uppercase" as const, marginBottom: 8 }}>Publish to a channel</div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" as const, marginBottom: 10 }}>
            {[
              { key: "landing_page", icon: "🌐", label: "Website" },
              { key: "email",        icon: "📧", label: "Email" },
              { key: "google_ads",   icon: "🔍", label: "Google Ads" },
            ].map((ch) => (
              <button key={ch.key} onClick={() => setActiveChannel(ch.key)}
                style={{
                  display: "flex", alignItems: "center", gap: 6, padding: "7px 14px", borderRadius: 10,
                  border: `1.5px solid ${activeChannel === ch.key ? color : "var(--card-border)"}`,
                  background: activeChannel === ch.key ? `${color}18` : "var(--card-bg-soft)",
                  color: activeChannel === ch.key ? color : "var(--text-secondary)",
                  fontSize: 12, fontWeight: 700, cursor: "pointer", fontFamily: "inherit",
                }}>
                <span>{ch.icon}</span>{ch.label}
              </button>
            ))}
            {[
              { icon: "📸", label: "Instagram" }, { icon: "🎵", label: "TikTok" },
              { icon: "▶️", label: "YouTube" }, { icon: "🏙️", label: "OOH" }, { icon: "📘", label: "Meta Ads" },
            ].map((ch) => (
              <span key={ch.label} title="Not available for standalone runs" style={{
                display: "flex", alignItems: "center", gap: 6, padding: "7px 14px", borderRadius: 10,
                border: "1.5px solid var(--card-border)", background: "transparent",
                color: "var(--text-muted)", fontSize: 12, fontWeight: 600, opacity: 0.45, cursor: "not-allowed",
              }}>
                <span>{ch.icon}</span>{ch.label}
              </span>
            ))}
          </div>

          {activeChannel === "landing_page" && (
            <div style={{ display: "flex", flexDirection: "column" as const, gap: 10 }}>
              {result.image_b64 && (
                <div style={{ borderRadius: 12, overflow: "hidden", position: "relative" as const,
                  border: "1px solid var(--card-border)", boxShadow: "0 4px 16px rgba(0,0,0,0.12)" }}>
                  <img src={`data:image/jpeg;base64,${result.image_b64}`} alt="Landing page hero"
                    style={{ width: "100%", display: "block", maxHeight: 200,
                      objectFit: "cover" as const }} />
                  {result.logo_b64 && (
                    <div style={{ position: "absolute" as const, top: 10, right: 10,
                      background: "rgba(255,255,255,0.92)", backdropFilter: "blur(8px)",
                      borderRadius: 8, padding: "5px 10px",
                      border: "1px solid rgba(255,255,255,0.6)" }}>
                      <img src={`data:image/png;base64,${result.logo_b64}`} alt="Brand logo"
                        style={{ height: 24, objectFit: "contain" as const, display: "block" }} />
                    </div>
                  )}
                  <div style={{ padding: "12px 14px", background: "var(--card-bg)" }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)",
                      marginBottom: 4, lineHeight: 1.3 }}>
                      {result.headline || ""}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                      {result.body ? String(result.body).slice(0, 100) + (String(result.body).length > 100 ? "…" : "") : ""}
                    </div>
                  </div>
                </div>
              )}
              <a href={`${API_BASE_PUB}/agents/landing/${result.landing_page_id}`} target="_blank" rel="noreferrer"
                style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "8px 16px",
                  borderRadius: 9, fontFamily: "inherit", fontSize: 12, fontWeight: 700, color: "white",
                  textDecoration: "none", background: `linear-gradient(135deg, ${color}, #6366f1)`,
                  alignSelf: "flex-start" as const }}>
                🌐 Open landing page ↗
              </a>
            </div>
          )}

          {activeChannel === "email" && (
            <>
              {showStandaloneEmailPreview && (
                <div style={{ position: "fixed" as const, inset: 0, zIndex: 1000,
                  background: "rgba(0,0,0,0.55)", display: "flex", alignItems: "center",
                  justifyContent: "center", padding: 24 }}
                  onClick={e => { if (e.target === e.currentTarget) setShowStandaloneEmailPreview(false); }}>
                  <div style={{ width: "100%", maxWidth: 540, borderRadius: 20,
                    background: "var(--card-bg)", border: "1px solid var(--card-border)",
                    boxShadow: "0 24px 60px rgba(0,0,0,0.35)",
                    display: "flex", flexDirection: "column" as const, maxHeight: "90vh" }}>

                    <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--card-border)",
                      display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
                      <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>📧 Email Preview</div>
                      <button onClick={() => setShowStandaloneEmailPreview(false)}
                        style={{ background: "none", border: "none", cursor: "pointer",
                          fontSize: 20, color: "var(--text-secondary)", lineHeight: 1, padding: 4 }}>✕</button>
                    </div>
                    <div style={{ padding: "14px 24px 0", flexShrink: 0 }}>
                      <label style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
                        textTransform: "uppercase" as const, color: "var(--text-secondary)", display: "block", marginBottom: 5 }}>
                        Subject line
                      </label>
                      <input value={saSubject} onChange={e => setSaSubject(e.target.value)}
                        placeholder="Email subject…"
                        style={{ width: "100%", padding: "9px 13px", borderRadius: 9,
                          border: "1.5px solid var(--card-border)", background: "var(--page-bg)",
                          color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit",
                          outline: "none", boxSizing: "border-box" as const }}
                        onFocus={e => e.currentTarget.style.borderColor = color}
                        onBlur={e => e.currentTarget.style.borderColor = "var(--card-border)"} />
                    </div>

                    <div style={{ overflowY: "auto", flex: 1 }}>
                      <div style={{ margin: "14px 24px", borderRadius: 12, overflow: "hidden",
                        border: "1px solid var(--card-border)", background: "#ffffff" }}>
                        {result?.image_b64 && (
                          <img src={`data:image/jpeg;base64,${result.image_b64}`} alt=""
                            style={{ width: "100%", maxHeight: 260, objectFit: "contain" as const, display: "block", background: "#f8fafc" }} />
                        )}
                        <div style={{ padding: "18px 20px", fontFamily: "Georgia, serif" }}>
                          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em",
                            textTransform: "uppercase" as const, color: "#888", marginBottom: 4, fontFamily: "system-ui" }}>Headline</div>
                          <textarea value={saHeadline} onChange={e => setSaHeadline(e.target.value)} rows={2}
                            style={{ width: "100%", fontSize: 20, fontWeight: 700, color: "#0f172a",
                              fontFamily: "Georgia, serif", border: "1.5px dashed #d0d0e0", borderRadius: 8,
                              background: "#fafafa", padding: "7px 10px", resize: "none" as const,
                              outline: "none", lineHeight: 1.3, boxSizing: "border-box" as const, marginBottom: 10 }}
                            onFocus={e => e.currentTarget.style.borderColor = color}
                            onBlur={e => e.currentTarget.style.borderColor = "#d0d0e0"} />
                          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em",
                            textTransform: "uppercase" as const, color: "#888", marginBottom: 4, fontFamily: "system-ui" }}>Body copy</div>
                          <textarea value={saBody} onChange={e => setSaBody(e.target.value)} rows={4}
                            style={{ width: "100%", fontSize: 13, color: "#374151", lineHeight: 1.7,
                              fontFamily: "Georgia, serif", border: "1.5px dashed #d0d0e0", borderRadius: 8,
                              background: "#fafafa", padding: "7px 10px", resize: "none" as const,
                              outline: "none", boxSizing: "border-box" as const }}
                            onFocus={e => e.currentTarget.style.borderColor = color}
                            onBlur={e => e.currentTarget.style.borderColor = "#d0d0e0"} />
                        </div>
                      </div>
                    </div>

                    <div style={{ padding: "14px 24px", borderTop: "1px solid var(--card-border)",
                      display: "flex", gap: 10, alignItems: "center", flexShrink: 0 }}>
                      <input type="email" placeholder="recipient@email.com" value={channelEmail}
                        onChange={e => setChannelEmail(e.target.value)}
                        style={{ flex: 1, padding: "9px 13px", borderRadius: 9,
                          border: "1.5px solid var(--card-border)", background: "var(--page-bg)",
                          color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit", outline: "none" }} />
                      <button onClick={() => { setShowStandaloneEmailPreview(false); handlePublishChannel("email"); }}
                        disabled={!channelEmail.trim() || channelStatus === "sending"}
                        style={{ padding: "9px 20px", borderRadius: 9, border: "none", fontWeight: 700,
                          fontSize: 13, whiteSpace: "nowrap" as const,
                          cursor: channelEmail.trim() ? "pointer" : "not-allowed",
                          background: channelEmail.trim() ? `linear-gradient(135deg,${color},#6366f1)` : "rgba(124,58,237,0.15)",
                          color: channelEmail.trim() ? "white" : "rgba(124,58,237,0.4)" }}>
                        {channelStatus === "sending" ? "Sending…" : "Send Email →"}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {emailLayouts.length === 0 && !emailLayoutBusy && (
                <button onClick={async () => {
                    setEmailLayoutBusy(true); setSelectedLayout(null); setMcResult(null);
                    try {
                      const res = await fetch(`${API_BASE_PUB}/mailchimp/email-templates`, {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                          prompt: prompt.trim(),
                          brand: result?.brand ?? "",
                        }),
                      });
                      const data = await res.json();
                      if (data.templates) {
                        const kvImage = result?.image_b64
                          ? `data:image/jpeg;base64,${result.image_b64}`
                          : null;
                        const injected = data.templates.map((tpl: any) => ({
                          ...tpl,
                          html: kvImage
                            ? tpl.html.replace(/__KV_IMAGE__/g, kvImage)
                            : tpl.html,
                        }));
                        setEmailLayouts(injected);
                        setEditSubject(data.subject ?? "");
                      }
                      fetch(`${API_BASE_PUB}/mailchimp/audiences`)
                        .then(r => r.json()).then(d => setMcAudiences(d.audiences ?? [])).catch(()=>{});
                    } catch { } finally { setEmailLayoutBusy(false); }
                  }}
                  style={{ padding: "10px 22px", borderRadius: 10, border: "none", fontFamily: "inherit",
                    fontSize: 13, fontWeight: 700, color: "white", cursor: "pointer",
                    background: `linear-gradient(135deg,${color},#6366f1)`,
                    boxShadow: `0 4px 16px ${color}40` }}>
                  ✦ Generate 3 Email Layouts
                </button>
              )}

              {emailLayoutBusy && (
                <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13,
                  color: "var(--text-secondary)" }}>
                  <div style={{ width: 16, height: 16, borderRadius: "50%",
                    border: `2px solid ${color}30`, borderTopColor: color,
                    animation: "spin 1s linear infinite" }} />
                  Generating 3 email layout variations…
                </div>
              )}

              {emailLayouts.length > 0 && !selectedLayout && (
                <div style={{ display: "flex", flexDirection: "column" as const, gap: 10 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color, letterSpacing: ".06em",
                    textTransform: "uppercase" as const }}>
                    Step 1 — Pick a layout
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
                    {emailLayouts.map((tpl: any) => (
                      <div key={tpl.id}
                        onClick={() => { setSelectedLayout(tpl); setEditSubject(tpl.subject ?? editSubject); setEditHtml(tpl.html); }}
                        style={{ borderRadius: 12, overflow: "hidden", cursor: "pointer",
                          border: `2px solid ${color}25`, transition: "all 0.15s",
                          boxShadow: `0 2px 12px ${color}10` }}
                        onMouseEnter={e => (e.currentTarget.style.borderColor = color)}
                        onMouseLeave={e => (e.currentTarget.style.borderColor = `${color}25`)}>
                        <div style={{ padding: "8px 10px", background: `${color}08`,
                          borderBottom: `1px solid ${color}15` }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color }}>{tpl.name}</div>
                          <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>{tpl.layout}</div>
                        </div>
                        <div style={{ position: "relative" as const, height: 180, overflow: "hidden", background: "#f8fafc" }}>
                          <iframe srcDoc={tpl.html} title={tpl.name}
                            style={{ width: "200%", height: "200%", border: "none",
                              transform: "scale(0.5)", transformOrigin: "top left",
                              pointerEvents: "none" as const }} />
                        </div>
                        <div style={{ padding: "8px 10px", textAlign: "center" as const,
                          fontSize: 12, fontWeight: 600, color, background: `${color}06` }}>
                          Select →
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedLayout && (
                <div style={{ display: "flex", flexDirection: "column" as const, gap: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color, letterSpacing: ".06em",
                      textTransform: "uppercase" as const }}>
                      Step 2 — Edit & Send · {selectedLayout.name}
                    </div>
                    <button onClick={() => { setSelectedLayout(null); setMcResult(null); }}
                      style={{ fontSize: 11, color: "var(--text-secondary)", background: "none",
                        border: "none", cursor: "pointer" }}>← Back to layouts</button>
                  </div>

                  <div style={{ borderRadius: 12, overflow: "hidden", border: "1px solid var(--card-border)",
                    boxShadow: "0 4px 20px rgba(0,0,0,0.08)" }}>
                    <iframe srcDoc={editHtml} title="Preview"
                      style={{ width: "100%", height: 320, border: "none", display: "block" }} />
                  </div>

                  <div style={{ display: "flex", flexDirection: "column" as const, gap: 10,
                    padding: 16, borderRadius: 12, background: "var(--card-bg)",
                    border: "1px solid var(--card-border)" }}>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                        textTransform: "uppercase" as const, letterSpacing: ".06em", marginBottom: 5 }}>Subject Line</div>
                      <input value={editSubject} onChange={e => setEditSubject(e.target.value)}
                        style={{ width: "100%", padding: "9px 12px", borderRadius: 8, fontSize: 13,
                          border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                          color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
                          boxSizing: "border-box" as const }} />
                    </div>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                        textTransform: "uppercase" as const, letterSpacing: ".06em", marginBottom: 5 }}>HTML Content (editable)</div>
                      <textarea value={editHtml} onChange={e => setEditHtml(e.target.value)} rows={5}
                        style={{ width: "100%", padding: "9px 12px", borderRadius: 8, fontSize: 11,
                          border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                          color: "var(--text-primary)", fontFamily: "monospace", outline: "none",
                          resize: "vertical" as const, boxSizing: "border-box" as const }} />
                    </div>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                        textTransform: "uppercase" as const, letterSpacing: ".06em", marginBottom: 5 }}>Mailchimp Audience</div>
                      <select value={mcListId} onChange={e => setMcListId(e.target.value)}
                        style={{ width: "100%", padding: "9px 12px", borderRadius: 8, fontSize: 13,
                          border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                          color: "var(--text-primary)", fontFamily: "inherit", outline: "none" }}>
                        <option value="">Select audience…</option>
                        {mcAudiences.map(a => (
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
                      style={{ padding: "9px 18px", borderRadius: 9, border: `1.5px solid ${color}40`,
                        fontSize: 12, fontWeight: 700, color, textDecoration: "none",
                        background: `${color}08` }}>
                      Preview ↗
                    </a>
                    <button disabled={!mcListId || mcSending}
                      onClick={async () => {
                        setMcSending(true); setMcResult(null);
                        try {
                          const r = await fetch(`${API_BASE_PUB}/mailchimp/send`, {
                            method: "POST", headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                              list_id: mcListId, subject: editSubject,
                              html: editHtml, from_name: "CampaignOS",
                              reply_to: "", preview_text: "",
                            }),
                          });
                          const d = await r.json();
                          if (!r.ok) throw new Error(d.detail);
                          setMcResult(d);
                        } catch (e: any) { alert(e.message); }
                        finally { setMcSending(false); }
                      }}
                      style={{ flex: 1, padding: "10px 22px", borderRadius: 9, border: "none",
                        fontSize: 13, fontWeight: 700, color: "white",
                        cursor: mcListId ? "pointer" : "not-allowed",
                        opacity: mcListId ? 1 : 0.4,
                        background: `linear-gradient(135deg,${color},#6366f1)`,
                        boxShadow: mcListId ? `0 4px 16px ${color}35` : "none" }}>
                      🐵 {mcSending ? "Sending via Mailchimp…" : "Send Campaign via Mailchimp"}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          {activeChannel === "google_ads" && (
            <button onClick={() => handlePublishChannel("google_ads")} disabled={channelStatus === "sending"}
              style={{ padding: "8px 16px", borderRadius: 9, border: "none", fontFamily: "inherit",
                fontSize: 12, fontWeight: 700, color: "white", cursor: "pointer",
                background: `linear-gradient(135deg, ${color}, #6366f1)` }}>
              {channelStatus === "sending" ? "Submitting…" : "Submit mock ad"}
            </button>
          )}

          {channelStatus === "done" && channelResult && (
            <div style={{ marginTop: 10, fontSize: 12, lineHeight: 1.6, color: "#10b981" }}>
              ✓ {channelResult.status === "skipped" ? channelResult.reason :
                  channelResult.public_url ? <>Live at <a href={channelResult.public_url} target="_blank" rel="noreferrer" style={{ color: "#10b981" }}>{channelResult.public_url}</a></> :
                  channelResult.ad_id ? `Mock ad submitted — ${channelResult.ad_id} (${channelResult.headline_1 ?? ""})` :
                  channelResult.status === "sent" ? `Email sent to ${channelResult.to}` :
                  "Done."}
            </div>
          )}
          {channelStatus === "error" && channelResult && (
            <div style={{ marginTop: 10, fontSize: 12, color: "#ef4444" }}>
              ⚠ {channelResult.error ?? channelResult.reason ?? "Publish failed."}
            </div>
          )}
        </div>
      )}

      {status === "done" && result && agentKey === "channel" && (
        <div style={{ marginTop: 16, display: "flex", flexDirection: "column" as const, gap: 16 }}>
          {result.image_b64 && (
            <div style={{ borderRadius: 14, overflow: "hidden", position: "relative" as const,
              boxShadow: "var(--shadow-md)" }}>
              <img src={`data:image/jpeg;base64,${result.image_b64}`} alt="Campaign visual"
                style={{ width: "100%", display: "block", maxHeight: 280, objectFit: "cover" as const }} />
              {result.logo_b64 && (
                <div style={{ position: "absolute" as const, top: 12, right: 12,
                  background: "rgba(255,255,255,0.92)", backdropFilter: "blur(8px)",
                  borderRadius: 10, padding: "6px 10px",
                  border: "1px solid rgba(255,255,255,0.6)" }}>
                  <img src={`data:image/png;base64,${result.logo_b64}`} alt="Brand logo"
                    style={{ height: 28, objectFit: "contain" as const, display: "block" }} />
                </div>
              )}
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
            {Object.entries(POLY_CHANNEL_CFG).filter(([key]) => result[key]).map(([key, cfg]) => (
              <div key={key} style={{
                borderRadius: 14, overflow: "hidden", background: "var(--card-bg-soft)",
                border: `1px solid ${cfg.color}30`,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px",
                  background: `${cfg.color}16`, borderBottom: `1px solid ${cfg.color}25` }}>
                  <span style={{ fontSize: 15 }}>{cfg.icon}</span>
                  <span style={{ fontSize: 11, fontWeight: 800, color: cfg.color, letterSpacing: "0.04em",
                    textTransform: "uppercase" as const }}>{cfg.label}</span>
                </div>
                <div style={{ padding: "14px 16px", fontSize: 13, color: "var(--text-primary)", lineHeight: 1.55 }}>
                  {String(result[key])}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {status === "done" && result && agentKey === "kv" && (
        <div style={{ marginTop: 16, paddingLeft: 14, borderLeft: `2px solid ${color}40` }}>
          {result.image_b64 ? (
            <>
              <img src={`data:image/jpeg;base64,${result.image_b64}`} alt={result.headline || "Key visual"}
                style={{ width: "100%", borderRadius: 14, display: "block",
                  boxShadow: "var(--shadow-md)" }} />
              {result.headline && (
                <div style={{ marginTop: 10, fontSize: 14, fontWeight: 700, color: "var(--text-primary)",
                  fontStyle: "italic" }}>"{result.headline}"</div>
              )}
              <div style={{ display: "flex", gap: 14, marginTop: 8 }}>
                <a href={`data:image/jpeg;base64,${result.image_b64}`} download="key-visual.jpg"
                  style={{ fontSize: 12, fontWeight: 700, color }}>
                  ⬇ Download
                </a>
                <button onClick={handleSaveKvToHub} disabled={kvSaveState === "saving"}
                  style={{ fontSize: 12, fontWeight: 700, background: "none", border: "none",
                    cursor: kvSaveState === "saving" ? "default" : "pointer", fontFamily: "inherit", padding: 0,
                    color: kvSaveState === "saved" ? "#10b981" : color }}>
                  {kvSaveState === "saved" ? "✓ Saved" : kvSaveState === "saving" ? "Saving…" : "💾 Save to Content Hub"}
                </button>
              </div>
            </>
          ) : (
            <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
              Headline generated ("{result.headline}") but image generation failed — try again.
            </div>
          )}
        </div>
      )}

      {status === "done" && result && agentKey === "reel" && (
        <div style={{ marginTop: 16, paddingLeft: 14, borderLeft: `2px solid ${color}40` }}>
          {result.video_b64 ? (
            <>
              <video controls autoPlay loop muted playsInline
                src={`data:video/mp4;base64,${result.video_b64}`}
                style={{ width: "100%", borderRadius: 14, display: "block",
                  boxShadow: "var(--shadow-md)" }} />
              {result.headline && (
                <div style={{ marginTop: 10, fontSize: 14, fontWeight: 700, color: "var(--text-primary)",
                  fontStyle: "italic" }}>"{result.headline}"</div>
              )}
              <div style={{ display: "flex", gap: 14, marginTop: 8 }}>
                <a href={`data:video/mp4;base64,${result.video_b64}`} download="campaign-reel.mp4"
                  style={{ fontSize: 12, fontWeight: 700, color }}>
                  ⬇ Download
                </a>
                <button onClick={handleSaveReelToHub} disabled={reelSaveState === "saving"}
                  style={{ fontSize: 12, fontWeight: 700, background: "none", border: "none",
                    cursor: reelSaveState === "saving" ? "default" : "pointer", fontFamily: "inherit", padding: 0,
                    color: reelSaveState === "saved" ? "#10b981" : color }}>
                  {reelSaveState === "saved" ? "✓ Saved" : reelSaveState === "saving" ? "Saving…" : "💾 Save to Content Hub"}
                </button>
              </div>
            </>
          ) : (
            <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
              Headline generated ("{result.headline}") but video generation failed — try again.
            </div>
          )}
        </div>
      )}

      {status === "done" && result && agentKey === "tvc" && (
        <div style={{ marginTop: 16, display: "flex", flexDirection: "column" as const, gap: 16 }}>
          {Array.isArray(result.scenes) && (result.scenes as any[]).length > 0 && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 800, color, letterSpacing: "0.08em",
                textTransform: "uppercase" as const, marginBottom: 10 }}>
                📝 {result.title} — {result.duration}s Script
              </div>
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
                {(result.scenes as any[]).map((scene: any, i: number) => (
                  <div key={i} style={{ padding: "12px 16px", borderRadius: 12,
                    background: "var(--card-bg-soft)", border: `1px solid ${color}25`,
                    display: "grid", gridTemplateColumns: "28px 1fr", gap: 12, alignItems: "flex-start" }}>
                    <div style={{ width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                      background: `linear-gradient(135deg,${color},#6366f1)`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 11, fontWeight: 800, color: "white" }}>{i + 1}</div>
                    <div>
                      <div style={{ fontSize: 12, color: "var(--text-primary)", lineHeight: 1.5, marginBottom: 4 }}>
                        {scene.visual}
                      </div>
                      {scene.voiceover && (
                        <div style={{ fontSize: 11, color, fontStyle: "italic" }}>
                          🎙 "{scene.voiceover}"
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.video_b64 ? (
            <div>
              <div style={{ fontSize: 11, fontWeight: 800, color, letterSpacing: "0.08em",
                textTransform: "uppercase" as const, marginBottom: 8 }}>
                🎥 Final TVC — {result.n_scenes} scenes · {result.duration}s
              </div>
              <video controls autoPlay loop muted playsInline
                src={`data:video/mp4;base64,${result.video_b64}`}
                style={{ width: "100%", borderRadius: 14, display: "block", boxShadow: "var(--shadow-md)" }} />
              {result.tagline && (
                <div style={{ marginTop: 8, fontSize: 13, fontWeight: 600, color: "var(--text-secondary)",
                  fontStyle: "italic" }}>"{result.tagline}"</div>
              )}
              <div style={{ display: "flex", gap: 14, marginTop: 8 }}>
                <a href={`data:video/mp4;base64,${result.video_b64}`} download="tvc.mp4"
                  style={{ fontSize: 12, fontWeight: 700, color }}>⬇ Download TVC</a>
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 13, color: "var(--text-tertiary)", padding: "12px 0" }}>
              {result.n_scenes === 0
                ? "Script ready but video generation failed — check Veo quota and retry."
                : `${result.n_scenes} of ${(result.scenes as any[])?.length} scenes generated — stitching failed. Individual clips available below.`}
            </div>
          )}

          {Array.isArray(result.scene_clips) && (result.scene_clips as string[]).length > 0 && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)",
                letterSpacing: "0.06em", textTransform: "uppercase" as const, marginBottom: 8 }}>
                Scene clips
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 10 }}>
                {(result.scene_clips as string[]).map((clip, i) => (
                  <div key={i}>
                    <video controls muted playsInline src={`data:video/mp4;base64,${clip}`}
                      style={{ width: "100%", borderRadius: 10, display: "block" }} />
                    <div style={{ fontSize: 10, color: "var(--text-secondary)", marginTop: 4, textAlign: "center" as const }}>
                      Scene {i + 1}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {status === "done" && result && agentKey === "email_templates" && (
        <div style={{ marginTop: 16, display: "flex", flexDirection: "column" as const, gap: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color, letterSpacing: "0.08em",
            textTransform: "uppercase" as const }}>
            📧 {(result.templates as any[])?.length} Email Templates — Subject: "{result.subject}"
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 14 }}>
            {((result.templates as any[]) ?? []).map((tpl: any) => (
              <div key={tpl.id} style={{ borderRadius: 14, overflow: "hidden",
                border: `1.5px solid ${color}30`,
                boxShadow: `0 4px 20px ${color}15` }}>
                <div style={{ padding: "10px 14px", background: `${color}12`,
                  borderBottom: `1px solid ${color}20`,
                  display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color }}>
                      {tpl.name}
                    </div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)", marginTop: 2 }}>
                      {tpl.layout}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <a href={`data:text/html;charset=utf-8,${encodeURIComponent(tpl.html)}`}
                      target="_blank" rel="noreferrer"
                      style={{ fontSize: 11, fontWeight: 700, color, textDecoration: "none",
                        padding: "4px 10px", borderRadius: 6, border: `1px solid ${color}40`,
                        background: `${color}08` }}>
                      Preview ↗
                    </a>
                    <a href={`data:text/html;charset=utf-8,${encodeURIComponent(tpl.html)}`}
                      download={`${tpl.id}-template.html`}
                      style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)",
                        textDecoration: "none", padding: "4px 10px", borderRadius: 6,
                        border: "1px solid var(--card-border)", background: "var(--card-bg-soft)" }}>
                      ⬇ HTML
                    </a>
                  </div>
                </div>
                <div style={{ position: "relative" as const, height: 240, overflow: "hidden",
                  background: "#f8fafc" }}>
                  <iframe
                    srcDoc={tpl.html}
                    style={{ width: "200%", height: "200%", border: "none",
                      transform: "scale(0.5)", transformOrigin: "top left",
                      pointerEvents: "none" as const }}
                    title={tpl.name}
                  />
                </div>
              </div>
            ))}
          </div>

          <div style={{ padding: "12px 16px", borderRadius: 10,
            background: "rgba(124,58,237,0.06)", border: "1px solid rgba(124,58,237,0.2)",
            fontSize: 12, color: "var(--text-secondary)" }}>
            💡 Pick a template, click <strong>Preview ↗</strong> to review, download the HTML,
            then paste it into <strong>Publishing → Email</strong> to send via Mailchimp.
          </div>
        </div>
      )}

      {status === "done" && result && agentKey === "briefing" && (
        <BriefingAgentDashboard result={result} color={color}
          originalPrompt={prompt} onRegenerate={handleRegenerate} />
      )}

      {status === "done" && result && agentKey !== "channel" && agentKey !== "kv" && agentKey !== "reel" && agentKey !== "tvc" && agentKey !== "email_templates" && agentKey !== "briefing" && (
        <div style={{ marginTop: 14, paddingLeft: 14, borderLeft: `2px solid ${color}40` }}>
          {Object.entries(result).filter(([k]) => k !== "agent").map(([key, val]) => (
            <div key={key} style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.06em",
                textTransform: "uppercase" as const, marginBottom: 2 }}>{key.replace(/_/g, " ")}</div>
              {Array.isArray(val) ? (
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "var(--text-primary)" }}>
                  {val.map((item, i) => <li key={i}>{String(item)}</li>)}
                </ul>
              ) : (
                <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.5 }}>{String(val)}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
