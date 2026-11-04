import { Link } from "react-router";

import { useAuth } from "../auth.jsx";
import { roleLabel } from "../roles.js";
import SessionGate from "../SessionGate.jsx";

export default function Home() {
  return (
    <SessionGate>
      <HomeContent />
    </SessionGate>
  );
}

function HomeContent() {
  const { status, user } = useAuth();

  if (status === "signedIn") {
    return (
      <section>
        <h1>Welcome, {user.name}</h1>
        <p>You are signed in as {roleLabel(user.role)}.</p>
        <p>Reporting and tracking faults arrive in the next steps.</p>
      </section>
    );
  }

  return (
    <section>
      <h1>Report and track maintenance faults</h1>
      <p>
        Anyone on the farm will be able to report broken or faulty equipment here, with photos,
        and follow the repair until it is confirmed fixed.
      </p>
      <p>
        <Link to="/login">Sign in</Link> to get started.
      </p>
    </section>
  );
}