import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import StockChart from "../components/StockChart";
import TimeRangeSelector from "../components/TimeRangeSelector";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function StockDetail() {
  const { ticker } = useParams();
  const [range, setRange] = useState("1Y");
  const [prediction, setPrediction] = useState(null);
  const [predictionError, setPredictionError] = useState("");
  const [isPredictionLoading, setIsPredictionLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPredictionDirection() {
      setIsPredictionLoading(true);
      setPredictionError("");
      setPrediction(null);

      try {
        const response = await fetch(
          `${API_BASE_URL}/stocks/${ticker}/prediction-direction`,
          { signal: controller.signal },
        );

        if (!response.ok) {
          throw new Error("Prediction direction is unavailable.");
        }

        const data = await response.json();
        setPrediction(data);
      } catch (error) {
        if (error.name !== "AbortError") {
          setPredictionError(error.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsPredictionLoading(false);
        }
      }
    }

    loadPredictionDirection();

    return () => controller.abort();
  }, [ticker]);

  const history = [
    { date: "2023-11-21", close: 492.56 },
    { date: "2024-05-01", close: 512.93 },
    { date: "2024-12-23", close: 507.12 },
    { date: "2025-01-02", close: 482.14 },
    { date: "2025-04-01", close: 471.83 },
    { date: "2025-07-01", close: 463.72 },
    { date: "2025-10-01", close: 489.31 },
    { date: "2026-01-02", close: 501.44 },
    { date: "2026-04-01", close: 493.26 },
    { date: "2026-07-01", close: 507.19 },
    { date: "2026-09-01", close: 512.37 },
    { date: "2026-09-13", close: 519.59 },
  ];
  const predictionDirectionClass =
    prediction?.prediction_direction.toLowerCase() ?? "";

  return (
    <main className="stock-detail-page">
      <Link to="/dashboard">Back to Dashboard</Link>

      <h1>{ticker}</h1>

      <section className="prediction-direction">
        <div>
          <p className="section-label">Forecast Direction</p>
          {isPredictionLoading && <h2>Loading...</h2>}
          {!isPredictionLoading && predictionError && (
            <h2 className="prediction-unavailable">Unavailable</h2>
          )}
          {!isPredictionLoading && prediction && (
            <h2 className={`prediction-heading ${predictionDirectionClass}`}>
              {prediction.direction_label}
            </h2>
          )}
        </div>

        {!isPredictionLoading && prediction && (
          <div className="prediction-metrics">
            <div>
              <span>Predicted Price</span>
              <strong>${prediction.predicted_price.toFixed(2)}</strong>
            </div>
            <div>
              <span>Predicted Change</span>
              <strong>
                {prediction.predicted_change >= 0 ? "+" : ""}
                {prediction.predicted_change.toFixed(2)} (
                {prediction.predicted_percent_change >= 0 ? "+" : ""}
                {prediction.predicted_percent_change.toFixed(2)}%)
              </strong>
            </div>
          </div>
        )}

        {!isPredictionLoading && predictionError && (
          <p className="prediction-error">{predictionError}</p>
        )}
      </section>

      <section className="stock-history">
        <div className="chart-header">
          <h2>Historical Performance</h2>

          <TimeRangeSelector
            selectedRange={range}
            onRangeChange={setRange}
          />
        </div>

        <StockChart data={history} range={range} />
      </section>
    </main>
  );
}

export default StockDetail;
