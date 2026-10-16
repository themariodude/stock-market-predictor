import test from "node:test";
import assert from "node:assert/strict";

import { loadWatchlist } from "../src/services/watchlist.js";

function mockResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  };
}

test("loads only the authenticated investor's favorites in saved order", async () => {
  const requests = [];

  const fetchImpl = async (url, options = {}) => {
    requests.push({ url, options });

    if (url.endsWith("/favorites")) {
      return mockResponse([
        { ticker: "RTX" },
        { ticker: "LMT" },
      ]);
    }

    if (url.endsWith("/stocks")) {
      return mockResponse([
        { ticker: "LMT", company_name: "Lockheed Martin" },
        { ticker: "RTX", company_name: "RTX Corporation" },
        { ticker: "BA", company_name: "Boeing" },
      ]);
    }

    throw new Error(`Unexpected request: ${url}`);
  };

  const result = await loadWatchlist("test-token", { fetchImpl });

  assert.deepEqual(result, [
    { ticker: "RTX", company: "RTX Corporation" },
    { ticker: "LMT", company: "Lockheed Martin" },
  ]);

  assert.equal(requests.length, 2);
  assert.ok(requests[0].url.endsWith("/favorites"));
  assert.ok(requests[1].url.endsWith("/stocks"));

  assert.equal(
    requests[0].options.headers.Authorization,
    "Bearer test-token"
  );

  assert.ok(
    requests.every((request) => !request.url.endsWith("/auth/me"))
  );
});

test("an empty watchlist needs no stock catalog request", async () => {
  const requests = [];

  const fetchImpl = async (url) => {
    requests.push(url);

    if (url.endsWith("/favorites")) {
      return mockResponse([]);
    }

    throw new Error(`Unexpected request: ${url}`);
  };

  const result = await loadWatchlist("test-token", { fetchImpl });

  assert.deepEqual(result, []);
  assert.equal(requests.length, 1);
  assert.ok(requests[0].endsWith("/favorites"));
});

test("preserves authentication failures so the page can require login", async () => {
  const fetchImpl = async () => mockResponse({}, 401);

  await assert.rejects(
    () => loadWatchlist("expired-token", { fetchImpl }),
    (error) => error.status === 401
  );
});

test("server errors retain their status instead of expiring the session", async () => {
  const fetchImpl = async () => mockResponse({}, 503);

  await assert.rejects(
    () => loadWatchlist("test-token", { fetchImpl }),
    (error) => error.status === 503
  );
});

test("a catalog failure is reported rather than showing an empty watchlist", async () => {
  const fetchImpl = async (url) => {
    if (url.endsWith("/favorites")) {
      return mockResponse([{ ticker: "LMT" }]);
    }

    if (url.endsWith("/stocks")) {
      return mockResponse({}, 500);
    }

    throw new Error(`Unexpected request: ${url}`);
  };

  await assert.rejects(
    () => loadWatchlist("test-token", { fetchImpl }),
    /Unable to load stock information/
  );
});

test("network failures can be retried", async () => {
  let attempts = 0;

  const fetchImpl = async (url) => {
    if (url.endsWith("/favorites")) {
      attempts += 1;

      if (attempts === 1) {
        throw new Error("Network unavailable");
      }

      return mockResponse([{ ticker: "LMT" }]);
    }

    if (url.endsWith("/stocks")) {
      return mockResponse([
        { ticker: "LMT", company_name: "Lockheed Martin" },
      ]);
    }

    throw new Error(`Unexpected request: ${url}`);
  };

  await assert.rejects(
    () => loadWatchlist("test-token", { fetchImpl }),
    /Network unavailable/
  );

  const result = await loadWatchlist("test-token", { fetchImpl });

  assert.deepEqual(result, [
    { ticker: "LMT", company: "Lockheed Martin" },
  ]);

  assert.equal(attempts, 2);
});

test("keeps saved tickers accessible when their company name is unavailable", async () => {
  const fetchImpl = async (url) => {
    if (url.endsWith("/favorites")) {
      return mockResponse([{ ticker: "LMT" }]);
    }

    if (url.endsWith("/stocks")) {
      return mockResponse([]);
    }

    throw new Error(`Unexpected request: ${url}`);
  };

  const result = await loadWatchlist("test-token", { fetchImpl });

  assert.deepEqual(result, [
    {
      ticker: "LMT",
      company: "Company information unavailable",
    },
  ]);
});
