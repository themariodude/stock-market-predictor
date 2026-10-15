
const API_BASE_URL = import.meta.env.VITE_API_URL || "";

async function favoritesRequest(path, token, options = {}) {
  if (!token) {
    throw new Error("Please log in to manage favorites.");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Your session has expired. Please log in again.");
    }

    if (response.status === 403) {
      throw new Error("You do not have permission to manage favorites.");
    }

    if (response.status === 404) {
      throw new Error("Stock not found.");
    }

    throw new Error("Unable to update favorites. Please try again.");
  }

  // Handle responses without a JSON body.
  if (response.status === 204) {
    return null;
  }

  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

// Get all favorite stocks for the logged-in user.
export function getFavorites(token) {
  return favoritesRequest("/favorites", token);
}

// Add a stock to favorites.
export function addFavorite(ticker, token) {
  return favoritesRequest(
    `/favorites/${encodeURIComponent(ticker.toUpperCase())}`,
    token,
    { method: "POST" }
  );
}

// Remove a stock from favorites.
export function removeFavorite(ticker, token) {
  return favoritesRequest(
    `/favorites/${encodeURIComponent(ticker.toUpperCase())}`,
    token,
    { method: "DELETE" }
  );
}
