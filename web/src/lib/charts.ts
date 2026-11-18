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
 * 5-step single-hue sequential ramps per product on dark `#1E1B16` ink background
 * (`dimmer = cheaper`, `brighter/more luminous = more expensive`).
 * Every dimmest step has >= 3.0:1 graphical contrast against `#1E1B16` (`ink`),
 * and every dot carries a crisp `#F6F0E4` (`sand`, 15.12:1 AAA) stroke.
 */
export const PRODUCT_RAMP_5: Record<ProductSlug, [string, string, string, string, string]> = {
  maize_white: [
    '#966814',
    interpolateRgb('#966814', '#E3A81F')(0.5),
    '#E3A81F',
    interpolateRgb('#E3A81F', '#FBF3D5')(0.5),
    '#FBF3D5',
  ],
  tomatoes: [
    '#B5471F',
    interpolateRgb('#B5471F', '#D46A43')(0.5),
    '#D46A43',
    interpolateRgb('#D46A43', '#F9E5DC')(0.5),
    '#F9E5DC',
  ],
  yam_white: [
    '#4E825B',
    interpolateRgb('#4E825B', '#7CB088')(0.5),
    '#7CB088',
    interpolateRgb('#7CB088', '#E3EFE6')(0.5),
    '#E3EFE6',
  ],
};

export interface HeroAnnotation {
  x: number;
  y: number;
  labelX: number;
  labelY: number;
  anchor: 'start' | 'middle' | 'end';
  leaderPath: string;
}

export interface HeroMorphData {
  x93: number[];
  y93: number[];
  def93: number[];
  fcBridge: Array<{
    x: number;
    y: number;
    l80: number;
    h80: number;
    l90: number;
    h90: number;
  }>;
}

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
  peakPoint: {
    x: number;
    y: number;
    price: number;
    date: string;
    labelX: number;
    labelY: number;
    anchor: 'start' | 'middle' | 'end';
  };
  lastObsPoint: {
    x: number;
    y: number;
    price: number;
    date: string;
    labelX: number;
    labelY: number;
  };
  bandLabelPos: {
    tickX1: number;
    tickY1: number;
    tickX2: number;
    labelX: number;
    labelY: number;
  };
  forecastEndLabelPos: {
    x: number;
    yLine1: number;
    yLine2: number;
  };
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
  morphData: HeroMorphData;
}

