
/**
 * US-41: Authenticated Market Alerts and Notifications API.
 */

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL ?? "";

const TOKEN_STORAGE_KEY = "stock-market-auth-token";

async function apiRequest(
  path,
  { method = "GET", body, token, fetchImpl } = {},
) {
  const accessToken =
    token ?? globalThis.localStorage?.getItem(TOKEN_STORAGE_KEY);

  if (!accessToken) {
    throw new Error("Please log in to manage market alerts.");
  }

  const requestHeaders = {
    Authorization: `Bearer ${accessToken}`,
  };

  if (body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
  }

  const response = await (fetchImpl ?? globalThis.fetch)(
    `${API_BASE_URL}${path}`,
    {
      method,
      headers: requestHeaders,
      ...(body !== undefined
        ? { body: JSON.stringify(body) }
        : {}),
    },
  );

  if (!response.ok) {
    let message = `Request failed (${response.status}).`;

    try {
      const data = await response.json();

      if (typeof data.detail === "string") {
        message = data.detail;
      }
    } catch {
      // Preserve the HTTP error if no JSON response is available.
    }

    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function getMarketAlerts(options) {
  return apiRequest("/market-alerts", options);
}

export function createMarketAlert(payload, options = {}) {
  return apiRequest("/market-alerts", {
    ...options,
    method: "POST",
    body: payload,
  });
}

export function updateMarketAlert(alertId, payload, options = {}) {
  return apiRequest(`/market-alerts/${encodeURIComponent(alertId)}`, {
    ...options,
    method: "PATCH",
    body: payload,
  });
}

export function deleteMarketAlert(alertId, options = {}) {
  return apiRequest(`/market-alerts/${encodeURIComponent(alertId)}`, {
    ...options,
    method: "DELETE",
  });
}

export function getMarketNotifications(options) {
  return apiRequest("/notifications", options);
}

export function markMarketNotificationRead(
  notificationId,
  options = {},
) {
  return apiRequest(
    `/notifications/${encodeURIComponent(notificationId)}/read`,
    {
      ...options,
      method: "PATCH",
    },
  );
}
