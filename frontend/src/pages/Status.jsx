import { useEffect, useState } from "react";

import { apiFetch } from "../api.js";

export default function Status() {
  const [state, setState] = useState("checking"); // "checking", "ok" or "unreachable"

  useEffect(() => {
    const controller = new AbortController();
    apiFetch("/api/health", { signal: controller.signal })
      .then((data) => setState(data?.status === "ok" ? "ok" : "unreachable"))
      .catch((error) => {
        if (error.name !== "AbortError") setState("unreachable");
      });
    return () => controller.abort(); // leaving the page cancels the request
  }, []);

  return (
    <section>
      <h1>System status</h1>
      {state === "checking" && <p>Checking the server...</p>}
      {state === "ok" && <p role="status">The server is running.</p>}
      {state === "unreachable" && (
        <p role="alert">The server cannot be reached. Please try again later.</p>
      )}
    </section>
  );
}