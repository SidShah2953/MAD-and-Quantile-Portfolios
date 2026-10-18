import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {scaleLinear} from 'd3-scale';
import {C, FONT, T} from '../brand';

/** 0..1 over `dur` frames starting at `start`. Explicitly a duration, not an
 *  end frame: mixing the two silently produces a decreasing input range. */
const seg = (frame: number, start: number, dur: number) =>
  interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

/* --------------------------------------------- scene 1: dispersion bands */

export type DispersionData = {
  periods: string[];
  stdAll: number[];
  stdTrimmed: number[];
  nOutliers: number[];
};

/**
 * The motivation figure, rebuilt for video. The paper draws 54 box-and-whisker
 * columns; at 1080p that is a texture, not a chart. Same statistic, same data:
 * the pooled half-yearly dispersion of sector returns with outliers in (outer
 * band) and with the 1.5xIQR outliers removed (inner band). The halo between
 * them is the inflation the optimiser is handed, and a cursor rides the sweep
 * reading it out period by period.
 */
export const AnimatedDispersion: React.FC<{
  data: DispersionData;
  width: number;
  height: number;
  sweepFrames: number;
  /** frame at which the cursor finishes gliding back onto the worst period */
  pinAt: number;
  /** scene frame at which this chart becomes visible */
  start?: number;
}> = ({data, width, height, sweepFrames, pinAt, start = 0}) => {
  const frame = useCurrentFrame() - start;
  const n = data.periods.length;
  const PAD_L = 92;
  const PAD_B = 46;
  const PAD_T = 16;
  const w = width - PAD_L;
  const h = height - PAD_B - PAD_T;

  const band = (s: number) => 2 * s * 100; // +/-2 sigma, in percent
  const vmax = Math.max(...data.stdAll.map(band)) * 1.08;
  const x = scaleLinear().domain([0, n - 1]).range([0, w]);
  const y = scaleLinear().domain([-vmax, vmax]).range([h, 0]);

  const worst = data.stdAll
    .map((s, i) => ({i, r: s / data.stdTrimmed[i]}))
    .reduce((a, b) => (b.r > a.r ? b : a));

  const swept = seg(frame, 0, sweepFrames);
  const sweepI = (n - 1) * swept;
  // after the sweep, travel back along the series and settle on the worst period
  const back = easeOut(seg(frame, pinAt - 34, 34));
  const cursorI = Math.max(0, Math.round(sweepI + (worst.i - sweepI) * back));
  // the bands stay fully drawn once the sweep has finished
  const visible = Math.max(2, Math.round(Math.max(sweepI, (n - 1) * swept)) + 1);

  const area = (vals: number[], k: number) => {
    let d = `M ${x(0)} ${y(band(vals[0]) * k)}`;
    for (let i = 1; i < visible; i++) d += ` L ${x(i)} ${y(band(vals[i]) * k)}`;
    for (let i = visible - 1; i >= 0; i--) d += ` L ${x(i)} ${y(-band(vals[i]) * k)}`;
    return d + ' Z';
  };

  const grow = easeOut(seg(frame, 0, 18));
  const ratio = data.stdAll[cursorI] / data.stdTrimmed[cursorI];

  return (
    <svg width={width} height={height} style={{display: 'block', overflow: 'visible'}}>
      <g transform={`translate(${PAD_L},${PAD_T})`}>
        {[-vmax / 2, 0, vmax / 2].map((g) => (
          <g key={g}>
            <line x1={0} x2={w} y1={y(g)} y2={y(g)} stroke={g === 0 ? C.ruleStrong : C.rule} />
            <text x={-14} y={y(g) + 6} textAnchor="end" fill={C.text3} style={{fontFamily: FONT.sans, fontSize: 19}}>
              {g.toFixed(1)}%
            </text>
          </g>
        ))}

        <path d={area(data.stdAll, grow)} fill={C.warn} fillOpacity={0.5} />
        <path d={area(data.stdTrimmed, grow)} fill="#0C2B38" />
        <path d={area(data.stdTrimmed, grow)} fill={C.glow} fillOpacity={0.5} />

        {/* leading-edge markers: the actual points, moving along the path */}
        {[1, -1].map((sgn) => (
          <g key={sgn}>
            <circle cx={x(cursorI)} cy={y(sgn * band(data.stdAll[cursorI]) * grow)} r={6} fill={C.warn} />
            <circle cx={x(cursorI)} cy={y(sgn * band(data.stdTrimmed[cursorI]) * grow)} r={6} fill={C.glow} />
          </g>
        ))}
        <line
          x1={x(cursorI)}
          x2={x(cursorI)}
          y1={y(band(data.stdAll[cursorI]) * grow)}
          y2={y(-band(data.stdAll[cursorI]) * grow)}
          stroke={C.text3}
          strokeWidth={1}
          strokeDasharray="3 4"
        />

        {[0, 10, 20, 30, 40, 53].map((i) => (
          <text
            key={i}
            x={x(i)}
            y={h + 30}
            textAnchor="middle"
            fill={C.text3}
            style={{fontFamily: FONT.sans, fontSize: 19}}
          >
            {data.periods[i]}
          </text>
        ))}

        {/* live readout, parked on the worst period once pinned */}
        <g
          transform={`translate(${Math.min(w - 300, Math.max(0, x(cursorI) + 18))},${y(vmax * 0.62)})`}
          opacity={seg(frame, 10, 14)}
        >
          <rect x={0} y={-34} width={290} height={76} rx={10} fill="rgba(5,12,15,.82)" stroke={C.rule} />
          <text x={16} y={-8} fill={C.text} style={{fontFamily: FONT.sans, fontSize: 24, fontWeight: 700}}>
            {data.periods[cursorI]}
          </text>
          <text x={16} y={26} fill={C.warn} style={{fontFamily: FONT.sans, fontSize: 25, fontWeight: 600, fontVariantNumeric: 'tabular-nums'}}>
            {ratio.toFixed(2)}&times; inflated
          </text>
        </g>
      </g>
    </svg>
  );
};

