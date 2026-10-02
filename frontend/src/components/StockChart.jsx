import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function StockChart({ data, range, prediction }) {
  if (!data || data.length === 0) {
    return (
      <div className="stock-chart">
        <p>No historical data available.</p>
      </div>
    );
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

    if (!days) {
      return data;
    }

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
    return (
      <div className="stock-chart">
        <p>No historical data available for this time range.</p>
      </div>
    );
  }

  const latestClose = visibleData[visibleData.length - 1];
  const showForecast =
    prediction?.as_of_date === latestClose.date &&
    Number.isFinite(latestClose.close) &&
    Number.isFinite(prediction?.current_price) &&
    Number.isFinite(prediction?.predicted_price) &&
    Math.abs(prediction.current_price - latestClose.close) < 0.01;
  const chartData = showForecast
    ? [
        ...visibleData.slice(0, -1),
        { ...latestClose, forecast: latestClose.close },
        { date: "Forecast", forecast: prediction.predicted_price },
      ]
    : visibleData;

  return (
    <div className="stock-chart">
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />

          <XAxis dataKey="date" minTickGap={30} />

          <YAxis
            domain={["auto", "auto"]}
            tickFormatter={(value) => `$${Number(value).toFixed(0)}`}
          />

          <Tooltip
            formatter={(value, name) => [`$${Number(value).toFixed(2)}`, name]}
          />

          <Legend />

          <Line
            type="monotone"
            dataKey="close"
            name="Observed close"
            stroke="#63d391"
            strokeWidth={2}
            dot={visibleData.length === 1}
          />
          {showForecast && (
            <Line
              type="linear"
              dataKey="forecast"
              name="Short-term forecast"
              stroke="#f2cb63"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ r: 4 }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      {visibleData.length === 1 && (
        <p className="chart-note">
          Only one historical closing price is available; a trend cannot be shown.
        </p>
      )}
      {showForecast && (
        <p className="chart-note">
          The dashed forecast follows the observed close on {prediction.as_of_date}.
          The forecast has no specified calendar date.
        </p>
      )}
      {prediction && !showForecast && (
        <p className="chart-note">
          Forecast as of {prediction.as_of_date ?? "an unknown date"} is shown
          above. Its base closing price does not match the latest historical
          close shown here, so it is not plotted as a dated price.
        </p>
      )}
    </div>
  );
}

export default StockChart;
