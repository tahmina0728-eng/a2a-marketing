import { useState } from "react";
import { contentHubAssetUrl, useContentHub, type ContentHubItem } from "./hooks/useContentHub";

function GalleryTile({ item, onDelete }: { item: ContentHubItem; onDelete: (id: string) => void }) {
  const [hover, setHover] = useState(false);
  const assetUrl = contentHubAssetUrl(item.id);
  const ext = item.kind === "reel" ? "mp4" : item.content_type.includes("png") ? "png" : "jpg";
  const isReel = item.kind === "reel";

  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        position: "relative" as const, aspectRatio: "1 / 1", overflow: "hidden",
        background: "var(--card-bg-soft)",
      }}>
      {isReel ? (
        <video src={assetUrl} muted loop playsInline
          onMouseEnter={(e) => e.currentTarget.play().catch(() => {})}
          onMouseLeave={(e) => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }}
          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
      ) : (
        <img src={assetUrl} alt="" loading="lazy"
          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
      )}

      {/* Always-visible kind badge, top-right */}
      <div style={{
        position: "absolute" as const, top: 8, right: 8, width: 26, height: 26, borderRadius: "50%",
        background: "rgba(0,0,0,0.55)", display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 12, backdropFilter: "blur(4px)",
      }}>{isReel ? "🎬" : "🎨"}</div>

      {/* Hover scrim with metadata + actions */}
      <div style={{
        position: "absolute" as const, inset: 0,
        background: "linear-gradient(to top, rgba(0,0,0,0.80) 0%, rgba(0,0,0,0.05) 50%, transparent 70%)",
        opacity: hover ? 1 : 0, transition: "opacity 0.18s ease", pointerEvents: "none" as const,
      }} />
      <div style={{
        position: "absolute" as const, top: 8, left: 8,
        opacity: hover ? 1 : 0, transition: "opacity 0.18s ease",
      }}>
        <span style={{ fontSize: 11, fontWeight: 800, color: "white", textShadow: "0 1px 4px rgba(0,0,0,0.6)" }}>
          {item.brand}
        </span>
      </div>
      <div style={{
        position: "absolute" as const, bottom: 8, left: 8, right: 8,
        display: "flex", gap: 6, opacity: hover ? 1 : 0,
        transform: hover ? "translateY(0)" : "translateY(4px)",
        transition: "opacity 0.18s ease, transform 0.18s ease",
      }}>
        <a href={assetUrl} download={`${item.brand}-${item.kind}-${item.id}.${ext}`}
          style={{
            flex: 1, textAlign: "center" as const, fontSize: 11, fontWeight: 700,
            padding: "5px 0", borderRadius: 7, textDecoration: "none",
            background: "rgba(255,255,255,0.95)", color: "#0f172a",
            pointerEvents: hover ? "auto" as const : "none" as const,
          }}>⬇</a>
        <button onClick={() => onDelete(item.id)} style={{
          fontSize: 11, padding: "5px 9px", borderRadius: 7, border: "none",
          background: "rgba(239,68,68,0.9)", color: "white", cursor: "pointer", fontFamily: "inherit",
          pointerEvents: hover ? "auto" as const : "none" as const,
        }}>🗑</button>
      </div>
    </div>
  );
}

function GallerySection({ title, accent, items, onDelete }: {
  title: string; accent: string; items: ContentHubItem[]; onDelete: (id: string) => void;
}) {
  return (
    <div style={{ marginBottom: 32 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, padding: "0 24px" }}>
        <h3 style={{ fontSize: 15, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>{title}</h3>
        <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 10px", borderRadius: 99,
          background: `${accent}18`, color: accent }}>{items.length}</span>
      </div>
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 3,
      }}>
        {items.map((item) => (
          <GalleryTile key={item.id} item={item} onDelete={onDelete} />
        ))}
      </div>
    </div>
  );
}

