export type PublishingChannel =
  | "instagram"
  | "facebook"
  | "linkedin"
  | "tiktok"
  | "youtube"
  | "website"
  | "email";

interface ChannelItem {
  id: PublishingChannel;
  label: string;
  color: string;
  icon: React.ReactNode;
}

const IMAGE_CHANNEL_IDS: PublishingChannel[] = ["instagram", "facebook", "linkedin", "website", "email"];
const VIDEO_CHANNEL_IDS: PublishingChannel[] = ["tiktok", "youtube", "instagram"];

const CHANNELS: ChannelItem[] = [
  {
    id: "instagram",
    label: "Instagram",
    color: "#E1306C",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <defs>
          <linearGradient id="ig" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor="#f09433"/>
            <stop offset="25%"  stopColor="#e6683c"/>
            <stop offset="50%"  stopColor="#dc2743"/>
            <stop offset="75%"  stopColor="#cc2366"/>
            <stop offset="100%" stopColor="#bc1888"/>
          </linearGradient>
        </defs>
        <rect x="2" y="2" width="20" height="20" rx="5" fill="url(#ig)"/>
        <circle cx="12" cy="12" r="4.5" stroke="white" strokeWidth="1.8" fill="none"/>
        <circle cx="17.5" cy="6.5" r="1.2" fill="white"/>
      </svg>
    ),
  },
  {
    id: "facebook",
    label: "Facebook",
    color: "#1877F2",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <rect width="24" height="24" rx="5" fill="#1877F2"/>
        <path d="M16 8h-2a1 1 0 0 0-1 1v2h3l-.5 3H13v7h-3v-7H8v-3h2V9a4 4 0 0 1 4-4h2v3z"
          fill="white"/>
      </svg>
    ),
  },
  {
    id: "linkedin",
    label: "LinkedIn",
    color: "#0A66C2",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <rect width="24" height="24" rx="4" fill="#0A66C2"/>
        <path d="M7 10h2v7H7v-7zm1-3a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3zm4 3h2v1h.1A2.8 2.8 0 0 1 16.6 10c2.2 0 2.4 1.5 2.4 3.4V17h-2v-3.2c0-.8 0-1.8-1.1-1.8-1.2 0-1.3.9-1.3 1.8V17H12v-7z"
          fill="white"/>
      </svg>
    ),
  },
  {
    id: "tiktok",
    label: "TikTok",
    color: "#010101",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <rect width="24" height="24" rx="5" fill="#010101"/>
        <path d="M16.5 5.5c.4.7 1.1 1.2 1.9 1.4v2a5 5 0 0 1-2.9-.9v4.3a4 4 0 1 1-2.5-3.7v2.1a2 2 0 1 0 1.4 1.9V5.5h2.1z"
          fill="white"/>
      </svg>
    ),
  },
  {
    id: "youtube",
    label: "YouTube",
    color: "#FF0000",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <rect width="24" height="24" rx="5" fill="#FF0000"/>
        <path d="M19.6 8.3A2 2 0 0 0 18.2 6.9C16.8 6.5 12 6.5 12 6.5s-4.8 0-6.2.4A2 2 0 0 0 4.4 8.3C4 9.7 4 12 4 12s0 2.3.4 3.7a2 2 0 0 0 1.4 1.4c1.4.4 6.2.4 6.2.4s4.8 0 6.2-.4a2 2 0 0 0 1.4-1.4c.4-1.4.4-3.7.4-3.7s0-2.3-.4-3.7z"
          fill="white"/>
        <path d="M10 15V9l5 3-5 3z" fill="#FF0000"/>
      </svg>
    ),
  },
  {
    id: "website",
    label: "Website",
    color: "#7c3aed",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <rect width="24" height="24" rx="5" fill="#7c3aed"/>
        <circle cx="12" cy="12" r="7" stroke="white" strokeWidth="1.5" fill="none"/>
        <path d="M12 5c-2 2-3 4.5-3 7s1 5 3 7M12 5c2 2 3 4.5 3 7s-1 5-3 7M5 12h14"
          stroke="white" strokeWidth="1.5" fill="none"/>
      </svg>
    ),
  },
  {
    id: "email",
    label: "Email",
    color: "#0369a1",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <rect width="24" height="24" rx="5" fill="#0369a1"/>
        <rect x="4" y="7" width="16" height="11" rx="1.5" stroke="white" strokeWidth="1.5" fill="none"/>
        <path d="M4 8l8 6 8-6" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
  },
];

