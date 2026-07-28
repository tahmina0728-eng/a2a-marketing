import { useState } from "react";

export default function BriefingAgentDashboard({ result, color, originalPrompt, onApprove, onRegenerate }: {
  result: Record<string, any>; color: string;
  originalPrompt?: string;
  onApprove?: () => void;
  onRegenerate?: (refinedPrompt: string, edits?: { fanTruth: string; goal: string; audience: string; market: string }) => void;
}) {
  const [activeTab, setActiveTab] = useState<string>("overview");

  // HITL state
  const [showHITL, setShowHITL]   = useState(false);
  const [hitlFeedback, setHitlFeedback] = useState("");

  const score    = typeof result.score === "number" ? result.score : 90;
  const verdict  = (result.verdict  as string) ?? (score >= 70 ? "PASS" : "NEEDS WORK");
  const brand    = (result.brand    as string) ?? "";
  const product  = (result.product  as string) ?? "";
  const fanTruth = (result.fan_truth as string) ?? "";
  const audience = (result.audience  as string) ?? "";
  const market   = (result.market    as string) ?? "";
  const season   = (result.season    as string) ?? "";
  const goal     = (result.goal      as string) ?? "";
  const summary  = (result.summary   as string) ?? "";
  const passColor = score >= 70 ? "#10b981" : "#f59e0b";

  // Editable HITL fields — initialized from current result
  const [editFanTruth, setEditFanTruth] = useState(fanTruth);
  const [editGoal,     setEditGoal]     = useState(goal);
  const [editAudience, setEditAudience] = useState(audience);
  const [editMarket,   setEditMarket]   = useState(market ? `${market}${season ? ` · ${season}` : ""}` : season);

  // AI diagnosis — derived from score + result fields
  const aiSuggestions: { icon: string; text: string; severity: "warn" | "info" }[] = [];
  if (score < 70) aiSuggestions.push({ icon: "⚡", severity: "warn", text: "Brief confidence is below threshold — key fields may be too vague." });
  if (!fanTruth)  aiSuggestions.push({ icon: "⚡", severity: "warn", text: "No Fan Truth detected. Add a specific, human consumer insight to strengthen the brief." });
  else if (fanTruth.split(" ").length < 8) aiSuggestions.push({ icon: "⚡", severity: "warn", text: "Fan Truth is very short. A richer, more specific truth improves creative quality." });
  if (!audience)  aiSuggestions.push({ icon: "💡", severity: "info", text: "Audience segment is missing. Adding a target persona improves channel recommendations." });
  if (!goal)      aiSuggestions.push({ icon: "💡", severity: "info", text: "Campaign goal not detected. Specify an objective (awareness, trial, loyalty, etc.)." });
  if (aiSuggestions.length === 0) aiSuggestions.push({ icon: "💡", severity: "info", text: "Brief scored well. Use the fields below to fine-tune any element before regenerating." });

  const handleTriggerRegenerate = () => {
    // Build natural-language prompt — brand name must appear prominently so the
    // backend's brand lookup can match it against the uploaded brands index.
    // Strategy: start with the original prompt as the base, then append
    // any fields the user changed as inline refinements.

    let base = originalPrompt?.trim() || [brand, product].filter(Boolean).join(" — ");

    const refinements: string[] = [];
    if (editGoal      && editGoal      !== goal)      refinements.push(`goal: ${editGoal}`);
    if (editFanTruth  && editFanTruth  !== fanTruth)  refinements.push(`fan truth: ${editFanTruth}`);
    if (editAudience  && editAudience  !== audience)  refinements.push(`audience: ${editAudience}`);
    if (editMarket    && editMarket    !== `${market}${season ? ` · ${season}` : ""}`)
      refinements.push(`market: ${editMarket}`);
    if (hitlFeedback.trim()) refinements.push(hitlFeedback.trim());

    const refinedPrompt = refinements.length
      ? `${base}. Refinements — ${refinements.join("; ")}`
      : base;

    setShowHITL(false);
    setHitlFeedback("");
    onRegenerate?.(refinedPrompt, {
      fanTruth: editFanTruth,
      goal:     editGoal,
      audience: editAudience,
      market:   editMarket,
    });
  };

  const DATA_SOURCE_COUNT = 5;

  const insights = [
    {
      title: "Brand Guidelines", confidence: 92, icon: "📚", accentColor: "#3b82f6",
      summary: fanTruth
        ? `Fan truth validated: "${fanTruth.slice(0, 80)}${fanTruth.length > 80 ? "…" : ""}"`
        : "Brand guidelines successfully validated against campaign objectives.",
    },
    {
      title: "Customer Insights", confidence: 88, icon: "👥", accentColor: "#8b5cf6",
      summary: audience
        ? `Target: ${audience}${market ? ` · ${market}` : ""}${season ? ` · ${season}` : ""}`
        : "Target segments identified with high behavioural alignment.",
    },
    {
      title: "Historical Insights", confidence: 84, icon: "📈", accentColor: "#10b981",
      summary: summary || "Previous campaign patterns inform creative direction and channel weighting.",
    },
  ];

  const tabs = [
    { id: "overview",  label: "Overview" },
    { id: "messages",  label: "Key Messages" },
    { id: "creative",  label: "Creative" },
    { id: "channels",  label: "Channels" },
    { id: "risks",     label: "Risks" },
    { id: "metrics",   label: "Metrics" },
  ];

  const donutSegs = [
    { label: "Brand",      n: 18, color: "#3b82f6" },
    { label: "Historical", n: 15, color: "#8b5cf6" },
    { label: "CDP",        n: 9,  color: "#10b981" },
    { label: "Market",     n: 5,  color: "#f59e0b" },
  ];
  const donutTotal = donutSegs.reduce((s, d) => s + d.n, 0);
  let cumAngle = -90;
  const donutPaths = donutSegs.map((seg) => {
    const angle = (seg.n / donutTotal) * 360;
    const startA = cumAngle;
    cumAngle += angle;
    const endA = cumAngle;
    const r = 42, cx = 60, cy = 60;
    const x1 = cx + r * Math.cos((startA * Math.PI) / 180);
    const y1 = cy + r * Math.sin((startA * Math.PI) / 180);
    const x2 = cx + r * Math.cos((endA   * Math.PI) / 180);
    const y2 = cy + r * Math.sin((endA   * Math.PI) / 180);
    const lg = angle > 180 ? 1 : 0;
    return { ...seg, d: `M 60 60 L ${x1} ${y1} A 42 42 0 ${lg} 1 ${x2} ${y2} Z` };
  });

  const ConfRing = ({ pct, accent }: { pct: number; accent: string }) => {
    const r = 22, circ = 2 * Math.PI * r;
    const dash = (pct / 100) * circ;
    return (
      <svg width={56} height={56} viewBox="0 0 56 56" style={{ flexShrink: 0 }}>
        <circle cx={28} cy={28} r={r} fill="none" stroke="var(--card-border)" strokeWidth={4} />
        <circle cx={28} cy={28} r={r} fill="none" stroke={accent} strokeWidth={4}
          strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"
          style={{ transform: "rotate(-90deg)", transformOrigin: "28px 28px" }} />
        <text x={28} y={33} textAnchor="middle" fontSize={11} fontWeight={800} fill={accent}>{pct}%</text>
      </svg>
    );
  };

  const tabContentMap: Record<string, React.ReactNode> = {
    overview: (
      <div style={{ display: "flex", flexDirection: "column" as const, gap: 12 }}>
        {goal && <>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#6b7280", letterSpacing: "0.08em", textTransform: "uppercase" as const }}>Campaign Goal</div>
          <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6 }}>{goal}</div>
        </>}
        {product && <>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#6b7280", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginTop: 4 }}>Product</div>
          <div style={{ fontSize: 13, color: "var(--text-primary)" }}>{product}</div>
        </>}
        {fanTruth && <>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#6b7280", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginTop: 4 }}>Fan Truth</div>
          <div style={{ fontSize: 13, fontStyle: "italic", color: "var(--text-primary)", lineHeight: 1.7,
            padding: "10px 14px", borderLeft: "3px solid #3b82f6",
            background: "rgba(59,130,246,0.06)", borderRadius: "0 8px 8px 0" }}>"{fanTruth}"</div>
        </>}
        {(audience || market || season) && (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" as const, marginTop: 4 }}>
            {audience && <span style={{ fontSize: 11, padding: "4px 12px", borderRadius: 99, background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.25)", color: "#3b82f6", fontWeight: 600 }}>{audience}</span>}
            {market   && <span style={{ fontSize: 11, padding: "4px 12px", borderRadius: 99, background: "rgba(139,92,246,0.1)", border: "1px solid rgba(139,92,246,0.25)", color: "#8b5cf6", fontWeight: 600 }}>{market}</span>}
            {season   && <span style={{ fontSize: 11, padding: "4px 12px", borderRadius: 99, background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.25)", color: "#10b981", fontWeight: 600 }}>{season}</span>}
          </div>
        )}
      </div>
    ),
    messages: (
      <div style={{ display: "flex", flexDirection: "column" as const, gap: 12 }}>
        {fanTruth && (
          <div style={{ padding: "13px 15px", borderRadius: 10, background: "rgba(59,130,246,0.06)", border: "1.5px solid rgba(59,130,246,0.2)" }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#3b82f6", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 6 }}>Primary Message</div>
            <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6 }}>{fanTruth}</div>
          </div>
        )}
        {goal && (
          <div style={{ padding: "13px 15px", borderRadius: 10, background: "rgba(16,185,129,0.06)", border: "1.5px solid rgba(16,185,129,0.2)" }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#10b981", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 6 }}>Campaign Objective</div>
            <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6 }}>{goal}</div>
          </div>
        )}
        <div style={{ padding: "13px 15px", borderRadius: 10, background: "rgba(245,158,11,0.06)", border: "1.5px solid rgba(245,158,11,0.2)" }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#f59e0b", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 6 }}>Tone of Voice</div>
          <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6 }}>Authoritative yet accessible, grounded in human truth, empathetic to real audience journeys.</div>
        </div>
      </div>
    ),
    creative: (
      <div style={{ display: "flex", flexDirection: "column" as const, gap: 12 }}>
        <div style={{ padding: "13px 15px", borderRadius: 10, background: "var(--card-bg-soft)", border: "1px solid var(--card-border)" }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#6b7280", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 6 }}>Visual Style</div>
          <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6 }}>White-dominant backgrounds with clean layouts. Product clearly featured with left third reserved for copy overlay. Natural lighting, authentic lifestyle imagery.</div>
        </div>
        <div style={{ padding: "13px 15px", borderRadius: 10, background: "var(--card-bg-soft)", border: "1px solid var(--card-border)" }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#6b7280", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 6 }}>Brand Compliance</div>
          <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6, display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 15, color: passColor }}>{verdict === "PASS" ? "✓" : "⚠"}</span>
            {verdict === "PASS" ? "Campaign aligns with brand guidelines and tone requirements." : "Some elements need review to meet brand guidelines."}
          </div>
        </div>
        {summary && (
          <div style={{ padding: "13px 15px", borderRadius: 10, background: "var(--card-bg-soft)", border: "1px solid var(--card-border)" }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#6b7280", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 6 }}>Agent Notes</div>
            <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6 }}>{summary}</div>
          </div>
        )}
      </div>
    ),
    channels: (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        {[
          { ch: "Social Media",    icon: "📸", reco: "Instagram & TikTok short-form, UGC-style content with product focus." },
          { ch: "Digital Display", icon: "🖥️", reco: "Programmatic banners, retargeting based on product category interest." },
          { ch: "Search",          icon: "🔍", reco: "Google Ads targeting relevant intent signals and competitor conquesting." },
          { ch: "Content / PR",    icon: "📰", reco: "Editorial placement and influencer partnerships relevant to the category." },
        ].map(({ ch, icon, reco }) => (
          <div key={ch} style={{ padding: "12px 13px", borderRadius: 10, background: "var(--card-bg-soft)", border: "1px solid var(--card-border)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 5 }}>
              <span style={{ fontSize: 13 }}>{icon}</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-primary)" }}>{ch}</span>
            </div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>{reco}</div>
          </div>
        ))}
      </div>
    ),
    risks: (
      <div style={{ display: "flex", flexDirection: "column" as const, gap: 10 }}>
        {[
          { level: "low",    label: "Health Claims",         desc: "All health claims must be substantiated. Avoid absolute claims ('cures', 'eliminates')." },
          { level: "medium", label: "Regulatory Compliance", desc: "OTC regulations vary by market. Ensure regional legal review before campaign launch." },
          { level: "low",    label: "Brand Safety",          desc: "Avoid placement near sensitive content. Block competitor health misinformation sites." },
        ].map(({ level, label, desc }) => (
          <div key={label} style={{ display: "flex", gap: 12, padding: "12px 14px", borderRadius: 10,
            background: "var(--card-bg-soft)",
            border: `1.5px solid ${level === "medium" ? "rgba(245,158,11,0.3)" : "rgba(16,185,129,0.25)"}` }}>
            <div style={{ width: 4, borderRadius: 4, flexShrink: 0, alignSelf: "stretch",
              background: level === "medium" ? "#f59e0b" : "#10b981" }} />
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", marginBottom: 3 }}>{label}</div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>{desc}</div>
            </div>
          </div>
        ))}
      </div>
    ),
    metrics: (
      <div style={{ display: "flex", flexDirection: "column" as const, gap: 10 }}>
        {[
          { metric: "Brand Awareness",  target: "+12% unaided recall",     frame: "3 months" },
          { metric: "Engagement Rate",  target: ">3.5% avg. engagement",   frame: "Campaign duration" },
          { metric: "Media ROI",        target: "2.8× ROAS",               frame: "Per flight" },
          { metric: "Share of Voice",   target: "+8pp above category avg",  frame: "Flight period" },
        ].map(({ metric, target, frame }) => (
          <div key={metric} style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "11px 13px", borderRadius: 10, background: "var(--card-bg-soft)", border: "1px solid var(--card-border)" }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>{metric}</div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>{frame}</div>
            </div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#3b82f6" }}>{target}</div>
          </div>
        ))}
      </div>
    ),
  };

  return (
    <div style={{ marginTop: 16 }}>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 13 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <span style={{ fontSize: 17 }}>📋</span>
          <span style={{ fontSize: 15, fontWeight: 800, color: "var(--text-primary)" }}>AI Briefing Agent</span>
          <span style={{ fontSize: 10, padding: "2px 9px", borderRadius: 99, fontWeight: 700,
            background: verdict === "PASS" ? "rgba(16,185,129,0.15)" : "rgba(245,158,11,0.15)",
            color: passColor,
            border: `1px solid ${verdict === "PASS" ? "rgba(16,185,129,0.3)" : "rgba(245,158,11,0.3)"}` }}>
            {verdict}
          </span>
          {(brand || product) && (
            <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
              {brand ? `— ${brand}` : ""}{product ? ` · ${product}` : ""}
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 7 }}>
          <button onClick={() => setShowHITL(v => !v)}
            style={{ padding: "5px 12px", borderRadius: 7,
              border: showHITL ? `1.5px solid ${color}` : "1.5px solid var(--card-border)",
              background: showHITL ? `${color}12` : "var(--card-bg-soft)",
              color: showHITL ? color : "var(--text-secondary)",
              fontSize: 11, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
              transition: "all 0.15s" }}>↺ Refine Brief</button>
          {onApprove ? (
            <button onClick={onApprove}
              style={{ padding: "5px 16px", borderRadius: 7, border: "none",
                background: "linear-gradient(135deg, #10b981, #059669)", color: "white",
                fontSize: 11, fontWeight: 700, cursor: "pointer", fontFamily: "inherit",
                boxShadow: "0 2px 10px rgba(16,185,129,0.35)" }}>
              ✓ Approve & Continue
            </button>
          ) : (
            <button style={{ padding: "5px 12px", borderRadius: 7, border: "none",
              background: `linear-gradient(135deg, ${color}, #6366f1)`, color: "white", fontSize: 11, fontWeight: 700,
              cursor: "pointer", fontFamily: "inherit" }}>⬇ Export</button>
          )}
        </div>
      </div>

      {/* ── HITL Regenerate Panel ───────────────────────────────────────── */}
      {showHITL && (
        <div style={{
          marginBottom: 16, borderRadius: 14,
          border: `1.5px solid ${color}40`,
          background: "var(--card-bg)",
          boxShadow: `0 4px 24px ${color}18`,
          overflow: "hidden",
        }}>
          {/* Panel header */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "14px 20px",
            borderBottom: `1px solid ${color}25`,
            background: `${color}08`,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 16 }}>↺</span>
              <div>
                <div style={{ fontSize: 13, fontWeight: 800, color: "var(--text-primary)" }}>Refine this brief</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 1 }}>
                  Edit any field and Logos will regenerate with your guidance
                </div>
              </div>
            </div>
            <button onClick={() => setShowHITL(false)}
              style={{ background: "none", border: "none", cursor: "pointer",
                fontSize: 18, color: "var(--text-secondary)", lineHeight: 1, padding: 4 }}>✕</button>
          </div>

          <div style={{ padding: "18px 20px", display: "flex", flexDirection: "column" as const, gap: 16 }}>

            {/* AI diagnosis */}
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 8 }}>
                AI Diagnosis
              </div>
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 6 }}>
                {aiSuggestions.map((s, i) => (
                  <div key={i} style={{
                    display: "flex", alignItems: "flex-start", gap: 10, padding: "10px 13px",
                    borderRadius: 9,
                    background: s.severity === "warn" ? "rgba(245,158,11,0.07)" : `${color}07`,
                    border: `1px solid ${s.severity === "warn" ? "rgba(245,158,11,0.25)" : `${color}25`}`,
                  }}>
                    <span style={{ fontSize: 13, flexShrink: 0 }}>{s.icon}</span>
                    <span style={{ fontSize: 12, color: "var(--text-primary)", lineHeight: 1.5 }}>{s.text}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Editable brief fields */}
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 10 }}>
                Edit Brief Fields
              </div>
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 10 }}>

                {/* Fan Truth */}
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, color, display: "block", marginBottom: 4 }}>
                    Fan Truth
                  </label>
                  <textarea
                    value={editFanTruth}
                    onChange={e => setEditFanTruth(e.target.value)}
                    rows={2}
                    placeholder="The human insight that connects brand and audience…"
                    style={{
                      width: "100%", padding: "9px 12px", borderRadius: 9, fontSize: 12,
                      border: `1.5px solid ${color}30`, background: "var(--card-bg-soft)",
                      color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
                      resize: "none" as const, lineHeight: 1.55, boxSizing: "border-box" as const,
                    }}
                    onFocus={e => e.currentTarget.style.borderColor = color}
                    onBlur={e => e.currentTarget.style.borderColor = `${color}30`}
                  />
                </div>

                {/* Goal */}
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, color, display: "block", marginBottom: 4 }}>
                    Campaign Goal
                  </label>
                  <input
                    value={editGoal}
                    onChange={e => setEditGoal(e.target.value)}
                    placeholder="e.g. Drive trial among new shoppers, increase brand awareness…"
                    style={{
                      width: "100%", padding: "9px 12px", borderRadius: 9, fontSize: 12,
                      border: `1.5px solid ${color}30`, background: "var(--card-bg-soft)",
                      color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
                      boxSizing: "border-box" as const,
                    }}
                    onFocus={e => e.currentTarget.style.borderColor = color}
                    onBlur={e => e.currentTarget.style.borderColor = `${color}30`}
                  />
                </div>

                {/* Audience + Market in a row */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div>
                    <label style={{ fontSize: 11, fontWeight: 700, color, display: "block", marginBottom: 4 }}>
                      Target Audience
                    </label>
                    <input
                      value={editAudience}
                      onChange={e => setEditAudience(e.target.value)}
                      placeholder="e.g. Adults 25–45 with sensitive teeth"
                      style={{
                        width: "100%", padding: "9px 12px", borderRadius: 9, fontSize: 12,
                        border: `1.5px solid ${color}30`, background: "var(--card-bg-soft)",
                        color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
                        boxSizing: "border-box" as const,
                      }}
                      onFocus={e => e.currentTarget.style.borderColor = color}
                      onBlur={e => e.currentTarget.style.borderColor = `${color}30`}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 11, fontWeight: 700, color, display: "block", marginBottom: 4 }}>
                      Market / Season
                    </label>
                    <input
                      value={editMarket}
                      onChange={e => setEditMarket(e.target.value)}
                      placeholder="e.g. UK · Winter"
                      style={{
                        width: "100%", padding: "9px 12px", borderRadius: 9, fontSize: 12,
                        border: `1.5px solid ${color}30`, background: "var(--card-bg-soft)",
                        color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
                        boxSizing: "border-box" as const,
                      }}
                      onFocus={e => e.currentTarget.style.borderColor = color}
                      onBlur={e => e.currentTarget.style.borderColor = `${color}30`}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Additional feedback */}
            <div>
              <label style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                letterSpacing: "0.08em", textTransform: "uppercase" as const, display: "block", marginBottom: 8 }}>
                Additional Feedback for Logos
              </label>
              <textarea
                value={hitlFeedback}
                onChange={e => setHitlFeedback(e.target.value)}
                rows={3}
                placeholder="Tell Logos what to improve, change the tone, add a seasonal angle, sharpen the insight…"
                style={{
                  width: "100%", padding: "10px 13px", borderRadius: 9, fontSize: 12,
                  border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                  color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
                  resize: "none" as const, lineHeight: 1.6, boxSizing: "border-box" as const,
                }}
                onFocus={e => e.currentTarget.style.borderColor = color}
                onBlur={e => e.currentTarget.style.borderColor = "var(--card-border)"}
              />
            </div>

            {/* Actions */}
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" as const }}>
              <button onClick={() => setShowHITL(false)}
                style={{ padding: "9px 18px", borderRadius: 9,
                  border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                  color: "var(--text-secondary)", fontSize: 12, fontWeight: 600,
                  cursor: "pointer", fontFamily: "inherit" }}>
                Cancel
              </button>
              <button
                onClick={handleTriggerRegenerate}
                disabled={!onRegenerate}
                style={{
                  padding: "9px 22px", borderRadius: 9, border: "none", fontFamily: "inherit",
                  fontSize: 12, fontWeight: 700, color: "white", cursor: onRegenerate ? "pointer" : "not-allowed",
                  opacity: onRegenerate ? 1 : 0.5,
                  background: `linear-gradient(135deg, ${color}, #6366f1)`,
                  boxShadow: `0 4px 14px ${color}40`,
                }}>
                ↺ Regenerate Brief →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Data Sources Section */}
      <div style={{ borderRadius: 12, border: "1px solid var(--card-border)", background: "var(--card-bg)",
        padding: "14px 18px", marginBottom: 13 }}>
        {/* Section header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>Data Sources</span>
            <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 600, color: "#10b981" }}>
              <svg width={12} height={12} viewBox="0 0 12 12" fill="none">
                <circle cx={6} cy={6} r={5.5} stroke="#10b981" strokeWidth={1}/>
                <path d="M3.5 6l1.8 1.8L8.5 4.5" stroke="#10b981" strokeWidth={1.4} strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              All sources connected
            </span>
          </div>
          <span style={{ fontSize: 10, color: "var(--text-muted)" }}>Last synced: 2 min ago
            <svg style={{ marginLeft: 4, verticalAlign: "middle" }} width={11} height={11} viewBox="0 0 12 12" fill="none">
              <circle cx={6} cy={6} r={5.5} stroke="#10b981" strokeWidth={1}/>
              <path d="M3.5 6l1.8 1.8L8.5 4.5" stroke="#10b981" strokeWidth={1.4} strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </span>
        </div>
        {/* Source cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10 }}>
          {[
            { label: "Brand Guidelines",    source: "Vertex AI Search", desc: `${result._chunks ?? 47} chunks retrieved`,  icon: (
              <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/>
              </svg>), iconBg: "rgba(59,130,246,0.1)" },
            { label: "Historical Campaigns", source: "BigQuery",         desc: "24 campaigns",               icon: (
              <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/>
              </svg>), iconBg: "rgba(139,92,246,0.1)" },
            { label: "Customer CDP",         source: "BigQuery",         desc: "3 audience segments",         icon: (
              <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx={9} cy={7} r={4}/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>), iconBg: "rgba(16,185,129,0.1)" },
            { label: "Product Catalogue",    source: "BigQuery",         desc: "Current",                    icon: (
              <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
                <line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>
              </svg>), iconBg: "rgba(245,158,11,0.1)" },
            { label: "Market Trends",        source: "Vertex AI Search", desc: "8 insights",                 icon: (
              <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="#06b6d4" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
                <polyline points="17 6 23 6 23 12"/>
              </svg>), iconBg: "rgba(6,182,212,0.1)" },
          ].map((src) => (
            <div key={src.label} style={{ borderRadius: 10, border: "1px solid var(--card-border)",
              background: "var(--card-bg-soft)", padding: "12px 13px",
              display: "flex", flexDirection: "column" as const, gap: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: src.iconBg,
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  {src.icon}
                </div>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.2 }}>{src.label}</div>
                  <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 1 }}>{src.source}</div>
                </div>
              </div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 500 }}>{src.desc}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, fontWeight: 700, color: "#10b981" }}>
                <svg width={10} height={10} viewBox="0 0 12 12" fill="none">
                  <circle cx={6} cy={6} r={5.5} stroke="#10b981" strokeWidth={1}/>
                  <path d="M3.5 6l1.8 1.8L8.5 4.5" stroke="#10b981" strokeWidth={1.4} strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Connected
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Insight Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 13 }}>
        {insights.map((ins) => (
          <div key={ins.title} style={{ padding: "13px", borderRadius: 12, background: "var(--card-bg)",
            border: "1px solid var(--card-border)", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 7 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 13 }}>{ins.icon}</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-primary)" }}>{ins.title}</span>
              </div>
              <ConfRing pct={ins.confidence} accent={ins.accentColor} />
            </div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.55 }}>{ins.summary}</div>
          </div>
        ))}
      </div>

      {/* Main: Tabs + Right Panel */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 244px", gap: 11 }}>

        {/* Tabbed briefing */}
        <div style={{ borderRadius: 12, border: "1px solid var(--card-border)", background: "var(--card-bg)", overflow: "hidden" }}>
          <div style={{ display: "flex", borderBottom: "1px solid var(--card-border)", overflowX: "auto" as const }}>
            {tabs.map((tab) => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                style={{ padding: "10px 13px", border: "none", background: "none", cursor: "pointer",
                  fontSize: 11, fontWeight: activeTab === tab.id ? 700 : 500,
                  color: activeTab === tab.id ? color : "var(--text-secondary)",
                  borderBottom: activeTab === tab.id ? `2px solid ${color}` : "2px solid transparent",
                  whiteSpace: "nowrap" as const, fontFamily: "inherit", transition: "color 0.15s", flexShrink: 0 }}>
                {tab.label}
              </button>
            ))}
          </div>
          <div style={{ padding: "18px 20px", overflowY: "auto" as const, minHeight: 220 }}>
            {tabContentMap[activeTab]}
          </div>
        </div>

        {/* Right panel */}
        <div style={{ display: "flex", flexDirection: "column" as const, gap: 10 }}>

          {/* Donut chart */}
          <div style={{ borderRadius: 12, border: "1px solid var(--card-border)", background: "var(--card-bg)", padding: "13px" }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.08em",
              textTransform: "uppercase" as const, marginBottom: 9 }}>Sources Overview</div>
            <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
              <svg width={116} height={116} viewBox="0 0 120 120" style={{ flexShrink: 0 }}>
                {donutPaths.map((p, i) => <path key={i} d={p.d} fill={p.color} opacity={0.88} />)}
                <circle cx={60} cy={60} r={26} fill="var(--card-bg)" />
                <text x={60} y={55} textAnchor="middle" fontSize={15} fontWeight={800} fill="var(--text-primary)">{donutTotal}</text>
                <text x={60} y={68} textAnchor="middle" fontSize={8} fill="var(--text-secondary)">total</text>
              </svg>
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 6, flex: 1 }}>
                {donutSegs.map((s) => (
                  <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color, flexShrink: 0 }} />
                    <span style={{ fontSize: 10, color: "var(--text-secondary)", flex: 1 }}>{s.label}</span>
                    <span style={{ fontSize: 10, fontWeight: 700, color: "var(--text-primary)" }}>{s.n}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Source Citations */}
          <div style={{ borderRadius: 12, border: "1px solid var(--card-border)", background: "var(--card-bg)", padding: "13px", flex: 1 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.08em",
              textTransform: "uppercase" as const, marginBottom: 9 }}>Source Citations</div>
            <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
              {[
                { label: "Brand Voice Guidelines", src: "Brand Guidelines" },
                { label: "Q4 2024 Campaign Report", src: "BigQuery"       },
                { label: "Audience Segmentation",   src: "CDP Analysis"   },
                { label: "Compliance Checklist",    src: "Brand Guidelines"},
              ].map((c) => (
                <div key={c.label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-primary)",
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const }}>{c.label}</div>
                    <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{c.src}</div>
                  </div>
                  <button style={{ padding: "3px 8px", borderRadius: 5, border: `1px solid ${color}40`,
                    background: `${color}08`, color, fontSize: 10, fontWeight: 700, cursor: "pointer",
                    fontFamily: "inherit", flexShrink: 0 }}>View</button>
                </div>
              ))}
            </div>
          </div>

          {/* Overall Confidence */}
          <div style={{ borderRadius: 12, padding: "13px 15px", display: "flex", alignItems: "center",
            justifyContent: "space-between",
            border: `1.5px solid ${verdict === "PASS" ? "rgba(16,185,129,0.4)" : "rgba(245,158,11,0.4)"}`,
            background: verdict === "PASS" ? "rgba(16,185,129,0.07)" : "rgba(245,158,11,0.07)" }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.08em",
                textTransform: "uppercase" as const, marginBottom: 3 }}>Overall Confidence</div>
              <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>Based on {DATA_SOURCE_COUNT} data sources</div>
            </div>
            <div style={{ fontSize: 26, fontWeight: 900, color: passColor }}>{score}%</div>
          </div>
        </div>
      </div>
    </div>
  );
}
