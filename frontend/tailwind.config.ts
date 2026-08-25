import type { Config } from "tailwindcss";
import colors from "tailwindcss/colors";
import formsPlugin from "@tailwindcss/forms";

const config: Config = {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./node_modules/@tremor/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    transparent: "transparent",
    current: "currentColor",
    extend: {
      colors: {
        tremor: {
          brand: {
            faint: colors.green[50],
            muted: colors.green[100],
            subtle: colors.green[600],
            DEFAULT: colors.green[600],
            emphasis: colors.green[700],
            inverted: colors.white,
          },
          background: {
            muted: colors.gray[50],
            subtle: colors.gray[100],
            DEFAULT: colors.white,
            emphasis: colors.gray[700],
          },
          border: {
            DEFAULT: colors.gray[200],
          },
          ring: {
            DEFAULT: colors.gray[200],
          },
          content: {
            subtle: colors.gray[400],
            DEFAULT: colors.gray[500],
            emphasis: colors.gray[700],
            strong: colors.gray[900],
            inverted: colors.white,
          },
        },
        "dark-tremor": {
          brand: {
            faint: "#0B1F14",
            muted: colors.green[900],
            subtle: colors.green[400],
            DEFAULT: colors.green[400],
            emphasis: colors.green[500],
            inverted: colors.green[950],
          },
          background: {
            muted: "#131A2B",
            subtle: colors.gray[800],
            DEFAULT: colors.gray[900],
            emphasis: colors.gray[300],
          },
          border: {
            DEFAULT: colors.gray[800],
          },
          ring: {
            DEFAULT: colors.gray[800],
          },
          content: {
            subtle: colors.gray[600],
            DEFAULT: colors.gray[500],
            emphasis: colors.gray[200],
            strong: colors.gray[50],
            inverted: colors.gray[950],
          },
        },
        // Tokens semánticos propios (independientes de los de Tremor):
        // reemplazan los bg-slate-*/text-slate-* fijos que tenía la app.
        // Responden al tema (clase "dark" en <html>, ver index.css).
        app: "rgb(var(--color-bg-app) / <alpha-value>)",
        surface: "rgb(var(--color-bg-surface) / <alpha-value>)",
        "surface-hover": "rgb(var(--color-bg-surface-hover) / <alpha-value>)",
        line: "rgb(var(--color-line) / <alpha-value>)",
        "line-strong": "rgb(var(--color-line-strong) / <alpha-value>)",
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        "ink-muted": "rgb(var(--color-ink-muted) / <alpha-value>)",
        "ink-faint": "rgb(var(--color-ink-faint) / <alpha-value>)",
        "danger-surface": "rgb(var(--color-danger-surface) / <alpha-value>)",
        danger: "rgb(var(--color-danger-text) / <alpha-value>)",
        // Acento general de la interfaz — verde fijo (no elegible por el
        // usuario, esa opción se eliminó por decisión de producto).
        // NUNCA usado dentro de los dashboards para no pisar sus colores
        // fijos (ver theme/colors.ts).
        accent: "rgb(var(--color-accent) / <alpha-value>)",
        "accent-emphasis": "rgb(var(--color-accent-emphasis) / <alpha-value>)",
        "accent-subtle": "rgb(var(--color-accent-subtle) / <alpha-value>)",
        // Paletas fijas por dashboard (ver theme/colors.ts para el uso).
        plaguicidas: {
          faint: "#042f2e",
          muted: colors.teal[800],
          subtle: colors.teal[600],
          DEFAULT: colors.teal[500],
          emphasis: colors.teal[400],
        },
        nutrientes: {
          faint: "#431407",
          muted: colors.orange[800],
          subtle: colors.orange[600],
          DEFAULT: colors.orange[500],
          emphasis: colors.orange[400],
        },
      },
      boxShadow: {
        "tremor-input": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        "tremor-card": "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
        "tremor-dropdown": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
        "dark-tremor-input": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        "dark-tremor-card": "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
        "dark-tremor-dropdown": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
      },
      borderRadius: {
        "tremor-small": "0.375rem",
        "tremor-default": "0.5rem",
        "tremor-full": "9999px",
      },
      fontSize: {
        "tremor-label": ["0.75rem", { lineHeight: "1rem" }],
        "tremor-default": ["0.875rem", { lineHeight: "1.25rem" }],
        "tremor-title": ["1.125rem", { lineHeight: "1.75rem" }],
        "tremor-metric": ["1.875rem", { lineHeight: "2.25rem" }],
      },
    },
  },
  safelist: [
    {
      pattern:
        /^(bg|text|border|ring|stroke|fill)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(?:50|100|200|300|400|500|600|700|800|900|950)$/,
      variants: ["hover", "data-[selected]"],
    },
  ],
  plugins: [formsPlugin],
};

export default config;
