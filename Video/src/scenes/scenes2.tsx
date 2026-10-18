import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {C, FONT, T} from '../brand';
import {Body, Eyebrow, Rise, SceneFade, Stage, Title} from '../components/ui';
import {AnimatedWeights} from '../components/charts';
import weights from '../../public/data/weights.json';

/* 6. CONVERGENCE -- the hero scene ------------------------------- 28s */
/** `at` is the frame each tenure is fully settled; the tween runs just before. */
const SCHEDULE = [
  {freq: '1mo', at: 95, label: 'Rebalanced monthly'},
  {freq: '3mo', at: 285, label: 'Rebalanced quarterly'},
  {freq: '6mo', at: 475, label: 'Rebalanced semiannually'},
  {freq: '1y', at: 665, label: 'Rebalanced annually'},
];
// Long tweens on purpose. With short ones the scene is four settled states
// separated by six seconds of stillness each; at 150 frames the allocations
// are visibly moving for most of the scene, which is the thing to watch.
const TWEEN = 150;
const SWEEP = 95;

const Stepper: React.FC<{active: number}> = ({active}) => (
  <div style={{display: 'flex', flexDirection: 'column', gap: 14}}>
    {SCHEDULE.map((t, i) => {
      const on = i === active;
      const done = i < active;
      return (
        <div key={t.freq} style={{display: 'flex', alignItems: 'center', gap: 16, opacity: on ? 1 : done ? 0.55 : 0.3}}>
          <div style={{width: 6, height: 34, borderRadius: 3, background: on ? C.glow : done ? C.peacock : C.ruleStrong}} />
          <div style={{fontFamily: FONT.sans, fontSize: on ? T.lead : T.body, fontWeight: on ? 700 : 500, color: on ? C.text : C.text3}}>
            {t.freq}
          </div>
        </div>
      );
    })}
  </div>
);

export const SceneConvergence: React.FC = () => {
  const frame = useCurrentFrame();
  let active = 0;
  SCHEDULE.forEach((sdl, i) => {
    if (frame >= sdl.at - TWEEN / 2) active = i;
  });
  return (
    <Stage>
      <SceneFade>
        <div style={{display: 'flex', gap: 44, height: '100%'}}>
          <div style={{width: 400, display: 'flex', flexDirection: 'column', gap: 24, flexShrink: 0}}>
            <Rise delay={0}>
              <Eyebrow>Why it matters less</Eyebrow>
            </Rise>
            <Rise delay={4}>
              <Title size={T.h2}>Different holdings, similar outcomes.</Title>
            </Rise>
            <Rise delay={10}>
              <Body size={T.body} style={{lineHeight: 1.5}}>
                One panel per risk proxy, same nine sectors plus cash. The four do not
                hold the same portfolio, at any rebalance interval.
              </Body>
            </Rise>
            <Rise delay={16}>
              <div style={{height: 1, background: C.rule}} />
            </Rise>
            <Stepper active={active} />
            <Rise delay={672} style={{marginTop: 'auto'}}>
              <div style={{borderLeft: `3px solid ${C.glow}`, paddingLeft: 20}}>
                <Body size={T.body} color={C.text} style={{lineHeight: 1.45}}>
                  Best schedule over worst: <strong style={{color: C.glow}}>1.60&times;</strong>
                </Body>
                <Body size={T.body} color={C.text} style={{lineHeight: 1.45}}>
                  Best proxy over worst: <strong style={{color: C.glow}}>1.23&times;</strong>
                </Body>
                <Body size={T.caption} color={C.text3} style={{lineHeight: 1.4, marginTop: 8}}>
                  Mean across the twelve budget-schedule cells.
                </Body>
              </div>
            </Rise>
          </div>

          <div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
            <AnimatedWeights
              data={weights as never}
              strategies={['Volatility', 'MAD', 'IQR', 'P95']}
              width={1240}
              height={760}
              schedule={SCHEDULE.map(({freq, at}) => ({freq, at}))}
              tweenFrames={TWEEN}
              sweepFrames={SWEEP}
            />
            <div
              style={{
                marginTop: 14,
                textAlign: 'center',
                fontFamily: FONT.sans,
                fontSize: T.caption,
                color: C.text3,
              }}
            >
              {SCHEDULE[active].label} &middot; 2000 to 2025 &middot; 10% risk budget
            </div>
          </div>
        </div>
      </SceneFade>
    </Stage>
  );
};

