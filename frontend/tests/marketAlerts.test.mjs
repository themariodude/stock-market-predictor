
import test from "node:test";
import assert from "node:assert/strict";

import {
  getMarketAlerts,
  createMarketAlert,
  updateMarketAlert,
  deleteMarketAlert,
  getMarketNotifications,
  markMarketNotificationRead,
} from "../src/services/marketAlerts.js";

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

test("GET alerts sends the investor bearer token", async () => {
  const mock = mockFetch([{ id: 1, ticker: "LMT" }]);

  const result = await getMarketAlerts({
    token: "test-token",
    fetchImpl: mock.fetchImpl,
  });

  assert.equal(mock.calls[0].options.method, "GET");
  assert.ok(mock.calls[0].url.endsWith("/alerts"));
  assert.equal(
    mock.calls[0].options.headers.Authorization,
    "Bearer test-token",
  );
  assert.equal(result[0].ticker, "LMT");
});

test("POST creates an alert with JSON data", async () => {
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

test("PATCH updates an existing alert", async () => {
  const mock = mockFetch({
    id: 7,
    is_active: false,
  });

  const result = await updateMarketAlert(
    7,
    { is_active: false },
    { token: "test-token", fetchImpl: mock.fetchImpl },
  );

  assert.ok(mock.calls[0].url.endsWith("/alerts/7"));
  assert.equal(mock.calls[0].options.method, "PATCH");
  assert.equal(result.is_active, false);
});

test("DELETE handles HTTP 204", async () => {
  const mock = mockFetch(null, 204);

  const result = await deleteMarketAlert(7, {
    token: "test-token",
    fetchImpl: mock.fetchImpl,
  });

  assert.ok(mock.calls[0].url.endsWith("/alerts/7"));
  assert.equal(mock.calls[0].options.method, "DELETE");
  assert.equal(result, null);
});

test("GET notifications retrieves investor history", async () => {
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

test("PATCH marks a notification as read", async () => {
  const mock = mockFetch({ id: 3, is_read: true });

  const result = await markMarketNotificationRead(3, {
    token: "test-token",
    fetchImpl: mock.fetchImpl,
  });

  assert.ok(
    mock.calls[0].url.endsWith("/notifications/3/read"),
  );
  assert.equal(mock.calls[0].options.method, "PATCH");
  assert.equal(result.is_read, true);
});

test("Missing authentication token rejects the request", async () => {
  await assert.rejects(
    getMarketAlerts({ token: "" }),
    /Please log in/,
  );
});

test("Backend HTTP errors are reported", async () => {
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
