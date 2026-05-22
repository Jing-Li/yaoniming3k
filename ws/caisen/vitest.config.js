/**
 * Vitest Configuration for Caisen Frontend Tests
 */
import { defineConfig } from 'vitest/config';

export default defineConfig({
    test: {
        globals: true,
        environment: 'node',
        include: ['tests/js/**/*.test.js'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            include: ['src/caisen/visualization/js/**/*.js'],
            exclude: []
        }
    }
});