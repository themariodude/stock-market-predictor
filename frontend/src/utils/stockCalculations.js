
export function calculatePercentChange(previousClose, latestClose) {
  if (
    !Number.isFinite(previousClose) ||
    !Number.isFinite(latestClose) ||
    previousClose <= 0 ||
    latestClose <= 0
  ) {
    return null;
  }

  return ((latestClose - previousClose) / previousClose) * 100;
}

export function summarizeSector(stocks) {
  const changes = stocks
    .map((stock) => stock.change)
    .filter(Number.isFinite);

  if (changes.length === 0) {
    return { averageChange: null, gainers: 0, decliners: 0 };
  }

  return {
    averageChange:
      changes.reduce((total, change) => total + change, 0) / changes.length,
    gainers: changes.filter((change) => change > 0).length,
    decliners: changes.filter((change) => change < 0).length,
  };
}


export function getSectorMovers(stocks, limit = 3) {
  const validStocks = stocks.filter(
    (stock) =>
      typeof stock.ticker === "string" &&
      Number.isFinite(stock.change)
  );

  const gainers = validStocks
    .filter((stock) => stock.change > 0)
    .sort((a, b) =>
      b.change - a.change ||
      a.ticker.localeCompare(b.ticker)
    )
    .slice(0, limit);

  const decliners = validStocks
    .filter((stock) => stock.change < 0)
    .sort((a, b) =>
      a.change - b.change ||
      a.ticker.localeCompare(b.ticker)
    )
    .slice(0, limit);

  return { gainers, decliners };
}
