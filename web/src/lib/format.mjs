/**
 * Single shared, locale-aware number and percentage formatter used by both
 * build-time data scripts (`web/scripts/prepare-data.mjs`) and Astro/browser runtime (`web/src/i18n/index.ts`).
 *
 * Uses deterministic decimal half-away-from-zero rounding (`roundHalfAway`) prior to
 * `Intl.NumberFormat` so IEEE-754 float edge cases (such as `19.45` -> `19.449999...`)
 * never round inconsistently between `.toFixed()` and `Intl.NumberFormat`.
 */

/**
 * Round a finite number to `digits` decimal places using half-away-from-zero.
 * @param {number} value
 * @param {number} [digits=1]
 * @returns {number}
 */
export function roundHalfAway(value, digits = 1) {
  if (!Number.isFinite(value)) return 0;
  const sign = value < 0 ? -1 : 1;
  const absVal = Math.abs(value);
  const shifted = Number(`${absVal}e${digits}`);
  const rounded = Number(`${Math.round(shifted)}e-${digits}`);
  return rounded === 0 ? 0 : sign * rounded;
}

/**
 * Format an integer according to locale (`fr-FR` or `en-GB`).
 * @param {number} value
 * @param {'fr' | 'en'} locale
 * @returns {string}
 */
export function formatInt(value, locale) {
  const rounded = roundHalfAway(value, 0);
  return new Intl.NumberFormat(locale === 'fr' ? 'fr-FR' : 'en-GB', {
    maximumFractionDigits: 0,
  }).format(rounded);
}

/**
 * Format a fixed-decimal number according to locale (`fr-FR` or `en-GB`).
 * @param {number} value
 * @param {'fr' | 'en'} locale
 * @param {number} [digits=1]
 * @returns {string}
 */
export function formatDecimal(value, locale, digits = 1) {
  const rounded = roundHalfAway(value, digits);
  return new Intl.NumberFormat(locale === 'fr' ? 'fr-FR' : 'en-GB', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(rounded);
}

/**
 * Format an unsigned percentage according to locale (`19,5 %` in FR, `19.5%` in EN).
 * @param {number} value
 * @param {'fr' | 'en'} locale
 * @param {number} [digits=1]
 * @returns {string}
 */
export function formatPct(value, locale, digits = 1) {
  const formatted = formatDecimal(value, locale, digits);
  return locale === 'fr' ? `${formatted} %` : `${formatted}%`;
}

/**
 * Format a signed percentage according to locale (`+24,1 %` / `−4,3 %` / `±0,0 %` in FR, `+24.1%` in EN).
 * @param {number} value
 * @param {'fr' | 'en'} locale
 * @param {number} [digits=1]
 * @returns {string}
 */
export function formatSignedPct(value, locale, digits = 1) {
  const rounded = roundHalfAway(value, digits);
  const formatted = formatDecimal(Math.abs(rounded), locale, digits);
  const sign = rounded > 0 ? '+' : rounded < 0 ? '−' : '±';
  return locale === 'fr' ? `${sign}${formatted} %` : `${sign}${formatted}%`;
}
