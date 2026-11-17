import { useState } from "react";
import { Link, Route, Routes, useNavigate } from "react-router";

import { useAuth } from "./auth.jsx";
import BrandMark from "./BrandMark.jsx";
import { NAV_ITEMS, visibleNavItems } from "./navigation.js";
import Account from "./pages/Account.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import NotFound from "./pages/NotFound.jsx";
import Register from "./pages/Register.jsx";
import Status from "./pages/Status.jsx";
import VerifyEmail from "./pages/VerifyEmail.jsx";
import PageLayout from "./PageLayout.jsx";
import RequireAuth from "./RequireAuth.jsx";
import { roleLabel } from "./roles.js";

function Header() {
  const auth = useAuth();
  const { status, user, signOut } = auth;
  const navigate = useNavigate();
  const [signOutError, setSignOutError] = useState("");

  async function handleSignOut() {
    setSignOutError("");
    try {
      await signOut();
    } catch {
      setSignOutError("Could not sign out. Check your connection and try again.");
      return;
    }
    navigate("/", { replace: true });
  }

  return (
    <header className="site-header">
      <p className="site-title">
        <BrandMark />
        Pill Brook Facility Maintenance
      </p>
      <nav aria-label="Main">
        <Link to="/">Home</Link>
        <Link to="/status">System status</Link>
        {visibleNavItems(NAV_ITEMS, auth).map((item) => (
          <Link key={item.to} to={item.to}>
            {item.label}
          </Link>
        ))}
        {status === "signedOut" && <Link to="/login">Sign in</Link>}
      </nav>
      {status === "signedIn" && (
        <div className="user-bar">
          <span>
            {user.name} ({roleLabel(user.role)})
          </span>
          <button type="button" onClick={handleSignOut}>
            Sign out
          </button>
        </div>
      )}
      {signOutError && (
        <p className="error" role="alert">
          {signOutError}
        </p>
      )}
    </header>
  );
}

export default function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route element={<PageLayout />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/status" element={<Status />} />
          <Route element={<RequireAuth />}>
            <Route path="/account" element={<Account />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </>
  );
}