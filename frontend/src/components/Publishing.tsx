import type { PublishingChannel } from "./PublishingNav";
import MailchimpPanel from "./Mailchimp";

const CHANNEL_META: Record<PublishingChannel, {
  label: string; color: string; desc: string; formats: string[];
}> = {
  instagram: {
    label: "Instagram", color: "#E1306C",
    desc: "Share campaign visuals, reels and stories to your Instagram audience.",
    formats: ["Feed Post (1:1)", "Stories (9:16)", "Reels (9:16)", "Carousel"],
  },
  facebook: {
    label: "Facebook", color: "#1877F2",
    desc: "Publish campaign content to Facebook pages and run targeted ad campaigns.",
    formats: ["Feed Post", "Stories", "Video", "Carousel Ad"],
  },
  linkedin: {
    label: "LinkedIn", color: "#0A66C2",
    desc: "Reach professional audiences with thought leadership and brand content.",
    formats: ["Single Image", "Video Post", "Document/PDF", "Carousel"],
  },
  tiktok: {
    label: "TikTok", color: "#010101",
    desc: "Publish short-form video reels and TVCs to TikTok for maximum reach.",
    formats: ["Video (9:16)", "Photo Mode", "Duet / Stitch"],
  },
  youtube: {
    label: "YouTube", color: "#FF0000",
    desc: "Upload full campaign videos and TVC films to your YouTube channel.",
    formats: ["Standard (16:9)", "Shorts (9:16)", "Pre-roll Ad"],
  },
  website: {
    label: "Website", color: "#7c3aed",
    desc: "Publish campaign landing pages and hero banners directly to your brand website.",
    formats: ["Landing Page", "Hero Banner", "Pop-up / Modal", "Blog Post"],
  },
  email: {
    label: "Email", color: "#0369a1",
    desc: "Send personalised HTML email campaigns via Eloqua or direct SMTP delivery.",
    formats: ["HTML Email", "Plain Text", "Newsletter", "Transactional"],
  },
};

interface PublishingProps {
  channel: PublishingChannel;
}

export default function Publishing({ channel }: PublishingProps) {
  const meta = CHANNEL_META[channel];

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" as const,
      alignItems: "center", justifyContent: "center",
      overflowY: "auto", position: "relative" as const, padding: "40px 24px" }}>

      {/* Page header */}
      <div style={{ maxWidth: 520, width: "100%", marginBottom: 28,
        position: "relative" as const, zIndex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, flexShrink: 0,
            background: `${meta.color}22`, border: `1.5px solid ${meta.color}55`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18 }}>
            {channel === "instagram" && "📸"}
            {channel === "facebook"  && "📘"}
            {channel === "linkedin"  && "💼"}
            {channel === "tiktok"    && "🎵"}
            {channel === "youtube"   && "▶️"}
            {channel === "website"   && "🌐"}
            {channel === "email"     && "📧"}
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800,
              color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
              {meta.label}
            </h1>
            <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>
              {meta.desc}
            </p>
          </div>

        </div>
      </div>

      {/* Content formats */}
      <div style={{ maxWidth: 520, width: "100%", position: "relative" as const, zIndex: 1 }}>
        <div style={{ padding: 24, borderRadius: 16,
          background: "var(--card-bg)", border: "1px solid var(--card-border)",
          boxShadow: "var(--shadow-sm)", marginBottom: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)",
            letterSpacing: "0.08em", textTransform: "uppercase" as const, marginBottom: 14 }}>
            Supported Formats
          </div>
          <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
            {meta.formats.map(f => (
              <span key={f} style={{ padding: "5px 14px", borderRadius: 99, fontSize: 12,
                fontWeight: 500, background: "var(--card-bg-soft)",
                border: "1px solid var(--card-border)", color: "var(--text-secondary)" }}>
                {f}
              </span>
            ))}
          </div>
        </div>

        {/* Email → Mailchimp panel; others → coming soon */}
        {channel === "email" ? (
          <MailchimpPanel />
        ) : (
          <div style={{ padding: 28, borderRadius: 16, textAlign: "center" as const,
            background: "var(--card-bg)", border: "1px solid var(--card-border)" }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🚀</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", marginBottom: 6 }}>
              Publishing to {meta.label} coming soon
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Connect your {meta.label} account to publish campaigns, reels and key visuals
              directly from CampaignOS — no manual export needed.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
