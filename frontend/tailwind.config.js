/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: { poppins: ["'Poppins'", "sans-serif"] },
      colors: {
        // shadcn CSS variable tokens — required for Radix UI components
        border:      "hsl(var(--border))",
        input:       "hsl(var(--input))",
        ring:        "hsl(var(--ring))",
        background:  "hsl(var(--background))",
        foreground:  "hsl(var(--foreground))",
        "input-background": "hsl(var(--input-background))",
        primary:     { DEFAULT: "hsl(var(--primary))",     foreground: "hsl(var(--primary-foreground))" },
        secondary:   { DEFAULT: "hsl(var(--secondary))",   foreground: "hsl(var(--secondary-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        muted:       { DEFAULT: "hsl(var(--muted))",       foreground: "hsl(var(--muted-foreground))" },
        accent:      { DEFAULT: "hsl(var(--accent))",      foreground: "hsl(var(--accent-foreground))" },
        popover:     { DEFAULT: "hsl(var(--popover))",     foreground: "hsl(var(--popover-foreground))" },
        card:        { DEFAULT: "hsl(var(--card))",        foreground: "hsl(var(--card-foreground))" },
        // Custom Topaz design tokens
        topaz: {
          navy:           "#14248A",
          purple:         "#9b5de5",
          bg:             "#fbfcfe",
          border:         "#d0d0e0",
          muted:          "#8c8ca1",
          text:           "#0f0f0f",
          "light-purple": "#f9f5ff",
        },
      },
      borderRadius: {
        lg:   "var(--radius)",
        md:   "calc(var(--radius) - 2px)",
        sm:   "calc(var(--radius) - 4px)",
        pill: "999px",
        xl:   "0.75rem",
        "2xl":"1rem",
      },
      boxShadow: {
        card: "0px 32px 32px rgba(10,13,18,0.06),0px 5px 2.5px rgba(10,13,18,0.04)",
      },
    },
  },
  plugins: [],
  corePlugins: { preflight: false },
};
