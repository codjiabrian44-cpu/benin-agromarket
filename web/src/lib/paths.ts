/**
 * Single base-path helper for all internal links, assets, fonts, sitemaps,
 * language switches, and client-side data fetches.
 * Works identically under `/` and under `/benin-agromarket/`.
 */

export function normalizeBasePath(baseUrl: string = import.meta.env.BASE_URL): string {
  const trimmed = (baseUrl || '/').trim();
  if (!trimmed || trimmed === '/') return '';
  const withLeading = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
  return withLeading.replace(/\/+$/, '');
}

export function withBase(path: string, baseUrl: string = import.meta.env.BASE_URL): string {
  const cleanBase = normalizeBasePath(baseUrl);
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  if (cleanPath === '/' && cleanBase) {
    return `${cleanBase}/`;
  }
  return `${cleanBase}${cleanPath}` || '/';
}
