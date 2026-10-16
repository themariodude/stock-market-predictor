import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const TOKEN_STORAGE_KEY = "stock-market-auth-token";
const USER_STORAGE_KEY = "stock-market-auth-user";

function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const registrationSuccess = location.state?.registrationSuccess === true;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error("The email or password you entered is incorrect.");
        }
        throw new Error(
          "Unable to reach the login service. Make sure the backend is running on port 8000, then try again.",
        );
      }

      const data = await response.json();
      localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));
      navigate(location.state?.from === "/watchlist" ? "/watchlist" : "/account", {
        replace: true,
      });
    } catch (loginError) {
      setError(loginError instanceof TypeError
        ? "Unable to reach the login service. Make sure the backend is running on port 8000, then try again."
        : loginError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="login-title">
        <Link to="/" className="back-button">
          Back to Home
        </Link>

        <p className="section-label">Investor Access</p>
        <h1 id="login-title">Log In</h1>
        <p className="auth-copy">
          Securely access your saved watchlist and account information.
        </p>
        {registrationSuccess && (
          <p role="status" className="auth-copy">
            Account created successfully! Please log in.
          </p>
        )}

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              autoComplete="email"
              inputMode="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>

          <label>
            Password
            <input
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error && <p className="form-error" role="alert">{error}</p>}

          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Logging in..." : "Log In"}
          </button>
        </form>
        <p className="auth-copy">
          Don't have an account? <Link to="/register">Create one</Link>
        </p>
      </section>
    </main>
  );
}

export default Login;
