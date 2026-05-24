import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiUrl = env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'
  const apiBase = apiUrl.replace('/api/v1', '')

  return {
    plugins: [
      react(),
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: [
          'favicon.ico',
          'icons/*.png',
          'screenshots/*.png'
        ],
        manifest: false, // We're using our own public/manifest.json
        workbox: {
          globPatterns: [
            'index.html',
            'favicon.ico',
            'manifest.json',
            'logo.svg',
            'icons/icon-192x192.png',
            'icons/icon-512x512.png',
            'icons/apple-touch-icon.png'
          ],
          runtimeCaching: [
            {
              // Cache images with CacheFirst strategy
              urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp)$/,
              handler: 'CacheFirst',
              options: {
                cacheName: 'image-cache',
                expiration: {
                  maxEntries: 60,
                  maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
                },
              },
            },
            {
              // Cache fonts with CacheFirst strategy
              urlPattern: /\.(?:woff|woff2|ttf|otf|eot)$/,
              handler: 'CacheFirst',
              options: {
                cacheName: 'font-cache',
                expiration: {
                  maxEntries: 20,
                  maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
                },
              },
            },
            {
              // Cache static assets with StaleWhileRevalidate
              urlPattern: /\/assets\/.*\.(?:js|css)$/,
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'static-resources',
                expiration: {
                  maxEntries: 100,
                  maxAgeSeconds: 60 * 60 * 24 * 7, // 7 days
                },
              },
            },
          ],
          navigateFallback: '/index.html',
          navigateFallbackDenylist: [/^\/api/],
        },
        devOptions: {
          enabled: false,
          type: 'module',
          navigateFallback: 'index.html',
        },
      }),
    ],
    server: {
      port: 5173,
      host: true,
      cors: true,
      proxy: {
        '/api': {
          target: apiBase,
          changeOrigin: true,
          secure: false
        }
      }
    },
    preview: {
      port: 5173,
      host: true,
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: false,
      minify: 'terser',
      chunkSizeWarningLimit: 500, // Warn if chunk > 500KB
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return;
            if (id.includes('@google/generative-ai')) return 'ai';
            if (id.includes('html2canvas')) return 'capture';
            if (id.includes('react') || id.includes('scheduler')) return 'vendor';
            if (
              id.includes('react-router') ||
              id.includes('axios') ||
              id.includes('lucide-react') ||
              id.includes('react-hot-toast')
            ) {
              return 'app-vendor';
            }
          },
        },
      },
    },
    test: { // Add this test configuration
      globals: true,
      environment: 'jsdom',
      setupFiles: './setupTests.js',
    },
  }
})
