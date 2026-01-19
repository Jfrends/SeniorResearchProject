import React, { useContext } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { AuthContext } from "../contexts/AuthContext";

export default function PrivateRoute() {
  const { token } = useContext(AuthContext);
  const location = useLocation();

  // returns user to login if no token in localStorage
  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  // otherwise go
  return <Outlet />;
}
