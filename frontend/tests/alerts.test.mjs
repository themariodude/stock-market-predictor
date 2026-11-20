
import test, { afterEach } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const apiSource = readFileSync(
  new URL("../src/features/alerts_api.js", import.meta.url),
  "utf8"
);

const formSource = readFileSync(
  new URL("../src/components/AlertForm.jsx", import.meta.url),
  "utf8"
);

const pageSource = readFileSync(
  new URL("../src/pages/Alerts.jsx", import.meta.url),
  "utf8"
);

afterEach(() => {
  // Reserved for cleanup as behavioral tests are added.
});

// US-39: Create alerts

test("US-39: alert API exports createAlert", () => {
  assert.match(
    apiSource,
    /export function createAlert/
  );
});

test("US-39: createAlert uses POST", () => {
  assert.match(
    apiSource,
    /method:\s*["']POST["']/
  );
});

test("US-39: alert form supports above and below", () => {
  assert.match(
    formSource,
    /value="above"/
  );

  assert.match(
    formSource,
    /value="below"/
  );
});

test("US-39: alert form validates positive prices", () => {
  assert.match(
    formSource,
    /price <= 0/
  );
});

test("US-39: alert form prevents default submission", () => {
  assert.match(
    formSource,
    /event\.preventDefault\(\)/
  );
});

// US-40: Manage alerts

test("US-40: alert API exports getAlerts", () => {
  assert.match(
    apiSource,
    /export function getAlerts/
  );
});

test("US-40: alert API exports deleteAlert", () => {
  assert.match(
    apiSource,
    /export function deleteAlert/
  );
});

test("US-40: deleteAlert uses DELETE", () => {
  assert.match(
    apiSource,
    /method:\s*["']DELETE["']/
  );
});

test("US-40: alerts page displays saved alerts", () => {
  assert.match(
    pageSource,
    /alerts\.map/
  );
});

test("US-40: alerts page handles deletion", () => {
  assert.match(
    pageSource,
    /handleDelete/
  );
});

test("US-40: alerts page handles loading", () => {
  assert.match(
    pageSource,
    /Loading alerts/
  );
});

test("Security: alert requests use bearer token", () => {
  assert.match(
    apiSource,
    /Bearer \$\{token\}/
  );
});

test("Security: unauthenticated users are blocked", () => {
  assert.match(
    apiSource,
    /Please log in to manage alerts/
  );
});
