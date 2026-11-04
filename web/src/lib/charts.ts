/**
 * Pure D3 SVG geometry builders using strictly `d3-scale`, `d3-shape`, `d3-array`, and `d3-interpolate`.
 * Zero external chart libraries.
 */

import { extent, max, min } from 'd3-array';
import { interpolateRgb } from 'd3-interpolate';
import { scaleLinear, scaleTime } from 'd3-scale';
import { area, curveMonotoneX, line } from 'd3-shape';
import type { ProductSlug } from '../i18n';
import type { ForecastPoint, HistoryPoint, Tier1MarketMapItem } from './data';

/**
 * 5-step single-hue sequential ramps per product (`light = cheaper`, `dark = more expensive`),
 * generated with `d3-interpolate` between the product's light tint, mid identity token, and deep shade.
 */
export const PRODUCT_RAMP_5: Record<ProductSlug, [string, string, string, string, string]> = {
  maize_white: [
    '#FBF3D5',
    interpolateRgb('#FBF3D5', '#E3A81F')(0.55),
    '#E3A81F',
    interpolateRgb('#E3A81F', '#7A5200')(0.5),
    '#7A5200',
  ],
  tomatoes: [
    '#F9E5DC',
    interpolateRgb('#F9E5DC', '#B5471F')(0.5),
    '#B5471F',
    interpolateRgb('#B5471F', '#6E240B')(0.5),
    '#6E240B',
  ],
  yam_white: [
    '#E3EFE6',
    interpolateRgb('#E3EFE6', '#2F5D3A')(0.48),
    '#2F5D3A',
    interpolateRgb('#2F5D3A', '#16331E')(0.5),
    '#16331E',
  ],
};

export interface HeroChartGeometry {
  width: number;
  height: number;
  margin: { top: number; right: number; bottom: number; left: number };
  forecastZoneWidth: number;
  historyPath: string;
  forecastPath: string;
  band80Path: string;
  band90Path: string;
  yTicks: Array<{ value: number; y: number }>;
  xTicks: Array<{ year: number; x: number }>;
  asOfX: number;
  forecastEndX: number;
  unobservedCount: number;
  lastObsPoint: { x: number; y: number; price: number; date: string };
  forecastPoints: Array<{
    x: number;
    y: number;
    yLow80: number;
    yHigh80: number;
    horizon: number;
    date: string;
    price: number;
    low80: number;
    high80: number;
  }>;
}

export function buildHeroChartGeometry(
  history: HistoryPoint[],
  forecasts: ForecastPoint[],
  width = 760,
  height = 280
): HeroChartGeometry {
  const margin = { top: 22, right: 44, bottom: 30, left: 48 };
  const forecastZoneWidth = 108; // Dedicated 108px visual span for the 3-month forecast fan
  const parseDate = (dStr: string) => new Date(`${dStr}T00:00:00Z`);

  const histDates = history.map((d) => parseDate(d.date));
  const [minDate, maxHistDate] = extent(histDates) as [Date, Date];

  const observedHistory = history.filter(
    (d): d is HistoryPoint & { price: number } =>
      d.is_observed !== false && typeof d.price === 'number' && Number.isFinite(d.price)
  );
  const unobservedCount = history.length - observedHistory.length;

  const allValues = [
    ...observedHistory.map((d) => d.price),
    ...forecasts.flatMap((f) => [f.low_90, f.high_90, f.point_forecast]),
  ];
  const yMaxRaw = max(allValues) ?? 500;
  const yMax = Math.ceil((yMaxRaw * 1.08) / 50) * 50;

  const asOfX = width - margin.right - forecastZoneWidth;
  const forecastEndX = width - margin.right;

  const xHistScale = scaleTime()
    .domain([minDate, maxHistDate])
    .range([margin.left, asOfX]);

  const xForecastScale = scaleLinear()
    .domain([0, 3])
    .range([asOfX, forecastEndX]);

  const yScale = scaleLinear()
    .domain([0, yMax])
    .nice(5)
    .range([height - margin.bottom, margin.top]);

  // Strictly break the SVG path whenever a calendar month is unobserved (`is_observed === false` or `price === null`)
  const histLineGen = line<HistoryPoint>()
    .defined((d) => d.is_observed !== false && typeof d.price === 'number' && Number.isFinite(d.price))
    .x((d) => xHistScale(parseDate(d.date)))
    .y((d) => yScale(d.price as number))
    .curve(curveMonotoneX);

  const lastObs = observedHistory[observedHistory.length - 1];
  const bridgePoints = [
    {
      h: 0,
      date: lastObs.date,
      point: lastObs.price,
      low80: lastObs.price,
      high80: lastObs.price,
      low90: lastObs.price,
      high90: lastObs.price,
    },
    ...forecasts.map((f) => ({
      h: f.horizon_months,
      date: f.target_date,
      point: f.point_forecast,
      low80: f.low_80,
      high80: f.high_80,
      low90: f.low_90,
      high90: f.high_90,
    })),
  ];

  const fcLineGen = line<(typeof bridgePoints)[number]>()
    .x((d) => xForecastScale(d.h))
    .y((d) => yScale(d.point))
    .curve(curveMonotoneX);

  const area80Gen = area<(typeof bridgePoints)[number]>()
    .x((d) => xForecastScale(d.h))
    .y0((d) => yScale(d.low80))
    .y1((d) => yScale(d.high80))
    .curve(curveMonotoneX);

  const area90Gen = area<(typeof bridgePoints)[number]>()
    .x((d) => xForecastScale(d.h))
    .y0((d) => yScale(d.low90))
    .y1((d) => yScale(d.high90))
    .curve(curveMonotoneX);

  const yTickValues = yScale.ticks(5);
  const yTicks = yTickValues.map((v) => ({
    value: v,
    y: Math.round(yScale(v) * 10) / 10,
  }));

  const years = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
  const xTicks = years.map((yr) => ({
    year: yr,
    x: Math.round(xHistScale(new Date(`${yr}-01-15T00:00:00Z`)) * 10) / 10,
  }));

  return {
    width,
    height,
    margin,
    forecastZoneWidth,
    historyPath: histLineGen(history) ?? '',
    forecastPath: fcLineGen(bridgePoints) ?? '',
    band80Path: area80Gen(bridgePoints) ?? '',
    band90Path: area90Gen(bridgePoints) ?? '',
    yTicks,
    xTicks,
    asOfX: Math.round(asOfX * 10) / 10,
    forecastEndX: Math.round(forecastEndX * 10) / 10,
    unobservedCount,
    lastObsPoint: {
      x: Math.round(asOfX * 10) / 10,
      y: Math.round(yScale(lastObs.price) * 10) / 10,
      price: lastObs.price,
      date: lastObs.date,
    },
    forecastPoints: forecasts.map((f) => ({
      x: Math.round(xForecastScale(f.horizon_months) * 10) / 10,
      y: Math.round(yScale(f.point_forecast) * 10) / 10,
      yLow80: Math.round(yScale(f.low_80) * 10) / 10,
      yHigh80: Math.round(yScale(f.high_80) * 10) / 10,
      horizon: f.horizon_months,
      date: f.target_date,
      price: f.point_forecast,
      low80: f.low_80,
      high80: f.high_80,
    })),
  };
}

