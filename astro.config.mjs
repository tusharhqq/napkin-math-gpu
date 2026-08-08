import { defineConfig } from "astro/config";

export default defineConfig({
  output: "static",
  vite: {
    server: {
      host: "0.0.0.0",
      allowedHosts: ["terminal.local"],
    },
  },
});
