import { useAuth } from "./auth.jsx";
import Forbidden from "./pages/Forbidden.jsx";

// Use inside RequireAuth. Hiding a link is only a convenience; the server enforces every rule.
export default function RequirePermission({ permission, children }) {
  const { can } = useAuth();
  return can(permission) ? children : <Forbidden />;
}