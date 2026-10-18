import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {scaleLinear} from 'd3-scale';
import {C, CASH_COLOR, ETF_COLORS, FONT, RAMP, STRATEGY_COLORS, T} from '../brand';

/* ---------------------------------------------------------------- helpers */

const hex = (h: string) => [
  parseInt(h.slice(1, 3), 16),
  parseInt(h.slice(3, 5), 16),
  parseInt(h.slice(5, 7), 16),
];

/** Piecewise-linear sample of the brand sequential ramp. */
export const rampColor = (t: number): string => {
  const x = Math.max(0, Math.min(1, t));
  for (let i = 0; i < RAMP.length - 1; i++) {
    const [p0, c0] = RAMP[i];
    const [p1, c1] = RAMP[i + 1];
    if (x <= p1) {
      const k = p1 === p0 ? 0 : (x - p0) / (p1 - p0);
      const a = hex(c0);
      const b = hex(c1);
      return `rgb(${a.map((v, j) => Math.round(v + (b[j] - v) * k)).join(',')})`;
    }
  }
  return RAMP[RAMP.length - 1][1];
};

const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

/** frame -> eased 0..1 over [start, start+dur]. */
const prog = (frame: number, start: number, dur: number) =>
  easeOutCubic(
    interpolate(frame, [start, start + dur], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    }),
  );

/* ------------------------------------------------------- animated heatmap */

export type Panel = {name: string; grid: (number | null)[][]};

/**
 * Cells fill and count up column by column, left to right, which is the
 * rebalance axis: the reveal order is the argument the scene is making.
 * Re-laid out for video -- far fewer, far larger cells than the paper's
 * five-panel page figure, and the benchmark panel is dropped to a caption.
 */
export const AnimatedHeatmap: React.FC<{
  panels: Panel[];
  risks: string[];
  freqs: string[];
  vmin: number;
  vmax: number;
  decimals?: number;
  width: number;
  height: number;
  /** frame each panel's cells begin filling */
  panelStart: number[];
  /** frame the panel titles and axes appear; keeping them together stops the
   *  first panel sitting alone in a quarter of the frame */
  chromeAt?: number;
  colStagger?: number;
  cellDur?: number;
  /** index into risks; outlines that row once revealed */
  highlightRow?: number;
  highlightFrom?: number;
}> = ({
  panels,
  risks,
  freqs,
  vmin,
  vmax,
  decimals = 0,
  width,
  height,
  panelStart,
  chromeAt = 0,
  colStagger = 14,
  cellDur = 20,
  highlightRow,
  highlightFrom,
}) => {
  const frame = useCurrentFrame();
  const GAP = 26;
  const AXIS_W = 92;
  const TITLE_H = 40;
  const XLAB_H = 34;
  const panelW = (width - AXIS_W - GAP * (panels.length - 1)) / panels.length;
  const cellH = (height - TITLE_H - XLAB_H) / risks.length;

  return (
    <svg width={width} height={height} style={{display: 'block', overflow: 'visible'}}>
      {panels.map((panel, pi) => {
        const x0 = AXIS_W + pi * (panelW + GAP);
        const cellW = panelW / freqs.length;
        const start = panelStart[pi] ?? 0;
        const chrome = prog(frame, chromeAt, 16);
        return (
          <g key={panel.name}>
            <text
              x={x0 + panelW / 2}
              y={TITLE_H - 14}
              textAnchor="middle"
              fill={C.text}
              opacity={chrome}
              style={{fontFamily: FONT.sans, fontSize: 26, fontWeight: 700}}
            >
              {panel.name}
            </text>
            {risks.map((_, ri) =>
              freqs.map((_f, ci) => (
                <rect
                  key={`slot-${ri}-${ci}`}
                  x={x0 + ci * (panelW / freqs.length) + 1}
                  y={TITLE_H + ri * cellH + 1}
                  width={panelW / freqs.length - 2}
                  height={cellH - 2}
                  fill="rgba(255,255,255,.028)"
                  opacity={chrome}
                />
              )),
            )}

            {risks.map((_, ri) =>
              freqs.map((_f, ci) => {
                const v = panel.grid[ri][ci];
                const cs = start + ci * colStagger;
                const p = prog(frame, cs, cellDur);
                if (p <= 0 || v == null) return null;
                const t = (v - vmin) / (vmax - vmin || 1);
                // The number fades in at its true value rather than counting up.
                // A count-up through 64 on its way to 258 is a false reading if
                // anyone pauses, which is not a trade worth making in a paper.
                const labelIn = prog(frame, cs + cellDur * 0.35, cellDur * 0.65);
                const x = x0 + ci * cellW;
                const y = TITLE_H + ri * cellH;
                return (
                  <g key={`${ri}-${ci}`}>
                    <rect
                      x={x + 1}
                      y={y + 1}
                      width={cellW - 2}
                      height={cellH - 2}
                      fill={rampColor(t)}
                      opacity={p}
                    />
                    <text
                      x={x + cellW / 2}
                      y={y + cellH / 2 + 10}
                      textAnchor="middle"
                      fill={t < 0.5 ? '#EAF3F5' : '#06222A'}
                      opacity={labelIn}
                      style={{
                        fontFamily: FONT.sans,
                        fontSize: 29,
                        fontWeight: 600,
                        fontVariantNumeric: 'tabular-nums',
                      }}
                    >
                      {v.toFixed(decimals)}
                    </text>
                  </g>
                );
              }),
            )}

            {highlightRow != null && highlightFrom != null && pi === 0 ? (
              <rect
                x={x0}
                y={TITLE_H + highlightRow * cellH}
                width={panelW}
                height={cellH}
                fill="none"
                stroke={C.glow}
                strokeWidth={3}
                opacity={prog(frame, highlightFrom, 14) * 0.9}
              />
            ) : null}

            {freqs.map((f, ci) => (
              <text
                key={f}
                x={x0 + ci * cellW + cellW / 2}
                y={height - 10}
                textAnchor="middle"
                fill={C.text3}
                opacity={chrome}
                style={{fontFamily: FONT.sans, fontSize: 22}}
              >
                {f}
              </text>
            ))}
          </g>
        );
      })}

      {risks.map((r, ri) => (
        <text
          key={r}
          x={AXIS_W - 18}
          y={TITLE_H + ri * cellH + cellH / 2 + 8}
          textAnchor="end"
          fill={C.text3}
          opacity={prog(frame, chromeAt, 16)}
          style={{fontFamily: FONT.sans, fontSize: 22, fontVariantNumeric: 'tabular-nums'}}
        >
          {r}
        </text>
      ))}
    </svg>
  );
};

