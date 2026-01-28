import React, { useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";
import { Box, Typography, Button, Paper, Stack } from "@mui/material";
import Header from "../components/Header"
import Footer from "../components/Footer"

export default function Dashboard() {
  const { userId, logout } = useContext(AuthContext);

  return (
    <Box sx={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column" }}>
      <Header />
      <Box
        sx={{
          width: "100vw",
          height: "100vh",
          bgcolor: "grey.100",
          display: "flex",
          justifyContent: "center",
          alignItems: "center"
        }}
      >
        <Paper elevation={3} sx={{ p: 4, textAlign: "center", width: 400 }}>
          <Typography variant="h5" gutterBottom sx={{ fontWeight: 600 }}>
            Welcome!
          </Typography>

          <Typography variant="body1" gutterBottom>
            You are logged in as:
          </Typography>

          <Typography variant="body2" sx={{ mb: 3, fontFamily: "monospace" }}>
            {userId}
          </Typography>

          <Stack spacing={2}>
            <Button variant="contained" color="primary" fullWidth>
              Go to My Files
            </Button>

            <Button
              variant="outlined"
              color="error"
              fullWidth
              onClick={logout}
            >
              Logout
            </Button>
          </Stack>
        </Paper>
      </Box>
      <Footer />
    </Box>
  );
}
