import { defineConfig } from 'astro/config';

/**
 * Single configuration variable for the static site base path (e.g., '/' locally or
 * '/benin-agromarket' on GitHub Pages). Override at build time with PUBLIC_BASE_PATH.
 */
export const SITE_BASE_PATH = process.env.PUBLIC_BASE_PATH || '/';

export default defineConfig({
  output: 'static',
  base: SITE_BASE_PATH,
  site: process.env.PUBLIC_SITE_URL || 'https://benin-agromarket.example.org',
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