interface PublishingNavProps {
  active: PublishingChannel;
  onChange: (c: PublishingChannel) => void;
  onPolyClick?: () => void;
  contentFilter?: "image" | "video";
}

export default function PublishingNav({ active, onChange, onPolyClick, contentFilter }: PublishingNavProps) {
  const visibleChannels = contentFilter
    ? CHANNELS.filter(ch =>
        contentFilter === "image"
          ? IMAGE_CHANNEL_IDS.includes(ch.id)
          : VIDEO_CHANNEL_IDS.includes(ch.id)
      )
    : CHANNELS;

  return (
    <div style={{ padding: "0 8px" }}>

      {/* Poly agent row */}
      <button
        onClick={onPolyClick}
        style={{ display: "flex", alignItems: "center", gap: 10,
          padding: "8px 10px", borderRadius: 8, border: "none",
          cursor: "pointer", fontFamily: "inherit", width: "100%",
          background: "transparent", transition: "all 0.15s" }}
        onMouseEnter={e => (e.currentTarget.style.background = "var(--card-hover-bg)")}
        onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
      >
        <img src="/agent-logo/Poly.png" alt="Poly"
          style={{ width: 22, height: 22, borderRadius: 6,
            objectFit: "cover" as const, flexShrink: 0 }} />
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)",
            lineHeight: 1.2 }}>Poly</div>
          <div style={{ fontSize: 10, color: "var(--text-secondary)", marginTop: 1 }}>
            Channel Adaptation
          </div>
        </div>
      </button>

      {/* Channels — indented under Poly */}

      {/* Left border to show nesting under Poly */}
      <div style={{ marginLeft: 18, borderLeft: "1.5px solid var(--card-border)",
        paddingLeft: 6 }}>
        {visibleChannels.map(ch => {
          const isActive = ch.id === active;
          return (
            <button
              key={ch.id}
              onClick={() => onChange(ch.id)}
              style={{
                display: "flex", alignItems: "center", gap: 9,
                padding: "7px 8px", borderRadius: 7, border: "none",
                cursor: "pointer", fontFamily: "inherit", width: "100%",
                transition: "all 0.15s",
                background: isActive ? "rgba(124,58,237,0.10)" : "transparent",
              }}
              onMouseEnter={e => {
                if (!isActive) e.currentTarget.style.background = "var(--card-hover-bg)";
              }}
              onMouseLeave={e => {
                if (!isActive) e.currentTarget.style.background = "transparent";
              }}
            >
              <span style={{ flexShrink: 0 }}>{ch.icon}</span>
              <span style={{ fontSize: 12, fontWeight: isActive ? 600 : 500,
                color: isActive ? "#7c3aed" : "var(--text-secondary)" }}>
                {ch.label}
              </span>
            </button>
          );
        })}

        {/* Connect Channel */}
        <button
          style={{ display: "flex", alignItems: "center", gap: 7,
            padding: "7px 8px", borderRadius: 7, border: "none",
            cursor: "pointer", fontFamily: "inherit", width: "100%",
            background: "transparent", transition: "all 0.15s",
            fontSize: 12, fontWeight: 500, color: "#7c3aed", marginTop: 2 }}
          onMouseEnter={e => e.currentTarget.style.background = "rgba(124,58,237,0.08)"}
          onMouseLeave={e => e.currentTarget.style.background = "transparent"}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Connect Channel
        </button>
      </div>
    </div>
  );
}
