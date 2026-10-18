/**
 * Brand tokens lifted verbatim from the website's only source of truth,
 * src/layouts/Shell.astro (~/Developer/website). Keep these in sync by hand:
 * the video has no build-time access to the site's CSS.
 */
export const C = {
  ground: '#050C0F',
  deep: '#0A2027',
  abyss: '#0C3A42',
  peacock: '#208EC5',
  glow: '#45B5ED',
  azure: '#2F6FE8',
  iris: '#6A5AD8',
  text: '#DEEAEC',
  text2: '#B4C6CA',
  text3: '#8CA2A6',
  rule: 'rgba(255,255,255,.08)',
  ruleStrong: 'rgba(255,255,255,.14)',
  peacockWash: 'rgba(32,142,197,.10)',
  peacockWashStrong: 'rgba(32,142,197,.17)',
  peacockLine: 'rgba(32,142,197,.42)',
  glowLine: 'rgba(69,181,237,.38)',
  glowLineSoft: 'rgba(69,181,237,.24)',
  onAccent: '#04171B',
  /** the one non-palette signal colour; reserved for the caveat scene */
  warn: '#E0A88F',
} as const;

export const FONT = {
  serif: '"Newsreader", Georgia, "Times New Roman", serif',
  sans: '"Schibsted Grotesk", "Helvetica Neue", Arial, sans-serif',
} as const;

/** 1920x1080 with a 96px safe gutter. */
export const SAFE = 96;
export const FPS = 30;

/**
 * One locked type scale. Every size in the piece comes from here: ad-hoc sizes
 * are what make a sequence of scenes read as a montage rather than one object.
 */
export const T = {
  display: 72,   // the opening question; the caveat headline
  stat: 64,      // the four big numbers in the test scene
  h1: 56,        // scene headlines and the closing statement
  h2: 44,        // the convergence headline, which shares its row with a figure
  lead: 34,      // the single line under a headline
  body: 28,      // annotations, the convergence rail, chips
  caption: 24,   // figure captions, meta, stat labels
  eyebrow: 22,   // the uppercase kicker
} as const;

/**
 * The same stops as BRAND_SEQ in tools/render_brand_figures.py. Luminance has
 * to cross over at 0.5, because the cell label flips from light to dark there.
 */
export const RAMP: [number, string][] = [
  [0.0, '#0E3A4B'],
  [0.3, '#156A90'],
  [0.48, '#2190C6'],
  [0.52, '#4FB2E2'],
  [0.72, '#93D4F2'],
  [1.0, '#DCF1FC'],
];

/** Nine sector bands plus cash, matching ETF_RAMP in the figure renderer. */
export const ETF_COLORS = [
  '#45B5ED', '#17556F', '#E0A88F', '#8ED3F0', '#2E9E8F',
  '#7FCBB8', '#2F6FE8', '#C98BC0', '#6A5AD8',
];
export const CASH_COLOR = '#384D55';

export const STRATEGY_COLORS: Record<string, string> = {
  'S&P 500': '#8CA2A6',
  Volatility: '#45B5ED',
  MAD: '#E0A88F',
  IQR: '#6A5AD8',
  P95: '#2E9E8F',
};
