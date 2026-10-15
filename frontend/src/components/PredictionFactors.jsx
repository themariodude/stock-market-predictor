function formatFactorValue(factor) {
  if (typeof factor.value !== "number") {
    return "Not available";
  }

  const amount = `$${Math.abs(factor.value).toFixed(2)}`;

  if (factor.unit === "USD/day") {
    const sign = factor.value > 0 ? "+" : factor.value < 0 ? "-" : "";
    return `${sign}${amount}/day`;
  }

  return amount;
}

function PredictionFactors({ explanation }) {
  const dataWindow = explanation.window;
  const factors = Array.isArray(explanation.factors) ? explanation.factors : [];
  const notUsed = Array.isArray(explanation.not_used) ? explanation.not_used : [];
  const limitations = Array.isArray(explanation.limitations)
    ? explanation.limitations
    : [];

  return (
    <section
      className="prediction-factors"
      aria-labelledby="prediction-factors-title"
    >
      <h2 id="prediction-factors-title">Prediction Factors</h2>
      <p>{explanation.summary}</p>

      {dataWindow && (
        <p>
          Based on {dataWindow.closing_prices} closing prices from{" "}
          {dataWindow.start_date} (${dataWindow.start_close.toFixed(2)}) to{" "}
          {dataWindow.end_date} (${dataWindow.end_close.toFixed(2)}).
        </p>
      )}

      {factors.length > 0 && (
        <ul className="factor-list">
          {factors.map((factor) => (
            <li className="factor-card" key={factor.name}>
              <span>{factor.label}</span>
              <strong>{formatFactorValue(factor)}</strong>
              <small>{factor.role}</small>
            </li>
          ))}
        </ul>
      )}

      {explanation.confidence_basis && (
        <p>
          <strong>About confidence:</strong> {explanation.confidence_basis}
        </p>
      )}

      {notUsed.length > 0 && (
        <p>Not used in this forecast: {notUsed.join("; ")}.</p>
      )}

      {limitations.length > 0 && (
        <details>
          <summary>Limitations</summary>
          <ul>
            {limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

export default PredictionFactors;
