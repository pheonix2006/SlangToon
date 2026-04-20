import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8889',
        changeOrigin: true,
        timeout: 6 * 60 * 1000, // 6 min — 匹配前端 SCRIPT_REQUEST 超时
      },
      '/data': {
        target: 'http://localhost:8889',
        changeOrigin: true,
      },
    },
  },
})
