import { useEffect, useState } from "react";

import AlertForm from "../components/AlertForm";
import {
  createAlert,
  deleteAlert,
  getAlerts,
  getAlertToken,
} from "../features/alerts_api";

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(
    () => Boolean(getAlertToken())
  );
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const token = getAlertToken();

  // Load saved alerts when the page opens.
  useEffect(() => {
    if (!token) return;

    let cancelled = false;

    async function fetchAlerts() {
      try {
        const data = await getAlerts();

        if (!cancelled) {
          setAlerts(data);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.message || "Failed to load alerts."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchAlerts();

    return () => {
      cancelled = true;
    };
  }, [token]);

  // US-39: Create a new stock alert.
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

      setMessage(
        "Stock alert created successfully."
      );
    } catch (err) {
      setError(
        err.message || "Failed to create alert."
      );
      throw err;
    } finally {
      setSubmitting(false);
    }
  }

  // US-40: Delete an existing stock alert.
  async function handleDelete(alertId) {
    setDeletingId(alertId);
    setError("");
    setMessage("");

    try {
      await deleteAlert(alertId);

      setAlerts((previous) =>
        previous.filter(
          (alert) => alert.id !== alertId
        )
      );

      setMessage(
        "Stock alert deleted successfully."
      );
    } catch (err) {
      setError(
        err.message || "Failed to delete alert."
      );
    } finally {
      setDeletingId(null);
    }
  }

  // Require authentication.
  if (!token) {
    return (
      <main className="alerts-page">
        <h1>Stock Alerts</h1>
        <p>
          Please log in to create and manage alerts.
        </p>
      </main>
    );
  }

  return (
    <main className="alerts-page">
      <h1>Stock Alerts</h1>

      <p>
        Create and manage stock-price alert
        conditions for your favorite
        defense-sector companies.
      </p>

      {/* US-39: Create Alert Form */}
      <AlertForm
        onCreate={handleCreate}
        submitting={submitting}
      />

      {/* Success and Error Messages */}
      {message && (
        <p role="status">{message}</p>
      )}

      {error && (
        <p role="alert">{error}</p>
      )}

      {/* US-40: Manage Saved Alerts */}
      <section className="alerts-list">
        <h2>My Alerts</h2>

        {loading ? (
          <p>Loading alerts...</p>
        ) : alerts.length === 0 ? (
          <p>No alerts configured yet.</p>
        ) : (
          <ul className="alerts-grid">
            {alerts.map((alert) => (
              <li
                className="alert-card"
                key={alert.id}
              >
                <div>
                  <strong>{alert.ticker}</strong>

                  <p>
                    Price{" "}
                    {alert.condition === "above"
                      ? "above"
                      : "below"}{" "}
                    $
                    {Number(
                      alert.threshold
                    ).toFixed(2)}
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
                  disabled={
                    deletingId === alert.id
                  }
                  onClick={() =>
                    handleDelete(alert.id)
                  }
                >
                  {deletingId === alert.id
                    ? "Deleting..."
                    : "Delete"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
