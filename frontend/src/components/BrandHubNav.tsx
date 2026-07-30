export type BrandHubSection =
  | "overview"
  | "logos"
  | "fonts"
  | "brand-assets"
  | "brand-voice"
  | "visual-identity"
  | "products"
  | "competitors"
  | "personas"
  | "messaging"
  | "legal"
  | "campaign-history"
  | "market-research"
  | "documents";

const BRANDS = [
  { id: "Rnorr",       label: "Rnorr",             emoji: "🎯" },
  { id: "Sunglow",     label: "Sunglow",            emoji: "✨" },
  { id: "Boozt",       label: "Boozt",              emoji: "👗" },
  { id: "Glenfiddich", label: "Glenfiddich × AMF1", emoji: "🥃" },
  { id: "UBS Bank",    label: "UBS Bank",           emoji: "🏦" },
  { id: "sunrise",     label: "Sunrise",            emoji: "🌅" },
  { id: "Haleon",      label: "Haleon",             emoji: "💊" },
];

type NavItem =
  | { type: "item"; id: BrandHubSection; label: string; inGroup?: boolean }
  | { type: "group-header"; label: string };

const BRAND_SECTIONS: NavItem[] = [
  { type: "item",         id: "overview",          label: "Overview" },
  { type: "group-header", label: "Brand Guidelines" },
  { type: "item",         id: "logos",             label: "Logos",            inGroup: true },
  { type: "item",         id: "fonts",             label: "Fonts",            inGroup: true },
  { type: "item",         id: "brand-assets",      label: "Brand Assets",     inGroup: true },
  { type: "item",         id: "brand-voice",       label: "Brand Voice",      inGroup: true },
  { type: "item",         id: "visual-identity",   label: "Visual Identity",  inGroup: true },
  { type: "item",         id: "products",          label: "Products & Services" },
  { type: "item",         id: "competitors",       label: "Competitors" },
  { type: "item",         id: "personas",          label: "Customer Personas" },
  { type: "item",         id: "messaging",         label: "Messaging" },
  { type: "item",         id: "legal",             label: "Legal & Compliance" },
  { type: "item",         id: "campaign-history",  label: "Campaign History" },
  { type: "item",         id: "market-research",   label: "Market Research" },
  { type: "item",         id: "documents",         label: "Documents" },
];

interface BrandHubNavProps {
  active: BrandHubSection;
  onChange: (s: BrandHubSection) => void;
  activeBrand: string;
  onBrandChange: (brand: string) => void;
}

export default function BrandHubNav({ active, onChange, activeBrand, onBrandChange }: BrandHubNavProps) {
  return (
    <div style={{ padding: "0 8px" }}>
      <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: "0.12em",
        textTransform: "uppercase" as const, color: "var(--text-secondary)",
        padding: "10px 10px 6px", opacity: 0.6 }}>
        Brand Hub
      </div>

      {BRANDS.map(brand => {
        const isBrandActive = activeBrand === brand.id;

        return (
          <div key={brand.id}>
            {/* Brand row */}
            <button
              onClick={() => {
                onBrandChange(brand.id);
                onChange("overview");
                localStorage.setItem("brandHub_activeBrand", brand.id);
              }}
              style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                gap: 8, padding: "7px 10px", borderRadius: 8, border: "none",
                cursor: "pointer", fontFamily: "inherit",
                fontSize: 13, fontWeight: isBrandActive ? 700 : 500,
                textAlign: "left" as const, width: "100%",
                transition: "all 0.15s",
                background: isBrandActive ? "rgba(124,58,237,0.10)" : "transparent",
                color: isBrandActive ? "#7c3aed" : "var(--text-secondary)",
              }}
              onMouseEnter={e => {
                if (!isBrandActive) e.currentTarget.style.background = "var(--card-hover-bg)";
              }}
              onMouseLeave={e => {
                if (!isBrandActive) e.currentTarget.style.background = "transparent";
              }}
            >
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 14 }}>{brand.emoji}</span>
                <span>{brand.label}</span>
              </span>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
                style={{ transform: isBrandActive ? "rotate(180deg)" : "none",
                  transition: "transform 0.2s", flexShrink: 0, opacity: 0.45 }}>
                <path d="M6 9l6 6 6-6"/>
              </svg>
            </button>

            {/* Section list — visible only for the active brand */}
            {isBrandActive && (
              <div style={{ marginBottom: 6 }}>
                {BRAND_SECTIONS.map((item, idx) => {
                  if (item.type === "group-header") {
                    return (
                      <div key={`gh-${idx}`} style={{
                        fontSize: 9, fontWeight: 700, letterSpacing: "0.10em",
                        textTransform: "uppercase" as const,
                        color: "var(--text-secondary)", opacity: 0.45,
                        padding: "8px 10px 2px 24px",
                      }}>
                        {item.label}
                      </div>
                    );
                  }

                  const isActive = active === item.id;
                  const indent = item.inGroup ? 36 : 24;

                  return (
                    <button
                      key={`${brand.id}-${item.id}-${idx}`}
                      onClick={() => onChange(item.id)}
                      style={{
                        display: "flex", alignItems: "center",
                        padding: `5px 10px 5px ${indent}px`,
                        borderRadius: 6, border: "none",
                        cursor: "pointer", fontFamily: "inherit",
                        fontSize: 12, fontWeight: isActive ? 600 : 400,
                        textAlign: "left" as const, width: "100%",
                        transition: "all 0.12s",
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
                      {item.label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
