import { summarizeSector } from "../utils/stockCalculations";

function SectorSummary({ stocks, supportedCount, period }) {
  const { averageChange, gainers, decliners } = summarizeSector(stocks);
  const averageClass = averageChange > 0
    ? "positive"
    : averageChange < 0
      ? "negative"
      : "";
  const averageLabel = averageChange === null
    ? "Unavailable"
    : `${averageChange > 0 ? "+" : ""}${averageChange.toFixed(2)}%`;

  return (
    <section className="sector-summary" aria-labelledby="sector-summary-heading">
      <h2 id="sector-summary-heading">Defense sector at a glance</h2>
      <p>
        A snapshot of the defense stocks supported by this app, using their
        latest shared trading dates.
      </p>
      <dl className="sector-summary-grid">
        <div>
          <dt>Supported stocks</dt>
          <dd>{supportedCount}</dd>
        </div>
        <div>
          <dt>Average price change</dt>
          <dd className={averageClass}>
            {averageLabel}
          </dd>
        </div>
        <div>
          <dt>Stocks up</dt>
          <dd>{gainers}</dd>
        </div>
        <div>
          <dt>Stocks down</dt>
          <dd>{decliners}</dd>
        </div>
      </dl>
      <p className="sector-summary-note">
        {period}. Equal-weighted average of close-to-close price changes for{" "}
        {stocks.length} of {supportedCount} supported stocks with available data.
      </p>
    </section>
  );
}

export default SectorSummary;
