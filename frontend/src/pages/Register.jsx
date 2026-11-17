import { useRef, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router";

import { ApiError, apiFetch } from "../api.js";
import { useAuth } from "../auth.jsx";
import ResendVerification from "../ResendVerification.jsx";
import SessionGate from "../SessionGate.jsx";

// Turns what the server said into text for the right place on the form.
function explain(error) {
  if (!(error instanceof ApiError)) {
    return { general: "The server cannot be reached. Please try again later." };
  }
  const first = error.problems[0]?.message;
  if (error.status === 422) {
    const fields = {};
    for (const problem of error.problems) (fields[problem.field] ??= []).push(problem.message);
    return Object.keys(fields).length ? { fields } : { general: "Check the details you entered." };
  }
  if (error.status === 409) {
    return { fields: { email: [first ?? "An account with this email address already exists."] }, duplicate: true };
  }
  if (error.status === 403 || error.status === 429) {
    return { general: first ?? "Registration is not available right now." };
  }
  return { general: "Something went wrong. Please try again." };
}

function CheckEmail({ email, emailSent }) {
  return (
    <section>
      <h1>Check your email</h1>
      {emailSent ? (
        <p>
          We sent a confirmation email to <strong>{email}</strong>. Open the link in it within 24 hours,
          then sign in.
        </p>
      ) : (
        <p className="error" role="alert">
          Your account was created, but the confirmation email could not be sent. Ask for another one below.
        </p>
      )}
      <ResendVerification initialEmail={email} />
      <p>
        <Link to="/login">Go to sign in</Link>
      </p>
    </section>
  );
}

export default function Register() {
  return (
    <SessionGate>
      <RegisterForm />
    </SessionGate>
  );
}

function RegisterForm() {
  const { status } = useAuth();
  const navigate = useNavigate();
  const passwordRef = useRef(null);
  const codeRef = useRef(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [code, setCode] = useState("");
  const [showPasswords, setShowPasswords] = useState(false);
  const [problem, setProblem] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(null);

  if (status === "signedIn") return <Navigate to="/" replace />;
  if (done) return <CheckEmail email={done.email} emailSent={done.emailSent} />;

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) return;
    setProblem({});
    if (!name.trim() || !email.trim() || !password || !code.trim()) {
      setProblem({ general: "Enter your name, email address, password and the farm access code." });
      return;
    }
    if (password !== repeat) {
      setProblem({ fields: { repeat: ["The two passwords do not match."] } });
      return;
    }
    setSubmitting(true);
    try {
      // The password is sent exactly as typed: it is never trimmed or changed.
      const result = await apiFetch("/api/auth/register", {
        method: "POST",
        body: { name: name.trim(), email: email.trim(), password, access_code: code.trim() },
      });
      if (result.verification_required) {
        setDone({ email: email.trim(), emailSent: result.verification_email_sent });
      } else {
        navigate("/login", { replace: true, state: { notice: "Account created. You can now sign in." } });
      }
    } catch (caught) {
      const explained = explain(caught);
      setProblem(explained);
      if (explained.fields?.password) {
        // Only when the password itself was refused are both boxes emptied.
        setPassword("");
        setRepeat("");
        setShowPasswords(false);
        passwordRef.current?.focus();
      } else if (caught instanceof ApiError && caught.status === 403) {
        codeRef.current?.focus();
      }
      setSubmitting(false);
    }
  }

  const errorsFor = (key) =>
    (problem.fields?.[key] ?? []).map((message) => (
      <p key={message} className="error" role="alert">
        {message}
      </p>
    ));

  return (
    <section>
      <h1>Create an account</h1>
      <p>For people who work on the farm. You need the farm access code.</p>
      {problem.general && (
        <p className="error" role="alert">
          {problem.general}
        </p>
      )}
      <form onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="name">Full name</label>
          <input
            id="name"
            name="name"
            type="text"
            autoComplete="name"
            maxLength={100}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          {errorsFor("name")}
        </div>
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
          {errorsFor("email")}
          {problem.duplicate && (
            <p>
              <Link to="/login">Sign in instead</Link>
            </p>
          )}
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <ul id="password-rules" className="rules">
            <li>At least 15 characters. A sentence of unrelated words works well.</li>
            <li>Do not use your name, your email name or "pillbrook".</li>
            <li>Do not use a common password.</li>
          </ul>
          <input
            id="password"
            name="password"
            ref={passwordRef}
            type={showPasswords ? "text" : "password"}
            autoComplete="new-password"
            aria-describedby="password-rules"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {errorsFor("password")}
        </div>
        <div className="field">
          <label htmlFor="repeat">Repeat the password</label>
          <input
            id="repeat"
            name="repeat"
            type={showPasswords ? "text" : "password"}
            autoComplete="new-password"
            value={repeat}
            onChange={(event) => setRepeat(event.target.value)}
          />
          {errorsFor("repeat")}
        </div>
        <div className="field checkbox">
          <input
            id="show-passwords"
            type="checkbox"
            checked={showPasswords}
            onChange={(event) => setShowPasswords(event.target.checked)}
          />
          <label htmlFor="show-passwords">Show passwords</label>
        </div>
        <div className="field">
          <label htmlFor="access-code">Farm access code</label>
          <p id="access-code-hint" className="hint">
            Ask the Facility Manager. You can type it with or without the dashes.
          </p>
          <input
            id="access-code"
            name="access_code"
            ref={codeRef}
            className="code-input"
            type="text"
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            aria-describedby="access-code-hint"
            value={code}
            onChange={(event) => setCode(event.target.value.toUpperCase())}
          />
        </div>
        <button type="submit" disabled={submitting}>
          {submitting ? "Creating account..." : "Create account"}
        </button>
      </form>
      <p>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </section>
  );
}