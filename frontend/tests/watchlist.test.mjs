import assert from "node:assert/strict";
import test from "node:test";

import { loadWatchlist } from "../src/services/watchlist.js";

function response(data, status = 200) {
  return { ok: status === 200, status, json: async () => data };
}

test("loads only the authenticated investor's favorites in saved order", async () => {
  const requests = [];
  const controller = new AbortController();
  const stocks = await loadWatchlist("investor-token", {
    signal: controller.signal,
    fetchImpl: async (url, options) => {
      requests.push({ url, options });
      return url.endsWith("/auth/me")
        ? response({ saved_stocks: ["RTX", "LMT", "RTX"] })
        : response([
            { ticker: "LMT", company_name: "Lockheed Martin" },
            { ticker: "RTX", company_name: "RTX Corporation" },
            { ticker: "BA", company_name: "Boeing" },
          ]);
    },
  });

  assert.deepEqual(stocks, [
    { ticker: "RTX", company: "RTX Corporation" },
    { ticker: "LMT", company: "Lockheed Martin" },
  ]);
  assert.equal(requests[0].options.headers.Authorization, "Bearer investor-token");
  assert.equal(requests.length, 2);
  assert.ok(requests.every(({ options }) => options.signal === controller.signal));
});

test("an empty watchlist needs no stock catalog request", async () => {
  let requests = 0;
  assert.deepEqual(await loadWatchlist("token", {
    fetchImpl: async () => {
      requests += 1;
      return response({ saved_stocks: [] });
    },
  }), []);
  assert.equal(requests, 1);
});

test("preserves authentication failures so the page can require login", async () => {
  await assert.rejects(loadWatchlist("expired", {
    fetchImpl: async () => response({}, 401),
  }), { status: 401 });
});

test("server errors retain their status instead of expiring the session", async () => {
  await assert.rejects(loadWatchlist("token", {
    fetchImpl: async () => response({}, 503),
  }), { status: 503 });
});

test("a catalog failure is reported rather than showing an empty watchlist", async () => {
  await assert.rejects(loadWatchlist("token", {
    fetchImpl: async (url) => url.endsWith("/auth/me")
      ? response({ saved_stocks: ["LMT"] })
      : response({}, 503),
  }), /Unable to load stock information/);
});

test("network failures can be retried", async () => {
  await assert.rejects(loadWatchlist("token", {
    fetchImpl: async () => { throw new TypeError("Failed to fetch"); },
  }), /Failed to fetch/);
  assert.deepEqual(await loadWatchlist("token", {
    fetchImpl: async () => response({ saved_stocks: [] }),
  }), []);
});

test("keeps saved tickers accessible when their company name is unavailable", async () => {
  assert.deepEqual(await loadWatchlist("token", {
    fetchImpl: async (url) => url.endsWith("/auth/me")
      ? response({ saved_stocks: ["LMT"] })
      : response([]),
  }), [{ ticker: "LMT", company: "Company information unavailable" }]);
});
