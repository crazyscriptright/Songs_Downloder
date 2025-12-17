import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 3000,
      open: true,
      proxy: {
        "/search": env.VITE_API_URL || "http://localhost:5000",
        "/download": env.VITE_API_URL || "http://localhost:5000",
        "/preview_url": env.VITE_API_URL || "http://localhost:5000",
        "/cancel_download": env.VITE_API_URL || "http://localhost:5000",
        "/clear_downloads": env.VITE_API_URL || "http://localhost:5000",
        "/suggestions": env.VITE_API_URL || "http://localhost:5000",
        "/get_file": env.VITE_API_URL || "http://localhost:5000",
        "/jiosaavn_suggestions": env.VITE_API_URL || "http://localhost:5000",
        "/proxy_image": env.VITE_API_URL || "http://localhost:5000",
        "/proxy": {
          target: env.VITE_API_URL || "http://localhost:5000",
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: "dist",
    },
    define: {
      "import.meta.env.VITE_API_URL": JSON.stringify(
        env.VITE_API_URL || "http://localhost:5000"
      ),
    },
  };
});
