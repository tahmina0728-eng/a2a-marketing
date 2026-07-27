import { useState, useRef, useEffect } from "react";

interface Option { value: string; label: string; icon?: React.ReactNode; }

interface FormSelectProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  options: (string | Option)[];
}

/**
 * Reliable custom select — doesn't depend on Radix portal or
 * Tailwind v4 classes. Uses inline styles throughout so it works
 * regardless of CSS variable setup.
 */
export default function FormSelect({ value, onChange, placeholder = "Select…", options }: FormSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const opts: Option[] = options.map(o =>
    typeof o === "string" ? { value: o, label: o } : o,
  );
  const selected = opts.find(o => o.value === value);

  return (
    <div ref={ref} style={{ position: "relative", width: "100%" }}>
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen(p => !p)}
        style={{
          width: "100%", height: 44, borderRadius: 12, padding: "0 14px",
          border: open ? "1.5px solid #7c3aed" : "1px solid #d0d0e0",
          background: "rgba(255,255,255,0.92)", backdropFilter: "blur(8px)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          cursor: "pointer", fontFamily: "'Poppins','Inter',sans-serif",
          fontSize: 13, color: selected ? "#0f0f0f" : "#8c8ca1",
          boxShadow: open ? "0 0 0 3px rgba(124,58,237,0.1)" : "none",
          transition: "all 0.15s ease",
        }}>
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {selected?.icon}
          {selected ? selected.label : placeholder}
        </span>
        <svg
          width="16" height="16" viewBox="0 0 24 24" fill="none"
          stroke={open ? "#7c3aed" : "#8c8ca1"} strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.2s", flexShrink: 0 }}>
          <path d="M6 9l6 6 6-6"/>
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 6px)", left: 0, right: 0, zIndex: 9999,
          background: "white", borderRadius: 12, border: "1px solid #d0d0e0",
          boxShadow: "0 8px 24px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.06)",
          overflow: "hidden", maxHeight: 320, overflowY: "auto",
        }}>
          {opts.map(opt => (
            <button
              key={opt.value}
              type="button"
              onClick={() => { onChange(opt.value); setOpen(false); }}
              style={{
                width: "100%", padding: "10px 14px", border: "none", textAlign: "left",
                cursor: "pointer", display: "flex", alignItems: "center", gap: 8,
                fontFamily: "'Poppins','Inter',sans-serif", fontSize: 13,
                color: opt.value === value ? "#7c3aed" : "#0f0f0f",
                background: opt.value === value ? "rgba(124,58,237,0.06)" : "white",
                fontWeight: opt.value === value ? 600 : 400,
                transition: "background 0.1s",
              }}
              onMouseEnter={e => { if (opt.value !== value) e.currentTarget.style.background = "#f5f5f8"; }}
              onMouseLeave={e => { e.currentTarget.style.background = opt.value === value ? "rgba(124,58,237,0.06)" : "white"; }}>
              {opt.icon}
              {opt.label}
              {opt.value === value && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#7c3aed"
                  strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginLeft: "auto" }}>
                  <path d="M20 6L9 17l-5-5"/>
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
