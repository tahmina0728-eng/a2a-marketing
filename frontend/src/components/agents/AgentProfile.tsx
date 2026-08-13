import { useState, useEffect } from "react";
import {
  HARNESS_STAGES, AGENT_COLORS, AGENT_DESCS, avatarUrl,
  WORKFLOW_STAGES, AGENT_INTROS, speakAgentIntro,
} from "../../constants/agents";
import BrandUploadPanel from "./BrandUploadPanel";
import AgentRunPanel from "./AgentRunPanel";

export default function AgentProfile({ agentKey, prompt, onPromptChange }: {
  agentKey: string;
  prompt: string; onPromptChange: (v: string) => void;
}) {
  const idx   = HARNESS_STAGES.findIndex((s) => s.key === agentKey);
  const stage = HARNESS_STAGES[idx];

  const color    = AGENT_COLORS[idx] ?? "#7c3aed";
  const longDesc = AGENT_DESCS[idx] ?? (stage?.desc ?? "");
  const avatar   = avatarUrl(stage?.label ?? "", idx);
  const workflowStage = WORKFLOW_STAGES.find((w) => w.agents.includes(agentKey))?.label ?? "";

  const [briefingDone,     setBriefingDone]     = useState(false);
  const [performanceDone, setPerformanceDone] = useState(false);

  const [speaking, setSpeaking] = useState(false);
  useEffect(() => {
    setSpeaking(true);
    speakAgentIntro(agentKey, () => setSpeaking(false));
    return () => { window.speechSynthesis?.cancel(); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentKey]);

  if (!stage) return null;

  const showHeader = !(agentKey === "briefing" && briefingDone) && !(agentKey === "performance" && performanceDone);

  return (
    <div style={{
      flex: 1, overflowY: "auto" as const,
      padding: showHeader ? "40px 48px" : "40px 48px",
      display: "flex", flexDirection: "column" as const,
      alignItems: "center", justifyContent: "center",
      position: "relative" as const, background: "transparent",
    }}>
      {showHeader && (
        <div style={{ position: "absolute" as const, inset: 0, zIndex: 0, pointerEvents: "none" as const,
          background: `radial-gradient(ellipse 70% 55% at 50% 40%, ${color}14 0%, transparent 70%)` }} />
      )}

      <div style={{
        maxWidth: agentKey === "performance" ? 900 : (showHeader ? 720 : 860),
        width: "100%",
        margin: "auto",
        position: "relative" as const, zIndex: 1,
      }}>

        {showHeader && (
          <div style={{ position: "relative" as const, overflow: "hidden", padding: "8px 4px 10px" }}>
            <div style={{ position: "absolute" as const, top: "-40%", right: "-10%", width: 320, height: 320,
              borderRadius: "50%", pointerEvents: "none" as const,
              background: `radial-gradient(circle, ${color}22 0%, transparent 70%)` }} />

            <div style={{ position: "relative" as const, zIndex: 1, display: "flex", alignItems: "center", gap: 20, marginBottom: 24 }}>
              <div style={{
                width: 76, height: 76, borderRadius: "50%", flexShrink: 0, position: "relative" as const,
                border: `3px solid ${color}80`, boxShadow: `0 0 28px ${color}40`, overflow: "hidden",
              }}>
                <img src={avatar} alt={stage.label} style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ fontSize: 28, fontWeight: 900, color: "var(--text-primary)", lineHeight: 1.1 }}>
                    {stage.label}
                  </div>
                  <button
                    onClick={() => {
                      if (speaking) { window.speechSynthesis?.cancel(); setSpeaking(false); }
                      else { setSpeaking(true); speakAgentIntro(agentKey, () => setSpeaking(false)); }
                    }}
                    title={speaking ? "Stop voice" : "Replay introduction"}
                    style={{ width: 32, height: 32, borderRadius: "50%", border: "none",
                      background: speaking ? `${color}28` : `${color}18`,
                      cursor: "pointer", flexShrink: 0,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      color, transition: "all 0.15s",
                      boxShadow: speaking ? `0 0 0 3px ${color}30` : "none" }}>
                    {speaking ? (
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
                    ) : (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                        <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
                        <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
                      </svg>
                    )}
                  </button>
                </div>
                {workflowStage && (
                  <span style={{ display: "inline-block", marginTop: 6, fontSize: 11, fontWeight: 700,
                    padding: "3px 10px", borderRadius: 99, letterSpacing: "0.04em",
                    background: `${color}18`, color }}>{workflowStage}</span>
                )}
              </div>
            </div>

            <p style={{ position: "relative" as const, zIndex: 1, fontSize: 16, color: "var(--text-primary)",
              lineHeight: 1.6, margin: "0 0 12px", textShadow: "0 1px 6px rgba(255,255,255,0.25)" }}>
              {longDesc}
            </p>
            {AGENT_INTROS[agentKey] && (
              <p style={{ position: "relative" as const, zIndex: 1, fontSize: 14,
                color: "var(--text-secondary)", lineHeight: 1.7, margin: "0 0 24px",
                fontStyle: "italic", borderLeft: `3px solid ${color}50`, paddingLeft: 14 }}>
                "{AGENT_INTROS[agentKey]}"
              </p>
            )}
          </div>
        )}

        {agentKey === "briefing" && showHeader && !prompt.trim() && <BrandUploadPanel />}

        <AgentRunPanel agentKey={agentKey} agentLabel={stage.label} color={color}
          prompt={prompt} onPromptChange={onPromptChange}
          onBriefingDone={() => setBriefingDone(true)}
          onPerformanceDone={() => setPerformanceDone(true)} />
      </div>
    </div>
  );
}
