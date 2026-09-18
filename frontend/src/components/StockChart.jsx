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
  }

  return (
    <div className="stock-chart">
      <p>Selected range: {range}</p>

      {data.map((point) => (
        <div key={point.date}>
          {point.date}: ${Number(point.close).toFixed(2)}
        </div>
      ))}
    </div>
  );
}

export default StockChart;
