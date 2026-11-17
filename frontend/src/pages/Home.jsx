import { useAuth } from "../auth.jsx";
import { roleLabel } from "../roles.js";
import SessionGate from "../SessionGate.jsx";
import Landing from "./Landing.jsx";

export default function Home() {
  const { status } = useAuth();
  // The landing page for a signed-out visitor fills the width of the screen. Every other state
  // (checking, server unreachable, signed in) sits in the normal page container.
  const landing = status === "signedOut";
  return (
    <main className={landing ? undefined : "page"}>
      <SessionGate>
        <HomeContent />
      </SessionGate>
    </main>
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

  return <Landing />;
}