export function buildSparklineGeometry(
  points: Array<{ date: string; median_price: number }>,
  width = 300,
  height = 68
): {
  linePath: string;
  areaPath: string;
  lastX: number;
  lastY: number;
  minVal: number;
  maxVal: number;
} {
  const padX = 6;
  const padY = 8;
  const vals = points.map((p) => p.median_price);
  const vMin = min(vals) ?? 0;
  const vMax = max(vals) ?? 100;

  const xScale = scaleLinear()
    .domain([0, Math.max(1, points.length - 1)])
    .range([padX, width - padX]);

  const yScale = scaleLinear()
    .domain([vMin * 0.94, vMax * 1.04])
    .range([height - padY, padY]);

  const lineGen = line<{ date: string; median_price: number }>()
    .x((_, idx) => xScale(idx))
    .y((d) => yScale(d.median_price))
    .curve(curveMonotoneX);

  const areaGen = area<{ date: string; median_price: number }>()
    .x((_, idx) => xScale(idx))
    .y0(height - padY)
    .y1((d) => yScale(d.median_price))
    .curve(curveMonotoneX);

  const lastIdx = points.length - 1;
  return {
    linePath: lineGen(points) ?? '',
    areaPath: areaGen(points) ?? '',
    lastX: Math.round(xScale(lastIdx) * 10) / 10,
    lastY: Math.round(yScale(points[lastIdx]?.median_price ?? vMin) * 10) / 10,
    minVal: vMin,
    maxVal: vMax,
  };
}

export interface DotMapNode extends Tier1MarketMapItem {
  cx: number;
  cy: number;
  stepIndex: 1 | 2 | 3 | 4 | 5;
  fillHex: string;
  isCheapest: boolean;
  isPriciest: boolean;
}

export interface MapCallout {
  node: DotMapNode;
  labelX: number;
  labelY: number;
  anchor: 'start' | 'end';
  leaderPath: string;
}

export function classifyMedianBracketStep(diffPct: number): 1 | 2 | 3 | 4 | 5 {
  if (diffPct <= -15) return 1;
  if (diffPct <= -5) return 2;
  if (diffPct < 5) return 3;
  if (diffPct < 15) return 4;
  return 5;
}

