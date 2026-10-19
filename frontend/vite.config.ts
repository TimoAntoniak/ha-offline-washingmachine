import { defineConfig } from "vite";

export default defineConfig(({ mode }) => ({
  build: {
    target: "es2022",
    outDir: "../custom_components/offline_laundry/frontend",
    emptyOutDir: true,
    minify: mode !== "development",
    sourcemap: mode === "development" ? "inline" : false,
    lib: {
      entry: "src/offline-laundry-card.ts",
      formats: ["es"],
      fileName: () => "offline-laundry-card.js",
    },
  },
}));
