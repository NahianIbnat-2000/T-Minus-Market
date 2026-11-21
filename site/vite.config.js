import { resolve } from "node:path";
import { defineConfig } from "vite";

// GitHub Pages serves the site at /<repo-name>/. Change BASE if the repository is renamed.
const BASE = process.env.SITE_BASE ?? "/T-Minus-Market/";

export default defineConfig({
  base: BASE,
  // site/data/ (written by pipeline/07_export_site_data.py) is served as-is at the site root.
  publicDir: "data",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: { input: { main: resolve(__dirname, "index.html"), methods: resolve(__dirname, "methods.html") } },
  },
});
