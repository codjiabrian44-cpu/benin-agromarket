import { defineConfig } from 'astro/config';

/**
 * Single configuration variables for GitHub Pages deployment (`site` and `base`).
 * Override at build time with PUBLIC_SITE_URL and PUBLIC_BASE_PATH.
 */
export const SITE_URL = process.env.PUBLIC_SITE_URL || 'https://codjiabrian44-cpu.github.io';
export const SITE_BASE_PATH = process.env.PUBLIC_BASE_PATH || '/benin-agromarket';

export default defineConfig({
  output: 'static',
  base: SITE_BASE_PATH,
  site: SITE_URL,
  trailingSlash: 'ignore',
  devToolbar: {
    enabled: false,
  },
  i18n: {
    defaultLocale: 'fr',
    locales: ['fr', 'en'],
    routing: {
      prefixDefaultLocale: false,
    },
  },
  build: {
    assets: '_astro',
    inlineStylesheets: 'never',
  },
  vite: {
    build: {
      assetsInlineLimit: 0,
    },
  },
});
