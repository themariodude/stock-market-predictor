
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function Register() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name, email, password }),
      });

      if (!response.ok) {
        if (response.status === 409) {
          throw new Error("An account with this email already exists.");
        }

        if (response.status === 422) {
          throw new Error("Please check your registration information.");
        }

        throw new Error("Registration failed. Please try again.");
      }

      navigate("/login", { state: { registrationSuccess: true } });
    } catch (registrationError) {
      setError(registrationError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="register-title">
        <Link to="/" className="back-button">
          Back to Home
        </Link>

        <p className="section-label">Investor Access</p>
        <h1 id="register-title">Create Account</h1>
        <p className="auth-copy">
          Register to securely access your investor account.
        </p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Name
            <input
              autoComplete="name"
              onChange={(event) => setName(event.target.value)}
              required
              maxLength={255}
              type="text"
              value={name}
            />
          </label>

          <label>
            Email
            <input
              autoComplete="email"
              inputMode="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              maxLength={255}
              type="email"
              value={email}
            />
          </label>

          <label>
            Password
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

          {error && <p className="form-error" role="alert">{error}</p>}

          <button
            className="primary-button"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <p className="auth-copy">
          Already have an account? <Link to="/login">Log In</Link>
        </p>
      </section>
    </main>
  );
}

export default Register;
