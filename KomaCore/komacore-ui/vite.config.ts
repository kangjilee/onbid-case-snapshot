import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    hmr: { clientPort: 443 },
    proxy: {
      // ✅ 프론트 오리진에서 /api/v1을 백엔드(로컬 8000)로 프록시
      '/api/v1': { 
        target: 'http://localhost:8000', 
        changeOrigin: true, 
        secure: false 
      }
    }
  },
  preview: { 
    host: '0.0.0.0', 
    port: 5173, 
    allowedHosts: true 
  },
  resolve: {
    alias: {
      '@assets': '/attached_assets'
    }
  }
});