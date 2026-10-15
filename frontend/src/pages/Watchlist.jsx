import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { loadWatchlist } from "../services/watchlist";

function Watchlist() {
  const navigate = useNavigate();
  const [stocks, setStocks] = useState([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem("stock-market-auth-token");
    function requireLogin() {
      navigate("/login", { replace: true, state: { from: "/watchlist" } });
    }

    if (!token) {
      requireLogin();
      return;
    }

    const controller = new AbortController();
    async function load() {
      try {
        const result = await loadWatchlist(token, { signal: controller.signal });
        if (!controller.signal.aborted) setStocks(result);
      } catch (loadError) {
        if (controller.signal.aborted) return;
        if (loadError.status === 401) {
          localStorage.removeItem("stock-market-auth-token");
          localStorage.removeItem("stock-market-auth-user");
          requireLogin();
          return;
        }
        setError("Unable to load your watchlist. Please try again.");
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }

    load();
    return () => controller.abort();
  }, [navigate, attempt]);

  function retry() {
    setError("");
    setStocks([]);
    setIsLoading(true);
    setAttempt((value) => value + 1);
  }

  return (
    <main className="watchlist-page">
      <nav className="watchlist-nav" aria-label="Watchlist navigation">
        <Link to="/dashboard" className="back-button">Back to Dashboard</Link>
        <Link to="/account" className="back-button">Saved Information</Link>
      </nav>
      <h1>My Watchlist</h1>
      <p>Your favorited stocks, together in one place. Select a stock to view its details.</p>

      {isLoading && <p role="status">Loading your watchlist...</p>}
      {!isLoading && error && (
        <div className="watchlist-message">
          <p className="form-error" role="alert">{error}</p>
          <button className="secondary-button" onClick={retry} type="button">Try Again</button>
        </div>
      )}
      {!isLoading && !error && stocks.length === 0 && (
        <section className="watchlist-message" aria-label="Empty watchlist">
          <h2>No favorited stocks yet</h2>
          <p>Your saved stocks will appear here.</p>
          <Link to="/dashboard" className="primary-button">Explore Stocks</Link>
        </section>
      )}
      {!isLoading && !error && stocks.length > 0 && (
        <section aria-label="Favorited stocks">
          <p>{stocks.length} {stocks.length === 1 ? "stock" : "stocks"} in your watchlist</p>
          <ul className="stock-grid watchlist-grid">
            {stocks.map((stock) => (
              <li key={stock.ticker}>
                <Link className="stock-card" to={`/stocks/${encodeURIComponent(stock.ticker)}`}>
                  <h2>{stock.ticker}</h2>
                  <p>{stock.company}</p>
                  <span>View stock details &rarr;</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}

export default Watchlist;
