# US-22 & US-23 - Favorite Stock and Remove Favorite Stock

As a logged-in investor, I want to favorite a stock so that I can easily find companies I regularly follow.

As a logged-in investor, I want to remove stocks from my favorites so that my saved stocks remain relevant.

## Files

- `backend/app/models/favorite.py`
- `backend/app/models/__init__.py`
- `backend/app/api/favorites.py`
- `backend/alembic/versions/d8e56a559ac0_create_favorites_table.py`
- `frontend/src/components/FavoriteButton.jsx`
- `frontend/src/components/FavoriteButton.css`
- `frontend/src/features/favorites_api.js`
- `frontend/src/pages/StockDetail.jsx`
- `frontend/vite.config.js`

## API

```text
GET /favorites
POST /favorites/{ticker}
DELETE /favorites/{ticker}
```

`GET /favorites` returns the authenticated user's saved favorite stocks.

`POST /favorites/{ticker}` adds a supported stock to the authenticated user's favorites.

`DELETE /favorites/{ticker}` removes a stock from the authenticated user's favorites.

All three endpoints require bearer-token authentication.

Favorites are stored in PostgreSQL and associated with the authenticated user's email. Duplicate favorites are prevented through a database unique constraint.

## Run Tests

From the repository root:

```bash
cd backend
python -m pytest
```

To verify the database migration:

```bash
alembic -c alembic.ini upgrade head
```

To run frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

## Usage

1. Log in to the application.
2. Navigate to a stock's detail page.
3. Click **Add to Favorites** to save the stock.
4. The button changes to **Favorited**.
5. Click the button again to remove the stock.
6. Refresh the page to verify that the favorite state persists.