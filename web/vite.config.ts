import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 4173,
    proxy: {
      "/admin": "http://127.0.0.1:8000",
      "/agent": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000"
    }
  }
});
