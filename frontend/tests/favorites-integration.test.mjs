
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

test("watchlist reflects favorite additions, removals, and repeated loads", async () => {
  const savedFavorites = new Set();

  const fetchImpl = async (url, options = {}) => {
    const method = options.method ?? "GET";

    // Return the currently saved favorites.
    if (url.endsWith("/favorites") && method === "GET") {
      return mockResponse(
        [...savedFavorites].map((ticker) => ({ ticker }))
      );
    }

    // Simulate adding LMT to favorites.
    if (url.endsWith("/favorites/LMT") && method === "POST") {
      savedFavorites.add("LMT");
      return mockResponse({ ticker: "LMT" }, 201);
    }

    // Simulate removing LMT from favorites.
    if (url.endsWith("/favorites/LMT") && method === "DELETE") {
      savedFavorites.delete("LMT");
      return mockResponse(null, 204);
    }

    // Return company information.
    if (url.endsWith("/stocks") && method === "GET") {
      return mockResponse([
        {
          ticker: "LMT",
          company_name: "Lockheed Martin",
        },
      ]);
    }

    throw new Error(`Unexpected request: ${method} ${url}`);
  };

  // Initially, the Watchlist should be empty.
  let watchlist = await loadWatchlist("test-token", { fetchImpl });

  assert.deepEqual(watchlist, []);

  // Simulate POST /favorites/LMT.
  const addResponse = await fetchImpl("/favorites/LMT", {
    method: "POST",
  });

  assert.equal(addResponse.status, 201);

  // The Watchlist should now include LMT.
  watchlist = await loadWatchlist("test-token", { fetchImpl });

  assert.deepEqual(watchlist, [
    {
      ticker: "LMT",
      company: "Lockheed Martin",
    },
  ]);

  // Simulate refreshing the Watchlist.
  watchlist = await loadWatchlist("test-token", { fetchImpl });

  assert.equal(watchlist.length, 1);
  assert.equal(watchlist[0].ticker, "LMT");

  // Simulate DELETE /favorites/LMT.
  const deleteResponse = await fetchImpl("/favorites/LMT", {
    method: "DELETE",
  });

  assert.equal(deleteResponse.status, 204);

  // The Watchlist should now be empty.
  watchlist = await loadWatchlist("test-token", { fetchImpl });

  assert.deepEqual(watchlist, []);

  // Confirm removal remains reflected after another load.
  watchlist = await loadWatchlist("test-token", { fetchImpl });

  assert.deepEqual(watchlist, []);
});
