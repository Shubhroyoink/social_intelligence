import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  cacheDir: '/tmp/vite-social-intelligence-cache',
  server: {
    port: 3000,
    host: true,
    watch: {
      usePolling: true,
    },
  },
});
