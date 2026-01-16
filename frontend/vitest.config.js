// =============================================================================
// SERV.O v8.1 - VITEST CONFIGURATION
// =============================================================================

import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    // Environment
    environment: 'jsdom',

    // Globals
    globals: true,

    // Setup files
    setupFiles: './src/test/setup.js',

    // Include patterns
    include: ['src/**/*.{test,spec}.{js,jsx}'],

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.js',
        '**/index.js',
      ],
    },

    // Timeouts
    testTimeout: 10000,

    // Reporter
    reporter: ['verbose'],
  },
});
