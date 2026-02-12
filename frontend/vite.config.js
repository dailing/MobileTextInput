import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../backend/static',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/profiles': { target: 'http://127.0.0.1:8080', changeOrigin: true },
      '/buttons': { target: 'http://127.0.0.1:8080', changeOrigin: true },
      '/simulate': { target: 'http://127.0.0.1:8080', changeOrigin: true },
      '/windows': { target: 'http://127.0.0.1:8080', changeOrigin: true },
    },
  },
})
