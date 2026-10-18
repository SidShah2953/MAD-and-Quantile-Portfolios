import React from 'react';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {C, FONT, STRATEGY_COLORS as SC, T} from '../brand';
import {Body, Chip, Eyebrow, Rise, SceneFade, Stage, Title} from '../components/ui';
import {AnimatedCurves, AnimatedHeatmap} from '../components/charts';
import {AnimatedDispersion, AnimatedTimeline} from '../components/charts2';
import dispersion from '../../public/data/dispersion.json';
import heat from '../../public/data/heatmaps.json';
import curves from '../../public/data/pv_curves.json';

const Col: React.FC<{gap?: number; children: React.ReactNode; style?: React.CSSProperties}> = ({
  gap = 28,
  children,
  style,
}) => <div style={{display: 'flex', flexDirection: 'column', gap, height: '100%', ...style}}>{children}</div>;

/* 1. THE QUESTION ------------------------------------------------- 13s */
const Key: React.FC<{color: string; children: React.ReactNode}> = ({color, children}) => (
  <div style={{display: 'flex', alignItems: 'center', gap: 10}}>
    <div style={{width: 22, height: 12, background: color, borderRadius: 3}} />
    <span style={{fontFamily: FONT.sans, fontSize: T.caption, color: C.text2}}>{children}</span>
  </div>
);

export const SceneQuestion: React.FC = () => (
  <Stage>
    <SceneFade>
      <Col gap={22}>
        <Rise static>
          <Eyebrow>The question</Eyebrow>
        </Rise>
        <Rise static>
          <Title size={T.display} style={{maxWidth: 1560}}>
            Which risk measure should you optimise against?
          </Title>
        </Rise>
        <Rise delay={20}>
          <div style={{display: 'flex', gap: 16, flexWrap: 'wrap'}}>
            <Chip>Variance</Chip>
            <Chip>Mean absolute deviation</Chip>
            <Chip>Interquartile range</Chip>
            <Chip>Central 95% range</Chip>
          </div>
        </Rise>
        <Rise delay={52}>
          <Body size={T.lead} style={{maxWidth: 1560}}>
            All four ask how far returns scatter. They disagree most when the data is messy,
            because a handful of extreme days moves some of them far more than others.
          </Body>
        </Rise>
        <Rise delay={92} style={{marginTop: 'auto'}}>
          <div style={{display: 'flex', gap: 34, marginBottom: 10}}>
            <Key color={C.warn}>±2σ including outliers</Key>
            <Key color={C.glow}>±2σ with the 1.5×IQR outliers removed</Key>
          </div>
          <AnimatedDispersion
            data={dispersion as never}
            width={1728}
            height={366}
            start={120}
            sweepFrames={150}
            pinAt={200}
          />
          <Body size={T.caption} color={C.text3} style={{marginTop: 10}}>
            Daily returns of nine U.S. sector ETFs, pooled within each calendar half-year.
          </Body>
        </Rise>
        <Rise delay={326}>
          <Body size={T.body} color={C.text}>
            In 2020H1 the outliers alone inflate the estimate{' '}
            <strong style={{color: C.warn}}>1.68×</strong>. That inflated number is what the
            optimiser is handed.
          </Body>
        </Rise>
      </Col>
    </SceneFade>
  </Stage>
);

/* 2. THE TEST ----------------------------------------------------- 14s */
const Stat: React.FC<{n: string; label: string}> = ({n, label}) => (
  <div style={{display: 'flex', flexDirection: 'column', gap: 4}}>
    <div style={{fontFamily: FONT.serif, fontSize: T.stat, lineHeight: 1, color: C.glow}}>{n}</div>
    <div style={{fontFamily: FONT.sans, fontSize: T.caption, color: C.text3, letterSpacing: '.04em'}}>{label}</div>
  </div>
);

