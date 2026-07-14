export interface BrandVoice {
  id: string;
  name: string;
  description: string;
  traits: string[];
  exampleSnippet: string;
}

export const VOICE_STORAGE_KEY = "brandhub_voices";

export const DEFAULT_VOICES: BrandVoice[] = [
  {
    id: "dv1",
    name: "Friendly & Warm",
    description: "Approachable, knowledgeable and clear. We sound like a helpful expert who genuinely cares about our audience.",
    traits: ["Helpful", "Clear", "Optimistic"],
    exampleSnippet: "Hi there! We're excited to help you get started. Our team has worked hard to make this as easy as possible for you.",
  },
  {
    id: "dv2",
    name: "Bold & Confident",
    description: "Direct, powerful and assertive. We make bold statements, inspire action and never shy away from ambition.",
    traits: ["Confident", "Bold", "Inspiring"],
    exampleSnippet: "Transform your business today. Don't wait. Seize this opportunity and lead the market.",
  },
  {
    id: "dv3",
    name: "Playful & Creative",
    description: "Fun, energetic and imaginative. We use wordplay, humour and creativity to make our brand stand out.",
    traits: ["Fun", "Energetic", "Imaginative"],
    exampleSnippet: "Colour outside the lines. Break the rules. Make something the world has never seen before.",
  },
  {
    id: "dv4",
    name: "Warm & Empathetic",
    description: "Compassionate, understanding and supportive. We create a safe space where our audience feels heard.",
    traits: ["Caring", "Gentle", "Understanding"],
    exampleSnippet: "We know this journey can feel overwhelming. You're not alone in this — we're here every step of the way.",
  },
];
