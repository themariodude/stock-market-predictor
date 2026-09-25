<<<<<<< HEAD
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function StockChart({ data, range }) {
  if (!data || data.length === 0) {
    return <p>No historical data available.</p>;
  }

  const filterDataByRange = () => {
    if (range === "MAX") {
      return data;
    }

    const daysByRange = {
      "1M": 30,
      "3M": 90,
      "6M": 180,
      "1Y": 365,
      "5Y": 1825,
    };

    const days = daysByRange[range];

    // If an unknown range is provided, display all data.
    if (!days) {
      return data;
    }

    // Use the newest available stock date rather than today's date.
    const newestDate = new Date(data[data.length - 1].date);
    const cutoffDate = new Date(newestDate);

    cutoffDate.setDate(cutoffDate.getDate() - days);

    return data.filter((point) => {
      const pointDate = new Date(point.date);
      return pointDate >= cutoffDate;
    });
  };

  const visibleData = filterDataByRange();

  if (visibleData.length === 0) {
    return <p>No historical data available for this time range.</p>;
=======
function StockChart({ data, range }) {
  // NOTE:
  // This is a temporary placeholder for US-05.
  // It will be replaced with a Recharts visualization later.

  if (!data || data.length === 0) {
    return (
      <div className="stock-chart">
        <p>No historical data available.</p>
      </div>
    );
>>>>>>> origin/main
  }

  return (
    <div className="stock-chart">
<<<<<<< HEAD
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={visibleData}>
          <CartesianGrid strokeDasharray="3 3" />

          <XAxis
            dataKey="date"
            minTickGap={30}
          />

          <YAxis
            domain={["auto", "auto"]}
            tickFormatter={(value) => `$${Number(value).toFixed(0)}`}
          />

          <Tooltip
            formatter={(value) => [
              `$${Number(value).toFixed(2)}`,
              "Closing Price",
            ]}
          />

          <Line
            type="monotone"
            dataKey="close"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
=======
      <p>Selected range: {range}</p>

      {data.map((point) => (
        <div key={point.date}>
          {point.date}: ${Number(point.close).toFixed(2)}
        </div>
      ))}
>>>>>>> origin/main
    </div>
  );
}

export default StockChart;
