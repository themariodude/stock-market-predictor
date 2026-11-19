import test from "node:test";
import assert from "node:assert/strict";
import { getComparisonMetrics } from "../src/utils/comparisonMetrics.js";

test("compares daily and calendar-month returns on shared dates", () => {
  const records = [
    { date: "2025-11-05", close: 50, high: 999, low: 1, volume: 10 },
    { date: "2025-11-07", close: 55, high: 70, low: 40, volume: 20 },
    { date: "2026-08-05", close: 60, high: 80, low: 55, volume: 30 },
    { date: "2026-10-05", close: 80, high: 90, low: 75, volume: 40 },
    { date: "2026-11-04", close: 100, high: 110, low: 80, volume: 50 },
    { date: "2026-11-05", close: 120, high: 150, low: 100, volume: 1234567 },
  ];
  const commonDates = records.slice(1).map((record) => record.date);

  assert.deepEqual(getComparisonMetrics(records, commonDates), {
    price: 120,
    change: 20,
    oneMonthReturn: 50,
    threeMonthReturn: 100,
    volume: 1234567,
    yearHigh: 150,
    yearLow: 40,
  });
});

test("uses the prior trading day near a month-end cutoff", () => {
  const records = [
    { date: "2025-12-31", close: 50 },
    { date: "2026-02-27", close: 80 },
    { date: "2026-03-30", close: 90 },
    { date: "2026-03-31", close: 100 },
  ];

  const metrics = getComparisonMetrics(
    records,
    records.map((record) => record.date)
  );

  assert.equal(metrics.oneMonthReturn, 25);
  assert.equal(metrics.threeMonthReturn, 100);
});

test("shows unavailable metrics when history is too sparse", () => {
  const records = [
    { date: "2026-07-01", close: 80, high: null, low: null },
    { date: "2026-11-04", close: 100, high: null, low: null },
    { date: "2026-11-05", close: 110, high: null, low: null, volume: -1 },
  ];

  assert.deepEqual(getComparisonMetrics(
    records,
    records.map((record) => record.date)
  ), {
    price: 110,
    change: 10,
    oneMonthReturn: null,
    threeMonthReturn: null,
    volume: null,
    yearHigh: null,
    yearLow: null,
  });
  assert.equal(getComparisonMetrics(records, ["2026-11-05"]), null);
});
