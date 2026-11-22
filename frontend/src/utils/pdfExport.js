
/**
 * US-37 - Download a stock analysis PDF.
 * Optional dependencies allow testing without a browser.
 */
export async function downloadStockPdf(
  ticker,
  apiBaseUrl,
  {
    fetchFn = fetch,
    urlApi = URL,
    documentRef = document,
    scheduleCleanup = setTimeout,
    now = () => new Date(),
  } = {}
) {
  const response = await fetchFn(
    `${apiBaseUrl}/reports/stocks/${encodeURIComponent(ticker)}/pdf`
  );

  if (!response.ok) {
    throw new Error("Unable to export PDF. Please try again.");
  }

  const contentType = response.headers.get("content-type") ?? "";

  if (!contentType.includes("application/pdf")) {
    throw new Error("The server did not return a valid PDF response.");
  }

  const blob = await response.blob();
  const url = urlApi.createObjectURL(blob);

  try {
    const link = documentRef.createElement("a");

    link.href = url;
    link.download = `${ticker.toUpperCase()}_Analysis_${now()
      .toISOString()
      .slice(0, 10)}.pdf`;

    documentRef.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    scheduleCleanup(() => urlApi.revokeObjectURL(url), 1000);
  }
}
