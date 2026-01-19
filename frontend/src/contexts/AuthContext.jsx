import React, { createContext, useState } from "react";
import PropTypes from "prop-types";

export const AuthContext = createContext({
  token: null,
  userId: null,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }) {
  // token from localStorage
  const [token, setToken] = useState(() => localStorage.getItem("token"));

  // parse id
  const userId = token ? JSON.parse(atob(token.split(".")[1])).sub : null;

  // sets new token and keeps in localStorage
  const login = (newToken) => {
    localStorage.setItem("token", newToken);
    setToken(newToken);
  };

  // logout func
  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, userId, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

AuthProvider.propTypes = {
  children: PropTypes.node.isRequired,
};
