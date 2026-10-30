import { Link } from "react-router";

export default function NotFound() {
  return (
    <section>
      <h1>Page not found</h1>
      <p>This page does not exist.</p>
      <Link to="/">Go to the home page</Link>
    </section>
  );
}