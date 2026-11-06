import test from "node:test";
import assert from "node:assert/strict";
import { summarizeSector } from "../src/utils/stockCalculations.js";

test("summarizes available stock changes with an equal-weighted average", () => {
  assert.deepEqual(summarizeSector([
    { change: 4 },
    { change: -2 },
    { change: 0 },
    { change: 2 },
  ]), {
    averageChange: 1,
    gainers: 2,
    decliners: 1,
  });
});

test("excludes unavailable changes and handles an empty sector", () => {
  assert.deepEqual(summarizeSector([
    { change: null },
    { change: NaN },
    { change: 3 },
  ]), {
    averageChange: 3,
    gainers: 1,
    decliners: 0,
  });
  assert.deepEqual(summarizeSector([]), {
    averageChange: null,
    gainers: 0,
    decliners: 0,
  });
});
