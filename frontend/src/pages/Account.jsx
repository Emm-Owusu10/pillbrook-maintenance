import { useAuth } from "../auth.jsx";
import { roleLabel } from "../roles.js";

export default function Account() {
  const { user } = useAuth();

  return (
    <section>
      <h1>My account</h1>
      <dl className="details">
        <dt>Name</dt>
        <dd>{user.name}</dd>
        <dt>Email address</dt>
        <dd>{user.email}</dd>
        <dt>Role</dt>
        <dd>{roleLabel(user.role)}</dd>
      </dl>
    </section>
  );
}