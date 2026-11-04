import fr from './fr.json';
import en from './en.json';

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
  const cleanBase = baseUrl === '/' ? '' : baseUrl.replace(/\/$/, '');
  if (locale === 'en') {
    return {
      home: `${cleanBase}/en/`,
      explorer: `${cleanBase}/en/explorer`,
      forecast: `${cleanBase}/en/forecast`,
      method: `${cleanBase}/en/method`,
      switchLang: `${cleanBase}/`,
    };
  }
  return {
    home: `${cleanBase}/`,
    explorer: `${cleanBase}/explorer`,
    forecast: `${cleanBase}/previsions`,
    method: `${cleanBase}/methode`,
    switchLang: `${cleanBase}/en/`,
  };
}

export function formatInt(value: number, locale: Locale): string {
  return new Intl.NumberFormat(locale === 'fr' ? 'fr-FR' : 'en-GB', {
    maximumFractionDigits: 0,
  }).format(Math.round(value));
}

export function formatDecimal(value: number, locale: Locale, digits = 1): string {
  return new Intl.NumberFormat(locale === 'fr' ? 'fr-FR' : 'en-GB', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function formatSignedPct(value: number, locale: Locale, digits = 1): string {
  const formatted = formatDecimal(Math.abs(value), locale, digits);
  const sign = value > 0 ? '+' : value < 0 ? '−' : '±';
  return locale === 'fr' ? `${sign}${formatted} %` : `${sign}${formatted}%`;
}

export function formatYearMonth(dateStr: string, dict: Dictionary): string {
  // e.g. "2026-09-15" -> "sept. 2026" or "Sep 2026"
  const [yr, mo] = dateStr.split('-');
  const mKey = String(parseInt(mo, 10)) as keyof typeof dict.monthsShort;
  return `${dict.monthsShort[mKey] ?? mo} ${yr}`;
}
