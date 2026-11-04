import { useAuth } from "./auth.jsx";

export default function SessionGate({ children }) {
  const { status, retry } = useAuth();

  if (status === "loading") return <p>Checking your session...</p>;
  if (status === "unreachable") {
    return (
      <section>
        <p className="error" role="alert">
          The server cannot be reached. Please check your connection.
        </p>
        <button type="button" onClick={retry}>
          Try again
        </button>
      </section>
    );
  }
  return children;
}