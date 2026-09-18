# US - 06 Market Data Retrieval Design

## Goal
Automatically retrieve stock-market data needed by the defense-sector forecasting system.

## Required Data
- Ticker Symbol
- Date/Timestamp
- Open
- High
- Low
- Close
- Adjusted close, if available
- Trading Volume

## Potential Providers
1. Alpha Vantage
**Considered because it provides a formal authenticated financial API and may be more appropriate for a production-oriented implementation. To reduce provider lock-in, market-data retrieval will be isolated behind a dedicated data-access component so the provider can be replaced later without changing the ML pipeline.**
2. Financial Modeling Prep
3. Yahoo Finance / yfinance
**yfinance is not affiliated with Yahoo Finance and is meant for educational purposes. Selected for prototype because the library provides low-complexity access to historical market data with direct compatibility with the project's expected pandas-based data pipeline.**

## Evaluation Criteria
- Historical Data Availability
- Current Market Data Availability
- Rate Limits
- Cost/Free tier
- Python Support
- Reliability
- Ease of Integration
- Ability to retrieve multiple defense-sector stocks

## Open Questions
- What programming language/ framework will the team use?
**Python/ Pandas, numpy, scikitlearn, XGBoost**
- Does Sprint 1 require live data or only historical data?
- How frequently should market data update?
- Where will retrieved data be stored?
- Which defense-sector companies are in scope?

### Provider Selection
yfinance is appropriate for the project's current research/ educational prototype, but its unofficial relationship with Yahoo Finance makes provider abstraction important if the system later moves toward production use.
