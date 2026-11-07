import { calculatePercentChange } from "./stockCalculations.js";

const DAY_MS = 24 * 60 * 60 * 1000;

function calendarMonthsBefore(date, months) {
  const [year, month, day] = date.split("-").map(Number);
  const firstOfMonth = new Date(Date.UTC(year, month - 1 - months, 1));
  const lastDay = new Date(Date.UTC(
    firstOfMonth.getUTCFullYear(),
    firstOfMonth.getUTCMonth() + 1,
    0
  )).getUTCDate();
  firstOfMonth.setUTCDate(Math.min(day, lastDay));
  return firstOfMonth.toISOString().slice(0, 10);
}

function returnForMonths(recordsByDate, commonDates, latestDate, months) {
  const cutoff = calendarMonthsBefore(latestDate, months);
  const baselineDate = commonDates.filter((date) => date <= cutoff).at(-1);

  // A missing month of data should not be presented as a one-month return.
  if (!baselineDate ||
      (Date.parse(cutoff) - Date.parse(baselineDate)) / DAY_MS > 7) {
    return null;
  }

  return calculatePercentChange(
    recordsByDate.get(baselineDate)?.close,
    recordsByDate.get(latestDate)?.close
  );
}

export function getComparisonMetrics(records, commonDates) {
  if (commonDates.length < 2) return null;

  const recordsByDate = new Map(records.map((record) => [record.date, record]));
  const latestDate = commonDates.at(-1);
  const previousDate = commonDates.at(-2);
  const latest = recordsByDate.get(latestDate);
  const change = calculatePercentChange(
    recordsByDate.get(previousDate)?.close,
    latest?.close
  );

  if (change === null) return null;

  const yearCutoff = new Date(Date.parse(latestDate) - 364 * DAY_MS)
    .toISOString().slice(0, 10);
  const yearRecords = records.filter(
    (record) => record.date >= yearCutoff && record.date <= latestDate
  );
  const validHighs = yearRecords
    .map((record) => record.high)
    .filter((value) => Number.isFinite(value) && value > 0);
  const validLows = yearRecords
    .map((record) => record.low)
    .filter((value) => Number.isFinite(value) && value > 0);

  return {
    price: latest.close,
    change,
    oneMonthReturn: returnForMonths(recordsByDate, commonDates, latestDate, 1),
    threeMonthReturn: returnForMonths(recordsByDate, commonDates, latestDate, 3),
    volume: Number.isSafeInteger(latest.volume) && latest.volume >= 0
      ? latest.volume
      : null,
    yearHigh: validHighs.length ? Math.max(...validHighs) : null,
    yearLow: validLows.length ? Math.min(...validLows) : null,
  };
}
