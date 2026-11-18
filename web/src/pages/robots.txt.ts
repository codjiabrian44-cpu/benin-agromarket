import type { APIRoute } from 'astro';
import { withBase } from '../lib/paths';

export const GET: APIRoute = ({ site }) => {
  const baseUrl = import.meta.env.BASE_URL || '/';
  const origin = site ?? new URL('https://codjiabrian44-cpu.github.io');
  const sitemapUrl = new URL(withBase('/sitemap.xml', baseUrl), origin).toString();

  const body = `User-agent: *\nAllow: /\n\nSitemap: ${sitemapUrl}\n`;
  return new Response(body, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
};
