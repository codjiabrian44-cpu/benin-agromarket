import type { APIRoute } from 'astro';

export const GET: APIRoute = ({ site }) => {
  const baseUrl = import.meta.env.BASE_URL || '/';
  const cleanBase = baseUrl === '/' ? '' : baseUrl.replace(/\/$/, '');
  const origin = site ?? new URL('https://benin-agromarket.example.org');
  const sitemapUrl = new URL(`${cleanBase}/sitemap.xml`, origin).toString();

  const body = `User-agent: *\nAllow: /\n\nSitemap: ${sitemapUrl}\n`;
  return new Response(body, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
};
