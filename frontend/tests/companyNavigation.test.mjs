
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const dashboardSource = readFileSync(
  new URL("../src/pages/Dashboard.jsx", import.meta.url),
  "utf8"
);

const appSource = readFileSync(
  new URL("../src/App.jsx", import.meta.url),
  "utf8"
);

const stockDetailSource = readFileSync(
  new URL("../src/pages/StockDetail.jsx", import.meta.url),
  "utf8"
);

test("dashboard provides stock detail links using the selected ticker", () => {
  assert.match(
    dashboardSource,
    /to=\{`\/stocks\/\$\{stock\.ticker\}`\}/
  );
});

test("application defines a dynamic stock detail route", () => {
  assert.match(
    appSource,
    /path="\/stocks\/:ticker"/
  );
});

test("stock detail reads the selected ticker from the URL", () => {
  assert.match(
    stockDetailSource,
    /const\s*\{\s*ticker\s*\}\s*=\s*useParams\(\)/
  );
});

test("stock detail requests prediction data for the selected ticker", () => {
  assert.match(
    stockDetailSource,
    /\/stocks\/\$\{ticker\}\/prediction-direction/
  );
});

test("stock detail requests historical data for the selected ticker", () => {
  assert.match(
    stockDetailSource,
    /\/stocks\/\$\{ticker\}\/history/
  );
});

test("stock detail provides navigation back to the dashboard", () => {
  assert.match(
    stockDetailSource,
    /<Link\s+to="\/dashboard"/
  );
});
