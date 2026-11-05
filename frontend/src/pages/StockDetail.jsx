import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import PredictionFactors from "../components/PredictionFactors";
import StockChart from "../components/StockChart";
import TimeRangeSelector from "../components/TimeRangeSelector";
import FavoriteButton from "../components/FavoriteButton";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function formatPercent(value, includeSign = false) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "Not available";
  }

  const percent = value * 100;
  const sign = includeSign && percent > 0 ? "+" : "";
  return `${sign}${percent.toFixed(2)}%`;
}

function formatCurrency(value) {
  return typeof value === "number" && Number.isFinite(value)
    ? `$${value.toFixed(2)}`
    : "Not available";
}

function StockDetail() {
  const { ticker } = useParams();
  const [range, setRange] = useState("1Y");
  const [prediction, setPrediction] = useState(null);
  const [predictionError, setPredictionError] = useState("");
  const [isPredictionLoading, setIsPredictionLoading] = useState(true);
  const [history, setHistory] = useState([]);
  const [riskMetrics, setRiskMetrics] = useState(null);
  const [historyError, setHistoryError] = useState("");
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [modelMetrics, setModelMetrics] = useState(null);
  const [modelMetricsError, setModelMetricsError] = useState("");
  const [isModelMetricsLoading, setIsModelMetricsLoading] = useState(true);

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
      setRiskMetrics(null);

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
        setRiskMetrics(
          result.risk_metrics && typeof result.risk_metrics === "object"
            ? result.risk_metrics
            : null,
        );
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

  useEffect(() => {
    const controller = new AbortController();

    async function loadModelMetrics() {
      setIsModelMetricsLoading(true);
      setModelMetricsError("");
      setModelMetrics(null);

      try {
        const response = await fetch(`${API_BASE_URL}/models/metrics`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error("Prediction model metrics are unavailable.");
        }

        setModelMetrics(await response.json());
      } catch (error) {
        if (error.name !== "AbortError") {
          setModelMetricsError(error.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsModelMetricsLoading(false);
        }
      }
    }

    loadModelMetrics();
    return () => controller.abort();
  }, []);

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

    <div className="stock-header">
      <h1>{ticker}</h1>
      <FavoriteButton key={ticker} ticker={ticker} />
    </div>

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

      {!isPredictionLoading && prediction?.explanation && (
        <PredictionFactors explanation={prediction.explanation} />
      )}

      <section className="risk-performance" aria-labelledby="risk-performance-title">
        <h2 id="risk-performance-title">Risk &amp; Return</h2>
        <p>
          Measures for the selected {range} historical period
          {riskMetrics?.price_basis === "adjusted_close"
            ? ", using adjusted closing prices where available."
            : ", using closing prices."}
        </p>

        {isHistoryLoading && <p>Calculating risk measures...</p>}
        {!isHistoryLoading && historyError && (
          <p className="history-error">
            Risk measures are unavailable because historical data could not be
            loaded.
          </p>
        )}
        {!isHistoryLoading && !historyError && riskMetrics && (
          <>
            <dl className="risk-metric-grid">
              <div className="risk-metric-card">
                <dt>Period return</dt>
                <dd>{formatPercent(riskMetrics.period_return, true)}</dd>
                <small>First to latest close</small>
              </div>
              <div className="risk-metric-card">
                <dt>Annualized volatility</dt>
                <dd>{formatPercent(riskMetrics.annualized_volatility)}</dd>
                <small>Daily return variability × √252</small>
              </div>
              <div className="risk-metric-card">
                <dt>Maximum drawdown</dt>
                <dd>{formatPercent(riskMetrics.max_drawdown)}</dd>
                <small>Largest peak-to-trough decline</small>
              </div>
              <div className="risk-metric-card">
                <dt>Lowest daily return</dt>
                <dd>{formatPercent(riskMetrics.worst_daily_return, true)}</dd>
                <small>Lowest close-to-close return in this period</small>
              </div>
              <div className="risk-metric-card">
                <dt>Highest daily return</dt>
                <dd>{formatPercent(riskMetrics.best_daily_return, true)}</dd>
                <small>Highest close-to-close return in this period</small>
              </div>
            </dl>
            <p className="risk-method-note">
              Based on {riskMetrics.daily_return_observations} daily returns.
              Volatility is annualized using 252 trading days; it describes
              historical price variability and does not predict future risk.
            </p>
          </>
        )}
        {!isHistoryLoading && !historyError && !riskMetrics && (
          <p>Risk measures are not available for this historical response.</p>
        )}
      </section>

      <section className="model-performance" aria-labelledby="model-performance-title">
        <h2 id="model-performance-title">Prediction Model Accuracy</h2>
        <p>
          Historical forecast errors are shown alongside market risk for
          context. Lower MAE and RMSE indicate smaller price prediction errors;
          they are not measures of investment risk.
        </p>
        {isModelMetricsLoading && <p>Loading model metrics...</p>}
        {!isModelMetricsLoading && modelMetricsError && (
          <p className="history-error">{modelMetricsError}</p>
        )}
        {!isModelMetricsLoading && modelMetrics && (
          <div className="model-metrics-table-wrap">
            <table className="model-metrics-table">
              <thead>
                <tr>
                  <th scope="col">Metric</th>
                  <th scope="col">Persistence baseline</th>
                  <th scope="col">Prediction model</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">MAE</th>
                  <td>{formatCurrency(modelMetrics.baseline?.mae)}</td>
                  <td>{formatCurrency(modelMetrics.model?.mae)}</td>
                </tr>
                <tr>
                  <th scope="row">RMSE</th>
                  <td>{formatCurrency(modelMetrics.baseline?.rmse)}</td>
                  <td>{formatCurrency(modelMetrics.model?.rmse)}</td>
                </tr>
              </tbody>
            </table>
          </div>
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
