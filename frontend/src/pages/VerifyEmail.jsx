import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";

import { ApiError, apiFetch } from "../api.js";
import ResendVerification from "../ResendVerification.jsx";

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{20,200}$/;

function readToken(hash) {
  const value = new URLSearchParams(hash.replace(/^#/, "")).get("token");
  return value && TOKEN_PATTERN.test(value) ? value : "";
}

export default function VerifyEmail() {
  const location = useLocation();
  const navigate = useNavigate();
  // Read the code once, then take it out of the address bar and the history.
  const token = useRef(readToken(location.hash)).current;
  const [state, setState] = useState(token ? "checking" : "missing"); // checking, confirmed, invalid, failed, missing
  const [problem, setProblem] = useState("");
  const started = useRef(false);

  async function confirm() {
    setState("checking");
    try {
      await apiFetch("/api/auth/verify-email", { method: "POST", body: { token } });
      setState("confirmed");
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        setProblem(error.problems[0]?.message ?? "This link is not valid or has expired.");
        setState("invalid");
      } else {
        setProblem(
          error instanceof ApiError
            ? "Something went wrong. Please try again."
            : "The server cannot be reached. Please try again later.",
        );
        setState("failed");
      }
    }
  }

  useEffect(() => {
    // "started" makes sure the one-time code is sent once, even when React runs this effect twice.
    if (!token || started.current) return;
    started.current = true;
    navigate(location.pathname, { replace: true }); // drops the code from the address bar
    confirm();
  }, []);

  if (state === "checking") return <p>Confirming your email address...</p>;

  if (state === "confirmed") {
    return (
      <section>
        <h1>Your email address is confirmed</h1>
        <p>
          You can now <Link to="/login">sign in</Link>.
        </p>
      </section>
    );
  }

  if (state === "failed") {
    return (
      <section>
        <h1>Confirm your email address</h1>
        <p className="error" role="alert">
          {problem}
        </p>
        <button type="button" onClick={confirm}>
          Try again
        </button>
      </section>
    );
  }

  return (
    <section>
      <h1>{state === "invalid" ? "This link is not valid" : "Confirm your email address"}</h1>
      {state === "invalid" ? (
        <p className="error" role="alert">
          {problem}
        </p>
      ) : (
        <p>Open the link in the email we sent you. If you cannot find it, ask for a new one below.</p>
      )}
      <ResendVerification />
    </section>
  );
}