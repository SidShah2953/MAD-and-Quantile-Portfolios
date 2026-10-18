import React from 'react';
import {Composition} from 'remotion';
import {FPS} from './brand';
import {MadVideo, TOTAL} from './Video';

export const RemotionRoot: React.FC = () => (
  <Composition id="MadPaper" component={MadVideo} durationInFrames={TOTAL} fps={FPS} width={1920} height={1080} />
);
