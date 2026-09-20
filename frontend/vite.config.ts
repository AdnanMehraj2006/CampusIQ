import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },

  server: {
    port: 5173,
    allowedHosts: ['fulfilling-peace-production-fa01.up.railway.app'],
  },

  preview: {
    port: 5173,
    allowedHosts: ['fulfilling-peace-production-fa01.up.railway.app'],
  },
})