import { useState } from "react";
import { API_BASE_PUB } from "../services/briefingApi";

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
  { id: "Rnorr",       label: "Rnorr",             emoji: "🎯", industry: "Food & Beverage"    },
  { id: "Sunglow",     label: "Sunglow",            emoji: "✨", industry: "Beauty & Lifestyle" },
  { id: "Boozt",       label: "Boozt",              emoji: "👗", industry: "Fashion & Retail"   },
  { id: "Glenfiddich", label: "Glenfiddich × AMF1", emoji: "🥃", industry: "Spirits & Luxury"  },
  { id: "UBS Bank",    label: "UBS Bank",           emoji: "🏦", industry: "Financial Services" },
  { id: "sunrise",     label: "Sunrise",            emoji: "🌅", industry: "Telecommunications" },
  { id: "Haleon",      label: "Haleon",             emoji: "💊", industry: "Consumer Health"    },
].map(b => ({ ...b, logo: `${API_BASE_PUB}/brand-logo/${encodeURIComponent(b.id)}` }));

// ── Inline Feather-style icons ───────────────────────────────────────────────

const ICON_PATHS: Record<string, string> = {
  grid:         "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  image:        "M21 19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z M8.5 10a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z M21 15l-5-5L5 21",
  type:         "M4 7V4h16v3M9 20h6M12 4v16",
  folder:       "M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z",
  eye:          "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  mic:          "M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z M19 10v2a7 7 0 0 1-14 0v-2 M12 19v4 M8 23h8",
  package:      "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z M3.27 6.96L12 12.01l8.73-5.05 M12 22.08V12",
  users:        "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M23 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75",
  user:         "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  message:      "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  search:       "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z M21 21l-4.35-4.35",
  barChart:     "M18 20V10 M12 20V4 M6 20v-6",
  file:         "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8",
  shield:       "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  chevronDown:  "M6 9l6 6 6-6",
  chevronRight: "M9 18l6-6-6-6",
  check:        "M20 6L9 17l-5-5",
};

function Icon({ name, size = 13, color }: { name: string; size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke={color ?? "currentColor"} strokeWidth="1.75"
      strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      {ICON_PATHS[name]?.split(" M ").map((seg, i) => (
        <path key={i} d={i === 0 ? seg : `M ${seg}`} />
      ))}
    </svg>
  );
}

// ── Nav data structure ───────────────────────────────────────────────────────

interface NavLeaf { id: BrandHubSection; label: string; icon: string; }

interface NavGroup {
  key: string;
  label: string;
  icon: string;
  defaultOpen?: boolean;
  items: NavLeaf[];
}

interface NavSection {
  sectionLabel: string | null;
  groups: NavGroup[];
}

const OVERVIEW_ITEM: NavLeaf = { id: "overview", label: "Overview", icon: "grid" };

const NAV_SECTIONS: NavSection[] = [
  {
    sectionLabel: "BRAND",
    groups: [
      {
        key: "identity", label: "Identity", icon: "image", defaultOpen: true,
        items: [
          { id: "logos",           label: "Logos",          icon: "image"  },
          { id: "fonts",           label: "Fonts",          icon: "type"   },
          { id: "brand-assets",    label: "Brand Assets",   icon: "folder" },
          { id: "visual-identity", label: "Visual Identity",icon: "eye"    },
        ],
      },
      {
        key: "strategy", label: "Strategy", icon: "mic", defaultOpen: false,
        items: [
          { id: "brand-voice",  label: "Brand Voice",         icon: "mic"     },
          { id: "products",     label: "Products & Services", icon: "package" },
          { id: "competitors",  label: "Competitors",         icon: "users"   },
          { id: "personas",     label: "Customer Personas",   icon: "user"    },
          { id: "messaging",    label: "Messaging",           icon: "message" },
        ],
      },
    ],
  },
  {
    sectionLabel: "KNOWLEDGE",
    groups: [
      {
        key: "knowledge", label: "Knowledge", icon: "search", defaultOpen: false,
        items: [
          { id: "market-research",  label: "Market Research",  icon: "search"   },
          { id: "campaign-history", label: "Campaign History", icon: "barChart" },
          { id: "documents",        label: "Documents",        icon: "file"     },
        ],
      },
    ],
  },
  {
    sectionLabel: "GOVERNANCE",
    groups: [
      {
        key: "governance", label: "Governance", icon: "shield", defaultOpen: false,
        items: [
          { id: "legal", label: "Legal & Compliance", icon: "shield" },
        ],
      },
    ],
  },
];

// ── Brand logo with img → emoji fallback ─────────────────────────────────────