export function buildHeroChartGeometry(
  history: HistoryPoint[],
  forecasts: ForecastPoint[],
  width = 820,
  height = 340,
  isMobile = false
): HeroChartGeometry {
  const margin = isMobile
    ? { top: 24, right: 14, bottom: 26, left: 42 }
    : { top: 34, right: 26, bottom: 32, left: 48 };
  const forecastZoneWidth = isMobile ? 84 : 148; // Generous 148px desktop / 84px mobile zone for 3-month forecast
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
  const yMax = Math.ceil((yMaxRaw * 1.14) / 50) * 50;

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

  const yTickValues = yScale.ticks(isMobile ? 3 : 5);
  const yTicks = yTickValues.map((v) => ({
    value: v,
    y: Math.round(yScale(v) * 10) / 10,
  }));

  const years = isMobile
    ? [2019, 2022, 2025]
    : [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
  const xTicks = years.map((yr) => ({
    year: yr,
    x: Math.round(xHistScale(new Date(`${yr}-01-15T00:00:00Z`)) * 10) / 10,
  }));

  // Find historical peak point (highest observed price in 2019–2026)
  let peakObs = observedHistory[0];
  for (const pt of observedHistory) {
    if (pt.price > peakObs.price) {
      peakObs = pt;
    }
  }
  const peakX = Math.round(xHistScale(parseDate(peakObs.date)) * 10) / 10;
  const peakY = Math.round(yScale(peakObs.price) * 10) / 10;

  // Collision-safe peak label placement
  const peakNearRight = peakX > asOfX - 180;
  const peakAnchor: 'start' | 'end' = peakNearRight ? 'end' : 'start';
  const peakLabelX = peakNearRight ? Math.round((peakX - 12) * 10) / 10 : Math.round((peakX + 12) * 10) / 10;
  const peakLabelY = Math.max(margin.top + 13, Math.round((peakY - 8) * 10) / 10);
  const peakLeaderEndX = peakAnchor === 'end' ? peakLabelX + 4 : peakLabelX - 4;
  const peakLeaderPath = `M ${peakX} ${peakY} L ${peakX} ${peakLabelY - 3} L ${peakLeaderEndX} ${peakLabelY - 3}`;

  const lastObsX = Math.round(asOfX * 10) / 10;
  const lastObsY = Math.round(yScale(lastObs.price) * 10) / 10;

  const fcPts = forecasts.map((f) => ({
    x: Math.round(xForecastScale(f.horizon_months) * 10) / 10,
    y: Math.round(yScale(f.point_forecast) * 10) / 10,
    yLow80: Math.round(yScale(f.low_80) * 10) / 10,
    yHigh80: Math.round(yScale(f.high_80) * 10) / 10,
    yLow90: Math.round(yScale(f.low_90) * 10) / 10,
    yHigh90: Math.round(yScale(f.high_90) * 10) / 10,
    horizon: f.horizon_months,
    date: f.target_date,
    price: f.point_forecast,
    low80: f.low_80,
    high80: f.high_80,
  }));

  const fcH3Pt = fcPts[fcPts.length - 1];

  // Anchor "Dernier relevé" cleanly to the LEFT of `asOfX` so it never crosses the vertical dashed line
  let lastObsLabelY = Math.round((lastObsY - 14) * 10) / 10;
  if (Math.abs(peakX - lastObsX) < 165 && Math.abs(lastObsLabelY - peakLabelY) < 22) {
    lastObsLabelY = Math.min(height - margin.bottom - 18, Math.round((lastObsY + 22) * 10) / 10);
  }
  lastObsLabelY = Math.max(margin.top + 28, Math.min(height - margin.bottom - 14, lastObsLabelY));
  const lastObsLabelX = Math.round((lastObsX - 10) * 10) / 10;
  const lastObsLeaderPath = `M ${lastObsX} ${lastObsY} L ${lastObsX - 5} ${lastObsLabelY - 3} L ${lastObsLabelX + 3} ${lastObsLabelY - 3}`;

  // Place 3-month forecast direct annotation in the right-hand forecast zone above the upper 90% fan
  const fcTopBandY = Math.min(fcH3Pt.yHigh90, fcH3Pt.y);
  const fcLabelY = Math.max(margin.top + 26, Math.min(height - margin.bottom - 56, Math.round((fcTopBandY - 22) * 10) / 10));
  const fcBandLabelY = Math.round((fcLabelY + 14) * 10) / 10;
  const fcLabelX = Math.round((forecastEndX - 4) * 10) / 10;
  const fcLeaderPath = `M ${fcH3Pt.x} ${fcH3Pt.y} L ${fcH3Pt.x} ${fcBandLabelY + 4}`;

  // Place the fan band annotation cleanly below the lower 90% boundary
  const fcBottomBandY = Math.max(fcH3Pt.yLow90, fcH3Pt.y);
  const fanLabelY = Math.min(
    height - margin.bottom - 8,
    Math.max(fcBandLabelY + 28, Math.round((fcBottomBandY + 16) * 10) / 10)
  );
  const fanLabelX = Math.round((asOfX + forecastZoneWidth * 0.52) * 10) / 10;

  // Build 93-point coordinate arrays for smooth 600ms client-side path morphing
  const histX: number[] = [];
  const histYRaw: Array<number | null> = [];
  const histDefined: boolean[] = [];

  for (const d of history) {
    const xVal = Math.round(xHistScale(parseDate(d.date)) * 10) / 10;
    histX.push(xVal);
    if (d.is_observed !== false && typeof d.price === 'number' && Number.isFinite(d.price)) {
      histYRaw.push(Math.round(yScale(d.price) * 10) / 10);
      histDefined.push(true);
    } else {
      histYRaw.push(null);
      histDefined.push(false);
    }
  }

  // Fill null Y positions via linear interpolation ONLY for the intermediate morph frames
  const histY: number[] = histYRaw.map((v, i) => {
    if (v !== null) return v;
    let prevIdx = i - 1;
    while (prevIdx >= 0 && histYRaw[prevIdx] === null) prevIdx--;
    let nextIdx = i + 1;
    while (nextIdx < histYRaw.length && histYRaw[nextIdx] === null) nextIdx++;
    const prevY = prevIdx >= 0 ? (histYRaw[prevIdx] as number) : lastObsY;
    const nextY = nextIdx < histYRaw.length ? (histYRaw[nextIdx] as number) : prevY;
    if (prevIdx >= 0 && nextIdx < histYRaw.length) {
      const ratio = (i - prevIdx) / (nextIdx - prevIdx);
      return Math.round((prevY + (nextY - prevY) * ratio) * 10) / 10;
    }
    return prevY;
  });

  const historyPath = histLineGen(history) ?? '';
  const forecastPath = fcLineGen(bridgePoints) ?? '';
  const band80Path = area80Gen(bridgePoints) ?? '';
  const band90Path = area90Gen(bridgePoints) ?? '';

  const bandTickX = fcPts[1]?.x ?? fcH3Pt.x;
  const bandTickY = fcPts[1]?.yLow90 ?? fcH3Pt.yLow90;
  const forecastZoneTextX = Math.round((asOfX + 10) * 10) / 10;

  return {
    width,
    height,
    margin,
    forecastZoneWidth,
    historyPath,
    forecastPath,
    band80Path,
    band90Path,
    yTicks,
    xTicks,
    asOfX: lastObsX,
    forecastEndX: Math.round(forecastEndX * 10) / 10,
    unobservedCount,
    peakPoint: {
      x: peakX,
      y: peakY,
      price: peakObs.price,
      date: peakObs.date,
      labelX: peakLabelX,
      labelY: peakLabelY,
      anchor: peakAnchor,
    },
    lastObsPoint: {
      x: lastObsX,
      y: lastObsY,
      price: lastObs.price,
      date: lastObs.date,
      labelX: lastObsLabelX,
      labelY: lastObsLabelY,
    },
    bandLabelPos: {
      tickX1: bandTickX,
      tickY1: bandTickY,
      tickX2: bandTickX,
      labelX: forecastZoneTextX,
      labelY: fanLabelY,
    },
    forecastEndLabelPos: {
      x: forecastZoneTextX,
      yLine1: fcLabelY,
      yLine2: fcBandLabelY,
    },
    forecastPoints: fcPts.map(({ yLow90: _l90, yHigh90: _h90, ...rest }) => rest),
    morphData: {
      x93: histX,
      y93: histY,
      def93: histDefined.map((d) => (d ? 1 : 0)),
      fcBridge: bridgePoints.map((b) => ({
        x: Math.round(xForecastScale(b.h) * 10) / 10,
        y: Math.round(yScale(b.point) * 10) / 10,
        l80: Math.round(yScale(b.low80) * 10) / 10,
        h80: Math.round(yScale(b.high80) * 10) / 10,
        l90: Math.round(yScale(b.low90) * 10) / 10,
        h90: Math.round(yScale(b.high90) * 10) / 10,
      })),
    },
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
  trueCx: number;
  trueCy: number;
  offsetPx: number;
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

/**
 * Deterministic collision relaxation for the dense southern Benin cluster.
 * Keeps every market dot strictly within `maxOffsetPx` (6.0 px) of its true projected `(trueCx, trueCy)`.
 */
function relaxSouthernClusterCollisions(
  rawNodes: DotMapNode[],
  minDist = 11.6,
  maxOffsetPx = 6.0,
  iterations = 45
): DotMapNode[] {
  const nodes = rawNodes.map((n) => ({ ...n }));
  const count = nodes.length;

  for (let iter = 0; iter < iterations; iter++) {
    const damping = 0.55 * (1 - iter / (iterations * 1.25));
    for (let i = 0; i < count; i++) {
      for (let j = i + 1; j < count; j++) {
        const a = nodes[i];
        const b = nodes[j];
        let dx = b.cx - a.cx;
        let dy = b.cy - a.cy;
        const dist = Math.hypot(dx, dy);
        if (dist < minDist) {
          if (dist < 0.001) {
            const angle = ((i * 7 + j * 13) % 12) * (Math.PI / 6);
            dx = Math.cos(angle);
            dy = Math.sin(angle);
          } else {
            dx /= dist;
            dy /= dist;
          }
          const push = (minDist - Math.max(dist, 0.001)) * 0.5 * damping;
          a.cx -= dx * push;
          a.cy -= dy * push;
          b.cx += dx * push;
          b.cy += dy * push;
        }
      }
    }

    // Clamp every dot strictly within `maxOffsetPx` (6.0 px) of its true geographic position
    for (const n of nodes) {
      const ox = n.cx - n.trueCx;
      const oy = n.cy - n.trueCy;
      const offset = Math.hypot(ox, oy);
      if (offset > maxOffsetPx) {
        const scale = (maxOffsetPx - 0.001) / offset;
        n.cx = n.trueCx + ox * scale;
        n.cy = n.trueCy + oy * scale;
      }
    }
  }

  return nodes.map((n) => {
    const cx = Math.round(n.cx * 10) / 10;
    const cy = Math.round(n.cy * 10) / 10;
    const rawOffset = Math.hypot(cx - n.trueCx, cy - n.trueCy);
    if (rawOffset > maxOffsetPx) {
      const ratio = (maxOffsetPx - 0.05) / rawOffset;
      const clampedCx = Math.round((n.trueCx + (cx - n.trueCx) * ratio) * 10) / 10;
      const clampedCy = Math.round((n.trueCy + (cy - n.trueCy) * ratio) * 10) / 10;
      return {
        ...n,
        cx: clampedCx,
        cy: clampedCy,
        offsetPx: Math.round(Math.hypot(clampedCx - n.trueCx, clampedCy - n.trueCy) * 100) / 100,
      };
    }
    return {
      ...n,
      cx,
      cy,
      offsetPx: Math.round(rawOffset * 100) / 100,
    };
  });
}

export function buildBeninDotMapGeometry(
  markets: Tier1MarketMapItem[],
  slug: ProductSlug,
  latBandLabels: { '6_5': string; '7_5': string; '9_5': string; '11_5': string },
  width = 440,
  height = 530,
  isMobile = false
): {
  width: number;
  height: number;
  mapLeft: number;
  mapRight: number;
  maxOffsetPx: number;
  rampColors: [string, string, string, string, string];
  nodes: DotMapNode[];
  cheapestCallout: MapCallout;
  priciestCallout: MapCallout;
  latBands: Array<{ lat: number; y: number; label: string }>;
} {
  // Benin geographic bounding box: Lat 6.15°N to 12.45°N, Lon 0.75°E to 3.88°E
  const mapLeft = isMobile ? 64 : 128;
  const mapRight = isMobile ? width - 14 : width - 18;
  const topPlotY = isMobile ? 24 : 38;
  const bottomPlotY = isMobile ? height - 20 : height - 68;
  const xScale = scaleLinear().domain([0.72, 3.92]).range([mapLeft, mapRight]);
  const yScale = scaleLinear().domain([6.15, 12.45]).range([bottomPlotY, topPlotY]);
  const rampColors = PRODUCT_RAMP_5[slug];

  const sortedByPrice = [...markets].sort((a, b) => a.last_observed_price - b.last_observed_price);
  const cheapestName = sortedByPrice[0]?.market_name ?? '';
  const priciestName = sortedByPrice[sortedByPrice.length - 1]?.market_name ?? '';

  // Sort South-to-North (latitude ascending, tie-breaker longitude ascending) for progressive reveal
  const sortedSouthToNorth = [...markets].sort(
    (a, b) => a.latitude - b.latitude || a.longitude - b.longitude
  );

  const initialNodes: DotMapNode[] = sortedSouthToNorth.map((m) => {
    const stepIndex = classifyMedianBracketStep(m.diff_vs_median_pct);
    const trueCx = Math.round(xScale(m.longitude) * 10) / 10;
    const trueCy = Math.round(yScale(m.latitude) * 10) / 10;
    return {
      ...m,
      cx: trueCx,
      cy: trueCy,
      trueCx,
      trueCy,
      offsetPx: 0,
      stepIndex,
      fillHex: rampColors[stepIndex - 1],
      isCheapest: m.market_name === cheapestName,
      isPriciest: m.market_name === priciestName,
    };
  });

  const nodes = isMobile
    ? relaxSouthernClusterCollisions(initialNodes, 9.5, 5.0, 45)
    : relaxSouthernClusterCollisions(initialNodes, 11.6, 6.0, 45);
  const maxOffsetPx = max(nodes.map((n) => n.offsetPx)) ?? 0;

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

  // Route both extremum callouts into the bottom callout gutter (y = height - 38 and y = height - 14)
  // so the upper map area remains 100% clear for the interactive floating tooltip
  let cheapestCallout: MapCallout;
  let priciestCallout: MapCallout;
  if (cheapestNode.cx <= priciestNode.cx) {
    cheapestCallout = makeSlotCallout(cheapestNode, 12, height - 38, 'start');
    priciestCallout = makeSlotCallout(priciestNode, mapRight, height - 14, 'end');
  } else {
    priciestCallout = makeSlotCallout(priciestNode, 12, height - 38, 'start');
    cheapestCallout = makeSlotCallout(cheapestNode, mapRight, height - 14, 'end');
  }

  const shortLatLabel = (raw: string) => (isMobile ? raw.split(' · ')[0] : raw);
  const latBands = [
    { lat: 6.5, y: Math.round(yScale(6.5) * 10) / 10, label: shortLatLabel(latBandLabels['6_5']) },
    { lat: 7.5, y: Math.round(yScale(7.5) * 10) / 10, label: shortLatLabel(latBandLabels['7_5']) },
    { lat: 9.5, y: Math.round(yScale(9.5) * 10) / 10, label: shortLatLabel(latBandLabels['9_5']) },
    { lat: 11.5, y: Math.round(yScale(11.5) * 10) / 10, label: shortLatLabel(latBandLabels['11_5']) },
  ];

  return {
    width,
    mapLeft,
    mapRight,
    maxOffsetPx,
    rampColors,
    nodes,
    cheapestCallout,
    priciestCallout,
    latBands,
    height,
  };
}

/**
 * Inset (~3x scale) of the dense southern Benin cluster (< 7.5°N) so coastal
 * and Abomey-plateau markets separate cleanly without hiding behind each other.
 */
export function buildSouthZoomMapGeometry(
  markets: Tier1MarketMapItem[],
  slug: ProductSlug,
  latBandLabels: { '6_5': string; '7_0': string },
  width = 340,
  height = 260
): {
  width: number;
  height: number;
  mapLeft: number;
  mapRight: number;
  maxOffsetPx: number;
  rampColors: [string, string, string, string, string];
  nodes: DotMapNode[];
  latBands: Array<{ lat: number; y: number; label: string }>;
} {
  const mapLeft = 48;
  const mapRight = width - 14;
  const topPlotY = 18;
  const bottomPlotY = height - 18;
  const xScale = scaleLinear().domain([1.62, 2.74]).range([mapLeft, mapRight]);
  const yScale = scaleLinear().domain([6.28, 7.45]).range([bottomPlotY, topPlotY]);
  const rampColors = PRODUCT_RAMP_5[slug];

  const sortedByPrice = [...markets].sort((a, b) => a.last_observed_price - b.last_observed_price);
  const cheapestName = sortedByPrice[0]?.market_name ?? '';
  const priciestName = sortedByPrice[sortedByPrice.length - 1]?.market_name ?? '';

  const southSorted = markets
    .filter((m) => m.latitude < 7.5)
    .sort((a, b) => a.latitude - b.latitude || a.longitude - b.longitude);

  const initialNodes: DotMapNode[] = southSorted.map((m) => {
    const stepIndex = classifyMedianBracketStep(m.diff_vs_median_pct);
    const trueCx = Math.round(xScale(m.longitude) * 10) / 10;
    const trueCy = Math.round(yScale(m.latitude) * 10) / 10;
    return {
      ...m,
      cx: trueCx,
      cy: trueCy,
      trueCx,
      trueCy,
      offsetPx: 0,
      stepIndex,
      fillHex: rampColors[stepIndex - 1],
      isCheapest: m.market_name === cheapestName,
      isPriciest: m.market_name === priciestName,
    };
  });

  const nodes = relaxSouthernClusterCollisions(initialNodes, 12.5, 11.0, 50);
  const maxOffsetPx = max(nodes.map((n) => n.offsetPx)) ?? 0;

  const latBands = [
    { lat: 6.5, y: Math.round(yScale(6.5) * 10) / 10, label: latBandLabels['6_5'] },
    { lat: 7.0, y: Math.round(yScale(7.0) * 10) / 10, label: latBandLabels['7_0'] },
  ];

  return {
    width,
    height,
    mapLeft,
    mapRight,
    maxOffsetPx,
    rampColors,
    nodes,
    latBands,
  };
}

/* ==========================================================================
   Shared Helpers for Explorer & Forecast Charts (Step 3.3)
   ========================================================================== */

export interface CalendarSeriesPoint {
  date: string;
  year_month: string;
  price: number | null;
  is_observed?: boolean;
  is_outlier?: boolean;
}

/**
 * Shared D3 line generator that strictly breaks whenever a month is unobserved
 * (`is_observed === false` or `price === null`).
 */
export function buildObservedLinePath<T extends CalendarSeriesPoint>(
  points: T[],
  xAccessor: (d: T) => number,
  yAccessor: (price: number) => number
): string {
  const gen = line<T>()
    .defined((d) => d.is_observed !== false && typeof d.price === 'number' && Number.isFinite(d.price))
    .x(xAccessor)
    .y((d) => yAccessor(d.price as number))
    .curve(curveMonotoneX);
  return gen(points) ?? '';
}

export type ExplorerRangePreset = '1y' | '3y' | 'all';

export interface ExplorerPointNode {
  index: number;
  date: string;
  year_month: string;
  x: number;
  y: number | null;
  price: number | null;
  isObserved: boolean;
  isOutlier: boolean;
  medianPrice: number | null;
  medianY: number | null;
}

export interface ExplorerChartGeometry {
  width: number;
  height: number;
  margin: { top: number; right: number; bottom: number; left: number };
  historyPath: string;
  medianPath: string;
  yTicks: Array<{ value: number; y: number }>;
  xTicks: Array<{ date: string; year: number; monthNum: number; x: number; isJan: boolean }>;
  points: ExplorerPointNode[];
  minObserved: number | null;
  maxObserved: number | null;
  unobservedCount: number;
}

export function buildExplorerChartGeometry(
  history93: HistoryPoint[],
  median93: CalendarSeriesPoint[],
  rangePreset: ExplorerRangePreset,
  includeMedian: boolean,
  width = 860,
  height = 330,
  isMobile = false
): ExplorerChartGeometry {
  const margin = isMobile
    ? { top: 18, right: 14, bottom: 28, left: 44 }
    : { top: 24, right: 24, bottom: 34, left: 52 };
  const sliceCount = rangePreset === '1y' ? 12 : rangePreset === '3y' ? 36 : history93.length;
  const slicedHist = history93.slice(-sliceCount);
  const slicedMedian = median93.slice(-sliceCount);

  const parseDate = (dStr: string) => new Date(`${dStr}T00:00:00Z`);
  const dates = slicedHist.map((d) => parseDate(d.date));
  const [minDate, maxDate] = extent(dates) as [Date, Date];

  const obsPrices = slicedHist
    .filter((d): d is HistoryPoint & { price: number } => d.is_observed !== false && typeof d.price === 'number' && Number.isFinite(d.price))
    .map((d) => d.price);

  const medianPrices = includeMedian
    ? slicedMedian
        .filter((d): d is CalendarSeriesPoint & { price: number } => d.is_observed !== false && typeof d.price === 'number' && Number.isFinite(d.price))
        .map((d) => d.price)
    : [];

  const allVals = [...obsPrices, ...medianPrices];
  const yMaxRaw = max(allVals) ?? 400;
  const yMax = Math.ceil((yMaxRaw * 1.12) / 50) * 50;

  const xScale = scaleTime()
    .domain([minDate, maxDate])
    .range([margin.left, width - margin.right]);

  const yScale = scaleLinear()
    .domain([0, yMax])
    .nice(5)
    .range([height - margin.bottom, margin.top]);

  const historyPath = buildObservedLinePath(
    slicedHist,
    (d) => xScale(parseDate(d.date)),
    (p) => yScale(p)
  );

  const medianPath = includeMedian
    ? buildObservedLinePath(
        slicedMedian,
        (d) => xScale(parseDate(d.date)),
        (p) => yScale(p)
      )
    : '';

  const yTicks = yScale.ticks(isMobile ? 3 : 5).map((value) => ({
    value,
    y: Math.round(yScale(value) * 10) / 10,
  }));

  const xTicks: Array<{ date: string; year: number; monthNum: number; x: number; isJan: boolean }> = [];
  for (let i = 0; i < slicedHist.length; i++) {
    const pt = slicedHist[i];
    const [yrStr, moStr] = pt.year_month.split('-');
    const yr = parseInt(yrStr, 10);
    const mo = parseInt(moStr, 10);
    if (isMobile) {
      if (rangePreset === '1y') {
        if (i === 0 || i === 4 || i === 8 || i === slicedHist.length - 1) {
          xTicks.push({
            date: pt.date,
            year: yr,
            monthNum: mo,
            x: Math.round(xScale(parseDate(pt.date)) * 10) / 10,
            isJan: mo === 1,
          });
        }
      } else if (rangePreset === '3y') {
        if (mo === 1) {
          xTicks.push({
            date: pt.date,
            year: yr,
            monthNum: mo,
            x: Math.round(xScale(parseDate(pt.date)) * 10) / 10,
            isJan: true,
          });
        }
      } else if (mo === 1 && (yr === 2019 || yr === 2022 || yr === 2025)) {
        xTicks.push({
          date: pt.date,
          year: yr,
          monthNum: mo,
          x: Math.round(xScale(parseDate(pt.date)) * 10) / 10,
          isJan: true,
        });
      }
      continue;
    }
    if (rangePreset === '1y') {
      // Every 2 months on 1y view so labels never collide
      if (i === 0 || i === slicedHist.length - 1 || mo % 2 === 1) {
        xTicks.push({
          date: pt.date,
          year: yr,
          monthNum: mo,
          x: Math.round(xScale(parseDate(pt.date)) * 10) / 10,
          isJan: mo === 1,
        });
      }
    } else if (rangePreset === '3y') {
      if (mo === 1 || mo === 7) {
        xTicks.push({
          date: pt.date,
          year: yr,
          monthNum: mo,
          x: Math.round(xScale(parseDate(pt.date)) * 10) / 10,
          isJan: mo === 1,
        });
      }
    } else {
      if (mo === 1) {
        xTicks.push({
          date: pt.date,
          year: yr,
          monthNum: mo,
          x: Math.round(xScale(parseDate(pt.date)) * 10) / 10,
          isJan: true,
        });
      }
    }
  }

  const medianByDate = new Map<string, number | null>();
  for (const m of slicedMedian) {
    medianByDate.set(m.date, m.is_observed !== false && typeof m.price === 'number' ? m.price : null);
  }

  const points: ExplorerPointNode[] = slicedHist.map((pt, index) => {
    const isObserved = pt.is_observed !== false && typeof pt.price === 'number' && Number.isFinite(pt.price);
    const price = isObserved ? (pt.price as number) : null;
    const medianPrice = medianByDate.get(pt.date) ?? null;
    return {
      index,
      date: pt.date,
      year_month: pt.year_month,
      x: Math.round(xScale(parseDate(pt.date)) * 10) / 10,
      y: price !== null ? Math.round(yScale(price) * 10) / 10 : null,
      price,
      isObserved,
      isOutlier: Boolean(pt.is_outlier),
      medianPrice,
      medianY: medianPrice !== null ? Math.round(yScale(medianPrice) * 10) / 10 : null,
    };
  });

  return {
    width,
    height,
    margin,
    historyPath,
    medianPath,
    yTicks,
    xTicks,
    points,
    minObserved: obsPrices.length ? (min(obsPrices) ?? null) : null,
    maxObserved: obsPrices.length ? (max(obsPrices) ?? null) : null,
    unobservedCount: slicedHist.length - obsPrices.length,
  };
}

export interface SeasonalityBarNode {
  monthNum: number;
  index: number;
  x: number;
  yTop: number;
  barHeight: number;
  isAbove100: boolean;
  isPeak: boolean;
  isTrough: boolean;
}

export interface SeasonalityChartGeometry {
  width: number;
  height: number;
  margin: { top: number; right: number; bottom: number; left: number };
  ref100Y: number;
  yTicks: Array<{ value: number; y: number }>;
  bars: SeasonalityBarNode[];
  barWidth: number;
}

export function buildSeasonalityChartGeometry(
  monthlyIndices: Array<{ month_num: number; index: number }>,
  width = 560,
  height = 220,
  isMobile = false
): SeasonalityChartGeometry {
  const margin = isMobile
    ? { top: 16, right: 10, bottom: 26, left: 36 }
    : { top: 20, right: 16, bottom: 30, left: 42 };
  const sorted = [...monthlyIndices].sort((a, b) => a.month_num - b.month_num);
  const vals = sorted.map((d) => d.index);
  const vMin = Math.min(85, Math.floor(((min(vals) ?? 80) - 6) / 10) * 10);
  const vMax = Math.max(115, Math.ceil(((max(vals) ?? 120) + 6) / 10) * 10);

  let peakMonth = sorted[0]?.month_num ?? 1;
  let troughMonth = sorted[0]?.month_num ?? 1;
  let maxVal = -Infinity;
  let minVal = Infinity;
  for (const d of sorted) {
    if (d.index > maxVal) {
      maxVal = d.index;
      peakMonth = d.month_num;
    }
    if (d.index < minVal) {
      minVal = d.index;
      troughMonth = d.month_num;
    }
  }

  const plotW = width - margin.left - margin.right;
  const stepW = plotW / 12;
  const barWidth = Math.max(isMobile ? 12 : 14, Math.round(stepW * 0.56));

  const yScale = scaleLinear()
    .domain([vMin, vMax])
    .range([height - margin.bottom, margin.top]);

  const ref100Y = Math.round(yScale(100) * 10) / 10;
  const yTicks = yScale.ticks(isMobile ? 3 : 4).map((value) => ({
    value,
    y: Math.round(yScale(value) * 10) / 10,
  }));

  const bars: SeasonalityBarNode[] = sorted.map((d, i) => {
    const cx = Math.round((margin.left + stepW * (i + 0.5)) * 10) / 10;
    const valY = Math.round(yScale(d.index) * 10) / 10;
    const isAbove100 = d.index >= 100;
    const yTop = isAbove100 ? valY : ref100Y;
    const barHeight = Math.max(2, Math.round(Math.abs(valY - ref100Y) * 10) / 10);
    return {
      monthNum: d.month_num,
      index: d.index,
      x: cx,
      yTop,
      barHeight,
      isAbove100,
      isPeak: d.month_num === peakMonth,
      isTrough: d.month_num === troughMonth,
    };
  });

  return {
    width,
    height,
    margin,
    ref100Y,
    yTicks,
    bars,
    barWidth,
  };
}

export interface ForecastChartGeometry {
  width: number;
  height: number;
  margin: { top: number; right: number; bottom: number; left: number };
  asOfX: number;
  forecastEndX: number;
  historyPath: string;
  forecastPath: string;
  band80Path: string;
  band90Path: string;
  yTicks: Array<{ value: number; y: number }>;
  xTicks: Array<{ date: string; year_month: string; x: number; isForecast: boolean }>;
  obsPoints: Array<{
    date: string;
    year_month: string;
    x: number;
    y: number | null;
    price: number | null;
    isObserved: boolean;
  }>;
  lastObsPoint: {
    date: string;
    year_month: string;
    x: number;
    y: number;
    price: number;
  };
  forecastPoints: Array<{
    horizon: number;
    date: string;
    year_month: string;
    x: number;
    y: number;
    yLow80: number;
    yHigh80: number;
    yLow90: number;
    yHigh90: number;
    price: number;
    low80: number;
    high80: number;
    low90: number;
    high90: number;
  }>;
  unobservedCount: number;
}

export function buildForecastChartGeometry(
  history93: HistoryPoint[],
  forecasts: ForecastPoint[],
  width = 860,
  height = 340,
  isMobile = false
): ForecastChartGeometry {
  const margin = isMobile
    ? { top: 22, right: 12, bottom: 28, left: 44 }
    : { top: 28, right: 26, bottom: 34, left: 52 };
  const forecastZoneWidth = isMobile ? 84 : 176;
  const recent24 = history93.slice(-24);
  const parseDate = (dStr: string) => new Date(`${dStr}T00:00:00Z`);

  const dates = recent24.map((d) => parseDate(d.date));
  const [minDate, maxHistDate] = extent(dates) as [Date, Date];

  const observed24 = recent24.filter(
    (d): d is HistoryPoint & { price: number } =>
      d.is_observed !== false && typeof d.price === 'number' && Number.isFinite(d.price)
  );
  const lastObs = observed24[observed24.length - 1];

  const allValues = [
    ...observed24.map((d) => d.price),
    ...forecasts.flatMap((f) => [f.low_90, f.high_90, f.point_forecast]),
  ];
  const yMaxRaw = max(allValues) ?? 400;
  const yMax = Math.ceil((yMaxRaw * 1.14) / 50) * 50;

  const asOfX = width - margin.right - forecastZoneWidth;
  const forecastEndX = width - margin.right;

  const xHistScale = scaleTime().domain([minDate, maxHistDate]).range([margin.left, asOfX]);
  const xForecastScale = scaleLinear().domain([0, 3]).range([asOfX, forecastEndX]);
  const yScale = scaleLinear()
    .domain([0, yMax])
    .nice(5)
    .range([height - margin.bottom, margin.top]);

  const historyPath = buildObservedLinePath(
    recent24,
    (d) => xHistScale(parseDate(d.date)),
    (p) => yScale(p)
  );

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

  const yTicks = yScale.ticks(isMobile ? 3 : 5).map((value) => ({
    value,
    y: Math.round(yScale(value) * 10) / 10,
  }));

  const xTicks: Array<{ date: string; year_month: string; x: number; isForecast: boolean }> = [];
  for (let i = 0; i < recent24.length; i++) {
    const keepTick = isMobile
      ? i === 0 || i === 12
      : i === 0 || i === 6 || i === 12 || i === 18 || i === recent24.length - 1;
    if (keepTick) {
      const pt = recent24[i];
      xTicks.push({
        date: pt.date,
        year_month: pt.year_month,
        x: Math.round(xHistScale(parseDate(pt.date)) * 10) / 10,
        isForecast: false,
      });
    }
  }
  const h3Fc = forecasts[forecasts.length - 1];
  if (h3Fc) {
    xTicks.push({
      date: h3Fc.target_date,
      year_month: h3Fc.year_month,
      x: Math.round(xForecastScale(h3Fc.horizon_months) * 10) / 10,
      isForecast: true,
    });
  }

  const obsPoints = recent24.map((pt) => {
    const isObserved = pt.is_observed !== false && typeof pt.price === 'number' && Number.isFinite(pt.price);
    return {
      date: pt.date,
      year_month: pt.year_month,
      x: Math.round(xHistScale(parseDate(pt.date)) * 10) / 10,
      y: isObserved ? Math.round(yScale(pt.price as number) * 10) / 10 : null,
      price: isObserved ? (pt.price as number) : null,
      isObserved,
    };
  });

  const forecastPoints = forecasts.map((f) => ({
    horizon: f.horizon_months,
    date: f.target_date,
    year_month: f.year_month,
    x: Math.round(xForecastScale(f.horizon_months) * 10) / 10,
    y: Math.round(yScale(f.point_forecast) * 10) / 10,
    yLow80: Math.round(yScale(f.low_80) * 10) / 10,
    yHigh80: Math.round(yScale(f.high_80) * 10) / 10,
    yLow90: Math.round(yScale(f.low_90) * 10) / 10,
    yHigh90: Math.round(yScale(f.high_90) * 10) / 10,
    price: f.point_forecast,
    low80: f.low_80,
    high80: f.high_80,
    low90: f.low_90,
    high90: f.high_90,
  }));

  return {
    width,
    height,
    margin,
    asOfX: Math.round(asOfX * 10) / 10,
    forecastEndX: Math.round(forecastEndX * 10) / 10,
    historyPath,
    forecastPath: fcLineGen(bridgePoints) ?? '',
    band80Path: area80Gen(bridgePoints) ?? '',
    band90Path: area90Gen(bridgePoints) ?? '',
    yTicks,
    xTicks,
    obsPoints,
    lastObsPoint: {
      date: lastObs.date,
      year_month: lastObs.year_month,
      x: Math.round(xHistScale(parseDate(lastObs.date)) * 10) / 10,
      y: Math.round(yScale(lastObs.price) * 10) / 10,
      price: lastObs.price,
    },
    forecastPoints,
    unobservedCount: recent24.length - observed24.length,
  };
}
