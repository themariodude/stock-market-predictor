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
   { date: "2023-11-21", close: 492.56 },
   { date: "2024-05-01", close: 512.93 },
   { date: "2024-12-23", close: 507.12 },
   { date: "2025-01-02", close: 482.14 },
   { date: "2025-04-01", close: 471.83 },
   { date: "2025-07-01", close: 463.72 },
   { date: "2025-10-01", close: 489.31 },
   { date: "2026-01-02", close: 501.44 },
   { date: "2026-04-01", close: 493.26 },
   { date: "2026-07-01", close: 507.19 },
   { date: "2026-09-01", close: 512.37 },
   { date: "2026-09-13", close: 519.59 },
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
