export function isValidPrediction(prediction) {
  if (!prediction || !["UP", "DOWN", "FLAT"].includes(prediction.prediction_direction)) {
    return false;
  }

  return (
    typeof prediction.direction_label === "string" &&
    prediction.direction_label.trim().length > 0 &&
    Number.isFinite(prediction.current_price) &&
    prediction.current_price > 0 &&
    Number.isFinite(prediction.predicted_price) &&
    prediction.predicted_price > 0 &&
    Number.isFinite(prediction.predicted_change) &&
    Number.isFinite(prediction.predicted_percent_change)
  );
}
