import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Configurable ports so `make backend` + `make frontend` can move off the
// canonical 8000/3000 when those are occupied (e.g. SSH tunnels).
//   HANGMAN_BACKEND_PORT  (default 8000) — uvicorn bind port
//   HANGMAN_FRONTEND_PORT (default 3000) — vite dev port
const backendPort = Number.parseInt(process.env.HANGMAN_BACKEND_PORT ?? '8000', 10);
const frontendPort = Number.parseInt(process.env.HANGMAN_FRONTEND_PORT ?? '3000', 10);

export default defineConfig({
  plugins: [react()],
  server: {
    port: frontendPort,
    proxy: {
      '/api': {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
});
