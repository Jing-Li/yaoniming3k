import { defineConfig, loadEnv } from 'vite';
import { resolve } from 'path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiProxy = env.VITE_API_PROXY || 'http://localhost:8001';

  return {
    root: '.',
    base: './',
    build: {
      outDir: 'dist',
      emptyOutDir: true,
      rollupOptions: {
        input: {
          main: resolve(__dirname, 'index.html'),
          report: resolve(__dirname, 'report.html'),
          strategy: resolve(__dirname, 'strategy.html'),
        },
      },
    },
    server: {
      port: 8000,
      proxy: {
        '/api': {
          target: apiProxy,
          changeOrigin: true,
        },
        '/ws': {
          target: apiProxy,
          ws: true,
          changeOrigin: true,
        },
      },
    },
    resolve: {
      alias: {
        '/js': resolve(__dirname, 'src/js'),
        '/src': resolve(__dirname, 'src'),
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      include: ['tests/js/**/*.test.js'],
    },
  };
});
