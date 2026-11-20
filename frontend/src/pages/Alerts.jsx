import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  getAlerts,
  createAlert,
  deleteAlert,
  getAlertToken,
} from "../features/alerts_api";

import {
  getMarketAlerts,
  createMarketAlert,
  updateMarketAlert,
  deleteMarketAlert,
} from "../services/marketAlerts";

const STOCKS = ["LMT", "RTX", "NOC", "GD", "LHX", "BA"];

export default function Alerts() {
  const navigate = useNavigate();
  const token = getAlertToken();

  const [priceAlerts, setPriceAlerts] = useState([]);
  const [marketAlerts, setMarketAlerts] = useState([]);
  const [loading, setLoading] = useState(Boolean(token));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [type, setType] = useState("price");
  const [ticker, setTicker] = useState("LMT");
  const [condition, setCondition] = useState("above");
  const [threshold, setThreshold] = useState("");

  const [editingId, setEditingId] = useState(null);
  const [editThreshold, setEditThreshold] = useState("");
  const [editDirection, setEditDirection] = useState("either");

  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }

    let cancelled = false;

    async function loadAlerts() {
      const results = await Promise.allSettled([
        getAlerts(),
        getMarketAlerts({ token }),
      ]);

      if (cancelled) return;

      const [prices, markets] = results;
      const failures = [];

      if (prices.status === "fulfilled") {
        setPriceAlerts(
          Array.isArray(prices.value) ? prices.value : []
        );
      } else {
        failures.push(
          `Price alerts: ${prices.reason?.message || "Request failed"}`
        );
      }

      if (markets.status === "fulfilled") {
        const value = markets.value;
        setMarketAlerts(
          Array.isArray(value)
            ? value
            : Array.isArray(value?.alerts)
              ? value.alerts
              : []
        );
      } else {
        failures.push(
          `Percentage alerts: ${
            markets.reason?.message || "Request failed"
          }`
        );
      }

      setError(failures.join(" | "));
      setLoading(false);
    }

    loadAlerts();

    return () => {
      cancelled = true;
    };
  }, [token, navigate, refreshKey]);

  function handleTypeChange(value) {
    setType(value);
    setCondition(value === "price" ? "above" : "either");
    setThreshold("");
    setError("");
  }

  function handleError(err) {
    if (err?.status === 401) {
      navigate("/login", { replace: true });
      return;
    }

    setError(err?.message || "Request failed.");
  }

  async function handleCreate(event) {
    event.preventDefault();

    const value = Number(threshold);

    if (
      threshold.trim() === "" ||
      !Number.isFinite(value) ||
      value <= 0 ||
      (type === "percent" && value > 100)
    ) {
      setError(
        type === "price"
          ? "Enter a valid target price."
          : "Enter a percentage greater than 0 and at most 100."
      );
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");

    try {
      if (type === "price") {
        const created = await createAlert({
          ticker,
          condition,
          threshold: value,
        });

        setPriceAlerts((previous) => [created, ...previous]);
      } else {
        const created = await createMarketAlert(
          {
            ticker,
            direction: condition,
            threshold_percent: value,
          },
          { token }
        );

        setMarketAlerts((previous) => [created, ...previous]);
      }

      setThreshold("");
      setMessage("Alert created successfully.");
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(alert) {
    if (!window.confirm(`Delete ${alert.ticker} alert?`)) {
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");

    try {
      if (alert.type === "price") {
        await deleteAlert(alert.id);

        setPriceAlerts((previous) =>
          previous.filter((item) => item.id !== alert.id)
        );
      } else {
        await deleteMarketAlert(alert.id, { token });

        setMarketAlerts((previous) =>
          previous.filter((item) => item.id !== alert.id)
        );
      }

      setMessage("Alert deleted successfully.");
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function handleToggle(alert) {
    setBusy(true);
    setError("");
    setMessage("");

    try {
      const updated = await updateMarketAlert(
        alert.id,
        { is_active: !alert.is_active },
        { token }
      );

      setMarketAlerts((previous) =>
        previous.map((item) =>
          item.id === alert.id ? updated : item
        )
      );

      setMessage("Alert status updated.");
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  function startEditing(alert) {
    setEditingId(alert.id);
    setEditThreshold(String(alert.threshold_percent));
    setEditDirection(alert.direction);
    setError("");
  }

  async function handleSaveEdit(event, alert) {
    event.preventDefault();

    const value = Number(editThreshold);

    if (
      editThreshold.trim() === "" ||
      !Number.isFinite(value) ||
      value <= 0 ||
      value > 100
    ) {
      setError("Enter a percentage greater than 0 and at most 100.");
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");

    try {
      const updated = await updateMarketAlert(
        alert.id,
        {
          threshold_percent: value,
          direction: editDirection,
        },
        { token }
      );

      setMarketAlerts((previous) =>
        previous.map((item) =>
          item.id === alert.id ? updated : item
        )
      );

      setEditingId(null);
      setMessage("Alert updated successfully.");
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  const allAlerts = [
    ...priceAlerts.map((alert) => ({
      ...alert,
      type: "price",
    })),
    ...marketAlerts.map((alert) => ({
      ...alert,
      type: "percent",
    })),
  ].sort(
    (a, b) =>
      new Date(b.created_at || 0) -
      new Date(a.created_at || 0)
  );

  if (!token) return null;

  return (
    <main
      className="alerts-page"
      style={{
        width: "calc(100% - 64px)",
        maxWidth: "1200px",
        margin: "0 auto",
        padding: "32px 0 64px",
        boxSizing: "border-box",
      }}
    >
      <nav className="dashboard-navigation">
        <Link to="/dashboard" className="back-button">
          Back to Dashboard
        </Link>

        <Link to="/notifications" className="back-button">
          Notifications
        </Link>
      </nav>

      <h1>Stock Alerts</h1>

      <p>
        Create and manage price and percentage-change alerts
        for defense-sector stocks.
      </p>

      <section className="alert-form-section">
        <h2>Create Alert</h2>

        <form className="alert-form" onSubmit={handleCreate}>
          <div>
            <label htmlFor="alert-type">Alert Type</label>
            <select
              id="alert-type"
              value={type}
              onChange={(event) =>
                handleTypeChange(event.target.value)
              }
            >
              <option value="price">Price Threshold</option>
              <option value="percent">Percentage Change</option>
            </select>
          </div>

          <div>
            <label htmlFor="alert-stock">Stock</label>
            <select
              id="alert-stock"
              value={ticker}
              onChange={(event) => setTicker(event.target.value)}
            >
              {STOCKS.map((stock) => (
                <option key={stock} value={stock}>
                  {stock}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="alert-condition">Condition</label>
            <select
              id="alert-condition"
              value={condition}
              onChange={(event) =>
                setCondition(event.target.value)
              }
            >
              {type === "price" ? (
                <>
                  <option value="above">Price Above</option>
                  <option value="below">Price Below</option>
                </>
              ) : (
                <>
                  <option value="either">Increase or Decrease</option>
                  <option value="increase">Increase</option>
                  <option value="decrease">Decrease</option>
                </>
              )}
            </select>
          </div>

          <div>
            <label htmlFor="alert-value">
              {type === "price"
                ? "Target Price ($)"
                : "Percentage Change (%)"}
            </label>

            <input
              id="alert-value"
              type="number"
              min={type === "price" ? "0.01" : "0.0001"}
              max={type === "percent" ? "100" : undefined}
              step="any"
              required
              value={threshold}
              onChange={(event) =>
                setThreshold(event.target.value)
              }
              placeholder={type === "price" ? "500" : "5"}
            />
          </div>

          <button
            className="alert-submit-button"
            type="submit"
            disabled={busy}
          >
            {busy ? "Processing..." : "Create Alert"}
          </button>
        </form>
      </section>

      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}

      <section className="alerts-list">
        <div className="alerts-list-header">
          <h2>My Alerts</h2>

          <button
            type="button"
            className="secondary-button"
            disabled={loading || busy}
            onClick={() => {
              setLoading(true);
              setRefreshKey((value) => value + 1);
            }}
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <p>Loading alerts...</p>
        ) : allAlerts.length === 0 ? (
          <p>No alerts configured yet.</p>
        ) : (
          <ul className="alerts-grid">
            {allAlerts.map((alert) => (
              <li
                className="alert-card"
                key={`${alert.type}-${alert.id}`}
              >
                <div>
                  <h3>{alert.ticker}</h3>

                  <p>
                    <strong>
                      {alert.type === "price"
                        ? "Price Threshold"
                        : "Percentage Change"}
                    </strong>
                  </p>

                  {alert.type === "price" ? (
                    <p>
                      Price {alert.condition} $
                      {Number(alert.threshold).toFixed(2)}
                    </p>
                  ) : (
                    <>
                      <p>
                        {Number(alert.threshold_percent).toFixed(2)}%
                        {" — "}{alert.direction}
                      </p>
                      <p>
                        Status: {alert.is_active ? "Active" : "Paused"}
                      </p>
                    </>
                  )}
                </div>

                {alert.type === "percent" &&
                editingId === alert.id ? (
                  <form
                    className="market-alert-form"
                    onSubmit={(event) =>
                      handleSaveEdit(event, alert)
                    }
                  >
                    <label>
                      Threshold (%)
                      <input
                        type="number"
                        min="0.0001"
                        max="100"
                        step="any"
                        required
                        value={editThreshold}
                        onChange={(event) =>
                          setEditThreshold(event.target.value)
                        }
                      />
                    </label>

                    <label>
                      Direction
                      <select
                        value={editDirection}
                        onChange={(event) =>
                          setEditDirection(event.target.value)
                        }
                      >
                        <option value="either">Either</option>
                        <option value="increase">Increase</option>
                        <option value="decrease">Decrease</option>
                      </select>
                    </label>

                    <button type="submit" disabled={busy}>
                      Save
                    </button>

                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => setEditingId(null)}
                    >
                      Cancel
                    </button>
                  </form>
                ) : (
                  <div className="market-alert-actions">
                    {alert.type === "percent" && (
                      <>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => startEditing(alert)}
                        >
                          Edit
                        </button>

                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => handleToggle(alert)}
                        >
                          {alert.is_active ? "Pause" : "Resume"}
                        </button>
                      </>
                    )}

                    <button
                      type="button"
                      className="alert-delete-button"
                      disabled={busy}
                      onClick={() => handleDelete(alert)}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