function EmptyState({ onStartCampaign }: { onStartCampaign?: () => void }) {
  return (
    <div style={{
      position: "relative" as const, overflow: "hidden",
      borderRadius: 24, padding: "70px 32px", margin: "0 24px",
      textAlign: "center" as const,
      background: "var(--card-bg)", border: "1px solid var(--card-border)",
    }}>
      {/* Ambient glow blobs */}
      <div style={{ position: "absolute" as const, top: "-30%", left: "10%", width: 320, height: 320,
        borderRadius: "50%", pointerEvents: "none" as const,
        background: "radial-gradient(circle, rgba(124,58,237,0.16) 0%, transparent 70%)" }} />
      <div style={{ position: "absolute" as const, bottom: "-35%", right: "8%", width: 340, height: 340,
        borderRadius: "50%", pointerEvents: "none" as const,
        background: "radial-gradient(circle, rgba(236,72,153,0.12) 0%, transparent 70%)" }} />

      <div style={{ position: "relative" as const, zIndex: 1 }}>
        <div style={{
          width: 84, height: 84, margin: "0 auto 22px", borderRadius: "50%",
          background: "radial-gradient(circle at 32% 28%, #f9a8ff 0%, #c084fc 28%, #7c3aed 62%, #4f46e5 100%)",
          boxShadow: "0 0 0 10px rgba(124,58,237,0.08), 0 10px 40px rgba(124,58,237,0.35)",
          display: "flex", alignItems: "center", justifyContent: "center",
          animation: "icon-breathe 2.6s ease-in-out infinite",
        }}>
          <span style={{ fontSize: 36 }}>📚</span>
        </div>

        <h3 style={{ fontSize: 22, fontWeight: 900, color: "var(--text-primary)", margin: "0 0 8px" }}>
          Your library is just getting started
        </h3>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6,
          maxWidth: 420, margin: "0 auto 26px" }}>
          Every key visual and reel you save lands here — searchable, downloadable,
          and ready to reuse across campaigns. Generate a campaign, then hit
          <strong style={{ color: "var(--text-primary)" }}> "💾 Save to Content Hub"</strong> on
          any key visual or reel.
        </p>

        {onStartCampaign && (
          <button onClick={onStartCampaign} style={{
            padding: "12px 28px", borderRadius: 12, border: "none", cursor: "pointer",
            fontFamily: "inherit", fontSize: 14, fontWeight: 700, color: "white",
            background: "linear-gradient(135deg, #7c3aed 0%, #a855f7 55%, #6366f1 100%)",
            boxShadow: "0 6px 24px rgba(124,58,237,0.40)",
          }}>
            ✨ Start a Campaign
          </button>
        )}
      </div>
    </div>
  );
}

export default function ContentHub({ onStartCampaign }: { onStartCampaign?: () => void }) {
  const { items, loading, error, remove } = useContentHub();

  const isEmpty = !loading && items.length === 0 && !error;
  const kvItems   = items.filter((it) => it.kind === "kv");
  const reelItems = items.filter((it) => it.kind === "reel");
  const heroItem  = kvItems[0] ?? reelItems[0] ?? null;

  if (isEmpty) {
    return (
      <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 40px", background: "var(--page-bg)",
        display: "flex", alignItems: "center" as const, justifyContent: "center" as const }}>
        <div style={{ maxWidth: 1200, width: "100%" }}>
          <h2 style={{ fontSize: 28, fontWeight: 900, color: "var(--text-primary)", margin: "0 0 6px",
            textAlign: "center" as const }}>
            Content <span style={{ background: "linear-gradient(135deg,#7c3aed,#a78bfa)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>Hub</span>
          </h2>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 14px", textAlign: "center" as const }}>
            Every key visual and reel you've saved, in one library.
          </p>
          <EmptyState onStartCampaign={onStartCampaign} />
        </div>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, background: "var(--page-bg)" }}>
      {/* Hero banner — uses the most recently saved asset */}
      <div style={{ position: "relative" as const, height: 260, background: "#0a0a13", overflow: "hidden" }}>
        {heroItem && (heroItem.kind === "reel" ? (
          <video src={contentHubAssetUrl(heroItem.id)} muted autoPlay loop playsInline
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block", opacity: 0.85 }} />
        ) : (
          <img src={contentHubAssetUrl(heroItem.id)} alt=""
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block", opacity: 0.85 }} />
        ))}
        <div style={{ position: "absolute" as const, inset: 0,
          background: "linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.15) 55%, rgba(0,0,0,0.35) 100%)" }} />
        {onStartCampaign && (
          <button onClick={onStartCampaign} style={{
            position: "absolute" as const, top: 20, left: 24, background: "none", border: "none",
            color: "white", fontSize: 20, cursor: "pointer", opacity: 0.85,
          }}>‹</button>
        )}
        <div style={{ position: "absolute" as const, bottom: 22, left: 28 }}>
          <h2 style={{ fontSize: 32, fontWeight: 800, color: "white", margin: 0,
            textShadow: "0 2px 10px rgba(0,0,0,0.4)" }}>Content Hub</h2>
          <p style={{ fontSize: 13, color: "rgba(255,255,255,0.85)", margin: "4px 0 0" }}>
            {items.length} saved asset{items.length === 1 ? "" : "s"} — your campaign library.
          </p>
        </div>
      </div>

      {/* Slim dark toolbar */}
      <div style={{ background: "#14141f", padding: "10px 24px", display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ fontSize: 16, opacity: 0.8 }}>📤</span>
      </div>

      {error && (
        <div style={{ color: "#ef4444", fontSize: 13, padding: "16px 24px" }}>Couldn't load Content Hub: {error}</div>
      )}

      <div style={{ padding: "24px 0 32px" }}>
        {kvItems.length > 0 && (
          <GallerySection title="Image Gallery" accent="#7c3aed" items={kvItems} onDelete={remove} />
        )}
        {reelItems.length > 0 && (
          <GallerySection title="Reel Gallery" accent="#ec4899" items={reelItems} onDelete={remove} />
        )}
      </div>
    </div>
  );
}
