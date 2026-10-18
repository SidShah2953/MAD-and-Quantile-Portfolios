/**
 * Standalone SVG of the dispersion chart's settled state.
 *
 * The chart in the video is live SVG drawn per frame by AnimatedDispersion;
 * this writes the same geometry to a file so the figure can be dropped into a
 * slide, a post or the paper without going through a raster screenshot.
 *
 * Usage:  node tools/export_dispersion_svg.mjs
 */
import {readFileSync, writeFileSync} from 'node:fs';
import {scaleLinear} from 'd3-scale';

const C = {
  ground: '#050C0F', text: '#DEEAEC', text3: '#8CA2A6',
  rule: 'rgba(255,255,255,.08)', ruleStrong: 'rgba(255,255,255,.14)',
  warn: '#E0A88F', glow: '#45B5ED', inner: '#0C2B38',
};
const SANS = '"Schibsted Grotesk","Helvetica Neue",Arial,sans-serif';

const d = JSON.parse(readFileSync(new URL('../public/data/dispersion.json', import.meta.url)));
const W = 1728, H = 420, PAD_L = 92, PAD_B = 46, PAD_T = 16;
const w = W - PAD_L, h = H - PAD_B - PAD_T;
const n = d.periods.length;
const band = (s) => 2 * s * 100;
const vmax = Math.max(...d.stdAll.map(band)) * 1.08;
const x = scaleLinear().domain([0, n - 1]).range([0, w]);
const y = scaleLinear().domain([-vmax, vmax]).range([h, 0]);

const area = (vals) => {
  let p = `M ${x(0)} ${y(band(vals[0]))}`;
  for (let i = 1; i < n; i++) p += ` L ${x(i)} ${y(band(vals[i]))}`;
  for (let i = n - 1; i >= 0; i--) p += ` L ${x(i)} ${y(-band(vals[i]))}`;
  return p + ' Z';
};

const worst = d.stdAll.map((s, i) => ({i, r: s / d.stdTrimmed[i]})).reduce((a, b) => (b.r > a.r ? b : a));
const ticks = [0, 10, 20, 30, 40, n - 1];

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<rect width="${W}" height="${H}" fill="${C.ground}"/>
<g transform="translate(${PAD_L},${PAD_T})" font-family='${SANS}'>
${[-vmax / 2, 0, vmax / 2].map((g) => `  <line x1="0" x2="${w}" y1="${y(g).toFixed(1)}" y2="${y(g).toFixed(1)}" stroke="${g === 0 ? C.ruleStrong : C.rule}"/>
  <text x="-14" y="${(y(g) + 6).toFixed(1)}" text-anchor="end" fill="${C.text3}" font-size="19">${g.toFixed(1)}%</text>`).join('\n')}
  <path d="${area(d.stdAll)}" fill="${C.warn}" fill-opacity="0.5"/>
  <path d="${area(d.stdTrimmed)}" fill="${C.inner}"/>
  <path d="${area(d.stdTrimmed)}" fill="${C.glow}" fill-opacity="0.5"/>
  <circle cx="${x(worst.i).toFixed(1)}" cy="${y(band(d.stdAll[worst.i])).toFixed(1)}" r="6" fill="${C.warn}"/>
  <circle cx="${x(worst.i).toFixed(1)}" cy="${y(-band(d.stdAll[worst.i])).toFixed(1)}" r="6" fill="${C.warn}"/>
  <circle cx="${x(worst.i).toFixed(1)}" cy="${y(band(d.stdTrimmed[worst.i])).toFixed(1)}" r="6" fill="${C.glow}"/>
  <circle cx="${x(worst.i).toFixed(1)}" cy="${y(-band(d.stdTrimmed[worst.i])).toFixed(1)}" r="6" fill="${C.glow}"/>
  <text x="${(x(worst.i) + 16).toFixed(1)}" y="${(y(vmax * 0.72)).toFixed(1)}" fill="${C.text}" font-size="24" font-weight="700">${d.periods[worst.i]}</text>
  <text x="${(x(worst.i) + 16).toFixed(1)}" y="${(y(vmax * 0.72) + 30).toFixed(1)}" fill="${C.warn}" font-size="25" font-weight="600">${worst.r.toFixed(2)}&#215; inflated</text>
${ticks.map((i) => `  <text x="${x(i).toFixed(1)}" y="${h + 30}" text-anchor="middle" fill="${C.text3}" font-size="19">${d.periods[i]}</text>`).join('\n')}
</g>
</svg>
`;

const out = new URL('../out/dispersion.svg', import.meta.url);
writeFileSync(out, svg);
console.log(`wrote ${out.pathname}  (${(svg.length / 1024).toFixed(0)} KB, ${n} half-years, worst ${d.periods[worst.i]} at ${worst.r.toFixed(2)}x)`);
