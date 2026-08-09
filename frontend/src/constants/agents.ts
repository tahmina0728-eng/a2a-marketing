export const HARNESS_STAGES = [
  { key: "briefing",    icon: "📋", label: "Logos",       desc: "Validating brief & Fan Truth score" },
  { key: "compliance",  icon: "🛡️", label: "Compliance",  desc: "Checking brand profile & regulatory rules" },
  { key: "strategy",    icon: "💡", label: "Helia",       desc: "Building big idea & strategy" },
  { key: "copy",        icon: "✍️", label: "Ideon",       desc: "Writing campaign copy variants" },
  { key: "culture",     icon: "🌍", label: "Aether",      desc: "Researching cultural intelligence" },
  { key: "kv",          icon: "🎨", label: "Morphis",     desc: "Generating key visual with Gemini 3 Pro Image" },
  { key: "reel",        icon: "🎬", label: "Kinetik",     desc: "Generating 6s campaign reel with Veo" },
  { key: "channel",     icon: "📡", label: "Poly",        desc: "Publishing to Instagram, TikTok & more" },
  { key: "performance", icon: "📊", label: "Nexus",       desc: "Forecasting reach, ROAS & channel performance" },
  { key: "tvc",         icon: "🎥", label: "Director",    desc: "Generates a 15s or 30s multi-scene TVC with Veo" },
];

// First 7 agents shown as individual nav entries in the sidebar (Nexus/Performance excluded —
// it's a forecasting stage, not a content-producing creative agent like the other seven).
// "channel" (Poly) removed from AI Agent — it lives under Publishing
export const SIDEBAR_AGENT_KEYS = ["briefing", "strategy", "copy", "culture", "kv", "reel", "tvc"];

export const STANDALONE_SUPPORTED = ["briefing", "strategy", "copy", "culture", "channel", "kv", "reel", "tvc", "email_templates"];

// Card styling for Poly's per-channel results — distinct accent colors so each
// channel reads like its own platform, not a generic key/value list.
export const POLY_CHANNEL_CFG: Record<string, { icon: string; label: string; color: string }> = {
  instagram:     { icon: "📸", label: "Instagram",     color: "#c026d3" },
  tiktok:        { icon: "🎵", label: "TikTok",         color: "#0f172a" },
  email_subject: { icon: "📧", label: "Email Subject",  color: "#0369a1" },
  ooh:           { icon: "🏙️", label: "OOH Billboard",  color: "#d97706" },
};

export const AGENT_INTROS: Record<string, string> = {
  briefing: "Hello! I'm Logos, the campaign briefing agent. Tell me about your brand, market and campaign objectives — I'll validate your brief, score the consumer truth, and prepare everything for the creative team.",
  strategy: "Hi, I'm Helia, your creative strategist. Share your campaign brief and I'll craft your big idea, hero message and creative territory that will guide the whole campaign.",
  copy:     "I'm Ideon, the copy agent. Give me your campaign direction and I'll write compelling headlines, body copy and calls to action — perfectly tuned to your brand voice and audience.",
  culture:  "Hello! I'm Aether, the cultural intelligence agent. I research trends, audience insights and cultural signals to make sure your campaign resonates with the right people at the right moment.",
  kv:       "Hi, I'm Morphis. I generate on-brand key visuals and hero images using Gemini's image model — campaign-ready visuals in seconds, with your logo and headline applied automatically.",
  reel:     "I'm Kinetik, your reel director. Describe your campaign and I'll generate a cinematic 6-second reel using Veo — complete with voiceover, brand overlay and logo.",
  tvc:      "I'm Director. Give me a brief and I'll produce a full TV commercial — I write the script, generate each scene with Veo, and stitch everything into a 15 or 30 second film.",
  channel:  "I'm Poly, the channel adaptation agent. Tell me your campaign and I'll adapt it for every platform — Instagram, TikTok, LinkedIn, email and landing pages.",
  email_templates: "Hi, I'm Mailer! Give me your campaign brief and I'll generate three beautiful email layout variations — Hero, Text-first and Product showcase — ready to send via Mailchimp.",
};

// Gender map based on avatar images:
// Logos=F, Helia=F, Ideon=M, Aether=M, Morphis=M, Kinetik=F, Poly=F, Director=M, Mailer=F
export const AGENT_GENDER: Record<string, "female" | "male"> = {
  briefing:        "female",  // Logos     — red/pink hair
  strategy:        "female",  // Helia     — hijab
  copy:            "male",    // Ideon     — beard
  culture:         "male",    // Aether    — dark hair
  kv:              "male",    // Morphis   — white beard + glasses
  reel:            "female",  // Kinetik   — curly hair + glasses
  channel:         "female",  // Poly      — black bob
  tvc:             "male",    // Director  — no avatar, default male
  email_templates: "female",  // Mailer    — female
};

