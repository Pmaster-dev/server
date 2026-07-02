import { defineConfig, devices } from "@playwright/test";

// The base URL used for smoke tests.
// In CI the preview server is started on VITE_PREVIEW_PORT (default 4173).
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:4173";

export default defineConfig({
  testDir: "tests/webview",
  testMatch: "**/*.spec.{js,ts}",

  // Fail fast in CI; allow retries locally
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // Detailed reporter in CI (list + HTML); interactive otherwise
  reporter: process.env.CI
    ? [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]]
    : [["html", { outputFolder: "playwright-report", open: "on-failure" }]],

  use: {
    baseURL: BASE_URL,
    // Always run headless; pass PLAYWRIGHT_HEADED=1 locally to override
    headless: process.env.PLAYWRIGHT_HEADED !== "1",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    trace: "retain-on-failure",
  },

  projects: [
    // Primary: Chromium (covers Electron-based webviews)
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    // Secondary: Firefox
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    // Optional: WebKit / Safari – skipped on BSD if binary unavailable
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
  ],

  // Start the Vite preview server before the test run
  webServer: {
    command: "npm run preview",
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
