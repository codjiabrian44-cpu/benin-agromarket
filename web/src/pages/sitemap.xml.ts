import type { APIRoute } from 'astro';
import { getLocalizedRoutes } from '../i18n';

export const GET: APIRoute = ({ site }) => {
  const baseUrl = import.meta.env.BASE_URL || '/';
  const origin = site ?? new URL('https://benin-agromarket.example.org');
  const fr = getLocalizedRoutes('fr', baseUrl);
  const en = getLocalizedRoutes('en', baseUrl);

  const pairs: Array<{ fr: string; en: string }> = [
    { fr: fr.home, en: en.home },
    { fr: fr.explorer, en: en.explorer },
    { fr: fr.forecast, en: en.forecast },
    { fr: fr.method, en: en.method },
  ];

  const urlsXml = pairs
    .flatMap((pair) => {
      const frHref = new URL(pair.fr, origin).toString();
      const enHref = new URL(pair.en, origin).toString();
      const altLinks = `    <xhtml:link rel="alternate" hreflang="fr" href="${frHref}" />\n    <xhtml:link rel="alternate" hreflang="en" href="${enHref}" />\n    <xhtml:link rel="alternate" hreflang="x-default" href="${frHref}" />`;
      return [
        `  <url>\n    <loc>${frHref}</loc>\n${altLinks}\n  </url>`,
        `  <url>\n    <loc>${enHref}</loc>\n${altLinks}\n  </url>`,
      ];
    })
    .join('\n');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n${urlsXml}\n</urlset>\n`;

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
    },
  });
};
