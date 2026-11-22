import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  getMarketAlerts,
  createMarketAlert,
  updateMarketAlert,
  deleteMarketAlert,
  getMarketNotifications,
  markMarketNotificationRead,
} from "../src/services/marketAlerts.js";

// --------------------------------------------------
// Unified Alerts - US-39, US-40, US-41
// --------------------------------------------------

const priceApiSource = readFileSync(
  new URL("../src/features/alerts_api.js", import.meta.url),
  "utf8",
);

const pageSource = readFileSync(
  new URL("../src/pages/Alerts.jsx", import.meta.url),
  "utf8",
);

function mockFetch(data, status = 200) {
  const calls = [];

  const fetchImpl = async (url, options) => {
    calls.push({ url, options });

    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => data,
    };
  };

  return { fetchImpl, calls };
}

// --------------------------------------------------
// US-39: Create Price Alerts
// --------------------------------------------------

test("US-39: price API exports createAlert", () => {
  assert.match(priceApiSource, /export function createAlert/);
});

test("US-39: price alert creation uses POST", () => {
  assert.match(priceApiSource, /method:\s*["']POST["']/);
});

test("US-39: unified page supports price alerts", () => {
  assert.match(pageSource, /Price Threshold/);
  assert.match(pageSource, /Price Above/);
  assert.match(pageSource, /Price Below/);
});

test("US-39: unified page validates positive thresholds", () => {
  assert.match(pageSource, /value <= 0/);
});

test("US-39: unified page prevents default submission", () => {
  assert.match(pageSource, /event\.preventDefault\(\)/);
});

// --------------------------------------------------
// US-40: Manage Price Alerts
// --------------------------------------------------

test("US-40: price API exports getAlerts", () => {
  assert.match(priceApiSource, /export function getAlerts/);
});

test("US-40: price API exports deleteAlert", () => {
  assert.match(priceApiSource, /export function deleteAlert/);
});

test("US-40: price alert deletion uses DELETE", () => {
  assert.match(priceApiSource, /method:\s*["']DELETE["']/);
});

test("US-40: unified page displays saved alerts", () => {
  assert.match(pageSource, /allAlerts\.map/);
});

test("US-40: unified page supports deleting alerts", () => {
  assert.match(pageSource, /handleDelete/);
});

test("US-40: unified page supports loading alerts", () => {
  assert.match(pageSource, /Loading alerts/);
});

test("US-40: price API uses bearer authentication", () => {
  assert.match(priceApiSource, /Bearer \$\{token\}/);
});

test("US-40: price API rejects missing authentication", () => {
  assert.match(
    priceApiSource,
    /Please log in to manage alerts/,
  );
});

// --------------------------------------------------
// US-41: Percentage-Change Alerts
// --------------------------------------------------

test("US-41: GET market alerts sends bearer token", async () => {
  const mock = mockFetch([{ id: 1, ticker: "LMT" }]);

  const result = await getMarketAlerts({
    token: "test-token",
    fetchImpl: mock.fetchImpl,
  });

  assert.equal(mock.calls[0].options.method, "GET");
  assert.ok(mock.calls[0].url.endsWith("/market-alerts"));
  assert.equal(
    mock.calls[0].options.headers.Authorization,
    "Bearer test-token",
  );
  assert.equal(result[0].ticker, "LMT");
});

test("US-41: POST creates percentage alert", async () => {
  const payload = {
    ticker: "LMT",
    threshold_percent: 5,
    direction: "increase",
  };

  const mock = mockFetch({ id: 1, ...payload }, 201);

  const result = await createMarketAlert(payload, {
    token: "test-token",
    fetchImpl: mock.fetchImpl,
  });

  assert.equal(mock.calls[0].options.method, "POST");
  assert.ok(mock.calls[0].url.endsWith("/market-alerts"));

  assert.equal(
    mock.calls[0].options.headers["Content-Type"],
    "application/json",
  );

  assert.deepEqual(
    JSON.parse(mock.calls[0].options.body),
    payload,
  );

  assert.equal(result.id, 1);
});

test("US-41: PATCH updates percentage alert", async () => {
  const mock = mockFetch({
    id: 7,
    is_active: false,
  });

  const result = await updateMarketAlert(
    7,
    { is_active: false },
    {
      token: "test-token",
      fetchImpl: mock.fetchImpl,
    },
  );

  assert.ok(mock.calls[0].url.endsWith("/market-alerts/7"));
  assert.equal(mock.calls[0].options.method, "PATCH");
  assert.equal(result.is_active, false);
});

test("US-41: DELETE handles HTTP 204", async () => {
  const mock = mockFetch(null, 204);

  const result = await deleteMarketAlert(7, {
    token: "test-token",
    fetchImpl: mock.fetchImpl,
  });

  assert.ok(mock.calls[0].url.endsWith("/market-alerts/7"));
  assert.equal(mock.calls[0].options.method, "DELETE");
  assert.equal(result, null);
});

// --------------------------------------------------
// US-41: Notifications
// --------------------------------------------------

test("US-41: GET retrieves notification history", async () => {
  const mock = mockFetch([
    { id: 3, ticker: "RTX", is_read: false },
  ]);

  const result = await getMarketNotifications({
    token: "test-token",
    fetchImpl: mock.fetchImpl,
  });

  assert.ok(mock.calls[0].url.endsWith("/notifications"));
  assert.equal(result[0].is_read, false);
});

test("US-41: PATCH marks notification as read", async () => {
  const mock = mockFetch({
    id: 3,
    is_read: true,
  });

  const result = await markMarketNotificationRead(
    3,
    {
      token: "test-token",
      fetchImpl: mock.fetchImpl,
    },
  );

  assert.ok(
    mock.calls[0].url.endsWith("/notifications/3/read"),
  );

  assert.equal(mock.calls[0].options.method, "PATCH");
  assert.equal(result.is_read, true);
});

// --------------------------------------------------
// Authentication and Error Handling
// --------------------------------------------------

test("US-41: missing token rejects market alert request", async () => {
  await assert.rejects(
    getMarketAlerts({ token: "" }),
    /Please log in/,
  );
});

test("US-41: backend HTTP errors are reported", async () => {
  const mock = mockFetch(
    { detail: "Authentication required." },
    401,
  );

  await assert.rejects(
    getMarketAlerts({
      token: "invalid-token",
      fetchImpl: mock.fetchImpl,
    }),
    /Authentication required/,
  );
});

// --------------------------------------------------
// Unified Frontend Integration
// --------------------------------------------------

test("Unified page loads both alert APIs", () => {
  assert.match(pageSource, /getAlerts\(\)/);
  assert.match(pageSource, /getMarketAlerts\(/);
});

test("Unified page supports both alert types", () => {
  assert.match(pageSource, /Price Threshold/);
  assert.match(pageSource, /Percentage Change/);
});

test("Unified page combines both saved alert lists", () => {
  assert.match(pageSource, /priceAlerts\.map/);
  assert.match(pageSource, /marketAlerts\.map/);
});

test("Unified page supports percentage alert editing", () => {
  assert.match(pageSource, /handleSaveEdit/);
  assert.match(pageSource, /updateMarketAlert/);
});

test("Unified page supports pause and resume", () => {
  assert.match(pageSource, /handleToggle/);
  assert.match(pageSource, /Pause/);
  assert.match(pageSource, /Resume/);
});

test("Unified page provides notification navigation", () => {
  assert.match(pageSource, /to="\/notifications"/);
});
