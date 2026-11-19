import { useCallback, useEffect, useState } from "react";

import AlertForm from "../components/AlertForm";
import {
  createAlert,
  deleteAlert,
  getAlerts,
  getAlertToken,
} from "../features/alerts_api";

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const token = getAlertToken();

  const loadAlerts = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getAlerts();
      setAlerts(data);
    } catch (err) {
      setError(err.message || "Failed to load alerts.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      loadAlerts();
    } else {
      setLoading(false);
    }
  }, [token, loadAlerts]);

  async function handleCreate(payload) {
    setSubmitting(true);
    setMessage("");
    setError("");

    try {
      const newAlert = await createAlert(payload);

      setAlerts((previous) => [
        newAlert,
        ...previous,
      ]);

      setMessage("Stock alert created successfully.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(alertId) {
    setDeletingId(alertId);
    setError("");
    setMessage("");

    try {
      await deleteAlert(alertId);

      setAlerts((previous) =>
        previous.filter((alert) => alert.id !== alertId)
      );

      setMessage("Stock alert deleted successfully.");
    } catch (err) {
      setError(err.message || "Failed to delete alert.");
    } finally {
      setDeletingId(null);
    }
  }

  if (!token) {
    return (
      <main className="alerts-page">
        <h1>Stock Alerts</h1>
        <p>Please log in to create and manage alerts.</p>
      </main>
    );
  }

  return (
    <main className="alerts-page">
      <h1>Stock Alerts</h1>

      <p>
        Create and manage stock-price alert conditions
        for your favorite defense-sector companies.
      </p>

      <AlertForm
        onCreate={handleCreate}
        submitting={submitting}
      />

      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}

      <section className="alerts-list">
        <h2>My Alerts</h2>

        {loading ? (
          <p>Loading alerts...</p>
        ) : alerts.length === 0 ? (
          <p>No alerts configured yet.</p>
        ) : (
          <ul className="alerts-grid">
            {alerts.map((alert) => (
                <li className="alert-card" key={alert.id}>
                <div>
                  <strong>{alert.ticker}</strong>

                  <p>
                    Price{" "}
                    {alert.condition === "above"
                      ? "above"
                      : "below"}{" "}
                    ${Number(alert.threshold).toFixed(2)}
                  </p>

                  <small>
                    Created:{" "}
                    {new Date(
                      alert.created_at
                    ).toLocaleString()}
                  </small>
                </div>

                <button
                  className="alert-delete-button"
                  type="button"
                  disabled={deletingId === alert.id}
                  onClick={() => handleDelete(alert.id)}
                >
                  {deletingId === alert.id ? "Deleting..." : "Delete"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
