import { useState } from "react";
import "./FavoriteButton.css";

export default function FavoriteButton({ ticker }) {
  const [isFavorite, setIsFavorite] = useState(false);

  function handleFavoriteClick() {
    setIsFavorite((previous) => !previous);
  }

  return (
    <button
      type="button"
      className={`favorite-button ${isFavorite ? "favorited" : ""}`}
      onClick={handleFavoriteClick}
      aria-pressed={isFavorite}
      aria-label={
        isFavorite
          ? `Remove ${ticker} from favorites`
          : `Add ${ticker} to favorites`
      }
    >
      <span className="favorite-star">
        {isFavorite ? "★" : "☆"}
      </span>

      <span>
        {isFavorite ? "Favorited" : "Add to Favorites"}
      </span>
    </button>
  );
}
