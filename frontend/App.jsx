import { Link, Route, Routes } from "react-router";

import Home from "./pages/Home.jsx";
import NotFound from "./pages/NotFound.jsx";
import Status from "./pages/Status.jsx";

export default function App() {
  return (
    <>
      <header className="site-header">
        <p className="site-title">Pill Brook Facility Maintenance</p>
        <nav aria-label="Main">
          <Link to="/">Home</Link>
          <Link to="/status">System status</Link>
        </nav>
      </header>
      <main className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/status" element={<Status />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </>
  );
}