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
        cream: "#f7f1e8",
        sand: "#e8dcc8",
        cedar: "#8b3a2b",
        ink: "#2a241c",
        sea: "#1f4e5f",
      },
      fontFamily: {
        display: ["var(--font-display)", "Fraunces", "Georgia", "serif"],
        sans: ["var(--font-sans)", "Source Sans 3", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
