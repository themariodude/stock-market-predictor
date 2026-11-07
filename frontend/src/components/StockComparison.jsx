const volumeFormatter = new Intl.NumberFormat("en-US");

function formatPrice(value) {
  return Number.isFinite(value) ? `$${value.toFixed(2)}` : "—";
}

function formatPercent(value) {
  if (!Number.isFinite(value)) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function percentClass(value) {
  return value > 0 ? "positive" : value < 0 ? "negative" : "";
}

function StockComparison({ stocks, previousDate, latestDate }) {
  return (
    <section className="stock-comparison" aria-labelledby="stock-comparison-heading">
      <h2 id="stock-comparison-heading">Compare defense stocks</h2>
      <p>
        Prices and daily changes use shared trading dates: {previousDate} to{" "}
        {latestDate}. All figures use available historical market data.
      </p>
      <div className="stock-comparison-scroll" role="region" aria-label="Defense stock comparison" tabIndex="0">
        <table>
          <caption>Recent performance and activity across supported companies</caption>
          <thead>
            <tr>
              <th scope="col">Company</th>
              <th scope="col">Latest close</th>
              <th scope="col">Daily change</th>
              <th scope="col">1-month return</th>
              <th scope="col">3-month return</th>
              <th scope="col">Volume</th>
              <th scope="col">52-week low</th>
              <th scope="col">52-week high</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((stock) => (
              <tr key={stock.ticker}>
                <th scope="row">
                  <strong>{stock.ticker}</strong>
                  <span>{stock.company}</span>
                  {!stock.metrics && <small>Data unavailable</small>}
                </th>
                <td>{formatPrice(stock.metrics?.price)}</td>
                <td className={percentClass(stock.metrics?.change)}>
                  {formatPercent(stock.metrics?.change)}
                </td>
                <td className={percentClass(stock.metrics?.oneMonthReturn)}>
                  {formatPercent(stock.metrics?.oneMonthReturn)}
                </td>
                <td className={percentClass(stock.metrics?.threeMonthReturn)}>
                  {formatPercent(stock.metrics?.threeMonthReturn)}
                </td>
                <td>
                  {Number.isSafeInteger(stock.metrics?.volume)
                    ? volumeFormatter.format(stock.metrics.volume)
                    : "—"}
                </td>
                <td>{formatPrice(stock.metrics?.yearLow)}</td>
                <td>{formatPrice(stock.metrics?.yearHigh)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="stock-comparison-note">
        Returns compare unadjusted closing prices near the calendar-month
        cutoffs; dividends are excluded. Volume is shares traded on {latestDate}.
        The 52-week range uses available daily highs and lows. A dash means
        that metric is unavailable.
      </p>
    </section>
  );
}

export default StockComparison;
