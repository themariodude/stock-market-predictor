import test from "node:test";
import assert from "node:assert/strict";
import { isValidPrediction } from "../src/utils/prediction.js";

const prediction = {
  prediction_direction: "UP",
  direction_label: "Upward",
  current_price: 100,
  predicted_price: 101,
  predicted_change: 1,
  predicted_percent_change: 1,
};

test("accepts valid forecasts without optional confidence information", () => {
  assert.equal(isValidPrediction(prediction), true);
  assert.equal(isValidPrediction({
    ...prediction,
    prediction_direction: "DOWN",
    direction_label: "Downward",
    predicted_price: 99,
    predicted_change: -1,
    predicted_percent_change: -1,
  }), true);
  assert.equal(isValidPrediction({
    ...prediction,
    prediction_direction: "FLAT",
    direction_label: "Flat",
    predicted_price: 100,
    predicted_change: 0,
    predicted_percent_change: 0,
  }), true);
});

test("rejects the successful API response with null forecast prices", () => {
  assert.equal(isValidPrediction({
    ...prediction,
    prediction_direction: "FLAT",
    direction_label: "Flat",
    current_price: null,
    predicted_price: null,
    predicted_change: null,
    predicted_percent_change: null,
  }), false);
});

test("rejects missing, nonnumeric, and nonfinite required forecast values", () => {
  for (const field of [
    "current_price",
    "predicted_price",
    "predicted_change",
    "predicted_percent_change",
  ]) {
    for (const value of [null, undefined, "101", NaN, Infinity, -Infinity]) {
      assert.equal(isValidPrediction({ ...prediction, [field]: value }), false,
        `${field} must reject ${String(value)}`);
    }
  }
});

test("rejects nonpositive stock prices and invalid direction metadata", () => {
  for (const field of ["current_price", "predicted_price"]) {
    for (const value of [0, -1]) {
      assert.equal(isValidPrediction({ ...prediction, [field]: value }), false);
    }
  }
  for (const value of [null, undefined, {}, [], "unavailable"]) {
    assert.equal(isValidPrediction(value), false);
  }
  for (const value of [null, undefined, "SIDEWAYS"]) {
    assert.equal(isValidPrediction({ ...prediction, prediction_direction: value }), false);
  }
  for (const value of [null, undefined, "", " "]) {
    assert.equal(isValidPrediction({ ...prediction, direction_label: value }), false);
  }
});