export const SceneTest: React.FC = () => (
  <Stage>
    <SceneFade>
      <Col gap={22}>
        <Rise delay={0}>
          <Eyebrow>The test</Eyebrow>
        </Rise>
        <Rise delay={5}>
          <Title size={T.h1} style={{maxWidth: 1560}}>
            Nine U.S. sector ETFs, under one identical set of constraints.
          </Title>
        </Rise>
        <Rise delay={28}>
          <div style={{display: 'flex', gap: 86}}>
            <Stat n="9" label="SECTOR ETFS" />
            <Stat n="~27" label="YEARS, 1999 TO 2025" />
            <Stat n="3" label="RISK BUDGETS" />
            <Stat n="4" label="REBALANCE SCHEDULES" />
          </div>
        </Rise>
        <Rise delay={68}>
          <div style={{display: 'flex', gap: 16, flexWrap: 'wrap'}}>
            <Chip accent={C.peacockLine}>Long-only</Chip>
            <Chip accent={C.peacockLine}>Fully invested</Chip>
            <Chip accent={C.peacockLine}>Allocation cap</Chip>
            <Chip accent={C.peacockLine}>Explicit cash sleeve</Chip>
          </div>
        </Rise>
        <Rise delay={106}>
          <Body size={T.lead} style={{maxWidth: 1600}}>
            Holding the constraints fixed is what makes the comparison mean anything.
            Otherwise implementation differences masquerade as differences between the
            measures themselves.
          </Body>
        </Rise>
        <Rise delay={150} style={{marginTop: 'auto'}}>
          <Body size={T.body} color={C.text}>
            And nothing is estimated on data the portfolio has already traded on:
          </Body>
          <div style={{marginTop: 14}}>
            <AnimatedTimeline width={1660} height={330} start={166} />
          </div>
        </Rise>
        <Rise delay={300}>
          <Body size={T.body} color={C.text} style={{maxWidth: 1600}}>
            Then vary two things independently: the{' '}
            <strong style={{color: C.glow}}>risk proxy</strong> and the{' '}
            <strong style={{color: C.glow}}>rebalancing schedule</strong>.
          </Body>
        </Rise>
      </Col>
    </SceneFade>
  </Stage>
);

/* 3. PORTFOLIO VALUE ----------------------------------------------- 7s */
export const SceneCurves: React.FC = () => (
  <Stage>
    <SceneFade>
      <Col gap={18}>
        <Rise delay={0}>
          <Eyebrow>The outcome</Eyebrow>
        </Rise>
        <Rise delay={4}>
          <Title size={T.h1}>Portfolio value, indexed to 100.</Title>
        </Rise>
        <Rise delay={8}>
          <Body size={T.body} style={{maxWidth: 1600}}>
            One panel per rebalance schedule, all four proxies and the benchmark inside each.
            The panels differ from each other far more than the lines differ within a panel.
          </Body>
        </Rise>
        <Rise delay={30} style={{marginTop: 6}}>
          <div style={{display: 'flex', gap: 30, flexWrap: 'wrap'}}>
            {['S&P 500', 'Volatility', 'MAD', 'IQR', 'P95'].map((n) => (
              <div key={n} style={{display: 'flex', alignItems: 'center', gap: 10}}>
                <div style={{width: 26, height: 4, background: SC[n], borderRadius: 2}} />
                <span style={{fontFamily: FONT.sans, fontSize: T.caption, color: C.text2}}>{n}</span>
              </div>
            ))}
          </div>
        </Rise>
        <div style={{marginTop: 'auto', marginBottom: 'auto'}}>
          <AnimatedCurves
            data={curves as never}
            freqs={['1mo', '3mo', '6mo', '1y']}
            width={1728}
            height={600}
            drawFrames={170}
          />
        </div>
      </Col>
    </SceneFade>
  </Stage>
);

