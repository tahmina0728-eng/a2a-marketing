import { contentHubAssetUrl, useContentHub, type ContentHubItem } from "./hooks/useContentHub";

function formatDate(ts: number): string {
  return new Date(ts * 1000).toLocaleString(undefined, {
    month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function ContentHubCard({ item, onDelete }: { item: ContentHubItem; onDelete: (id: string) => void }) {
  const assetUrl = contentHubAssetUrl(item.id);
  const ext = item.kind === "reel" ? "mp4" : item.content_type.includes("png") ? "png" : "jpg";

  return (
    <div style={{
      background: "var(--card-bg)", border: "1px solid var(--card-border)",
      borderRadius: 14, overflow: "hidden", display: "flex", flexDirection: "column" as const,
      boxShadow: "var(--shadow-sm)",
    }}>
      <div style={{ position: "relative" as const, aspectRatio: "4 / 3", background: "var(--card-bg-soft)" }}>
        {item.kind === "reel" ? (
          <video src={assetUrl} muted loop playsInline
            onMouseEnter={(e) => e.currentTarget.play().catch(() => {})}
            onMouseLeave={(e) => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
        ) : (
          <img src={assetUrl} alt={item.headline || item.campaign_name}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
        )}
        <span style={{
          position: "absolute" as const, top: 8, left: 8, fontSize: 10, fontWeight: 800,
          padding: "3px 9px", borderRadius: 99, letterSpacing: "0.06em", textTransform: "uppercase" as const,
          background: item.kind === "reel" ? "rgba(236,72,153,0.92)" : "rgba(124,58,237,0.92)",
          color: "white",
        }}>{item.kind === "reel" ? "🎬 Reel" : "🎨 KV"}</span>
      </div>

      <div style={{ padding: "12px 14px", display: "flex", flexDirection: "column" as const, gap: 4, flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{item.brand}</div>
        {item.campaign_name && (
          <div style={{ fontSize: 11, color: "var(--text-secondary)", overflow: "hidden",
            textOverflow: "ellipsis", whiteSpace: "nowrap" as const }}>{item.campaign_name}</div>
        )}
        {item.headline && (
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontStyle: "italic", lineHeight: 1.4,
            display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any, overflow: "hidden" }}>
            "{item.headline}"
          </div>
        )}
        <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>{formatDate(item.created_at)}</div>

        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <a href={assetUrl} download={`${item.brand}-${item.kind}-${item.id}.${ext}`}
            style={{
              flex: 1, textAlign: "center" as const, fontSize: 12, fontWeight: 700,
              padding: "7px 10px", borderRadius: 8, textDecoration: "none",
              background: "var(--accent)", color: "white",
            }}>⬇ Download</a>
          <button onClick={() => onDelete(item.id)}
            style={{
              fontSize: 12, fontWeight: 600, padding: "7px 10px", borderRadius: 8,
              border: "1px solid var(--card-border)", background: "transparent",
              color: "var(--text-tertiary)", cursor: "pointer", fontFamily: "inherit",
            }}>🗑</button>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ onStartCampaign }: { onStartCampaign?: () => void }) {
  return (
    <div style={{
      position: "relative" as const, overflow: "hidden",
      borderRadius: 24, padding: "70px 32px",
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

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 40px", background: "var(--page-bg)",
      display: "flex", flexDirection: "column" as const,
      alignItems: isEmpty ? "center" as const : "stretch" as const,
      justifyContent: isEmpty ? "center" as const : "flex-start" as const }}>
      <div style={{ maxWidth: 1200, width: "100%", margin: "0 auto" }}>
        <h2 style={{ fontSize: 28, fontWeight: 900, color: "var(--text-primary)", margin: "0 0 6px",
          textAlign: isEmpty ? "center" as const : "left" as const }}>
          Content <span style={{ background: "linear-gradient(135deg,#7c3aed,#a78bfa)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>Hub</span>
        </h2>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 14px",
          textAlign: isEmpty ? "center" as const : "left" as const }}>
          {items.length > 0
            ? `${items.length} saved asset${items.length === 1 ? "" : "s"} — your campaign library.`
            : "Every key visual and reel you've saved, in one library."}
        </p>

        {loading && items.length === 0 && (
          <div style={{ color: "var(--text-tertiary)", fontSize: 14 }}>Loading…</div>
        )}
        {error && (
          <div style={{ color: "#ef4444", fontSize: 13, marginBottom: 16 }}>Couldn't load Content Hub: {error}</div>
        )}
        {isEmpty && <EmptyState onStartCampaign={onStartCampaign} />}

        {!isEmpty && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 18 }}>
            {items.map((item) => (
              <ContentHubCard key={item.id} item={item} onDelete={remove} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
