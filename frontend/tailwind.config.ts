import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        "sidebar-bg": "var(--sidebar-bg)",
        "input-bg": "var(--input-bg)",
        "border-subtle": "var(--border-subtle)",
        accent: "var(--accent)",
        "accent-hover": "var(--accent-hover)",
      },
      maxWidth: {
        chat: "768px",
      },
    },
  },
  plugins: [],
};
export default config;
