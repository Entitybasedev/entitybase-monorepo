import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const API_TARGET = process.env.API_TARGET || 'http://localhost:8083'
const STREAM_TARGET = process.env.STREAM_TARGET || 'http://localhost:8888'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 8085,
    strictPort: true,
    proxy: {
      // Stream backend routes must be ordered before the generic /v1 rule
      '/v1/streams': { target: STREAM_TARGET, changeOrigin: true },
      '/v1/topics': { target: STREAM_TARGET, changeOrigin: true },
      '/k2s/health': {
        target: STREAM_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/k2s/, ''),
      },
      '/v1': { target: API_TARGET, changeOrigin: true },
      '/health': { target: API_TARGET, changeOrigin: true },
    },
  },
})
