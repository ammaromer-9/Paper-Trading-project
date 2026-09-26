import { NavLink } from "react-router-dom";
import { useAuth } from "../AuthContext";

export default function NavBar() {
  const { email, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <span className="navbar-brand">Paper Trading</span>

        <nav className="navbar-links">
          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? "active" : "")}>
            Dashboard
          </NavLink>
          <NavLink to="/trade" className={({ isActive }) => (isActive ? "active" : "")}>
            Trade
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => (isActive ? "active" : "")}>
            History
          </NavLink>
        </nav>

        <div className="navbar-user">
          <span className="navbar-email">{email}</span>
          <button type="button" className="button-secondary" onClick={logout}>
            Log out
          </button>
        </div>
      </div>
    </header>
  );
}
