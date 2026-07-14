import { useState, useMemo } from "react";
import { contentHubAssetUrl, useContentHub, type ContentHubItem } from "./hooks/useContentHub";

// ── Helpers ────────────────────────────────────────────────────
function timeAgo(ts: number): string {
  const s = Math.floor(Date.now() / 1000 - ts);
  if (s < 60)    return `${s}s ago`;
  if (s < 3600)  return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function fmtLabel(item: ContentHubItem) {
  return item.kind === "reel" ? "Reel" : "Image";
}

function fileExt(item: ContentHubItem) {
  return item.kind === "reel" ? "mp4" : item.content_type.includes("png") ? "png" : "jpg";
}

// ── Asset Card ─────────────────────────────────────────────────
function AssetCard({ item, selected, onClick }: {
  item: ContentHubItem; selected: boolean; onClick: () => void;
}) {
  const [hover, setHover] = useState(false);
  const url   = contentHubAssetUrl(item.id);
  const isReel = item.kind === "reel";
  const accent = isReel ? "#ec4899" : "#7c3aed";

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        borderRadius: 12, overflow: "hidden", cursor: "pointer",
        border: `1.5px solid ${selected ? accent : hover ? `${accent}55` : "var(--card-border)"}`,
        background: "var(--card-bg)",
        boxShadow: selected ? `0 0 0 3px ${accent}22` : hover ? "0 4px 20px rgba(0,0,0,0.12)" : "none",
        transition: "border-color 0.15s, box-shadow 0.15s",
        position: "relative" as const,
      }}>

      {/* Thumbnail */}
      <div style={{ aspectRatio: "16/9", position: "relative" as const, overflow: "hidden", background: "#0a0a12" }}>
        {isReel
          ? <video src={url} muted loop playsInline
              style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
          : <img src={url} alt={item.headline || item.brand} loading="lazy"
              style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
        }

        {/* Gradient */}
        <div style={{ position: "absolute" as const, inset: 0,
          background: "linear-gradient(to top, rgba(0,0,0,0.65) 0%, transparent 55%)",
          pointerEvents: "none" as const }} />

        {/* Play overlay for reels */}
        {isReel && (
          <div style={{ position: "absolute" as const, top: "50%", left: "50%",
            transform: "translate(-50%,-50%)", width: 34, height: 34, borderRadius: "50%",
            background: "rgba(255,255,255,0.18)", backdropFilter: "blur(8px)",
            display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg width="10" height="12" viewBox="0 0 10 12" fill="white"><path d="M0 0l10 6-10 6z"/></svg>
          </div>
        )}

        {/* Format badge */}
        <div style={{ position: "absolute" as const, bottom: 8, left: 8,
          padding: "2px 8px", borderRadius: 6,
          background: `${accent}cc`, backdropFilter: "blur(4px)",
          fontSize: 10, fontWeight: 700, color: "white",
          letterSpacing: ".04em", textTransform: "uppercase" as const }}>
          {fmtLabel(item)}
        </div>

        {/* Time */}
        <div style={{ position: "absolute" as const, bottom: 8, right: 8,
          fontSize: 10, color: "rgba(255,255,255,0.65)", fontWeight: 600 }}>
          {timeAgo(item.created_at)}
        </div>

        {/* Hover: download button */}
        {hover && (
          <div style={{ position: "absolute" as const, top: 8, right: 8 }}
            onClick={e => e.stopPropagation()}>
            <a href={url} download={`${item.brand}-${item.kind}.${fileExt(item)}`}
              title="Download"
              style={{ width: 28, height: 28, borderRadius: 8, display: "flex",
                alignItems: "center", justifyContent: "center",
                background: "rgba(255,255,255,0.15)", backdropFilter: "blur(8px)",
                border: "1px solid rgba(255,255,255,0.2)", color: "white",
                textDecoration: "none", fontSize: 12 }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                strokeWidth="2.5" strokeLinecap="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </a>
          </div>
        )}
      </div>

      {/* Card footer */}
      <div style={{ padding: "10px 12px 12px" }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)",
          textTransform: "uppercase" as const, letterSpacing: ".06em", marginBottom: 3 }}>
          {item.brand}
        </div>
        {item.headline && (
          <div style={{ fontSize: 12, color: "var(--text-primary)", fontWeight: 600,
            lineHeight: 1.45, overflow: "hidden", display: "-webkit-box",
            WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any }}>
            {item.headline}
          </div>
        )}
        {item.campaign_name && (
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4,
            overflow: "hidden", whiteSpace: "nowrap" as const, textOverflow: "ellipsis" }}>
            {item.campaign_name}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Detail Modal ───────────────────────────────────────────────
function DetailModal({ item, onDelete, onClose }: {
  item: ContentHubItem; onDelete: (id: string) => void; onClose: () => void;
}) {
  const url    = contentHubAssetUrl(item.id);
  const isReel = item.kind === "reel";
  const accent = isReel ? "#ec4899" : "#7c3aed";

  const meta = [
    { label: "Brand",    value: item.brand },
    { label: "Campaign", value: item.campaign_name || "—" },
    { label: "Format",   value: fmtLabel(item) },
    { label: "Created",  value: new Date(item.created_at * 1000).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) },
  ];

  return (
    /* Backdrop */
    <div
      onClick={onClose}
      style={{ position: "fixed" as const, inset: 0, zIndex: 300,
        background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "24px" }}>

      {/* Card */}
      <div
        onClick={e => e.stopPropagation()}
        style={{ width: "100%", maxWidth: 780, borderRadius: 20,
          background: "var(--card-bg)", border: "1.5px solid var(--card-border)",
          boxShadow: "0 32px 80px rgba(0,0,0,0.4)",
          overflow: "hidden", display: "flex", flexDirection: "column" as const }}>

        {/* Large image */}
        <div style={{ position: "relative" as const, background: "#0a0a12" }}>
          {isReel
            ? <video src={url} controls autoPlay muted loop playsInline
                style={{ width: "100%", maxHeight: 440, objectFit: "contain", display: "block" }} />
            : <img src={url} alt={item.headline || item.brand}
                style={{ width: "100%", maxHeight: 440, objectFit: "contain", display: "block" }} />
          }
          {/* Close button */}
          <button onClick={onClose}
            style={{ position: "absolute" as const, top: 14, right: 14,
              width: 32, height: 32, borderRadius: "50%", border: "none",
              background: "rgba(0,0,0,0.5)", backdropFilter: "blur(8px)",
              color: "white", fontSize: 18, cursor: "pointer", lineHeight: 1,
              display: "flex", alignItems: "center", justifyContent: "center" }}>×</button>
        </div>

        {/* Info row */}
        <div style={{ padding: "20px 24px 24px", display: "flex",
          gap: 24, alignItems: "flex-start" }}>

          {/* Left: headline + meta */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              {item.headline && (
                <div style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)",
                  lineHeight: 1.3 }}>
                  {item.headline}
                </div>
              )}
              <span style={{ flexShrink: 0, padding: "3px 10px", borderRadius: 8,
                background: `${accent}18`, color: accent,
                fontSize: 10, fontWeight: 700, letterSpacing: ".05em",
                textTransform: "uppercase" as const }}>
                {fmtLabel(item)}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 24px" }}>
              {meta.map(({ label, value }) => (
                <div key={label}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-tertiary)",
                    textTransform: "uppercase" as const, letterSpacing: ".06em", marginBottom: 2 }}>
                    {label}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.4 }}>
                    {value}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: actions */}
          <div style={{ display: "flex", flexDirection: "column" as const, gap: 8, flexShrink: 0 }}>
            <a href={url} download={`${item.brand}-${item.kind}.${fileExt(item)}`}
              style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 18px",
                borderRadius: 10, border: "1.5px solid var(--card-border)", background: "transparent",
                color: "var(--text-primary)", fontSize: 13, fontWeight: 600,
                textDecoration: "none", whiteSpace: "nowrap" as const }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                strokeWidth="2" strokeLinecap="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              Download
            </a>
            <button onClick={() => { onDelete(item.id); onClose(); }}
              style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 18px",
                borderRadius: 10, border: "1.5px solid rgba(239,68,68,0.3)", background: "transparent",
                color: "#ef4444", fontSize: 13, fontWeight: 600, cursor: "pointer",
                fontFamily: "inherit", whiteSpace: "nowrap" as const }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                strokeWidth="2" strokeLinecap="round">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                <path d="M10 11v6M14 11v6M9 6V4h6v2"/>
              </svg>
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Empty State ────────────────────────────────────────────────
function EmptyState({ onStartCampaign }: { onStartCampaign?: () => void }) {
  return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
      padding: "60px 32px" }}>
      <div style={{ textAlign: "center" as const, maxWidth: 420 }}>
        <div style={{ width: 80, height: 80, margin: "0 auto 20px", borderRadius: "50%",
          background: "radial-gradient(circle at 32% 28%, #f9a8ff 0%, #c084fc 28%, #7c3aed 62%, #4f46e5 100%)",
          boxShadow: "0 0 0 10px rgba(124,58,237,0.08), 0 10px 40px rgba(124,58,237,0.3)",
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 34 }}>📚</div>
        <h3 style={{ fontSize: 20, fontWeight: 900, color: "var(--text-primary)", margin: "0 0 8px" }}>
          Your library is empty
        </h3>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.65, margin: "0 0 24px" }}>
          Save generated assets using <strong style={{ color: "var(--text-primary)" }}>💾 Save to Content Hub</strong> on any campaign image or reel.
        </p>
        {onStartCampaign && (
          <button onClick={onStartCampaign} style={{ padding: "11px 28px", borderRadius: 12,
            border: "none", cursor: "pointer", fontFamily: "inherit", fontSize: 14,
            fontWeight: 700, color: "white",
            background: "linear-gradient(135deg, #7c3aed 0%, #a855f7 55%, #6366f1 100%)",
            boxShadow: "0 6px 24px rgba(124,58,237,0.38)" }}>
            ✨ Start a Campaign
          </button>
        )}
      </div>
    </div>
  );
}

