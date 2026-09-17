import { Link } from 'react-router-dom';

const FEATURES = [
  {
    title: "Historical Data",
    description: "Review historical price movements for major defense-sector companies."
  },
  {
    title: "Stock Visualizations",
    description: "Explore stock performance through clear and interactive charts."
  },
  {
    title: "Predictive Analytics",
    description: "View model-generated forecasts and analytics as the project develops."
  }
];

function Home() {
  return (
    <main className="home-page">
      {/* Title, blurb, and button into the dashboard */}
      <section className="hero">
        <h1>Defense Stock Market Predictor</h1>
        <p>
          Explore historical defense-sector stock data, visualize market trends,
          and view predictive analytics powered by financial and economic data.
        </p>

        <Link to="/dashboard">
          <button>Explore Stocks</button>
        </Link>
      </section>
      
      {/* Three feature cards summarizing what the app offers.
          — could be replaced with a map to avoid keeping both in sync. */}
      <section className="features">
        <div className="feature-card">
          <h2>Historical Data</h2>
          <p>
            Review historical price movements for major defense-sector companies.
          </p>
        </div>

        <div className="feature-card">
          <h2>Stock Visualizations</h2>
          <p>
            Explore stock performance through clear and interactive charts.
          </p>
        </div>

        <div className="feature-card">
          <h2>Predictive Analytics</h2>
          <p>
            View model-generated forecasts and analytics as the project develops.
          </p>
        </div>
      </section>
    </main>
  );
}
export default Home;

