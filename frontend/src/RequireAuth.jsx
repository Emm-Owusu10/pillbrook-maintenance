import { Navigate, Outlet, useLocation } from "react-router";

import { useAuth } from "./auth.jsx";
import SessionGate from "./SessionGate.jsx";

export default function RequireAuth() {
  const { status, signedOutOnPurpose } = useAuth();
  const location = useLocation();

  let content;
  if (status === "signedIn") {
    content = <Outlet />;
  } else if (signedOutOnPurpose) {
    content = <Navigate to="/" replace />; // the person chose to leave, so do not ask them to sign in again
  } else {
    content = <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return <SessionGate>{content}</SessionGate>;
}