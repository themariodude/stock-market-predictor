# stock-market-predictor
CPSC 491 Stock Market Predictor for defense-sector analysis and forecasting

Deployment credential setup and verification: [US-60](README-US60.md).

## View Watchlist

Open **My Watchlist** from the dashboard or account page, or visit `/watchlist`.
Investors must log in; after logging in from this page, they return to their
watchlist. Each saved stock shows its ticker and company name and links to its
stock details. The page includes loading, empty, and error states with retry.

The watchlist uses the authenticated `/auth/me` account's `saved_stocks` and
company names from `/stocks`. The current backend demo account has LMT, RTX,
and NOC saved. Adding or removing favorites is outside this viewing story.

To verify locally, start the backend and frontend, log in with the configured
demo investor, and open My Watchlist. Confirm only saved stocks appear and each
opens its detail page. In browser developer tools, clearing the auth token
should require login; blocking `/auth/me` should show an error with Try Again.
An account with no saved stocks should show the empty state and Explore Stocks.

Frontend checks (run from `frontend`): `npm test`, `npm run lint`, `npm run build`.
On Windows PowerShell, use `npm.cmd` if script execution policy blocks `npm`.
