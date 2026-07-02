/**
 * Webview smoke tests – headless Playwright suite
 *
 * These tests run against the Vite preview server (`npm run preview`) and
 * verify that the built bundle loads correctly inside a browser context.
 * They are designed to catch catastrophic regressions (blank page, JS errors,
 * missing critical DOM nodes) before a release is promoted.
 */

import { test, expect } from "@playwright/test";

// ──────────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Collect all browser console errors that occurred during the test.
 * @param {import('@playwright/test').Page} page
 * @returns {string[]}
 */
function collectConsoleErrors(page) {
  const errors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      errors.push(msg.text());
    }
  });
  return errors;
}

// ──────────────────────────────────────────────────────────────────────────────
// Suite: bundle integrity
// ──────────────────────────────────────────────────────────────────────────────

test.describe("Bundle integrity", () => {
  test("root page returns HTTP 200", async ({ page }) => {
    const response = await page.goto("/");
    expect(response?.status()).toBe(200);
  });

  test("page title is present and non-empty", async ({ page }) => {
    await page.goto("/");
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title.length).toBeGreaterThan(0);
  });

  test("no uncaught JS errors on initial load", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/");
    // Allow a brief moment for async errors to surface
    await page.waitForTimeout(500);
    expect(errors).toHaveLength(0);
  });

  test("main entry script is loaded", async ({ page }) => {
    // Collect all script tags and verify at least one hashed JS chunk was loaded
    await page.goto("/");
    const scripts = await page.evaluate(() =>
      Array.from(document.querySelectorAll("script[src]")).map((s) => s.src)
    );
    const hashedChunk = scripts.some((src) =>
      /assets\/[^/]+-[a-f0-9]{8}\.js/.test(src)
    );
    expect(hashedChunk).toBe(true);
  });

  test("critical CSS is injected", async ({ page }) => {
    await page.goto("/");
    const links = await page.evaluate(() =>
      Array.from(document.querySelectorAll("link[rel='stylesheet']")).map(
        (l) => l.href
      )
    );
    // Either inline <style> tags or an external stylesheet must be present
    const styles = await page.evaluate(
      () => document.querySelectorAll("style").length
    );
    expect(links.length + styles).toBeGreaterThan(0);
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// Suite: webview navigation
// ──────────────────────────────────────────────────────────────────────────────

test.describe("Webview navigation", () => {
  test("page is interactive within 5 s", async ({ page }) => {
    await page.goto("/");
    // Wait for network idle (all resources fetched)
    await page.waitForLoadState("networkidle", { timeout: 5_000 });
  });

  test("no broken resource requests (4xx/5xx)", async ({ page }) => {
    const failed = [];
    page.on("response", (res) => {
      if (res.status() >= 400) {
        failed.push(`${res.status()} ${res.url()}`);
      }
    });
    await page.goto("/");
    await page.waitForLoadState("networkidle", { timeout: 5_000 });
    expect(failed).toHaveLength(0);
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// Suite: bundle size gate (soft)
// ──────────────────────────────────────────────────────────────────────────────

test.describe("Bundle size gate", () => {
  test("total transferred bytes are within budget (1 MB)", async ({
    page,
  }) => {
    let totalBytes = 0;
    page.on("response", async (res) => {
      try {
        const body = await res.body();
        totalBytes += body.length;
      } catch {
        // ignore responses that can't be read
      }
    });
    await page.goto("/");
    await page.waitForLoadState("networkidle", { timeout: 5_000 });
    // Soft budget: 1 MB uncompressed
    expect(totalBytes).toBeLessThan(1024 * 1024);
  });
});
