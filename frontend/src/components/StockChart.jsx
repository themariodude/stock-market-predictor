function StockChart({ data, range }) {
  // NOTE: this is a placeholder chart that lists date/price pairs
  return (
    <div className="stock-chart">
      <p>Selected range: {range}</p>

      {data.map((point) => (
        <div key={point.date}>
          {point.date}: ${point.close.toFixed(2)}
        </div>
      ))}
    </div>
  );
}

export default StockChart;