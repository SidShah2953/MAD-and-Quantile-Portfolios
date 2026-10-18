import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {C, FONT, SAFE, T} from '../brand';

/** Ground + the site's faint peacock haze, so every scene sits on the same base. */
export const Stage: React.FC<{children: React.ReactNode}> = ({children}) => (
  <AbsoluteFill style={{backgroundColor: C.ground}}>
    <AbsoluteFill
      style={{
        background:
          `radial-gradient(1200px 700px at 18% 8%, ${C.peacockWash}, transparent 70%),` +
          `radial-gradient(1000px 620px at 88% 92%, rgba(106,90,216,.08), transparent 70%)`,
      }}
    />
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        padding: SAFE,
        boxSizing: 'border-box',
      }}
    >
      {children}
    </div>
  </AbsoluteFill>
);

/** Fade + a short rise. delay is in frames. */
export const Rise: React.FC<{
  delay?: number;
  y?: number;
  /** Render fully settled from frame 0. The opening frame is the thumbnail, so
   *  the first scene's kicker and headline must not animate up from nothing. */
  static?: boolean;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({delay = 0, y = 26, static: isStatic = false, children, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = isStatic
    ? 1
    : spring({frame: frame - delay, fps, config: {damping: 200}, durationInFrames: 26});
  return (
    <div style={{...style, opacity: s, transform: `translateY(${(1 - s) * y}px)`}}>{children}</div>
  );
};

/**
 * Kept as a passthrough. Scene fade-out used to live here, but crossfades are
 * now handled by <TransitionSeries> in Video.tsx; doing both would double-fade
 * and dip to the bare ground between scenes.
 */
export const SceneFade: React.FC<{out?: number; children: React.ReactNode}> = ({children}) => (
  <div style={{width: '100%', height: '100%'}}>{children}</div>
);

export const Eyebrow: React.FC<{children: React.ReactNode; color?: string}> = ({children, color = C.glow}) => (
  <div
    style={{
      fontFamily: FONT.sans,
      fontSize: T.eyebrow,
      letterSpacing: '.18em',
      textTransform: 'uppercase',
      fontWeight: 600,
      color,
    }}
  >
    {children}
  </div>
);

export const Title: React.FC<{children: React.ReactNode; size?: number; style?: React.CSSProperties}> = ({
  children,
  size = T.h1,
  style,
}) => (
  <div
    style={{
      fontFamily: FONT.serif,
      fontSize: size,
      lineHeight: 1.12,
      fontWeight: 500,
      color: C.text,
      letterSpacing: '-.01em',
      ...style,
    }}
  >
    {children}
  </div>
);

export const Body: React.FC<{children: React.ReactNode; size?: number; color?: string; style?: React.CSSProperties}> = ({
  children,
  size = T.body,
  color = C.text2,
  style,
}) => (
  <div style={{fontFamily: FONT.sans, fontSize: size, lineHeight: 1.45, color, ...style}}>{children}</div>
);

export const Chip: React.FC<{children: React.ReactNode; accent?: string}> = ({children, accent = C.peacock}) => (
  <div
    style={{
      fontFamily: FONT.sans,
      fontSize: T.body,
      fontWeight: 600,
      color: C.text,
      padding: '12px 26px',
      borderRadius: 999,
      border: `1px solid ${accent}`,
      background: C.peacockWash,
      whiteSpace: 'nowrap',
    }}
  >
    {children}
  </div>
);

/** Thin progress rule along the bottom, so a muted viewer knows how long is left. */
export const Progress: React.FC<{total: number}> = ({total}) => {
  const frame = useCurrentFrame();
  const p = Math.min(1, frame / total);
  return (
    <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 4, background: C.rule}}>
      <div style={{width: `${p * 100}%`, height: '100%', background: C.peacock}} />
    </div>
  );
};
