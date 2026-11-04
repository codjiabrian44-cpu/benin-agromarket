/**
 * Pure D3 SVG geometry builders using strictly `d3-scale`, `d3-shape`, `d3-array`, and `d3-interpolate`.
 * Zero external chart libraries.
 */

import { extent, max, min } from 'd3-array';
import { scaleLinear, scaleTime } from 'd3-scale';
import { area, curveMonotoneX, line } from 'd3-shape';
import type { ForecastPoint, HistoryPoint, Tier1MarketMapItem } from './data';

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
  height = 360
): HeroChartGeometry {
  const margin = { top: 26, right: 52, bottom: 38, left: 54 };
  const forecastZoneWidth = 108; // Dedicated 108px visual span for the 3-month forecast fan
  const parseDate = (dStr: string) => new Date(`${dStr}T00:00:00Z`);

  const histDates = history.map((d) => parseDate(d.date));
  const [minDate, maxHistDate] = extent(histDates) as [Date, Date];

  const allValues = [
    ...history.map((d) => d.price),
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

  const histLineGen = line<HistoryPoint>()
    .x((d) => xHistScale(parseDate(d.date)))
    .y((d) => yScale(d.price))
    .curve(curveMonotoneX);

  const lastObs = history[history.length - 1];
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
  width = 280,
  height = 68
): { linePath: string; areaPath: string; lastX: number; lastY: number; minVal: number; maxVal: number } {
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
  tierBand: 'below' | 'near' | 'above';
}

export function buildBeninDotMapGeometry(
  markets: Tier1MarketMapItem[],
  width = 420,
  height = 490
): {
  width: number;
  height: number;
  mapLeft: number;
  mapRight: number;
  nodes: DotMapNode[];
  latBands: Array<{ lat: number; y: number; label: string }>;
} {
  // Benin geographic bounding box: Lat 6.15°N to 12.45°N, Lon 0.75°E to 3.88°E
  // Reserve a clean left gutter (x = 10..118) for latitude zone labels so zero labels overlap market dots
  const mapLeft = 124;
  const mapRight = width - 24;
  const padY = 28;
  const xScale = scaleLinear().domain([0.72, 3.92]).range([mapLeft, mapRight]);
  const yScale = scaleLinear().domain([6.15, 12.45]).range([height - padY, padY]);

  const nodes: DotMapNode[] = markets.map((m) => {
    const tierBand =
      m.diff_vs_median_pct <= -10
        ? 'below'
        : m.diff_vs_median_pct >= 10
          ? 'above'
          : 'near';
    return {
      ...m,
      cx: Math.round(xScale(m.longitude) * 10) / 10,
      cy: Math.round(yScale(m.latitude) * 10) / 10,
      tierBand,
    };
  });

  const latBands = [
    { lat: 6.5, y: Math.round(yScale(6.5) * 10) / 10, label: '6.5°N · Sud' },
    { lat: 7.5, y: Math.round(yScale(7.5) * 10) / 10, label: '7.5°N · Sud/Centre' },
    { lat: 9.5, y: Math.round(yScale(9.5) * 10) / 10, label: '9.5°N · Centre/Nord' },
    { lat: 11.5, y: Math.round(yScale(11.5) * 10) / 10, label: '11.5°N · Nord' },
  ];

  return { width, height, mapLeft, mapRight, nodes, latBands };
}
