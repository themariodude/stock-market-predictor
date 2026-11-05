
import test from "node:test";
import assert from "node:assert/strict";
import {
  calculatePercentChange,
  getSectorMovers,
} from "../src/utils/stockCalculations.js";

test("calculates a positive percentage change", () => {
  assert.equal(calculatePercentChange(100, 105), 5);
});

test("calculates a negative percentage change", () => {
  assert.equal(calculatePercentChange(100, 95), -5);
});

test("returns zero for unchanged prices", () => {
  assert.equal(calculatePercentChange(100, 100), 0);
});

test("rejects zero or negative prices", () => {
  assert.equal(calculatePercentChange(0, 100), null);
  assert.equal(calculatePercentChange(-10, 100), null);
});

test("rejects missing or invalid values", () => {
  assert.equal(calculatePercentChange(null, 100), null);
  assert.equal(calculatePercentChange(NaN, 100), null);
  assert.equal(calculatePercentChange(100, Infinity), null);
});


const sampleStocks = [
  { ticker: "LMT", change: 1.27 },
  { ticker: "RTX", change: 0.82 },
  { ticker: "NOC", change: -0.41 },
  { ticker: "GD", change: 0.35 },
  { ticker: "LHX", change: 1.11 },
  { ticker: "BA", change: -0.63 },
];

test("ranks the top three gainers correctly", () => {
  const { gainers } = getSectorMovers(sampleStocks);

  assert.deepEqual(
    gainers.map((stock) => stock.ticker),
    ["LMT", "LHX", "RTX"]
  );
});

test("ranks decliners by largest loss first", () => {
  const { decliners } = getSectorMovers(sampleStocks);

  assert.deepEqual(
    decliners.map((stock) => stock.ticker),
    ["BA", "NOC"]
  );
});

test("excludes unchanged stocks", () => {
  const stocks = [
    { ticker: "LMT", change: 0 },
    { ticker: "RTX", change: 2 },
    { ticker: "BA", change: -1 },
  ];

  const { gainers, decliners } = getSectorMovers(stocks);

  assert.equal(gainers.length, 1);
  assert.equal(decliners.length, 1);
});

test("handles empty stock data", () => {
  const { gainers, decliners } = getSectorMovers([]);

  assert.deepEqual(gainers, []);
  assert.deepEqual(decliners, []);
});

test("excludes invalid percentage changes", () => {
  const stocks = [
    { ticker: "LMT", change: NaN },
    { ticker: "RTX", change: 1.5 },
    { ticker: "BA", change: null },
  ];

  const { gainers, decliners } = getSectorMovers(stocks);

  assert.deepEqual(
    gainers.map((stock) => stock.ticker),
    ["RTX"]
  );
  assert.deepEqual(decliners, []);
});

