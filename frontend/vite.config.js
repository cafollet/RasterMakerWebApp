import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'



// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ['devserver-master--visionary-stardust-12a862.netlify.app',
    'raster-maker-web-app-5f9m.vercel.app']
  }
})
