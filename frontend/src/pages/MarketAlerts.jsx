
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  createMarketAlert,
  deleteMarketAlert,
  getMarketAlerts,
  updateMarketAlert,
} from "../services/marketAlerts";

const TOKEN_KEY = "stock-market-auth-token";
const USER_KEY = "stock-market-auth-user";

function MarketAlerts() {
  const navigate = useNavigate();

  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);

  const [ticker, setTicker] = useState("");
  const [threshold, setThreshold] = useState("5");
  const [direction, setDirection] = useState("either");

  const [editingId, setEditingId] = useState(null);
  const [editThreshold, setEditThreshold] = useState("");
  const [editDirection, setEditDirection] = useState("either");

  function requireLogin() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    navigate("/login", {
      replace: true,
      state: { from: "/alerts" },
    });
  }

  function getToken() {
    const token = localStorage.getItem(TOKEN_KEY);

    if (!token) {
      requireLogin();
      throw new Error("Please log in to manage alerts.");
    }

    return token;
  }

  function handleError(requestError) {
    if (requestError?.status === 401) {
      requireLogin();
      return;
    }

    setError(requestError?.message || "Something went wrong.");
  }

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);

    if (!token) {
      navigate("/login", {
        replace: true,
        state: { from: "/alerts" },
      });
      return;
    }

    let active = true;

    async function loadAlerts() {
      try {
        const data = await getMarketAlerts({ token });

        if (!active) return;

        if (!Array.isArray(data)) {
          throw new Error("Invalid market alerts response.");
        }

        setAlerts(data);
        setError("");
      } catch (requestError) {
        if (!active) return;

        if (requestError?.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
          navigate("/login", {
            replace: true,
            state: { from: "/alerts" },
          });
          return;
        }

        setError(
          requestError?.message || "Unable to load market alerts.",
        );
      } finally {
        if (active) setLoading(false);
      }
    }

    loadAlerts();

    return () => {
      active = false;
    };
  }, [navigate, attempt]);

  async function handleCreate(event) {
    event.preventDefault();

    const percent = Number(threshold);

    if (!Number.isFinite(percent) || percent <= 0 || percent > 100) {
      setError("Threshold must be greater than 0 and at most 100.");
      return;
    }

    setBusy(true);
    setError("");

    try {
      const created = await createMarketAlert(
        {
          ticker: ticker.trim().toUpperCase(),
          threshold_percent: percent,
          direction,
        },
        { token: getToken() },
      );

      setAlerts((current) => [created, ...current]);
      setTicker("");
      setThreshold("5");
      setDirection("either");
    } catch (requestError) {
      handleError(requestError);
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

  async function handleUpdate(event, alertId) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      const updated = await updateMarketAlert(
        alertId,
        {
          threshold_percent: Number(editThreshold),
          direction: editDirection,
        },
        { token: getToken() },
      );

      setAlerts((current) =>
        current.map((alert) =>
          alert.id === alertId ? updated : alert,
        ),
      );

      setEditingId(null);
    } catch (requestError) {
      handleError(requestError);
    } finally {
      setBusy(false);
    }
  }

  async function handleToggle(alert) {
    setBusy(true);
    setError("");

    try {
      const updated = await updateMarketAlert(
        alert.id,
        { is_active: !alert.is_active },
        { token: getToken() },
      );

      setAlerts((current) =>
        current.map((item) =>
          item.id === alert.id ? updated : item,
        ),
      );
    } catch (requestError) {
      handleError(requestError);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(alert) {
    if (!window.confirm(`Delete the ${alert.ticker} alert?`)) {
      return;
    }

    setBusy(true);
    setError("");

    try {
      await deleteMarketAlert(alert.id, {
        token: getToken(),
      });

      setAlerts((current) =>
        current.filter((item) => item.id !== alert.id),
      );
    } catch (requestError) {
      handleError(requestError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="market-alerts-page">
      <nav className="market-alerts-nav" aria-label="Alerts navigation">
        <Link to="/dashboard" className="back-button">
          Back to Dashboard
        </Link>
        <Link to="/watchlist" className="back-button">
          My Watchlist
        </Link>
        <Link to="/notifications" className="back-button">
          Notifications
        </Link>
      </nav>

      <h1>Market Change Alerts</h1>
      <p>
        Configure alerts for significant daily stock-price changes.
        Notifications are checked after the market closes.
      </p>

      <section className="market-alert-panel">
        <h2>Create Alert</h2>

        <form onSubmit={handleCreate} className="market-alert-form">
          <label>
            Stock Ticker
            <input
              type="text"
              value={ticker}
              onChange={(event) => setTicker(event.target.value)}
              placeholder="LMT"
              maxLength={10}
              required
            />
          </label>

          <label>
            Change Threshold (%)
            <input
              type="number"
              value={threshold}
              onChange={(event) => setThreshold(event.target.value)}
              min="0.1"
              max="100"
              step="0.1"
              required
            />
          </label>

          <label>
            Direction
            <select
              value={direction}
              onChange={(event) => setDirection(event.target.value)}
            >
              <option value="either">Increase or Decrease</option>
              <option value="increase">Increase</option>
              <option value="decrease">Decrease</option>
            </select>
          </label>

          <button type="submit" className="primary-button" disabled={busy}>
            {busy ? "Processing..." : "Create Alert"}
          </button>
        </form>
      </section>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <section className="market-alert-panel" aria-label="Saved alerts">
        <h2>My Alerts</h2>

        {loading && <p role="status">Loading market alerts...</p>}

        {!loading && error && (
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setLoading(true);
              setAttempt((value) => value + 1);
            }}
          >
            Refresh Alerts
          </button>
        )}

        {!loading && alerts.length === 0 && (
          <p>No market alerts configured yet.</p>
        )}

        {!loading && alerts.map((alert) => (
          <article className="market-alert-card" key={alert.id}>
            <div className="market-alert-card-header">
              <h3>{alert.ticker}</h3>
              <span>
                {alert.is_active ? "Active" : "Paused"}
              </span>
            </div>

            <p>
              {Number(alert.threshold_percent).toFixed(1)}% — {alert.direction}
            </p>

            {editingId === alert.id ? (
              <form
                className="market-alert-form"
                onSubmit={(event) => handleUpdate(event, alert.id)}
              >
                <label>
                  Threshold (%)
                  <input
                    type="number"
                    min="0.0001"
                    max="100"
                    step="0.0001"
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
                  Save Changes
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
                <button
                  type="button"
                  className="secondary-button"
                  disabled={busy}
                  onClick={() => startEditing(alert)}
                >
                  Edit
                </button>

                <button
                  type="button"
                  className="secondary-button"
                  disabled={busy}
                  onClick={() => handleToggle(alert)}
                >
                  {alert.is_active ? "Pause" : "Resume"}
                </button>

                <button
                  type="button"
                  className="secondary-button"
                  disabled={busy}
                  onClick={() => handleDelete(alert)}
                >
                  Delete
                </button>
              </div>
            )}
          </article>
        ))}
      </section>
    </main>
  );
}

export default MarketAlerts;
