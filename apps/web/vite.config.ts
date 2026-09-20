import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    // Use an IPv4 loopback target for Linux development. The frontend still
    // requires the API process to be running; this avoids localhost/IPv6
    // resolution differences when the API is bound to 127.0.0.1.
    proxy: { "/api": "http://127.0.0.1:8000", "/health": "http://127.0.0.1:8000" },
  },
});