// ── Main ───────────────────────────────────────────────────────
type Tab = "all" | "image" | "reel";

export default function ContentHub({ onStartCampaign }: { onStartCampaign?: () => void }) {
  const { items, loading, error, remove } = useContentHub();
  const [tab, setTab]         = useState<Tab>("all");
  const [search, setSearch]   = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const kvCount   = items.filter(i => i.kind === "kv").length;
  const reelCount = items.filter(i => i.kind === "reel").length;

  const filtered = useMemo(() => items.filter(item => {
    if (tab === "image" && item.kind !== "kv")   return false;
    if (tab === "reel"  && item.kind !== "reel") return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        item.brand.toLowerCase().includes(q) ||
        (item.headline ?? "").toLowerCase().includes(q) ||
        (item.campaign_name ?? "").toLowerCase().includes(q)
      );
    }
    return true;
  }), [items, tab, search]);

  const selected = selectedId ? (items.find(i => i.id === selectedId) ?? null) : null;

  const TABS: { key: Tab; label: string; count: number }[] = [
    { key: "all",   label: "All Assets", count: items.length },
    { key: "image", label: "Images",     count: kvCount },
    { key: "reel",  label: "Reels",      count: reelCount },
  ];

  const isEmpty = !loading && items.length === 0 && !error;

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" as const,
      overflow: "hidden", background: "var(--page-bg)" }}>

      {/* ── Header ── */}
      <div style={{ padding: "28px 32px 0", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "flex-start",
          justifyContent: "space-between", marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 900, color: "var(--text-primary)", margin: "0 0 4px" }}>
              Content{" "}
              <span style={{ background: "linear-gradient(135deg,#7c3aed,#a78bfa)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                backgroundClip: "text" }}>Hub</span>
            </h2>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
              All your campaign assets in one gallery.
            </p>
          </div>

          {/* Search */}
          <div style={{ position: "relative" as const }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke="var(--text-tertiary)" strokeWidth="2" strokeLinecap="round"
              style={{ position: "absolute" as const, left: 12, top: "50%",
                transform: "translateY(-50%)", pointerEvents: "none" as const }}>
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search assets…"
              style={{ padding: "9px 14px 9px 36px", borderRadius: 10, width: 220,
                border: "1.5px solid var(--card-border)", background: "var(--card-bg)",
                color: "var(--text-primary)", fontFamily: "inherit", fontSize: 13,
                outline: "none", boxSizing: "border-box" as const }} />
          </div>
        </div>

        {/* ── Tabs ── */}
        <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--card-border)" }}>
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              style={{ padding: "9px 16px", border: "none", background: "transparent",
                cursor: "pointer", fontFamily: "inherit", fontSize: 13, fontWeight: 600,
                color: tab === t.key ? "#7c3aed" : "var(--text-secondary)",
                borderBottom: tab === t.key ? "2px solid #7c3aed" : "2px solid transparent",
                marginBottom: -1, display: "flex", alignItems: "center", gap: 7,
                transition: "color 0.15s" }}>
              {t.label}
              {t.count > 0 && (
                <span style={{ padding: "1px 7px", borderRadius: 99, fontSize: 10, fontWeight: 700,
                  background: tab === t.key ? "rgba(124,58,237,0.12)" : "var(--card-border)",
                  color: tab === t.key ? "#7c3aed" : "var(--text-secondary)" }}>
                  {t.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* ── Body ── */}
      {error && (
        <div style={{ padding: "16px 32px", fontSize: 13, color: "#ef4444" }}>
          Couldn't load Content Hub: {error}
        </div>
      )}

      {isEmpty ? (
        <EmptyState onStartCampaign={onStartCampaign} />
      ) : (
        <div style={{ flex: 1, overflowY: "auto" as const, padding: "20px 24px 32px" }}>
          {loading && (
            <div style={{ color: "var(--text-secondary)", fontSize: 13, padding: "40px 0",
              textAlign: "center" as const }}>Loading…</div>
          )}
          {!loading && filtered.length === 0 && (
            <div style={{ color: "var(--text-secondary)", fontSize: 13, padding: "40px 0",
              textAlign: "center" as const }}>No assets match your search.</div>
          )}
          <div style={{ display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: 16, alignContent: "start" }}>
            {filtered.map(item => (
              <AssetCard key={item.id} item={item}
                selected={selectedId === item.id}
                onClick={() => setSelectedId(prev => prev === item.id ? null : item.id)} />
            ))}
          </div>
        </div>

        {/* Detail modal — centred overlay */}
        {selected && (
          <DetailModal item={selected} onDelete={remove}
            onClose={() => setSelectedId(null)} />
        )}
      )}
    </div>
  );
}