/* ------------------------------------------------- animated stacked areas */

export type WeightsData = {
  dates: string[];
  columns: string[];
  tenures: Record<string, Record<string, number[][]>>;
};

/**
 * Four proxies as a 2x2 grid rather than the paper's four full-width rows, so
 * each panel is roughly three times taller and the bands are actually
 * readable at 1080p. The tenures are tweened in place on a shared monthly
 * grid, so the convergence is something you watch happen rather than a cut
 * between two images.
 */
export const AnimatedWeights: React.FC<{
  data: WeightsData;
  strategies: string[];
  width: number;
  height: number;
  /** [{freq, at}] - `at` is the frame this tenure is fully settled */
  schedule: {freq: string; at: number}[];
  tweenFrames: number;
  /** frames over which the first tenure sweeps in left to right */
  sweepFrames: number;
}> = ({data, strategies, width, height, schedule, tweenFrames, sweepFrames}) => {
  const frame = useCurrentFrame();
  const n = data.dates.length;

  // which pair of tenures are we between, and how far
  let from = schedule[0].freq;
  let to = schedule[0].freq;
  let k = 1;
  for (let i = 0; i < schedule.length; i++) {
    if (frame >= schedule[i].at) {
      from = to = schedule[i].freq;
      k = 1;
    }
    if (i + 1 < schedule.length && frame > schedule[i].at && frame < schedule[i + 1].at) {
      const tweenStart = schedule[i + 1].at - tweenFrames;
      if (frame >= tweenStart) {
        from = schedule[i].freq;
        to = schedule[i + 1].freq;
        k = easeOutCubic((frame - tweenStart) / tweenFrames);
      }
    }
  }

  // Linear, not eased. This drives an index into a time axis: an ease-out
  // flattens near the end, consecutive frames round to the same month, and the
  // sweep sits visibly frozen for its last second or two.
  const sweep = interpolate(frame, [0, sweepFrames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const visible = Math.max(2, Math.round(n * sweep));

  const COLS = 2;
  const GAP_X = 40;
  const GAP_Y = 46;
  const panelW = (width - GAP_X) / COLS;
  const panelH = (height - GAP_Y) / 2 - 26;

  const x = scaleLinear().domain([0, n - 1]).range([0, panelW]);
  const y = scaleLinear().domain([0, 100]).range([panelH, 0]);

  return (
    <svg width={width} height={height} style={{display: 'block', overflow: 'visible'}}>
      {strategies.map((s, si) => {
        const gx = (si % COLS) * (panelW + GAP_X);
        const gy = Math.floor(si / COLS) * (panelH + GAP_Y + 26) + 26;
        const a = data.tenures[from]?.[s];
        const b = data.tenures[to]?.[s];
        if (!a || !b) return null;

        // cumulative stack, interpolated between the two tenures
        const cum = new Array(visible).fill(0);
        const bands: {color: string; d: string}[] = [];
        for (let ci = 0; ci < data.columns.length; ci++) {
          const top: number[] = new Array(visible);
          for (let i = 0; i < visible; i++) {
            const v = a[ci][i] + (b[ci][i] - a[ci][i]) * k;
            cum[i] += v;
            top[i] = cum[i];
          }
          let d = `M ${x(0)} ${y(cum[0] - (a[ci][0] + (b[ci][0] - a[ci][0]) * k))}`;
          const bottom: number[] = new Array(visible);
          for (let i = 0; i < visible; i++) {
            const v = a[ci][i] + (b[ci][i] - a[ci][i]) * k;
            bottom[i] = cum[i] - v;
          }
          d = `M ${x(0)} ${y(top[0])}`;
          for (let i = 1; i < visible; i++) d += ` L ${x(i)} ${y(top[i])}`;
          for (let i = visible - 1; i >= 0; i--) d += ` L ${x(i)} ${y(bottom[i])}`;
          d += ' Z';
          bands.push({
            color: data.columns[ci] === 'CSH' ? CASH_COLOR : ETF_COLORS[ci % ETF_COLORS.length],
            d,
          });
        }

        return (
          <g key={s} transform={`translate(${gx},${gy})`}>
            <text
              x={0}
              y={-10}
              fill={C.text}
              style={{fontFamily: FONT.sans, fontSize: 24, fontWeight: 700}}
            >
              {s}
            </text>
            <rect x={0} y={0} width={panelW} height={panelH} fill="rgba(255,255,255,.025)" />
            {bands.map((band, i) => (
              <path key={i} d={band.d} fill={band.color} />
            ))}
            {[0, 50, 100].map((g) => (
              <line
                key={g}
                x1={0}
                x2={panelW}
                y1={y(g)}
                y2={y(g)}
                stroke={C.rule}
                strokeWidth={1}
              />
            ))}
          </g>
        );
      })}
    </svg>
  );
};

/* ------------------------------------------------------- animated curves */

export type CurveData = Record<string, {dates: string[]; series: Record<string, number[]>}>;

/** Indexed portfolio value, drawn on left to right: 27 years unfolding. */
export const AnimatedCurves: React.FC<{
  data: CurveData;
  freqs: string[];
  width: number;
  height: number;
  drawFrames: number;
}> = ({data, freqs, width, height, drawFrames}) => {
  const frame = useCurrentFrame();
  const COLS = 2;
  const GAP_X = 54;
  const GAP_Y = 54;
  const panelW = (width - GAP_X) / COLS;
  const panelH = (height - GAP_Y) / 2 - 24;

  const all = freqs.flatMap((f) => Object.values(data[f].series).flat());
  const vmax = Math.max(...all);
  // Linear for the same reason as the weights sweep: this is a time axis.
  const t = interpolate(frame, [0, drawFrames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <svg width={width} height={height} style={{display: 'block', overflow: 'visible'}}>
      {freqs.map((f, fi) => {
        const d = data[f];
        const n = d.dates.length;
        const visible = Math.max(2, Math.round(n * t));
        const x = scaleLinear().domain([0, n - 1]).range([0, panelW]);
        const y = scaleLinear().domain([0, vmax]).range([panelH, 0]);
        const gx = (fi % COLS) * (panelW + GAP_X);
        const gy = Math.floor(fi / COLS) * (panelH + GAP_Y + 24) + 24;
        return (
          <g key={f} transform={`translate(${gx},${gy})`}>
            <text x={0} y={-10} fill={C.text} style={{fontFamily: FONT.sans, fontSize: 24, fontWeight: 700}}>
              {f}
            </text>
            {[0, 200, 400, 600].map((g) =>
              g <= vmax ? (
                <g key={g}>
                  <line x1={0} x2={panelW} y1={y(g)} y2={y(g)} stroke={C.rule} strokeWidth={1} />
                  <text x={-10} y={y(g) + 6} textAnchor="end" fill={C.text3} style={{fontFamily: FONT.sans, fontSize: 18}}>
                    {g}
                  </text>
                </g>
              ) : null,
            )}
            {Object.entries(d.series).map(([name, vals]) => {
              let path = `M ${x(0)} ${y(vals[0])}`;
              for (let i = 1; i < visible; i++) path += ` L ${x(i)} ${y(vals[i])}`;
              return (
                <path
                  key={name}
                  d={path}
                  fill="none"
                  stroke={STRATEGY_COLORS[name] ?? C.text3}
                  strokeWidth={name === 'S&P 500' ? 2 : 2.6}
                  strokeOpacity={name === 'S&P 500' ? 0.75 : 1}
                  strokeDasharray={name === 'S&P 500' ? '7 5' : undefined}
                />
              );
            })}
          </g>
        );
      })}
    </svg>
  );
};
