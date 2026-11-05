import { Link } from "react-router-dom";
import SectorMovers from "../components/SectorMovers";
import { useEffect, useState } from "react";
import {
  calculatePercentChange,
  getSectorMovers,
} from "../utils/stockCalculations";


const API_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";

function getTodayInNewYork() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());

  const get = (type) =>
    parts.find((part) => part.type === type).value;

  return `${get("year")}-${get("month")}-${get("day")}`;
}

async function getJSON(url, signal) {
  const response = await fetch(url, { signal });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${url}`);
  }

  return response.json();
}


function Dashboard() {
  const [marketStocks, setMarketStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [period, setPeriod] = useState("");
  const [unavailable, setUnavailable] = useState(0);


  useEffect(() => {
    const controller = new AbortController();

    async function loadStocks() {
      try {
        setLoading(true);
        setError("");

        // Retrieve supported defense-sector stocks.
        const companies = await getJSON(
          `${API_URL}/stocks`,
          controller.signal
        );

        if (!Array.isArray(companies)) {
          throw new Error("Invalid supported-stocks response");
        }

        const today = getTodayInNewYork();

        // Retrieve each stock's historical prices.
        const results = await Promise.allSettled(
          companies.map(async (company) => {
            const result = await getJSON(
              `${API_URL}/stocks/${company.ticker}/history`,
              controller.signal
            );

            if (!Array.isArray(result.data)) {
              throw new Error("Missing historical data");
            }

            const records = result.data
              .filter((record) =>
                typeof record.date === "string" &&
                /^\d{4}-\d{2}-\d{2}$/.test(record.date) &&
                record.date < today &&
                typeof record.close === "number" &&
                Number.isFinite(record.close) &&
                record.close > 0
              )
              .sort((a, b) =>
                a.date.localeCompare(b.date)
              );

            if (records.length < 2) {
              throw new Error("Insufficient historical data");
            }

            return { company, records };
          })
        );

        if (controller.signal.aborted) return;

        const histories = results
          .filter((result) => result.status === "fulfilled")
          .map((result) => result.value);

        if (histories.length === 0) {
          throw new Error("No valid stock histories available");
        }

        // Find trading dates shared by the available stocks.
        const commonDates = histories[0].records
          .map((record) => record.date)
          .filter((date) =>
            histories.every((item) =>
              item.records.some((record) => record.date === date)
            )
          )
          .sort();

        if (commonDates.length < 2) {
          throw new Error("No common comparison dates available");
        }

        const previousDate = commonDates.at(-2);
        const latestDate = commonDates.at(-1);

        const calculated = histories.flatMap(
          ({ company, records }) => {
            const previous = records.find(
              (record) => record.date === previousDate
            );
            const latest = records.find(
              (record) => record.date === latestDate
            );

            const change = calculatePercentChange(
              previous.close,
              latest.close
            );

            if (change === null) return [];

            return [{
              ticker: company.ticker,
              company: company.company_name || company.ticker,
              price: latest.close,
              change,
            }];
          }
        );

        setMarketStocks(calculated);
        setPeriod(`${previousDate} to ${latestDate}`);
        setUnavailable(companies.length - calculated.length);
      } catch (err) {
        if (controller.signal.aborted) return;

        console.error("Stock loading failed:", err);
        setError("Unable to load sector market data.");
        setMarketStocks([]);
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    loadStocks();

    return () => controller.abort();
  }, []);


  // Rank stocks using real backend data.
  const { gainers, decliners } = getSectorMovers(marketStocks);

  return (

    <main className="dashboard-page">
      <Link to="/" className="back-button">
        ← Back to Home
      </Link>

      <Link to="/account" className="account-link">
        Saved Information
      </Link>

      <h1>Defense Stock Dashboard</h1>

      <Link to="/watchlist" className="back-button">
        My Watchlist
      </Link>

      <p>Select a stock to view its historical performance.</p>

      {loading && <p>Loading market data...</p>}

      {error && <p role="alert">{error}</p>}

      {!loading && !error && (
        <>
          <p>Comparison period: {period}</p>

          {unavailable > 0 && (
            <p role="status">
              Data unavailable for {unavailable} stock(s).
            </p>
          )}

          <SectorMovers
            gainers={gainers}
            decliners={decliners}
          />

          <section className="stock-grid">
            {marketStocks.map((stock) => (
              <Link
                key={stock.ticker}
                to={`/stocks/${stock.ticker}`}
                className="stock-card"
              >
                <h2>{stock.ticker}</h2>
                <p>{stock.company}</p>
                <h3>${stock.price.toFixed(2)}</h3>

                <p
                  className={
                    stock.change >= 0
                      ? "positive"
                      : "negative"
                  }
                >
                  {stock.change > 0 ? "+" : ""}
                  {stock.change.toFixed(2)}%
                </p>
              </Link>
            ))}
          </section>
        </>
      )}
    </main>
  );

}

export default Dashboard;
