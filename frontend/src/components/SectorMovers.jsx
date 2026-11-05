
import { Link } from "react-router-dom";

function SectorMovers({
  gainers,
  decliners,
}) {
  return (
    <section className="sector-movers">
      <h2>Sector Movers</h2>

      <h3>Top Gainers</h3>

      {gainers.length === 0 && (
        <p>No stocks gained during this period.</p>
      )}

      {gainers.map((stock) => (
        <p key={stock.ticker} className="positive">
          <Link to={`/stocks/${stock.ticker}`}>
            {stock.ticker} — {stock.company}
          </Link>
          : +{stock.change.toFixed(2)}%
          {" "}(${stock.price.toFixed(2)})
        </p>
      ))}

      <h3>Top Decliners</h3>

      {decliners.length === 0 && (
        <p>No stocks declined during this period.</p>
      )}

      {decliners.map((stock) => (
        <p key={stock.ticker} className="negative">
          <Link to={`/stocks/${stock.ticker}`}>
            {stock.ticker} — {stock.company}
          </Link>
          : {stock.change.toFixed(2)}%
          {" "}(${stock.price.toFixed(2)})
        </p>
      ))}
    </section>
  );
}

export default SectorMovers;
