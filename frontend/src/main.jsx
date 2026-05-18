import React from "react";
import { createRoot } from "react-dom/client";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import App from "./App";
import "./styles.css";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#0f766e" },
    secondary: { main: "#d97706" },
    background: {
      default: "#f4f5ef",
      paper: "#fffef8",
    },
  },
  typography: {
    fontFamily: "'Space Grotesk', sans-serif",
    h4: { fontWeight: 700 },
    button: { textTransform: "none", fontWeight: 600 },
  },
});

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
