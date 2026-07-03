export type BrandHubSection =
  | "guidelines"
  | "voice"
  | "visual-identity"
  | "products"
  | "competitors"
  | "personas";

interface NavItem {
  id: BrandHubSection;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: "guidelines",
    label: "Brand Guidelines",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
    ),
  },
  {
    id: "voice",
    label: "Brand Voice",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
        <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
      </svg>
    ),
  },
  {
    id: "visual-identity",
    label: "Visual Identity",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <circle cx="12" cy="12" r="4"/>
        <line x1="21.17" y1="8" x2="12" y2="8"/>
        <line x1="3.95" y1="6.06" x2="8.54" y2="14"/>
        <line x1="10.88" y1="21.94" x2="15.46" y2="14"/>
      </svg>
    ),
  },
  {
    id: "products",
    label: "Products & Services",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
        <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
        <line x1="12" y1="22.08" x2="12" y2="12"/>
      </svg>
    ),
  },
  {
    id: "competitors",
    label: "Competitors",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </svg>
    ),
  },
  {
    id: "personas",
    label: "Customer Personas",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>
    ),
  },
];

interface BrandHubNavProps {
  active: BrandHubSection;
  onChange: (s: BrandHubSection) => void;
}

export default function BrandHubNav({ active, onChange }: BrandHubNavProps) {
  return (
    <div style={{ padding: "0 8px" }}>
      {/* Section label */}
      <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: "0.12em",
        textTransform: "uppercase" as const, color: "var(--text-secondary)",
        padding: "10px 10px 6px", opacity: 0.6 }}>
        Brand Knowledge
      </div>

      {NAV_ITEMS.map(item => {
        const isActive = item.id === active;
        return (
          <button
            key={item.id}
            onClick={() => onChange(item.id)}
            style={{
              display: "flex", alignItems: "center", gap: 10,
              padding: "8px 10px", borderRadius: 8, border: "none",
              cursor: "pointer", fontFamily: "inherit",
              fontSize: 13, fontWeight: isActive ? 600 : 500,
              textAlign: "left" as const, width: "100%",
              transition: "all 0.15s",
              background: isActive ? "rgba(124,58,237,0.10)" : "transparent",
              color: isActive ? "#7c3aed" : "var(--text-secondary)",
            }}
            onMouseEnter={e => {
              if (!isActive) e.currentTarget.style.background = "var(--card-hover-bg)";
            }}
            onMouseLeave={e => {
              if (!isActive) e.currentTarget.style.background = "transparent";
            }}
          >
            <span style={{ flexShrink: 0, opacity: isActive ? 1 : 0.65 }}>
              {item.icon}
            </span>
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
