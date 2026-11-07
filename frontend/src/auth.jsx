import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { ApiError, apiFetch, setCsrfToken, setSessionEndedHandler } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [status, setStatus] = useState("loading"); // "loading", "signedIn", "signedOut" or "unreachable"
  const [user, setUser] = useState(null);
  // What this person's role may do. The server decides; the screens only follow.
  const [permissions, setPermissions] = useState([]);
  const [notice, setNotice] = useState("");
  // True after the person pressed Sign out, so protected pages send them home, not to the sign-in page.
  const [signedOutOnPurpose, setSignedOutOnPurpose] = useState(false);

  const applySignedIn = useCallback((data) => {
    setCsrfToken(data.csrf_token);
    setUser(data.user);
    setPermissions(Array.isArray(data.permissions) ? data.permissions : []);
    setStatus("signedIn");
    setNotice("");
    setSignedOutOnPurpose(false);
  }, []);

  const applySignedOut = useCallback(() => {
    setCsrfToken(null);
    setUser(null);
    setPermissions([]);
    setStatus("signedOut");
  }, []);

  // Ask the server who is signed in. This is how a reload keeps you signed in.
  const check = useCallback(
    async (signal) => {
      setStatus("loading");
      try {
        applySignedIn(await apiFetch("/api/auth/me", { signal }));
      } catch (error) {
        if (error.name === "AbortError") return;
        if (error instanceof ApiError && error.status === 401) applySignedOut();
        else setStatus("unreachable");
      }
    },
    [applySignedIn, applySignedOut],
  );

  useEffect(() => {
    const controller = new AbortController();
    check(controller.signal);
    return () => controller.abort();
  }, [check]);

  // If any later request is refused because the session ended, go back to signed out.
  useEffect(() => {
    setSessionEndedHandler(() => {
      applySignedOut();
      setSignedOutOnPurpose(false);
      setNotice("Your session has ended. Please sign in again.");
    });
    return () => setSessionEndedHandler(null);
  }, [applySignedOut]);

  const signIn = useCallback(
    async (email, password) => {
      applySignedIn(await apiFetch("/api/auth/login", { method: "POST", body: { email, password } }));
    },
    [applySignedIn],
  );

  const signOut = useCallback(async () => {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
    } catch (error) {
      // A 401 means the server no longer holds this session, so forgetting it here is correct.
      // Any other problem (no connection, a refused handshake word) is passed on to the caller.
      if (!(error instanceof ApiError && error.status === 401)) throw error;
    }
    applySignedOut();
    setSignedOutOnPurpose(true);
  }, [applySignedOut]);

  const can = useCallback((permission) => permissions.includes(permission), [permissions]);
  const clearNotice = useCallback(() => setNotice(""), []);
  const retry = useCallback(() => check(), [check]);

  const value = useMemo(
    () => ({ status, user, permissions, can, notice, signedOutOnPurpose, clearNotice, signIn, signOut, retry }),
    [status, user, permissions, can, notice, signedOutOnPurpose, clearNotice, signIn, signOut, retry],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === null) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}