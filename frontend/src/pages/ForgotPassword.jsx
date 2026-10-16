
import { useState } from "react";
import { Link } from "react-router-dom";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/password-reset/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        throw new Error(
          response.status === 422
            ? "Please enter a valid email address."
            : "Unable to process your request. Please try again.",
        );
      }

      setMessage(
        "If an account exists for this email, password reset instructions will be sent.",
      );
    } catch (requestError) {
      setError(
        requestError instanceof TypeError
          ? "Unable to reach the server. Please try again."
          : requestError.message,
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="forgot-title">
        <Link to="/login" className="back-button">
          Back to Login
        </Link>

        <p className="section-label">Investor Access</p>
        <h1 id="forgot-title">Forgot Password?</h1>
        <p className="auth-copy">
          Enter your registered email address to request a password reset link.
        </p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              autoComplete="email"
              inputMode="email"
              maxLength={255}
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>

          {error && <p className="form-error" role="alert">{error}</p>}
          {message && <p className="auth-copy" role="status">{message}</p>}

          <button
            className="primary-button"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Sending..." : "Send Reset Link"}
          </button>
        </form>

        <p className="auth-copy">
          Remember your password? <Link to="/login">Log In</Link>
        </p>
      </section>
    </main>
  );
}

export default ForgotPassword;
