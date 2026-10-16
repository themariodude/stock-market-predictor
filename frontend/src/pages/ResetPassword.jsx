
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8 || password.length > 128) {
      setError("Password must be between 8 and 128 characters.");
      return;
    }

    if (!token) {
      setError("This reset link is invalid. Please request a new one.");
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/password-reset/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          new_password: password,
        }),
      });

      if (!response.ok) {
        if (response.status === 400) {
          throw new Error(
            "This reset link is invalid, expired, or already used. Please request a new one.",
          );
        }

        if (response.status === 422) {
          throw new Error("Please enter a valid new password.");
        }

        throw new Error("Unable to reset your password. Please try again.");
      }

      navigate("/login", {
        replace: true,
        state: { passwordResetSuccess: true },
      });
    } catch (resetError) {
      setError(
        resetError instanceof TypeError
          ? "Unable to reach the server. Please try again."
          : resetError.message,
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="reset-title">
        <Link to="/login" className="back-button">
          Back to Login
        </Link>

        <p className="section-label">Investor Access</p>
        <h1 id="reset-title">Reset Password</h1>
        <p className="auth-copy">
          Choose a new password for your investor account.
        </p>

        {!token ? (
          <p className="form-error" role="alert">
            Invalid reset link. <Link to="/forgot-password">Request a new link</Link>.
          </p>
        ) : (
          <form className="login-form" onSubmit={handleSubmit}>
            <label>
              New Password
              <input
                autoComplete="new-password"
                minLength={8}
                maxLength={128}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </label>

            <label>
              Confirm New Password
              <input
                autoComplete="new-password"
                minLength={8}
                maxLength={128}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                type="password"
                value={confirmPassword}
              />
            </label>

            {error && <p className="form-error" role="alert">{error}</p>}

            <button
              className="primary-button"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? "Resetting..." : "Reset Password"}
            </button>
          </form>
        )}

        <p className="auth-copy">
          Need a new link? <Link to="/forgot-password">Request Password Reset</Link>
        </p>
      </section>
    </main>
  );
}

export default ResetPassword;
