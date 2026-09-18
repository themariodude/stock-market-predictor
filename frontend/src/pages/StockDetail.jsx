import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import StockChart from "../components/StockChart";
import TimeRangeSelector from "../components/TimeRangeSelector";

function StockDetail() {
  // Reads the ":ticker" segment from the current URL
  const { ticker } = useParams();
  // Currently selected time range for the chart
  const [range, setRange] = useState("1Y");

  // Static historical closing prices.
  // TODO: stock/range currently only shows the same five days of data.
  const history = [
    { date: "Sep 1", close: 465.2 },
    { date: "Sep 2", close: 468.7 },
    { date: "Sep 3", close: 470.1 },
    { date: "Sep 4", close: 469.4 },
    { date: "Sep 5", close: 472.35 },
  ];

  return (
    <main className="stock-detail-page">
      <Link to="/dashboard">← Back to Dashboard</Link>

      <h1>{ticker}</h1>

      <section className="stock-history">
        <div className="chart-header">
          <h2>Historical Performance</h2>

          <TimeRangeSelector
            selectedRange={range}
            onRangeChange={setRange}
          />
        </div>

        <StockChart 
          data={history}
          range={range} />
      </section>
    </main>
  );
}

export default StockDetail;
