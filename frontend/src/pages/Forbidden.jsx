import { Link } from "react-router";

export default function Forbidden() {
  return (
    <section>
      <h1>You don't have permission</h1>
      <p>
        Your role does not allow you to use this page. If you think this is a mistake, ask the
        Administrator.
      </p>
      <Link to="/">Go to the home page</Link>
    </section>
  );
}