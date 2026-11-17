import { useState } from "react";

import { apiFetch } from "./api.js";

// Asks for another confirmation email. The server always answers the same way, so this form
// never learns, and never says, whether the address is registered.
export default function ResendVerification({ initialEmail = "" }) {
  const [email, setEmail] = useState(initialEmail);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (sending) return;
    setMessage("");
    if (!email.trim()) {
      setError("Enter your email address.");
      return;
    }
    setError("");
    setSending(true);
    try {
      const data = await apiFetch("/api/auth/resend-verification", {
        method: "POST",
        body: { email: email.trim() },
      });
      setMessage(data?.message ?? "If that address still needs confirming, a new email is on its way.");
    } catch {
      setError("The request could not be sent. Please try again later.");
    } finally {
      setSending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h2>Need a new link?</h2>
      {message && (
        <p className="notice" role="status">
          {message}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="field">
        <label htmlFor="resend-email">Email address</label>
        <input
          id="resend-email"
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
      <button type="submit" disabled={sending}>
        {sending ? "Sending..." : "Send a new link"}
      </button>
    </form>
  );
}