import { defineConfig, loadEnv } from "vite";
import { visualizer } from "rollup-plugin-visualizer";

// Bundle size budgets (bytes)
const CHUNK_WARN_LIMIT = 300 * 1024;  // 300 kB
const CHUNK_ERROR_LIMIT = 500 * 1024; // 500 kB

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const isAnalyze = mode === "analyze";
  const isProd = mode === "production" || mode === "analyze";

  return {
    // ── Output ─────────────────────────────────────────────────────────────
    build: {
      outDir: "dist",
      emptyOutDir: true,

      // Deterministic asset naming for cache-busting
      rollupOptions: {
        output: {
          // Entry chunk
          entryFileNames: "assets/[name]-[hash].js",
          // Dynamic/split chunks
          chunkFileNames: "assets/[name]-[hash].js",
          // Static assets (images, fonts, etc.)
          assetFileNames: "assets/[name]-[hash][extname]",

          // Manual chunk splitting: isolate large vendor libs
          manualChunks(id) {
            if (id.includes("node_modules")) {
              return "vendor";
            }
          },
        },
      },

      // Sourcemaps: full for dev/staging, hidden (no public URL) for prod
      sourcemap: isProd ? "hidden" : true,

      // Warn / fail on oversized chunks
      chunkSizeWarningLimit: CHUNK_WARN_LIMIT / 1024, // vite expects kB

      // Minify in production
      minify: isProd ? "esbuild" : false,

      // Target modern browsers only (drops legacy polyfills)
      target: ["es2020", "chrome100", "firefox100", "safari15"],
    },

    // ── Plugins ────────────────────────────────────────────────────────────
    plugins: [
      // Bundle size visualizer – only during `npm run analyze`
      isAnalyze &&
        visualizer({
          open: true,
          filename: "dist/bundle-report.html",
          gzipSize: true,
          brotliSize: true,
        }),
    ].filter(Boolean),

    // ── Dev server ─────────────────────────────────────────────────────────
    server: {
      port: parseInt(env.VITE_DEV_PORT || "5173", 10),
      strictPort: true,
      // Expose on all interfaces when running inside a container
      host: env.VITE_DEV_HOST || "localhost",
    },

    // ── Preview (post-build) ───────────────────────────────────────────────
    preview: {
      port: parseInt(env.VITE_PREVIEW_PORT || "4173", 10),
      strictPort: true,
      host: env.VITE_PREVIEW_HOST || "localhost",
    },

    // ── Env prefix ────────────────────────────────────────────────────────
    envPrefix: "VITE_",
  };
});
