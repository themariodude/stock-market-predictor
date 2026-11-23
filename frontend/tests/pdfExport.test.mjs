
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { downloadStockPdf } from "../src/utils/pdfExport.js";

const stockDetailSource = readFileSync(
  new URL("../src/pages/StockDetail.jsx", import.meta.url),
  "utf8"
);

function makeResponse(ok = true, type = "application/pdf") {
  return {
    ok,
    headers: {
      get: () => type,
    },
    blob: async () => ({ type }),
  };
}

function makeMocks(fetchFn = async () => makeResponse()) {
  const result = {
    requestedUrl: "",
    filename: "",
    clicks: 0,
    revoked: false,
  };

  const options = {
    fetchFn: async (url) => {
      result.requestedUrl = url;
      return fetchFn(url);
    },
    urlApi: {
      createObjectURL: () => "blob:test-pdf",
      revokeObjectURL: () => {
        result.revoked = true;
      },
    },
    documentRef: {
      createElement: () => ({
        set href(value) {
          result.href = value;
        },
        set download(value) {
          result.filename = value;
        },
        click() {
          result.clicks += 1;
        },
        remove() {},
      }),
      body: {
        appendChild() {},
      },
    },
    scheduleCleanup: (callback) => callback(),
    now: () => new Date("2026-11-18T12:00:00Z"),
  };

  return { options, result };
}

test("exports PDF for the selected stock ticker", async () => {
  const { options, result } = makeMocks();

  await downloadStockPdf("NOC", "http://localhost:8000", options);

  assert.equal(
    result.requestedUrl,
    "http://localhost:8000/reports/stocks/NOC/pdf"
  );
  assert.equal(result.filename, "NOC_Analysis_2026-11-18.pdf");
  assert.equal(result.clicks, 1);
  assert.equal(result.revoked, true);
});

test("rejects failed API responses", async () => {
  const { options, result } = makeMocks(
    async () => makeResponse(false)
  );

  await assert.rejects(
    downloadStockPdf("LMT", "", options),
    /Unable to export PDF/
  );

  assert.equal(result.clicks, 0);
});

test("rejects responses that are not PDF", async () => {
  const { options, result } = makeMocks(
    async () => makeResponse(true, "application/json")
  );

  await assert.rejects(
    downloadStockPdf("LMT", "", options),
    /valid PDF response/
  );

  assert.equal(result.clicks, 0);
});

test("handles network failures", async () => {
  const { options, result } = makeMocks(async () => {
    throw new TypeError("Failed to fetch");
  });

  await assert.rejects(
    downloadStockPdf("LMT", "", options),
    /Failed to fetch/
  );

  assert.equal(result.clicks, 0);
});

test("allows retry after a failed request", async () => {
  let fail = true;

  const { options, result } = makeMocks(async () => {
    if (fail) {
      throw new TypeError("Failed to fetch");
    }
    return makeResponse();
  });

  await assert.rejects(downloadStockPdf("LMT", "", options));

  fail = false;

  await downloadStockPdf("LMT", "", options);

  assert.equal(result.clicks, 1);
});

test("stock detail provides loading and error UI", () => {
  assert.match(
    stockDetailSource,
    /disabled=\{isPdfExporting\}/
  );

  assert.match(
    stockDetailSource,
    /Generating PDF/
  );

  assert.match(
    stockDetailSource,
    /pdfExportError\s*&&/
  );

  assert.match(
    stockDetailSource,
    /role="alert"/
  );
});
