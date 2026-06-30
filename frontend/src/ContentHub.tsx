import { useState } from "react";
import { contentHubAssetUrl, useContentHub, type ContentHubItem } from "./hooks/useContentHub";

function SlideCard({ item, onDelete }: { item: ContentHubItem; onDelete: (id: string) => void }) {
  const assetUrl = contentHubAssetUrl(item.id);
  const ext = item.kind === "reel" ? "mp4" : item.content_type.includes("png") ? "png" : "jpg";
  const isReel = item.kind === "reel";

  return (
    <div style={{ position: "relative" as const, width: "100%", height: "100%", overflow: "hidden" }}>
      {isReel ? (
        <video src={assetUrl} muted autoPlay loop playsInline
          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
      ) : (
        <img src={assetUrl} alt={item.headline || item.brand} loading="lazy"
          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
      )}

      {/* Permanent bottom gradient for text legibility */}
      <div style={{
        position: "absolute" as const, bottom: 0, left: 0, right: 0, height: "55%",
        background: "linear-gradient(to top, rgba(0,0,0,0.82) 0%, transparent 100%)",
        pointerEvents: "none" as const,
      }} />

      {/* Metadata */}
      <div style={{ position: "absolute" as const, bottom: 24, left: 28, right: 80 }}>
        <div style={{ fontSize: 13, fontWeight: 800, color: "rgba(255,255,255,0.75)",
          letterSpacing: "0.04em", marginBottom: 4, textTransform: "uppercase" as const }}>
          {item.brand}
        </div>
        {item.headline && (
          <div style={{ fontSize: 20, fontWeight: 700, color: "white", lineHeight: 1.3,
            textShadow: "0 2px 8px rgba(0,0,0,0.4)",
            display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any,
            overflow: "hidden" }}>
            "{item.headline}"
          </div>
        )}
      </div>

      {/* Action buttons — always visible bottom-right */}
      <div style={{ position: "absolute" as const, bottom: 24, right: 24, display: "flex", gap: 8 }}>
        <a href={assetUrl} download={`${item.brand}-${item.kind}-${item.id}.${ext}`}
          style={{
            width: 36, height: 36, borderRadius: "50%", display: "flex", alignItems: "center",
            justifyContent: "center", textDecoration: "none", fontSize: 14,
            background: "rgba(255,255,255,0.18)", backdropFilter: "blur(8px)",
            border: "1px solid rgba(255,255,255,0.3)", color: "white",
            transition: "background 0.15s",
          }}>⬇</a>
        <button onClick={() => onDelete(item.id)} style={{
          width: 36, height: 36, borderRadius: "50%", display: "flex", alignItems: "center",
          justifyContent: "center", cursor: "pointer", fontSize: 14, fontFamily: "inherit",
          border: "1px solid rgba(255,255,255,0.2)", background: "rgba(239,68,68,0.55)",
          backdropFilter: "blur(8px)", color: "white", transition: "background 0.15s",
        }}>🗑</button>
      </div>
    </div>
  );
}

