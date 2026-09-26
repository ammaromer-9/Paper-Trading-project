import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../AuthContext";

// Sends already-logged-in users away from /login and /signup.
export default function PublicOnlyRoute() {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}
