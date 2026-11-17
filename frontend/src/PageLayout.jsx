import { Outlet } from "react-router";

// The normal frame for every page except the landing page, which fills the width of the screen.
export default function PageLayout() {
  return (
    <main className="page">
      <Outlet />
    </main>
  );
}