function Carousel({ items, onDelete, aspectRatio, accent }: {
  items: ContentHubItem[]; onDelete: (id: string) => void;
  aspectRatio: string; accent: string;
}) {
  const [idx, setIdx] = useState(0);
  const current = items[idx];
  if (!current) return null;

  const prev = () => setIdx(i => (i - 1 + items.length) % items.length);
  const next = () => setIdx(i => (i + 1) % items.length);

  return (
    <div style={{ position: "relative" as const, width: "100%" }}>
      {/* Main slide */}
      <div key={current.id} style={{
        aspectRatio, width: "100%", borderRadius: 18, overflow: "hidden",
        boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
        animation: "msg-in 0.3s ease both",
      }}>
        <SlideCard item={current} onDelete={onDelete} />
      </div>

      {/* Navigation — only if more than one item */}
      {items.length > 1 && (
        <>
          {/* Prev arrow */}
          <button onClick={prev} style={{
            position: "absolute" as const, left: -20, top: "50%", transform: "translateY(-50%)",
            width: 40, height: 40, borderRadius: "50%", border: "none", cursor: "pointer",
            background: "var(--card-bg-translucent)", backdropFilter: "blur(12px)",
            boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
            color: "var(--text-primary)", fontSize: 18, fontWeight: 700,
            display: "flex", alignItems: "center", justifyContent: "center",
            transition: "transform 0.15s, box-shadow 0.15s",
          }}>‹</button>

          {/* Next arrow */}
          <button onClick={next} style={{
            position: "absolute" as const, right: -20, top: "50%", transform: "translateY(-50%)",
            width: 40, height: 40, borderRadius: "50%", border: "none", cursor: "pointer",
            background: "var(--card-bg-translucent)", backdropFilter: "blur(12px)",
            boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
            color: "var(--text-primary)", fontSize: 18, fontWeight: 700,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>›</button>
        </>
      )}

      {/* Dot indicators + counter */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 16, marginTop: 20 }}>
        <div style={{ display: "flex", gap: 6 }}>
          {items.map((_, i) => (
            <button key={i} onClick={() => setIdx(i)} style={{
              width: i === idx ? 22 : 7, height: 7, borderRadius: 99, border: "none",
              cursor: "pointer", padding: 0,
              background: i === idx ? accent : "var(--card-border)",
              transition: "all 0.25s ease",
              boxShadow: i === idx ? `0 0 8px ${accent}80` : "none",
            }} />
          ))}
        </div>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)" }}>
          {idx + 1} / {items.length}
        </span>
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
        }}><span style={{ fontSize: 36 }}>📚</span></div>

        <h3 style={{ fontSize: 22, fontWeight: 900, color: "var(--text-primary)", margin: "0 0 8px" }}>
          Your library is just getting started
        </h3>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6,
          maxWidth: 420, margin: "0 auto 26px" }}>
          Every key visual and reel you save lands here — downloadable and ready to reuse.
          Hit <strong style={{ color: "var(--text-primary)" }}>"💾 Save to Content Hub"</strong> on
          any generated asset.
        </p>
        {onStartCampaign && (
          <button onClick={onStartCampaign} style={{
            padding: "12px 28px", borderRadius: 12, border: "none", cursor: "pointer",
            fontFamily: "inherit", fontSize: 14, fontWeight: 700, color: "white",
            background: "linear-gradient(135deg, #7c3aed 0%, #a855f7 55%, #6366f1 100%)",
            boxShadow: "0 6px 24px rgba(124,58,237,0.40)",
          }}>✨ Start a Campaign</button>
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

  if (isEmpty) {
    return (
      <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 40px", background: "var(--page-bg)",
        display: "flex", alignItems: "center" as const, justifyContent: "center" as const }}>
        <div style={{ maxWidth: 900, width: "100%" }}>
          <h2 style={{ fontSize: 28, fontWeight: 900, color: "var(--text-primary)", margin: "0 0 6px",
            textAlign: "center" as const }}>
            Content <span style={{ background: "linear-gradient(135deg,#7c3aed,#a78bfa)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>Hub</span>
          </h2>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px", textAlign: "center" as const }}>
            Every key visual and reel you've saved, in one library.
          </p>
          <EmptyState onStartCampaign={onStartCampaign} />
        </div>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, background: "var(--page-bg)",
      padding: "40px 60px 60px" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ marginBottom: 40 }}>
          <h2 style={{ fontSize: 28, fontWeight: 900, color: "var(--text-primary)", margin: "0 0 4px" }}>
            Content <span style={{ background: "linear-gradient(135deg,#7c3aed,#a78bfa)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>Hub</span>
          </h2>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0 }}>
            {items.length} saved asset{items.length === 1 ? "" : "s"} — your campaign library.
          </p>
        </div>

        {error && (
          <div style={{ color: "#ef4444", fontSize: 13, marginBottom: 20 }}>
            Couldn't load Content Hub: {error}
          </div>
        )}

        {/* Image Gallery — landscape 16:9 carousel */}
        {kvItems.length > 0 && (
          <div style={{ marginBottom: 56 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
              <span style={{ fontSize: 16 }}>🎨</span>
              <h3 style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                Image Gallery
              </h3>
              <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 10px", borderRadius: 99,
                background: "rgba(124,58,237,0.14)", color: "#7c3aed" }}>{kvItems.length}</span>
            </div>
            <div style={{ padding: "0 24px" }}>
              <Carousel items={kvItems} onDelete={remove} aspectRatio="16 / 9" accent="#7c3aed" />
            </div>
          </div>
        )}

        {/* Reel Gallery — portrait 9:16 carousel, narrower */}
        {reelItems.length > 0 && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
              <span style={{ fontSize: 16 }}>🎬</span>
              <h3 style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                Reel Gallery
              </h3>
              <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 10px", borderRadius: 99,
                background: "rgba(236,72,153,0.14)", color: "#ec4899" }}>{reelItems.length}</span>
            </div>
            <div style={{ padding: "0 24px" }}>
              <Carousel items={reelItems} onDelete={remove} aspectRatio="16 / 9" accent="#ec4899" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