/* 7. THE CAVEAT --------------------------------------------------- 13s */
export const SceneCaveat: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: C.ground}}>
    <AbsoluteFill
      style={{
        background: `radial-gradient(1100px 650px at 50% 40%, rgba(224,168,143,.09), transparent 70%)`,
      }}
    />
    <div style={{position: 'relative', width: '100%', height: '100%', padding: 96, boxSizing: 'border-box'}}>
      <SceneFade>
        <div style={{display: 'flex', flexDirection: 'column', gap: 34, justifyContent: 'center', height: '100%'}}>
          <Rise delay={0}>
            <Eyebrow color={C.warn}>The caveat, and it stays in</Eyebrow>
          </Rise>
          <Rise delay={16}>
            <Title size={T.display} style={{maxWidth: 1560}}>
              The block-bootstrap intervals include zero.
            </Title>
          </Rise>
          <Rise delay={80}>
            <div style={{borderLeft: `3px solid ${C.warn}`, paddingLeft: 32, maxWidth: 1480}}>
              <Body size={T.lead} style={{lineHeight: 1.5}}>
                The point differences are large, but with so few non-overlapping long-horizon
                periods they are not uniformly distinguishable from zero.
              </Body>
            </div>
          </Rise>
          <Rise delay={150}>
            <Body size={T.body} color={C.text2} style={{maxWidth: 1540, lineHeight: 1.45}}>
              Resampling whole holding periods, rather than individual days, keeps the
              serial structure of returns intact. There are only so many non-overlapping
              long-horizon periods in 27 years, and that is what widens the interval.
            </Body>
          </Rise>
          <Rise delay={215}>
            <Body size={T.lead} color={C.text} style={{maxWidth: 1500, lineHeight: 1.4}}>
              So this is a <strong style={{color: C.warn}}>robust ordering of design choices</strong>, not a
              formally established dominance.
            </Body>
          </Rise>
        </div>
      </SceneFade>
    </div>
  </AbsoluteFill>
);

/* 8. THE READ + CLOSING CARD -------------------------------------- 14s */
export const SceneClose: React.FC = () => (
  <Stage>
    <div style={{display: 'flex', flexDirection: 'column', height: '100%', gap: 30}}>
      <Rise delay={0}>
        <Eyebrow>The practical read</Eyebrow>
      </Rise>
      <Rise delay={8}>
        <Title size={T.h1} style={{maxWidth: 1580}}>
          Operational decisions like rebalancing cadence probably deserve more attention
          than the risk metric people argue about.
        </Title>
      </Rise>

      <Rise delay={66}>
        <Body size={T.body} style={{maxWidth: 1580}}>
          The risk measure is the part of this that gets argued about. The schedule is the
          part that moved the outcome.
        </Body>
      </Rise>

      <div style={{marginTop: 'auto'}}>
        <Rise delay={120}>
          <div style={{height: 1, background: C.rule, marginBottom: 34}} />
        </Rise>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 60}}>
          <div style={{display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 1080}}>
            <Rise delay={140} y={14}>
              <div style={{fontFamily: FONT.serif, fontSize: T.lead, color: C.text, lineHeight: 1.25}}>
                Rebalancing Frequency Dominates Risk-Proxy Choice
              </div>
            </Rise>
            <Rise delay={168} y={14}>
              <div style={{fontFamily: FONT.sans, fontSize: T.body, color: C.text2}}>
                Siddhant Shah &middot; Aishwarya Malhotra &middot; Gourav Salotra &middot; Eugene Pinsky
              </div>
            </Rise>
            <Rise delay={196} y={14}>
              <div style={{fontFamily: FONT.sans, fontSize: T.caption, color: C.text3}}>
                Risks (MDPI) 14(10): 229 &middot; 2 October 2026 &middot; open access
              </div>
            </Rise>
          </div>
          <div style={{display: 'flex', flexDirection: 'column', gap: 12, textAlign: 'right'}}>
            <Rise delay={224} y={14}>
              <div style={{fontFamily: FONT.sans, fontSize: T.body, color: C.glow}}>doi.org/10.3390/risks14100229</div>
            </Rise>
            <Rise delay={248} y={14}>
              <div style={{fontFamily: FONT.sans, fontSize: T.caption, color: C.text3}}>
                github.com/SidShah2953/MAD-and-Quantile-Portfolios
              </div>
            </Rise>
          </div>
        </div>
      </div>
    </div>
  </Stage>
);
