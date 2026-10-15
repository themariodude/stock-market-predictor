import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const TOKEN_STORAGE_KEY = "stock-market-auth-token";
const USER_STORAGE_KEY = "stock-market-auth-user";

function getStoredUser() {
  const storedUser = localStorage.getItem(USER_STORAGE_KEY);
  if (!storedUser) {
    return null;
  }

  try {
    return JSON.parse(storedUser);
  } catch {
    localStorage.removeItem(USER_STORAGE_KEY);
    return null;
  }
}

function Account() {
  const navigate = useNavigate();
  const [account, setAccount] = useState(getStoredUser);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) {
      navigate("/login");
      return;
    }

    const controller = new AbortController();

    async function loadAccount() {
      setError("");

      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          localStorage.removeItem(TOKEN_STORAGE_KEY);
          localStorage.removeItem(USER_STORAGE_KEY);
          throw new Error("Your session has expired. Please log in again.");
        }

        const data = await response.json();
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data));
        setAccount(data);
      } catch (accountError) {
        if (accountError.name !== "AbortError") {
          setError(accountError.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    loadAccount();

    return () => controller.abort();
  }, [navigate]);

  function handleLogout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
    navigate("/login");
  }

  return (
    <main className="account-page">
      <div className="page-header">
        <div>
          <Link to="/dashboard" className="back-button">
            Back to Dashboard
          </Link>
          <h1>Saved Information</h1>
          <Link to="/watchlist" className="back-button">My Watchlist</Link>
        </div>

        <button className="secondary-button" onClick={handleLogout} type="button">
          Log Out
        </button>
      </div>

      {isLoading && <p>Loading saved information...</p>}
      {!isLoading && error && <p className="form-error">{error}</p>}
      {!isLoading && account && !error && (
        <section className="account-summary" aria-label="Saved account information">
          <div>
            <span>Name</span>
            <strong>{account.name}</strong>
          </div>
          <div>
            <span>Email</span>
            <strong>{account.email}</strong>
          </div>
          <div>
            <span>Investment Focus</span>
            <strong>{account.investment_focus}</strong>
          </div>

          <div className="saved-stocks">
            <span>Saved Stocks</span>
            <ul>
              {account.saved_stocks.map((ticker) => (
                <li key={ticker}>
                  <Link to={`/stocks/${ticker}`}>{ticker}</Link>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </main>
  );
}

export default Account;
