
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  getMarketNotifications,
  markMarketNotificationRead,
} from "../services/marketAlerts";

const TOKEN_KEY = "stock-market-auth-token";
const USER_KEY = "stock-market-auth-user";

function Notifications() {
  const navigate = useNavigate();

  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);

    if (!token) {
      navigate("/login", {
        replace: true,
        state: { from: "/notifications" },
      });
      return;
    }

    let active = true;

    async function loadNotifications() {
      setLoading(true);
      setError("");

      try {
        const data = await getMarketNotifications({ token });

        if (!active) return;

        if (!Array.isArray(data)) {
          throw new Error("Invalid notifications response.");
        }

        setNotifications(data);
      } catch (requestError) {
        if (!active) return;

        if (requestError?.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);

          navigate("/login", {
            replace: true,
            state: { from: "/notifications" },
          });
          return;
        }

        setError(
          requestError?.message ||
            "Unable to load notifications.",
        );
      } finally {
        if (active) setLoading(false);
      }
    }

    loadNotifications();

    return () => {
      active = false;
    };
  }, [navigate, attempt]);

  async function handleMarkRead(notificationId) {
    const token = localStorage.getItem(TOKEN_KEY);

    if (!token) {
      navigate("/login", {
        replace: true,
        state: { from: "/notifications" },
      });
      return;
    }

    setBusyId(notificationId);
    setError("");

    try {
      const updated = await markMarketNotificationRead(
        notificationId,
        { token },
      );

      setNotifications((current) =>
        current.map((notification) =>
          notification.id === notificationId
            ? updated
            : notification,
        ),
      );
    } catch (requestError) {
      if (requestError?.status === 401) {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);

        navigate("/login", {
          replace: true,
          state: { from: "/notifications" },
        });
        return;
      }

      setError(
        requestError?.message ||
          "Unable to mark notification as read.",
      );
    } finally {
      setBusyId(null);
    }
  }

  const unreadCount = notifications.filter(
    (notification) => !notification.is_read,
  ).length;

  return (
    <main className="market-alerts-page">
      <nav
        className="market-alerts-nav"
        aria-label="Notifications navigation"
      >
        <Link to="/dashboard" className="back-button">
          Back to Dashboard
        </Link>

        <Link to="/market-alerts" className="back-button">
          My Market Alerts
        </Link>
      </nav>

      <h1>Market Notifications</h1>

      <p>
        Significant stock-price changes detected by your
        configured market alerts.
      </p>

      <section
        className="market-alert-panel"
        aria-label="Notification history"
      >
        <div className="notification-heading">
          <h2>Notification History</h2>

          <button
            type="button"
            className="secondary-button"
            disabled={loading}
            onClick={() => setAttempt((value) => value + 1)}
          >
            Refresh
          </button>
        </div>

        {loading && (
          <p role="status">Loading notifications...</p>
        )}

        {error && (
          <div>
            <p className="form-error" role="alert">
              {error}
            </p>
            <button
              type="button"
              className="secondary-button"
              onClick={() => setAttempt((value) => value + 1)}
            >
              Try Again
            </button>
          </div>
        )}

        {!loading && !error && (
          <p>
            {unreadCount} unread notification
            {unreadCount === 1 ? "" : "s"}
          </p>
        )}

        {!loading &&
          !error &&
          notifications.length === 0 && (
            <div className="notification-empty">
              <h3>No notifications yet</h3>
              <p>
                When a configured market-change threshold
                is reached, notifications will appear here.
              </p>
              <Link to="/market-alerts" className="primary-button">
                Configure Market Alerts
              </Link>
            </div>
          )}

        {!loading &&
          !error &&
          notifications.map((notification) => {
            const change = Number(
              notification.observed_change_percent,
            );

            const changeText = Number.isFinite(change)
              ? `${change > 0 ? "+" : ""}${change.toFixed(2)}%`
              : "Unavailable";

            const observedPrice = Number(
              notification.observed_price,
            );

            const referencePrice = Number(
              notification.reference_price,
            );

            return (
              <article
                key={notification.id}
                className={`notification-card ${
                  notification.is_read
                    ? "notification-read"
                    : "notification-unread"
                }`}
              >
                <div className="notification-heading">
                  <h3>{notification.ticker}</h3>
                  <span>
                    {notification.is_read ? "Read" : "Unread"}
                  </span>
                </div>

                <p>
                  Market change: <strong>{changeText}</strong>
                </p>

                <p>
                  Previous close:{" "}
                  {Number.isFinite(referencePrice)
                    ? `$${referencePrice.toFixed(2)}`
                    : "Unavailable"}
                </p>

                <p>
                  Observed close:{" "}
                  {Number.isFinite(observedPrice)
                    ? `$${observedPrice.toFixed(2)}`
                    : "Unavailable"}
                </p>

                <p>
                  Alert threshold:{" "}
                  {notification.threshold_percent}%
                </p>

                <p className="notification-date">
                  Detected:{" "}
                  {new Date(
                    notification.triggered_at,
                  ).toLocaleString()}
                </p>

                {!notification.is_read && (
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={busyId !== null}
                    onClick={() =>
                      handleMarkRead(notification.id)
                    }
                  >
                    {busyId === notification.id
                      ? "Updating..."
                      : "Mark as Read"}
                  </button>
                )}
              </article>
            );
          })}
      </section>
    </main>
  );
}

export default Notifications;
