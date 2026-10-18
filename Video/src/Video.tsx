import React from 'react';
import {AbsoluteFill} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {loadFont as loadSerif} from '@remotion/google-fonts/Newsreader';
import {loadFont as loadSans} from '@remotion/google-fonts/SchibstedGrotesk';
import {C} from './brand';
import {Progress} from './components/ui';
import {SceneCurves, SceneDrawdown, SceneQuestion, SceneResult, SceneTest} from './scenes/scenes';
import {SceneCaveat, SceneClose, SceneConvergence} from './scenes/scenes2';

loadSerif('normal', {weights: ['500'], subsets: ['latin'], ignoreTooManyRequestsWarning: true});
loadSans('normal', {weights: ['500', '600', '700'], subsets: ['latin'], ignoreTooManyRequestsWarning: true});

/**
 * Scenes crossfade rather than each fading out to an empty stage. Fading every
 * scene to nothing left a ~0.4s dip to the bare ground at all seven boundaries,
 * which made the piece read as separate slides instead of one object.
 */
export const TRANSITION = 18;

/** Scene order is the paper's argument, and must not be reordered. */
export const SCENES = [
  {id: 'question', Comp: SceneQuestion, hold: 420},
  {id: 'test', Comp: SceneTest, hold: 420},
  {id: 'curves', Comp: SceneCurves, hold: 240},
  {id: 'result', Comp: SceneResult, hold: 450},
  {id: 'drawdown', Comp: SceneDrawdown, hold: 240},
  {id: 'convergence', Comp: SceneConvergence, hold: 780},
  {id: 'caveat', Comp: SceneCaveat, hold: 300},
  {id: 'close', Comp: SceneClose, hold: 330},
] as const;

/**
 * A transition overlaps its neighbours rather than adding time, so each scene
 * carries TRANSITION extra frames to keep the hold the storyboard specifies.
 * Total = sum(hold + TRANSITION) - TRANSITION * (n - 1).
 */
export const TOTAL =
  SCENES.reduce((a, s) => a + s.hold + TRANSITION, 0) - TRANSITION * (SCENES.length - 1);

export const MadVideo: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: C.ground}}>
    <TransitionSeries>
      {SCENES.map(({id, Comp, hold}, i) => (
        <React.Fragment key={id}>
          {i > 0 ? (
            <TransitionSeries.Transition
              presentation={fade()}
              timing={linearTiming({durationInFrames: TRANSITION})}
            />
          ) : null}
          <TransitionSeries.Sequence durationInFrames={hold + TRANSITION}>
            <Comp />
          </TransitionSeries.Sequence>
        </React.Fragment>
      ))}
    </TransitionSeries>
    <Progress total={TOTAL} />
  </AbsoluteFill>
);
