const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";

const TOKEN_KEY = "stock-market-auth-token";

export function getAlertToken() {
  return localStorage.getItem(TOKEN_KEY);
}

async function alertRequest(path, options = {}) {
  const token = getAlertToken();

  if (!token) {
    throw new Error("Please log in to manage alerts.");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;

    try {
      const data = await response.json();

      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (response.status === 401) {
        message = "Your session has expired. Please log in again.";
      } else if (response.status === 422) {
        message = "Please check your alert settings.";
      }
    } catch {
      // Keep the default error message.
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function getAlerts() {
  return alertRequest("/alerts");
}

export function createAlert(alert) {
  return alertRequest("/alerts", {
    method: "POST",
    body: JSON.stringify(alert),
  });
}

export function deleteAlert(alertId) {
  return alertRequest(`/alerts/${alertId}`, {
    method: "DELETE",
  });
}
