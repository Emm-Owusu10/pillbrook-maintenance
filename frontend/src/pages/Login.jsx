import { useRef, useState } from "react";
import { Navigate, useLocation } from "react-router";

import { ApiError } from "../api.js";
import { useAuth } from "../auth.jsx";
import SessionGate from "../SessionGate.jsx";

// Only a path inside this site is accepted, so a sign-in link can never send anyone elsewhere.
const SAFE_PATH = /^\/(?![/\\])/;

function safeDestination(from) {
  return typeof from === "string" && SAFE_PATH.test(from) ? from : "/";
}

function messageFor(error) {
  if (error instanceof ApiError) {
    if (error.status === 422) return "Enter your email address and your password.";
    if (error.status === 401 || error.status === 429) {
      return error.problems[0]?.message ?? "Sign-in failed. Please try again.";
    }
    return "Something went wrong. Please try again.";
  }
  return "The server cannot be reached. Please try again later.";
}

export default function Login() {
  return (
    <SessionGate>
      <LoginForm />
    </SessionGate>
  );
}

function LoginForm() {
  const { status, notice, signIn } = useAuth();
  const location = useLocation();
  const passwordRef = useRef(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Already signed in, or just signed in: go to the page that was asked for, or the home page.
  if (status === "signedIn") {
    return <Navigate to={safeDestination(location.state?.from)} replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) return;
    if (!email.trim() || !password) {
      setError("Enter your email address and your password.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await signIn(email.trim(), password); // the password itself is never trimmed or altered
    } catch (caught) {
      setError(messageFor(caught));
      setPassword(""); // a wrong password is not left sitting in the box
      setShowPassword(false);
      setSubmitting(false);
      passwordRef.current?.focus();
    }
  }

  return (
    <section>
      <h1>Sign in</h1>
      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <form onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="email">Email address</label>
          <input
            id="email"
            name="email"
            type="email"
            inputMode="email"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            ref={passwordRef}
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        <div className="field checkbox">
          <input
            id="show-password"
            type="checkbox"
            checked={showPassword}
            onChange={(event) => setShowPassword(event.target.checked)}
          />
          <label htmlFor="show-password">Show password</label>
        </div>
        <button type="submit" disabled={submitting}>
          {submitting ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </section>
  );
}