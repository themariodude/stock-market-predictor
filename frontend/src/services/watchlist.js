const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL ?? "";

export async function loadWatchlist(token, { signal, fetchImpl = fetch } = {}) {
  const accountResponse = await fetchImpl(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    signal,
  });

  if (!accountResponse.ok) {
    const error = new Error("Unable to load your watchlist. Please try again.");
    error.status = accountResponse.status;
    throw error;
  }

  const account = await accountResponse.json();
  const tickers = [...new Set(account.saved_stocks)];
  if (tickers.length === 0) return [];

  const stocksResponse = await fetchImpl(`${API_BASE_URL}/stocks`, { signal });
  if (!stocksResponse.ok) {
    throw new Error("Unable to load stock information. Please try again.");
  }

  const stocks = await stocksResponse.json();
  const companies = new Map(stocks.map((stock) => [stock.ticker, stock.company_name]));
  return tickers.map((ticker) => ({
    ticker,
    company: companies.get(ticker) ?? "Company information unavailable",
  }));
}
