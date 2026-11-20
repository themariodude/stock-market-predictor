import { useState } from "react";

const SUPPORTED_STOCKS = [
  "LMT",
  "RTX",
  "NOC",
  "GD",
  "LHX",
  "BA",
];

export default function AlertForm({ onCreate, submitting }) {
  const [ticker, setTicker] = useState("LMT");
  const [condition, setCondition] = useState("above");
  const [threshold, setThreshold] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    const price = Number(threshold);

    if (
      threshold.trim() === "" ||
      !Number.isFinite(price) ||
      price <= 0
    ) {
      setError("Please enter a valid price above zero.");
      return;
    }

    try {
      await onCreate({
        ticker,
        condition,
        threshold: price,
      });

      setThreshold("");
    } catch (err) {
      setError(err.message || "Could not create alert.");
    }
  }

  return (
    <section className="alert-form-section">
        <h2>Create Stock Alert</h2>

        <form className="alert-form" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="alert-ticker">Stock</label>
          <select
            id="alert-ticker"
            value={ticker}
            onChange={(event) => setTicker(event.target.value)}
          >
            {SUPPORTED_STOCKS.map((stock) => (
              <option key={stock} value={stock}>
                {stock}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="alert-condition">
            Alert Condition
          </label>

          <select
            id="alert-condition"
            value={condition}
            onChange={(event) =>
              setCondition(event.target.value)
            }
          >
            <option value="above">Price Above</option>
            <option value="below">Price Below</option>
          </select>
        </div>

        <div>
          <label htmlFor="alert-threshold">
            Target Price ($)
          </label>

          <input
            id="alert-threshold"
            type="number"
            min="0.01"
            step="any"
            value={threshold}
            onChange={(event) =>
              setThreshold(event.target.value)
            }
            placeholder="Enter target price"
            required
          />
        </div>

        {error && <p role="alert">{error}</p>}

        <button
          className="alert-submit-button"
          type="submit"
          disabled={submitting}
        >
          {submitting ? "Creating..." : "Create Alert"}
        </button>
      </form>
    </section>
  );
}
