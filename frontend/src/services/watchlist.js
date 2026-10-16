const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL ?? "";

export async function loadWatchlist(
  token,
  { signal, fetchImpl = fetch } = {}
) {
  if (!token) {
    const error = new Error("Please log in to view your watchlist.");
    error.status = 401;
    throw error;
  }

  // Retrieve saved favorites from PostgreSQL-backed API.
  const favoritesResponse = await fetchImpl(
    `${API_BASE_URL}/favorites`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      signal,
    }
  );

  if (!favoritesResponse.ok) {
    const error = new Error(
      "Unable to load your watchlist. Please try again."
    );

    error.status = favoritesResponse.status;
    throw error;
  }

  const favorites = await favoritesResponse.json();

  if (!Array.isArray(favorites)) {
    throw new Error("Invalid favorites response.");
  }

  // Extract unique ticker symbols.
  const tickers = [
    ...new Set(
      favorites.map((favorite) => favorite.ticker)
    ),
  ];

  if (tickers.length === 0) {
    return [];
  }

  // Retrieve company names using the existing stocks API.
  const stocksResponse = await fetchImpl(
    `${API_BASE_URL}/stocks`,
    { signal }
  );

  if (!stocksResponse.ok) {
    throw new Error(
      "Unable to load stock information. Please try again."
    );
  }

  const stocks = await stocksResponse.json();

  const companies = new Map(
    stocks.map((stock) => [
      stock.ticker,
      stock.company_name,
    ])
  );

  // Return the same data structure expected by Watchlist.jsx.
  return tickers.map((ticker) => ({
    ticker,
    company:
      companies.get(ticker) ??
      "Company information unavailable",
  }));
}
