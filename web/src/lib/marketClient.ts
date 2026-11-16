import type { Locale, ProductSlug } from '../i18n';
import type { MarketSeries, ProductPayload, SeasonalityByZoneItem } from './data';
import type { ExplorerRangePreset } from './charts';

const productCache = new Map<ProductSlug, ProductPayload>();

const PRODUCT_ALIASES: Record<string, ProductSlug> = {
  maize_white: 'maize_white',
  'mais-blanc': 'maize_white',
  mais: 'maize_white',
  'white-maize': 'maize_white',
  maize: 'maize_white',
  tomatoes: 'tomatoes',
  tomate: 'tomatoes',
  tomato: 'tomatoes',
  yam_white: 'yam_white',
  'igname-blanche': 'yam_white',
  igname: 'yam_white',
  'white-yam': 'yam_white',
  yam: 'yam_white',
};

const PRODUCT_CANONICAL_PARAM: Record<Locale, Record<ProductSlug, string>> = {
  fr: {
    maize_white: 'mais-blanc',
    tomatoes: 'tomate',
    yam_white: 'igname-blanche',
  },
  en: {
    maize_white: 'white-maize',
    tomatoes: 'tomato',
    yam_white: 'white-yam',
  },
};

export interface UrlState {
  product: ProductSlug;
  market: string | null;
  range: ExplorerRangePreset;
  median: boolean;
  horizon: 1 | 2 | 3;
}

export function parseUrlState(): UrlState {
  if (typeof window === 'undefined') {
    return { product: 'maize_white', market: null, range: 'all', median: false, horizon: 3 };
  }
  const params = new URLSearchParams(window.location.search);
  const rawProd = (params.get('produit') || params.get('product') || '').trim().toLowerCase();
  const product: ProductSlug = PRODUCT_ALIASES[rawProd] ?? 'maize_white';

  const rawMarket = (params.get('marche') || params.get('market') || '').trim();
  const market = rawMarket.length > 0 ? rawMarket : null;

  const rawRange = (params.get('plage') || params.get('range') || '').trim().toLowerCase();
  let range: ExplorerRangePreset = 'all';
  if (rawRange === '1y' || rawRange === '1an' || rawRange === '1') range = '1y';
  else if (rawRange === '3y' || rawRange === '3ans' || rawRange === '3') range = '3y';
  else if (rawRange === 'all' || rawRange === 'tout') range = 'all';

  const rawMedian = (params.get('mediane') || params.get('median') || '').trim().toLowerCase();
  const median = rawMedian === '1' || rawMedian === 'true' || rawMedian === 'oui' || rawMedian === 'yes';

  const rawHorizon = parseInt((params.get('horizon') || '3').trim(), 10);
  const horizon: 1 | 2 | 3 = rawHorizon === 1 ? 1 : rawHorizon === 2 ? 2 : 3;

  return { product, market, range, median, horizon };
}

export function canonicalizeExplorerUrl(
  _locale: Locale,
  state: { product: ProductSlug; market: string; range: ExplorerRangePreset; median: boolean }
): void {
  if (typeof window === 'undefined') return;
  const params = new URLSearchParams();
  params.set('product', state.product);
  params.set('market', state.market);
  params.set('range', state.range);
  params.set('median', state.median ? '1' : '0');
  const nextUrl = `${window.location.pathname}?${params.toString()}`;
  window.history.replaceState(null, '', nextUrl);
}

export function canonicalizeForecastUrl(
  _locale: Locale,
  state: { product: ProductSlug; market: string; horizon: 1 | 2 | 3 }
): void {
  if (typeof window === 'undefined') return;
  const params = new URLSearchParams();
  params.set('product', state.product);
  params.set('market', state.market);
  params.set('horizon', String(state.horizon));
  const nextUrl = `${window.location.pathname}?${params.toString()}`;
  window.history.replaceState(null, '', nextUrl);
}

export async function loadProductPayload(baseUrl: string, slug: ProductSlug): Promise<ProductPayload> {
  const cached = productCache.get(slug);
  if (cached) return cached;
  const cleanBase = baseUrl === '/' ? '' : baseUrl.replace(/\/$/, '');
  const res = await fetch(`${cleanBase}/data/product-${slug}.json`);
  if (!res.ok) {
    throw new Error(`Failed to load product data (${slug}): ${res.status}`);
  }
  const data = (await res.json()) as ProductPayload;
  productCache.set(slug, data);
  return data;
}

export function groupMarketsByDepartment(
  seriesList: MarketSeries[]
): Array<{ department: string; markets: MarketSeries[] }> {
  const map = new Map<string, MarketSeries[]>();
  for (const s of seriesList) {
    const dept = s.admin1 || 'Autre';
    const arr = map.get(dept);
    if (arr) arr.push(s);
    else map.set(dept, [s]);
  }
  return Array.from(map.entries())
    .sort((a, b) => a[0].localeCompare(b[0], 'fr'))
    .map(([department, markets]) => ({
      department,
      markets: [...markets].sort((a, b) => a.market.localeCompare(b.market, 'fr')),
    }));
}

export function resolveMarketSeries(
  seriesList: MarketSeries[],
  preferredName: string | null
): MarketSeries {
  if (preferredName) {
    const norm = preferredName.toLowerCase();
    const exact = seriesList.find((s) => s.market.toLowerCase() === norm || s.market_id === preferredName);
    if (exact) return exact;
    const partial = seriesList.find((s) => s.market.toLowerCase().includes(norm));
    if (partial) return partial;
  }
  const dantokpa = seriesList.find((s) => s.market === 'Dantokpa');
  return dantokpa ?? seriesList[0];
}

export function findMatchingZoneSeasonality(
  zones: SeasonalityByZoneItem[],
  agroZone: string
): SeasonalityByZoneItem {
  const prefix = agroZone.split('(')[0].trim().toLowerCase();
  const matched = zones.find((z) => z.zone.toLowerCase().startsWith(prefix));
  return matched ?? zones[0];
}
