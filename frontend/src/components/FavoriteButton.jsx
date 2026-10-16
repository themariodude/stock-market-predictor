import { useEffect, useState } from "react";

import {
  getFavorites,
  addFavorite,
  removeFavorite,
} from "../features/favorites_api";

import "./FavoriteButton.css";

export default function FavoriteButton({ ticker, token }) {
  const [isFavorite, setIsFavorite] = useState(false);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState("");
  const [statusKnown, setStatusKnown] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadFavoriteStatus() {
      setError("");
      setIsFavorite(false);
      setStatusKnown(false);

      if (!token || !ticker) {
        setChecking(false);
        return;
      }

      setChecking(true);

      try {
        const favorites = await getFavorites(token);

        if (!active) return;

        // Expected backend response:
        // [{ ticker: "LMT" }, { ticker: "RTX" }]
        if (!Array.isArray(favorites)) {
          throw new Error("Unexpected favorites response.");
        }

        const found = favorites.some(
          (stock) =>
            stock.ticker?.toUpperCase() === ticker.toUpperCase()
        );

        setIsFavorite(found);
        setStatusKnown(true);
      } catch (err) {
        if (active) {
          setError(err.message);
        }
      } finally {
        if (active) {
          setChecking(false);
        }
      }
    }

    loadFavoriteStatus();

    return () => {
      active = false;
    };
  }, [ticker, token]);

  async function handleToggle() {
    if (!token || loading || checking || !statusKnown) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      if (isFavorite) {
        await removeFavorite(ticker, token);
        setIsFavorite(false);
      } else {
        await addFavorite(ticker, token);
        setIsFavorite(true);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <p className="favorite-login-message">
        Log in to save favorite stocks.
      </p>
    );
  }

  return (
    <div className="favorite-container">
      <button
        type="button"
        className={`favorite-button ${
          isFavorite ? "favorited" : ""
        }`}
        onClick={handleToggle}
        disabled={loading || checking || !statusKnown}
        aria-pressed={isFavorite}
        aria-label={
          isFavorite
            ? `Remove ${ticker} from favorites`
            : `Add ${ticker} to favorites`
        }
      >
        <span className="favorite-star" aria-hidden="true">
          {isFavorite ? "★" : "☆"}
        </span>

        <span>
          {checking
            ? "Checking..."
            : loading
              ? "Saving..."
              : isFavorite
                ? "Favorited"
                : "Add to Favorites"}
        </span>
      </button>

      {error && (
        <p className="favorite-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