/* 4. THE RESULT GRID ---------------------------------------------- 15s */
const Note: React.FC<{dot: string; children: React.ReactNode; delay: number}> = ({dot, children, delay}) => (
  <Rise delay={delay}>
    <div style={{display: 'flex', gap: 16, alignItems: 'baseline'}}>
      <div style={{width: 14, height: 14, borderRadius: 999, background: dot, flexShrink: 0, transform: 'translateY(-2px)'}} />
      <div style={{fontFamily: FONT.sans, fontSize: T.body, color: C.text2, lineHeight: 1.35}}>{children}</div>
    </div>
  </Rise>
);

const PV_PANELS = (heat.pvOrder as string[])
  .filter((n) => n !== 'S&P 500')
  .map((name) => ({name, grid: (heat.pv as never as Record<string, number[][]>)[name]}));
const PV_VALUES = PV_PANELS.flatMap((p) => p.grid.flat());

export const SceneResult: React.FC = () => (
  <Stage>
    <SceneFade>
      <Col gap={20}>
        <Rise delay={0}>
          <Eyebrow>The result</Eyebrow>
        </Rise>
        <Rise delay={4}>
          <Body size={T.caption} color={C.text3}>
            Terminal value of $100. Rows are risk budgets, columns are rebalance frequencies.
            Buy-and-hold S&amp;P 500 returns $469 throughout.
          </Body>
        </Rise>
        <div style={{marginTop: 10}}>
          <AnimatedHeatmap
            panels={PV_PANELS}
            risks={heat.risks as string[]}
            freqs={heat.freqs as string[]}
            vmin={Math.min(...PV_VALUES)}
            vmax={Math.max(...PV_VALUES)}
            width={1728}
            height={500}
            chromeAt={14}
            panelStart={[34, 196, 214, 232]}
            colStagger={22}
            cellDur={22}
            highlightRow={2}
            highlightFrom={130}
          />
        </div>
        <div style={{display: 'flex', flexDirection: 'column', gap: 16, marginTop: 14}}>
          <Note dot={C.glow} delay={132}>
            Move <strong style={{color: C.text}}>across a row</strong>, changing only the rebalance schedule: the numbers move a long way.
          </Note>
          <Note dot={C.peacock} delay={262}>
            Move <strong style={{color: C.text}}>between panels</strong>, changing only the risk proxy: the same pattern repeats.
          </Note>
        </div>
        <Rise delay={350} style={{marginTop: 'auto'}}>
          <Title size={T.h1} style={{maxWidth: 1600}}>
            Rebalancing cadence moved outcomes more than the risk proxy did.
          </Title>
        </Rise>
      </Col>
    </SceneFade>
  </Stage>
);

/* 5. DRAWDOWN ------------------------------------------------------ 8s */
const MDD_PANELS = (heat.mddOrder as string[]).map((name) => ({
  name,
  grid: (heat.mdd as never as Record<string, number[][]>)[name],
}));
const MDD_VALUES = MDD_PANELS.flatMap((p) => p.grid.flat());

export const SceneDrawdown: React.FC = () => (
  <Stage>
    <SceneFade>
      <Col gap={20}>
        <Rise delay={0}>
          <Eyebrow>And in drawdown</Eyebrow>
        </Rise>
        <Rise delay={4}>
          <Title size={T.h1}>The same ordering holds for maximum drawdown.</Title>
        </Rise>
        <Rise delay={10}>
          <Body size={T.body} style={{maxWidth: 1620}}>
            Worst peak-to-trough loss measured across the whole 27 years, not reset at each
            rebalance. Deeper is worse. The 6-month column is the mildest almost everywhere.
          </Body>
        </Rise>
        <div style={{marginTop: 'auto', marginBottom: 'auto'}}>
          <AnimatedHeatmap
            panels={MDD_PANELS}
            risks={heat.risks as string[]}
            freqs={heat.freqs as string[]}
            vmin={Math.min(...MDD_VALUES)}
            vmax={Math.max(...MDD_VALUES)}
            decimals={1}
            width={1728}
            height={560}
            chromeAt={10}
            panelStart={[26, 52, 78, 104]}
            colStagger={20}
            cellDur={24}
          />
        </div>
      </Col>
    </SceneFade>
  </Stage>
);
