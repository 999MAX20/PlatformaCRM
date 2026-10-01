import type { Config } from "tailwindcss";
import plugin from "tailwindcss/plugin";
import palette from "./src/theme/semantic-tokens.json";

type Token = keyof typeof palette.tokens;
const color = (token: Token) => `rgb(var(--color-${token.replaceAll(".", "-")}-rgb) / <alpha-value>)`;
const brand = {
  50: color("brand.soft"),
  100: color("brand.border"),
  200: color("brand.border"),
  300: color("brand.accent"),
  500: color("brand.default"),
  600: color("brand.hover"),
  700: color("brand.content"),
  800: color("brand.pressed"),
  900: color("brand.pressed"),
};

// One versioned value source for CSS, Tailwind and alpha-modified utilities.
const semanticVariables = Object.fromEntries(
  Object.entries(palette.tokens).flatMap(([name, value]) => {
    const variable = `--color-${name.replaceAll(".", "-")}`;
    const entries = [[variable, value]];
    if (/^#[0-9a-f]{6}$/i.test(value)) {
      entries.push([`${variable}-rgb`, [1, 3, 5].map((offset) => parseInt(value.slice(offset, offset + 2), 16)).join(" ")]);
    }
    return entries;
  }),
);

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        platforma: {
          bg: color("surface.canvas"),
          page: color("surface.canvas"),
          surface: color("surface.default"),
          surfaceWarm: color("surface.subtle"),
          card: color("surface.default"),
          muted: color("text.muted"),
          mutedSoft: color("text.muted"),
          border: color("border.default"),
          control: color("border.control"),
          text: color("text.primary"),
          ink: color("text.primary"),
          subtle: color("text.secondary"),
          faint: color("text.muted"),
          primary: color("brand.default"),
          secondary: color("ai.content"),
          success: color("success.content"),
          warning: color("warning.content"),
          warningSoft: color("warning.soft"),
          danger: color("danger.content"),
          dangerSoft: color("danger.soft"),
          info: color("info.content"),
        },
        disabled: {
          surface: color("disabled.surface"),
          content: color("disabled.content"),
          border: color("disabled.border"),
        },
        primary: brand,
        brand,
        ai: {
          50: color("ai.soft"),
          100: "#DDD2FF",
          500: color("ai.content"),
          600: color("ai.content"),
          700: color("ai.hover"),
        },
        discovery: {
          50: "#EEF2FF",
          100: "#C7D2FE",
          600: "#4F46E5",
          700: "#4338CA",
        },
        surface: {
          DEFAULT: color("surface.canvas"),
          page: color("surface.canvas"),
          muted: color("surface.subtle"),
          card: color("surface.default"),
          warm: color("surface.subtle"),
          hover: color("surface.hover"),
        },
        ink: color("text.primary"),
        midnight: color("text.primary"),
      },
      boxShadow: {
        soft: "0 1px 3px rgba(23, 32, 30, 0.06)",
        card: "0 4px 12px rgba(23, 32, 30, 0.05)",
        panel: "0 12px 28px rgba(23, 32, 30, 0.10)",
        glow: "0 12px 32px rgba(0, 122, 89, 0.18)",
        premium: "0 10px 15px rgba(23, 32, 30, 0.10)",
        "platforma-card": "0 4px 12px rgba(23, 32, 30, 0.05)",
      },
      fontSize: {
        "crm-caption": ["0.75rem", { lineHeight: "1rem" }],
        "crm-body": ["0.875rem", { lineHeight: "1.25rem" }],
        "crm-section": ["1.125rem", { lineHeight: "1.5rem" }],
        "crm-title": ["1.5rem", { lineHeight: "2rem" }],
      },
      borderRadius: {
        control: "0.625rem",
        card: "0.75rem",
        "2xl": "0.75rem",
        "3xl": "1rem",
      },
      backgroundImage: {
        "primary-gradient": "linear-gradient(135deg, var(--color-brand-default) 0%, var(--color-brand-hover) 100%)",
        "dashboard-gradient": "linear-gradient(135deg, var(--color-surface-default) 0%, var(--color-surface-subtle) 100%)",
        "ai-gradient": "linear-gradient(135deg, var(--color-ai-content) 0%, var(--color-ai-hover) 100%)",
        "sidebar-depth":
          "linear-gradient(180deg, var(--color-surface-default) 0%, var(--color-surface-canvas) 100%)",
        "soft-mesh":
          "linear-gradient(180deg, var(--color-surface-canvas) 0%, var(--color-surface-subtle) 100%)",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        slideDown: {
          "0%": { opacity: "0", transform: "translateY(-10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        shimmer: "shimmer 1.8s infinite",
        "slide-down": "slideDown 180ms ease-out",
      },
    },
  },
  plugins: [plugin(({ addBase }) => addBase({ ":root": semanticVariables }))],
} satisfies Config;
