import { useState, useMemo, useCallback, useEffect, useRef, Component, Fragment, type ReactNode, type ErrorInfo } from "react";

// ── Error boundary — shows error instead of blank page ────────
class ErrorBoundary extends Component<{ children: ReactNode }, { error: string | null }> {
  state = { error: null };
  static getDerivedStateFromError(e: Error) { return { error: e.message }; }
  componentDidCatch(e: Error, info: ErrorInfo) { console.error("CampaignOS render error:", e, info); }
  render() {
    if (this.state.error) return (
      <div style={{ padding: 48, fontFamily: "Inter,sans-serif", color: "var(--text-primary)", background: "var(--page-bg)", minHeight: "100vh" }}>
        <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8, color: "#f87171" }}>⚠ Render Error</div>
        <pre style={{ fontSize: 12, background: "var(--card-bg)", border: "1px solid rgba(255,255,255,0.09)", padding: 16, borderRadius: 8, overflowX: "auto" as const, color: "var(--text-tertiary)" }}>{this.state.error}</pre>
        <button onClick={() => this.setState({ error: null })} style={{ marginTop: 16, padding: "8px 20px",
          borderRadius: 8, border: "none", background: "#0055A4", color: "white", cursor: "pointer" }}>
          Dismiss
        </button>
      </div>
    );
    return this.props.children;
  }
}
import "./App.css";
import { usePipeline } from "./hooks/usePipeline";
import { useTheme } from "./hooks/useTheme";
import { saveToContentHub } from "./hooks/useContentHub";
import ContentHub from "./ContentHub";
import CampaignForm from "./components/CampaignForm";
import type { HarnessBriefRequest, AgentEvent } from "./types/pipeline";

// ── Infosys Aster logo — top-left header (small, with "Powered by") ──
function AsterLogo({ size = 1 }: { size?: number }) {
  const w = 90 * size, h = 53 * size;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, userSelect: "none" as const }}>
      <span style={{ fontSize: 10 * size, color: "var(--text-tertiary)", fontWeight: 400,
        fontFamily: "'Inter',sans-serif", letterSpacing: "0.05em",
        textTransform: "uppercase" as const, whiteSpace: "nowrap" as const }}>
        Powered by
      </span>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 499.39 292.79"
        width={w} height={h} style={{ display: "block", flexShrink: 0 }}>
        <defs><style>{`.al1{fill:#004a85}.al2{fill:#221f1f}.al3,.al4{fill:#0c7ec2}.al4{fill-rule:evenodd}.al5{fill:#231f20}`}</style></defs>
        <path className="al2" d="M438.29,120.34l1.13-2.09s.04-.08.07-.13l-1.2,2.22"/>
        <g>
          <path className="al3" d="M444.83,32.23s0,0,0,0h0c.08.18.13.33.18.41l-.18-.43v.02"/>
          <polyline className="al4" points="132.5 12.96 132.5 .36 145.01 .36 145.01 104.33 132.5 104.33 132.5 12.96"/>
          <path className="al5" d="M372.98,119.68l1.11-2.04s.04-.08.07-.13l-1.17,2.17"/>
          <path className="al3" d="M363.11,43.19s0,0,0,0h0c.08.18.13.33.18.41l-.18-.43v.02"/>
          <path className="al3" d="M436.59,60.35c-13.67-6.78-18.31-8.21-18.18-15.96,0-10.32,8.44-13.44,15.45-13.44,7.99,0,13.03,2.96,20.07,8.08v-12.06c-5.72-1.99-10.49-2.78-16.93-2.75-12.98-.03-24.77,4.71-27.72,15.7l-16.11,39.82-1.66,5.01-1.47-5.01-12.75-31.02-4.21-10.33c-.03-.08-.07-.15-.1-.23h0c-.15-.35-.3-.74-.43-1.07l-4.16-10.25c-1.5-.41-3.34-.84-5.28-1.28h0s0,0,0,0c-4-.87-8.58-1.63-12.13-1.58-.53,0-1.12,0-1.68,0-15.02-.02-29.47,6.3-29.47,21.24,0,.87.05,1.68.1,2.48-6.02-14.3-19-24.2-34.06-24.2h-.44c-1.65.03-3.28.18-4.92.43h-42.3c-1.73-10.71,3.24-16.8,10.73-16.8,9.43,0,13.49,2.8,17.57,6.58,0,0,.28,0,.41.03,0,0,0-.49.02-1.25V2.12C264.26.9,259.57,0,251.07,0,237.94,0,228.49,8.64,227.16,23.94h-10.1v7.57h9.97v60.2c0,.23,0,.43-.03.63v11.98h11.32V31.52h25.44c-9.41,7.62-15.53,20.01-15.53,34.01,0,23.05,16.61,41.76,37.18,42.02h0c.15,0,.31,0,.44,0,20.77,0,37.6-18.81,37.6-42.02,0-2.75-.25-5.45-.71-8.08,3.75,6.02,10.89,8.95,20.5,13.1,11.34,4.8,17.69,8.97,17.69,16.12,0,8.59-8.11,13.03-17.21,12.98-8.9,0-15.86-3.62-23.61-10.66v13.49c4.71,3.04,12.05,4.79,19.96,4.79,6.12-.02,16.14-1.37,23.02-7.19h0,0c4.36-3.7,7.45-9.18,7.45-17.23-.03-6.66-2.98-11.3-7.45-14.89h0s0,0,0,0c-3.92-3.19-8.97-5.56-14.22-7.85-13.66-6.78-18.87-8.18-18.72-15.96,0-10.33,8.97-13.44,15.99-13.44,3.05,0,5.68.43,8.16,1.28,4.62,1.73,6.15,5.17,7.77,8.89.49,1.15.82,1.89,1.02,2.32v-.02s-.27-.64-.27-.64l.27.61h0s0,0,0,0h0s0,0,0,0c.18.43.39.9.18.46l9.69,23.38,11.65,28.12c-3.6,8.21-7.62,16.8-10.41,22.26l-.07.15-.07.13c-.41.77-.77,1.49-1.11,2.12-.43.84-.83,1.56-1.14,2.09l-2.63,4.89h11.1c4.84-10.7,25.39-60.75,29.8-71.51,2.9,7.75,10.02,10.86,20.85,15.55,11.35,4.79,17.7,8.97,17.7,16.14,0,8.56-8.11,13.02-17.22,12.95-9.25,0-16.42-3.91-24.5-11.48l-.74-.58v13.72c4.53,3.77,12.69,5.97,21.59,5.97,9.97-.02,30.47-3.62,30.47-24.43-.05-12.47-10.43-17.85-21.67-22.72M286,100.23h-.58c-13.93-.18-25.37-15.12-25.7-33.76-.34-18.92,10.91-34.45,25.12-34.68.2-.03.41-.03.58,0,13.94.15,25.4,15.12,25.7,33.76.33,18.89-10.91,34.43-25.12,34.68Z"/>
          <path className="al4" d="M168.37,24.71l.13,9.1v.61h.12c.13-.38.33-.71.51-.94,4.62-4.94,10.4-9.82,24.17-9.82s21.69,11.2,22.05,18.23v49.82s0,12.62,0,12.62h-11.29v-57.29c0-8.77-7.71-15.12-17.17-15.12-7.82,0-17.92,7.06-18.25,14.2v45.61l.03.34v12.26h-11.32l.03-12.59-.03-56.55.03-10.48h10.99"/>
          <path className="al1" d="M305.92,274.48h2.15s0,16.62,0,16.62h-.96c-31.77.02-56.86-25.22-56.86-56.88v-94.99h16.28v41.56h41.53v16.54h-41.53v34.86c0,28.68,21.99,42.4,39.39,42.29"/>
          <path className="al1" d="M96.83,234.71c.11-20.29-14.44-40.63-40.14-40.73-23.13-.09-39.8,18.24-40.27,39.49-.45,20.48,15.05,40.8,39.97,41.01,22.85.19,40.32-17.46,40.44-39.76M0,234.4c-.01-30.66,24.28-56.85,56.58-57,14.94-.07,29.72,6,40.48,16.66v-12.86h16.28v108.39h-16.28v-15.05c-10.45,10.4-24.86,16.57-40.19,16.58C23.02,291.12.02,263.69,0,234.4Z"/>
          <path className="al1" d="M337.27,244.85c4.68,17.93,18.9,29.42,35.46,29.42,12.67,0,24.55-6.63,30.79-18.12h20.27c-8.38,22.21-28.64,36.63-51.83,36.63-30.4,0-54.95-26.89-54.95-55.73,0-34.1,25.72-57.87,54.37-57.87,31.76,0,55.92,24.55,55.92,55.54,0,3.31,0,6.43-.58,10.13h-89.44ZM407.03,229.26c-1.56-18.32-17.73-31.57-35.07-31.57s-33.13,13.06-34.69,31.57h69.76Z"/>
          <path className="al1" d="M443.53,288.88v-111.31h16.55v11.91h.34c4.27-7.3,26.51-10.83,38.97-11.62v19.9c-15.35.59-38.11-.12-38.11,29.78v61.34h-17.74Z"/>
          <path className="al1" d="M166.97,225.99h-6.88c-8.84,0-16.07-7.23-16.07-16.07h0c0-8.84,7.23-16.07,16.07-16.07h43.53c8.84,0,16.07,7.23,16.07,16.07h0s15.78-.19,15.78-.19v-2.94c0-15.61-12.77-28.39-28.39-28.39h-50.44c-15.61,0-28.39,12.77-28.39,28.39v6.26c0,15.61,12.77,28.39,28.39,28.39h8.6l5.08-.05h33.3c8.84,0,16.07,7.23,16.07,16.07h0c0,8.84-7.23,16.07-16.07,16.07h-43.53c-8.84,0-16.07-7.23-16.07-16.07h0l-15.78.19v2.94c0,15.61,12.77,28.39,28.39,28.39h50.44c15.61,0,28.39-12.77,28.39-28.39v-6.26c0-15.61-12.77-28.39-28.39-28.39h-35.92l-4.18.05Z"/>
        </g>
      </svg>
    </div>
  );
}


// ── Wizard constants ─────────────────────────────────────────

type GoalId = "launch" | "sales" | "community" | "reengagement" | "expansion" | "custom";

const GOALS = [
  { id: "launch"       as GoalId, icon: "🚀", label: "Launch Awareness",  desc: "Introduce a new product" },
  { id: "sales"        as GoalId, icon: "📈", label: "Drive Sales",        desc: "Increase transactions & ROAS" },
  { id: "community"    as GoalId, icon: "👥", label: "Build Community",    desc: "Grow brand advocates" },
  { id: "reengagement" as GoalId, icon: "🎯", label: "Re-engagement",      desc: "Win back lapsed customers" },
  { id: "expansion"    as GoalId, icon: "🌍", label: "Market Expansion",   desc: "Enter new territories" },
  { id: "custom"       as GoalId, icon: "✏️", label: "Custom",             desc: "Write your own goal" },
];

const BRANDS = [
  { id: "Rnorr",       label: "Rnorr",       emoji: "🥣", logo: "/brands/rnorr-logo.png"       },
  { id: "Sunglow",     label: "Sunglow",     emoji: "✨", logo: "/brands/sunglow-logo.png"     },
  { id: "Boozt",       label: "Boozt",       emoji: "💨", logo: "/brands/boozt-logo.png"       },
  { id: "Glenfiddich", label: "Glenfiddich × AMF1", emoji: "🥃", logo: "/brands/glenfiddich-logo.png" },
  { id: "UBS Bank",    label: "UBS Bank",    emoji: "🏦", logo: "/brands/ubs-bank-logo.png"    },
];


const BRAND_PRODUCTS: Record<string, string[]> = {
  Rnorr:     ["Chicken Stock Cubes", "Beef Stock Cubes", "Vegetable Stock Cubes",
              "Stock Pots", "Bouillon Powder", "Concentrated Liquid Stock",
              "Soup Range", "Gravy Granules", "Seasoning Sachets"],
  Sunglow:   ["Moisture Shampoo", "Moisture Conditioner", "Deep Repair Treatment",
              "Scalp Nourish Oil", "Define & Glow Serum", "Leave-In Conditioner",
              "Curl Refresh Spray", "Edge Control", "Protective Style Serum"],
  Boozt:       ["Original Energy", "Zero Sugar", "Sport Hydration",
               "Tropical Blast", "Arctic Mint", "Classic"],
  Glenfiddich: ["16 Year Old — AMF1 Limited Edition", "12 Year Old", "15 Year Old",
               "18 Year Old", "21 Year Old Gran Reserva", "14 Year Old Bourbon Cask",
               "IPA Experiment", "Project XX", "Grand Cru 23 Year Old"],
  "UBS Bank":  ["Wealth Management", "Private Banking", "Asset Management",
               "Investment Banking", "Sustainable Finance", "Family Office Services",
               "Philanthropy Advisory", "Corporate Solutions", "Personal Banking"],
};

const BRAND_CATEGORY: Record<string, string> = {
  Rnorr:       "Dry Cook-In Sauces",
  Sunglow:     "Hair Care",
  Boozt:       "Energy Drinks",
  Glenfiddich: "Single Malt Scotch Whisky × Aston Martin F1",
  "UBS Bank":  "Private Banking & Wealth Management",
};

const BRAND_FAN_TRUTHS: Record<string, string[]> = {
  Rnorr: [
    "That moment when a weeknight dinner smells like it took all day",
    "Real flavour shouldn't take real time",
    "The shortcut that feels like cheating — but isn't",
    "Home cooking is how you say 'I care' without saying it",
    "A stock cube is the secret ingredient every great cook pretends isn't there",
  ],
  Sunglow: [
    "The first look in the mirror after wash day — that's your glow",
    "Your crown is not a problem to manage, it's a conversation to have",
    "Good hair day isn't luck — it's science built for you from the start",
    "Hair that glows because it's healthy, not because it's hidden",
    "When your hair does exactly what it wants to — and you let it",
  ],
  Boozt: [
    "That first sip when you need to switch on — that's a Boozt moment",
    "Energy that moves with you, not against you",
    "The can that turns 'I can't' into 'watch me'",
    "Peak performance isn't a personality — it's a decision you make every day",
    "Zero limits. Pure energy. One can.",
  ],
  Glenfiddich: [
    "Two icons. One bottle. The moment after the race is the one worth celebrating.",
    "16 years of patience. One season of speed. Both take everything you've got.",
    "The podium moment is loud. What you raise a glass to afterwards is yours alone.",
    "When you gift a Glenfiddich AMF1, you're not giving a bottle — you're giving a story.",
    "136 years of craft. The same obsession Aston Martin bring to every lap.",
    "The first sip of a whisky that's older than most of your friendships",
  ],
  "UBS Bank": [
    "Confidence isn't about having all the answers — it's about having the right advisor.",
    "When your wealth works as hard as you do, clarity replaces complexity.",
    "The best financial decisions aren't made in a rush — they're made with precision.",
    "A clearer financial future isn't a luxury. It's what the right partnership makes possible.",
    "Real wealth isn't just what you accumulate — it's what you protect for the next generation.",
  ],
};

const AGE_GROUPS       = ["13–17", "18–24", "25–34", "35–44", "45–54", "55+"];
const ALCOHOL_BRANDS   = ["Glenfiddich"];
const INTERESTS: Record<string, string[]> = {
  Rnorr:     ["Home cooks", "Families", "Students", "Budget shoppers", "Food lovers", "Meal preppers", "Time-poor professionals"],
  Sunglow:   ["Natural hair community", "Protective styles", "Wash day routines", "Scalp health", "Curl definition", "Black hair care", "Beauty enthusiasts"],
  Boozt:       ["Athletes & gym-goers", "Students", "Festival-goers", "Gamers", "Young professionals", "Outdoor adventurers"],
  Glenfiddich: ["F1 enthusiasts", "Whisky connoisseurs", "Premium gifters", "Luxury collectors", "Corporate entertainers", "Motorsport fans", "Occasion celebrators"],
  "UBS Bank":  ["High-net-worth individuals", "Investors & wealth builders", "Entrepreneurs & founders", "Family offices", "Institutional investors", "Sustainable finance advocates", "Premium banking clients"],
  default:     ["Families", "Students", "Young professionals", "Beauty lovers", "Lifestyle"],
};
const REGIONS     = ["United Kingdom", "Australia", "United States", "New Zealand", "SEA", "Global"];
const SEASONS     = ["Spring", "Summer", "Autumn", "Winter", "All Year"];
const MOMENT_TYPES = ["Day-to-Day", "Brand Moment", "Partnership Moment"];

const CHANNELS_LIST = [
  { id: "Instagram",  icon: "📸", label: "Instagram" },
  { id: "TikTok",     icon: "🎵", label: "TikTok" },
  { id: "YouTube",    icon: "▶️", label: "YouTube" },
  { id: "OOH",        icon: "🏙️", label: "OOH" },
  { id: "Google Ads", icon: "🔍", label: "Google Ads" },
  { id: "Meta Ads",   icon: "📘", label: "Meta Ads" },
  { id: "Website",    icon: "🌐", label: "Website" },
  { id: "Email",      icon: "📧", label: "Email" },
];

const KPI_OPTIONS = [
  { id: "reach",       label: "5M Reach" },
  { id: "ctr",         label: "2.5% CTR" },
  { id: "roas",        label: "3x ROAS" },
  { id: "conversions", label: "+10% Conv." },
  { id: "engagement",  label: "4% Engagement" },
  { id: "views",       label: "10M Views" },
];

const BUDGETS = [
  { value: "£50,000",   label: "£50K",  desc: "Pilot" },
  { value: "£100,000",  label: "£100K", desc: "Regional" },
  { value: "£250,000",  label: "£250K", desc: "Multi-channel" },
  { value: "£500,000",  label: "£500K", desc: "Full campaign" },
  { value: "£1,000,000",label: "£1M",   desc: "Flagship" },
  { value: "custom",    label: "Custom", desc: "Enter amount" },
];

interface WizardData {
  campaignName: string;
  brand: string;
  mode: "new" | "adapt" | "";
  goal: GoalId | "";
  goalCustom: string;
  product: string;
  productCustom: string;
  fanTruth: string;
  fanTruthCustom: string;
  audienceAge: string[];
  audienceInterests: string[];
  audienceRegions: string[];
  season: string;
  momentType: string;
  channels: string[];
  kpis: string[];
  budget: string;
  budgetCustom: string;
  uploadedAssets: string[];
  uploadedFileNames: string[];
}

// ── A2A orb gradient — matches the brand logo PNG ─────────────
// White glass highlight top-right, hot pink/magenta centre, lavender-purple edges
const ORB_BG = [
  "radial-gradient(circle at 71% 26%, rgba(255,255,255,0.88) 0%, rgba(255,255,255,0) 42%)",
  "radial-gradient(circle at 36% 54%, #f028cc 0%, #cc3cf2 26%, #8840e0 52%, #b898f8 80%, #ddd6fe 100%)",
].join(", ");

// Website-videos clips used as ambient background videos in the wizard
const BG_REELS = [
  "https://storage.googleapis.com/dauntless-karma-497108-b0-campaignos/website-videos/clip4.mp4",
  "https://storage.googleapis.com/dauntless-karma-497108-b0-campaignos/website-videos/clip7.mp4",
  "https://storage.googleapis.com/dauntless-karma-497108-b0-campaignos/website-videos/clip11.mp4",
  "https://storage.googleapis.com/dauntless-karma-497108-b0-campaignos/website-videos/clip14.mp4",
];


// ── Smooth crossfade background video player ─────────────────
function BgVideoPlayer({
  fixed = false,
  brightness = 0.5,
  saturate = 1.1,
  onIndex,
}: {
  fixed?: boolean;
  brightness?: number;
  saturate?: number;
  onIndex?: (i: number) => void;
}) {
  const [slot, setSlot] = useState<0 | 1>(0);
  const refA = useRef<HTMLVideoElement>(null);
  const refB = useRef<HTMLVideoElement>(null);
  const slotIdx = useRef<[number, number]>([0, 1 % BG_REELS.length]);
  const nextIdx = useRef(2 % BG_REELS.length);

  const handleEnded = (finished: 0 | 1) => {
    const other = (1 - finished) as 0 | 1;
    const otherRef = other === 0 ? refA : refB;
    otherRef.current?.play().catch(() => {});
    setSlot(other);
    onIndex?.(slotIdx.current[other]);
    setTimeout(() => {
      const upcoming = nextIdx.current;
      slotIdx.current[finished] = upcoming;
      nextIdx.current = (upcoming + 1) % BG_REELS.length;
      const finishedRef = finished === 0 ? refA : refB;
      if (finishedRef.current) {
        finishedRef.current.src = BG_REELS[upcoming];
        finishedRef.current.load();
      }
    }, 900);
  };

  const pos = fixed
    ? { position: "fixed" as const, inset: 0 }
    : { position: "absolute" as const, inset: 0 };

  const base: React.CSSProperties = {
    ...pos,
    width: "100%", height: "100%",
    objectFit: "cover" as const,
    zIndex: 0,
    filter: `brightness(${brightness}) saturate(${saturate})`,
    pointerEvents: "none" as const,
    transition: "opacity 0.8s ease-in-out",
  };

  return (
    <>
      <video ref={refA} muted playsInline autoPlay
        src={BG_REELS[0]}
        onEnded={() => handleEnded(0)}
        style={{ ...base, opacity: slot === 0 ? 1 : 0 }} />
      <video ref={refB} muted playsInline
        src={BG_REELS[1 % BG_REELS.length]}
        onEnded={() => handleEnded(1)}
        style={{ ...base, opacity: slot === 1 ? 1 : 0 }} />
    </>
  );
}

// ── Harness pipeline agents (for loading display) ────────────
// Order matches actual backend execution
const HARNESS_STAGES = [
  { key: "briefing",     icon: "📋", label: "Logos",    desc: "Validating brief & Fan Truth score" },
  { key: "strategy",     icon: "💡", label: "Helia",    desc: "Building big idea & strategy" },
  { key: "copy",         icon: "✍️", label: "Ideon",    desc: "Writing campaign copy variants" },
  { key: "culture",      icon: "🌍", label: "Aether",   desc: "Researching cultural intelligence" },
  { key: "kv",           icon: "🎨", label: "Morphis",  desc: "Generating key visual with Gemini 3 Pro Image" },
  { key: "reel",         icon: "🎬", label: "Kinetik",  desc: "Generating 6s campaign reel with Veo" },
  { key: "channel",      icon: "📡", label: "Poly",     desc: "Publishing to Instagram, TikTok & more" },
  { key: "performance",  icon: "📊", label: "Nexus",    desc: "Forecasting reach, ROAS & channel performance" },
];

// First 7 agents shown as individual nav entries in the sidebar (Nexus/Performance excluded —
// it's a forecasting stage, not a content-producing creative agent like the other seven).
const SIDEBAR_AGENT_KEYS = ["briefing", "strategy", "copy", "culture", "kv", "reel", "channel"];


