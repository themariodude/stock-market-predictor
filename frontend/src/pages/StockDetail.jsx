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
  const [history, setHistory] = useState([]);
  const [historyError, setHistoryError] = useState("");
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);

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

  useEffect(() => {
    const controller = new AbortController();

    async function loadHistory() {
      setIsHistoryLoading(true);
      setHistoryError("");
      setHistory([]);

      try {
        const response = await fetch(
          `${API_BASE_URL}/stocks/${ticker}/history?time_range=${range}`,
          { signal: controller.signal },
        );

        if (!response.ok) {
          throw new Error("Historical data is unavailable.");
        }

        const result = await response.json();
        if (!Array.isArray(result.data)) {
          throw new Error("Historical data is unavailable.");
        }

        setHistory(result.data);
      } catch (error) {
        if (error.name !== "AbortError") {
          setHistoryError(error.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsHistoryLoading(false);
        }
      }
    }

    loadHistory();

    return () => controller.abort();
  }, [ticker, range]);

  const predictionDirectionClass =
    prediction?.prediction_direction.toLowerCase() ?? "";
  const hasPredictionConfidence =
    typeof prediction?.prediction_confidence === "number";
  const economicFactors = Array.isArray(prediction?.economic_factors)
    ? prediction.economic_factors
    : [];

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
            {hasPredictionConfidence && (
              <div className="prediction-confidence">
                <span>{prediction.confidence_label}</span>
                <strong>{prediction.prediction_confidence.toFixed(1)}%</strong>
                <div
                  className="confidence-track"
                  aria-label={`Prediction confidence ${prediction.prediction_confidence.toFixed(1)} percent`}
                >
                  <div
                    className="confidence-fill"
                    style={{
                      width: `${prediction.prediction_confidence}%`,
                    }}
                  />
                </div>
                <small>
                  {prediction.prediction_uncertainty.toFixed(1)}% uncertainty
                </small>
              </div>
            )}
          </div>
        )}

        {!isPredictionLoading && predictionError && (
          <p className="prediction-error">{predictionError}</p>
        )}
      </section>

      {!isPredictionLoading && prediction && (
        <section className="economic-factors" aria-labelledby="economic-factors-title">
          <h2 id="economic-factors-title">Economic Context</h2>
          <p>
            Published indicators available before the latest closing price used
            for this forecast
            {prediction.as_of_date ? ` on ${prediction.as_of_date}` : ""}.
            The forecast uses recent stock prices; these indicators provide
            context rather than a measure of their effect on it.
          </p>

          {economicFactors.length > 0 ? (
            <ul className="factor-list">
              {economicFactors.map((factor) => (
                <li className="factor-card" key={factor.id}>
                  <span>{factor.name}</span>
                  <strong>
                    {factor.value.toFixed(2)}{factor.unit}
                  </strong>
                  <small>Published {factor.published_on}</small>
                </li>
              ))}
            </ul>
          ) : (
            <p className="factor-empty">
              Economic factor data is not available for this forecast.
            </p>
          )}
        </section>
      )}

      <section className="stock-history">
        <div className="chart-header">
          <h2>Historical Performance</h2>

          <TimeRangeSelector
            selectedRange={range}
            onRangeChange={setRange}
          />
        </div>

        {isHistoryLoading && <p>Loading historical data...</p>}
        {!isHistoryLoading && historyError && (
          <p className="history-error">{historyError}</p>
        )}
        {!isHistoryLoading && !historyError && (
          <StockChart data={history} range={range} prediction={prediction} />
        )}
      </section>
    </main>
  );
}

export default StockDetail;
