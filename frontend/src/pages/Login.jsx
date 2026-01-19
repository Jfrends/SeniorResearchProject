import React, { useState, useContext } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  Avatar,
  Paper,
  Stack,
  IconButton,
  InputAdornment,
  Link,
  CircularProgress
} from "@mui/material";
import { Visibility, VisibilityOff } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../contexts/AuthContext";

function Login() {
  const navigate = useNavigate();
  const { login } = useContext(AuthContext);

  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    email: "",
    password: ""
  });
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const toggleShowPassword = () => setShowPassword(prev => !prev);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setErrorMessage("");
    setSuccessMessage("");

    const formattedData = { ...formData };

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(formattedData)
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to login");
      }

      const data = await response.json();
      login(data.token);
      setSuccessMessage("User logged in successfully!");

      // Clear form
      setFormData({ email: "", password: "" });

      // decode JWT payload for user id
      const { sub: userId } = JSON.parse(atob(data.token.split(".")[1]));
      navigate("/dashboard");
    } catch (error) {
      setErrorMessage(error.message || "An error occurred during log in.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      sx={{
        width: "100vw",
        height: "100vh",
        backgroundColor: "grey.200"
      }}
    >
      <Paper elevation={3} sx={{ p: 4, width: 380, textAlign: "center" }}>
        <Stack spacing={2} alignItems="center">
          <Avatar sx={{ bgcolor: "success.main" }} />
          <Typography variant="h5" color="success.main">
            Welcome
          </Typography>
        </Stack>

        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
          <Stack spacing={2}>
            <TextField
              label="Email Address"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              fullWidth
            />

            <TextField
              label="Password"
              name="password"
              type={showPassword ? "text" : "password"}
              value={formData.password}
              onChange={handleChange}
              fullWidth
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={toggleShowPassword} edge="end">
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                )
              }}
            />

            {errorMessage && (
              <Typography color="error" variant="body2" textAlign="center">
                {errorMessage}
              </Typography>
            )}

            {successMessage && (
              <Typography color="success.main" variant="body2" textAlign="center">
                {successMessage}
              </Typography>
            )}

            <Button
              type="submit"
              variant="contained"
              sx={{ bgcolor: "success.main" }}
              disabled={loading}
              fullWidth
            >
              {loading ? <CircularProgress size={24} color="inherit" /> : "Login"}
            </Button>
          </Stack>
        </Box>

        <Box mt={2}>
          <Typography variant="body2">
            New to us?{" "}
            <Link href="/signup" underline="hover" color="success.main">
              Sign Up
            </Link>
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
}

export default Login;