// Female voice keywords (across macOS, Windows, Chrome, Android)
export const FEMALE_VOICE = /samantha|zira|google uk english female|karen|moira|victoria|amy|emma|joanna|kimberly|salli|ivy|ava|nicole|allison|fiona|catherine|kate|susan|lisa|helen|linda|jessica|anna|julia|hazel|tessa|veena|nora|sara|amelie|ioana/i;

// Male voice keywords — includes Microsoft Windows voices
export const MALE_VOICE   = /microsoft david|microsoft mark|microsoft james|microsoft george|microsoft richard|microsoft sean|google uk english male|daniel|alex|fred|lee|tom|oliver|aaron|brian|matthew|stephen|russell|jorge|diego|martin|thomas|luca|reed|evan|arthur|eddy|albert/i;

export function speakAgentIntro(agentKey: string, onDone?: () => void) {
  const text = AGENT_INTROS[agentKey];
  if (!text || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();

  const gender = AGENT_GENDER[agentKey] ?? "female";

  const doSpeak = () => {
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate = 1.0; utt.volume = 1.0;
    const voices = window.speechSynthesis.getVoices().filter(v => v.lang.startsWith("en"));

    let pick: SpeechSynthesisVoice | undefined;
    if (gender === "female") {
      pick = voices.find(v => FEMALE_VOICE.test(v.name));
      if (!pick) pick = voices.find(v => !MALE_VOICE.test(v.name));
      utt.pitch = 1.15;
    } else {
      pick = voices.find(v => MALE_VOICE.test(v.name));
      if (!pick) pick = voices.find(v => !FEMALE_VOICE.test(v.name));
      utt.pitch = 0.85;
    }

    if (pick) utt.voice = pick;
    if (onDone) utt.onend = onDone;
    window.speechSynthesis.speak(utt);
  };

  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) {
    window.speechSynthesis.onvoiceschanged = () => {
      window.speechSynthesis.onvoiceschanged = null;
      doSpeak();
    };
  } else {
    doSpeak();
  }
}

export const AGENT_COLORS = ["#7c3aed","#06b6d4","#10b981","#f59e0b","#ec4899","#6366f1","#14b8a6","#f43f5e"];
export const AGENT_DESCS  = [
  "Understands your goals, audience, product and campaign objectives",
  "Crafts big ideas and messaging territories that inspire",
  "Writes compelling headlines, copy, scripts and captions",
  "Analyzes cultural trends, insights and audience behaviors",
  "Creates striking key visuals, ad designs and imagery",
  "Produces engaging short videos and reels visually",
  "Adapts content for every platform and channel",
  "Forecasts reach, ROAS and performance before launch",
];

// Local agent logo PNGs downloaded from GCS bucket (agent-logo/).
// Keyed by HARNESS_STAGES index (0=Logos,1=Helia,...,7=Nexus).
// "Kinetic.png" is the filename in the bucket for the Kinetik agent.
export const AGENT_AVATARS: Record<number, string> = {
  0: "/agent-logo/Logo 2.png",   // Logos
  1: "/agent-logo/Helia.png",    // Helia
  2: "/agent-logo/Ideon.png",    // Ideon
  3: "/agent-logo/Aether.png",   // Aether
  4: "/agent-logo/Morphis.png",  // Morphis
  5: "/agent-logo/Kinetic.png",  // Kinetik
  6: "/agent-logo/Poly.png",     // Poly
};
export const avatarUrl = (_label: string, idx: number): string =>
  AGENT_AVATARS[idx] ?? `https://i.pravatar.cc/150?img=${[12,5,32,47,23,68,17,55][idx] ?? 1}`;

export const WORKFLOW_STAGES = [
  { id: "brief",    label: "Brief Intake",        agents: ["briefing"] },
  { id: "creative", label: "Creative Direction",  agents: ["culture", "strategy", "copy", "kv", "reel"] },
  { id: "channel",  label: "Channel Adoption",    agents: ["channel"] },
  { id: "activate", label: "Activation",          agents: [] as string[] },
  { id: "perform",  label: "Performance",         agents: ["performance"] },
];