function BrandLogo({ src, emoji, size = 22 }: { src: string; emoji: string; size?: number }) {
  const [failed, setFailed] = useState(false);
  if (failed) return <span style={{ fontSize: size * 0.7, lineHeight: 1 }}>{emoji}</span>;
  return (
    <img src={src} alt="" onError={() => setFailed(true)}
      style={{ width: size, height: size, objectFit: "contain", display: "block" }} />
  );
}

// ── Main nav ─────────────────────────────────────────────────────────────────

interface BrandHubNavProps {
  active: BrandHubSection;
  onChange: (s: BrandHubSection) => void;
  activeBrand: string;
  onBrandChange: (brand: string) => void;
}

export default function BrandHubNav({ active, onChange, activeBrand, onBrandChange }: BrandHubNavProps) {
  const [brandDropdownOpen, setBrandDropdownOpen] = useState(false);
  const [openGroups, setOpenGroups] = useState<Set<string>>(() =>
    new Set(NAV_SECTIONS.flatMap(s => s.groups.filter(g => g.defaultOpen).map(g => g.key)))
  );

  const toggleGroup = (key: string) => setOpenGroups(prev => {
    const next = new Set(prev);
    next.has(key) ? next.delete(key) : next.add(key);
    return next;
  });

  const activeBrandData = BRANDS.find(b => b.id === activeBrand) ?? BRANDS[0];

  // NavLeaf item
  const NavItem = ({ item, indent = 14 }: { item: NavLeaf; indent?: number }) => {
    const isActive = active === item.id;
    return (
      <button
        onClick={() => onChange(item.id)}
        style={{
          display: "flex", alignItems: "center", gap: 8,
          width: "100%", border: "none", cursor: "pointer",
          fontFamily: "inherit", textAlign: "left" as const,
          padding: `5px 12px 5px ${indent}px`,
          fontSize: 12, fontWeight: isActive ? 600 : 400,
          color: isActive ? "#7c3aed" : "var(--text-secondary)",
          background: isActive ? "rgba(124,58,237,0.07)" : "transparent",
          borderLeft: isActive ? "2px solid #7c3aed" : "2px solid transparent",
          borderRadius: "0 6px 6px 0",
          transition: "all 0.12s",
        }}
        onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = "rgba(124,58,237,0.04)"; }}
        onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = "transparent"; }}
      >
        <span style={{ opacity: isActive ? 1 : 0.55 }}>
          <Icon name={item.icon} size={12} />
        </span>
        {item.label}
      </button>
    );
  };

  return (
    <div style={{ padding: "0 0 16px" }}>

      {/* ── Brand selector ── */}
      <div style={{ position: "relative" as const }}>
        <button
          onClick={() => setBrandDropdownOpen(v => !v)}
          style={{
            display: "flex", alignItems: "center", gap: 10,
            width: "100%", border: "none", cursor: "pointer",
            fontFamily: "inherit", textAlign: "left" as const,
            padding: "10px 14px 10px 12px",
            background: "transparent",
            borderBottom: brandDropdownOpen ? "1px solid rgba(124,58,237,0.15)" : "1px solid transparent",
            transition: "border-color 0.15s",
          }}
        >
          <div style={{
            width: 32, height: 32, borderRadius: 8, flexShrink: 0,
            background: "var(--card-bg)", border: "1px solid var(--border-color)",
            display: "flex", alignItems: "center", justifyContent: "center",
            overflow: "hidden", padding: 4,
          }}>
            <BrandLogo src={activeBrandData.logo} emoji={activeBrandData.emoji} size={22} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)",
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const }}>
              {activeBrandData.label}
            </div>
            <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginTop: 1 }}>
              Brand workspace
            </div>
          </div>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
            stroke="var(--text-tertiary)" strokeWidth="2.5" strokeLinecap="round">
            <path d={brandDropdownOpen ? "M18 15l-6-6-6 6" : "M6 9l6 6 6-6"} />
          </svg>
        </button>

        {/* Brand dropdown */}
        {brandDropdownOpen && (
          <div style={{
            position: "absolute" as const, top: "100%", left: 8, right: 8, zIndex: 50,
            background: "var(--card-bg)", border: "1px solid var(--border-color)",
            borderRadius: 10, boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
            padding: "6px 0", marginTop: 4,
          }}>
            {BRANDS.map(brand => {
              const isSelected = brand.id === activeBrand;
              return (
                <button
                  key={brand.id}
                  onClick={() => {
                    onBrandChange(brand.id);
                    onChange("overview");
                    localStorage.setItem("brandHub_activeBrand", brand.id);
                    setBrandDropdownOpen(false);
                  }}
                  style={{
                    display: "flex", alignItems: "center", gap: 9,
                    width: "100%", border: "none", cursor: "pointer",
                    fontFamily: "inherit", textAlign: "left" as const,
                    padding: "7px 12px",
                    background: isSelected ? "rgba(124,58,237,0.07)" : "transparent",
                    transition: "background 0.1s",
                  }}
                  onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = "rgba(124,58,237,0.04)"; }}
                  onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}
                >
                  <div style={{
                    width: 24, height: 24, borderRadius: 6, flexShrink: 0,
                    background: "var(--page-bg)", border: "1px solid var(--border-color)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    overflow: "hidden", padding: 3,
                  }}>
                    <BrandLogo src={brand.logo} emoji={brand.emoji} size={16} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: isSelected ? 600 : 400,
                      color: isSelected ? "#7c3aed" : "var(--text-primary)",
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const }}>
                      {brand.label}
                    </div>
                    <div style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{brand.industry}</div>
                  </div>
                  {isSelected && <Icon name="check" size={12} color="#7c3aed" />}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Overview ── */}
      <div style={{ padding: "8px 0 4px" }}>
        <NavItem item={OVERVIEW_ITEM} indent={14} />
      </div>

      {/* ── Sections ── */}
      {NAV_SECTIONS.map(section => {
        const isSingleGroup = section.groups.length === 1;
        return (
        <div key={section.sectionLabel} style={{ marginTop: 8 }}>

          {section.groups.map(group => {
            const isOpen = openGroups.has(group.key);
            const groupHasActive = group.items.some(i => i.id === active);

            return (
              <div key={group.key}>
                {isSingleGroup ? (
                  /* Single-group section: section label IS the toggle row */
                  <button
                    onClick={() => toggleGroup(group.key)}
                    style={{
                      display: "flex", alignItems: "center", gap: 7,
                      width: "100%", border: "none", cursor: "pointer",
                      fontFamily: "inherit", textAlign: "left" as const,
                      padding: "5px 12px 5px 14px",
                      background: "transparent",
                      borderLeft: "2px solid transparent",
                      borderRadius: "0 6px 6px 0",
                      transition: "all 0.12s",
                    }}
                    onMouseEnter={e => { e.currentTarget.style.background = "rgba(124,58,237,0.04)"; }}
                    onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
                  >
                    <span style={{ color: "var(--text-tertiary)", display: "inline-flex",
                      transform: isOpen ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 0.2s" }}>
                      <Icon name="chevronDown" size={11} />
                    </span>
                    <span style={{
                      fontSize: 9, fontWeight: 800, letterSpacing: "0.13em",
                      textTransform: "uppercase" as const,
                      color: groupHasActive && !isOpen ? "#7c3aed" : "var(--text-tertiary)",
                    }}>
                      {section.sectionLabel}
                    </span>
                  </button>
                ) : (
                  /* Multi-group section: section label is a static header, each group has its own toggle */
                  <>
                    {group === section.groups[0] && section.sectionLabel && (
                      <div style={{
                        fontSize: 9, fontWeight: 800, letterSpacing: "0.13em",
                        textTransform: "uppercase" as const,
                        color: "var(--text-tertiary)",
                        padding: "6px 14px 4px",
                      }}>
                        {section.sectionLabel}
                      </div>
                    )}
                    <button
                      onClick={() => toggleGroup(group.key)}
                      style={{
                        display: "flex", alignItems: "center", gap: 7,
                        width: "100%", border: "none", cursor: "pointer",
                        fontFamily: "inherit", textAlign: "left" as const,
                        padding: "5px 12px 5px 14px",
                        fontSize: 12, fontWeight: (groupHasActive && !isOpen) ? 600 : 500,
                        color: (groupHasActive && !isOpen) ? "#7c3aed" : "var(--text-primary)",
                        background: "transparent",
                        borderLeft: (groupHasActive && !isOpen) ? "2px solid #7c3aed" : "2px solid transparent",
                        borderRadius: "0 6px 6px 0",
                        transition: "all 0.12s",
                      }}
                      onMouseEnter={e => { e.currentTarget.style.background = "rgba(124,58,237,0.04)"; }}
                      onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
                    >
                      <span style={{ color: "var(--text-tertiary)", display: "inline-flex",
                        transform: isOpen ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 0.2s" }}>
                        <Icon name="chevronDown" size={11} />
                      </span>
                      {group.label}
                    </button>
                  </>
                )}

                {/* Expanded items */}
                {isOpen && (
                  <div style={{ paddingBottom: 2 }}>
                    {group.items.map(item => (
                      <NavItem key={item.id} item={item} indent={isSingleGroup ? 22 : 30} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        );
      })}
    </div>
  );
}
