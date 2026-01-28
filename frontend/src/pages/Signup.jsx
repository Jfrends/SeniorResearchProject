import React, { useState, useContext } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  Container,
  Avatar,
  Link,
  CircularProgress,
  IconButton,
  InputAdornment,
} from "@mui/material";
import { Visibility, VisibilityOff, ArrowBack } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../contexts/AuthContext";

function Signup() {
  const navigate = useNavigate();
  const { login } = useContext(AuthContext);

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
  });
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const handleChange = (e) => {
    setFormData({...formData, [e.target.name]: e.target.value});
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/signup`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Signup failed");
      }

      const data = await res.json();
      login(data.token);

      setSuccessMessage("User created successfully!");
      setFormData({ name: "", email: "", password: "" });

      const { sub: userId } = JSON.parse(atob(data.token.split(".")[1]));
      navigate(`/dashboard`);

    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        backgroundColor: "#eee",
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
      }}
    >
      <Container maxWidth="xs" sx={{ textAlign: "center" }}>
        <Avatar sx={{ bgcolor: "primary", margin: "0 auto" }} />
        <Typography variant="h4" sx={{ mt: 1, color: "primary" }}>
          Welcome
        </Typography>

        <Box component="form" onSubmit={handleSubmit} sx={{
          mt: 3,
          p: 3,
          borderRadius: 2,
          bgcolor: "white",
          boxShadow: 2
        }}>
          <TextField
            label="Name"
            name="name"
            fullWidth
            margin="normal"
            value={formData.name}
            onChange={handleChange}
          />

          <TextField
            label="Email Address"
            name="email"
            type="email"
            fullWidth
            margin="normal"
            value={formData.email}
            onChange={handleChange}
          />

          <TextField
            label="Password"
            name="password"
            type={showPassword ? "text" : "password"}
            fullWidth
            margin="normal"
            value={formData.password}
            onChange={handleChange}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowPassword(!showPassword)}>
                    {showPassword ? <VisibilityOff/> : <Visibility/>}
                  </IconButton>
                </InputAdornment>
              )
            }}
          />

          {errorMessage && (
            <Typography color="error" sx={{ mt: 1 }}>
              {errorMessage}
            </Typography>
          )}

          {successMessage && (
            <Typography color="primary" sx={{ mt: 1 }}>
              {successMessage}
            </Typography>
          )}

          <Button
            type="submit"
            variant="contained"
            fullWidth
            sx={{ mt: 2, bgcolor: "primary" }}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : "Sign Up"}
          </Button>
        </Box>
        <Typography variant="body2">
          <Link
            href="/login"
            underline="hover"
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              mt: 2,
              color: "primary",
              fontWeight: 500,
              fontFamily: "inherit"
            }}
          >
            <ArrowBack sx={{ mr: 0.5 }} /> Back to Login
          </Link>
        </Typography>
      </Container>
    </Box>
  );
}

export default Signup;