export function buildBeninDotMapGeometry(
  markets: Tier1MarketMapItem[],
  slug: ProductSlug,
  latBandLabels: { '6_5': string; '7_5': string; '9_5': string; '11_5': string },
  width = 430,
  height = 520
): {
  width: number;
  height: number;
  mapLeft: number;
  mapRight: number;
  rampColors: [string, string, string, string, string];
  nodes: DotMapNode[];
  cheapestCallout: MapCallout;
  priciestCallout: MapCallout;
  latBands: Array<{ lat: number; y: number; label: string }>;
} {
  // Benin geographic bounding box: Lat 6.15°N to 12.45°N, Lon 0.75°E to 3.88°E
  // Reserve a clean left gutter (x = 10..122) for latitude zone labels, top gutter (y = 8..34)
  // and bottom callout gutter (y = 460..514) so callout labels never touch any market dot.
  const mapLeft = 128;
  const mapRight = width - 18;
  const topPlotY = 42;
  const bottomPlotY = height - 64; // 456px: all market dots fall strictly in y = [45..448]
  const xScale = scaleLinear().domain([0.72, 3.92]).range([mapLeft, mapRight]);
  const yScale = scaleLinear().domain([6.15, 12.45]).range([bottomPlotY, topPlotY]);
  const rampColors = PRODUCT_RAMP_5[slug];

  // Identify cheapest and most expensive market
  const sortedByPrice = [...markets].sort((a, b) => a.last_observed_price - b.last_observed_price);
  const cheapestName = sortedByPrice[0]?.market_name ?? '';
  const priciestName = sortedByPrice[sortedByPrice.length - 1]?.market_name ?? '';

  const nodes: DotMapNode[] = markets.map((m) => {
    const stepIndex = classifyMedianBracketStep(m.diff_vs_median_pct);
    return {
      ...m,
      cx: Math.round(xScale(m.longitude) * 10) / 10,
      cy: Math.round(yScale(m.latitude) * 10) / 10,
      stepIndex,
      fillHex: rampColors[stepIndex - 1],
      isCheapest: m.market_name === cheapestName,
      isPriciest: m.market_name === priciestName,
    };
  });

  const cheapestNode = nodes.find((n) => n.isCheapest) ?? nodes[0];
  const priciestNode = nodes.find((n) => n.isPriciest) ?? nodes[nodes.length - 1];

  const makeSlotCallout = (
    node: DotMapNode,
    labelX: number,
    labelY: number,
    anchor: 'start' | 'end'
  ): MapCallout => {
    const lineEndX = anchor === 'end' ? labelX - 6 : labelX + 6;
    const lineY = Math.round((labelY - 3.5) * 10) / 10;
    const elbowX = Math.round(node.cx * 10) / 10;
    return {
      node,
      labelX,
      labelY,
      anchor,
      leaderPath: `M ${node.cx} ${node.cy} L ${elbowX} ${lineY} L ${lineEndX} ${lineY}`,
    };
  };

  let cheapestCallout: MapCallout;
  let priciestCallout: MapCallout;

  const cheapInNorth = cheapestNode.cy < 260;
  const priceInNorth = priciestNode.cy < 260;

  if (cheapInNorth && !priceInNorth) {
    cheapestCallout = makeSlotCallout(cheapestNode, mapRight, 22, 'end');
    priciestCallout = makeSlotCallout(priciestNode, mapRight, height - 16, 'end');
  } else if (!cheapInNorth && priceInNorth) {
    priciestCallout = makeSlotCallout(priciestNode, mapRight, 22, 'end');
    cheapestCallout = makeSlotCallout(cheapestNode, mapRight, height - 16, 'end');
  } else if (cheapInNorth && priceInNorth) {
    if (cheapestNode.cy <= priciestNode.cy) {
      cheapestCallout = makeSlotCallout(cheapestNode, mapRight, 18, 'end');
      priciestCallout = makeSlotCallout(priciestNode, mapRight, 34, 'end');
    } else {
      priciestCallout = makeSlotCallout(priciestNode, mapRight, 18, 'end');
      cheapestCallout = makeSlotCallout(cheapestNode, mapRight, 34, 'end');
    }
  } else {
    // Both in southern/central half: route both into the dedicated 64px bottom callout gutter (y = 480 and y = 504)
    if (cheapestNode.cx <= priciestNode.cx) {
      cheapestCallout = makeSlotCallout(cheapestNode, 14, height - 36, 'start');
      priciestCallout = makeSlotCallout(priciestNode, mapRight, height - 12, 'end');
    } else {
      priciestCallout = makeSlotCallout(priciestNode, 14, height - 36, 'start');
      cheapestCallout = makeSlotCallout(cheapestNode, mapRight, height - 12, 'end');
    }
  }

  const latBands = [
    { lat: 6.5, y: Math.round(yScale(6.5) * 10) / 10, label: latBandLabels['6_5'] },
    { lat: 7.5, y: Math.round(yScale(7.5) * 10) / 10, label: latBandLabels['7_5'] },
    { lat: 9.5, y: Math.round(yScale(9.5) * 10) / 10, label: latBandLabels['9_5'] },
    { lat: 11.5, y: Math.round(yScale(11.5) * 10) / 10, label: latBandLabels['11_5'] },
  ];

  return {
    width,
    height,
    mapLeft,
    mapRight,
    rampColors,
    nodes,
    cheapestCallout,
    priciestCallout,
    latBands,
  };
}
