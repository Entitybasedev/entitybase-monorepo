import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const API_TARGET = process.env.API_TARGET || 'http://localhost:8083'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 8085,
    strictPort: true,
    proxy: {
      '/v1': { target: API_TARGET, changeOrigin: true },
      '/health': { target: API_TARGET, changeOrigin: true },
    },
  },
})
