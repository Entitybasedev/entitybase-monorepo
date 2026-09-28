import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 8888,
    host: '0.0.0.0',
    allowedHosts: ['all'],
  },
  build: {
    outDir: 'dist',
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
