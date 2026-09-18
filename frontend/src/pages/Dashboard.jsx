import { Link } from "react-router-dom";

function Dashboard() {
  // Placeholder data for defense-sector stocks.
  const stocks = [
    {
      ticker: "LMT",
      company: "Lockheed Martin",
      price: 472.35,
      change: 1.27,
    },
    {
      ticker: "RTX",
      company: "RTX",
      price: 158.42,
      change: 0.82,
    },
    {
      ticker: "NOC",
      company: "Northrop Grumman",
      price: 612.18,
      change: -0.41,
    },
    {
      ticker: "GD",
      company: "General Dynamics",
      price: 331.54,
      change: 0.35,
    },
    {
      ticker: "LHX",
      company: "L3Harris Technologies",
      price: 298.61,
      change: 1.11,
    },
    {
      ticker: "BA",
      company: "Boeing",
      price: 221.74,
      change: -0.63,
    },
  ];

  return (
    <main className="dashboard-page">
      <Link to="/" className="back-button">
        ← Back to Home
      </Link>
      <h1>Defense Stock Dashboard</h1>
      <p>Select a stock to view its historical performance.</p>
      {/* Grid of clickable stock cardsthat link to detail page
          using the ticker as the URL param (matches ":ticker" in App.jsx) */}
      <section className="stock-grid">
        {stocks.map((stock) => (
          <Link
            key={stock.ticker}
            to={`/stocks/${stock.ticker}`}
            className="stock-card"
          >
            <h2>{stock.ticker}</h2>
            <p>{stock.company}</p>
            <h3>${stock.price.toFixed(2)}</h3>

            <p className={stock.change >= 0 ? "positive" : "negative"}>
              {stock.change >= 0 ? "+" : ""}
              {stock.change.toFixed(2)}%
            </p>
          </Link>
        ))}
      </section>
    </main>
  );
}

export default Dashboard;
