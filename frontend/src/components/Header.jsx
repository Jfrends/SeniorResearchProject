import * as React from "react";
import { useContext } from "react";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../contexts/AuthContext";

export default function Header() {
  const navigate = useNavigate();
  const { userId, logout } = useContext(AuthContext);

  const handleMyFiles = () => {
    navigate("/files");
  };

  return (
    <AppBar position="static">
      <Toolbar sx={{ display: "flex", justifyContent: "space-between" }}>
        <Typography variant="h6" component="div" sx={{ cursor: "pointer" }} onClick={() => navigate("/")}>
          FileSearcher
        </Typography>

        <Box>
          <Button color="inherit" onClick={handleMyFiles}>
            My Files
          </Button>
          <Button color="inherit" onClick={logout}>
            Logout
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
