function TimeRangeSelector({ selectedRange, onRangeChange }) {
  // Time-range options shown as buttons
  const ranges = ["1M", "6M", "1Y", "5Y"];

  return (
    <div className="time-range-selector">
      {ranges.map((range) => (
        <button
          key={range}
          onClick={() => onRangeChange(range)}
          // Disable the button for whichever range is currently active
          disabled={selectedRange === range}
        >
          {range}
        </button>
      ))}
    </div>
  );
}

export default TimeRangeSelector;