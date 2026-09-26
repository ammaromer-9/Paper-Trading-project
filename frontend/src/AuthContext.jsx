import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [email, setEmail] = useState(() => localStorage.getItem("email"));
  const [sessionMessage, setSessionMessage] = useState(null);
  const navigate = useNavigate();

  const logout = useCallback(
    (message) => {
      localStorage.removeItem("token");
      localStorage.removeItem("email");
      setToken(null);
      setEmail(null);
      if (message) setSessionMessage(message);
      navigate("/login", { replace: true });
    },
    [navigate],
  );

  useEffect(() => {
    function handleExpired() {
      logout("Your session expired. Please log in again.");
    }
    window.addEventListener("auth:expired", handleExpired);
    return () => window.removeEventListener("auth:expired", handleExpired);
  }, [logout]);

  async function login(emailInput, password) {
    const data = await api.login(emailInput, password);
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("email", emailInput);
    setToken(data.access_token);
    setEmail(emailInput);
  }

  async function signup(emailInput, password) {
    await api.signup(emailInput, password);
    await login(emailInput, password);
  }

  const value = {
    email,
    isAuthenticated: Boolean(token),
    sessionMessage,
    clearSessionMessage: () => setSessionMessage(null),
    login,
    signup,
    logout: () => logout(),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
