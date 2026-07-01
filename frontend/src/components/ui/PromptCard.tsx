interface PromptCardProps {
  value: string;
  onChange: (v: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  loading?: boolean;
  loadingLabel?: string;
  accentColor?: string;
}

/**
 * Shared prompt-input card used on every standalone-agent page and
 * the campaign form objective field. Uses inline styles so it renders
 * correctly regardless of whether Tailwind has fully processed.
 */
export default function PromptCard({
  value,
  onChange,
  onSubmit,
  placeholder = "Describe your brand, market, and campaign direction — I'll help you move it forward",
  disabled = false,
  loading = false,
  loadingLabel = "Running…",
  accentColor = "#7c3aed",
}: PromptCardProps) {
  const canSubmit = value.trim() && !disabled && !loading;

  const cardStyle: React.CSSProperties = {
    borderRadius: 16,
    border: "1px solid #d0d0e0",
    background: "rgba(255,255,255,0.92)",
    backdropFilter: "blur(12px)",
    WebkitBackdropFilter: "blur(12px)",
    overflow: "hidden",
    boxShadow: "0 2px 12px rgba(0,0,0,0.07)",
  };

  const textareaStyle: React.CSSProperties = {
    width: "100%",
    padding: "16px 16px 10px",
    border: "none",
    resize: "none",
    background: "transparent",
    color: "#0f0f0f",
    fontFamily: "'Poppins', 'Inter', sans-serif",
    fontSize: 13,
    lineHeight: 1.6,
    outline: "none",
    minHeight: 58,
    display: "block",
    boxSizing: "border-box",
  };

  const rowStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "8px 12px",
    borderTop: "1px solid rgba(208,208,224,0.5)",
  };

  const iconBtnStyle: React.CSSProperties = {
    width: 32, height: 32, borderRadius: "50%", border: "1px solid #d0d0e0",
    background: "transparent", display: "flex", alignItems: "center", justifyContent: "center",
    cursor: "pointer", flexShrink: 0,
  };

  const sendBtnStyle: React.CSSProperties = {
    width: 32, height: 32, borderRadius: "50%", border: "none",
    background: canSubmit
      ? `linear-gradient(135deg, ${accentColor}, #6366f1)`
      : "rgba(155,93,229,0.25)",
    display: "flex", alignItems: "center", justifyContent: "center",
    cursor: canSubmit ? "pointer" : "default", flexShrink: 0,
    transition: "all 0.15s ease",
  };

  return (
    <div style={cardStyle}>
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && canSubmit) onSubmit?.(); }}
        disabled={disabled || loading}
        placeholder={loading ? "" : placeholder}
        style={{
          ...textareaStyle,
          color: value ? "#0f0f0f" : undefined,
        }}
      />
      {loading && loadingLabel && (
        <div style={{ padding: "0 16px 8px", fontSize: 12, color: "#8c8ca1", fontFamily: "'Poppins','Inter',sans-serif" }}>
          {loadingLabel}
        </div>
      )}
      <div style={rowStyle}>
        {/* Left */}
        <button style={iconBtnStyle} type="button">
          <span style={{ fontSize: 16, color: "#8c8ca1", lineHeight: 1 }}>+</span>
        </button>
        {/* Right */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button style={iconBtnStyle} type="button">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke="#8c8ca1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8"/>
            </svg>
          </button>
          <button style={sendBtnStyle} type="button" onClick={() => canSubmit && onSubmit?.()}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
