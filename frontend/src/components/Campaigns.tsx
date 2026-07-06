import { useState } from "react";

const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────
type FormatType = "image" | "video" | "reel" | "tvc";
type ImageSize  = "1:1" | "4:5" | "16:9" | "9:16";
type VideoLen   = "15s" | "30s" | "45s" | "60s";
type TVCLen     = "15" | "30";

interface GeneratedResult {
  image_b64?:   string;
  video_b64?:   string;
  scene_clips?: string[];
  headline?:    string;
  body?:        string;
  tagline?:     string;
}

// ── Shared small components ────────────────────────────────────
const StepBadge = ({ n, active, done }: { n: number; active: boolean; done: boolean }) => (
  <div style={{
    width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 12, fontWeight: 800,
    background: done ? "#10b981" : active ? "linear-gradient(135deg,#7c3aed,#6366f1)" : "var(--card-bg-soft)",
    color: done || active ? "white" : "var(--text-secondary)",
    border: done || active ? "none" : "1.5px solid var(--card-border)",
  }}>{done ? "✓" : n}</div>
);

// ── Format Card ────────────────────────────────────────────────
function FormatCard({ label, icon, desc, selected, onClick, sizes, selectedSize, onSize }: {
  id?: FormatType; label: string; icon: string; desc: string;
  selected: boolean; onClick: () => void;
  sizes: string[]; selectedSize: string; onSize: (s: string) => void;
}) {
  return (
    <div onClick={onClick} style={{
      padding: 16, borderRadius: 14, cursor: "pointer", transition: "all 0.15s",
      border: `2px solid ${selected ? "#7c3aed" : "var(--card-border)"}`,
      background: selected ? "rgba(124,58,237,0.08)" : "var(--card-bg-soft)",
      position: "relative" as const,
    }}>
      {selected && (
        <div style={{ position: "absolute" as const, top: 10, right: 10,
          width: 20, height: 20, borderRadius: "50%",
          background: "linear-gradient(135deg,#7c3aed,#6366f1)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 10, color: "white", fontWeight: 800 }}>✓</div>
      )}
      <div style={{ fontSize: 22, marginBottom: 8 }}>{icon}</div>
      <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: 12 }}>{desc}</div>
      {selected && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" as const }}>
          {sizes.map(s => (
            <button key={s} onClick={e => { e.stopPropagation(); onSize(s); }}
              style={{ padding: "3px 10px", borderRadius: 6, border: "none", cursor: "pointer",
                fontSize: 11, fontWeight: 600,
                background: selectedSize === s ? "#7c3aed" : "var(--card-bg)",
                color: selectedSize === s ? "white" : "var(--text-secondary)" }}>
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────
export default function Campaigns() {
  // Step 1 — Brief
  const [brief, setBrief]         = useState("");
  const [brand, setBrand]         = useState("");
  const [goal, setGoal]           = useState("");
  const [audience, setAudience]   = useState("");
  const [platform, setPlatform]   = useState("");

  // Step 2 — Format
  const [formats, setFormats]     = useState<Set<FormatType>>(new Set());
  const [imgSize, setImgSize]     = useState<ImageSize>("16:9");
  const [vidLen, setVidLen]       = useState<VideoLen>("30s");
  const [tvcLen, setTvcLen]       = useState<TVCLen>("15");

  // Step 3 — Copy
  const [copyResult, setCopyResult] = useState<{headline:string;body:string;cta:string}|null>(null);
  const [copyLoading, setCopyLoading] = useState(false);

  // Step 4 — Generate
  const [generating, setGenerating] = useState(false);
  const [results, setResults]       = useState<Record<FormatType, GeneratedResult>>({} as any);
  const [previewTab, setPreviewTab] = useState<FormatType>("image");
  const [activeStep, setActiveStep] = useState(1);

  const brands   = ["Rnorr", "Sunglow", "Boozt", "Glenfiddich", "UBS Bank"];
  const goals    = ["Brand Awareness", "Drive Sales", "Lead Generation", "Product Launch", "Engagement"];
  const audiences = ["Women 18–35", "Men 25–45", "Gen Z 16–24", "Professionals 30–50", "Families"];
  const platforms = ["Instagram", "TikTok", "YouTube", "LinkedIn", "Facebook"];

  const promptForAgent = `${brand ? `Brand: ${brand}. ` : ""}${brief}${goal ? ` Goal: ${goal}.` : ""}${audience ? ` Audience: ${audience}.` : ""}${platform ? ` Platform: ${platform}.` : ""}`;

  // Step 3: Generate copy
  const generateCopy = async () => {
    if (!brief.trim()) return;
    setCopyLoading(true);
    try {
      const res = await fetch(`${API_BASE}/agents/copy/run`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: promptForAgent }),
      });
      const data = await res.json();
      setCopyResult({
        headline: data.short?.headline || data.headline || "",
        body:     data.long?.body      || data.body     || "",
        cta:      data.cta             || "Learn More",
      });
      setActiveStep(4);
    } catch { /* ignore */ } finally { setCopyLoading(false); }
  };

  // Step 4: Generate content
  const generateContent = async () => {
    if (!brief.trim() || formats.size === 0) return;
    setGenerating(true);
    const newResults: Record<FormatType, GeneratedResult> = {} as any;

    for (const fmt of Array.from(formats)) {
      try {
        const body: Record<string, unknown> = { prompt: promptForAgent };
        if (fmt === "tvc") body.duration = parseInt(tvcLen);

        const agentKey = fmt === "image" ? "kv" : fmt === "tvc" ? "tvc" : "reel";
        const res = await fetch(`${API_BASE}/agents/${agentKey}/run`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const data = await res.json();
        newResults[fmt] = data;
        // Show first result as soon as it arrives
        setResults(prev => ({ ...prev, [fmt]: data }));
        setPreviewTab(fmt);
      } catch { /* ignore */ }
    }
    setGenerating(false);
  };

  const toggleFormat = (f: FormatType) => {
    setFormats(prev => {
      const next = new Set(prev);
      next.has(f) ? next.delete(f) : next.add(f);
      return next;
    });
    setActiveStep(s => Math.max(s, 2));
  };

  const hasResult = (f: FormatType) => !!results[f]?.image_b64 || !!results[f]?.video_b64;
  const anyResult = Object.values(results).some(r => r?.image_b64 || r?.video_b64);

  const sel = { background: "var(--card-bg-soft)", border: "1.5px solid var(--card-border)",
    color: "var(--text-primary)", fontFamily: "inherit", fontSize: 12, borderRadius: 8,
    padding: "7px 10px", outline: "none", cursor: "pointer", width: "100%" };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" as const,
      overflow: "hidden", height: "100vh" }}>

      {/* ── Header ── */}
      <div style={{ padding: "18px 28px", display: "flex", alignItems: "center",
        justifyContent: "space-between", borderBottom: "1px solid var(--card-border)",
        background: "var(--card-bg)", flexShrink: 0 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: "var(--text-primary)" }}>
            Create New Campaign ✨
          </h1>
          <p style={{ margin: "3px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
            Describe your idea and AI agents will generate on-brand content across formats.
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button style={{ padding: "9px 20px", borderRadius: 10, fontWeight: 600, fontSize: 13,
            border: "1.5px solid var(--card-border)", background: "transparent",
            color: "var(--text-primary)", cursor: "pointer" }}>
            Save Draft
          </button>
          <button onClick={generateContent}
            disabled={generating || formats.size === 0 || !brief.trim()}
            style={{ padding: "9px 22px", borderRadius: 10, fontWeight: 700, fontSize: 13,
              border: "none", cursor: formats.size > 0 && brief.trim() ? "pointer" : "not-allowed",
              background: "linear-gradient(135deg,#7c3aed,#6366f1)", color: "white",
              opacity: formats.size === 0 || !brief.trim() ? 0.5 : 1,
              display: "flex", alignItems: "center", gap: 8 }}>
            {generating ? "⏳ Generating…" : "✦ Generate Content"}
          </button>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* ── LEFT: Steps ── */}
        <div style={{ width: 520, flexShrink: 0, overflowY: "auto",
          borderRight: "1px solid var(--card-border)", padding: "24px 28px",
          display: "flex", flexDirection: "column" as const, gap: 28 }}>

          {/* Step 1 — Campaign Brief */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
              <StepBadge n={1} active={activeStep === 1} done={activeStep > 1 && !!brief.trim()} />
              <div>
                <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>Campaign Brief</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Describe what you want to create</div>
              </div>
            </div>
            <textarea value={brief} onChange={e => { setBrief(e.target.value); setActiveStep(1); }}
              placeholder="Create a Christmas campaign for Rnorr stock cubes targeting UK families. Warm, festive, family-focused — show the joy of cooking together."
              rows={5}
              style={{ width: "100%", padding: "14px 16px", borderRadius: 12, resize: "none" as const,
                border: "1.5px solid var(--card-border)", background: "var(--card-bg-soft)",
                color: "var(--text-primary)", fontFamily: "inherit", fontSize: 13,
                lineHeight: 1.6, outline: "none", boxSizing: "border-box" as const,
                transition: "border-color 0.15s" }}
              onFocus={e => e.currentTarget.style.borderColor = "#7c3aed"}
              onBlur={e => e.currentTarget.style.borderColor = "var(--card-border)"} />
            <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" as const }}>
              {[
                { label: "Brand", value: brand, set: setBrand, opts: brands },
                { label: "Goal",  value: goal,  set: setGoal,  opts: goals },
                { label: "Audience", value: audience, set: setAudience, opts: audiences },
                { label: "Platform", value: platform, set: setPlatform, opts: platforms },
              ].map(f => (
                <div key={f.label} style={{ flex: 1, minWidth: 110 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                    marginBottom: 4, textTransform: "uppercase" as const, letterSpacing: ".06em" }}>
                    {f.label}
                  </div>
                  <select value={f.value} onChange={e => { f.set(e.target.value); setActiveStep(s => Math.max(s, 1)); }}
                    style={sel}>
                    <option value="">Select…</option>
                    {f.opts.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>
              ))}
            </div>
            {brief.trim() && (
              <button onClick={() => setActiveStep(2)}
                style={{ marginTop: 12, padding: "8px 20px", borderRadius: 8, border: "none",
                  background: "linear-gradient(135deg,#7c3aed,#6366f1)", color: "white",
                  fontWeight: 600, fontSize: 12, cursor: "pointer" }}>
                Next: Choose Format →
              </button>
            )}
          </div>

          {/* Step 2 — Choose Format */}
          <div style={{ opacity: activeStep >= 2 ? 1 : 0.4, transition: "opacity 0.2s",
            pointerEvents: activeStep >= 2 ? "auto" : "none" as any }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
              <StepBadge n={2} active={activeStep === 2} done={activeStep > 2 && formats.size > 0} />
              <div>
                <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>Choose Format</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Select content type — choose one or multiple</div>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <FormatCard id="image" label="Image" icon="🎨" desc="Key visuals, hero banners & social posts."
                selected={formats.has("image")} onClick={() => toggleFormat("image")}
                sizes={["1:1","4:5","16:9","9:16"]} selectedSize={imgSize}
                onSize={s => setImgSize(s as ImageSize)} />
              <FormatCard id="reel" label="Reel" icon="🎬" desc="6-second Veo reels for social media."
                selected={formats.has("reel")} onClick={() => toggleFormat("reel")}
                sizes={["9:16","16:9"]} selectedSize="9:16" onSize={() => {}} />
              <FormatCard id="tvc" label="TVC" icon="📺" desc="15s or 30s TV commercials via Veo."
                selected={formats.has("tvc")} onClick={() => toggleFormat("tvc")}
                sizes={["15s","30s"]} selectedSize={tvcLen + "s"}
                onSize={s => setTvcLen(s.replace("s","") as TVCLen)} />
              <FormatCard id="video" label="Video Ad" icon="▶️" desc="Longer video ads up to 60s."
                selected={formats.has("video")} onClick={() => toggleFormat("video")}
                sizes={["15s","30s","45s","60s"]} selectedSize={vidLen}
                onSize={s => setVidLen(s as VideoLen)} />
            </div>
            {formats.size > 0 && (
              <button onClick={() => setActiveStep(3)}
                style={{ marginTop: 12, padding: "8px 20px", borderRadius: 8, border: "none",
                  background: "linear-gradient(135deg,#7c3aed,#6366f1)", color: "white",
                  fontWeight: 600, fontSize: 12, cursor: "pointer" }}>
                Next: Copy Agent →
              </button>
            )}
          </div>

          {/* Step 3 — Copy Agent (Ideon) */}
          <div style={{ opacity: activeStep >= 3 ? 1 : 0.4, transition: "opacity 0.2s",
            pointerEvents: activeStep >= 3 ? "auto" : "none" as any }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
              <StepBadge n={3} active={activeStep === 3} done={!!copyResult} />
              <div>
                <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>Copy Agent — Ideon</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Generate headlines, body copy and CTAs</div>
              </div>
            </div>
            {copyResult ? (
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 10 }}>
                {[
                  { label: "Headline", val: copyResult.headline },
                  { label: "Body",     val: copyResult.body },
                  { label: "CTA",      val: copyResult.cta },
                ].map(f => (
                  <div key={f.label}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                      textTransform: "uppercase" as const, letterSpacing: ".06em", marginBottom: 4 }}>
                      {f.label}
                    </div>
                    <div style={{ padding: "10px 14px", borderRadius: 10,
                      background: "var(--card-bg-soft)", border: "1px solid var(--card-border)",
                      fontSize: 13, color: "var(--text-primary)", lineHeight: 1.5 }}>
                      {f.val}
                    </div>
                  </div>
                ))}
                <button onClick={generateCopy} disabled={copyLoading}
                  style={{ alignSelf: "flex-start" as const, padding: "6px 16px", borderRadius: 8,
                    border: "1.5px solid var(--card-border)", background: "transparent",
                    color: "var(--text-secondary)", fontSize: 12, cursor: "pointer" }}>
                  ↻ Regenerate Copy
                </button>
              </div>
            ) : (
              <button onClick={generateCopy} disabled={copyLoading || !brief.trim()}
                style={{ padding: "10px 24px", borderRadius: 10, border: "none",
                  background: "linear-gradient(135deg,#7c3aed,#6366f1)", color: "white",
                  fontWeight: 700, fontSize: 13, cursor: "pointer",
                  opacity: !brief.trim() ? 0.5 : 1 }}>
                {copyLoading ? "✍️ Writing copy…" : "✍️ Generate Copy with Ideon"}
              </button>
            )}
          </div>

          {/* Step 4 — Generate */}
          <div style={{ opacity: activeStep >= 4 ? 1 : 0.4, transition: "opacity 0.2s",
            pointerEvents: activeStep >= 4 ? "auto" : "none" as any }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
              <StepBadge n={4} active={activeStep === 4} done={anyResult} />
              <div>
                <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>Generate Content</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  {formats.size > 0
                    ? `Will generate: ${Array.from(formats).map(f => f === "image" ? "Image (Morphis)" : f === "reel" ? "Reel (Kinetik)" : f === "tvc" ? `TVC ${tvcLen}s (Director)` : "Video").join(" · ")}`
                    : "Select a format above"}
                </div>
              </div>
            </div>
            <button onClick={generateContent}
              disabled={generating || formats.size === 0 || !brief.trim()}
              style={{ padding: "12px 28px", borderRadius: 12, border: "none",
                background: "linear-gradient(135deg,#7c3aed,#a855f7,#6366f1)", color: "white",
                fontWeight: 700, fontSize: 14, cursor: "pointer",
                boxShadow: "0 4px 20px rgba(124,58,237,0.4)",
                opacity: formats.size === 0 || !brief.trim() ? 0.5 : 1 }}>
              {generating ? "⏳ Generating content…" : "✦ Generate Content"}
            </button>
          </div>
        </div>

        {/* ── RIGHT: Preview ── */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px 28px",
          display: "flex", flexDirection: "column" as const, gap: 20 }}>

          {/* Preview header */}
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)", marginBottom: 4 }}>
              AI Campaign Preview
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              See how your campaign could look in different formats.
            </div>
          </div>

          {/* Format tabs */}
          {anyResult && (
            <div style={{ display: "flex", gap: 8, borderBottom: "1px solid var(--card-border)",
              paddingBottom: 0 }}>
              {(["image","reel","tvc","video"] as FormatType[]).filter(f => hasResult(f)).map(f => (
                <button key={f} onClick={() => setPreviewTab(f)}
                  style={{ padding: "8px 18px", border: "none", cursor: "pointer",
                    background: "transparent", fontFamily: "inherit", fontSize: 13,
                    fontWeight: previewTab === f ? 700 : 500,
                    color: previewTab === f ? "#7c3aed" : "var(--text-secondary)",
                    borderBottom: `2px solid ${previewTab === f ? "#7c3aed" : "transparent"}`,
                    transition: "all 0.15s" }}>
                  {f === "image" ? "🎨 Image" : f === "reel" ? "🎬 Reel" : f === "tvc" ? "📺 TVC" : "▶️ Video"}
                </button>
              ))}
            </div>
          )}

          {/* Preview content */}
          {!anyResult && !generating ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
              flexDirection: "column" as const, gap: 16, opacity: 0.5 }}>
              <div style={{ fontSize: 48 }}>✦</div>
              <div style={{ fontSize: 14, color: "var(--text-secondary)", textAlign: "center" as const }}>
                Fill in your brief and generate content<br/>to see the preview here
              </div>
            </div>
          ) : generating ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
              flexDirection: "column" as const, gap: 16 }}>
              <div style={{ fontSize: 36, animation: "hub-beat 1.5s ease-in-out infinite" }}>⏳</div>
              <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>Generating your campaign…</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)", opacity: 0.7 }}>
                {Array.from(formats).map(f =>
                  f === "tvc" ? `TVC ${tvcLen}s (Director)` :
                  f === "image" ? "Image (Morphis)" :
                  f === "reel" ? "Reel (Kinetik)" : "Video"
                ).join(" · ")}
              </div>
            </div>
          ) : hasResult(previewTab) ? (
            <div style={{ display: "flex", flexDirection: "column" as const, gap: 16 }}>
              {/* Image preview */}
              {previewTab === "image" && results.image?.image_b64 && (
                <div style={{ borderRadius: 16, overflow: "hidden", boxShadow: "var(--shadow-md)" }}>
                  <img src={`data:image/jpeg;base64,${results.image.image_b64}`}
                    style={{ width: "100%", display: "block" }} alt="Campaign visual" />
                </div>
              )}
              {/* Video/Reel/TVC preview */}
              {(previewTab === "reel" || previewTab === "tvc" || previewTab === "video") &&
                (results[previewTab]?.video_b64) && (
                <div style={{ borderRadius: 16, overflow: "hidden", boxShadow: "var(--shadow-md)" }}>
                  <video controls autoPlay loop muted playsInline
                    src={`data:video/mp4;base64,${results[previewTab].video_b64}`}
                    style={{ width: "100%", display: "block" }} />
                </div>
              )}
              {/* Headline */}
              {copyResult && (
                <div style={{ padding: "14px 18px", borderRadius: 12,
                  background: "var(--card-bg)", border: "1px solid var(--card-border)" }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 6,
                    fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: ".06em" }}>
                    Campaign Headline
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
                    {copyResult.headline}
                  </div>
                </div>
              )}
            </div>
          ) : null}

          {/* Campaign Insights */}
          {anyResult && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              {[
                { label: "Best Format", value: formats.has("reel") ? "Reel" : "Image",
                  sub: "92% higher engagement", icon: "🏆" },
                { label: "Top Platform", value: platform || "Instagram",
                  sub: "76% of your audience", icon: "📱" },
                { label: "Best Time to Post", value: "7:00 PM",
                  sub: "Today · Peak engagement", icon: "🕖" },
              ].map(i => (
                <div key={i.label} style={{ padding: "14px 16px", borderRadius: 12,
                  background: "var(--card-bg)", border: "1px solid var(--card-border)" }}>
                  <div style={{ fontSize: 18, marginBottom: 6 }}>{i.icon}</div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)",
                    textTransform: "uppercase" as const, letterSpacing: ".06em", marginBottom: 4 }}>
                    {i.label}
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)", marginBottom: 2 }}>
                    {i.value}
                  </div>
                  <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>{i.sub}</div>
                </div>
              ))}
            </div>
          )}

          {/* Brand Compliance */}
          {anyResult && brand && (
            <div style={{ padding: "16px 20px", borderRadius: 14,
              background: "var(--card-bg)", border: "1px solid var(--card-border)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>Brand Compliance</div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                    AI checks your content against brand guidelines
                  </div>
                </div>
                <div style={{ fontSize: 24, fontWeight: 900, color: "#10b981" }}>98%</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 6 }}>
                {["Brand colours", "Logo placement", "Typography", "Tone of voice", "Brand locks"].map(c => (
                  <div key={c} style={{ display: "flex", alignItems: "center", gap: 8,
                    fontSize: 12, color: "var(--text-secondary)" }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981"
                      strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                    {c}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