/* ------------------------------------------- scene 2: no-look-ahead timeline */

/**
 * The timeline schematic, rebuilt as a staged reveal: estimation window, then
 * the arrow that says what is taken from it, then the rebalance boundary, then
 * the holding window it feeds. Built here rather than swept over a rendered
 * PNG so each step lands when the text explaining it lands.
 */
export const AnimatedTimeline: React.FC<{width: number; height: number; start?: number}> = ({
  width,
  height,
  start = 0,
}) => {
  const frame = useCurrentFrame() - start;
  const MID = height / 2;
  const BOX_H = 104;
  const half = (width - 30) / 2;
  const estW = half * easeOut(seg(frame, 0, 26));
  const holdW = half * easeOut(seg(frame, 54, 26));
  const axis = seg(frame, 0, 20);

  return (
    <svg width={width} height={height} style={{display: 'block', overflow: 'visible'}}>
      <line
        x1={0}
        x2={width * axis}
        y1={MID + BOX_H / 2 + 64}
        y2={MID + BOX_H / 2 + 64}
        stroke={C.text3}
        strokeWidth={2}
      />
      <polygon
        points={`${width * axis},${MID + BOX_H / 2 + 64} ${width * axis - 13},${MID + BOX_H / 2 + 58} ${width * axis - 13},${MID + BOX_H / 2 + 70}`}
        fill={C.text3}
        opacity={axis}
      />
      <text x={0} y={MID + BOX_H / 2 + 94} fill={C.text3} style={{fontFamily: FONT.sans, fontSize: 20}}>
        Time
      </text>

      {/* estimation window */}
      <rect x={0} y={MID - BOX_H / 2} width={estW} height={BOX_H} rx={8} fill="#123B38" stroke="#7FCBB8" strokeWidth={2} />
      <text
        x={half / 2}
        y={MID + 7}
        textAnchor="middle"
        fill={C.text}
        opacity={seg(frame, 18, 12)}
        style={{fontFamily: FONT.sans, fontSize: 23, fontWeight: 700}}
      >
        Period k−1 · estimation window
      </text>

      {/* what we take from it */}
      <g opacity={seg(frame, 30, 14)}>
        <line x1={28} x2={half - 40} y1={MID + BOX_H / 2 + 26} y2={MID + BOX_H / 2 + 26} stroke="#7FCBB8" strokeWidth={2} />
        <polygon points={`${half - 40},${MID + BOX_H / 2 + 26} ${half - 52},${MID + BOX_H / 2 + 20} ${half - 52},${MID + BOX_H / 2 + 32}`} fill="#7FCBB8" />
        <text x={28} y={MID + BOX_H / 2 + 52} fill="#7FCBB8" style={{fontFamily: FONT.sans, fontSize: 21, fontStyle: 'italic'}}>
          estimate the dispersion here
        </text>
      </g>

      {/* the rebalance boundary */}
      <g opacity={seg(frame, 46, 10)}>
        <line
          x1={half + 15}
          x2={half + 15}
          y1={MID - BOX_H / 2 - 34}
          y2={MID + BOX_H / 2 + 14}
          stroke={C.warn}
          strokeWidth={3}
          strokeDasharray="8 7"
        />
        <text x={half + 15} y={MID - BOX_H / 2 - 48} textAnchor="middle" fill={C.warn} style={{fontFamily: FONT.sans, fontSize: 22, fontWeight: 700}}>
          rebalance
        </text>
      </g>

      {/* holding window */}
      <rect
        x={half + 30}
        y={MID - BOX_H / 2}
        width={holdW}
        height={BOX_H}
        rx={8}
        fill="#0F3448"
        stroke={C.glow}
        strokeWidth={2}
      />
      <text
        x={half + 30 + half / 2}
        y={MID + 7}
        textAnchor="middle"
        fill={C.text}
        opacity={seg(frame, 72, 12)}
        style={{fontFamily: FONT.sans, fontSize: 23, fontWeight: 700}}
      >
        Period k · holding window
      </text>

      <g opacity={seg(frame, 84, 14)}>
        <line x1={half + 120} x2={width - 24} y1={MID - BOX_H / 2 - 26} y2={MID - BOX_H / 2 - 26} stroke={C.glow} strokeWidth={2} />
        <polygon points={`${width - 24},${MID - BOX_H / 2 - 26} ${width - 36},${MID - BOX_H / 2 - 32} ${width - 36},${MID - BOX_H / 2 - 20}`} fill={C.glow} />
        <text x={half + 120} y={MID - BOX_H / 2 - 38} fill={C.glow} style={{fontFamily: FONT.sans, fontSize: 21, fontStyle: 'italic'}}>
          hold those weights here, unchanged
        </text>
      </g>
    </svg>
  );
};
