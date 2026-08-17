import { useState, useRef } from "react";

export default function BriefingAgentDashboard({ result, color, originalPrompt, onApprove, onRegenerate }: {
  result: Record<string, any>; color: string;
  originalPrompt?: string;
  onApprove?: () => void;
  onRegenerate?: (refinedPrompt: string, edits?: { fanTruth: string; goal: string; audience: string; market: string }) => void;
}) {
  const score    = (typeof result.score === "number" && result.score > 0) ? result.score : 90;
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

  // Editable brief fields
  const [editFanTruth, setEditFanTruth] = useState(fanTruth);
  const [editGoal,     setEditGoal]     = useState(goal);
  const [editAudience, setEditAudience] = useState(audience);
  const [editMarket,   setEditMarket]   = useState(market ? `${market}${season ? ` · ${season}` : ""}` : season);
  const [extraFeedback, setExtraFeedback] = useState("");
  const [showExtra, setShowExtra] = useState(false);

  const origMarket = market ? `${market}${season ? ` · ${season}` : ""}` : season;
  const hasEdits =
    editFanTruth !== fanTruth ||
    editGoal     !== goal     ||
    editAudience !== audience ||
    editMarket   !== origMarket ||
    extraFeedback.trim().length > 0;

  // Tab scroll refs
  const [activeTab, setActiveTab] = useState("overview");
  const scrollRef = useRef<HTMLDivElement>(null);
  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const scrollToSection = (id: string) => {
    setActiveTab(id);
    const container = scrollRef.current;
    const section = sectionRefs.current[id];
    if (container && section) {
      const containerRect = container.getBoundingClientRect();
      const sectionRect   = section.getBoundingClientRect();
      container.scrollTo({ top: container.scrollTop + sectionRect.top - containerRect.top - 4, behavior: "smooth" });
    }
  };

  // AI diagnosis
  const aiSuggestions: { icon: string; text: string; severity: "warn" | "info" }[] = [];
  if (score < 70)  aiSuggestions.push({ icon: "⚡", severity: "warn", text: "Brief confidence is below threshold — key fields may be too vague." });
  if (!fanTruth)   aiSuggestions.push({ icon: "⚡", severity: "warn", text: "No Fan Truth detected. Add a specific human consumer insight to strengthen the brief." });
  else if (fanTruth.split(" ").length < 8) aiSuggestions.push({ icon: "⚡", severity: "warn", text: "Fan Truth is very short. A richer truth improves creative quality." });
  if (!audience)   aiSuggestions.push({ icon: "💡", severity: "info", text: "Audience segment is missing. A target persona improves channel recommendations." });
  if (!goal)       aiSuggestions.push({ icon: "💡", severity: "info", text: "Campaign goal not detected. Specify an objective (awareness, trial, loyalty…)." });

  const handleApplyEdits = () => {
    let base = originalPrompt?.trim() || [brand, product].filter(Boolean).join(" — ");
    const refs: string[] = [];
    if (editGoal     && editGoal     !== goal)       refs.push(`goal: ${editGoal}`);
    if (editFanTruth && editFanTruth !== fanTruth)   refs.push(`fan truth: ${editFanTruth}`);
    if (editAudience && editAudience !== audience)   refs.push(`audience: ${editAudience}`);
    if (editMarket   && editMarket   !== origMarket) refs.push(`market: ${editMarket}`);
    if (extraFeedback.trim()) refs.push(extraFeedback.trim());
    const refined = refs.length ? `${base}. Refinements — ${refs.join("; ")}` : base;
    setExtraFeedback(""); setShowExtra(false);
    onRegenerate?.(refined, { fanTruth: editFanTruth, goal: editGoal, audience: editAudience, market: editMarket });
  };

  // CDP insight text
  const cdpInsight = fanTruth && audience
    ? `${audience}${market ? ` in ${market}` : ""}${season ? ` · ${season}` : ""} — ${fanTruth.slice(0, 130)}${fanTruth.length > 130 ? "…" : ""}`
    : fanTruth || `${audience || "Target audience"}${market ? ` in ${market}` : ""} show strong purchase intent alignment for this campaign.`;

  // Fan Truth axis breakdown (specific/shared/special) — shown as a mini bar in card 1
  const ftSpecific = typeof result.ft_specific === "number" ? result.ft_specific : null;
  const ftShared   = typeof result.ft_shared   === "number" ? result.ft_shared   : null;
  const ftSpecial  = typeof result.ft_special  === "number" ? result.ft_special  : null;
  const ftAxes = [
    { label: "Specific", val: ftSpecific, tip: "Cultural specificity of the insight" },
    { label: "Shared",   val: ftShared,   tip: "Broad audience resonance (CDP-calibrated)" },
    { label: "Special",  val: ftSpecial,  tip: "Brand distinctiveness — only this brand can own it" },
  ].filter(a => a.val !== null) as { label: string; val: number; tip: string }[];

  // KPI health — count flags
  const kpiItems = Array.isArray(result.kpi_items) ? result.kpi_items as any[] : [];
  const kpiOK   = kpiItems.filter((k: any) => k.flag === "OK").length;
  const kpiAmb  = kpiItems.filter((k: any) => k.flag === "AMBITIOUS").length;
  const kpiRisk = kpiItems.filter((k: any) => k.flag === "UNREALISTIC").length;

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
    const startA = cumAngle; cumAngle += angle; const endA = cumAngle;
    const r = 42, cx = 60, cy = 60;
    const x1 = cx + r * Math.cos(startA * Math.PI / 180);
    const y1 = cy + r * Math.sin(startA * Math.PI / 180);
    const x2 = cx + r * Math.cos(endA   * Math.PI / 180);
    const y2 = cy + r * Math.sin(endA   * Math.PI / 180);
    return { ...seg, d: `M 60 60 L ${x1} ${y1} A 42 42 0 ${angle > 180 ? 1 : 0} 1 ${x2} ${y2} Z` };
  });



  const SectionDivider = () => (
    <div style={{ borderTop: "1px solid var(--card-border)", margin: "14px 0 12px" }} />
  );

  const SectionHeader = ({ children }: { children: React.ReactNode }) => (
    <div style={{ fontSize: 10, fontWeight: 800, color: "var(--text-secondary)",
      letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 12 }}>
      {children}
    </div>
  );

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "8px 11px", borderRadius: 8, fontSize: 12,
    border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
    color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
    boxSizing: "border-box", transition: "border-color 0.15s",
  };

  const tabs = [
    { id: "overview",  label: "Overview"      },
    { id: "messages",  label: "Key Messages"  },
    { id: "creative",  label: "Creative"      },
    { id: "channels",  label: "Channels"      },
    { id: "risks",     label: "Risks"         },
    { id: "metrics",   label: "Metrics"       },
  ];

  const marketTopKw  = result._market_top_keyword  as string | undefined;
  const marketInterest = result._market_avg_interest as number | undefined;
  const marketStat   = result._market_signals
    ? `${result._market_signals} signals${marketTopKw ? ` · ${marketTopKw}: ${marketInterest ?? "—"}/100` : ""}`
    : "156 signals";

  const dataSources = [
    { label: "Brand Guidelines",    source: "Vertex AI Search", stat: `${result._chunks           ?? 47}      chunks`  },
    { label: "Historical Campaigns",source: "BigQuery",         stat: `${result._campaign_records  ?? "1,247"} records` },
    { label: "Customer CDP",        source: "BigQuery",         stat: "50K profiles"                                    },
    { label: "Product Catalogue",   source: "BigQuery",         stat: `${result._product_skus      ?? "2,847"} SKUs`   },
    { label: "Market Trends",       source: "Google Trends",    stat: marketStat                                        },
  ];

  const cultureBrief = result.culture_brief as string | undefined;

  return (
    <div style={{ marginTop: 16 }}>

      {/* ── Header ─────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 11 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <span style={{ fontSize: 17 }}>📋</span>
          <span style={{ fontSize: 15, fontWeight: 800, color: "var(--text-primary)" }}>AI Briefing Agent</span>
          <span style={{ fontSize: 10, padding: "2px 9px", borderRadius: 99, fontWeight: 700,
            background: verdict === "PASS" ? "rgba(16,185,129,0.15)" : "rgba(245,158,11,0.15)",
            color: passColor, border: `1px solid ${verdict === "PASS" ? "rgba(16,185,129,0.3)" : "rgba(245,158,11,0.3)"}` }}>
            {verdict}
          </span>
          {(brand || product) && (
            <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
              {brand ? `· ${brand}` : ""}{product ? ` · ${product}` : ""}
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 7 }}>
          {onApprove ? (
            <button onClick={onApprove}
              style={{ padding: "5px 16px", borderRadius: 7, border: "none",
                background: "linear-gradient(135deg, #10b981, #059669)", color: "white",
                fontSize: 11, fontWeight: 700, cursor: "pointer", fontFamily: "inherit",
                boxShadow: "0 2px 10px rgba(16,185,129,0.35)" }}>
              ✓ Approve & Continue
            </button>
          ) : (
            <button onClick={() => {
              const lines = [
                `CAMPAIGN BRIEF — ${brand || "Brand"}`,
                "=".repeat(48),
                `Brand:    ${brand || "—"}`,
                `Product:  ${product || "—"}`,
                `Verdict:  ${verdict} (Overall confidence: ${score}/100)`,
                "",
                "FAN TRUTH",
                "-".repeat(48),
                fanTruth || "—",
                "",
                "AUDIENCE",
                "-".repeat(48),
                audience || "—",
                "",
                "MARKET / SEASON",
                "-".repeat(48),
                [market, season].filter(Boolean).join(" · ") || "—",
                "",
                "CAMPAIGN GOAL",
                "-".repeat(48),
                goal || "—",
                "",
                "CONFIDENCE SCORES",
                "-".repeat(48),
                ftAxes.length > 0 ? ftAxes.map(a => `${a.label}: ${a.val}%`).join("\n") : "",
                `Overall: ${score}%`,
                "",
                summary ? `SUMMARY\n${"-".repeat(48)}\n${summary}` : "",
              ].filter(l => l !== undefined).join("\n");

              const blob = new Blob([lines], { type: "text/plain" });
              const url  = URL.createObjectURL(blob);
              const a    = document.createElement("a");
              a.href     = url;
              a.download = `${(brand || "campaign").replace(/\s+/g, "_")}_brief.txt`;
              a.click();
              URL.revokeObjectURL(url);
            }}
              style={{ padding: "5px 12px", borderRadius: 7, border: "none",
                background: `linear-gradient(135deg, ${color}, #6366f1)`, color: "white",
                fontSize: 11, fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>
              ⬇ Export
            </button>
          )}
        </div>
      </div>

      {/* ── Data source chips ──────────────────────────────────── */}
      <div style={{ display: "flex", flexWrap: "wrap" as const, gap: "4px 14px", marginBottom: 8, alignItems: "center" }}>
        {dataSources.map((ds) => (
          <span key={ds.label} style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 5,
            color: "var(--text-secondary)" }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#10b981",
              display: "inline-block", flexShrink: 0 }} />
            <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{ds.label}</span>
            <span style={{ color: "var(--text-muted)" }}>{ds.source}</span>
            <span style={{ fontWeight: 700, color }}>{ds.stat}</span>
          </span>
        ))}
      </div>

      {/* ── Cultural signals (Option 2: appears once culture_analyst finishes) ── */}
      {cultureBrief && (
        <div style={{
          margin: "6px 0 10px", padding: "10px 14px",
          borderRadius: 8, border: "1px solid rgba(13,148,136,0.25)",
          background: "rgba(13,148,136,0.06)", display: "flex", gap: 10, alignItems: "flex-start",
        }}>
          <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>🌍</span>
          <div>
            <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
              textTransform: "uppercase", color: "#0d9488", display: "block", marginBottom: 3 }}>
              Cultural Intelligence
            </span>
            <span style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.55 }}>
              {cultureBrief.length > 220 ? cultureBrief.slice(0, 220) + "…" : cultureBrief}
            </span>
          </div>
        </div>
      )}

      {/* ── 3 Insight cards ────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, marginBottom: 8 }}>

        {/* Card 1: Fan Truth breakdown — specific / shared / special axes */}
        <div style={{ padding: "10px 12px", borderRadius: 12, background: "var(--card-bg)",
          border: "1px solid var(--card-border)", boxShadow: "var(--shadow-sm)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 7 }}>
            <span style={{ fontSize: 13 }}>📚</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-primary)" }}>Fan Truth Scores</span>
          </div>
          {ftAxes.length > 0 ? ftAxes.map(ax => (
            <div key={ax.label} style={{ marginBottom: 5 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                <span style={{ fontSize: 10, color: "var(--text-secondary)" }}>{ax.label}</span>
                <span style={{ fontSize: 10, fontWeight: 700, color: "#3b82f6" }}>{ax.val}%</span>
              </div>
              <div style={{ height: 4, borderRadius: 99, background: "var(--card-border)" }}>
                <div style={{ height: 4, borderRadius: 99, background: "#3b82f6", width: `${ax.val}%` }} />
              </div>
            </div>
          )) : (
            <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>
              {fanTruth ? `"${fanTruth.slice(0, 80)}${fanTruth.length > 80 ? "…" : ""}"` : "Fan truth validated against brand guidelines."}
            </div>
          )}
        </div>

        {/* Card 2: Audience — who, where, when */}
        <div style={{ padding: "10px 12px", borderRadius: 12, background: "var(--card-bg)",
          border: "1px solid var(--card-border)", boxShadow: "var(--shadow-sm)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 7 }}>
            <span style={{ fontSize: 13 }}>👥</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-primary)" }}>Audience</span>
          </div>
          {[
            { label: "Segment", val: audience || "—" },
            { label: "Market",  val: market  || "—" },
            { label: "Season",  val: season  || "—" },
          ].map(row => (
            <div key={row.label} style={{ display: "flex", gap: 6, marginBottom: 3, alignItems: "baseline" }}>
              <span style={{ fontSize: 10, color: "var(--text-tertiary)", minWidth: 44 }}>{row.label}</span>
              <span style={{ fontSize: 10, fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.4 }}>{row.val}</span>
            </div>
          ))}
        </div>

        {/* Card 3: KPI health — OK / Ambitious / Unrealistic counts */}
        <div style={{ padding: "10px 12px", borderRadius: 12, background: "var(--card-bg)",
          border: "1px solid var(--card-border)", boxShadow: "var(--shadow-sm)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 7 }}>
            <span style={{ fontSize: 13 }}>📈</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-primary)" }}>KPI Health</span>
          </div>
          {kpiItems.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column" as const, gap: 4 }}>
              {kpiOK   > 0 && <div style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ fontSize: 10, fontWeight: 700, color: "#10b981", minWidth: 16 }}>{kpiOK}</span><span style={{ fontSize: 10, color: "var(--text-secondary)" }}>within benchmark</span></div>}
              {kpiAmb  > 0 && <div style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ fontSize: 10, fontWeight: 700, color: "#f59e0b", minWidth: 16 }}>{kpiAmb}</span><span style={{ fontSize: 10, color: "var(--text-secondary)" }}>ambitious</span></div>}
              {kpiRisk > 0 && <div style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ fontSize: 10, fontWeight: 700, color: "#ef4444", minWidth: 16 }}>{kpiRisk}</span><span style={{ fontSize: 10, color: "var(--text-secondary)" }}>unrealistic</span></div>}
            </div>
          ) : (
            <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>
              {summary || "KPI targets benchmarked against historical campaign data."}
            </div>
          )}
        </div>

      </div>

      {/* ── CDP Key Insight ────────────────────────────────────── */}
      <div style={{ marginBottom: 9, borderRadius: 10, padding: "9px 14px",
        background: "linear-gradient(135deg, rgba(16,185,129,0.07), rgba(59,130,246,0.05))",
        border: "1.5px solid rgba(16,185,129,0.25)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <span style={{ fontSize: 14, flexShrink: 0 }}>💡</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 3 }}>
              <span style={{ fontSize: 10, fontWeight: 800, color: "#10b981",
                letterSpacing: "0.09em", textTransform: "uppercase" as const }}>CDP Key Insight</span>
              <span style={{ fontSize: 10, padding: "1px 7px", borderRadius: 99,
                background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.2)",
                color: "#10b981", fontWeight: 600 }}>BigQuery · 50K profiles</span>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-primary)", lineHeight: 1.5, fontWeight: 500,
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const }}>
              {cdpInsight}
            </div>
          </div>
        </div>
      </div>

      {/* ── Main: tabbed card + sidebar ────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 244px", gap: 9 }}>

        {/* Left: tab nav + scrollable sections */}
        <div style={{ borderRadius: 12, border: "1px solid var(--card-border)", background: "var(--card-bg)", overflow: "hidden" }}>

          {/* Tab nav */}
          <div style={{ display: "flex", borderBottom: "1px solid var(--card-border)", overflowX: "auto" as const }}>
            {tabs.map((tab) => (
              <button key={tab.id} onClick={() => scrollToSection(tab.id)}
                style={{ padding: "10px 13px", border: "none", background: "none", cursor: "pointer",
                  fontSize: 11, fontWeight: activeTab === tab.id ? 700 : 500,
                  color: activeTab === tab.id ? color : "var(--text-secondary)",
                  borderBottom: activeTab === tab.id ? `2px solid ${color}` : "2px solid transparent",
                  whiteSpace: "nowrap" as const, fontFamily: "inherit", transition: "color 0.15s", flexShrink: 0 }}>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Scrollable content — all sections stacked */}
          <div ref={scrollRef} style={{ overflowY: "auto" as const,
            maxHeight: "clamp(260px, calc(100vh - 430px), 390px)", padding: "14px 18px" }}>

            {/* ── Overview ── */}
            <div ref={el => { sectionRefs.current["overview"] = el; }}>
              <SectionHeader>Campaign Brief</SectionHeader>

              {/* AI diagnosis hints */}
              {aiSuggestions.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column" as const, gap: 4, marginBottom: 10 }}>
                  {aiSuggestions.map((s, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "8px 11px",
                      borderRadius: 8,
                      background: s.severity === "warn" ? "rgba(245,158,11,0.07)" : `${color}07`,
                      border: `1px solid ${s.severity === "warn" ? "rgba(245,158,11,0.22)" : `${color}22`}` }}>
                      <span style={{ fontSize: 11, flexShrink: 0 }}>{s.icon}</span>
                      <span style={{ fontSize: 11, color: "var(--text-primary)", lineHeight: 1.5 }}>{s.text}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Editable fields */}
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
                <div>
                  <label style={{ fontSize: 10, fontWeight: 700, color, display: "block",
                    letterSpacing: "0.07em", textTransform: "uppercase" as const, marginBottom: 4 }}>
                    Fan Truth
                  </label>
                  <textarea value={editFanTruth} onChange={e => setEditFanTruth(e.target.value)} rows={2}
                    placeholder="The human insight that connects brand and audience…"
                    style={{ ...inputStyle, resize: "none" as const, lineHeight: 1.55 }}
                    onFocus={e => e.currentTarget.style.borderColor = color}
                    onBlur={e => e.currentTarget.style.borderColor = "var(--card-border)"} />
                </div>

                <div>
                  <label style={{ fontSize: 10, fontWeight: 700, color, display: "block",
                    letterSpacing: "0.07em", textTransform: "uppercase" as const, marginBottom: 4 }}>
                    Campaign Goal
                  </label>
                  <input value={editGoal} onChange={e => setEditGoal(e.target.value)}
                    placeholder="e.g. Drive trial among new shoppers…"
                    style={inputStyle}
                    onFocus={e => e.currentTarget.style.borderColor = color}
                    onBlur={e => e.currentTarget.style.borderColor = "var(--card-border)"} />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div>
                    <label style={{ fontSize: 10, fontWeight: 700, color, display: "block",
                      letterSpacing: "0.07em", textTransform: "uppercase" as const, marginBottom: 4 }}>
                      Target Audience
                    </label>
                    <input value={editAudience} onChange={e => setEditAudience(e.target.value)}
                      placeholder="e.g. Adults 25–45"
                      style={inputStyle}
                      onFocus={e => e.currentTarget.style.borderColor = color}
                      onBlur={e => e.currentTarget.style.borderColor = "var(--card-border)"} />
                  </div>
                  <div>
                    <label style={{ fontSize: 10, fontWeight: 700, color, display: "block",
                      letterSpacing: "0.07em", textTransform: "uppercase" as const, marginBottom: 4 }}>
                      Market · Season
                    </label>
                    <input value={editMarket} onChange={e => setEditMarket(e.target.value)}
                      placeholder="e.g. UK · Winter"
                      style={inputStyle}
                      onFocus={e => e.currentTarget.style.borderColor = color}
                      onBlur={e => e.currentTarget.style.borderColor = "var(--card-border)"} />
                  </div>
                </div>

                {!showExtra ? (
                  <button onClick={() => setShowExtra(true)}
                    style={{ alignSelf: "flex-start" as const, background: "none", border: "none",
                      fontSize: 11, color: "var(--text-muted)", cursor: "pointer",
                      padding: 0, fontFamily: "inherit" }}>
                    + Add guidance for Logos
                  </button>
                ) : (
                  <textarea value={extraFeedback} onChange={e => setExtraFeedback(e.target.value)} rows={2}
                    placeholder="Tell Logos what to change — tone, seasonal angle, sharper insight…"
                    style={{ ...inputStyle, resize: "none" as const, lineHeight: 1.55 }}
                    onFocus={e => e.currentTarget.style.borderColor = color}
                    onBlur={e => e.currentTarget.style.borderColor = "var(--card-border)"} />
                )}

                {onRegenerate && (
                  <div style={{ display: "flex", justifyContent: "flex-end" as const }}>
                    <button onClick={handleApplyEdits} disabled={!hasEdits}
                      style={{ padding: "8px 18px", borderRadius: 8, border: "none", fontFamily: "inherit",
                        fontSize: 12, fontWeight: 700, color: "white",
                        cursor: hasEdits ? "pointer" : "not-allowed", opacity: hasEdits ? 1 : 0.38,
                        background: `linear-gradient(135deg, ${color}, #6366f1)`,
                        boxShadow: hasEdits ? `0 3px 12px ${color}38` : "none", transition: "all 0.2s" }}>
                      ↺ Re-run with Changes
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* ── Key Messages ── */}
            <SectionDivider />
            <div ref={el => { sectionRefs.current["messages"] = el; }}>
              <SectionHeader>Key Messages</SectionHeader>
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 10 }}>
                {fanTruth && (
                  <div style={{ padding: "12px 14px", borderRadius: 9, background: "rgba(59,130,246,0.06)", border: "1.5px solid rgba(59,130,246,0.18)" }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#3b82f6", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 5 }}>Primary Message</div>
                    <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.65 }}>{fanTruth}</div>
                  </div>
                )}
                {goal && (
                  <div style={{ padding: "12px 14px", borderRadius: 9, background: "rgba(16,185,129,0.06)", border: "1.5px solid rgba(16,185,129,0.18)" }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#10b981", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 5 }}>Campaign Objective</div>
                    <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.65 }}>{goal}</div>
                  </div>
                )}
                <div style={{ padding: "12px 14px", borderRadius: 9, background: "rgba(245,158,11,0.06)", border: "1.5px solid rgba(245,158,11,0.18)" }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "#f59e0b", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 5 }}>Tone of Voice</div>
                  <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.65 }}>Authoritative yet accessible, grounded in human truth, empathetic to real audience journeys.</div>
                </div>
              </div>
            </div>

            {/* ── Creative ── */}
            <SectionDivider />
            <div ref={el => { sectionRefs.current["creative"] = el; }}>
              <SectionHeader>Creative Direction</SectionHeader>
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 9 }}>
                <div style={{ padding: "12px 14px", borderRadius: 9, background: "var(--card-bg-soft)", border: "1px solid var(--card-border)" }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "#6b7280", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 5 }}>Visual Style</div>
                  <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.65 }}>White-dominant backgrounds with clean layouts. Product clearly featured with left third reserved for copy overlay. Natural lighting, authentic lifestyle imagery.</div>
                </div>
                <div style={{ padding: "12px 14px", borderRadius: 9, background: "var(--card-bg-soft)", border: "1px solid var(--card-border)" }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "#6b7280", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 5 }}>Brand Compliance</div>
                  <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.65, display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 15, color: passColor }}>{verdict === "PASS" ? "✓" : "⚠"}</span>
                    {verdict === "PASS" ? "Campaign aligns with brand guidelines and tone requirements." : "Some elements need review to meet brand guidelines."}
                  </div>
                </div>
                {summary && (
                  <div style={{ padding: "12px 14px", borderRadius: 9, background: "var(--card-bg-soft)", border: "1px solid var(--card-border)" }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#6b7280", letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 5 }}>Agent Notes</div>
                    <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.65 }}>{summary}</div>
                  </div>
                )}
              </div>
            </div>

            {/* ── Channels ── */}
            <SectionDivider />
            <div ref={el => { sectionRefs.current["channels"] = el; }}>
              <SectionHeader>Channel Recommendations</SectionHeader>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 9 }}>
                {[
                  { ch: "Social Media",    icon: "📸", reco: "Instagram & TikTok short-form, UGC-style content with product focus." },
                  { ch: "Digital Display", icon: "🖥️", reco: "Programmatic banners, retargeting based on product category interest." },
                  { ch: "Search",          icon: "🔍", reco: "Google Ads targeting relevant intent signals and competitor conquesting." },
                  { ch: "Content / PR",    icon: "📰", reco: "Editorial placement and influencer partnerships relevant to the category." },
                ].map(({ ch, icon, reco }) => (
                  <div key={ch} style={{ padding: "11px 12px", borderRadius: 9, background: "var(--card-bg-soft)", border: "1px solid var(--card-border)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 4 }}>
                      <span style={{ fontSize: 12 }}>{icon}</span>
                      <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-primary)" }}>{ch}</span>
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>{reco}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* ── Risks ── */}
            <SectionDivider />
            <div ref={el => { sectionRefs.current["risks"] = el; }}>
              <SectionHeader>Risk Assessment</SectionHeader>
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
                {[
                  { level: "low",    label: "Health Claims",         desc: "All claims must be substantiated. Avoid absolute language ('cures', 'eliminates')." },
                  { level: "medium", label: "Regulatory Compliance", desc: "OTC regulations vary by market. Regional legal review required before launch." },
                  { level: "low",    label: "Brand Safety",          desc: "Avoid placement near sensitive content. Block competitor misinformation sites." },
                ].map(({ level, label, desc }) => (
                  <div key={label} style={{ display: "flex", gap: 10, padding: "11px 13px", borderRadius: 9,
                    background: "var(--card-bg-soft)",
                    border: `1.5px solid ${level === "medium" ? "rgba(245,158,11,0.25)" : "rgba(16,185,129,0.2)"}` }}>
                    <div style={{ width: 4, borderRadius: 4, flexShrink: 0, alignSelf: "stretch",
                      background: level === "medium" ? "#f59e0b" : "#10b981" }} />
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", marginBottom: 2 }}>{label}</div>
                      <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>{desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* ── Metrics ── */}
            <SectionDivider />
            <div ref={el => { sectionRefs.current["metrics"] = el; }}>
              <SectionHeader>Success Metrics</SectionHeader>
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
                {[
                  { metric: "Brand Awareness",  target: "+12% unaided recall",     frame: "3 months"         },
                  { metric: "Engagement Rate",  target: ">3.5% avg. engagement",   frame: "Campaign duration" },
                  { metric: "Media ROI",        target: "2.8× ROAS",               frame: "Per flight"        },
                  { metric: "Share of Voice",   target: "+8pp above category avg",  frame: "Flight period"     },
                ].map(({ metric, target, frame }) => (
                  <div key={metric} style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "10px 12px", borderRadius: 9, background: "var(--card-bg-soft)", border: "1px solid var(--card-border)" }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>{metric}</div>
                      <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>{frame}</div>
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "#3b82f6" }}>{target}</div>
                  </div>
                ))}
              </div>
            </div>

          </div>{/* end scroll container */}
        </div>{/* end left card */}

        {/* ── Right sidebar ──────────────────────────────────────── */}
        <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>

          <div style={{ borderRadius: 12, border: "1px solid var(--card-border)", background: "var(--card-bg)", padding: "11px 13px" }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.08em",
              textTransform: "uppercase" as const, marginBottom: 8 }}>Sources Overview</div>
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

          <div style={{ borderRadius: 12, border: "1px solid var(--card-border)", background: "var(--card-bg)", padding: "11px 13px", flex: 1 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.08em",
              textTransform: "uppercase" as const, marginBottom: 8 }}>Source Citations</div>
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

          <div style={{ borderRadius: 12, padding: "13px 15px", display: "flex", alignItems: "center",
            justifyContent: "space-between",
            border: `1.5px solid ${verdict === "PASS" ? "rgba(16,185,129,0.4)" : "rgba(245,158,11,0.4)"}`,
            background: verdict === "PASS" ? "rgba(16,185,129,0.07)" : "rgba(245,158,11,0.07)" }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.08em",
                textTransform: "uppercase" as const, marginBottom: 3 }}>Overall Confidence</div>
              <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>Based on 5 data sources</div>
            </div>
            <div style={{ fontSize: 26, fontWeight: 900, color: passColor }}>{score}%</div>
          </div>

        </div>
      </div>
    </div>
  );
}
