import * as React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

export default function Footer() {
  return (
    <Box
      component="footer"
      sx={{
        py: 2,
        px: 2,
        textAlign: "center",
        borderTop: "1px solid rgba(0,0,0,0.12)",
        mt: "auto"
      }}
    >
      <Typography variant="body2" color="text.secondary">
        © {new Date().getFullYear()} MyApp — All rights reserved.
      </Typography>
    </Box>
  );
}
