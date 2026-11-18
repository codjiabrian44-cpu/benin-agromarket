import fr from './fr.json';
import en from './en.json';
import {
  formatDecimal,
  formatInt,
  formatPct,
  formatSignedPct,
  roundHalfAway,
} from '../lib/format.mjs';
import { withBase } from '../lib/paths';

export { formatDecimal, formatInt, formatPct, formatSignedPct, roundHalfAway };

export type Locale = 'fr' | 'en';
export type Dictionary = typeof fr;
export type ProductSlug = 'maize_white' | 'tomatoes' | 'yam_white';

const DICTIONARIES: Record<Locale, Dictionary> = {
  fr,
  en,
};

export function getDictionary(locale: Locale): Dictionary {
  return DICTIONARIES[locale] ?? fr;
}

/**
 * Resolve localized route paths while respecting Astro's single `BASE_URL` configuration variable.
 */
export function getLocalizedRoutes(locale: Locale, baseUrl: string = import.meta.env.BASE_URL) {
  if (locale === 'en') {
    return {
      home: withBase('/en/', baseUrl),
      explorer: withBase('/en/explorer', baseUrl),
      forecast: withBase('/en/forecast', baseUrl),
      method: withBase('/en/method', baseUrl),
      notFound: withBase('/en/404/', baseUrl),
      switchLang: withBase('/', baseUrl),
    };
  }
  return {
    home: withBase('/', baseUrl),
    explorer: withBase('/explorer', baseUrl),
    forecast: withBase('/previsions', baseUrl),
    method: withBase('/methode', baseUrl),
    notFound: withBase('/404.html', baseUrl),
    switchLang: withBase('/en/', baseUrl),
  };
}

export function formatYearMonth(dateStr: string, dict: Dictionary): string {
  // e.g. "2026-09-15" -> "sept. 2026" or "Sep 2026"
  const [yr, mo] = dateStr.split('-');
  const mKey = String(parseInt(mo, 10)) as keyof typeof dict.monthsShort;
  return `${dict.monthsShort[mKey] ?? mo} ${yr}`;
}

export function formatYearMonthLong(dateStr: string, dict: Dictionary): string {
  // e.g. "2026-09-15" -> "septembre 2026" or "September 2026"
  const [yr, mo] = dateStr.split('-');
  const mKey = String(parseInt(mo, 10)) as keyof typeof dict.months;
  return `${dict.months[mKey] ?? mo} ${yr}`;
}

export function formatModelName(modelId: string, dict: Dictionary): string {
  const key = modelId as keyof typeof dict.models;
  return dict.models[key] ?? modelId;
}

export function formatZoneName(zoneRaw: string, dict: Dictionary): string {
  const key = zoneRaw as keyof typeof dict.zones;
  return dict.zones[key] ?? zoneRaw;
}

export function formatHorizonAtMonths(h: number, dict: Dictionary): string {
  if (h === 1) return dict.home.hero.horizonAtMonth1;
  return dict.home.hero.horizonAtMonths.replace('{h}', String(h));
}

export function formatComputedStoryProse(
  count: number,
  troughMonth: string,
  peakMonth: string,
  ratioFormatted: string,
  dict: Dictionary
): string {
  return dict.home.stories.computedProseTemplate
    .replace('{count}', String(count))
    .replace('{troughMonth}', troughMonth)
    .replace('{peakMonth}', peakMonth)
    .replace('{ratio}', ratioFormatted);
}