// ── Individual agent profile page (static — sidebar nav) ──────
// ── Brand onboarding upload panel (Logos agent only) ───────────
function BrandUploadPanel() {
  const [brandName, setBrandName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [uploaded, setUploaded] = useState<Record<string, number>>({});
  const [skipped, setSkipped] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState("");

  const handleUpload = async () => {
    if (!brandName.trim() || !file) return;
    setStatus("uploading");
    setErrorMsg(""); setUploaded({}); setSkipped([]);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API_BASE_PUB}/brands/${encodeURIComponent(brandName.trim())}/upload`, {
        method: "POST", body: fd,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `Upload failed (${res.status})`);
      setUploaded(data.uploaded ?? {});
      setSkipped(data.skipped ?? []);
      setStatus("done");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  };

  return (
    <div style={{ marginTop: 12, paddingTop: 16, borderTop: "1px solid var(--card-border)" }}>
      <div style={{ fontSize: 13, fontWeight: 800, color: "var(--text-primary)", marginBottom: 4 }}>
        📁 Onboard a new brand
      </div>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5, margin: "0 0 14px" }}>
        Upload a .zip with <code>Guidelines/</code>, <code>Logos/</code>, <code>Font/</code>,{" "}
        <code>Colours/</code> and <code>Assets/</code> subfolders. Logos will re-index its search
        index so it can immediately retrieve the new brand's guidelines.
      </p>

      <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
        <input value={brandName} onChange={(e) => setBrandName(e.target.value)}
          placeholder="Brand name (e.g. Acme Corp)"
          style={{ flex: 1, padding: "8px 12px", borderRadius: 8, fontSize: 13,
            border: "1px solid var(--card-border)", background: "var(--input-bg)",
            color: "var(--text-primary)", fontFamily: "inherit", outline: "none" }} />
        <label style={{ padding: "8px 14px", borderRadius: 8, fontSize: 13, fontWeight: 600,
          border: "1px solid var(--card-border)", background: "var(--card-bg-soft)",
          color: "var(--text-secondary)", cursor: "pointer", whiteSpace: "nowrap" as const }}>
          {file ? file.name.slice(0, 22) : "Choose .zip"}
          <input type="file" accept=".zip" style={{ display: "none" }}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </label>
      </div>

      <button onClick={handleUpload} disabled={!brandName.trim() || !file || status === "uploading"}
        style={{ padding: "9px 18px", borderRadius: 10, border: "none", fontFamily: "inherit",
          fontSize: 13, fontWeight: 700, color: "white", cursor: (!brandName.trim() || !file) ? "default" : "pointer",
          opacity: (!brandName.trim() || !file) ? 0.4 : 1,
          background: "linear-gradient(135deg, #7c3aed, #6366f1)" }}>
        {status === "uploading" ? "Uploading & indexing…" : "Upload & index"}
      </button>

      {status === "error" && (
        <div style={{ marginTop: 12, fontSize: 12, lineHeight: 1.5, color: "#ef4444" }}>⚠ {errorMsg}</div>
      )}

      {status === "done" && (
        <div style={{ marginTop: 14, padding: "14px 16px", borderRadius: 12,
          background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.25)" }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#10b981", marginBottom: 6 }}>
            ✓ "{brandName.trim()}" indexed and searchable
          </div>
          <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 6, marginBottom: skipped.length ? 8 : 0 }}>
            {Object.entries(uploaded).map(([cat, n]) => (
              <span key={cat} style={{ fontSize: 11, fontWeight: 600, padding: "3px 9px", borderRadius: 99,
                background: "var(--card-bg-soft)", border: "1px solid var(--card-border)",
                color: "var(--text-secondary)" }}>{n} {cat}</span>
            ))}
            {Object.keys(uploaded).length === 0 && (
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>No files matched a known category.</span>
            )}
          </div>
          {skipped.length > 0 && (
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8 }}>
              {skipped.length} file{skipped.length > 1 ? "s" : ""} skipped (not inside a recognised subfolder):{" "}
              {skipped.slice(0, 3).join(", ")}{skipped.length > 3 ? `, +${skipped.length - 3} more` : ""}
            </div>
          )}
          <div style={{ fontSize: 11.5, color: "var(--text-tertiary)", lineHeight: 1.55,
            borderTop: "1px solid rgba(16,185,129,0.18)", paddingTop: 8 }}>
            Logos can now retrieve this brand's guidelines for brief validation. It's <strong>not yet</strong>{" "}
            selectable in the campaign wizard's brand picker — that list is still a fixed set and needs a
            separate code change (logo asset, product list, fan truths) to add a new brand there.
          </div>
        </div>
      )}
    </div>
  );
}

// ── Standalone single-agent run panel ──────────────────────────
const STANDALONE_SUPPORTED = ["briefing", "strategy", "copy", "culture", "channel", "kv", "reel"];

// Card styling for Poly's per-channel results — distinct accent colors so each
// channel reads like its own platform, not a generic key/value list.
const POLY_CHANNEL_CFG: Record<string, { icon: string; label: string; color: string }> = {
  instagram:     { icon: "📸", label: "Instagram",     color: "#c026d3" },
  tiktok:        { icon: "🎵", label: "TikTok",         color: "#0f172a" },
  email_subject: { icon: "📧", label: "Email Subject",  color: "#0369a1" },
  ooh:           { icon: "🏙️", label: "OOH Billboard",  color: "#d97706" },
};

function AgentRunPanel({ agentKey, agentLabel, color, prompt, onPromptChange }: {
  agentKey: string; agentLabel: string; color: string;
  prompt: string; onPromptChange: (v: string) => void;
}) {
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [result, setResult] = useState<Record<string, any> | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [activeChannel, setActiveChannel] = useState<string | null>(null);
  const [channelEmail, setChannelEmail] = useState("");
  const [channelStatus, setChannelStatus] = useState<"idle" | "sending" | "done" | "error">("idle");
  const [channelResult, setChannelResult] = useState<Record<string, any> | null>(null);
  const [kvSaveState, setKvSaveState] = useState<"idle" | "saving" | "saved">("idle");
  // Standalone email preview modal
  const [showStandaloneEmailPreview, setShowStandaloneEmailPreview] = useState(false);
  const [saSubject,  setSaSubject]  = useState("");
  const [saHeadline, setSaHeadline] = useState("");
  const [saBody,     setSaBody]     = useState("");
  const supported = STANDALONE_SUPPORTED.includes(agentKey);

  const handleSaveKvToHub = async () => {
    if (!result?.image_b64) return;
    setKvSaveState("saving");
    try {
      await saveToContentHub({
        kind: "kv", brand: result.brand ?? "", campaignName: "", campaignId: "",
        headline: result.headline ?? "",
        assetDataUrl: `data:image/jpeg;base64,${result.image_b64}`,
      });
      setKvSaveState("saved");
      setTimeout(() => setKvSaveState("idle"), 2500);
    } catch (e) {
      console.error("standalone_kv_save_failed", e);
      setKvSaveState("idle");
    }
  };

  const [reelSaveState, setReelSaveState] = useState<"idle" | "saving" | "saved">("idle");

  const handleSaveReelToHub = async () => {
    if (!result?.video_b64) return;
    setReelSaveState("saving");
    try {
      await saveToContentHub({
        kind: "reel", brand: result.brand ?? "", campaignName: "", campaignId: "",
        headline: result.headline ?? "",
        assetDataUrl: `data:video/mp4;base64,${result.video_b64}`,
      });
      setReelSaveState("saved");
      setTimeout(() => setReelSaveState("idle"), 2500);
    } catch (e) {
      console.error("standalone_reel_save_failed", e);
      setReelSaveState("idle");
    }
  };

  const handleRun = async () => {
    if (!prompt.trim()) return;
    setStatus("running"); setErrorMsg(""); setResult(null);
    setKvSaveState("idle"); setReelSaveState("idle");
    setActiveChannel(null); setChannelStatus("idle"); setChannelResult(null);
    try {
      const res = await fetch(`${API_BASE_PUB}/agents/${agentKey}/run`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `Run failed (${res.status})`);
      setResult(data);
      setStatus("done");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  };

  const handlePublishChannel = async (channel: string) => {
    if (!result?.landing_page_id) return;
    if (channel === "email" && !channelEmail.trim()) return;
    setChannelStatus("sending"); setChannelResult(null);
    try {
      const res = await fetch(`${API_BASE_PUB}/agents/channel/publish`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          page_id:       result.landing_page_id,
          channel,
          to_email:      channelEmail.trim(),
          // Pass the preview-edited values so user edits reach the email
          email_subject: saSubject  || undefined,
          headline:      saHeadline || undefined,
          body:          saBody     || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `Publish failed (${res.status})`);
      setChannelResult(data);
      setChannelStatus(data?.status === "error" ? "error" : "done");
    } catch (e) {
      setChannelResult({ error: e instanceof Error ? e.message : String(e) });
      setChannelStatus("error");
    }
  };

  const AGENT_AGENDA: Record<string, string> = {
    briefing: "What campaign should I brief and validate?",
    strategy: "What campaign strategy should I build?",
    copy:     "What headlines and copy should I write?",
    culture:  "What cultural insights should I research?",
    kv:       "What key visual should I create?",
    reel:     "What campaign reel should I generate?",
    channel:  "How should I adapt this campaign for channels?",
  };

  const AGENT_RUNNING_MSG: Record<string, string> = {
    briefing: "Logos is validating your brief and scoring the Fan Truth…",
    strategy: "Helia is building your campaign strategy and big idea…",
    copy:     "Ideon is writing headlines and copy for your campaign…",
    culture:  "Aether is researching cultural trends and audience insights…",
    kv:       "Morphis is generating your key visual with Gemini 3 Pro Image…",
    reel:     "Kinetik is generating your 6-second reel with Veo — this can take 2-5 minutes…",
    channel:  "Poly is adapting your campaign across channels and building the landing page…",
  };

  return (
    <div style={{ marginTop: 20 }}>
      {status === "running" ? (
        /* ── Running state — replaces the prompt card ── */
        <div style={{ textAlign: "center" as const, padding: "32px 16px" }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>
            {agentLabel} is working…
          </div>
          <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6, maxWidth: 320, margin: "0 auto 20px",
            textShadow: "0 1px 4px rgba(255,255,255,0.2)" }}>
            {AGENT_RUNNING_MSG[agentKey] ?? `${agentLabel} is processing your request…`}
          </div>
          <div style={{ display: "flex", justifyContent: "center", gap: 6 }}>
            {[0, 1, 2].map(i => (
              <div key={i} style={{
                width: 8, height: 8, borderRadius: "50%", background: color,
                animation: `pulse-glow 1.2s ${i * 0.2}s ease-in-out infinite`,
              }} />
            ))}
          </div>
        </div>
      ) : (
        <>
          {/* Greeting — left-aligned, close to prompt */}
          <h3 style={{ fontSize: 20, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 10px", lineHeight: 1.3 }}>
            <span style={{ background: `linear-gradient(135deg, ${color}, #6366f1)`,
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
              Hello!
            </span>{" "}
            {AGENT_AGENDA[agentKey] ?? `What would you like ${agentLabel} to do?`}
          </h3>

          {/* Chat-style prompt card */}
          <div style={{
            borderRadius: 16, border: "1px solid var(--card-border)", background: "var(--card-bg)",
            boxShadow: "var(--shadow-sm)", overflow: "hidden",
          }}>
            <textarea value={prompt} onChange={(e) => onPromptChange(e.target.value)}
              rows={1}
              placeholder="Describe your brand, market, and campaign direction — I'll help you move it forward"
              style={{ width: "100%", padding: "18px 16px", border: "none", resize: "none" as const,
                background: "transparent", color: "var(--text-primary)", fontFamily: "inherit",
                fontSize: 13, lineHeight: 1.6, outline: "none", boxSizing: "border-box" as const,
                display: "block", minHeight: 58 }} />

            {/* Action row */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "8px 12px", borderTop: "1px solid var(--card-border)" }}>
              <button style={{ width: 28, height: 28, borderRadius: "50%", border: "1px solid var(--card-border)",
                background: "var(--card-bg-soft)", color: "var(--text-tertiary)", cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 400 }}>
                +
              </button>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <button style={{ width: 32, height: 32, borderRadius: "50%", border: "1px solid var(--card-border)",
                  background: "var(--card-bg-soft)", color: "var(--text-tertiary)", cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>
                  🎤
                </button>
                <button onClick={handleRun} disabled={!supported || !prompt.trim()}
                  style={{
                    width: 32, height: 32, borderRadius: "50%", border: "none",
                    cursor: (!supported || !prompt.trim()) ? "default" : "pointer",
                    opacity: (!supported || !prompt.trim()) ? 0.4 : 1, fontFamily: "inherit",
                    background: `linear-gradient(135deg, ${color}, #6366f1)`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: "white", fontSize: 14, fontWeight: 700,
                  }}>→</button>
              </div>
            </div>
          </div>
        </>
      )}

      {status === "error" && (
        <div style={{ marginTop: 12, fontSize: 12, lineHeight: 1.5, color: "#ef4444" }}>⚠ {errorMsg}</div>
      )}

      {agentKey === "channel" && status === "done" && result?.landing_page_id && (
        <div style={{ marginTop: 16, paddingLeft: 14, borderLeft: `2px solid ${color}40` }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.06em",
            textTransform: "uppercase" as const, marginBottom: 8 }}>Publish to a channel</div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" as const, marginBottom: 10 }}>
            {[
              { key: "landing_page", icon: "🌐", label: "Website" },
              { key: "email",        icon: "📧", label: "Email" },
              { key: "google_ads",   icon: "🔍", label: "Google Ads" },
            ].map((ch) => (
              <button key={ch.key} onClick={() => setActiveChannel(ch.key)}
                style={{
                  display: "flex", alignItems: "center", gap: 6, padding: "7px 14px", borderRadius: 10,
                  border: `1.5px solid ${activeChannel === ch.key ? color : "var(--card-border)"}`,
                  background: activeChannel === ch.key ? `${color}18` : "var(--card-bg-soft)",
                  color: activeChannel === ch.key ? color : "var(--text-secondary)",
                  fontSize: 12, fontWeight: 700, cursor: "pointer", fontFamily: "inherit",
                }}>
                <span>{ch.icon}</span>{ch.label}
              </button>
            ))}
            {[
              { icon: "📸", label: "Instagram" }, { icon: "🎵", label: "TikTok" },
              { icon: "▶️", label: "YouTube" }, { icon: "🏙️", label: "OOH" }, { icon: "📘", label: "Meta Ads" },
            ].map((ch) => (
              <span key={ch.label} title="Not available for standalone runs" style={{
                display: "flex", alignItems: "center", gap: 6, padding: "7px 14px", borderRadius: 10,
                border: "1.5px solid var(--card-border)", background: "transparent",
                color: "var(--text-muted)", fontSize: 12, fontWeight: 600, opacity: 0.45, cursor: "not-allowed",
              }}>
                <span>{ch.icon}</span>{ch.label}
              </span>
            ))}
          </div>

          {activeChannel === "landing_page" && (
            <a href={`${API_BASE_PUB}/agents/landing/${result.landing_page_id}`} target="_blank" rel="noreferrer"
              style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "8px 16px",
                borderRadius: 9, fontFamily: "inherit", fontSize: 12, fontWeight: 700, color: "white",
                textDecoration: "none", background: `linear-gradient(135deg, ${color}, #6366f1)` }}>
              🌐 Open landing page ↗
            </a>
          )}

          {activeChannel === "email" && (
            <>
              {/* Standalone email preview modal */}
              {showStandaloneEmailPreview && (
                <div style={{ position: "fixed" as const, inset: 0, zIndex: 1000,
                  background: "rgba(0,0,0,0.55)", display: "flex", alignItems: "center",
                  justifyContent: "center", padding: 24 }}
                  onClick={e => { if (e.target === e.currentTarget) setShowStandaloneEmailPreview(false); }}>
                  <div style={{ width: "100%", maxWidth: 540, borderRadius: 20,
                    background: "var(--card-bg)", border: "1px solid var(--card-border)",
                    boxShadow: "0 24px 60px rgba(0,0,0,0.35)",
                    display: "flex", flexDirection: "column" as const, maxHeight: "90vh" }}>

                    {/* Sticky header */}
                    <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--card-border)",
                      display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
                      <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>📧 Email Preview</div>
                      <button onClick={() => setShowStandaloneEmailPreview(false)}
                        style={{ background: "none", border: "none", cursor: "pointer",
                          fontSize: 20, color: "var(--text-secondary)", lineHeight: 1, padding: 4 }}>✕</button>
                    </div>
                    <div style={{ padding: "14px 24px 0", flexShrink: 0 }}>
                      <label style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
                        textTransform: "uppercase" as const, color: "var(--text-secondary)", display: "block", marginBottom: 5 }}>
                        Subject line
                      </label>
                      <input value={saSubject} onChange={e => setSaSubject(e.target.value)}
                        placeholder="Email subject…"
                        style={{ width: "100%", padding: "9px 13px", borderRadius: 9,
                          border: "1.5px solid var(--card-border)", background: "var(--page-bg)",
                          color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit",
                          outline: "none", boxSizing: "border-box" as const }}
                        onFocus={e => e.currentTarget.style.borderColor = color}
                        onBlur={e => e.currentTarget.style.borderColor = "var(--card-border)"} />
                    </div>

                    {/* Scrollable body */}
                    <div style={{ overflowY: "auto", flex: 1 }}>
                      <div style={{ margin: "14px 24px", borderRadius: 12, overflow: "hidden",
                        border: "1px solid var(--card-border)", background: "#ffffff" }}>
                        {result?.image_b64 && (
                          <img src={`data:image/jpeg;base64,${result.image_b64}`} alt=""
                            style={{ width: "100%", maxHeight: 260, objectFit: "contain" as const, display: "block", background: "#f8fafc" }} />
                        )}
                        <div style={{ padding: "18px 20px", fontFamily: "Georgia, serif" }}>
                          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em",
                            textTransform: "uppercase" as const, color: "#888", marginBottom: 4, fontFamily: "system-ui" }}>Headline</div>
                          <textarea value={saHeadline} onChange={e => setSaHeadline(e.target.value)} rows={2}
                            style={{ width: "100%", fontSize: 20, fontWeight: 700, color: "#0f172a",
                              fontFamily: "Georgia, serif", border: "1.5px dashed #d0d0e0", borderRadius: 8,
                              background: "#fafafa", padding: "7px 10px", resize: "none" as const,
                              outline: "none", lineHeight: 1.3, boxSizing: "border-box" as const, marginBottom: 10 }}
                            onFocus={e => e.currentTarget.style.borderColor = color}
                            onBlur={e => e.currentTarget.style.borderColor = "#d0d0e0"} />
                          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em",
                            textTransform: "uppercase" as const, color: "#888", marginBottom: 4, fontFamily: "system-ui" }}>Body copy</div>
                          <textarea value={saBody} onChange={e => setSaBody(e.target.value)} rows={4}
                            style={{ width: "100%", fontSize: 13, color: "#374151", lineHeight: 1.7,
                              fontFamily: "Georgia, serif", border: "1.5px dashed #d0d0e0", borderRadius: 8,
                              background: "#fafafa", padding: "7px 10px", resize: "none" as const,
                              outline: "none", boxSizing: "border-box" as const }}
                            onFocus={e => e.currentTarget.style.borderColor = color}
                            onBlur={e => e.currentTarget.style.borderColor = "#d0d0e0"} />
                        </div>
                      </div>
                    </div>

                    {/* Sticky footer */}
                    <div style={{ padding: "14px 24px", borderTop: "1px solid var(--card-border)",
                      display: "flex", gap: 10, alignItems: "center", flexShrink: 0 }}>
                      <input type="email" placeholder="recipient@email.com" value={channelEmail}
                        onChange={e => setChannelEmail(e.target.value)}
                        style={{ flex: 1, padding: "9px 13px", borderRadius: 9,
                          border: "1.5px solid var(--card-border)", background: "var(--page-bg)",
                          color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit", outline: "none" }} />
                      <button onClick={() => { setShowStandaloneEmailPreview(false); handlePublishChannel("email"); }}
                        disabled={!channelEmail.trim() || channelStatus === "sending"}
                        style={{ padding: "9px 20px", borderRadius: 9, border: "none", fontWeight: 700,
                          fontSize: 13, whiteSpace: "nowrap" as const,
                          cursor: channelEmail.trim() ? "pointer" : "not-allowed",
                          background: channelEmail.trim() ? `linear-gradient(135deg,${color},#6366f1)` : "rgba(124,58,237,0.15)",
                          color: channelEmail.trim() ? "white" : "rgba(124,58,237,0.4)" }}>
                        {channelStatus === "sending" ? "Sending…" : "Send Email →"}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              <button onClick={() => {
                setSaSubject(result?.email_subject ?? result?.headline ?? "");
                setSaHeadline(result?.headline ?? "");
                setSaBody(result?.body ?? result?.copy ?? result?.landing_body ?? result?.headline ?? "");
                setShowStandaloneEmailPreview(true);
              }}
                style={{ padding: "8px 16px", borderRadius: 9, border: "none", fontFamily: "inherit",
                  fontSize: 12, fontWeight: 700, color: "white", cursor: "pointer",
                  background: `linear-gradient(135deg, ${color}, #6366f1)` }}>
                👁 Preview & Edit Email
              </button>
            </>
          )}

          {activeChannel === "google_ads" && (
            <button onClick={() => handlePublishChannel("google_ads")} disabled={channelStatus === "sending"}
              style={{ padding: "8px 16px", borderRadius: 9, border: "none", fontFamily: "inherit",
                fontSize: 12, fontWeight: 700, color: "white", cursor: "pointer",
                background: `linear-gradient(135deg, ${color}, #6366f1)` }}>
              {channelStatus === "sending" ? "Submitting…" : "Submit mock ad"}
            </button>
          )}

          {channelStatus === "done" && channelResult && (
            <div style={{ marginTop: 10, fontSize: 12, lineHeight: 1.6, color: "#10b981" }}>
              ✓ {channelResult.status === "skipped" ? channelResult.reason :
                  channelResult.public_url ? <>Live at <a href={channelResult.public_url} target="_blank" rel="noreferrer" style={{ color: "#10b981" }}>{channelResult.public_url}</a></> :
                  channelResult.ad_id ? `Mock ad submitted — ${channelResult.ad_id} (${channelResult.headline_1 ?? ""})` :
                  channelResult.status === "sent" ? `Email sent to ${channelResult.to}` :
                  "Done."}
            </div>
          )}
          {channelStatus === "error" && channelResult && (
            <div style={{ marginTop: 10, fontSize: 12, color: "#ef4444" }}>
              ⚠ {channelResult.error ?? channelResult.reason ?? "Publish failed."}
            </div>
          )}
        </div>
      )}

      {status === "done" && result && agentKey === "channel" && (
        <div style={{ marginTop: 16, display: "flex", flexDirection: "column" as const, gap: 16 }}>

          {/* Campaign visual from Morphis/GCS */}
          {result.image_b64 && (
            <div style={{ borderRadius: 14, overflow: "hidden", position: "relative" as const,
              boxShadow: "var(--shadow-md)" }}>
              <img src={`data:image/jpeg;base64,${result.image_b64}`} alt="Campaign visual"
                style={{ width: "100%", display: "block", maxHeight: 280, objectFit: "cover" as const }} />
              {result.logo_b64 && (
                <div style={{ position: "absolute" as const, top: 12, right: 12,
                  background: "rgba(255,255,255,0.92)", backdropFilter: "blur(8px)",
                  borderRadius: 10, padding: "6px 10px",
                  border: "1px solid rgba(255,255,255,0.6)" }}>
                  <img src={`data:image/png;base64,${result.logo_b64}`} alt="Brand logo"
                    style={{ height: 28, objectFit: "contain" as const, display: "block" }} />
                </div>
              )}
            </div>
          )}

          {/* Channel copy cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
            {Object.entries(POLY_CHANNEL_CFG).filter(([key]) => result[key]).map(([key, cfg]) => (
              <div key={key} style={{
                borderRadius: 14, overflow: "hidden", background: "var(--card-bg-soft)",
                border: `1px solid ${cfg.color}30`,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px",
                  background: `${cfg.color}16`, borderBottom: `1px solid ${cfg.color}25` }}>
                  <span style={{ fontSize: 15 }}>{cfg.icon}</span>
                  <span style={{ fontSize: 11, fontWeight: 800, color: cfg.color, letterSpacing: "0.04em",
                    textTransform: "uppercase" as const }}>{cfg.label}</span>
                </div>
                <div style={{ padding: "14px 16px", fontSize: 13, color: "var(--text-primary)", lineHeight: 1.55 }}>
                  {String(result[key])}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {status === "done" && result && agentKey === "kv" && (
        <div style={{ marginTop: 16, paddingLeft: 14, borderLeft: `2px solid ${color}40` }}>
          {result.image_b64 ? (
            <>
              <img src={`data:image/jpeg;base64,${result.image_b64}`} alt={result.headline || "Key visual"}
                style={{ width: "100%", borderRadius: 14, display: "block",
                  boxShadow: "var(--shadow-md)" }} />
              {result.headline && (
                <div style={{ marginTop: 10, fontSize: 14, fontWeight: 700, color: "var(--text-primary)",
                  fontStyle: "italic" }}>"{result.headline}"</div>
              )}
              <div style={{ display: "flex", gap: 14, marginTop: 8 }}>
                <a href={`data:image/jpeg;base64,${result.image_b64}`} download="key-visual.jpg"
                  style={{ fontSize: 12, fontWeight: 700, color }}>
                  ⬇ Download
                </a>
                <button onClick={handleSaveKvToHub} disabled={kvSaveState === "saving"}
                  style={{ fontSize: 12, fontWeight: 700, background: "none", border: "none",
                    cursor: kvSaveState === "saving" ? "default" : "pointer", fontFamily: "inherit", padding: 0,
                    color: kvSaveState === "saved" ? "#10b981" : color }}>
                  {kvSaveState === "saved" ? "✓ Saved" : kvSaveState === "saving" ? "Saving…" : "💾 Save to Content Hub"}
                </button>
              </div>
            </>
          ) : (
            <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
              Headline generated ("{result.headline}") but image generation failed — try again.
            </div>
          )}
        </div>
      )}

      {status === "done" && result && agentKey === "reel" && (
        <div style={{ marginTop: 16, paddingLeft: 14, borderLeft: `2px solid ${color}40` }}>
          {result.video_b64 ? (
            <>
              <video controls autoPlay loop muted playsInline
                src={`data:video/mp4;base64,${result.video_b64}`}
                style={{ width: "100%", borderRadius: 14, display: "block",
                  boxShadow: "var(--shadow-md)" }} />
              {result.headline && (
                <div style={{ marginTop: 10, fontSize: 14, fontWeight: 700, color: "var(--text-primary)",
                  fontStyle: "italic" }}>"{result.headline}"</div>
              )}
              <div style={{ display: "flex", gap: 14, marginTop: 8 }}>
                <a href={`data:video/mp4;base64,${result.video_b64}`} download="campaign-reel.mp4"
                  style={{ fontSize: 12, fontWeight: 700, color }}>
                  ⬇ Download
                </a>
                <button onClick={handleSaveReelToHub} disabled={reelSaveState === "saving"}
                  style={{ fontSize: 12, fontWeight: 700, background: "none", border: "none",
                    cursor: reelSaveState === "saving" ? "default" : "pointer", fontFamily: "inherit", padding: 0,
                    color: reelSaveState === "saved" ? "#10b981" : color }}>
                  {reelSaveState === "saved" ? "✓ Saved" : reelSaveState === "saving" ? "Saving…" : "💾 Save to Content Hub"}
                </button>
              </div>
            </>
          ) : (
            <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
              Headline generated ("{result.headline}") but video generation failed — try again.
            </div>
          )}
        </div>
      )}

      {status === "done" && result && agentKey !== "channel" && agentKey !== "kv" && agentKey !== "reel" && (
        <div style={{ marginTop: 14, paddingLeft: 14, borderLeft: `2px solid ${color}40` }}>
          {Object.entries(result).filter(([k]) => k !== "agent").map(([key, val]) => (
            <div key={key} style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.06em",
                textTransform: "uppercase" as const, marginBottom: 2 }}>{key.replace(/_/g, " ")}</div>
              {Array.isArray(val) ? (
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "var(--text-primary)" }}>
                  {val.map((item, i) => <li key={i}>{String(item)}</li>)}
                </ul>
              ) : (
                <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.5 }}>{String(val)}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AgentProfile({ agentKey, prompt, onPromptChange }: {
  agentKey: string;
  prompt: string; onPromptChange: (v: string) => void;
}) {
  const idx   = HARNESS_STAGES.findIndex((s) => s.key === agentKey);
  const stage = HARNESS_STAGES[idx];
  if (!stage) return null;

  const color    = AGENT_COLORS[idx] ?? "#7c3aed";
  const longDesc = AGENT_DESCS[idx] ?? stage.desc;
  const avatar   = avatarUrl(stage.label, idx);
  const workflowStage = WORKFLOW_STAGES.find((w) => w.agents.includes(agentKey))?.label ?? "";

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "40px 48px",
      display: "flex", alignItems: "center", justifyContent: "center",
      position: "relative" as const, background: "transparent" }}>
      <div style={{ position: "absolute" as const, inset: 0, zIndex: 0, pointerEvents: "none" as const,
        background: `radial-gradient(ellipse 70% 55% at 50% 40%, ${color}14 0%, transparent 70%)` }} />

      <div style={{ maxWidth: 720, width: "100%", position: "relative" as const, zIndex: 1 }}>
        <div style={{ position: "relative" as const, overflow: "hidden", padding: "8px 4px 10px" }}>
          <div style={{ position: "absolute" as const, top: "-40%", right: "-10%", width: 320, height: 320,
            borderRadius: "50%", pointerEvents: "none" as const,
            background: `radial-gradient(circle, ${color}22 0%, transparent 70%)` }} />

          <div style={{ position: "relative" as const, zIndex: 1, display: "flex", alignItems: "center", gap: 20, marginBottom: 24 }}>
            <div style={{
              width: 76, height: 76, borderRadius: "50%", flexShrink: 0, position: "relative" as const,
              border: `3px solid ${color}80`, boxShadow: `0 0 28px ${color}40`, overflow: "hidden",
            }}>
              <img src={avatar} alt={stage.label} style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
            </div>
            <div>
              <div style={{ fontSize: 28, fontWeight: 900, color: "var(--text-primary)", lineHeight: 1.1 }}>
                {stage.label}
              </div>
              {workflowStage && (
                <span style={{
                  display: "inline-block", marginTop: 6, fontSize: 11, fontWeight: 700,
                  padding: "3px 10px", borderRadius: 99, letterSpacing: "0.04em",
                  background: `${color}18`, color,
                }}>{workflowStage}</span>
              )}
            </div>
          </div>

          <p style={{ position: "relative" as const, zIndex: 1, fontSize: 16, color: "var(--text-primary)",
            lineHeight: 1.6, margin: "0 0 24px", textShadow: "0 1px 6px rgba(255,255,255,0.25)" }}>
            {longDesc}
          </p>

        </div>

        {agentKey === "briefing" && <BrandUploadPanel />}

        {agentKey !== "performance" && (
          <AgentRunPanel agentKey={agentKey} agentLabel={stage.label} color={color}
            prompt={prompt} onPromptChange={onPromptChange} />
        )}
      </div>
    </div>
  );
}

// ── Brief Form (legacy multi-step wizard — replaced by CampaignForm) ────────
// @ts-expect-error: kept for reference, replaced by CampaignForm
function BriefForm({ onFullCampaign }: {
  onFullCampaign: (brief: HarnessBriefRequest) => void;
}) {
  const [step, setStep] = useState(0);
  const [d, setD] = useState<WizardData>({
    campaignName: "",
    brand: "",
    mode: "",
    goal: "", goalCustom: "",
    product: "", productCustom: "",
    fanTruth: "", fanTruthCustom: "",
    audienceAge: [], audienceInterests: [], audienceRegions: [],
    season: "", momentType: "",
    channels: [],
    kpis: [],
    budget: "", budgetCustom: "",
    uploadedAssets: [],
    uploadedFileNames: [],
  });

  const TOTAL_STEPS = d.mode === "adapt" ? 9 : 8;

  function toggle<T>(arr: T[], val: T): T[] {
    return arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val];
  }

  function canProceed(): boolean {
    switch (step) {
      case 0: return !!d.brand;
      case 1: return !!d.mode;
      case 2: return !!d.goal && (d.goal !== "custom" || !!d.goalCustom.trim());
      case 3: return !!d.product || !!d.productCustom.trim();
      case 4: return !!d.fanTruth || !!d.fanTruthCustom.trim();
      case 5: return true;
      case 6: return d.channels.length > 0 && d.kpis.length > 0;
      case 7: return d.budget !== "" || !!d.budgetCustom.trim();
      case 8: return d.campaignName.trim().length >= 3;
      case 9: return true;
      default: return true;
    }
  }


  function handleFullLaunch() {
    const goal       = d.goal === "custom" ? d.goalCustom : GOALS.find((g) => g.id === d.goal)?.label ?? "";
    const product    = d.product === "custom" ? d.productCustom : d.product;
    const fanTruth   = d.fanTruth === "custom" ? d.fanTruthCustom : d.fanTruth;
    const kpisStr    = d.kpis.map((k) => KPI_OPTIONS.find((o) => o.id === k)?.label ?? k).join(", ");
    const budget     = d.budget === "custom" ? `£${d.budgetCustom}` : d.budget;
    const ageRange   = d.audienceAge.length > 0 ? d.audienceAge[0].replace("–", "-") : "All ages";
    const market     = d.audienceRegions[0] ?? "UK";
    const category   = BRAND_CATEGORY[d.brand] ?? "Food & Beverage";

    const brief: HarnessBriefRequest = {
      campaign_name:    d.campaignName.trim(),
      brand:            d.brand,
      goal, budget, kpis: kpisStr, product,
      product_category: category,
      fan_truth:        fanTruth,
      channels:         d.channels,
      market, season: d.season, moment_type: d.momentType,
      audience: {
        segment:  d.audienceInterests.join(", ") || "General audience",
        location: market, age_range: ageRange, gender: "All genders",
        interests: d.audienceInterests.join(", ") || undefined,
      },
      tone: "Warm & friendly",
      mode: d.mode as "new" | "adapt",
      uploaded_assets: d.uploadedAssets,
    };
    onFullCampaign(brief);
  }

  const stepContent = () => {
    switch (step) {
      case 0:
        return (
          <>
            <div className="wizard-step-label">Step 1 of {TOTAL_STEPS}</div>
            <h2 className="wizard-heading">Select your <span className="gradient-text">brand</span></h2>
            <p className="wizard-subheading">Which brand is this campaign for?</p>
            <div className="goal-grid" style={{ gridTemplateColumns: "repeat(5, 1fr)" }}>
              {BRANDS.map((b) => (
                <div key={b.id} className={`goal-tile${d.brand === b.id ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, brand: b.id, product: "", productCustom: "" }))}>
                  <div className="goal-tile-icon" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 48,
                    background: b.id === "Glenfiddich" ? "#ffffff" : "transparent",
                    borderRadius: b.id === "Glenfiddich" ? 8 : 0,
                    padding: b.id === "Glenfiddich" ? "4px 10px" : 0 }}>
                    <img src={b.logo} alt={b.label}
                      style={{ height: b.id === "Glenfiddich" ? "auto" : 40, maxHeight: b.id === "Glenfiddich" ? 36 : 40, maxWidth: "100%", objectFit: "contain", display: "block" }} />
                  </div>
                  <div className="goal-tile-label">{b.label}</div>
                </div>
              ))}
            </div>
          </>
        );

      case 1:
        return (
          <>
            <div className="wizard-step-label">Step 2 of {TOTAL_STEPS}</div>
            <h2 className="wizard-heading">What type of <span className="gradient-text">campaign?</span></h2>
            <p className="wizard-subheading">Choose how you want to work with the AI agents</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 8 }}>
              <div
                className={`goal-tile${d.mode === "new" ? " selected" : ""}`}
                onClick={() => setD((p) => ({ ...p, mode: "new" }))}
                style={{ padding: "28px 20px", display: "flex", flexDirection: "column" as const, gap: 12, cursor: "pointer" }}>
                <span style={{ fontSize: 36 }}>✨</span>
                <div className="goal-tile-label" style={{ fontSize: 16 }}>New Campaign Creation</div>
                <div className="goal-tile-desc" style={{ lineHeight: 1.5 }}>
                  Build a full campaign from scratch — brief, strategy, key visuals, copy, and channel adaptation generated by AI.
                </div>
              </div>
              <div
                className={`goal-tile${d.mode === "adapt" ? " selected" : ""}`}
                onClick={() => setD((p) => ({ ...p, mode: "adapt" }))}
                style={{ padding: "28px 20px", display: "flex", flexDirection: "column" as const, gap: 12, cursor: "pointer" }}>
                <span style={{ fontSize: 36 }}>🔄</span>
                <div className="goal-tile-label" style={{ fontSize: 16 }}>Adapt Existing Campaign</div>
                <div className="goal-tile-desc" style={{ lineHeight: 1.5 }}>
                  Upload existing assets and let the AI adapt them for new channels, markets, or moments — faster and brand-safe.
                </div>
              </div>
            </div>
          </>
        );

      case 2:
        return (
          <>
            <div className="wizard-step-label">Step 3 of {TOTAL_STEPS}</div>
            <h2 className="wizard-heading">What's your <span className="gradient-text">campaign goal?</span></h2>
            <p className="wizard-subheading">Choose the primary objective for this campaign</p>
            <div className="goal-grid">
              {GOALS.map((g) => (
                <div key={g.id} className={`goal-tile${d.goal === g.id ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, goal: g.id }))}>
                  <span className="goal-tile-icon">{g.icon}</span>
                  <div className="goal-tile-label">{g.label}</div>
                  <div className="goal-tile-desc">{g.desc}</div>
                </div>
              ))}
            </div>
            {d.goal === "custom" && (
              <textarea className="dark-textarea" rows={3}
                placeholder="Describe your campaign goal..."
                value={d.goalCustom}
                onChange={(e) => setD((p) => ({ ...p, goalCustom: e.target.value }))} />
            )}
          </>
        );

      case 3:
        return (
          <>
            <div className="wizard-step-label">Step 4 of {TOTAL_STEPS}</div>
            <h2 className="wizard-heading">What are we <span className="gradient-text">promoting?</span></h2>
            <p className="wizard-subheading">Select a product or enter your own</p>
            <div className="chip-group">
              {(BRAND_PRODUCTS[d.brand] ?? []).map((p: string) => (
                <button key={p} className={`chip${d.product === p ? " selected" : ""}`}
                  onClick={() => setD((prev) => ({ ...prev, product: prev.product === p ? "" : p, productCustom: "" }))}>
                  {p}
                </button>
              ))}
              <button className={`chip${d.product === "custom" ? " selected" : ""}`}
                onClick={() => setD((p) => ({ ...p, product: "custom", productCustom: "" }))}>
                + Other
              </button>
            </div>
            {d.product === "custom" && (
              <input className="dark-input" placeholder="e.g. New McWrap"
                value={d.productCustom}
                onChange={(e) => setD((p) => ({ ...p, productCustom: e.target.value }))} />
            )}
          </>
        );

      case 4:
        return (
          <>
            <div className="wizard-step-label">Step 5 of {TOTAL_STEPS}</div>
            <h2 className="wizard-heading">What <span className="gradient-text">fan truth</span> drives this?</h2>
            <p className="wizard-subheading">Pick a {d.brand} fan truth or write your own</p>
            <div className="truth-stack">
              {(BRAND_FAN_TRUTHS[d.brand] ?? []).map((ft) => (
                <div key={ft} className={`truth-card${d.fanTruth === ft ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, fanTruth: ft, fanTruthCustom: "" }))}>
                  <span style={{ marginRight: 8, opacity: 0.4 }}>❝</span>{ft}
                </div>
              ))}
              <div className={`truth-card${d.fanTruth === "custom" ? " selected" : ""}`}
                onClick={() => setD((p) => ({ ...p, fanTruth: "custom" }))}>
                <span style={{ marginRight: 8 }}>✏️</span>Write your own...
              </div>
            </div>
            {d.fanTruth === "custom" && (
              <textarea className="dark-textarea" rows={3}
                placeholder="Describe the fan truth behind this campaign..."
                value={d.fanTruthCustom}
                onChange={(e) => setD((p) => ({ ...p, fanTruthCustom: e.target.value }))} />
            )}
          </>
        );

      case 5:
        return (
          <>
            <div className="wizard-step-label">Step 6 of {TOTAL_STEPS}</div>
            <h2 className="wizard-heading">Who are you <span className="gradient-text">targeting?</span></h2>
            <p className="wizard-subheading">Select all that apply</p>
            <div className="section-label">Age groups{ALCOHOL_BRANDS.includes(d.brand) ? " · 18+ only (UK alcohol law)" : ""}</div>
            <div className="chip-group">
              {AGE_GROUPS.filter(a => !ALCOHOL_BRANDS.includes(d.brand) || a !== "13–17").map((a) => (
                <button key={a} className={`chip${d.audienceAge.includes(a) ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, audienceAge: toggle(p.audienceAge, a) }))}>
                  {a}
                </button>
              ))}
            </div>
            <div className="section-label">Interests</div>
            <div className="chip-group">
              {(INTERESTS[d.brand as keyof typeof INTERESTS] ?? INTERESTS.default).map((i: string) => (
                <button key={i} className={`chip${d.audienceInterests.includes(i) ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, audienceInterests: toggle(p.audienceInterests, i) }))}>
                  {i}
                </button>
              ))}
            </div>
            <div className="section-label">Market / Region</div>
            <div className="chip-group">
              {REGIONS.map((r) => (
                <button key={r} className={`chip${d.audienceRegions.includes(r) ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, audienceRegions: toggle(p.audienceRegions, r) }))}>
                  {r}
                </button>
              ))}
            </div>
            <div className="section-label">Season</div>
            <div className="chip-group">
              {SEASONS.map((s) => (
                <button key={s} className={`chip${d.season === s ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, season: s }))}>
                  {s}
                </button>
              ))}
            </div>
          </>
        );

      case 6:
        return (
          <>
            <div className="wizard-step-label">Step 7 of {TOTAL_STEPS}</div>
            <h2 className="wizard-heading">Channels <span className="gradient-text">&amp; KPIs</span></h2>
            <p className="wizard-subheading">Where will the campaign run and how will we measure success?</p>
            <div className="section-label">Channels</div>
            <div className="channel-grid">
              {CHANNELS_LIST.map((ch) => (
                <div key={ch.id} className={`channel-tile${d.channels.includes(ch.id) ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, channels: toggle(p.channels, ch.id) }))}>
                  <span className="channel-icon">{ch.icon}</span>
                  <span className="channel-label">{ch.label}</span>
                </div>
              ))}
            </div>
            <div className="section-label">Success metrics</div>
            <div className="chip-group">
              {KPI_OPTIONS.map((k) => (
                <button key={k.id} className={`chip${d.kpis.includes(k.id) ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, kpis: toggle(p.kpis, k.id) }))}>
                  {k.label}
                </button>
              ))}
            </div>
            <div className="section-label">Campaign moment</div>
            <div className="chip-group">
              {MOMENT_TYPES.map((m) => (
                <button key={m} className={`chip${d.momentType === m ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, momentType: m }))}>
                  {m}
                </button>
              ))}
            </div>
          </>
        );

      case 7:
        return (
          <>
            <div className="wizard-step-label">Step 8 of {TOTAL_STEPS}</div>
            <h2 className="wizard-heading">What's your <span className="gradient-text">budget?</span></h2>
            <p className="wizard-subheading">Total campaign spend</p>
            <div className="budget-grid">
              {BUDGETS.map((b) => (
                <div key={b.value} className={`budget-card${d.budget === b.value ? " selected" : ""}`}
                  onClick={() => setD((p) => ({ ...p, budget: b.value }))}>
                  <div className="budget-amount">{b.label}</div>
                  <div className="budget-desc">{b.desc}</div>
                </div>
              ))}
            </div>
            {d.budget === "custom" && (
              <input className="dark-input" placeholder="Enter budget (e.g. £750,000)"
                value={d.budgetCustom}
                onChange={(e) => setD((p) => ({ ...p, budgetCustom: e.target.value }))} />
            )}
          </>
        );

      case 8: {
        const reviewGoal    = d.goal === "custom" ? d.goalCustom : GOALS.find((g) => g.id === d.goal)?.label ?? "";
        const reviewProduct = d.product === "custom" ? d.productCustom : d.product;
        const reviewTruth   = d.fanTruth === "custom" ? d.fanTruthCustom : d.fanTruth;
        const reviewAud     = [...d.audienceAge, ...d.audienceInterests, ...d.audienceRegions];
        const reviewKpis    = d.kpis.map((k) => KPI_OPTIONS.find((o) => o.id === k)?.label ?? k);
        const reviewBudget  = d.budget === "custom" ? `£${d.budgetCustom}` : d.budget;
        return (
          <>
            <div className="wizard-step-label">Review</div>
            <h2 className="wizard-heading">Ready to <span className="gradient-text">launch?</span></h2>
            <p className="wizard-subheading">
              {d.mode === "adapt"
                ? "Name your campaign — you'll upload existing assets on the next step"
                : "Name your campaign then send it to the agents"}
            </p>
            <input className="dark-input" placeholder="Campaign name (e.g. Summer Awareness 2026)"
              value={d.campaignName}
              onChange={(e) => setD((p) => ({ ...p, campaignName: e.target.value }))}
              style={{ marginBottom: 4, fontSize: 16 }} />
            {d.campaignName.trim().length < 3 && (
              <p style={{ fontSize: 12, color: "#f59e0b", marginBottom: 16, marginTop: 0 }}>
                ⚠ Campaign name must be at least 3 characters
              </p>
            )}
            <div className="review-grid">
              <div className="review-item">
                <div className="review-item-label">Mode</div>
                <div className="review-item-value">{d.mode === "adapt" ? "Adapt Existing" : "New Campaign"}</div>
              </div>
              <div className="review-item review-item-full">
                <div className="review-item-label">Goal</div>
                <div className="review-item-value">{reviewGoal}</div>
              </div>
              <div className="review-item">
                <div className="review-item-label">Product</div>
                <div className="review-item-value">{reviewProduct}</div>
              </div>
              <div className="review-item">
                <div className="review-item-label">Budget</div>
                <div className="review-item-value">{reviewBudget}</div>
              </div>
              <div className="review-item review-item-full">
                <div className="review-item-label">Fan Truth</div>
                <div className="review-item-value" style={{ fontStyle: "italic", opacity: 0.8 }}>"{reviewTruth}"</div>
              </div>
              <div className="review-item">
                <div className="review-item-label">Channels</div>
                <div className="review-item-value">{d.channels.join(", ")}</div>
              </div>
              <div className="review-item">
                <div className="review-item-label">KPIs</div>
                <div className="review-item-value">{reviewKpis.join(", ")}</div>
              </div>
              <div className="review-item">
                <div className="review-item-label">Season</div>
                <div className="review-item-value">{d.season} · {d.momentType}</div>
              </div>
              {reviewAud.length > 0 && (
                <div className="review-item review-item-full">
                  <div className="review-item-label">Audience</div>
                  <div className="review-item-value">{reviewAud.join(", ")}</div>
                </div>
              )}
            </div>
          </>
        );
      }

      case 9:
        return (
          <>
            <div className="wizard-step-label">Step 9 of 9 · Adapt Mode</div>
            <h2 className="wizard-heading">Upload your <span className="gradient-text">existing assets</span></h2>
            <p className="wizard-subheading">Add images, videos, or copy files from your current campaign</p>
            <div
              style={{
                border: "2px dashed rgba(124,58,237,0.45)", borderRadius: 16, padding: "40px 24px",
                textAlign: "center" as const, cursor: "pointer", background: "rgba(124,58,237,0.06)",
                marginBottom: 16,
              }}
              onClick={() => document.getElementById("asset-upload-input")?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const files = Array.from(e.dataTransfer.files);
                const names = files.map(f => f.name);
                const urls  = files.map(f => URL.createObjectURL(f));
                setD((p) => ({
                  ...p,
                  uploadedFileNames: [...p.uploadedFileNames, ...names],
                  uploadedAssets:    [...p.uploadedAssets,    ...urls],
                }));
              }}>
              <div style={{ fontSize: 40, marginBottom: 8 }}>📁</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#7c3aed" }}>
                Click or drag files here
              </div>
              <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 4 }}>
                Images, videos, PDFs, copy docs — any format
              </div>
              <input id="asset-upload-input" type="file" multiple style={{ display: "none" }}
                onChange={(e) => {
                  const files = Array.from(e.target.files ?? []);
                  const names = files.map(f => f.name);
                  const urls  = files.map(f => URL.createObjectURL(f));
                  setD((p) => ({
                    ...p,
                    uploadedFileNames: [...p.uploadedFileNames, ...names],
                    uploadedAssets:    [...p.uploadedAssets,    ...urls],
                  }));
                }} />
            </div>
            {d.uploadedFileNames.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 6 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#7c3aed", letterSpacing: "0.08em",
                  textTransform: "uppercase" as const, marginBottom: 2 }}>
                  {d.uploadedFileNames.length} file{d.uploadedFileNames.length > 1 ? "s" : ""} ready
                </div>
                {d.uploadedFileNames.map((name, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "8px 12px", borderRadius: 8, background: "#f3f0ff", border: "1px solid #ddd6fe" }}>
                    <span style={{ fontSize: 12, color: "#3730a3", fontWeight: 500 }}>📄 {name}</span>
                    <button
                      onClick={() => setD((p) => ({
                        ...p,
                        uploadedFileNames: p.uploadedFileNames.filter((_, j) => j !== i),
                        uploadedAssets:    p.uploadedAssets.filter((_, j) => j !== i),
                      }))}
                      style={{ background: "none", border: "none", cursor: "pointer",
                        color: "#9ca3af", fontSize: 14, padding: "0 4px" }}>
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            )}
          </>
        );

      default: return null;
    }
  };

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, position: "relative" as const }}>

      {/* Background video — all wizard steps until pipeline starts */}
      <>
        <BgVideoPlayer fixed brightness={0.55} saturate={0.9} />
        <div style={{
          position: "fixed" as const, inset: 0, zIndex: 1, pointerEvents: "none" as const,
          background: "var(--video-wash)",
        }} />
        <div style={{
          position: "fixed" as const, inset: 0, zIndex: 1, pointerEvents: "none" as const,
          background: "radial-gradient(ellipse 70% 60% at 50% 50%, rgba(124,58,237,0.06) 0%, transparent 70%)",
        }} />
      </>

      <div style={{ minHeight: "100%", display: "flex", alignItems: "center",
        justifyContent: "center", padding: "48px",
        position: "relative" as const, zIndex: 2 }}>
        <div style={{ maxWidth: 640, width: "100%" }}>
          <div key={step} className="step-content">{stepContent()}</div>
          <div className="wizard-nav">
            {step > 0
              ? <button className="wizard-back-btn" onClick={() => setStep((s) => s - 1)}>← Back</button>
              : <div />}
            {step < TOTAL_STEPS
              ? <button disabled={!canProceed()} onClick={() => setStep((s) => s + 1)} style={{
                  width: 48, height: 48, borderRadius: "50%", border: "none", cursor: canProceed() ? "pointer" : "not-allowed",
                  background: ORB_BG,
                  color: "white", fontSize: 20, display: "flex", alignItems: "center", justifyContent: "center",
                  boxShadow: canProceed() ? "0 4px 16px rgba(124,58,237,0.45)" : "none",
                  opacity: canProceed() ? 1 : 0.35, transition: "opacity 0.15s, box-shadow 0.15s",
                }}>→</button>
              : <button className="wizard-launch-btn" disabled={!canProceed()} onClick={handleFullLaunch}>
                  🚀 Generate AI Campaign
                </button>}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Agent visual themes ───────────────────────────────────────
const AGENT_VISUALS: Record<string, { g1: string; g2: string; blob1: string; blob2: string; title: string }> = {
  briefing: { g1: "#7c3aed", g2: "#4f46e5", blob1: "#a78bfa", blob2: "#818cf8", title: "Validating Brief" },
  culture:  { g1: "#0d9488", g2: "#0891b2", blob1: "#2dd4bf", blob2: "#22d3ee", title: "Cultural Research" },
  strategy: { g1: "#d97706", g2: "#ea580c", blob1: "#fbbf24", blob2: "#fb923c", title: "Creative Strategy" },
  copy:     { g1: "#0055A4", g2: "#0369a1", blob1: "#3b82f6", blob2: "#06b6d4", title: "Writing Copy" },
  kv:       { g1: "#be123c", g2: "#c2410c", blob1: "#fb7185", blob2: "#fb923c", title: "Key Visual" },
  channel:  { g1: "#4338ca", g2: "#0e7490", blob1: "#818cf8", blob2: "#22d3ee", title: "Channel Adaptation" },
};
const DEFAULT_VISUAL = { g1: "#1e293b", g2: "#334155", blob1: "#475569", blob2: "#64748b", title: "Starting…" };

// ── Agent content panels ──────────────────────────────────────
const CDP_SOURCE: Record<string, { label: string; from: string }> = {
  Rnorr:   { label: "CDP / Sephora",    from: "Kaggle · BigQuery" },
  Sunglow: { label: "CDP / Sephora",    from: "Kaggle · BigQuery" },
  Boozt:   { label: "CDP Profiles",     from: "Synthetic Segments" },
};
function getDataSources(brand?: string) {
  const cdp = CDP_SOURCE[brand ?? ""] ?? { label: "CDP Profiles", from: "Synthetic Segments" };
  return [
    { id: "brand",    icon: "📚", label: "Brand Guidelines",      from: "GCS Bucket",         delay: 0    },
    { id: "fantruth", icon: "💡", label: "Fan Truth Library",      from: "Vertex AI Search",   delay: 800  },
    { id: "history",  icon: "📈", label: "Historical Campaigns",   from: "BigQuery",           delay: 1600 },
    { id: "cdp",      icon: "👥", label: cdp.label,                from: cdp.from,             delay: 2400 },
  ];
}

function BriefingPanel({ m, liveMsg, brand }: { m?: Record<string,unknown>; liveMsg: string|null; brand?: string }) {
  const ft      = (m?.fan_truth ?? {}) as any;
  const aud     = (m?.audience  ?? {}) as any;
  const kpis    = (m?.kpis      ?? []) as any[];
  const hasData = !!ft?.overall;

  const score      = hasData ? (ft.overall ?? 0) : 0;
  const verdict    = hasData ? (ft.verdict ?? "—") : "—";
  const scoreColor = score >= 70 ? "#10b981" : score >= 55 ? "#f59e0b" : "#ef4444";
  const r = 28, circ = 2 * Math.PI * r, dash = circ * Math.min(score, 100) / 100;

  return (
    <div style={{ width: "100%" }}>

      {/* ── Data sources (always visible, loading → ✓) ── */}
      <div style={{ fontSize: 10, fontWeight: 700, color: "#7c3aed", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 8 }}>
        {hasData ? "Data Sources ✓" : "Querying Data Sources"}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 12 }}>
        {getDataSources(brand).map((src, idx) => (
          <div key={src.id} className="source-card" style={{ animationDelay: `${src.delay}ms`, padding: "8px 10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 30, height: 30, borderRadius: 8, flexShrink: 0,
                background: hasData ? "#f0fdf4" : "#f3f0ff",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>{src.icon}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#1a2332", whiteSpace: "nowrap" as const,
                  overflow: "hidden", textOverflow: "ellipsis" }}>{src.label}</div>
                <div style={{ fontSize: 9, color: "var(--text-tertiary)" }}>← {src.from}</div>
              </div>
              {hasData
                ? <span style={{ fontSize: 11, color: "#10b981", fontWeight: 800, flexShrink: 0 }}>✓</span>
                : <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
                    {[0,1,2].map(d => <span key={d} className="source-dot"
                      style={{ animationDelay: `${idx * 0.15 + d * 0.2}s` }} />)}
                  </div>}
            </div>
          </div>
        ))}
      </div>

      {/* ── Live message while loading ── */}
      {!hasData && liveMsg && (
        <div style={{ fontSize: 11, color: "#7c3aed", fontStyle: "italic", marginBottom: 8 }}>{liveMsg}</div>
      )}

      {/* ── Fan Truth gauge + KPIs + CDP — fade in when milestone arrives ── */}
      {hasData && (
        <div className="msg-fade">
          {/* Fan Truth */}
          <div style={{ borderRadius: 14, overflow: "hidden", marginBottom: 10,
            border: `1.5px solid ${scoreColor}30` }}>
            <div style={{ background: `linear-gradient(135deg, ${scoreColor}14, ${scoreColor}05)`,
              padding: "12px 14px", display: "flex", alignItems: "center", gap: 12 }}>
              <svg width="68" height="68" viewBox="0 0 68 68" style={{ flexShrink: 0 }}>
                <circle cx="34" cy="34" r={r} fill="none" stroke="#e2e8f0" strokeWidth="6"/>
                <circle cx="34" cy="34" r={r} fill="none" stroke={scoreColor} strokeWidth="6"
                  strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" transform="rotate(-90 34 34)"
                  style={{ transition: "stroke-dasharray 1.4s ease" }}/>
                <text x="34" y="31" textAnchor="middle" fill={scoreColor} fontSize="15" fontWeight="900">{score}</text>
                <text x="34" y="44" textAnchor="middle" fill="var(--text-muted)" fontSize="9">/100</text>
              </svg>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 22, fontWeight: 900, color: scoreColor }}>{score}/100</span>
                  {verdict === "PASS" && (
                    <span style={{ fontSize: 10, fontWeight: 800, padding: "2px 10px", borderRadius: 20,
                      background: "#dcfce7", color: "#065f46", border: "1px solid #86efac" }}>PASS</span>
                  )}
                </div>
                <div style={{ fontSize: 9, color: "var(--text-tertiary)", fontWeight: 700, letterSpacing: "0.08em",
                  textTransform: "uppercase" as const, marginBottom: 3 }}>Fan Truth Score</div>
                {ft.statement && (
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", fontStyle: "italic", lineHeight: 1.4 }}>
                    "{String(ft.statement).slice(0, 80)}{String(ft.statement).length > 80 ? "…" : ""}"
                  </div>
                )}
              </div>
            </div>
            {/* KPI strip */}
            {kpis.length > 0 && (
              <div style={{ display: "flex", borderTop: `1px solid ${scoreColor}18` }}>
                {kpis.slice(0, 3).map((k: any, i: number) => {
                  const displayFlag = k.flag === "UNREALISTIC" ? "AMBITIOUS" : (k.flag ?? "OK");
                  const fc = displayFlag === "OK" ? "#10b981" : "#f59e0b";
                  return (
                    <div key={i} style={{ flex: 1, padding: "7px 8px",
                      borderRight: i < 2 ? `1px solid ${scoreColor}15` : "none",
                      textAlign: "center" as const, background: `${fc}08` }}>
                      <div style={{ fontSize: 9, color: "var(--text-tertiary)", fontWeight: 600 }}>{k.metric}</div>
                      <div style={{ fontSize: 9, fontWeight: 800, color: fc, marginTop: 1 }}>{displayFlag}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* CDP audience */}
          {(aud.count || aud.income) && (
            <div style={{ padding: "9px 12px", borderRadius: 12, background: "#eff6ff", border: "1px solid #bfdbfe" }}>
              <div style={{ fontSize: 9, fontWeight: 700, color: "#0055A4", letterSpacing: "0.09em",
                textTransform: "uppercase" as const, marginBottom: 7 }}>
                Audience Intelligence · Kaggle CDP / Sephora
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" as const, alignItems: "center" }}>
                {aud.count && (
                  <div style={{ textAlign: "center" as const }}>
                    <div style={{ fontSize: 20, fontWeight: 900, color: "#0055A4", lineHeight: 1 }}>
                      {String(aud.count).replace(/\D.*/, "")}
                    </div>
                    <div style={{ fontSize: 9, color: "var(--text-tertiary)" }}>profiles matched</div>
                  </div>
                )}
                <div style={{ flex: 1 }}>
                  {aud.income && (
                    <div style={{ fontSize: 11, fontWeight: 600, color: "#1e40af", marginBottom: 2 }}>
                      💰 {aud.income}
                    </div>
                  )}
                  {aud.channels && (
                    <div style={{ fontSize: 11, color: "#3b82f6" }}>📡 {aud.channels}</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StrategyPanel({ m }: { m?: Record<string,unknown> }) {
  const hero     = String(m?.hero_message ?? "");
  const big      = String(m?.big_idea ?? "");
  const tagline  = String(m?.tagline ?? "");
  const fw       = String(m?.strategic_framework ?? "");
  const pillars  = (m?.messaging_pillars ?? []) as string[];
  const imgB64   = m?.hero_image_b64 ? String(m.hero_image_b64) : "";
  if (!hero) return (
    <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
      {["Building big idea", "Defining messaging pillars", "Crafting strategy"].map((step, i) => (
        <div key={i} className="source-card" style={{ animationDelay: `${i * 350}ms`, padding: "10px 14px" }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{step}</div>
          <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
            {[0,1,2].map(d => <span key={d} className="source-dot" style={{ animationDelay: `${d * 0.2}s` }} />)}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div style={{ width: "100%", borderRadius: 18, overflow: "hidden", border: "1px solid #fde68a",
      boxShadow: "0 8px 32px rgba(217,119,6,0.15)" }}>
      {/* Hero visual — brand image OR gradient */}
      <div style={{ position: "relative" as const, minHeight: 160, overflow: "hidden" }}>
        {imgB64 ? (
          <img src={`data:image/jpeg;base64,${imgB64}`} alt="brand asset"
            style={{ width: "100%", height: 180, objectFit: "cover", display: "block" }} />
        ) : (
          <div style={{ height: 160, background: "linear-gradient(135deg, #d97706 0%, #ea580c 100%)", position: "relative" as const }}>
            <div style={{ position: "absolute" as const, top: -40, right: -40, width: 160, height: 160,
              borderRadius: "50%", background: "rgba(255,255,255,0.08)" }} />
            <div style={{ position: "absolute" as const, bottom: -30, left: -30, width: 100, height: 100,
              borderRadius: "50%", background: "#f1f5f9" }} />
          </div>
        )}
        {/* Hero message overlay */}
        <div style={{ position: "absolute" as const, inset: 0,
          background: imgB64 ? "linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.2) 60%, transparent 100%)" : "none",
          display: "flex", flexDirection: "column" as const, justifyContent: "flex-end", padding: "16px 18px" }}>
          <div style={{ fontSize: 9, fontWeight: 700, color: imgB64 ? "rgba(255,255,255,0.7)" : "rgba(255,255,255,0.65)",
            letterSpacing: "0.14em", textTransform: "uppercase" as const, marginBottom: 4 }}>
            {big || "Campaign Concept"}
          </div>
          <div style={{ fontSize: imgB64 ? 18 : 22, fontWeight: 900,
            color: "white", lineHeight: 1.25, textShadow: "0 2px 8px rgba(0,0,0,0.3)" }}>
            "{hero}"
          </div>
          {tagline && <div style={{ fontSize: 11, color: "rgba(255,255,255,0.8)", marginTop: 4, fontStyle: "italic" }}>{tagline}</div>}
        </div>
      </div>

      {/* Strategic framework */}
      {fw && (
        <div style={{ padding: "12px 16px", background: "#fffbeb" }}>
          <div style={{ fontSize: 9, fontWeight: 700, color: "#92400e", letterSpacing: "0.1em",
            textTransform: "uppercase" as const, marginBottom: 5 }}>Strategic Framework</div>
          <div style={{ fontSize: 12, color: "#78350f", lineHeight: 1.6 }}>
            {fw.slice(0, 220)}{fw.length > 220 ? "…" : ""}
          </div>
        </div>
      )}

      {/* Messaging pillars */}
      {pillars.length > 0 && (
        <div style={{ padding: "10px 14px", background: "#fff7ed", borderTop: "1px solid #fed7aa",
          display: "flex", flexWrap: "wrap" as const, gap: 5 }}>
          {pillars.slice(0, 3).map((p, i) => (
            <span key={i} style={{ fontSize: 10, padding: "3px 10px", borderRadius: 99,
              background: "#fef3c7", border: "1px solid #fde68a", color: "#92400e", fontWeight: 600 }}>
              {String(p).slice(0, 42)}{String(p).length > 42 ? "…" : ""}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function CopyPanel({ m }: { m?: Record<string,unknown> }) {
  if (!m?.short_headline) return (
    <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
      {["Writing headlines", "Crafting body copy", "Generating captions"].map((step, i) => (
        <div key={i} className="source-card" style={{ animationDelay: `${i * 350}ms`, padding: "10px 14px" }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{step}</div>
          <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
            {[0,1,2].map(d => <span key={d} className="source-dot" style={{ animationDelay: `${d * 0.2}s` }} />)}
          </div>
        </div>
      ))}
    </div>
  );
  return (
    <div style={{ width: "100%" }}>
      {/* Billboard mock */}
      <div style={{ borderRadius: 14, overflow: "hidden", marginBottom: 10, border: "1px solid #bfdbfe" }}>
        <div style={{ background: "linear-gradient(135deg, #0055A4, #0369a1)", padding: "18px 20px", textAlign: "center" as const, position: "relative" as const }}>
          <div style={{ fontSize: 9, fontWeight: 700, color: "rgba(255,255,255,0.6)", letterSpacing: "0.14em", textTransform: "uppercase" as const, marginBottom: 6 }}>Billboard · Short</div>
          <div style={{ fontSize: 22, fontWeight: 900, color: "white", lineHeight: 1.2 }}>"{m.short_headline as string}"</div>
        </div>
        {!!m.cta && <div style={{ background: "#0055A4", padding: "8px", textAlign: "center" as const }}>
          <span style={{ display: "inline-block", padding: "5px 18px", borderRadius: 99, background: "white", color: "#0055A4", fontSize: 11, fontWeight: 800 }}>{String(m.cta)}</span>
        </div>}
      </div>

      {/* Medium + long */}
      {!!m.medium_headline && (
        <div style={{ marginBottom: 8, padding: "10px 12px", borderRadius: 10, background: "#f0f9ff", border: "1px solid #bae6fd" }}>
          <div style={{ fontSize: 9, fontWeight: 700, color: "#0369a1", textTransform: "uppercase" as const, letterSpacing: "0.1em", marginBottom: 4 }}>Digital · Medium</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>"{String(m.medium_headline)}"</div>
        </div>
      )}
      {!!m.body && (
        <div style={{ marginBottom: 8, padding: "10px 12px", borderRadius: 10, background: "var(--page-bg)", border: "1px solid #e2e8f0", fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6 }}>
          {String(m.body).slice(0, 140)}{String(m.body).length > 140 ? "…" : ""}
        </div>
      )}

      {/* Channel-specific copy — dynamic from whatever was selected */}
      {(() => {
        const channelCopy = m.channel_copy as Record<string, string> | null | undefined;
        if (!channelCopy || Object.keys(channelCopy).length === 0) return null;
        const COPY_CFG: Record<string, { icon: string; color: string; bg: string; border: string; label: string }> = {
          instagram_caption: { icon: "📸", color: "#7c3aed", bg: "#fdf4ff", border: "#e9d5ff", label: "Instagram" },
          tiktok_hook:       { icon: "🎵", color: "#be185d", bg: "#fff0f6", border: "#ffd6e7", label: "TikTok Hook" },
          youtube_script:    { icon: "▶️", color: "#dc2626", bg: "#fff1f2", border: "#fecdd3", label: "YouTube" },
          google_headline:   { icon: "🔍", color: "#1967d2", bg: "#eff6ff", border: "#bfdbfe", label: "Google Ads" },
          meta_caption:      { icon: "📘", color: "#1877f2", bg: "#eff6ff", border: "#dbeafe", label: "Meta Ads" },
          ooh_headline:      { icon: "🏙️", color: "#d97706", bg: "#fffbeb", border: "#fde68a", label: "OOH" },
          web_headline:      { icon: "🌐", color: "#059669", bg: "#f0fdf4", border: "#86efac", label: "Website" },
          email_subject:     { icon: "📧", color: "#0369a1", bg: "#f0f9ff", border: "#bae6fd", label: "Email" },
        };
        const entries = Object.entries(m.channel_copy as Record<string, string>);
        return (
          <div style={{ display: "grid", gridTemplateColumns: entries.length > 1 ? "1fr 1fr" : "1fr", gap: 8 }}>
            {entries.map(([key, val]) => {
              const cfg = COPY_CFG[key] ?? { icon: "📢", color: "var(--text-tertiary)", bg: "#eef0f4", border: "#e2e8f0", label: key };
              return (
                <div key={key} style={{ padding: "9px 11px", borderRadius: 10, background: cfg.bg, border: `1px solid ${cfg.border}` }}>
                  <div style={{ fontSize: 9, fontWeight: 700, color: cfg.color, textTransform: "uppercase" as const, letterSpacing: "0.1em", marginBottom: 4 }}>
                    {cfg.icon} {cfg.label}
                  </div>
                  <div style={{ fontSize: 11, color: cfg.color, lineHeight: 1.4 }}>
                    {val.slice(0, 90)}{val.length > 90 ? "…" : ""}
                  </div>
                </div>
              );
            })}
          </div>
        );
      })()}
    </div>
  );
}

const CHANNEL_CFG: Record<string, { icon: string; color: string; bg: string; border: string }> = {
  instagram: { icon: "📸", color: "#c026d3", bg: "#fdf4ff", border: "#e9d5ff" },
  tiktok:    { icon: "🎵", color: "var(--text-primary)", bg: "#eef0f4", border: "#e2e8f0" },
  google:    { icon: "🔍", color: "#1967d2", bg: "#eff6ff", border: "#bfdbfe" },
  email:     { icon: "📧", color: "#059669", bg: "#f0fdf4", border: "#86efac" },
  ooh:       { icon: "🪧", color: "#d97706", bg: "#fffbeb", border: "#fde68a" },
  youtube:   { icon: "▶️", color: "#dc2626", bg: "#fff1f2", border: "#fecdd3" },
};

function ChannelPanel({ m, liveMsg }: { m?: Record<string,unknown>; liveMsg: string|null }) {
  const hasData = m && Object.keys(m).length > 0;

  if (!hasData) return (
    <div style={{ width: "100%" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "#4338ca", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 12 }}>Adapting for Channels</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {["📸 Instagram", "🎵 TikTok", "🔍 Google Ads", "📧 Email"].map((ch, i) => (
          <div key={i} className="source-card" style={{ animationDelay: `${i * 250}ms`, padding: "12px 14px" }}>
            <div style={{ fontSize: 14, marginBottom: 6 }}>{ch}</div>
            <div style={{ display: "flex", gap: 4 }}>
              {[0,1,2].map(d => <span key={d} className="source-dot" style={{ animationDelay: `${d * 0.2}s` }} />)}
            </div>
          </div>
        ))}
      </div>
      {liveMsg && <div style={{ marginTop: 10, fontSize: 12, color: "#4338ca", fontStyle: "italic" }}>{liveMsg}</div>}
    </div>
  );

  return (
    <div style={{ width: "100%" }} className="msg-fade">
      <div style={{ fontSize: 10, fontWeight: 700, color: "#4338ca", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 12 }}>
        {Object.keys(m!).length} Channels Ready to Publish
      </div>
      <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
        {Object.entries(m!).map(([key, val]) => {
          const ch  = val as any;
          const cfg = CHANNEL_CFG[key] ?? { icon: "📢", color: "var(--text-tertiary)", bg: "#eef0f4", border: "#e2e8f0" };
          return (
            <div key={key} style={{ borderRadius: 12, overflow: "hidden", border: `1px solid ${cfg.border}` }}>
              <div style={{ padding: "7px 12px", background: cfg.bg, borderBottom: `1px solid ${cfg.border}`,
                display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 15 }}>{cfg.icon}</span>
                <span style={{ fontSize: 12, fontWeight: 800, color: cfg.color }}>{ch.platform}</span>
                <span style={{ marginLeft: "auto", fontSize: 9, padding: "2px 8px", borderRadius: 99,
                  background: cfg.border, color: cfg.color, fontWeight: 700 }}>{ch.format}</span>
                <span style={{ fontSize: 10, color: "#10b981", fontWeight: 700 }}>✓ Ready</span>
              </div>
              <div style={{ padding: "8px 12px", background: "white" }}>
                {(ch.headline || ch.hook) && (
                  <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>
                    "{String(ch.headline || ch.hook).slice(0, 60)}{String(ch.headline || ch.hook).length > 60 ? "…" : ""}"
                  </div>
                )}
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {ch.cta && <span style={{ fontSize: 10, padding: "2px 10px", borderRadius: 99,
                    background: cfg.color, color: "white", fontWeight: 700 }}>{ch.cta}</span>}
                  {ch.caption && <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{String(ch.caption).slice(0, 50)}…</span>}
                  {ch.subject && <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>Subject: {ch.subject}</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PerformancePanel({ m, liveMsg }: { m?: Record<string,unknown>; liveMsg: string|null }) {
  const hasData = m && (m.predicted_total_reach || m.headline_prediction);
  const ROSE = "#f43f5e";

  if (!hasData) return (
    <div style={{ width: "100%" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: ROSE, letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 12 }}>Forecasting Performance</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {["📊 Reach model", "💰 ROAS curves", "🎯 Confidence", "⏱ 48h watchlist"].map((item, i) => (
          <div key={i} className="source-card" style={{ animationDelay: `${i * 250}ms`, padding: "12px 14px" }}>
            <div style={{ fontSize: 13, marginBottom: 6 }}>{item}</div>
            <div style={{ display: "flex", gap: 4 }}>
              {[0,1,2].map(d => <span key={d} className="source-dot" style={{ animationDelay: `${d * 0.2}s` }} />)}
            </div>
          </div>
        ))}
      </div>
      {liveMsg && <div style={{ marginTop: 10, fontSize: 12, color: ROSE, fontStyle: "italic" }}>{liveMsg}</div>}
    </div>
  );

  const confColor = (c: string) => c === "HIGH" ? "#059669" : c === "MEDIUM" ? "#d97706" : "#dc2626";
  const conf = String(m?.overall_confidence ?? "—");

  return (
    <div style={{ width: "100%" }} className="msg-fade">
      <div style={{ fontSize: 10, fontWeight: 700, color: ROSE, letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 12 }}>Pre-Launch Forecast — Nexus</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 10 }}>
        {[
          { label: "Total Reach",   value: String(m?.predicted_total_reach ?? "—") },
          { label: "Blended ROAS",  value: String(m?.predicted_blended_roas ?? "—") },
        ].map(({ label, value }) => (
          <div key={label} style={{ background: "white", border: "1px solid #fecdd3", borderRadius: 10,
            padding: "10px 12px", textAlign: "center" as const }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: "#111827" }}>{value}</div>
            <div style={{ fontSize: 10, color: "#9ca3af", fontWeight: 600, marginTop: 2,
              textTransform: "uppercase" as const }}>{label}</div>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px",
        background: "white", border: "1px solid #fecdd3", borderRadius: 10 }}>
        <span style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>Confidence:</span>
        <span style={{ fontSize: 12, fontWeight: 800, color: confColor(conf) }}>{conf}</span>
      </div>
      {!!m?.headline_prediction && (
        <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-secondary)", fontStyle: "italic",
          lineHeight: 1.5, padding: "8px 12px", background: "#fff1f3", borderRadius: 10,
          border: "1px solid #fecdd3" }}>
          "{String(m!.headline_prediction).slice(0, 120)}{String(m!.headline_prediction).length > 120 ? "…" : ""}"
        </div>
      )}
    </div>
  );
}

function CulturePanel({ m }: { m?: Record<string,unknown> }) {
  const raw = String(m?.brief ?? "");
  if (!raw) return (
    <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
      {["Scanning cultural signals", "Analysing audience trends", "Mapping brand moments"].map((step, i) => (
        <div key={i} className="source-card" style={{ animationDelay: `${i * 350}ms`, padding: "10px 14px" }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{step}</div>
          <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
            {[0,1,2].map(d => <span key={d} className="source-dot" style={{ animationDelay: `${d * 0.2}s` }} />)}
          </div>
        </div>
      ))}
    </div>
  );
  // Strip markdown: **bold**, ## headers, leading bullets
  const clean = raw
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/^#+\s*/gm, "")
    .replace(/^[-*]\s*/gm, "")
    .trim();
  // Split on sentence boundaries, filter out short/empty fragments
  const sentences = clean
    .split(/(?<=[.!?])\s+/)
    .map(s => s.trim())
    .filter(s => s.length > 25)
    .slice(0, 4);
  if (sentences.length === 0) return null;
  return (
    <div style={{ width: "100%" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "#0d9488", letterSpacing: "0.09em",
        textTransform: "uppercase" as const, marginBottom: 10 }}>Cultural Intelligence Brief</div>
      {sentences.map((s, i) => (
        <div key={i} style={{ display: "flex", gap: 10, marginBottom: 10, padding: "10px 12px",
          borderRadius: 10, background: i === 0 ? "#f0fdfa" : "var(--page-bg)",
          border: `1px solid ${i === 0 ? "#99f6e4" : "#e2e8f0"}` }}>
          <span style={{ fontSize: 14, flexShrink: 0 }}>{["🌍", "💫", "🎯", "⚡"][i]}</span>
          <span style={{ fontSize: 12, color: "#1a2332", lineHeight: 1.5 }}>
            {s}{s.slice(-1).match(/[.!?]/) ? "" : "."}
          </span>
        </div>
      ))}
    </div>
  );
}

function KVPanel({ m, liveMsg, reelMilestone }: { m?: Record<string,unknown>; liveMsg: string|null; reelMilestone?: Record<string,unknown> }) {
  const [selectedImg, setSelectedImg] = useState(0);
  const brandLocks  = m?.brand_locks  ? String(m.brand_locks)  : "";
  const bigIdea     = m?.big_idea     ? String(m.big_idea)     : "";
  const imagePrompt = m?.image_prompt ? String(m.image_prompt) : "";
  const imageB64    = m?.image_b64    ? String(m.image_b64)    : "";
  const imagesB64   = m?.images_b64   ? (m.images_b64 as string[]) : imageB64 ? [imageB64] : [];
  const videoB64    = reelMilestone?.video_b64 ? String(reelMilestone.video_b64) : "";
  // GCS public URL fallback — used when SSE dropped before video_b64 arrived
  const videoUri    = reelMilestone?.video_uri ? String(reelMilestone.video_uri)
                        .replace(/^gs:\/\/([^/]+)\/(.+)$/, "https://storage.googleapis.com/$1/$2")
                      : "";
  const videoSrc    = videoB64 ? `data:video/mp4;base64,${videoB64}` : videoUri;

  const activeStep = imagesB64.length > 0 ? 4 : imagePrompt ? 3 : bigIdea ? 2 : brandLocks ? 1 : 0;
  const isGeneratingImg = imagesB64.length === 0 && (liveMsg?.toLowerCase().includes("imagen") || !!imagePrompt);

  const KV_STEPS = [
    {
      icon: "🔒",
      labelWaiting:  "Brand Locks",
      labelActive:   "Brand Locks Extracting...",
      labelDone:     "Brand Locks Extracted",
      content: brandLocks,
    },
    {
      icon: "💡",
      labelWaiting:  "Big Idea",
      labelActive:   "Big Idea Developing...",
      labelDone:     "Big Idea Developed",
      content: bigIdea,
    },
    {
      icon: "🖼️",
      labelWaiting:  "Image Prompt",
      labelActive:   "Image Prompt Crafting...",
      labelDone:     "Image Prompt Crafted",
      content: imagePrompt,
    },
    {
      icon: "✨",
      labelWaiting:  "Key Visual",
      labelActive:   "Key Visual Generating...",
      labelDone:     imagesB64.length > 1 ? `${imagesB64.length} Variations Generated` : "Key Visual Generated",
      content: imagesB64.length > 0 ? imagesB64[0] : "",
    },
  ];

  return (
    <div style={{ width: "100%" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "#7c3aed", letterSpacing: "0.09em",
        textTransform: "uppercase" as const, marginBottom: 12 }}>Image Generation Pipeline</div>

      {/* 2×2 card grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        {KV_STEPS.map((step, i) => {
          const isDone   = i < activeStep || (i === 3 && imagesB64.length > 0);
          const isActive = !isDone && (i === activeStep || (i === 3 && isGeneratingImg));
          const label    = isDone ? step.labelDone : isActive ? step.labelActive : step.labelWaiting;

          return (
            <div key={i} className={isDone || isActive ? "msg-fade" : ""} style={{
              borderRadius: 12,
              background: isDone ? "white" : isActive ? "#faf5ff" : "var(--page-bg)",
              border: `1.5px solid ${isDone ? "#ede9fe" : isActive ? "#ddd6fe" : "#e2e8f0"}`,
              padding: "14px 14px",
              display: "flex", flexDirection: "column" as const, gap: 8,
            }}>
              {/* Card header */}
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 20, flexShrink: 0 }}>{step.icon}</span>
                <span style={{ fontSize: 12, fontWeight: isDone || isActive ? 700 : 500, flex: 1,
                  color: isDone ? "#7c3aed" : isActive ? "#7c3aed" : "var(--text-muted)", lineHeight: 1.3 }}>
                  {label}
                </span>
                {isDone && (
                  <span style={{ color: "#7c3aed", fontWeight: 800, fontSize: 14, flexShrink: 0 }}>✓</span>
                )}
                {isActive && (
                  <div style={{ display: "flex", gap: 3, flexShrink: 0 }}>
                    {[0,1,2].map(d => (
                      <span key={d} className="source-dot"
                        style={{ animationDelay: `${d * 0.2}s`, background: "#7c3aed" }} />
                    ))}
                  </div>
                )}
              </div>

              {/* Card content — only shown when done */}
              {isDone && step.content && (
                <div style={{ marginTop: 2 }}>
                  {i === 3 && imagesB64.length > 0 ? (
                    <div>
                      <img src={`data:image/jpeg;base64,${imagesB64[selectedImg]}`} alt="Key visual"
                        style={{ width: "100%", borderRadius: 8, display: "block",
                          marginBottom: imagesB64.length > 1 ? 6 : 0 }} />
                      {imagesB64.length > 1 && (
                        <>
                          <div style={{ display: "flex", gap: 4 }}>
                            {imagesB64.map((img, idx) => (
                              <div key={idx} onClick={() => setSelectedImg(idx)}
                                style={{ flex: 1, cursor: "pointer", borderRadius: 4, overflow: "hidden",
                                  border: `2px solid ${idx === selectedImg ? "#7c3aed" : "transparent"}`,
                                  opacity: idx === selectedImg ? 1 : 0.55, transition: "all 0.2s" }}>
                                <img src={`data:image/jpeg;base64,${img}`} alt={`v${idx + 1}`}
                                  style={{ width: "100%", display: "block" }} />
                              </div>
                            ))}
                          </div>
                          <div style={{ fontSize: 10, color: "#7c3aed", fontWeight: 600, marginTop: 4,
                            textAlign: "center" as const }}>
                            Variation {selectedImg + 1} / {imagesB64.length} · click to select
                          </div>
                        </>
                      )}
                    </div>
                  ) : (
                    <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.6,
                      display: "-webkit-box", WebkitLineClamp: 3,
                      WebkitBoxOrient: "vertical" as any, overflow: "hidden" }}>
                      {step.content.replace(/\*\*/g, "").replace(/^#+\s*/gm, "").slice(0, 160)}
                      {step.content.length > 160 ? "…" : ""}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

    {/* Campaign Reel video player */}
    {videoSrc && (
      <div style={{ marginTop: 16, padding: "14px 16px", background: "#111827", borderRadius: 12 }}>
        <div style={{ fontSize: 11, fontWeight: 800, color: "#f59e0b", letterSpacing: "0.1em",
          textTransform: "uppercase" as const, marginBottom: 10 }}>🎬 Campaign Reel · 6s</div>
        <video controls autoPlay loop muted playsInline
          style={{ width: "100%", borderRadius: 8, display: "block" }}
          src={videoSrc} />
        <a href={videoSrc} download="campaign-reel.mp4"
          style={{ display: "inline-block", marginTop: 10, fontSize: 11, fontWeight: 700,
            color: "#f59e0b", textDecoration: "none" }}>
          ⬇ Download Reel
        </a>
      </div>
    )}
    </div>
  );
}

// ── Reel spotlight panel (used inside RunningView spotlight card) ─
function ReelSpotlightPanel({ m, liveMsg }: { m?: Record<string,unknown>; liveMsg: string|null }) {
  const videoB64 = m?.video_b64 ? String(m.video_b64) : "";
  const videoUri = m?.video_uri
    ? String(m.video_uri).replace(/^gs:\/\/([^/]+)\/(.+)$/, "https://storage.googleapis.com/$1/$2")
    : "";
  const videoSrc = videoB64 ? `data:video/mp4;base64,${videoB64}` : videoUri;
  if (videoSrc) {
    return (
      <div style={{ width: "100%" }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#ec4899", letterSpacing: "0.1em",
          textTransform: "uppercase" as const, marginBottom: 10 }}>🎬 Campaign Reel · 6s</div>
        <video controls autoPlay loop muted playsInline
          style={{ width: "100%", borderRadius: 12, display: "block",
            boxShadow: "0 4px 24px rgba(0,0,0,0.15)" }}
          src={videoSrc} />
        <a href={videoSrc} download="campaign-reel.mp4"
          style={{ display: "inline-block", marginTop: 10, fontSize: 12, fontWeight: 700,
            color: "#ec4899", textDecoration: "none" }}>
          ⬇ Download Reel
        </a>
      </div>
    );
  }
  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column" as const, gap: 8 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "#ec4899", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 4 }}>Generating Reel</div>
      {["Composing scene", "Rendering frames", "Encoding video"].map((step, i) => (
        <div key={i} className="source-card" style={{ animationDelay: `${i * 400}ms`, padding: "10px 14px" }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>{step}</div>
          <div style={{ display: "flex", gap: 4 }}>
            {[0,1,2].map(d => <span key={d} className="source-dot" style={{ animationDelay: `${d * 0.2}s` }} />)}
          </div>
        </div>
      ))}
      {liveMsg && <div style={{ fontSize: 11, color: "#ec4899", fontStyle: "italic", marginTop: 4 }}>{liveMsg}</div>}
    </div>
  );
}

// ── Running view (pipeline in progress) ─────────────────────
function RunningView({
  agentStatus,
  liveLog,
  milestones,
  compact = false,
  brand,
}: {
  agentStatus: Record<string, string>;
  liveLog: AgentEvent[];
  milestones: Record<string, Record<string, unknown>>;
  compact?: boolean;
  brand?: string;
}) {
  // Most recent running agent
  const activeKey = useMemo(() =>
    [...liveLog].reverse().find(e => e.status === "running")?.agent ?? null,
  [liveLog]);

  // Most recent done agent (to show completion card between agents)
  const lastDoneEvent = useMemo(() =>
    [...liveLog].reverse().find(e => e.status === "done"),
  [liveLog]);

  // Displayed key/mode — stays on "done" result for 10s before switching to next running agent
  const [displayKey,  setDisplayKey]  = useState<string | null>(null);
  const [displayMode, setDisplayMode] = useState<"running" | "done" | "idle">("idle");
  const dwellTimer    = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Ref mirrors displayMode so the effect always reads the current value (avoids stale closure)
  const displayModeRef = useRef<"running" | "done" | "idle">("idle");

  const setMode = useCallback((m: "running" | "done" | "idle") => {
    displayModeRef.current = m;
    setDisplayMode(m);
  }, []);

  useEffect(() => {
    if (activeKey) {
      if (displayModeRef.current === "done") {
        // Hold the current done result for 10s before switching to next running agent
        if (dwellTimer.current) clearTimeout(dwellTimer.current);
        dwellTimer.current = setTimeout(() => {
          setDisplayKey(activeKey);
          setMode("running");
        }, 10000);
      } else {
        if (dwellTimer.current) clearTimeout(dwellTimer.current);
        setDisplayKey(activeKey);
        setMode("running");
      }
    } else if (lastDoneEvent) {
      if (dwellTimer.current) clearTimeout(dwellTimer.current);
      setDisplayKey(lastDoneEvent.agent ?? null);
      setMode("done");
    } else {
      setDisplayKey(null);
      setMode("idle");
    }
    return () => { if (dwellTimer.current) clearTimeout(dwellTimer.current); };
  }, [activeKey, lastDoneEvent?.agent, setMode]);

  const liveMsg = useMemo(() => {
    if (!displayKey) return null;
    if (displayMode === "done") {
      return [...liveLog].reverse().find(e => e.agent === displayKey && e.status === "done")?.message ?? null;
    }
    return [...liveLog].reverse().find(e => e.agent === displayKey && e.status === "running")?.message ?? null;
  }, [liveLog, displayKey, displayMode]);

  const v = displayKey ? (AGENT_VISUALS[displayKey] ?? DEFAULT_VISUAL) : DEFAULT_VISUAL;
  const stage = displayKey ? HARNESS_STAGES.find(s => s.key === displayKey) : null;

  const doneCount = HARNESS_STAGES.filter(s => agentStatus[s.key] === "done").length;

  return (
    <div style={{ display: "flex", height: compact ? "100%" : "100vh", overflow: "hidden", fontFamily: "Inter,sans-serif" }}>

      {/* ── LEFT: step sidebar — hidden in compact/3-panel mode ── */}
      <div style={{ width: 340, flexShrink: 0, background: "var(--card-bg)", borderRight: "1px solid var(--card-border)",
        display: compact ? "none" : "flex", flexDirection: "column", padding: "28px 20px", overflowY: "auto" as const }}>

        {/* Logo */}
        <div style={{ marginBottom: 28 }}><AsterLogo /></div>

        {/* Progress bar */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.09em",
            textTransform: "uppercase" as const, marginBottom: 6 }}>Agents Activating</div>
          <div style={{ height: 5, background: "rgba(255,255,255,0.07)", borderRadius: 99, overflow: "hidden" }}>
            <div style={{ height: "100%", borderRadius: 99, transition: "width 0.8s ease",
              background: `linear-gradient(90deg, ${v.g1}, ${v.g2})`,
              boxShadow: `0 0 10px ${v.g1}80`,
              width: `${Math.max(4, (doneCount / HARNESS_STAGES.length) * 100)}%` }} />
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 5 }}>
            {doneCount} of {HARNESS_STAGES.length} complete · 2–5 min
          </div>
        </div>

        {/* Step list */}
        <div style={{ display: "flex", flexDirection: "column" as const, gap: 5, flex: 1 }}>
          {HARNESS_STAGES.map((s, i) => {
            const st    = agentStatus[s.key];
            const isOn  = s.key === activeKey;
            const isDone = st === "done";
            const vis   = AGENT_VISUALS[s.key] ?? DEFAULT_VISUAL;
            return (
              <div key={s.key} style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "10px 13px", borderRadius: 12,
                background: isOn ? `${vis.g1}22` : isDone ? "rgba(16,185,129,0.07)" : "rgba(255,255,255,0.03)",
                border: `1.5px solid ${isOn ? vis.g1 + "55" : isDone ? "rgba(16,185,129,0.22)" : "rgba(255,255,255,0.07)"}`,
                transition: "all 0.35s ease",
              }}>
                {/* Circle */}
                <div style={{
                  width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: isDone ? 13 : 11, fontWeight: 700,
                  background: isOn ? vis.g1 : isDone ? "#10b981" : "rgba(255,255,255,0.08)",
                  color: isOn || isDone ? "#fff" : "var(--text-secondary)",
                  boxShadow: isOn ? `0 0 0 4px ${vis.g1}28` : "none",
                  animation: isOn ? "step-ring 1.6s ease-in-out infinite" : "none",
                }}>
                  {isDone ? "✓" : isOn ? "⋯" : i + 1}
                </div>

                <div style={{ flex: 1, minWidth: 0, display: "flex", alignItems: "center", gap: 8 }}>
                  <img src={AGENT_AVATARS[i]} alt={s.label}
                    style={{ width: 22, height: 22, borderRadius: 6, objectFit: "cover", flexShrink: 0 }} />
                  <div style={{ fontSize: 12, fontWeight: 700,
                    color: isOn ? vis.g1 : isDone ? "#34d399" : "var(--text-tertiary)" }}>
                    {s.label}
                  </div>
                  <div style={{ fontSize: 11, marginTop: 1,
                    color: isOn ? vis.g1 + "cc" : isDone ? "#6ee7b780" : "var(--text-secondary)" }}>
                    {isOn ? "Running now" : isDone ? "Complete ✓" : "Waiting"}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── RIGHT: spotlight panel ────────────────────────────── */}
      <div style={{ flex: 1, position: "relative" as const, overflow: "auto",
        background: `linear-gradient(145deg, ${v.g1}12 0%, ${v.g2}08 50%, #f8fafc 100%)`,
        display: "flex", alignItems: "flex-start", justifyContent: "center",
        paddingTop: 48,
        transition: "background 1s ease" }}>

        {/* Animated blobs */}
        <div className="blob blob-1" style={{
          background: `radial-gradient(circle, ${v.blob1}42 0%, transparent 68%)`,
        }} />
        <div className="blob blob-2" style={{
          background: `radial-gradient(circle, ${v.blob2}32 0%, transparent 68%)`,
        }} />

        {/* Grid overlay */}
        <div style={{ position: "absolute" as const, inset: 0, opacity: 1,
          backgroundImage: "linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)",
          backgroundSize: "44px 44px" }} />

        {/* Spotlight card — re-animates on agent/mode change */}
        {displayMode !== "idle" ? (
          // Phase 1: agent running, no milestone data yet → large pulsing orb
          (displayMode === "running" && !milestones[displayKey ?? ""]) ? (
            <div key={`orb-${displayKey}`} style={{
              position: "relative" as const, zIndex: 2,
              display: "flex", flexDirection: "column" as const,
              alignItems: "center", justifyContent: "center", gap: 28,
            }}>
              <div style={{
                width: 90, height: 90, borderRadius: "50%",
                background: ORB_BG,
                boxShadow: "0 8px 32px rgba(200,40,200,0.32)",
                display: "flex", alignItems: "center", justifyContent: "center",
                animation: "icon-breathe 2.5s ease-in-out infinite",
              }}>
                <svg width={34} height={34} viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L13.8 10.2L22 12L13.8 13.8L12 22L10.2 13.8L2 12L10.2 10.2Z" fill="white" />
                </svg>
              </div>
              <div style={{ textAlign: "center" as const }}>
                <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.12em",
                  color: v.g1, textTransform: "uppercase" as const, marginBottom: 8 }}>
                  {stage?.label ?? "Agent"} · Running
                </div>
                <div style={{ fontSize: 20, fontWeight: 600, color: "var(--text-tertiary)", letterSpacing: "-0.01em" }}>
                  Generating ...
                </div>
              </div>
            </div>
          ) : (
          // Phase 2/3: milestone present or agent done → spotlight card with results
          <div key={displayKey ?? "idle"} className="spotlight-card" style={{
            position: "relative" as const, zIndex: 2,
            background: "rgba(255,255,255,0.82)",
            backdropFilter: "blur(28px)", WebkitBackdropFilter: "blur(28px)",
            border: `1.5px solid ${v.g1}28`,
            borderRadius: 24, padding: "28px 30px",
            width: displayKey === "kv" ? "min(680px, 92%)" : "min(580px, 92%)",
            maxHeight: "80vh", overflowY: "auto" as const,
            boxShadow: `0 20px 72px ${v.g1}18, 0 4px 20px rgba(0,0,0,0.07)`,
          }}>
            {/* Header row */}
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
              <div style={{ position: "relative" as const, flexShrink: 0 }}>
                {displayMode === "running" && <>
                  <div style={{ position: "absolute" as const, inset: -10, borderRadius: "50%",
                    border: `2px solid ${v.g1}25`, animation: "ring-spin 6s linear infinite" }} />
                  <div style={{ position: "absolute" as const, inset: -20, borderRadius: "50%",
                    border: `1.5px dashed ${v.g1}15`, animation: "ring-spin 10s linear infinite reverse" }} />
                </>}
                {displayMode === "done" && <div style={{ position: "absolute" as const, top: -4, right: -4, zIndex: 1,
                  width: 22, height: 22, borderRadius: "50%", background: "#10b981",
                  border: "2px solid white", display: "flex", alignItems: "center",
                  justifyContent: "center", fontSize: 12, color: "white", fontWeight: 800 }}>✓</div>}
                <div style={{ width: 72, height: 72, borderRadius: "50%", overflow: "hidden",
                  border: `2px solid ${v.g1}60`,
                  boxShadow: `0 0 36px ${v.g1}28`,
                  animation: displayMode === "running" ? "icon-breathe 2.5s ease-in-out infinite" : "none",
                }}>
                  {stage ? (
                    <img src={AGENT_AVATARS[HARNESS_STAGES.findIndex(s => s.key === displayKey)]}
                      alt={stage.label}
                      style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
                  ) : (
                    <div style={{ width: "100%", height: "100%", background: `${v.g1}22`,
                      display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28 }}>🤖</div>
                  )}
                </div>
              </div>
              <div>
                {displayMode === "done" && (
                  <div style={{ display: "inline-flex", alignItems: "center", gap: 5, marginBottom: 4,
                    padding: "3px 10px", borderRadius: 99,
                    background: "#dcfce7", border: "1px solid #86efac" }}>
                    <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.1em",
                      textTransform: "uppercase" as const, color: "#15803d" }}>
                      {stage?.label ?? "Agent"} · Complete ✓
                    </span>
                  </div>
                )}
                <div style={{ fontSize: 20, fontWeight: 800, color: "var(--text-primary)", lineHeight: 1.2 }}>
                  {v.title}{displayMode === "done" ? " ✓" : ""}
                </div>
              </div>
            </div>

            {/* Agent-specific content panel */}
            <div key={displayKey ?? "idle"} className="msg-fade">
              {displayKey === "briefing"  && <BriefingPanel m={milestones.briefing} liveMsg={liveMsg} brand={brand} />}
              {displayKey === "strategy"  && <StrategyPanel m={milestones.strategy} />}
              {displayKey === "copy"      && <CopyPanel m={milestones.copy} />}
              {displayKey === "culture"   && <CulturePanel m={milestones.culture} />}
              {displayKey === "kv"        && <KVPanel m={milestones.kv} liveMsg={liveMsg} reelMilestone={milestones.reel as Record<string,unknown> | undefined} />}
              {displayKey === "reel"      && <ReelSpotlightPanel m={milestones.reel} liveMsg={liveMsg} />}
              {displayKey === "channel"     && <ChannelPanel m={milestones.channel} liveMsg={liveMsg} />}
              {displayKey === "performance" && <PerformancePanel m={milestones.performance} liveMsg={liveMsg} />}
            </div>
          </div>
          )
        ) : (
          /* ── Idle: animated agent network ── */
          <div style={{ position: "relative" as const, zIndex: 1, display: "flex",
            flexDirection: "column" as const, alignItems: "center", justifyContent: "center",
            width: "100%", gap: 28 }}>

            {/* Network graph */}
            <div style={{ position: "relative" as const, width: 400, height: 400, flexShrink: 0 }}>

              {/* SVG: rings + connecting lines */}
              <svg viewBox="0 0 400 400" style={{ position: "absolute" as const, inset: 0, width: "100%", height: "100%", overflow: "visible" }}>
                {/* Pulsing rings */}
                {[60, 95, 140].map((r, ri) => (
                  <circle key={ri} cx="200" cy="200" r={r} fill="none"
                    stroke="rgba(124,58,237,0.18)" strokeWidth="1"
                    style={{ animation: `ring-out ${2.5 + ri * 0.8}s ${ri * 0.4}s ease-out infinite` }} />
                ))}
                {/* Connecting lines from center to each agent */}
                {HARNESS_STAGES.map((s, i) => {
                  const a = (i / HARNESS_STAGES.length) * 2 * Math.PI - Math.PI / 2;
                  const x2 = 200 + Math.cos(a) * 158;
                  const y2 = 200 + Math.sin(a) * 158;
                  const vis = AGENT_VISUALS[s.key] ?? DEFAULT_VISUAL;
                  return (
                    <line key={s.key} x1="200" y1="200" x2={x2} y2={y2}
                      stroke={vis.g1} strokeOpacity="0.25" strokeWidth="1.5"
                      strokeDasharray="6 5"
                      style={{ animation: `dash-move 2s ${i * 0.22}s linear infinite` }} />
                  );
                })}
              </svg>

              {/* Central hub */}
              <div style={{
                position: "absolute" as const, left: "50%", top: "50%",
                transform: "translate(-50%,-50%)",
                width: 72, height: 72, borderRadius: "50%", zIndex: 3,
                background: "linear-gradient(135deg, #0055A4, #4f46e5)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 32,
                boxShadow: "0 0 0 8px rgba(0,85,164,0.12), 0 0 40px rgba(0,85,164,0.35)",
                animation: "hub-beat 2s ease-in-out infinite",
              }}>🤖</div>

              {/* Agent nodes */}
              {HARNESS_STAGES.map((s, i) => {
                const a    = (i / HARNESS_STAGES.length) * 2 * Math.PI - Math.PI / 2;
                const r    = 158;
                const cx   = 200 + Math.cos(a) * r;
                const cy   = 200 + Math.sin(a) * r;
                const vis  = AGENT_VISUALS[s.key] ?? DEFAULT_VISUAL;
                // Label offset away from center
                const lx   = Math.cos(a) * 32;
                const ly   = Math.sin(a) * 32;
                return (
                  <div key={s.key} style={{
                    position: "absolute" as const,
                    left: cx, top: cy,
                    transform: "translate(-50%,-50%)",
                    zIndex: 2,
                    animation: `node-in 0.5s ${0.15 + i * 0.12}s cubic-bezier(0.22,1,0.36,1) both`,
                  }}>
                    {/* Node circle */}
                    <div style={{
                      width: 46, height: 46, borderRadius: "50%",
                      border: `2px solid ${vis.g1}60`, overflow: "hidden",
                      boxShadow: `0 0 16px ${vis.g1}28`,
                      animation: `node-glow 2.4s ${i * 0.35}s ease-in-out infinite`,
                    }}>
                      <img src={AGENT_AVATARS[i]} alt={s.label}
                        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
                    </div>
                    {/* Label */}
                    <div style={{
                      position: "absolute" as const,
                      left: `calc(50% + ${lx}px)`,
                      top: `calc(50% + ${ly}px)`,
                      transform: "translate(-50%,-50%)",
                      fontSize: 9, fontWeight: 700, color: vis.g1,
                      whiteSpace: "nowrap" as const,
                      background: "rgba(10,8,28,0.88)",
                      padding: "2px 6px", borderRadius: 6,
                      border: `1px solid ${vis.g1}35`,
                    }}>{s.label}</div>
                  </div>
                );
              })}
            </div>

            {/* Title */}
            <div style={{ textAlign: "center" as const }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)",
                letterSpacing: "-0.02em", marginBottom: 8 }}>
                Agents Activating...
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                {[0,1,2].map(d => (
                  <div key={d} style={{ width: 6, height: 6, borderRadius: "50%", background: "#7c3aed",
                    opacity: 0.7, animation: `wave-dot 1.4s ${d * 0.2}s ease-in-out infinite` }} />
                ))}
                <span style={{ fontSize: 13, color: "var(--text-secondary)", marginLeft: 4 }}>
                  {HARNESS_STAGES.length} agents connecting
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Distribute Campaign Panel ─────────────────────────────────
const API_BASE_PUB = import.meta.env.VITE_API_URL || "http://localhost:8000";

const PUBLISH_CHANNEL_CFG: Record<string, { icon: string; color: string; bg: string; border: string; desc: string; publishKey: string }> = {
  "Instagram":  { icon: "📸", color: "#c026d3", bg: "#fdf4ff", border: "#e9d5ff", desc: "Feed + Stories post",   publishKey: "instagram" },
  "TikTok":     { icon: "🎵", color: "var(--text-primary)", bg: "#f1f5f9", border: "#cbd5e1", desc: "Short-form video",       publishKey: "tiktok"    },
  "YouTube":    { icon: "▶️", color: "#dc2626", bg: "#fff1f2", border: "#fecdd3", desc: "Pre-roll ad",            publishKey: "youtube"   },
  "OOH":        { icon: "🏙️", color: "#d97706", bg: "#fffbeb", border: "#fde68a", desc: "Digital billboard",     publishKey: "ooh"       },
  "Google Ads": { icon: "🔍", color: "#1967d2", bg: "#eff6ff", border: "#bfdbfe", desc: "Responsive Search Ad",  publishKey: "google_ads"},
  "Meta Ads":   { icon: "📘", color: "#1877f2", bg: "#eff6ff", border: "#dbeafe", desc: "FB + Instagram Ad",     publishKey: "meta_ads"  },
  "Website":    { icon: "🌐", color: "#059669", bg: "#f0fdf4", border: "#86efac", desc: "Opens brand website",   publishKey: "landing_page"},
  "Email":      { icon: "📧", color: "#0369a1", bg: "#f0f9ff", border: "#bae6fd", desc: "Branded email blast",   publishKey: "email"     },
};

function DistributePanel({ output, campaignId, selectedImageB64 }: {
  output: Record<string, unknown> | null; campaignId: string | null; selectedImageB64?: string;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [email,    setEmail]    = useState("d.hendon17@gmail.com");
  const [loading,  setLoading]  = useState(false);
  const [published, setPublished] = useState(false);
  const [results,  setResults]  = useState<Record<string, any> | null>(null);
  const [error,    setError]    = useState("");

  // ── Email preview modal state ──────────────────────────────────────────
  const [showEmailPreview, setShowEmailPreview] = useState(false);
  const [previewSubject,   setPreviewSubject]   = useState("");
  const [previewHeadline,  setPreviewHeadline]  = useState("");
  const [previewBody,      setPreviewBody]      = useState("");
  const [landingUrl, setLandingUrl] = useState<string>(() => {
    // Restore persisted landing URL for this campaign on mount
    return campaignId ? localStorage.getItem(`landing_url_${campaignId}`) ?? "" : "";
  });

  const cp       = (output as any)?.creative_pipeline;
  const strategy = (output as any)?.creative_strategy;
  const copy     = (output as any)?.campaign_copy;
  const brief    = (output as any)?.machine_brief ?? output as any;
  const brandFromId = campaignId ? campaignId.replace(/^campaign-/, "").split("-")[0].replace(/^(.)/, (c: string) => c.toUpperCase()) : "";
  const brand    = String((output as any)?.brand ?? brandFromId ?? "");

  // Channels from brief — try multiple locations in the output tree
  const _rawCh = brief?.channels
    ?? (output as any)?.channels
    ?? (brief as any)?.structured_brief?.channels;
  const wizardChannels: string[] = Array.isArray(_rawCh)
    ? _rawCh
    : typeof _rawCh === "string"
      ? (() => { try { const p = JSON.parse(_rawCh); return Array.isArray(p) ? p : [_rawCh]; } catch { return []; } })()
      : [];
  // Always show all channels — fall back to full list if brief data is absent
  const displayChannels: string[] = wizardChannels.length > 0
    ? wizardChannels
    : Object.keys(PUBLISH_CHANNEL_CFG);

  const toggle = (key: string) => setSelected(s => { const n = new Set(s); n.has(key) ? n.delete(key) : n.add(key); return n; });

  const openEmailPreview = () => {
    setPreviewSubject((copy as any)?.channel_copy?.email_subject ?? copy?.short?.headline ?? strategy?.hero_message ?? "");
    setPreviewHeadline(copy?.short?.headline ?? copy?.medium?.headline ?? strategy?.hero_message ?? "");
    setPreviewBody(copy?.long?.body ?? copy?.medium?.headline ?? "");
    setShowEmailPreview(true);
  };

  const handlePublish = useCallback(async () => {
    if (selected.size === 0) return;
    if (!campaignId) { setError("No campaign ID"); return; }
    setLoading(true); setError(""); setResults(null);
    try {
      const res = await fetch(`${API_BASE_PUB}/publish/${campaignId}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand,
          hero_message:    strategy?.hero_message ?? "",
          // Use preview-edited values when email channel is selected so the
          // user's edits from the preview modal are included in the send
          short_headline:  (selected.has("email") && previewHeadline) ? previewHeadline : (copy?.short?.headline  ?? ""),
          medium_headline: copy?.medium?.headline ?? "",
          body:            (selected.has("email") && previewBody)     ? previewBody     : (copy?.long?.body       ?? ""),
          cta:             copy?.cta              ?? "",
          tagline:         strategy?.tagline      ?? "",
          email_subject:   (selected.has("email") && previewSubject)  ? previewSubject  : ((copy as any)?.channel_copy?.email_subject ?? copy?.short?.headline ?? ""),
          // Product name for email footer / product spotlight
          product_name:    String((output as any)?.product_name ?? brief?.structured_brief?.product ?? ""),
          // KV image — use explicitly selected variation first
          image_b64:       selectedImageB64 ?? cp?.images_b64?.[0] ?? cp?.image_b64 ?? "",
          to_email:        selected.has("email") ? email : "",
          channels:        Array.from(selected),
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? "Publish failed");
      setResults(json.results); setPublished(true);
      // Persist landing page URL so it survives navigation / page reload
      const _lpResult = json.results?.landing_page;
      if (_lpResult?.url && campaignId) {
        const _fullUrl = `${API_BASE_PUB}${_lpResult.url}`;
        localStorage.setItem(`landing_url_${campaignId}`, _fullUrl);
        setLandingUrl(_fullUrl);
      }
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [campaignId, brand, strategy, copy, cp, email, selected, selectedImageB64]);

  if (!strategy && !cp?.culture_brief) return null;

  const publishedCount = results ? Object.values(results).filter((r: any) => r.status !== "skipped" && r.status !== "error").length : 0;

  return (
    <div style={{ borderRadius: 20, overflow: "hidden", border: "1px solid rgba(124,58,237,0.22)",
      boxShadow: "0 4px 32px rgba(124,58,237,0.15)", backdropFilter: "blur(8px)" }}>
      {/* Dark header */}
      <div style={{ background: "var(--page-bg)",
        padding: "32px 36px 28px", position: "relative", overflow: "hidden",
        borderBottom: "1px solid rgba(124,58,237,0.18)" }}>
        {/* Decorative orb shapes */}
        <div style={{ position: "absolute", top: -50, right: -50, width: 200, height: 200,
          borderRadius: "50%", background: "rgba(124,58,237,0.18)", pointerEvents: "none" as const }} />
        <div style={{ position: "absolute", bottom: -30, left: -30, width: 140, height: 140,
          borderRadius: "50%", background: "rgba(99,102,241,0.12)", pointerEvents: "none" as const }} />

        <div style={{ position: "relative", zIndex: 1 }}>
          <div style={{ fontSize: 10, fontWeight: 800, color: "#a78bfa", letterSpacing: "0.18em",
            textTransform: "uppercase" as const, marginBottom: 8 }}>
            Final Step
          </div>
          <div style={{ fontSize: 26, fontWeight: 900, color: "var(--text-primary)", lineHeight: 1.2, marginBottom: 6 }}>
            {published ? `✅ Live on ${publishedCount} channel${publishedCount !== 1 ? "s" : ""}` : "🚀 Launch Campaign"}
          </div>
          <div style={{ fontSize: 13, color: "var(--text-tertiary)", marginBottom: published ? 8 : 24 }}>
            {published ? "Your campaign is now live. Track performance in your dashboards." : `Select channels to activate — ${displayChannels.length} available`}
          </div>

          {/* Re-publish button */}
          {published && (
            <button onClick={() => { setPublished(false); setResults(null); setSelected(new Set()); }}
              style={{ background: "none", border: "1.5px solid rgba(167,139,250,0.40)", color: "#a78bfa",
                borderRadius: 99, padding: "6px 16px", fontSize: 12, fontWeight: 700,
                cursor: "pointer", marginBottom: 16 }}>
              + Publish to more channels
            </button>
          )}

          {/* Channel selection chips */}
          {!published && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" as const }}>
              {displayChannels.map(ch => {
                const cfg = PUBLISH_CHANNEL_CFG[ch];
                if (!cfg) return null;
                const isOn = selected.has(cfg.publishKey);
                return (
                  <div key={ch} onClick={() => toggle(cfg.publishKey)}
                    style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 16px",
                      borderRadius: 12, cursor: "pointer", transition: "all 0.2s",
                      background: isOn ? "rgba(124,58,237,0.85)" : "rgba(255,255,255,0.04)",
                      border: `1.5px solid ${isOn ? "#7c3aed" : "rgba(255,255,255,0.10)"}`,
                      boxShadow: isOn ? "0 0 0 3px rgba(124,58,237,0.20), 0 4px 16px rgba(124,58,237,0.25)" : "none" }}>
                    <span style={{ fontSize: 18 }}>{cfg.icon}</span>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: isOn ? "white" : "#cbd5e1" }}>{ch}</div>
                      <div style={{ fontSize: 9, color: isOn ? "rgba(255,255,255,0.65)" : "var(--text-secondary)" }}>{cfg.desc}</div>
                    </div>
                    <div style={{ width: 18, height: 18, borderRadius: "50%", marginLeft: 4, flexShrink: 0,
                      background: isOn ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.06)",
                      border: `2px solid ${isOn ? "rgba(255,255,255,0.5)" : "rgba(255,255,255,0.15)"}`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 10, color: isOn ? "white" : "var(--text-secondary)", fontWeight: 800 }}>
                      {isOn ? "✓" : ""}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── Email preview modal ─────────────────────────────────────────── */}
      {showEmailPreview && (
        <div style={{ position: "fixed" as const, inset: 0, zIndex: 1000,
          background: "rgba(0,0,0,0.55)", display: "flex", alignItems: "center",
          justifyContent: "center", padding: 24 }}
          onClick={e => { if (e.target === e.currentTarget) setShowEmailPreview(false); }}>
          <div style={{ width: "100%", maxWidth: 560, maxHeight: "90vh",
            borderRadius: 20, background: "var(--card-bg)", border: "1px solid var(--card-border)",
            boxShadow: "0 24px 60px rgba(0,0,0,0.35)", display: "flex", flexDirection: "column" }}>

            {/* Sticky header — always visible */}
            <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--card-border)",
              display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
              <div style={{ fontSize: 15, fontWeight: 800, color: "var(--text-primary)" }}>📧 Email Preview</div>
              <button onClick={() => setShowEmailPreview(false)}
                style={{ background: "none", border: "none", cursor: "pointer", fontSize: 20,
                  color: "var(--text-secondary)", lineHeight: 1, padding: 4 }}>✕</button>
            </div>
            <div style={{ padding: "14px 24px 0", flexShrink: 0 }}>
              <label style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
                textTransform: "uppercase" as const, color: "var(--text-secondary)", display: "block", marginBottom: 5 }}>
                Subject line
              </label>
              <input value={previewSubject} onChange={e => setPreviewSubject(e.target.value)}
                placeholder="Email subject…"
                style={{ width: "100%", padding: "9px 13px", borderRadius: 9,
                  border: "1.5px solid var(--card-border)", background: "var(--page-bg)",
                  color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit",
                  outline: "none", boxSizing: "border-box" as const }}
                onFocus={e => e.currentTarget.style.borderColor = "#7c3aed"}
                onBlur={e => e.currentTarget.style.borderColor = "var(--card-border)"} />
            </div>

            {/* Scrollable email body */}
            <div style={{ overflowY: "auto", flex: 1 }}>
            <div style={{ margin: "14px 24px", borderRadius: 12, overflow: "hidden",
              border: "1px solid var(--card-border)", background: "#ffffff" }}>

              {/* Hero image */}
              {(selectedImageB64 ?? (output as any)?.creative_pipeline?.image_b64) && (
                <img
                  src={`data:image/jpeg;base64,${selectedImageB64 ?? (output as any)?.creative_pipeline?.image_b64}`}
                  alt="Campaign visual"
                  style={{ width: "100%", maxHeight: 260, objectFit: "contain" as const, display: "block", background: "#f8fafc" }} />
              )}

              <div style={{ padding: "20px 24px", fontFamily: "Georgia, serif" }}>
                {/* Editable headline */}
                <label style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em",
                  textTransform: "uppercase" as const, color: "#888", display: "block", marginBottom: 4,
                  fontFamily: "system-ui, sans-serif" }}>Headline</label>
                <textarea value={previewHeadline} onChange={e => setPreviewHeadline(e.target.value)}
                  rows={2}
                  style={{ width: "100%", fontSize: 22, fontWeight: 700, color: "#0f172a",
                    fontFamily: "Georgia, serif", border: "1.5px dashed #d0d0e0", borderRadius: 8,
                    background: "#fafafa", padding: "8px 10px", resize: "none" as const,
                    outline: "none", lineHeight: 1.3, boxSizing: "border-box" as const,
                    marginBottom: 12, transition: "border-color 0.15s" }}
                  onFocus={e => e.currentTarget.style.borderColor = "#7c3aed"}
                  onBlur={e => e.currentTarget.style.borderColor = "#d0d0e0"} />

                {/* Editable body copy */}
                <label style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em",
                  textTransform: "uppercase" as const, color: "#888", display: "block", marginBottom: 4,
                  fontFamily: "system-ui, sans-serif" }}>Body copy</label>
                <textarea value={previewBody} onChange={e => setPreviewBody(e.target.value)}
                  rows={4}
                  style={{ width: "100%", fontSize: 14, color: "#374151", lineHeight: 1.7,
                    fontFamily: "Georgia, serif", border: "1.5px dashed #d0d0e0", borderRadius: 8,
                    background: "#fafafa", padding: "8px 10px", resize: "none" as const,
                    outline: "none", boxSizing: "border-box" as const,
                    marginBottom: 16, transition: "border-color 0.15s" }}
                  onFocus={e => e.currentTarget.style.borderColor = "#7c3aed"}
                  onBlur={e => e.currentTarget.style.borderColor = "#d0d0e0"} />

                {/* CTA button preview */}
                {(copy as any)?.cta && (
                  <div style={{ textAlign: "center" as const }}>
                    <div style={{ display: "inline-block", padding: "12px 28px",
                      background: "linear-gradient(135deg,#7c3aed,#6366f1)",
                      color: "white", borderRadius: 8, fontSize: 14, fontWeight: 700,
                      fontFamily: "system-ui, sans-serif" }}>
                      {(copy as any).cta}
                    </div>
                  </div>
                )}
              </div>
            </div>

            </div>{/* end scrollable body */}

            {/* Sticky footer — always visible */}
            <div style={{ padding: "14px 24px", borderTop: "1px solid var(--card-border)",
              display: "flex", gap: 10, alignItems: "center", flexShrink: 0 }}>
              <input type="email" placeholder="Recipient email address" value={email}
                onChange={e => setEmail(e.target.value)}
                style={{ flex: 1, padding: "9px 13px", borderRadius: 9,
                  border: "1.5px solid var(--card-border)", background: "var(--page-bg)",
                  color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit", outline: "none" }}
                onFocus={e => e.currentTarget.style.borderColor = "#7c3aed"}
                onBlur={e => e.currentTarget.style.borderColor = "var(--card-border)"} />
              <button disabled={!email.trim() || loading}
                onClick={() => { setShowEmailPreview(false); handlePublish(); }}
                style={{ padding: "9px 20px", borderRadius: 9, border: "none", fontWeight: 700,
                  fontSize: 13, whiteSpace: "nowrap" as const,
                  cursor: email.trim() ? "pointer" : "not-allowed",
                  background: email.trim() ? ORB_BG : "rgba(124,58,237,0.15)",
                  color: email.trim() ? "white" : "rgba(124,58,237,0.4)",
                  boxShadow: email.trim() ? "0 4px 16px rgba(124,58,237,0.3)" : "none" }}>
                {loading ? "Sending…" : "Send Email →"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Action bar */}
      {!published && (
        <div style={{ padding: "16px 36px", background: "var(--card-bg)", display: "flex",
          alignItems: "center", gap: 16, borderTop: "1px solid var(--card-border)" }}>
          {/* Selected image thumbnail */}
          {selectedImageB64 && (
            <div style={{ flexShrink: 0, position: "relative" as const }}>
              <img src={`data:image/jpeg;base64,${selectedImageB64}`} alt="Selected key visual"
                style={{ width: 48, height: 48, objectFit: "cover" as const, borderRadius: 8,
                  border: "2px solid rgba(124,58,237,0.35)", display: "block" }} />
              <div style={{ position: "absolute" as const, top: -4, right: -4, width: 15, height: 15,
                borderRadius: "50%", background: "#7c3aed", border: "2px solid #f8fafc",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 8, color: "white", fontWeight: 800, lineHeight: 1 }}>✓</div>
            </div>
          )}
          {selected.has("email") && !showEmailPreview && (
            <input type="email" placeholder="Recipient email address" value={email} onChange={e => setEmail(e.target.value)}
              style={{ flex: 1, padding: "10px 14px", borderRadius: 10, border: "1.5px solid rgba(124,58,237,0.30)",
                background: "var(--page-bg)", color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit", outline: "none" }} />
          )}
          {selected.size === 0 ? (
            <div style={{ flex: 1, fontSize: 13, color: "var(--text-secondary)", fontStyle: "italic" }}>
              Select channels above to enable launch
            </div>
          ) : (
            <div style={{ flex: 1, fontSize: 13, color: "#a78bfa", fontWeight: 500 }}>
              {selected.size} channel{selected.size > 1 ? "s" : ""} selected
            </div>
          )}
          {/* If email is the only channel selected, show "Preview Email" button */}
          {selected.size > 0 && selected.has("email") && selected.size === 1 ? (
            <button onClick={openEmailPreview} disabled={loading}
              style={{ padding: "12px 28px", borderRadius: 12, border: "none", cursor: "pointer",
                background: ORB_BG, color: "white", fontSize: 13, fontWeight: 800,
                letterSpacing: "0.02em", transition: "all 0.2s",
                boxShadow: "0 4px 20px rgba(124,58,237,0.40)" }}>
              👁 Preview & Edit Email
            </button>
          ) : (
            <button onClick={selected.has("email") && selected.size > 1
              ? () => { openEmailPreview(); }
              : handlePublish}
              disabled={loading || selected.size === 0}
              style={{ padding: "12px 28px", borderRadius: 12, border: "none",
                cursor: selected.size === 0 ? "not-allowed" : "pointer",
                background: selected.size === 0 ? "rgba(255,255,255,0.05)" : ORB_BG,
                color: selected.size === 0 ? "var(--text-secondary)" : "white",
                fontSize: 13, fontWeight: 800, letterSpacing: "0.02em", transition: "all 0.2s",
                boxShadow: selected.size > 0 ? "0 4px 20px rgba(124,58,237,0.40)" : "none" }}>
              {loading ? "Launching…" : selected.size === 0 ? "Select Channels" : `🚀 Launch to ${selected.size} Channel${selected.size > 1 ? "s" : ""}`}
            </button>
          )}
        </div>
      )}

      {/* Published results */}
      {/* Persistent landing page URL banner — always visible once created */}
      {landingUrl && (
        <div style={{ padding: "16px 40px", background: "rgba(16,185,129,0.08)", borderTop: "1.5px solid rgba(52,211,153,0.25)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 20 }}>🌐</span>
            <div>
              <div style={{ fontSize: 12, fontWeight: 800, color: "#34d399", letterSpacing: "0.08em", textTransform: "uppercase" }}>Landing Page Live</div>
              <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2, wordBreak: "break-all" }}>{landingUrl}</div>
            </div>
          </div>
          <a href={landingUrl} target="_blank" rel="noreferrer"
            style={{ background: "linear-gradient(135deg,#059669,#047857)", color: "white", padding: "10px 24px", borderRadius: 99, fontWeight: 700, fontSize: 13, whiteSpace: "nowrap", textDecoration: "none" }}>
            Open Website →
          </a>
        </div>
      )}

      {published && results && (
        <div style={{ padding: "24px 40px", background: "rgba(16,185,129,0.05)", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
          {Object.entries(results).map(([key, r]: [string, any]) => {
            const isDone = r.status !== "skipped" && r.status !== "error";
            return (
              <div key={key} style={{ padding: "14px 16px", borderRadius: 12,
                background: isDone ? "rgba(16,185,129,0.10)" : "rgba(255,255,255,0.03)",
                border: `1.5px solid ${isDone ? "rgba(52,211,153,0.30)" : "rgba(255,255,255,0.07)"}` }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: isDone ? "#34d399" : "var(--text-secondary)", marginBottom: 4 }}>
                  {isDone ? "✅" : "⏭"} {key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
                </div>
                {key === "email" && r.to && <div style={{ fontSize: 10, color: "var(--text-tertiary)" }}>Sent to {r.to}</div>}
                {r.ad_id && <div style={{ fontSize: 10, color: "var(--text-tertiary)" }}>ID: {r.ad_id}</div>}
              </div>
            );
          })}
        </div>
      )}

      {error && (
        <div style={{ padding: "12px 40px", background: "rgba(239,68,68,0.08)", fontSize: 12, color: "#fca5a5",
          borderTop: "1px solid rgba(239,68,68,0.20)" }}>{error}</div>
      )}
    </div>
  );
}
// ── Results view ─────────────────────────────────────────────

// Stage card — defined outside ResultsView so React reconciler sees a stable type
function StageCard({ step, label, color, children }: {
  step: number; label: string; color: string; children: React.ReactNode;
}) {
  return (
    <div style={{
      marginBottom: 24, borderRadius: 20, overflow: "hidden",
      border: `1px solid ${color}28`,
      boxShadow: `0 0 24px ${color}22, 0 4px 20px rgba(0,0,0,0.08)`,
      background: "var(--card-bg)",
    }}>
      <div style={{
        padding: "13px 22px",
        background: `linear-gradient(135deg, ${color}12 0%, ${color}04 100%)`,
        borderBottom: `1px solid ${color}18`,
        display: "flex", alignItems: "center", gap: 12,
      }}>
        <div style={{
          width: 26, height: 26, borderRadius: "50%",
          background: `linear-gradient(135deg, ${color}, ${color}aa)`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 11, fontWeight: 900, color: "white", flexShrink: 0,
          boxShadow: `0 2px 10px ${color}55`,
        }}>{step}</div>
        <span style={{
          fontSize: 10, fontWeight: 800, color: color,
          letterSpacing: "0.18em", textTransform: "uppercase" as const,
        }}>{label}</span>
        <div style={{ flex: 1 }} />
        <div style={{ width: 5, height: 5, borderRadius: "50%", background: color, opacity: 0.7 }} />
      </div>
      {children}
    </div>
  );
}

function ResultsView({ output, campaignId }: {
  output: Record<string, unknown> | null;
  campaignId: string | null;
}) {
  const [expanded,   setExpanded]   = useState(false);
  const [selectedKV, setSelectedKV] = useState(0);
  const [copyTab,    setCopyTab]    = useState<"short" | "medium" | "long" | "channels">("short");
  const [kvSaveState,   setKvSaveState]   = useState<"idle" | "saving" | "saved">("idle");
  const [reelSaveState, setReelSaveState] = useState<"idle" | "saving" | "saved">("idle");

  const brief    = output as any;
  const strategy = output?.creative_strategy as any;
  const copy     = output?.campaign_copy as any;
  const cp       = (output as any)?.creative_pipeline;
  const cdpLines = output?.audience_insights
    ? String(output.audience_insights).split("\n").filter((l: string) => l.trim()) : [];

  const imagesB64: string[] = cp?.images_b64 ?? (cp?.image_b64 ? [cp.image_b64] : []);
  const videoB64: string    = cp?.video_b64 ? String(cp.video_b64) : "";
  const videoUri: string    = cp?.video_uri
    ? String(cp.video_uri).replace(/^gs:\/\/([^/]+)\/(.+)$/, "https://storage.googleapis.com/$1/$2") : "";
  const videoSrc: string    = videoB64 ? `data:video/mp4;base64,${videoB64}` : videoUri;
  const adaptations = cp?.channel_adaptations as Record<string, { label: string; image_b64: string; ratio: string }> | undefined;
  const perfForecast = (output as any)?.performance_forecast as Record<string, unknown> | undefined;

  const resultHeadline = copy?.short?.headline ?? strategy?.hero_message ?? "";

  const handleSaveKV = async () => {
    setKvSaveState("saving");
    try {
      await saveToContentHub({
        kind: "kv", brand: brief?.brand ?? "", campaignName: brief?.campaign_name ?? "",
        campaignId: campaignId ?? "", headline: resultHeadline,
        assetDataUrl: `data:image/jpeg;base64,${imagesB64[selectedKV]}`,
      });
      setKvSaveState("saved");
      setTimeout(() => setKvSaveState("idle"), 2500);
    } catch (e) {
      console.error("content_hub_save_kv_failed", e);
      setKvSaveState("idle");
    }
  };

  const handleSaveReel = async () => {
    setReelSaveState("saving");
    try {
      await saveToContentHub({
        kind: "reel", brand: brief?.brand ?? "", campaignName: brief?.campaign_name ?? "",
        campaignId: campaignId ?? "", headline: resultHeadline,
        assetDataUrl: videoSrc,
      });
      setReelSaveState("saved");
      setTimeout(() => setReelSaveState("idle"), 2500);
    } catch (e) {
      console.error("content_hub_save_reel_failed", e);
      setReelSaveState("idle");
    }
  };

  const CHANNEL_ICONS: Record<string, string> = {
    instagram_feed: "📸", instagram_stories: "📱", tiktok: "🎵",
    youtube: "▶️", google_ads: "🔍", meta_ads: "📘", email: "📧", ooh: "🏙️", website: "🌐",
  };
  const COPY_CH: Record<string, { icon: string; label: string; color: string }> = {
    instagram_caption: { icon: "📸", label: "Instagram", color: "#c084fc" },
    tiktok_hook:       { icon: "🎵", label: "TikTok",    color: "#f472b6" },
    youtube_script:    { icon: "▶️", label: "YouTube",   color: "#f87171" },
    google_headline:   { icon: "🔍", label: "Google",    color: "#60a5fa" },
    meta_caption:      { icon: "📘", label: "Meta",      color: "#60a5fa" },
    ooh_headline:      { icon: "🏙️", label: "OOH",      color: "#fbbf24" },
    web_headline:      { icon: "🌐", label: "Website",   color: "#34d399" },
    email_subject:     { icon: "📧", label: "Email",     color: "#38bdf8" },
  };

  // Sequential step counter — increments only for present stages
  let stepN = 0;
  const S = () => ++stepN;

  return (
    <div style={{ flex: 1, overflowY: "auto", background: "var(--page-bg)" }}>

      {/* Sticky campaign banner */}
      {campaignId && (
        <div style={{
          padding: "10px 28px", borderBottom: "1px solid var(--card-border)",
          display: "flex", alignItems: "center", gap: 10,
          background: "var(--card-bg-translucent)", backdropFilter: "blur(16px)",
          position: "sticky", top: 0, zIndex: 20,
        }}>
          <span style={{
            fontSize: 11, fontWeight: 700, padding: "3px 12px", borderRadius: 99,
            background: "rgba(124,58,237,0.10)", border: "1px solid rgba(124,58,237,0.28)", color: "#7c3aed",
          }}>✦ Campaign Ready</span>
          <span style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>#{campaignId}</span>
        </div>
      )}

      <div style={{ maxWidth: 960, margin: "0 auto", padding: "36px 24px 24px" }}>

        {/* ── 1. Brief Validation ────────────────────────────────────────── */}
        {brief && (() => {
          const n = S();
          const score   = brief.fan_truth?.overall ?? 0;
          const verdict = brief.fan_truth?.verdict ?? "FAIL";
          const sc = score >= 75 ? "#10b981" : score >= 60 ? "#f59e0b" : "#ef4444";
          const r = 46; const circ = 2 * Math.PI * r; const dash = circ * Math.min(score, 100) / 100;
          return (
            <StageCard step={n} label="Brief Validation" color="#7c3aed">
              {/* Score + statement row */}
              <div style={{ display: "grid", gridTemplateColumns: "180px 1fr" }}>
                {/* Left: big ring */}
                <div style={{
                  display: "flex", flexDirection: "column" as const, alignItems: "center",
                  justifyContent: "center", gap: 10, padding: "28px 16px",
                  borderRight: "1px solid rgba(255,255,255,0.07)",
                  background: "rgba(124,58,237,0.05)",
                }}>
                  <svg width="110" height="110" viewBox="0 0 110 110">
                    <circle cx="55" cy="55" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
                    <circle cx="55" cy="55" r={r} fill="none" stroke={sc} strokeWidth="8"
                      strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
                      transform="rotate(-90 55 55)"
                      style={{ transition: "stroke-dasharray 1.2s cubic-bezier(0.4,0,0.2,1)", filter: `drop-shadow(0 0 7px ${sc}88)` }} />
                    <text x="55" y="50" textAnchor="middle" fill={sc} fontSize="22" fontWeight="800" fontFamily="Inter,sans-serif">{score}</text>
                    <text x="55" y="67" textAnchor="middle" fill="#334155" fontSize="11" fontFamily="Inter,sans-serif">/100</text>
                  </svg>
                  <div style={{ textAlign: "center" as const }}>
                    <div style={{ fontSize: 9, color: "#334155", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase" as const, marginBottom: 5 }}>Fan Truth</div>
                    {verdict === "PASS" && (
                      <span style={{
                        fontSize: 11, fontWeight: 800, padding: "3px 14px", borderRadius: 99,
                        background: "rgba(16,185,129,0.14)", color: "#10b981",
                        border: "1px solid rgba(16,185,129,0.3)",
                      }}>PASS</span>
                    )}
                  </div>
                </div>
                {/* Right: statement + KPIs */}
                <div style={{ padding: "22px 22px 18px" }}>
                  {brief.fan_truth?.statement && (
                    <div style={{
                      padding: "12px 16px", borderRadius: 12, marginBottom: 14,
                      background: "rgba(124,58,237,0.08)", border: "1px solid rgba(124,58,237,0.20)",
                      fontSize: 14, color: "#6d28d9", fontStyle: "italic", lineHeight: 1.6,
                    }}>"{brief.fan_truth.statement}"</div>
                  )}
                  {brief.kpis?.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column" as const, gap: 6 }}>
                      {brief.kpis.slice(0, 4).map((k: any, i: number) => {
                        const displayFlag = k.flag === "UNREALISTIC" ? "AMBITIOUS" : (k.flag ?? "OK");
                        const CF: Record<string, { bg: string; color: string; border: string; icon: string }> = {
                          OK:        { bg: "rgba(16,185,129,0.07)", color: "#10b981", border: "rgba(16,185,129,0.20)", icon: "✓" },
                          AMBITIOUS: { bg: "rgba(245,158,11,0.07)", color: "#f59e0b", border: "rgba(245,158,11,0.20)", icon: "↑" },
                        };
                        const c = CF[displayFlag] ?? CF.OK;
                        return (
                          <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 12px", borderRadius: 10, background: c.bg, border: `1px solid ${c.border}` }}>
                            <span style={{ fontSize: 13, fontWeight: 700, color: c.color, width: 18, textAlign: "center" as const }}>{c.icon}</span>
                            <span style={{ flex: 1, fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{k.metric}</span>
                            <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>— {k.target}</span>
                            <span style={{ fontSize: 10, fontWeight: 700, color: c.color, padding: "2px 8px", background: `${c.color}18`, borderRadius: 8 }}>{displayFlag}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
              {/* Validation notes */}
              {brief.validation_notes && (
                <div style={{ padding: "12px 22px", fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.7, borderTop: "1px solid rgba(15,23,42,0.06)", background: "rgba(15,23,42,0.04)" }}>
                  {brief.validation_notes}
                </div>
              )}
              {/* CDP strip */}
              {cdpLines.length > 0 && (() => {
                const g = (k: string) => { const l = cdpLines.find((x: string) => x.toLowerCase().includes(k)); return l ? l.split(":").slice(1).join(":").trim() : null; };
                const cnt    = cdpLines.find((l: string) => l.includes("profiles"))?.match(/(\d[\d,]+)\s+\w+\s+profiles/)?.[1] ?? null;
                const income = g("household income"); const chans = g("top channels");
                const crmIdx = cdpLines.findIndex((l: string) => l.includes("CRM notes"));
                const crm    = crmIdx >= 0 ? cdpLines.slice(crmIdx + 1).join(" ").slice(0, 160) : null;
                return (
                  <div style={{ padding: "14px 22px", background: "rgba(124,58,237,0.06)", borderTop: "1px solid rgba(124,58,237,0.14)" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                      <span style={{ fontSize: 10, fontWeight: 700, color: "#a78bfa", letterSpacing: "0.1em", textTransform: "uppercase" as const }}>👥 CDP Audience Intelligence</span>
                      <span style={{ fontSize: 9, padding: "2px 8px", borderRadius: 99, background: "rgba(124,58,237,0.18)", color: "#a78bfa", border: "1px solid rgba(124,58,237,0.28)" }}>KAGGLE CDP</span>
                    </div>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" as const }}>
                      {cnt && <div style={{ padding: "8px 14px", borderRadius: 10, background: "var(--card-bg)", border: "1px solid rgba(124,58,237,0.2)", textAlign: "center" as const }}>
                        <div style={{ fontSize: 18, fontWeight: 900, color: "#a78bfa" }}>{cnt}</div>
                        <div style={{ fontSize: 9, color: "var(--text-secondary)" }}>profiles</div>
                      </div>}
                      {income && <div style={{ flex: 1, padding: "8px 14px", borderRadius: 10, background: "var(--card-bg)", border: "1px solid rgba(124,58,237,0.2)" }}>
                        <div style={{ fontSize: 9, color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase" as const, marginBottom: 2 }}>Avg Income</div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: "#a78bfa" }}>{income}</div>
                      </div>}
                      {chans && <div style={{ flex: 2, padding: "8px 14px", borderRadius: 10, background: "var(--card-bg)", border: "1px solid rgba(124,58,237,0.2)" }}>
                        <div style={{ fontSize: 9, color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase" as const, marginBottom: 2 }}>Top Channels</div>
                        <div style={{ fontSize: 12, color: "#a78bfa" }}>{chans}</div>
                      </div>}
                    </div>
                    {crm && <div style={{ marginTop: 8, fontSize: 11, color: "var(--text-secondary)", fontStyle: "italic", lineHeight: 1.5 }}>"{crm}…"</div>}
                  </div>
                );
              })()}
            </StageCard>
          );
        })()}

        {/* ── 2. Creative Strategy ───────────────────────────────────────── */}
        {strategy?.hero_message && (() => {
          const n = S();
          return (
            <StageCard step={n} label="Creative Strategy" color="#6366f1">
              {/* Bold gradient hero */}
              <div style={{
                padding: "36px 32px", position: "relative" as const, overflow: "hidden",
                background: "linear-gradient(135deg, #312e81 0%, #3730a3 40%, #4338ca 70%, #4f46e5 100%)",
              }}>
                <div style={{ position: "absolute" as const, inset: 0, background: "radial-gradient(ellipse 90% 80% at 15% 50%, rgba(255,255,255,0.07) 0%, transparent 65%)", pointerEvents: "none" }} />
                <div style={{ position: "relative" as const }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "rgba(255,255,255,0.5)", letterSpacing: "0.18em", textTransform: "uppercase" as const, marginBottom: 10 }}>
                    {strategy.big_idea || "Campaign Concept"}
                  </div>
                  <div style={{ fontSize: 30, fontWeight: 900, color: "white", lineHeight: 1.18, letterSpacing: "-0.01em", marginBottom: 8 }}>
                    "{strategy.hero_message}"
                  </div>
                  {strategy.tagline && (
                    <div style={{ fontSize: 13, color: "rgba(255,255,255,0.65)", fontStyle: "italic" }}>{strategy.tagline}</div>
                  )}
                </div>
              </div>
              {strategy.strategic_framework && (
                <div style={{ padding: "16px 24px", fontSize: 13, color: "var(--text-tertiary)", lineHeight: 1.75, background: "rgba(99,102,241,0.05)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                  {strategy.strategic_framework.slice(0, 340)}{strategy.strategic_framework.length > 340 ? "…" : ""}
                </div>
              )}
              {strategy.messaging_pillars?.length > 0 && (
                <div style={{ padding: "14px 20px", display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
                  {strategy.messaging_pillars.slice(0, 4).map((p: string, i: number) => (
                    <span key={i} style={{ fontSize: 11, padding: "5px 16px", borderRadius: 99, background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.28)", color: "#a5b4fc", fontWeight: 600 }}>
                      {String(p).slice(0, 50)}
                    </span>
                  ))}
                </div>
              )}
            </StageCard>
          );
        })()}

        {/* ── 3. Campaign Copy ───────────────────────────────────────────── */}
        {copy?.short?.headline && (() => {
          const n = S();
          const hasMedium   = !!copy.medium?.headline;
          const hasLong     = !!copy.long?.body;
          const hasChannels = copy.channel_copy && Object.keys(copy.channel_copy as object).length > 0;
          return (
            <StageCard step={n} label="Campaign Copy" color="#a855f7">
              {/* Tab bar */}
              <div style={{ display: "flex", borderBottom: "1px solid var(--card-border)", background: "rgba(0,0,0,0.25)" }}>
                {([
                  { key: "short",    label: "Short"    },
                  ...(hasMedium   ? [{ key: "medium",   label: "Medium"   }] : []),
                  ...(hasLong     ? [{ key: "long",     label: "Long"     }] : []),
                  ...(hasChannels ? [{ key: "channels", label: "Channels" }] : []),
                ] as { key: typeof copyTab; label: string }[]).map(({ key, label }) => (
                  <button key={key} onClick={() => setCopyTab(key)} style={{
                    padding: "11px 22px", border: "none", cursor: "pointer", background: "transparent",
                    fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" as const,
                    color: copyTab === key ? "#7c3aed" : "var(--text-secondary)",
                    borderBottom: `2px solid ${copyTab === key ? "#a855f7" : "transparent"}`,
                    transition: "color 0.15s",
                  }}>{label}</button>
                ))}
              </div>
              <div style={{ padding: "24px" }}>
                {copyTab === "short" && (
                  <div>
                    <div style={{ padding: "28px 24px", borderRadius: 14, textAlign: "center" as const, marginBottom: 14, background: "linear-gradient(135deg, rgba(168,85,247,0.14), rgba(168,85,247,0.05))", border: "1px solid rgba(168,85,247,0.22)" }}>
                      <div style={{ fontSize: 10, color: "#c084fc", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase" as const, marginBottom: 10 }}>Short Headline</div>
                      <div style={{ fontSize: 28, fontWeight: 900, color: "var(--text-primary)", lineHeight: 1.2 }}>"{copy.short.headline}"</div>
                    </div>
                    {copy.cta && (
                      <div style={{ textAlign: "center" as const }}>
                        <span style={{ display: "inline-block", padding: "9px 28px", borderRadius: 99, background: "linear-gradient(135deg, #7c3aed, #a855f7)", color: "white", fontSize: 13, fontWeight: 800, letterSpacing: "0.04em", boxShadow: "0 4px 16px rgba(168,85,247,0.35)" }}>{copy.cta}</span>
                      </div>
                    )}
                  </div>
                )}
                {copyTab === "medium" && (
                  <div style={{ padding: "22px 24px", borderRadius: 14, background: "rgba(168,85,247,0.07)", border: "1px solid rgba(168,85,247,0.18)" }}>
                    <div style={{ fontSize: 10, color: "#c084fc", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase" as const, marginBottom: 10 }}>Medium Headline</div>
                    {copy.medium?.headline && <div style={{ fontSize: 20, fontWeight: 800, color: "var(--text-primary)", lineHeight: 1.3, marginBottom: 10 }}>"{copy.medium.headline}"</div>}
                    {copy.medium?.body && <div style={{ fontSize: 13, color: "var(--text-tertiary)", lineHeight: 1.7 }}>{copy.medium.body.slice(0, 220)}{copy.medium.body.length > 220 ? "…" : ""}</div>}
                  </div>
                )}
                {copyTab === "long" && (
                  <div style={{ padding: "22px 24px", borderRadius: 14, background: "rgba(168,85,247,0.07)", border: "1px solid rgba(168,85,247,0.18)" }}>
                    <div style={{ fontSize: 10, color: "#c084fc", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase" as const, marginBottom: 10 }}>Long Copy</div>
                    {copy.long?.headline && <div style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", marginBottom: 10 }}>"{copy.long.headline}"</div>}
                    {copy.long?.body && <div style={{ fontSize: 13, color: "var(--text-tertiary)", lineHeight: 1.75 }}>{copy.long.body.slice(0, 320)}{copy.long.body.length > 320 ? "…" : ""}</div>}
                  </div>
                )}
                {copyTab === "channels" && hasChannels && (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                    {Object.entries(copy.channel_copy as Record<string, string>).map(([key, val]) => {
                      const cfg = COPY_CH[key] ?? { icon: "📢", label: key, color: "var(--text-tertiary)" };
                      return (
                        <div key={key} style={{ padding: "12px 14px", borderRadius: 12, background: "var(--card-bg)", border: "1px solid var(--card-border)" }}>
                          <div style={{ fontSize: 9, fontWeight: 700, color: cfg.color, textTransform: "uppercase" as const, letterSpacing: "0.1em", marginBottom: 5 }}>{cfg.icon} {cfg.label}</div>
                          <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5 }}>{val.slice(0, 100)}{val.length > 100 ? "…" : ""}</div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </StageCard>
          );
        })()}

        {/* ── 4. Cultural Intelligence ───────────────────────────────────── */}
        {cp?.culture_brief && (() => {
          const n = S();
          const sentences = cp.culture_brief.replace(/\*\*([^*]+)\*\*/g, "$1").replace(/^#+\s*/gm, "").split(/(?<=[.!?])\s+/).filter((s: string) => s.length > 25).slice(0, 4);
          const icons  = ["🌍", "💫", "🎯", "⚡"];
          return (
            <StageCard step={n} label="Cultural Intelligence" color="#0d9488">
              <div style={{ padding: "20px 22px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {sentences.map((s: string, i: number) => (
                  <div key={i} style={{ padding: "14px 16px", borderRadius: 14, display: "flex", gap: 10, alignItems: "flex-start", background: i % 2 === 0 ? "rgba(13,148,136,0.09)" : "rgba(13,148,136,0.05)", border: "1px solid rgba(13,148,136,0.18)" }}>
                    <span style={{ fontSize: 18, flexShrink: 0, marginTop: 1 }}>{icons[i] ?? "✦"}</span>
                    <span style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6 }}>{s}</span>
                  </div>
                ))}
              </div>
            </StageCard>
          );
        })()}

        {/* ── 5. Key Visual ─────────────────────────────────────────────── */}
        {imagesB64.length > 0 && (() => {
          const n = S();
          return (
            <StageCard step={n} label={`Key Visual${imagesB64.length > 1 ? ` — ${imagesB64.length} Variations` : ""}`} color="#e11d48">
              {/* Full-bleed image */}
              <div>
                <img src={`data:image/jpeg;base64,${imagesB64[selectedKV]}`} alt="Key visual"
                  style={{ width: "100%", display: "block", maxHeight: 580, objectFit: "cover" }} />
                <div style={{ padding: "10px 16px", background: "rgba(15,23,42,0.04)", borderTop: "1px solid rgba(255,255,255,0.07)", display: "flex", justifyContent: "flex-end", gap: 8 }}>
                  <button onClick={handleSaveKV} disabled={kvSaveState === "saving"}
                    style={{ padding: "5px 14px", borderRadius: 99, background: kvSaveState === "saved" ? "rgba(16,185,129,0.15)" : "rgba(124,58,237,0.15)",
                      border: `1px solid ${kvSaveState === "saved" ? "rgba(16,185,129,0.35)" : "rgba(124,58,237,0.35)"}`,
                      color: kvSaveState === "saved" ? "#10b981" : "#7c3aed", fontSize: 11, fontWeight: 700,
                      cursor: kvSaveState === "saving" ? "default" : "pointer", fontFamily: "inherit" }}>
                    {kvSaveState === "saved" ? "✓ Saved" : kvSaveState === "saving" ? "Saving…" : "💾 Save to Content Hub"}
                  </button>
                  <a href={`data:image/jpeg;base64,${imagesB64[selectedKV]}`} download={`kv-${selectedKV + 1}.jpg`}
                    style={{ padding: "5px 14px", borderRadius: 99, background: "rgba(225,29,72,0.15)", border: "1px solid rgba(225,29,72,0.35)", color: "#f43f5e", fontSize: 11, fontWeight: 700, textDecoration: "none" }}>
                    ⬇ Download
                  </a>
                </div>
              </div>
              {imagesB64.length > 1 && (
                <div style={{ padding: "14px 18px", background: "rgba(15,23,42,0.04)", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "#f43f5e", letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 10 }}>Variations</div>
                  <div style={{ display: "flex", gap: 8 }}>
                    {imagesB64.map((img, idx) => (
                      <div key={idx} onClick={() => setSelectedKV(idx)} style={{ flex: 1, cursor: "pointer", borderRadius: 8, overflow: "hidden", border: `2px solid ${idx === selectedKV ? "#e11d48" : "rgba(255,255,255,0.1)"}`, opacity: idx === selectedKV ? 1 : 0.45, transition: "all 0.2s", boxShadow: idx === selectedKV ? "0 0 0 1px rgba(225,29,72,0.4), 0 4px 14px rgba(225,29,72,0.2)" : "none" }}>
                        <img src={`data:image/jpeg;base64,${img}`} alt={`V${idx + 1}`} style={{ width: "100%", display: "block" }} />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </StageCard>
          );
        })()}

        {/* ── 6. Campaign Reel ──────────────────────────────────────────── */}
        {videoSrc && (() => {
          const n = S();
          return (
            <StageCard step={n} label="Campaign Reel — Veo 3" color="#d97706">
              <div style={{ background: "#000" }}>
                <video controls autoPlay loop muted playsInline style={{ width: "100%", display: "block", maxHeight: 500 }} src={videoSrc} />
              </div>
              <div style={{ padding: "10px 18px", display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(15,23,42,0.04)", gap: 8 }}>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>6s · 16:9 · Veo 3</span>
                <div style={{ display: "flex", gap: 8 }}>
                  <button onClick={handleSaveReel} disabled={reelSaveState === "saving"}
                    style={{ padding: "4px 12px", borderRadius: 99, background: reelSaveState === "saved" ? "rgba(16,185,129,0.15)" : "rgba(124,58,237,0.15)",
                      border: `1px solid ${reelSaveState === "saved" ? "rgba(16,185,129,0.35)" : "rgba(124,58,237,0.35)"}`,
                      color: reelSaveState === "saved" ? "#10b981" : "#7c3aed", fontSize: 11, fontWeight: 700,
                      cursor: reelSaveState === "saving" ? "default" : "pointer", fontFamily: "inherit" }}>
                    {reelSaveState === "saved" ? "✓ Saved" : reelSaveState === "saving" ? "Saving…" : "💾 Save to Content Hub"}
                  </button>
                  <a href={videoSrc} download="campaign-reel.mp4" style={{ fontSize: 11, fontWeight: 700, color: "#fbbf24", textDecoration: "none" }}>⬇ Download mp4</a>
                </div>
              </div>
            </StageCard>
          );
        })()}

        {/* ── 7. Channel Adaptations ────────────────────────────────────── */}
        {adaptations && Object.keys(adaptations).length > 0 && (() => {
          const n = S();
          return (
            <StageCard step={n} label={`Channel Adaptations — ${Object.keys(adaptations).length} formats`} color="#3b82f6">
              <div style={{ padding: "16px", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(215px, 1fr))", gap: 10, alignItems: "start" }}>
                {Object.entries(adaptations).map(([key, val]) => (
                  <div key={key} style={{ borderRadius: 12, overflow: "hidden", border: "1px solid rgba(59,130,246,0.2)", background: "rgba(59,130,246,0.04)", alignSelf: "start" }}>
                    <div style={{ padding: "7px 12px", display: "flex", alignItems: "center", gap: 6, borderBottom: "1px solid rgba(59,130,246,0.14)" }}>
                      <span style={{ fontSize: 13 }}>{CHANNEL_ICONS[key] ?? "📺"}</span>
                      <span style={{ fontSize: 11, fontWeight: 700, color: "#60a5fa" }}>{val.label}</span>
                      <span style={{ marginLeft: "auto", fontSize: 9, color: "#334155", fontFamily: "monospace" }}>{val.ratio}</span>
                    </div>
                    <img src={`data:image/jpeg;base64,${val.image_b64}`} alt={val.label} style={{ width: "100%", display: "block" }} />
                  </div>
                ))}
              </div>
            </StageCard>
          );
        })()}

        {/* ── 8. Performance Forecast ───────────────────────────────────── */}
        {perfForecast && (() => {
          const n  = S();
          const pf = perfForecast as any;
          const ROSE        = "#fb7185";
          const ROSE_BORDER = "rgba(251,113,133,0.22)";
          const ROSE_LIGHT  = "rgba(251,113,133,0.06)";
          const cC = (c: string) => c === "HIGH" ? "#34d399" : c === "MEDIUM" ? "#fbbf24" : "#f87171";
          const cB = (c: string) => c === "HIGH" ? "rgba(52,211,153,0.12)" : c === "MEDIUM" ? "rgba(251,191,36,0.12)" : "rgba(248,113,113,0.12)";
          const cD = (c: string) => c === "HIGH" ? "rgba(52,211,153,0.28)" : c === "MEDIUM" ? "rgba(251,191,36,0.28)" : "rgba(248,113,113,0.28)";
          const channelForecasts: any[] = Array.isArray(pf.channel_forecasts) ? pf.channel_forecasts : [];
          const conf = String(pf.overall_confidence ?? "—");
          return (
            <StageCard step={n} label="Performance Forecast" color="#fb7185">
              {pf.headline_prediction && (
                <div style={{ padding: "20px 24px", background: ROSE_LIGHT, borderBottom: `1px solid ${ROSE_BORDER}` }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: ROSE, letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 6 }}>Forecast Headline</div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", fontStyle: "italic", lineHeight: 1.45 }}>"{pf.headline_prediction}"</div>
                </div>
              )}
              {/* 3 hero KPI tiles */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", borderBottom: `1px solid ${ROSE_BORDER}` }}>
                {[
                  { label: "Predicted Reach", value: pf.predicted_total_reach  ?? "—" },
                  { label: "Blended ROAS",    value: pf.predicted_blended_roas ?? "—" },
                  { label: "Confidence",      value: conf },
                ].map(({ label, value }, i) => (
                  <div key={label} style={{ padding: "22px 18px", textAlign: "center" as const, borderRight: i < 2 ? `1px solid ${ROSE_BORDER}` : "none", background: i === 2 ? cB(value) : "transparent" }}>
                    <div style={{ fontSize: 28, fontWeight: 900, letterSpacing: "-0.02em", color: label === "Confidence" ? cC(value) : "#111827" }}>{value}</div>
                    <div style={{ fontSize: 9, color: "#334155", fontWeight: 700, marginTop: 5, textTransform: "uppercase" as const, letterSpacing: "0.08em" }}>{label}</div>
                  </div>
                ))}
              </div>
              {channelForecasts.length > 0 && (
                <div style={{ padding: "16px 20px", borderBottom: `1px solid ${ROSE_BORDER}` }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: ROSE, letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 12 }}>Channel Forecasts</div>
                  <div style={{ display: "flex", flexDirection: "column" as const, gap: 6 }}>
                    {channelForecasts.map((cf: any, i: number) => (
                      <div key={i} style={{ display: "grid", gridTemplateColumns: "140px 1fr 1fr 1fr 1fr auto", alignItems: "center", gap: 10, padding: "10px 14px", background: ROSE_LIGHT, borderRadius: 10, border: `1px solid ${ROSE_BORDER}` }}>
                        <div style={{ fontWeight: 700, fontSize: 12, color: "var(--text-primary)" }}>{cf.channel}</div>
                        {[{ v: cf.predicted_reach, l: "Reach" }, { v: cf.predicted_ctr, l: "CTR" }, { v: cf.predicted_roas, l: "ROAS" }, { v: cf.predicted_engagement, l: "Eng." }].map(({ v, l }) => (
                          <div key={l} style={{ textAlign: "center" as const }}>
                            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{v ?? "—"}</div>
                            <div style={{ fontSize: 9, color: "#334155", fontWeight: 600, textTransform: "uppercase" as const }}>{l}</div>
                          </div>
                        ))}
                        <span style={{ fontSize: 10, fontWeight: 700, padding: "3px 9px", borderRadius: 99, background: cB(cf.confidence), color: cC(cf.confidence), border: `1px solid ${cD(cf.confidence)}`, textTransform: "uppercase" as const, whiteSpace: "nowrap" as const }}>{cf.confidence}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {(pf.top_risk || pf.top_opportunity) && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", borderBottom: `1px solid ${ROSE_BORDER}` }}>
                  {pf.top_risk && <div style={{ padding: "14px 18px", borderRight: `1px solid ${ROSE_BORDER}` }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#f87171", letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 6 }}>⚠ Top Risk</div>
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)", lineHeight: 1.6 }}>{pf.top_risk}</div>
                  </div>}
                  {pf.top_opportunity && <div style={{ padding: "14px 18px" }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#34d399", letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 6 }}>✦ Top Opportunity</div>
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)", lineHeight: 1.6 }}>{pf.top_opportunity}</div>
                  </div>}
                </div>
              )}
              {Array.isArray(pf.first_48h_watchlist) && pf.first_48h_watchlist.length > 0 && (
                <div style={{ padding: "14px 18px" }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: ROSE, letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 8 }}>First 48h Watchlist</div>
                  <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 6 }}>
                    {(pf.first_48h_watchlist as string[]).map((item: string, i: number) => (
                      <span key={i} style={{ fontSize: 11, padding: "4px 10px", borderRadius: 99, background: ROSE_LIGHT, border: `1px solid ${ROSE_BORDER}`, color: ROSE, fontWeight: 600 }}>⏱ {item}</span>
                    ))}
                  </div>
                </div>
              )}
            </StageCard>
          );
        })()}

        {/* ── Launch ────────────────────────────────────────────────────── */}
        <StageCard step={S()} label="Launch Campaign" color="#10b981">
          <DistributePanel output={output} campaignId={campaignId} selectedImageB64={imagesB64[selectedKV] ?? undefined} />
        </StageCard>

        {/* Raw JSON toggle */}
        {output && (
          <div style={{ marginTop: 8, padding: "12px 16px", borderRadius: 12, background: "rgba(255,255,255,0.03)", border: "1px solid var(--card-border)" }}>
            <button style={styles.expandBtn} onClick={() => setExpanded(e => !e)}>
              {expanded ? "▲ Hide" : "▼ Show"} full pipeline output (JSON)
            </button>
            {expanded && <pre style={styles.jsonPre}>{JSON.stringify(output, null, 2)}</pre>}
          </div>
        )}
      </div>
      <div style={{ height: 60 }} />
    </div>
  );
}
// ── Agent network wakeup screen (shown before Logos starts) ───
const AGENT_COLORS = ["#7c3aed","#06b6d4","#10b981","#f59e0b","#ec4899","#6366f1","#14b8a6","#f43f5e"];
const AGENT_DESCS  = [
  "Understands your goals, audience, product and campaign objectives",
  "Crafts big ideas and messaging territories that inspire",
  "Writes compelling headlines, copy, scripts and captions",
  "Analyzes cultural trends, insights and audience behaviors",
  "Creates striking key visuals, ad designs and imagery",
  "Produces engaging short videos and reels visually",
  "Adapts content for every platform and channel",
  "Forecasts reach, ROAS and performance before launch",
];
// Real-looking photo headshots — one consistent photo per agent (pravatar.cc)
// Local agent logo PNGs downloaded from GCS bucket (agent-logo/).
// Keyed by HARNESS_STAGES index (0=Logos,1=Helia,...,7=Nexus).
// "Kinetic.png" is the filename in the bucket for the Kinetik agent.
const AGENT_AVATARS: Record<number, string> = {
  0: "/agent-logo/Logo 2.png",   // Logos
  1: "/agent-logo/Helia.png",    // Helia
  2: "/agent-logo/Ideon.png",    // Ideon
  3: "/agent-logo/Aether.png",   // Aether
  4: "/agent-logo/Morphis.png",  // Morphis
  5: "/agent-logo/Kinetic.png",  // Kinetik
  6: "/agent-logo/Poly.png",     // Poly
};
const avatarUrl = (_label: string, idx: number): string =>
  AGENT_AVATARS[idx] ?? `https://i.pravatar.cc/150?img=${[12,5,32,47,23,68,17,55][idx] ?? 1}`;

// Card left is relative to outer div layout pos (n.x), transform shifts visual by -27.
// Right gap = RIGHT_X - 54; Left gap = -170 - LEFT_X. Set both to 6px for clean spacing.
const RIGHT_X = 60;
const LEFT_X  = -176;

const CARD_OFF: [number, number][] = [
  [-58, -90],      // 0 Logos — centred above avatar: co[0]=(54-170)/2, co[1]=-(card_h+gap)
  [RIGHT_X, -10],  // 1 Helia
  [RIGHT_X, -12],  // 2 Ideon
  [RIGHT_X,   6],  // 3 Aether

  [LEFT_X,    6],  // 4 Morphis
  [LEFT_X,  -12],  // 5 Kinetik
  [LEFT_X,  -36],  // 6 Poly
  [RIGHT_X,  28],  // 7 Nexus — lower right
];
function AgentNetworkWakeUp() {
  const W = 680, H = 400, cx = W / 2, cy = H / 2, R = 160;

  // Scale the fixed-size diagram to fit any screen width
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver(entries => {
      const w = entries[0].contentRect.width;
      setScale(Math.min(1, (w - 32) / W));   // 16px padding each side
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const nodes = HARNESS_STAGES.map((s, i) => {
    const a = (i / HARNESS_STAGES.length) * 2 * Math.PI - Math.PI / 2;
    return { ...s, x: cx + Math.cos(a) * R, y: cy + Math.sin(a) * R,
      num: String(i + 1).padStart(2, "0"), color: AGENT_COLORS[i], desc: AGENT_DESCS[i],
      co: CARD_OFF[i], avatar: avatarUrl(s.label, i) };
  });

  return (
    <div ref={containerRef} style={{ flex: 1, display: "flex", flexDirection: "column" as const,
      background: "var(--page-bg)",
      overflow: "hidden", position: "relative" as const }}>

      {/* Subtle grid */}
      <div style={{ position: "absolute" as const, inset: 0, opacity: 1,
        backgroundImage: "linear-gradient(rgba(124,58,237,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(124,58,237,0.04) 1px,transparent 1px)",
        backgroundSize: "44px 44px", pointerEvents: "none" as const }} />

      {/* Ambient blobs */}
      <div style={{ position: "absolute" as const, top: "-20%", right: "-10%",
        width: 500, height: 500, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(124,58,237,0.12) 0%, transparent 70%)",
        pointerEvents: "none" as const }} />
      <div style={{ position: "absolute" as const, bottom: "-20%", left: "-10%",
        width: 400, height: 400, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(99,102,241,0.10) 0%, transparent 70%)",
        pointerEvents: "none" as const }} />

      {/* Title — font scales down on small screens */}
      <div style={{ textAlign: "center" as const, padding: "24px 16px 0", position: "relative", zIndex: 10 }}>
        <h2 style={{ fontSize: `clamp(16px, ${scale * 24}px, 24px)`, fontWeight: 800, color: "var(--text-primary)",
          letterSpacing: "-0.02em", marginBottom: 6, lineHeight: 1.3 }}>
          Seven AI Agents.{" "}
          <span style={{ background: ORB_BG, WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
            One Powerful Campaign.
          </span>
        </h2>
        <p style={{ fontSize: `clamp(10px, ${scale * 12}px, 12px)`, color: "var(--text-primary)", lineHeight: 1.6,
          maxWidth: 460, margin: "0 auto", textShadow: "0 1px 4px rgba(255,255,255,0.2)" }}>
          From strategy to content, visuals to videos, and channel-optimised publishing —
          our AI agents collaborate to launch campaigns that perform.
        </p>
      </div>

      {/* Network diagram — scales uniformly to fit any screen width */}
      <div style={{ flex: 1, display: "flex", alignItems: "flex-start", justifyContent: "center",
        paddingTop: Math.round(110 * scale), overflow: "hidden" }}>
        <div style={{ position: "relative" as const, width: W, height: H, overflow: "visible",
          transform: `scale(${scale})`, transformOrigin: "top center",
          marginBottom: H * (scale - 1) /* collapse empty space when scaled down */ }}>

          {/* SVG: rings + connecting lines + travelling dots */}
          <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H}
            style={{ position: "absolute" as const, inset: 0, overflow: "visible" }}>
            {[42, 72, 108].map((r, ri) => (
              <circle key={ri} cx={cx} cy={cy} r={r} fill="none"
                stroke="rgba(124,58,237,0.12)" strokeWidth="1.2"
                style={{ animation: `ring-out ${2.5 + ri * 0.8}s ${ri * 0.4}s ease-out infinite` }} />
            ))}
            {nodes.map((n, i) => (
              <line key={n.key} x1={cx} y1={cy} x2={n.x} y2={n.y}
                stroke={n.color} strokeOpacity="0.25" strokeWidth="1.5"
                strokeDasharray="6 5"
                style={{ animation: `dash-move 2s ${i * 0.22}s linear infinite` }} />
            ))}
            {/* Travelling dot on each line */}
            {nodes.map((n, i) => {
              const t = 0.52;
              return <circle key={`d${i}`}
                cx={cx + (n.x - cx) * t} cy={cy + (n.y - cy) * t} r={3}
                fill={n.color}
                style={{ animation: `wave-dot 1.8s ${i * 0.25}s ease-in-out infinite` }} />;
            })}
          </svg>

          {/* Central hub */}
          <div style={{ position: "absolute" as const, left: cx, top: cy,
            transform: "translate(-50%,-50%)", zIndex: 4,
            animation: "hub-beat 2s ease-in-out infinite" }}>
            <GradientOrb size={78} />
          </div>

          {/* Agent nodes + badges + info cards */}
          {nodes.map((n, i) => (
            <div key={n.key} style={{ position: "absolute" as const, left: n.x, top: n.y,
              transform: "translate(-50%,-50%)", zIndex: 3,
              animation: `node-in 0.5s ${0.15 + i * 0.12}s cubic-bezier(0.22,1,0.36,1) both` }}>

              {/* Node circle with avatar */}
              <div style={{ width: 54, height: 54, borderRadius: "50%", position: "relative" as const,
                border: `2.5px solid ${n.color}70`,
                boxShadow: `0 0 20px ${n.color}35, 0 2px 8px rgba(0,0,0,0.1)`,
                overflow: "hidden",
                animation: `node-glow 2.4s ${i * 0.35}s ease-in-out infinite` }}>
                <img src={n.avatar} alt={n.label}
                  style={{ width: "100%", height: "100%", display: "block", objectFit: "cover" }} />
                {/* Number badge */}
                <div style={{ position: "absolute" as const, top: -7, right: n.co[0] < 0 ? undefined : -7,
                  left: n.co[0] < 0 ? -7 : undefined,
                  width: 19, height: 19, borderRadius: "50%",
                  background: n.color, border: "2px solid white",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 8, fontWeight: 800, color: "white",
                  boxShadow: `0 0 6px ${n.color}80` }}>{n.num}</div>
              </div>

              {/* Info card */}
              <div style={{ position: "absolute" as const,
                left: n.co[0], top: n.co[1],
                width: 170, padding: "9px 12px",
                background: "var(--card-bg-translucent)",
                backdropFilter: "blur(12px)",
                border: `1px solid ${n.color}35`,
                borderRadius: 10,
                boxShadow: `0 4px 16px var(--card-border), 0 0 12px ${n.color}22`,
                textAlign: i === 0 ? "center" as const : n.co[0] < 0 ? "right" as const : "left" as const }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: n.color, marginBottom: 3 }}>
                  {n.label}
                </div>
                <div style={{ fontSize: 9.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>{n.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Working Together strip */}
      <div style={{ padding: "8px 24px 12px",
        borderTop: "1px solid rgba(124,58,237,0.12)",
        display: "flex", alignItems: "center", gap: 6, flexShrink: 0,
        background: "var(--card-bg)" }}>
        <div style={{ fontSize: 10, fontWeight: 800, color: "#7c3aed",
          letterSpacing: "0.04em", marginRight: 8, lineHeight: 1.4,
          whiteSpace: "nowrap" as const }}>Working<br/>Together</div>
        {HARNESS_STAGES.map((s, i) => (
          <Fragment key={s.key}>
            <div style={{ display: "flex", alignItems: "center", gap: 4,
              padding: "3px 9px", borderRadius: 6,
              background: "rgba(124,58,237,0.10)",
              border: "1px solid rgba(124,58,237,0.22)" }}>
              <img src={AGENT_AVATARS[i]} alt={s.label}
                style={{ width: 14, height: 14, borderRadius: 3, objectFit: "cover", flexShrink: 0 }} />
              <span style={{ fontSize: 9.5, color: "#a78bfa", fontWeight: 600,
                whiteSpace: "nowrap" as const }}>{s.label}</span>
            </div>
            {i < HARNESS_STAGES.length - 1 && (
              <span style={{ color: "#7c3aed", fontSize: 10, flexShrink: 0 }}>→</span>
            )}
          </Fragment>
        ))}
      </div>
    </div>
  );
}

// ── Briefing agent orb header ─────────────────────────────────
function OrbHeader({ done }: { done: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 28 }}>
      <div style={{
        width: 52, height: 52, borderRadius: "50%", flexShrink: 0,
        background: ORB_BG,
        boxShadow: "0 4px 20px rgba(200,40,200,0.3)",
        display: "flex", alignItems: "center", justifyContent: "center",
        animation: done ? "none" : "icon-breathe 2.5s ease-in-out infinite",
      }}>
        <svg width={20} height={20} viewBox="0 0 24 24" fill="none">
          <path d="M12 2L13.8 10.2L22 12L13.8 13.8L12 22L10.2 13.8L2 12L10.2 10.2Z" fill="white" />
        </svg>
      </div>
      <div>
        <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.12em",
          color: "#7c3aed", textTransform: "uppercase" as const, marginBottom: 3 }}>
          LOGOS · {done ? "COMPLETE ✓" : "RUNNING"}
        </div>
        <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)" }}>Validating Brief</div>
      </div>
    </div>
  );
}

// ── Brief Intake view — 3-phase A2A style ────────────────────
// Phase 1: "Generating..." orb (agent not yet active)
// Phase 2: Data sources streaming in (agent running, data flowing)
// Phase 3: Brief summary cards (agent done)
// All phases share the same purple/violet color identity.
const BRIEF_DATA_SOURCES = [
  { id: "brand",    icon: "📚", label: "Brand Guidelines",     from: "GCS Bucket",        delay: 0    },
  { id: "fantruth", icon: "💡", label: "Fan Truth Library",    from: "Vertex AI Search",  delay: 600  },
  { id: "history",  icon: "📈", label: "Historical Campaigns", from: "BigQuery",           delay: 1200 },
  { id: "cdp",      icon: "👥", label: "CDP / Sephora",        from: "Kaggle · BigQuery", delay: 1800 },
];
function BriefIntakeView({
  brief,
  milestone,
  liveMsg,
  agentDone,
}: {
  brief: import("./types/pipeline").HarnessBriefRequest | null;
  milestone: Record<string, unknown> | undefined;
  liveMsg: string | null;
  agentDone: boolean;
}) {
  const ft   = (milestone?.fan_truth ?? {}) as any;
  const aud  = (milestone?.audience  ?? {}) as any;
  const kpis = (milestone?.kpis      ?? []) as any[];

  // Phase logic
  const hasData = !!milestone || !!liveMsg;
  // phase 1: nothing yet, phase 2: data flowing, phase 3: done
  const phase: 1 | 2 | 3 = agentDone ? 3 : hasData ? 2 : 1;

  // ── Phase 1: Generating spinner ─────────────────────────────
  if (phase === 1) {
    return (
      <div style={{ flex: 1, display: "flex", flexDirection: "column" as const,
        alignItems: "center", justifyContent: "center", gap: 28 }}>
        <div style={{
          width: 90, height: 90, borderRadius: "50%",
          background: ORB_BG,
          boxShadow: "0 8px 32px rgba(200,40,200,0.32)",
          display: "flex", alignItems: "center", justifyContent: "center",
          animation: "icon-breathe 2.5s ease-in-out infinite",
        }}>
          <svg width={34} height={34} viewBox="0 0 24 24" fill="none">
            <path d="M12 2L13.8 10.2L22 12L13.8 13.8L12 22L10.2 13.8L2 12L10.2 10.2Z" fill="white" />
          </svg>
        </div>
        <div style={{ fontSize: 20, fontWeight: 600, color: "var(--text-secondary)", letterSpacing: "-0.01em" }}>
          Generating ...
        </div>
      </div>
    );
  }

  // ── Phase 2: Data sources streaming ─────────────────────────
  if (phase === 2) {
    const hasAllSources = !!milestone?.fan_truth;
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
        padding: "40px 48px", overflowY: "auto" as const,
        background: "var(--page-bg)" }}>
        <div style={{ width: "100%", maxWidth: 680 }}>
          <OrbHeader done={false} />

          {/* Data sources */}
          <div style={{ fontSize: 11, fontWeight: 800, color: "#7c3aed", letterSpacing: "0.12em",
            textTransform: "uppercase" as const, marginBottom: 16 }}>
            Querying Data Sources
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 24 }}>
            {BRIEF_DATA_SOURCES.map((src, idx) => {
              const done = hasAllSources || (milestone && idx === 0);
              return (
                <div key={src.id} style={{
                  display: "flex", alignItems: "center", gap: 16,
                  padding: "20px 22px", borderRadius: 16,
                  background: done ? "rgba(124,58,237,0.14)" : "rgba(255,255,255,0.04)",
                  border: `1.5px solid ${done ? "rgba(124,58,237,0.40)" : "rgba(255,255,255,0.08)"}`,
                  boxShadow: done ? "0 4px 20px rgba(124,58,237,0.14)" : "0 2px 8px rgba(0,0,0,0.3)",
                  backdropFilter: "blur(8px)",
                  transition: "all 0.4s ease",
                }}>
                  <div style={{ width: 48, height: 48, borderRadius: 12, flexShrink: 0,
                    background: done ? "rgba(124,58,237,0.20)" : "rgba(255,255,255,0.06)",
                    display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22 }}>
                    {src.icon}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 3 }}>
                      {src.label}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>← {src.from}</div>
                  </div>
                  {done
                    ? <span style={{ fontSize: 16, color: "#7c3aed", fontWeight: 800, flexShrink: 0 }}>✓</span>
                    : <div style={{ display: "flex", gap: 3, flexShrink: 0 }}>
                        {[0,1,2].map(d => (
                          <div key={d} style={{ width: 5, height: 5, borderRadius: "50%",
                            background: "#cc3cf2",
                            animation: `wave-dot 1.2s ${idx * 0.15 + d * 0.2}s ease-in-out infinite` }} />
                        ))}
                      </div>}
                </div>
              );
            })}
          </div>

          {/* Live message */}
          {liveMsg && (
            <div style={{ fontSize: 13, color: "#7c3aed", fontStyle: "italic",
              padding: "10px 14px", borderRadius: 10,
              background: "rgba(124,58,237,0.06)", border: "1px solid rgba(124,58,237,0.15)" }}>
              {liveMsg}
            </div>
          )}

          {/* Fan Truth preview when it arrives */}
          {ft?.overall !== undefined && (
            <div style={{ marginTop: 16, padding: "16px 18px", borderRadius: 12,
              background: "rgba(124,58,237,0.10)", border: "1.5px solid rgba(124,58,237,0.28)" }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: "#a78bfa",
                letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 10 }}>
                Fan Truth Score
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 32, fontWeight: 900,
                  color: ft.overall >= 70 ? "#10b981" : ft.overall >= 50 ? "#f59e0b" : "#ef4444" }}>
                  {ft.overall}/100
                </span>
                {ft.verdict === "PASS" && (
                  <span style={{ fontSize: 11, fontWeight: 800, padding: "3px 12px", borderRadius: 99,
                    background: "rgba(16,185,129,0.18)", color: "#34d399" }}>
                    PASS
                  </span>
                )}
              </div>
              {ft.statement && (
                <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-tertiary)", fontStyle: "italic" }}>
                  "{String(ft.statement).slice(0, 110)}…"
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Phase 3: Brief summary cards ────────────────────────────
  const Card = ({ title, children, full }: { title: string; children: React.ReactNode; full?: boolean }) => (
    <div style={{
      background: "var(--card-bg)", border: "1px solid rgba(124,58,237,0.18)", borderRadius: 14,
      padding: "22px 24px", gridColumn: full ? "1 / -1" : undefined,
      backdropFilter: "blur(8px)",
      boxShadow: "0 4px 20px rgba(0,0,0,0.09)",
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#a78bfa", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );

  const scoreColor = ft?.overall >= 70 ? "#10b981" : ft?.overall >= 50 ? "#f59e0b" : "#ef4444";
  const interestTags = [
    ...(brief?.audience?.age_range ? [brief.audience.age_range] : []),
    ...(brief?.audience?.interests ? brief.audience.interests.split(", ").filter(Boolean) : []),
  ];

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "var(--page-bg)" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <OrbHeader done={true} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

        {/* Brand */}
        <Card title="Brand">
          <div style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", lineHeight: 1.1, marginBottom: 6 }}>
            {brief?.brand ?? "—"}
          </div>
          <div style={{ fontSize: 14, color: "#6b7280" }}>{brief?.product ?? ""}</div>
        </Card>

        {/* Objective */}
        <Card title="Objective">
          <div style={{ fontSize: 15, color: "var(--text-secondary)", lineHeight: 1.6 }}>
            {brief?.goal ?? "—"}
          </div>
        </Card>

        {/* Target Audience */}
        <Card title="Target Audience">
          <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>
            {brief?.audience?.segment || "General Audience"}
          </div>
          {brief?.audience?.age_range && (
            <div style={{ fontSize: 14, color: "var(--text-tertiary)", marginBottom: 10 }}>
              {brief.audience.age_range}
            </div>
          )}
          <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 6 }}>
            {interestTags.map((t, i) => (
              <span key={i} style={{ fontSize: 12, padding: "3px 10px", borderRadius: 99,
                background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.12)", color: "var(--text-tertiary)" }}>
                {t}
              </span>
            ))}
            {brief?.market && (
              <span style={{ fontSize: 12, padding: "3px 10px", borderRadius: 99,
                background: "rgba(124,58,237,0.14)", border: "1px solid rgba(124,58,237,0.30)", color: "#a78bfa" }}>
                {brief.market}
              </span>
            )}
          </div>
        </Card>

        {/* Channels */}
        <Card title="Channels">
          <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
            {(brief?.channels ?? []).map((ch, i) => (
              <span key={i} style={{ fontSize: 13, padding: "5px 14px", borderRadius: 99,
                background: "rgba(124,58,237,0.14)", border: "1px solid rgba(124,58,237,0.28)", color: "#a78bfa", fontWeight: 500 }}>
                {ch}
              </span>
            ))}
          </div>
        </Card>

        {/* KPIs */}
        <Card title="KPIs">
          {kpis.length > 0 ? (
            kpis.slice(0, 4).map((k: any, i: number) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8,
                marginBottom: 8, fontSize: 14, color: "var(--text-primary)" }}>
                <span style={{ color: "#a78bfa", fontWeight: 700 }}>→</span>
                <span style={{ fontWeight: 600 }}>{k.metric}</span>
                {k.target && <span style={{ color: "var(--text-tertiary)" }}>— {k.target}</span>}
              </div>
            ))
          ) : (brief?.kpis ? brief.kpis.split(", ").map((k, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8,
              marginBottom: 8, fontSize: 14, color: "var(--text-primary)" }}>
              <span style={{ color: "#a78bfa", fontWeight: 700 }}>→</span> {k}
            </div>
          )) : null)}
        </Card>

        {/* Fan Truth */}
        <Card title="Fan Truth Score">
          {ft?.overall !== undefined ? (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
                <span style={{ fontSize: 28, fontWeight: 800, color: scoreColor }}>
                  {ft.overall}/100
                </span>
                {ft.verdict === "PASS" && (
                  <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 99,
                    background: "rgba(16,185,129,0.18)", color: "#34d399" }}>
                    PASS
                  </span>
                )}
              </div>
              {ft.statement && (
                <div style={{ fontSize: 13, color: "var(--text-tertiary)", fontStyle: "italic", lineHeight: 1.5 }}>
                  "{String(ft.statement).slice(0, 100)}{String(ft.statement).length > 100 ? "…" : ""}"
                </div>
              )}
              {aud?.count && (
                <div style={{ marginTop: 8, fontSize: 12, color: "#a78bfa" }}>
                  👥 {String(aud.count).replace(/\D.*/, "")} profiles matched
                  {aud.income ? ` · ${aud.income}` : ""}
                </div>
              )}
            </div>
          ) : (
            <div style={{ fontSize: 14, color: "#9ca3af" }}>Awaiting score…</div>
          )}
        </Card>

        {/* Tone of Voice — full width */}
        <Card title="Tone of Voice" full>
          <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", fontStyle: "italic" }}>
            "{brief?.tone || "Bold, warm, unapologetically confident"}"
          </div>
        </Card>

        </div>{/* grid */}
      </div>
    </div>
  );
}

// ── Shared agent intake helpers ──────────────────────────────
function AgentIntakeHeader({ label, title, done }: {
  label: string; title: string; done: boolean;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 28 }}>
      {/* Always the same A2A purple orb */}
      <div style={{
        width: 52, height: 52, borderRadius: "50%", flexShrink: 0,
        background: ORB_BG,
        boxShadow: "0 4px 20px rgba(200,40,200,0.3)",
        display: "flex", alignItems: "center", justifyContent: "center",
        animation: done ? "none" : "icon-breathe 2.5s ease-in-out infinite",
      }}>
        <svg width={22} height={22} viewBox="0 0 24 24" fill="none">
          <path d="M12 2L13.8 10.2L22 12L13.8 13.8L12 22L10.2 13.8L2 12L10.2 10.2Z" fill="white" />
        </svg>
      </div>
      <div>
        <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.12em",
          color: "#7c3aed", textTransform: "uppercase" as const, marginBottom: 3 }}>
          {label} · {done ? "COMPLETE ✓" : "RUNNING"}
        </div>
        <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)" }}>{title}</div>
      </div>
    </div>
  );
}

function AgentGeneratingView({ liveMsg }: { liveMsg?: string | null }) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" as const,
      alignItems: "center", justifyContent: "center", gap: 24 }}>
      <div style={{
        width: 90, height: 90, borderRadius: "50%",
        background: ORB_BG,
        boxShadow: "0 8px 32px rgba(200,40,200,0.32)",
        display: "flex", alignItems: "center", justifyContent: "center",
        animation: "icon-breathe 2.5s ease-in-out infinite",
      }}>
        <svg width={34} height={34} viewBox="0 0 24 24" fill="none">
          <path d="M12 2L13.8 10.2L22 12L13.8 13.8L12 22L10.2 13.8L2 12L10.2 10.2Z" fill="white" />
        </svg>
      </div>
      <div style={{ fontSize: 20, fontWeight: 600, color: "var(--text-tertiary)", letterSpacing: "-0.01em" }}>
        Generating ...
      </div>
      {liveMsg && (
        <div style={{ fontSize: 12, color: "var(--text-secondary)", fontStyle: "italic", maxWidth: 340,
          textAlign: "center" as const, lineHeight: 1.5, padding: "0 24px" }}>
          {liveMsg}
        </div>
      )}
    </div>
  );
}

// ── Strategy / Content Creator intake view ────────────────────
function StrategyIntakeView({ milestone, liveMsg }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
}) {
  const m = (milestone ?? {}) as any;

  // Stay on orb until real milestone data arrives
  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  const SCard = ({ title, children, full }: { title: string; children: React.ReactNode; full?: boolean }) => (
    <div style={{ background: "var(--card-bg)", border: "1px solid rgba(124,58,237,0.18)", borderRadius: 14,
      padding: "22px 24px", gridColumn: full ? "1 / -1" : undefined,
      backdropFilter: "blur(8px)", boxShadow: "0 4px 20px rgba(0,0,0,0.09)" }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#a78bfa", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "var(--page-bg)" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <AgentIntakeHeader label="HELIA" title="Creative Strategy" done={true} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {m.big_idea && (
            <SCard title="Big Idea" full>
              <div style={{ fontSize: 22, fontWeight: 800, fontStyle: "italic",
                color: "#6d28d9", lineHeight: 1.3 }}>"{m.big_idea}"</div>
            </SCard>
          )}
          {m.hero_message && (
            <SCard title="Hero Message" full>
              <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.4 }}>
                "{m.hero_message}"
              </div>
              {m.tagline && (
                <div style={{ marginTop: 8, fontSize: 14, color: "var(--text-tertiary)", fontStyle: "italic" }}>
                  {m.tagline}
                </div>
              )}
            </SCard>
          )}
          {m.strategic_framework && (
            <SCard title="Strategic Framework">
              <div style={{ fontSize: 13, color: "var(--text-tertiary)", lineHeight: 1.7 }}>
                {String(m.strategic_framework).slice(0, 260)}
                {String(m.strategic_framework).length > 260 ? "…" : ""}
              </div>
            </SCard>
          )}
          {(m.messaging_pillars as string[])?.length > 0 && (
            <SCard title="Messaging Pillars">
              <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
                {(m.messaging_pillars as string[]).slice(0, 4).map((p: string, i: number) => (
                  <span key={i} style={{ fontSize: 12, padding: "5px 12px", borderRadius: 99,
                    background: "rgba(124,58,237,0.14)", border: "1px solid rgba(124,58,237,0.28)", color: "#a78bfa", fontWeight: 600 }}>
                    {String(p).slice(0, 40)}
                  </span>
                ))}
              </div>
            </SCard>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Copy Agent intake view ────────────────────────────────────
function CopyIntakeView({ milestone, liveMsg }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
}) {
  const g1 = "#7c3aed", g2 = "#6d28d9";
  const m = (milestone ?? {}) as any;

  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  const CCard = ({ title, children, full }: { title: string; children: React.ReactNode; full?: boolean }) => (
    <div style={{ background: "var(--card-bg)", border: "1px solid rgba(124,58,237,0.18)", borderRadius: 14,
      padding: "22px 24px", gridColumn: full ? "1 / -1" : undefined,
      backdropFilter: "blur(8px)", boxShadow: "0 4px 20px rgba(0,0,0,0.09)" }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#a78bfa", letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );

  const channelCopy = m.channel_copy as Record<string, string> | undefined;
  const COPY_CFG: Record<string, { icon: string; label: string; color: string; bg: string }> = {
    instagram_caption: { icon: "📸", label: "Instagram", color: "#7c3aed", bg: "#fdf4ff" },
    tiktok_hook:       { icon: "🎵", label: "TikTok",    color: "#be185d", bg: "#fff0f6" },
    youtube_script:    { icon: "▶️", label: "YouTube",   color: "#dc2626", bg: "#fff1f2" },
    google_headline:   { icon: "🔍", label: "Google",    color: "#1967d2", bg: "#eff6ff" },
    meta_caption:      { icon: "📘", label: "Meta",      color: "#1877f2", bg: "#eff6ff" },
    ooh_headline:      { icon: "🏙️", label: "OOH",      color: "#d97706", bg: "#fffbeb" },
    web_headline:      { icon: "🌐", label: "Website",   color: "#059669", bg: "#f0fdf4" },
    email_subject:     { icon: "📧", label: "Email",     color: "#0369a1", bg: "#f0f9ff" },
  };

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "var(--page-bg)" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <AgentIntakeHeader label="IDEON" title="Campaign Copy" done={true} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {/* Billboard hero */}
          {m.short_headline && (
            <CCard title="Short Headline" full>
              <div style={{ background: `linear-gradient(135deg, ${g1}, ${g2})`,
                borderRadius: 10, padding: "20px 24px", textAlign: "center" as const, marginBottom: 8 }}>
                <div style={{ fontSize: 22, fontWeight: 900, color: "white", lineHeight: 1.2 }}>
                  "{m.short_headline}"
                </div>
                {m.cta && (
                  <div style={{ marginTop: 12, display: "inline-block", padding: "6px 20px",
                    borderRadius: 99, background: "white", color: g1, fontSize: 12, fontWeight: 800 }}>
                    {m.cta}
                  </div>
                )}
              </div>
            </CCard>
          )}
          {m.medium_headline && (
            <CCard title="Medium Headline">
              <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.4 }}>
                "{m.medium_headline}"
              </div>
            </CCard>
          )}
          {m.body && (
            <CCard title="Body Copy">
              <div style={{ fontSize: 13, color: "var(--text-tertiary)", lineHeight: 1.7 }}>
                {String(m.body).slice(0, 200)}{String(m.body).length > 200 ? "…" : ""}
              </div>
            </CCard>
          )}
          {channelCopy && Object.keys(channelCopy).length > 0 && (
            <CCard title="Channel Copy" full>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {Object.entries(channelCopy).map(([key, val]) => {
                  const cfg = COPY_CFG[key] ?? { icon: "📢", label: key, color: "var(--text-tertiary)", bg: "#eef0f4" };
                  return (
                    <div key={key} style={{ padding: "10px 12px", borderRadius: 10,
                      background: "var(--card-bg)", border: `1px solid rgba(255,255,255,0.09)` }}>
                      <div style={{ fontSize: 10, fontWeight: 700, color: cfg.color,
                        textTransform: "uppercase" as const, letterSpacing: "0.1em", marginBottom: 5 }}>
                        {cfg.icon} {cfg.label}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-tertiary)", lineHeight: 1.4 }}>
                        {val.slice(0, 90)}{val.length > 90 ? "…" : ""}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CCard>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Culture / Cultural Research intake view ───────────────────
function CultureIntakeView({ milestone, liveMsg }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
}) {
  const raw = milestone?.brief ? String(milestone.brief) : "";

  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  const sentences = raw
    .replace(/\*\*([^*]+)\*\*/g, "$1").replace(/^#+\s*/gm, "").replace(/^[-*]\s*/gm, "")
    .split(/(?<=[.!?])\s+/).map(s => s.trim()).filter(s => s.length > 25).slice(0, 6);

  const ICONS = ["🌍", "💫", "🎯", "⚡", "🔥", "✨"];

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "var(--page-bg)" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <AgentIntakeHeader label="AETHER" title="Cultural Intelligence" done={true} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          {sentences.map((s, i) => (
            <div key={i} style={{ display: "flex", gap: 14, padding: "18px 20px",
              borderRadius: 14, background: "var(--card-bg)",
              border: `1px solid ${i === 0 ? "rgba(124,58,237,0.30)" : "rgba(255,255,255,0.08)"}`,
              backdropFilter: "blur(8px)",
              boxShadow: `0 4px 20px rgba(0,0,0,0.09)`,
              gridColumn: i === 0 ? "1 / -1" : undefined }}>
              <span style={{ fontSize: 22, flexShrink: 0, marginTop: 2 }}>{ICONS[i]}</span>
              <span style={{ fontSize: i === 0 ? 15 : 13, color: "var(--text-secondary)", lineHeight: 1.6,
                fontWeight: i === 0 ? 600 : 400 }}>
                {s}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── KV Generator intake view ─────────────────────────────────
function KVIntakeView({ milestone, liveMsg, reelMilestone, agentDone }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
  reelMilestone: Record<string,unknown> | undefined;
  agentDone?: boolean;
}) {
  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  return (
    <div style={{ flex: 1, overflowY: "auto" as const,
      background: "var(--page-bg)" }}>
      <div style={{ minHeight: "100%", display: "flex", flexDirection: "column" as const,
        justifyContent: "center", padding: "32px 36px" }}>
        <div style={{ maxWidth: 800, margin: "0 auto", width: "100%" }}>
          <AgentIntakeHeader label="MORPHIS" title="Key Visual" done={agentDone ?? true} />
          <KVPanel m={milestone} liveMsg={liveMsg} reelMilestone={reelMilestone} />
        </div>
      </div>
    </div>
  );
}

// ── Reel Generator intake view ────────────────────────────────
function ReelIntakeView({ milestone, liveMsg }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
}) {
  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  const videoB64 = milestone.video_b64 ? String(milestone.video_b64) : "";
  const videoUri = milestone.video_uri
    ? String(milestone.video_uri).replace(/^gs:\/\/([^/]+)\/(.+)$/, "https://storage.googleapis.com/$1/$2")
    : "";
  const videoSrc = videoB64 ? `data:video/mp4;base64,${videoB64}` : videoUri;

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "var(--page-bg)" }}>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <AgentIntakeHeader label="KINETIK" title="Campaign Reel" done={true} />
        {videoSrc ? (
          <div style={{ background: "var(--card-bg)", borderRadius: 16, padding: "20px 24px", border: "1px solid var(--card-border)", boxShadow: "0 2px 12px rgba(0,0,0,0.06)" }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: "#f59e0b",
              letterSpacing: "0.1em", textTransform: "uppercase" as const, marginBottom: 12 }}>
              🎬 Campaign Reel · 6s
            </div>
            <video controls autoPlay loop muted playsInline
              style={{ width: "100%", borderRadius: 10, display: "block" }}
              src={videoSrc} />
            <a href={videoSrc} download="campaign-reel.mp4"
              style={{ display: "inline-block", marginTop: 12, fontSize: 12, fontWeight: 700,
                color: "#f59e0b", textDecoration: "none" }}>
              ⬇ Download Reel
            </a>
          </div>
        ) : (
          <AgentGeneratingView liveMsg={liveMsg} />
        )}
      </div>
    </div>
  );
}

// ── Channel Adapter intake view ───────────────────────────────
function ChannelAdapterIntakeView({ milestone, liveMsg }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
}) {
  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "var(--page-bg)" }}>
      <div style={{ maxWidth: 860, margin: "0 auto" }}>
        <AgentIntakeHeader label="POLY" title="Publishing to Channels" done={true} />
        <ChannelPanel m={milestone} liveMsg={liveMsg} />
      </div>
    </div>
  );
}

// ── Performance / Nexus forecast view ────────────────────────
function PerformanceIntakeView({ milestone, liveMsg }: {
  milestone: Record<string,unknown> | undefined;
  liveMsg: string | null;
}) {
  if (!milestone) return <AgentGeneratingView liveMsg={liveMsg} />;

  const m = milestone as any;
  const channelForecasts: any[] = Array.isArray(m.channel_forecasts) ? m.channel_forecasts : [];

  const ROSE = "#fb7185";
  const ROSE_LIGHT = "rgba(251,113,133,0.08)";
  const ROSE_BORDER = "rgba(251,113,133,0.25)";

  const confColor = (c: string) =>
    c === "HIGH" ? "#34d399" : c === "MEDIUM" ? "#fbbf24" : "#f87171";
  const confBg    = (c: string) =>
    c === "HIGH" ? "rgba(52,211,153,0.12)" : c === "MEDIUM" ? "rgba(251,191,36,0.12)" : "rgba(248,113,113,0.12)";
  const confBorder = (c: string) =>
    c === "HIGH" ? "rgba(52,211,153,0.30)" : c === "MEDIUM" ? "rgba(251,191,36,0.30)" : "rgba(248,113,113,0.30)";

  const FCard = ({ title, children, full }: { title: string; children: React.ReactNode; full?: boolean }) => (
    <div style={{
      background: "var(--card-bg)", border: `1px solid ${ROSE_BORDER}`, borderRadius: 14,
      padding: "22px 24px", gridColumn: full ? "1 / -1" : undefined,
      boxShadow: "0 4px 16px rgba(0,0,0,0.08)", backdropFilter: "blur(8px)",
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: ROSE, letterSpacing: "0.1em",
        textTransform: "uppercase" as const, marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );

  return (
    <div style={{ flex: 1, overflowY: "auto" as const, padding: "32px 36px",
      background: "var(--page-bg)" }}>
      <div style={{ maxWidth: 920, margin: "0 auto" }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 28 }}>
          <div style={{
            width: 52, height: 52, borderRadius: "50%", flexShrink: 0,
            background: `linear-gradient(135deg, ${ROSE} 0%, #be123c 100%)`,
            boxShadow: "0 4px 20px rgba(251,113,133,0.32)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <span style={{ fontSize: 22 }}>📊</span>
          </div>
          <div>
            <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.12em",
              color: ROSE, textTransform: "uppercase" as const, marginBottom: 3 }}>
              NEXUS · COMPLETE ✓
            </div>
            <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)" }}>Pre-Launch Performance Forecast</div>
          </div>
        </div>

        {/* Top KPI strip */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 20 }}>
          {[
            { label: "Predicted Reach",  value: m.predicted_total_reach,  icon: "👥" },
            { label: "Blended ROAS",     value: m.predicted_blended_roas, icon: "💰" },
            { label: "Confidence",        value: m.overall_confidence,     icon: "🎯" },
          ].map(({ label, value, icon }) => (
            <div key={label} style={{
              background: "var(--card-bg)", border: `1px solid ${ROSE_BORDER}`, borderRadius: 12,
              padding: "16px 20px", textAlign: "center" as const,
              boxShadow: "0 4px 16px rgba(0,0,0,0.08)", backdropFilter: "blur(8px)",
            }}>
              <div style={{ fontSize: 20, marginBottom: 6 }}>{icon}</div>
              <div style={{ fontSize: 20, fontWeight: 800, color: "var(--text-primary)" }}>{value ?? "—"}</div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 600, marginTop: 3,
                textTransform: "uppercase" as const, letterSpacing: "0.06em" }}>{label}</div>
            </div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

          {/* Headline prediction */}
          {m.headline_prediction && (
            <FCard title="Forecast Headline" full>
              <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.45,
                fontStyle: "italic" }}>
                "{m.headline_prediction}"
              </div>
            </FCard>
          )}

          {/* Fan Truth impact */}
          {m.fan_truth_impact && (
            <FCard title="Fan Truth Impact">
              <div style={{ fontSize: 13, color: "var(--text-tertiary)", lineHeight: 1.7 }}>{m.fan_truth_impact}</div>
            </FCard>
          )}

          {/* Benchmark comparison */}
          {m.benchmark_comparison && (
            <FCard title="vs. Benchmarks">
              <div style={{ fontSize: 13, color: "var(--text-tertiary)", lineHeight: 1.7 }}>{m.benchmark_comparison}</div>
            </FCard>
          )}

          {/* Channel-by-channel forecasts */}
          {channelForecasts.length > 0 && (
            <FCard title="Channel Forecasts" full>
              <div style={{ display: "flex", flexDirection: "column" as const, gap: 12 }}>
                {channelForecasts.map((cf: any, i: number) => (
                  <div key={i} style={{
                    display: "grid", gridTemplateColumns: "160px 1fr 1fr 1fr 1fr auto",
                    alignItems: "center", gap: 12,
                    background: ROSE_LIGHT, borderRadius: 10, padding: "14px 16px",
                    border: `1px solid ${ROSE_BORDER}`,
                  }}>
                    <div style={{ fontWeight: 700, fontSize: 13, color: "var(--text-primary)" }}>
                      {cf.channel}
                    </div>
                    <div style={{ textAlign: "center" as const }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>{cf.predicted_reach}</div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase" as const }}>Reach</div>
                    </div>
                    <div style={{ textAlign: "center" as const }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>{cf.predicted_ctr}</div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase" as const }}>CTR</div>
                    </div>
                    <div style={{ textAlign: "center" as const }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>{cf.predicted_roas}</div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase" as const }}>ROAS</div>
                    </div>
                    <div style={{ textAlign: "center" as const }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>{cf.predicted_engagement}</div>
                      <div style={{ fontSize: 10, color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase" as const }}>Eng.</div>
                    </div>
                    <div>
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: "4px 10px", borderRadius: 99,
                        background: confBg(cf.confidence), color: confColor(cf.confidence),
                        border: `1px solid ${confBorder(cf.confidence)}`,
                        textTransform: "uppercase" as const, letterSpacing: "0.06em",
                      }}>{cf.confidence}</span>
                    </div>
                  </div>
                ))}
              </div>
            </FCard>
          )}

          {/* Risk / Opportunity */}
          {(m.top_risk || m.top_opportunity) && (
            <>
              {m.top_risk && (
                <FCard title="Top Risk">
                  <div style={{ fontSize: 13, color: "var(--text-tertiary)", lineHeight: 1.7 }}>{m.top_risk}</div>
                </FCard>
              )}
              {m.top_opportunity && (
                <FCard title="Top Opportunity">
                  <div style={{ fontSize: 13, color: "var(--text-tertiary)", lineHeight: 1.7 }}>{m.top_opportunity}</div>
                </FCard>
              )}
            </>
          )}

          {/* First 48h watchlist */}
          {Array.isArray(m.first_48h_watchlist) && m.first_48h_watchlist.length > 0 && (
            <FCard title="First 48h Watchlist" full>
              <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
                {(m.first_48h_watchlist as string[]).map((item: string, i: number) => (
                  <span key={i} style={{
                    fontSize: 12, padding: "5px 12px", borderRadius: 99,
                    background: ROSE_LIGHT, border: `1px solid ${ROSE_BORDER}`,
                    color: ROSE, fontWeight: 600,
                  }}>⏱ {item}</span>
                ))}
              </div>
            </FCard>
          )}

          {/* Budget split */}
          {m.recommended_budget_split && Object.keys(m.recommended_budget_split).length > 0 && (
            <FCard title="Recommended Budget Split" full>
              <div style={{ display: "flex", flexWrap: "wrap" as const, gap: 8 }}>
                {Object.entries(m.recommended_budget_split as Record<string,number>).map(([ch, pct]) => (
                  <div key={ch} style={{
                    display: "flex", alignItems: "center", gap: 8,
                    background: ROSE_LIGHT, border: `1px solid ${ROSE_BORDER}`,
                    borderRadius: 10, padding: "8px 14px",
                  }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)" }}>{ch}</span>
                    <span style={{ fontSize: 15, fontWeight: 800, color: ROSE }}>{(pct * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </FCard>
          )}

        </div>
      </div>
    </div>
  );
}

// ── Gradient Orb (A2A logo style) ────────────────────────────
function GradientOrb({ size = 40 }: { size?: number }) {
  const u = `orb${size}`;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100"
      style={{ display: "block", flexShrink: 0,
        filter: `drop-shadow(0 ${size*0.07}px ${size*0.28}px rgba(200,40,200,0.38)) drop-shadow(0 0 ${size*0.08}px rgba(255,255,255,0.5))` }}>
      <defs>
        {/* Base: hot magenta-pink centre → deep purple-lavender edge */}
        <radialGradient id={`${u}a`} cx="36%" cy="54%" r="80%">
          <stop offset="0%"   stopColor="#f028cc"/>
          <stop offset="22%"  stopColor="#cc3cf2"/>
          <stop offset="50%"  stopColor="#8840e0"/>
          <stop offset="78%"  stopColor="#b898f8"/>
          <stop offset="100%" stopColor="#ddd6fe"/>
        </radialGradient>
        {/* Warm coral-peach bloom on right — matches logo warmth */}
        <radialGradient id={`${u}b`} cx="76%" cy="54%" r="42%">
          <stop offset="0%"   stopColor="#ffaacc" stopOpacity="0.75"/>
          <stop offset="100%" stopColor="#ffaacc" stopOpacity="0"/>
        </radialGradient>
        {/* Bright glass specular highlight — top-RIGHT (as in logo) */}
        <radialGradient id={`${u}c`} cx="70%" cy="24%" r="32%">
          <stop offset="0%"   stopColor="var(--card-bg)" stopOpacity="0.9"/>
          <stop offset="60%"  stopColor="var(--card-bg)" stopOpacity="0.25"/>
          <stop offset="100%" stopColor="var(--card-bg)" stopOpacity="0"/>
        </radialGradient>
        {/* Soft bottom depth shadow */}
        <radialGradient id={`${u}d`} cx="50%" cy="90%" r="36%">
          <stop offset="0%"   stopColor="#300060" stopOpacity="0.4"/>
          <stop offset="100%" stopColor="#300060" stopOpacity="0"/>
        </radialGradient>
        <clipPath id={`${u}clip`}><circle cx="50" cy="50" r="49"/></clipPath>
      </defs>

      {/* Layered sphere */}
      <circle cx="50" cy="50" r="49" fill={`url(#${u}a)`}/>
      <circle cx="50" cy="50" r="49" fill={`url(#${u}b)`}/>
      <circle cx="50" cy="50" r="49" fill={`url(#${u}c)`}/>
      <circle cx="50" cy="50" r="49" fill={`url(#${u}d)`}/>

      {/* 4-point sparkle star — large and luminous */}
      <path clipPath={`url(#${u}clip)`}
        d="M50 18 Q51.8 35 59 42 Q76 48 80 50 Q76 52 59 58 Q51.8 65 50 82 Q48.2 65 41 58 Q24 52 20 50 Q24 48 41 42 Q48.2 35 50 18 Z"
        fill="white"/>

      {/* Soft white rim */}
      <circle cx="50" cy="50" r="48.5" fill="none"
        stroke="rgba(255,255,255,0.3)" strokeWidth="1.5"/>
    </svg>
  );
}

// Background reels — Veo 3 outputs from previous campaigns
// ── Home screen ───────────────────────────────────────────────
function HomeScreen({ onStart }: { onStart: () => void }) {
  const [input, setInput] = useState("");
  const [reelIdx, setReelIdx] = useState(0);

  return (
    <div style={{ flex: 1, position: "relative" as const, overflow: "hidden", display: "flex",
      alignItems: "center", justifyContent: "center" }}>

      {/* Background video */}
      <BgVideoPlayer brightness={0.55} saturate={1.2} onIndex={setReelIdx} />

      {/* Dark overlay + purple vignette */}
      <div style={{
        position: "absolute" as const, inset: 0, zIndex: 1,
        background: "linear-gradient(135deg, rgba(7,7,15,0.82) 0%, rgba(13,9,32,0.70) 50%, rgba(7,7,15,0.88) 100%)",
      }} />

      {/* Radial purple glow from center */}
      <div style={{
        position: "absolute" as const, inset: 0, zIndex: 1,
        background: "radial-gradient(ellipse 70% 60% at 50% 50%, rgba(124,58,237,0.12) 0%, transparent 70%)",
        pointerEvents: "none" as const,
      }} />

      {/* Content */}
      <div style={{ position: "relative" as const, zIndex: 2,
        padding: "0 32px", maxWidth: 680, width: "100%", textAlign: "center" as const }}>

        <div style={{ display: "flex", justifyContent: "center", marginBottom: 28 }}>
          <GradientOrb size={72} />
        </div>

        {/* Label chip */}
        <div style={{ display: "inline-flex", alignItems: "center", gap: 6,
          background: "rgba(124,58,237,0.18)", border: "1px solid rgba(124,58,237,0.35)",
          borderRadius: 99, padding: "5px 14px", marginBottom: 20 }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#a78bfa",
            display: "inline-block", boxShadow: "0 0 8px #a78bfa" }} />
          <span style={{ fontSize: 11, fontWeight: 700, color: "#a78bfa", letterSpacing: "0.12em",
            textTransform: "uppercase" as const }}>Powered by Veo 3 · 8 AI Agents</span>
        </div>

        <h1 style={{ fontSize: 44, fontWeight: 900, color: "var(--text-primary)", lineHeight: 1.15,
          marginBottom: 18, letterSpacing: "-0.04em", fontFamily: "inherit" }}>
          Campaign Intelligence,{" "}
          <span style={{
            background: "linear-gradient(135deg, #c084fc 0%, #a78bfa 40%, #818cf8 100%)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
          }}>Creative Excellence</span>
        </h1>

        <p style={{ fontSize: 15, color: "rgba(241,245,249,0.65)", lineHeight: 1.8,
          maxWidth: 520, margin: "0 auto 36px" }}>
          Deploy a coordinated team of AI agents that analyze culture, develop strategy,
          generate creative assets, and prepare content for every marketing channel — all from
          a single campaign brief.
        </p>

        {/* Prompt input */}
        <div style={{ background: "#f1f5f9", border: "1.5px solid rgba(124,58,237,0.30)",
          borderRadius: 18, padding: "18px 22px",
          boxShadow: "0 8px 32px rgba(0,0,0,0.10), 0 0 0 1px rgba(124,58,237,0.12)",
          textAlign: "left" as const, backdropFilter: "blur(16px)" }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
            <span style={{ fontSize: 16, marginTop: 2, color: "#7c3aed" }}>✦</span>
            <textarea
              style={{ flex: 1, border: "none", outline: "none", fontSize: 15, color: "var(--text-primary)",
                resize: "none" as const, background: "transparent", minHeight: 52,
                fontFamily: "inherit", lineHeight: 1.6 }}
              placeholder="e.g. Glenfiddich 12 Year — Diwali gifting for affluent UK audiences..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onStart(); }}}
            />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
            <div style={{ fontSize: 11, color: "rgba(241,245,249,0.35)" }}>⏎ Enter to start · Shift+Enter for newline</div>
            <button onClick={onStart} style={{
              height: 38, padding: "0 20px", borderRadius: 99,
              background: "linear-gradient(135deg, #7c3aed, #6366f1)",
              border: "none", cursor: "pointer", color: "white", fontSize: 13, fontWeight: 700,
              display: "flex", alignItems: "center", gap: 6,
              boxShadow: "0 4px 16px rgba(124,58,237,0.45)",
              transition: "all 0.2s",
            }}>Launch →</button>
          </div>
        </div>

        {/* Reel indicator dots */}
        <div style={{ display: "flex", justifyContent: "center", gap: 6, marginTop: 20 }}>
          {BG_REELS.map((_, i) => (
            <div key={i} onClick={() => setReelIdx(i)}
              style={{ width: i === reelIdx ? 20 : 6, height: 6, borderRadius: 99, cursor: "pointer",
                background: i === reelIdx ? "#a78bfa" : "rgba(255,255,255,0.22)",
                transition: "all 0.3s", boxShadow: i === reelIdx ? "0 0 8px #a78bfa" : "none" }} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────

function Sidebar({ theme, onToggleTheme, view, onNavigate, activeAgentKey, onSelectAgent }: {
  theme: "light" | "dark"; onToggleTheme: () => void;
  view: "app" | "hub" | "agent"; onNavigate: (v: "app" | "hub") => void;
  activeAgentKey: string | null; onSelectAgent: (key: string) => void;
}) {
  return (
    <div style={{ width: 260, flexShrink: 0, height: "100vh",
      background: "transparent",
      display: "flex", flexDirection: "column" as const,
      position: "relative" as const, zIndex: 10, overflow: "hidden" }}>

      {/* Subtle aurora blob — top (light purple on white) */}
      <div style={{ position: "absolute" as const, top: -60, left: -50,
        width: 240, height: 240, borderRadius: "50%", pointerEvents: "none" as const,
        background: "radial-gradient(circle, rgba(168,85,247,0.10) 0%, transparent 65%)",
        animation: "hub-beat 5s ease-in-out infinite" }} />


      {/* Subtle grid */}
      <div style={{ position: "absolute" as const, inset: 0, opacity: 0.025,
        backgroundImage: "linear-gradient(rgba(124,58,237,1) 1px, transparent 1px), linear-gradient(90deg, rgba(124,58,237,1) 1px, transparent 1px)",
        backgroundSize: "36px 36px", pointerEvents: "none" as const }} />

      {/* Logo — orb inline with A2A, tagline stacked below */}
      <div style={{ padding: "28px 20px 24px", position: "relative" as const, zIndex: 2 }}>
        {/* Row: orb + A2A on the same line */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
          <GradientOrb size={46} />
          <span style={{
            fontSize: 30, fontWeight: 900, letterSpacing: "-0.05em", lineHeight: 1,
            background: ORB_BG,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
            filter: "drop-shadow(0 0 6px rgba(124,58,237,0.25))",
          }}>A2A</span>
        </div>
        {/* Tagline — each word on its own line */}
        <div style={{ display: "flex", flexDirection: "column" as const, gap: 4, paddingLeft: 4 }}>
          {["Marketing", "Advertising", "Media"].map(word => (
            <span key={word} style={{
              fontSize: 9, fontWeight: 700, letterSpacing: "0.16em",
              textTransform: "uppercase" as const, color: "var(--text-tertiary)", lineHeight: 1,
            }}>{word}</span>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div style={{ height: 1, margin: "0 20px",
        background: "linear-gradient(90deg, transparent, rgba(124,58,237,0.2), transparent)",
        position: "relative" as const, zIndex: 2 }} />

      {/* Navigation */}
      <div style={{ padding: "16px 16px 0", display: "flex", flexDirection: "column" as const, gap: 4,
        position: "relative" as const, zIndex: 2 }}>
        {([
          { id: "app" as const,  icon: "🏠", label: "Home" },
          { id: "hub" as const,  icon: "📚", label: "Content Hub" },
        ]).map((nav) => (
          <button key={nav.id} onClick={() => onNavigate(nav.id)} style={{
            display: "flex", alignItems: "center", gap: 10, padding: "9px 12px",
            borderRadius: 10, border: "none", cursor: "pointer", fontFamily: "inherit",
            fontSize: 13, fontWeight: 600, textAlign: "left" as const,
            background: view === nav.id ? "var(--sel-bg)" : "transparent",
            color: view === nav.id ? "var(--sel-brd)" : "var(--text-secondary)",
          }}>
            <span style={{ fontSize: 15 }}>{nav.icon}</span>
            {nav.label}
          </button>
        ))}
      </div>

      {/* Agents — flat list, always visible */}
      <div style={{ padding: "4px 16px 0", position: "relative" as const, zIndex: 2 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.1em",
          textTransform: "uppercase" as const, padding: "10px 12px 6px" }}>Agents</div>
      </div>
      <div style={{ flex: 1, overflowY: "auto" as const, display: "flex", flexDirection: "column" as const,
        gap: 2, padding: "0 16px", position: "relative" as const, zIndex: 2 }}>
        {SIDEBAR_AGENT_KEYS.map((key) => {
          const idx   = HARNESS_STAGES.findIndex((s) => s.key === key);
          const stage = HARNESS_STAGES[idx];
          const isActive = view === "agent" && activeAgentKey === key;
          return (
            <button key={key} onClick={() => onSelectAgent(key)} style={{
              display: "flex", alignItems: "center", gap: 10, padding: "8px 12px",
              borderRadius: 10, border: "none", cursor: "pointer", fontFamily: "inherit",
              fontSize: 13, fontWeight: 600, textAlign: "left" as const,
              background: isActive ? "var(--sel-bg)" : "transparent",
              color: isActive ? "var(--sel-brd)" : "var(--text-secondary)",
            }}>
              <img src={AGENT_AVATARS[idx] ?? stage.icon} alt={stage.label}
                style={{ width: 22, height: 22, borderRadius: 6, objectFit: "cover", flexShrink: 0 }} />
              {stage.label}
            </button>
          );
        })}
      </div>

      {/* Theme toggle */}
      <div style={{ padding: "0 20px 12px", position: "relative" as const, zIndex: 2 }}>
        <button onClick={onToggleTheme} style={{
          width: "100%", display: "flex", alignItems: "center", gap: 8,
          padding: "8px 12px", borderRadius: 10,
          border: "1px solid var(--card-border)", background: "var(--card-bg-soft)",
          color: "var(--text-secondary)", fontSize: 12, fontWeight: 600,
          cursor: "pointer", fontFamily: "inherit",
        }}>
          <span style={{ fontSize: 14 }}>{theme === "light" ? "🌙" : "☀️"}</span>
          {theme === "light" ? "Dark mode" : "Light mode"}
        </button>
      </div>

      {/* Powered by Infosys Aster */}
      <div style={{ padding: "14px 20px", borderTop: "1px solid var(--card-border)",
        position: "relative" as const, zIndex: 2 }}>
        <AsterLogo size={0.62} />
      </div>
    </div>
  );
}

// ── Steps panel ───────────────────────────────────────────────
// All 7 agents mapped to their workflow stage
const WORKFLOW_STAGES = [
  { id: "brief",    label: "Brief Intake",        agents: ["briefing"] },
  { id: "creative", label: "Creative Direction",  agents: ["culture", "strategy", "copy", "kv", "reel"] },
  { id: "channel",  label: "Channel Adoption",    agents: ["channel"] },
  { id: "activate", label: "Activation",          agents: [] as string[] },
  { id: "perform",  label: "Performance",         agents: ["performance"] },
];

function StepsPanel({ campaignName, activeStageId, agentStatus, liveLog, onEditName }: {
  campaignName: string;
  activeStageId: string | null;
  agentStatus: Record<string, string>;
  liveLog: AgentEvent[];
  onEditName: () => void;
}) {
  const [editing, setEditing]   = useState(false);
  const [nameVal, setNameVal]   = useState(campaignName);
  const [request, setRequest]   = useState("");
  const activeIdx = WORKFLOW_STAGES.findIndex(s => s.id === activeStageId);

  useEffect(() => { setNameVal(campaignName); }, [campaignName]);

  // Latest message for a given agent key
  const agentMsg = (key: string) =>
    [...liveLog].reverse().find(e => e.agent === key && e.status === "running")?.message ?? null;

  return (
    <div style={{ width: 260, flexShrink: 0, height: "100vh", background: "var(--card-bg)",
      borderRight: "1px solid var(--card-border)", display: "flex", flexDirection: "column" as const }}>

      {/* Campaign name header */}
      <div style={{ padding: "18px 18px 14px", borderBottom: "1px solid var(--card-border)",
        display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 26, height: 26, borderRadius: 6, background: "#f1f5f9", flexShrink: 0,
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, color: "var(--text-secondary)" }}>□</div>
        {editing ? (
          <input autoFocus value={nameVal} onChange={e => setNameVal(e.target.value)}
            onBlur={() => { onEditName(); setEditing(false); }}
            onKeyDown={e => { if (e.key === "Enter") { onEditName(); setEditing(false); }}}
            style={{ flex: 1, fontSize: 13, fontWeight: 600, border: "none",
              outline: "1.5px solid #7c3aed", borderRadius: 6, padding: "2px 6px", fontFamily: "inherit",
              background: "#f1f5f9", color: "var(--text-primary)" }} />
        ) : (
          <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: "var(--text-primary)",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const }}>
            {campaignName}
          </span>
        )}
        <button onClick={() => setEditing(true)}
          style={{ background: "none", border: "none", cursor: "pointer",
            color: "var(--text-secondary)", fontSize: 13, padding: 2, flexShrink: 0 }}>✎</button>
      </div>

      {/* Workflow stages — timeline layout */}
      <div style={{ flex: 1, overflowY: "auto" as const, padding: "20px 0 8px" }}>
        {WORKFLOW_STAGES.map((stage, idx) => {
          const isActive    = stage.id === activeStageId;
          const isDone      = activeIdx > idx;
          const isLast      = idx === WORKFLOW_STAGES.length - 1;
          const stageAgents = HARNESS_STAGES.filter(s => stage.agents.includes(s.key));

          return (
            <div key={stage.id} style={{ display: "flex", paddingLeft: 18 }}>
              {/* Left rail: circle + connector line */}
              <div style={{ display: "flex", flexDirection: "column" as const,
                alignItems: "center", width: 26, flexShrink: 0 }}>
                {/* Step circle — A2A gradient for done/active, grey for future */}
                <div style={{
                  width: 24, height: 24, borderRadius: "50%", flexShrink: 0, zIndex: 1,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 10, fontWeight: 700,
                  background: (isDone || isActive)
                    ? ORB_BG
                    : "var(--card-border)",
                  color: (isDone || isActive) ? "white" : "var(--text-tertiary)",
                  border: (isDone || isActive) ? "none" : "1.5px solid rgba(15,23,42,0.14)",
                  boxShadow: isActive ? "0 0 0 4px rgba(124,58,237,0.15)" : "none",
                  transition: "all 0.3s",
                }}>
                  {isDone ? "✓" : idx + 1}
                </div>
                {/* Connector line */}
                {!isLast && (
                  <div style={{
                    width: 1.5, flex: 1, minHeight: 20, marginTop: 2,
                    background: isDone
                      ? "linear-gradient(rgba(124,58,237,0.5), rgba(167,139,250,0.2))"
                      : "var(--card-border)",
                    transition: "background 0.4s",
                  }} />
                )}
              </div>

              {/* Right content */}
              <div style={{ flex: 1, paddingLeft: 12, paddingBottom: isLast ? 0 : 20, paddingRight: 18 }}>
                {/* Stage label */}
                <div style={{
                  fontSize: 13, fontWeight: isActive ? 700 : 500, paddingTop: 3,
                  color: isActive ? "var(--text-primary)" : isDone ? "var(--text-muted)" : "var(--text-tertiary)",
                  marginBottom: (isDone || isActive) && stageAgents.length > 0 ? 10 : 0,
                }}>
                  {stage.label}
                </div>

                {/* Agents — active/done stage */}
                {stageAgents.length > 0 && (isDone || isActive) && (
                  <div style={{ display: "flex", flexDirection: "column" as const, gap: 2 }}>
                    {stageAgents.map(s => {
                      const st      = agentStatus[s.key];
                      const isRun   = st === "running";
                      const isDoneA = st === "done";
                      const msg     = isRun ? agentMsg(s.key) : null;
                      return (
                        <div key={s.key} style={{ marginBottom: isRun && msg ? 6 : 2 }}>
                          {/* Agent row */}
                          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "3px 0" }}>
                            <span style={{
                              fontSize: 11, width: 14, textAlign: "center" as const, flexShrink: 0,
                              color: isDoneA ? "#7c3aed" : isRun ? "#7c3aed" : "rgba(15,23,42,0.18)",
                              fontWeight: 700,
                            }}>✦</span>
                            <span style={{
                              fontSize: 12, flex: 1, lineHeight: 1.3,
                              fontWeight: isRun ? 600 : 400,
                              color: isDoneA ? "var(--text-secondary)" : isRun ? "#a78bfa" : "var(--text-secondary)",
                            }}>
                              {s.label}
                            </span>
                            {isDoneA && (
                              <span style={{ fontSize: 11, color: "#10b981", fontWeight: 700, flexShrink: 0 }}>✓</span>
                            )}
                            {isRun && (
                              <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
                                {[0,1,2].map(d => (
                                  <div key={d} style={{ width: 3, height: 3, borderRadius: "50%",
                                    background: "#7c3aed",
                                    animation: `wave-dot 1.2s ${d * 0.2}s ease-in-out infinite` }} />
                                ))}
                              </div>
                            )}
                          </div>
                          {/* Live message — shown below running agent */}
                          {isRun && msg && (
                            <div style={{
                              marginTop: 4, marginLeft: 20, fontSize: 11,
                              color: "var(--text-secondary)", lineHeight: 1.55,
                              display: "-webkit-box", WebkitLineClamp: 3,
                              WebkitBoxOrient: "vertical" as const, overflow: "hidden",
                            }}>
                              {msg}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Agents — future/inactive stage */}
                {stageAgents.length > 0 && !isDone && !isActive && (
                  <div style={{ display: "flex", flexDirection: "column" as const, gap: 2 }}>
                    {stageAgents.map(s => (
                      <div key={s.key} style={{ display: "flex", alignItems: "center", gap: 6, padding: "3px 0" }}>
                        <span style={{ fontSize: 11, width: 14, textAlign: "center" as const,
                          color: "rgba(15,23,42,0.15)", fontWeight: 700, flexShrink: 0 }}>✦</span>
                        <span style={{ fontSize: 12, color: "#334155" }}>{s.label}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Request input */}
      <div style={{ padding: "12px 14px", borderTop: "1px solid var(--card-border)" }}>
        <div style={{ background: "var(--page-bg)", border: "1px solid var(--card-border)", borderRadius: 12, padding: "10px 12px" }}>
          <textarea placeholder="Describe your request..." value={request}
            onChange={e => setRequest(e.target.value)}
            style={{ width: "100%", border: "none", outline: "none", background: "transparent",
              fontSize: 12, color: "var(--text-tertiary)", resize: "none" as const,
              fontFamily: "inherit", lineHeight: 1.5, minHeight: 36, maxHeight: 72 }} />
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
            <div style={{ width: 24, height: 24, borderRadius: "50%", border: "1.5px solid var(--card-border)",
              background: "var(--card-bg)", display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 13, cursor: "pointer", color: "var(--text-tertiary)" }}>+</div>
            <button style={{
              width: 30, height: 30, borderRadius: "50%",
              background: request.trim() ? "#7c3aed" : "rgba(15,23,42,0.06)",
              border: "none", cursor: request.trim() ? "pointer" : "default",
              color: "white", fontSize: 14,
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "background 0.2s",
            }}>→</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────
export default function App() {
  const { state, startFullCampaign, reset } = usePipeline();
  const { theme, toggleTheme } = useTheme();
  const [view, setView] = useState<"app" | "hub" | "agent">("app");
  const [activeAgentKey, setActiveAgentKey] = useState<string | null>(null);
  const [campaignPrompt, setCampaignPrompt] = useState("");

  const [wizardStarted, setWizardStarted]   = useState(true);
  const [campaignName,  setCampaignName]    = useState("New Campaign");
  const [briefData,     setBriefData]       = useState<import("./types/pipeline").HarnessBriefRequest | null>(null);

  const handleReset = () => {
    reset();
    setWizardStarted(false);
    setCampaignName("New Campaign");
  };

  const handleLaunch = (brief: import("./types/pipeline").HarnessBriefRequest) => {
    if (brief.campaign_name?.trim()) setCampaignName(brief.campaign_name.trim());
    setBriefData(brief);
    startFullCampaign(brief);
  };

  // Derive which workflow stage is currently active
  const activeStageId = (() => {
    if (state.status === "idle") return wizardStarted ? "brief" : null;
    if (state.status === "running") {
      const as = state.agentStatus;
      if (["performance"].some(k => as[k] === "running" || as[k] === "done")) return "perform";
      if (["channel"].some(k => as[k] === "running" || as[k] === "done")) return "channel";
      if (["culture","strategy","copy","kv","reel"].some(k => as[k] === "running" || as[k] === "done")) return "creative";
      return "brief";
    }
    if (state.status === "done") return "activate";
    return null;
  })();

  return (
    <ErrorBoundary>
      {view === "agent" && (
        <>
          <BgVideoPlayer fixed brightness={0.6} saturate={1.05} />
          <div style={{ position: "fixed" as const, inset: 0, zIndex: 0, pointerEvents: "none" as const,
            background: "var(--video-wash)" }} />
        </>
      )}
      <div style={{ display: "flex", height: "100vh", overflow: "hidden",
        position: "relative" as const, zIndex: 1,
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif" }}>

        {/* Left: Sidebar */}
        <Sidebar theme={theme} onToggleTheme={toggleTheme} view={view} onNavigate={setView}
          activeAgentKey={activeAgentKey}
          onSelectAgent={(key) => { setActiveAgentKey(key); setView("agent"); }} />

        {view === "hub" ? (
          <ContentHub onStartCampaign={() => setView("app")} />
        ) : view === "agent" && activeAgentKey ? (
          <AgentProfile key={activeAgentKey} agentKey={activeAgentKey}
            prompt={campaignPrompt} onPromptChange={setCampaignPrompt} />
        ) : (
        <>
        {/* Middle: Steps panel — hidden during wakeup (before any agent starts) */}
        {(state.status === "running" || state.status === "done") &&
          !(state.status === "running" && !state.agentStatus["briefing"]) && (
          <StepsPanel
            campaignName={campaignName}
            activeStageId={activeStageId}
            agentStatus={state.agentStatus}
            liveLog={state.liveLog}
            onEditName={() => {}}
          />
        )}

        {/* Right: Content area */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column" as const,
          overflow: "hidden", background: "var(--page-bg)" }}>

          {/* Top bar — sidebar toggle on home, breadcrumb during pipeline */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "12px 20px", borderBottom: "1px solid var(--card-border)", flexShrink: 0, minHeight: 52,
            background: "var(--card-bg)", backdropFilter: "blur(12px)" }}>
            {/* Left: sidebar toggle icon */}
            <button style={{ width: 32, height: 32, borderRadius: 8, border: "1px solid rgba(255,255,255,0.10)",
              background: "var(--card-bg)", cursor: "pointer", display: "flex", alignItems: "center",
              justifyContent: "center", color: "var(--text-tertiary)", flexShrink: 0 }}>
              <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <rect x={3} y={3} width={7} height={18} rx={1}/><rect x={14} y={3} width={7} height={18} rx={1}/>
              </svg>
            </button>

            {/* Right: pipeline title + action buttons — hidden on wakeup screen */}
            {(state.status === "running" || state.status === "done") &&
              !(state.status === "running" && !state.agentStatus["briefing"]) && (
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                {/* <h2 style={{ fontSize: 15, fontWeight: 600, color: "#111827", margin: 0 }}>
                  {state.status === "running"
                    ? (WORKFLOW_STAGES.find(s => s.id === activeStageId)?.label ?? "Running")
                    : "Campaign Ready ✅"}
                </h2> */}
                {/* <div style={{ display: "flex", gap: 10 }}>
                    {state.status === "done" && (
                      <button style={{ display: "flex", alignItems: "center", gap: 6,
                        padding: "7px 16px", borderRadius: 8, border: "none", cursor: "pointer",
                        background: "linear-gradient(135deg, #7c3aed, #a855f7)",
                        color: "white", fontSize: 13, fontWeight: 700, fontFamily: "inherit" }}>
                        ✓ Accept
                      </button>
                    )}
                    <button onClick={handleReset}
                      style={{ padding: "7px 16px", borderRadius: 8, border: "1.5px solid #e5e7eb",
                        cursor: "pointer", background: "white", color: "var(--text-secondary)",
                        fontSize: 13, fontWeight: 600, fontFamily: "inherit" }}>
                      Cancel
                    </button>
                  </div> */}
              </div>
            )}
          </div>

          {/* Content */}
          <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" as const }}>
            {state.status === "idle" && !wizardStarted && (
              <HomeScreen onStart={() => setWizardStarted(true)} />
            )}

            {state.status === "idle" && wizardStarted && (
              <>
                <BgVideoPlayer fixed brightness={0.55} saturate={0.9} />
                <div style={{ position: "fixed" as const, inset: 0, zIndex: 1,
                  pointerEvents: "none" as const, background: "var(--video-wash)" }} />
                <div style={{ position: "relative" as const, zIndex: 2, flex: 1, display: "flex",
                  flexDirection: "column" as const, overflow: "hidden" }}>
                  <CampaignForm onFullCampaign={handleLaunch} />
                </div>
              </>
            )}

            {/* Agent network wakeup — shown immediately after launch, before Logos starts */}
            {state.status === "running" && activeStageId === "brief" &&
              !state.agentStatus["briefing"] && (
              <AgentNetworkWakeUp />
            )}

            {/* Logos (briefing agent) intake view */}
            {state.status === "running" && activeStageId === "brief" &&
              !!state.agentStatus["briefing"] && (
              <BriefIntakeView
                brief={briefData}
                milestone={state.milestones["briefing"]}
                liveMsg={[...state.liveLog].reverse().find(e => e.agent === "briefing" && e.status === "running")?.message ?? null}
                agentDone={state.agentStatus["briefing"] === "done"}
              />
            )}

            {state.status === "running" && activeStageId !== "brief" && (() => {
              // Prioritise agentStatus so we get the right agent the instant it
              // starts, even before any liveLog entries have arrived for it.
              const focusKey =
                HARNESS_STAGES.find(s => state.agentStatus[s.key] === "running")?.key
                ?? [...state.liveLog].reverse().find(e => e.status === "running")?.agent
                ?? [...state.liveLog].reverse().find(e => e.status === "done")?.agent
                ?? null;
              const liveMsg = (key: string) =>
                [...state.liveLog].reverse().find(e => e.agent === key && e.status === "running")?.message ?? null;

              if (focusKey === "strategy") return (
                <StrategyIntakeView
                  milestone={state.milestones["strategy"]}
                  liveMsg={liveMsg("strategy")}
                />
              );
              if (focusKey === "copy") return (
                <CopyIntakeView
                  milestone={state.milestones["copy"]}
                  liveMsg={liveMsg("copy")}
                />
              );
              if (focusKey === "culture") return (
                <CultureIntakeView
                  milestone={state.milestones["culture"]}
                  liveMsg={liveMsg("culture")}
                />
              );
              if (focusKey === "kv") return (
                <KVIntakeView
                  milestone={state.milestones["kv"]}
                  liveMsg={liveMsg("kv")}
                  reelMilestone={state.milestones["reel"]}
                  agentDone={state.agentStatus["kv"] === "done"}
                />
              );
              if (focusKey === "reel") return (
                <ReelIntakeView
                  milestone={state.milestones["reel"]}
                  liveMsg={liveMsg("reel")}
                />
              );
              if (focusKey === "channel") return (
                <ChannelAdapterIntakeView
                  milestone={state.milestones["channel"]}
                  liveMsg={liveMsg("channel")}
                />
              );
              if (focusKey === "performance") return (
                <PerformanceIntakeView
                  milestone={state.milestones["performance"]}
                  liveMsg={liveMsg("performance")}
                />
              );
              // fallback (focusKey null)
              return (
                <RunningView
                  agentStatus={state.agentStatus}
                  liveLog={state.liveLog}
                  milestones={state.milestones}
                  compact={true}
                  brand={briefData?.brand}
                />
              );
            })()}

            {state.status === "error" && (() => {
              const isAuth = state.error?.includes("credentials") || state.error?.includes("auth");
              return (
                <div style={styles.errorPage}>
                  <div style={styles.errorCard}>
                    <div style={styles.errorTitle}>⚠️ Pipeline Error</div>
                    <div style={styles.errorMsg}>{state.error}</div>
                    {isAuth && (
                      <div style={styles.authHint}>
                        <strong>Fix:</strong> Run this in your terminal, then restart the harness:
                        <pre style={styles.authCmd}>gcloud auth application-default login</pre>
                      </div>
                    )}
                    <button className="reset-btn" onClick={handleReset} style={{ marginTop: 20 }}>Try Again</button>
                  </div>
                </div>
              );
            })()}

            {state.status === "done" && (
              <ResultsView
                output={state.pipeline_output}
                campaignId={state.campaign_id}
              />
            )}
          </div>
        </div>
        </>
        )}
      </div>
    </ErrorBoundary>
  );
}

// ── Styles ───────────────────────────────────────────────────
const styles: Record<string, React.CSSProperties> = {
  // Running
  // ── Infosys Aster light theme ──────────────────────────────

  runningPage: {
    minHeight: "100vh", display: "flex", flexDirection: "column" as const,
    alignItems: "center", background: "var(--page-bg)", padding: 0,
  },
  runningCard: {
    background: "var(--card-bg)", border: "1px solid rgba(255,255,255,0.09)",
    borderRadius: 16, padding: "40px 48px", maxWidth: 560, width: "100%",
    boxShadow: "0 4px 24px rgba(0,0,0,0.09)", backdropFilter: "blur(8px)", marginTop: 40,
  },
  runningTitle: {
    fontSize: 22, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8,
  },
  runningSubtitle: {
    fontSize: 14, color: "var(--text-tertiary)", marginBottom: 32, lineHeight: 1.6,
  },
  stageList: { display: "flex", flexDirection: "column", gap: 12 },
  stageIcon: { fontSize: 20, width: 32, flexShrink: 0 },
  stageInfo: { flex: 1 },
  stageName: { fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" },
  stageDesc: { fontSize: 12, color: "var(--text-secondary)", marginTop: 2 },

  // Results
  resultsPage: {
    minHeight: "100vh", background: "var(--page-bg)",
  },
  resultsHero: {
    background: "var(--card-bg-translucent)",
    borderBottom: "1px solid var(--card-border)",
    padding: "20px 32px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.07)",
    backdropFilter: "blur(12px)",
  },
  resultsHeroInner: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    maxWidth: 1200, margin: "0 auto",
  },
  resultsTitle: { fontSize: 18, fontWeight: 700, color: "var(--text-primary)" },
  campaignIdTag: {
    fontSize: 11, color: "var(--text-secondary)", marginTop: 3, fontFamily: "monospace",
    letterSpacing: "0.05em",
  },
  resultsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 20,
    maxWidth: 1200,
    margin: "24px auto",
    padding: "0 32px",
  },
  resultCard: {
    background: "var(--card-bg)", border: "1px solid rgba(255,255,255,0.09)",
    borderRadius: 14, padding: 22,
    boxShadow: "0 4px 20px rgba(0,0,0,0.09)",
    backdropFilter: "blur(8px)",
  },
  cardHeader: { fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 14 },
  cardRow: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  cardLabel: { fontSize: 11, color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "0.06em" },
  cardValue: { fontSize: 13, color: "var(--text-secondary)" },
  cardText: { fontSize: 13, color: "var(--text-tertiary)", lineHeight: 1.6, marginTop: 12 },
  badge: {
    fontSize: 11, fontWeight: 700, padding: "3px 10px",
    borderRadius: 20, textTransform: "uppercase" as const,
  },
  bigIdea: {
    fontSize: 20, fontWeight: 700, color: "#7c3aed",
    fontStyle: "italic", lineHeight: 1.5, marginBottom: 16,
  },
  copyGrid: { display: "flex", flexDirection: "column" as const, gap: 16 },
  copyBlock: {},
  copyLabel: { fontSize: 10, fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" as const, marginBottom: 6, letterSpacing: "0.08em" },
  copyText: { fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6 },
  expandBtn: {
    background: "none", border: "none", color: "var(--text-secondary)", fontSize: 12,
    cursor: "pointer", padding: 0, marginBottom: 12,
  },
  jsonPre: {
    fontSize: 11, color: "var(--text-tertiary)", background: "rgba(255,255,255,0.03)",
    border: "1px solid var(--card-border)",
    borderRadius: 8, padding: 16, overflowX: "auto" as const,
    whiteSpace: "pre-wrap" as const, maxHeight: 400, overflowY: "auto" as const,
  },

  // Error
  errorPage: {
    minHeight: "100vh", display: "flex", alignItems: "center",
    justifyContent: "center", background: "var(--page-bg)",
  },
  errorCard: {
    background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.25)",
    borderRadius: 16, padding: 40, maxWidth: 480, textAlign: "center" as const,
    boxShadow: "0 4px 24px rgba(239,68,68,0.12)", backdropFilter: "blur(8px)",
  },
  errorTitle: { fontSize: 20, fontWeight: 700, color: "#f87171", marginBottom: 12 },
  errorMsg: { fontSize: 14, color: "#fca5a5", lineHeight: 1.6 },
  authHint: { marginTop: 16, fontSize: 13, color: "var(--text-tertiary)", lineHeight: 1.6, textAlign: "left" as const },
  authCmd: { marginTop: 8, background: "var(--card-bg)", border: "1px solid rgba(255,255,255,0.09)", padding: "10px 14px", borderRadius: 8, fontSize: 12, color: "#a78bfa", fontFamily: "monospace" },
};
