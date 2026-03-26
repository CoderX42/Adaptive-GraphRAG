import { defineConfig, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'

/** 开发时 base 为 /app/，仅打开 localhost:5173/ 会 404；重定向到 /app/ */
function redirectRootToApp(): Plugin {
  return {
    name: 'redirect-root-to-app',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const path = req.url?.split('?')[0] ?? ''
        if (path === '/' || path === '') {
          res.statusCode = 302
          res.setHeader('Location', '/app/')
          res.end()
          return
        }
        next()
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), redirectRootToApp()],
  base: '/app/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    // 必须带 /app/ 前缀；自动打开避免误以为「启动失败」
    open: '/app/',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
