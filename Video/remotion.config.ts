import {Config} from '@remotion/cli/config';

// PNG frames, not JPEG. JPEG frames make ffmpeg pick yuvj420p, the deprecated
// full-range pixel format; a player that ignores the range flag then treats it
// as limited range and crushes the #050C0F ground to black.
Config.setVideoImageFormat('png');
Config.setPixelFormat('yuv420p');
Config.setColorSpace('bt709');
// The stacked-area charts are dense, thin-banded and full of hard colour edges,
// which is the worst case for 4:2:0. CRF 16 keeps the band boundaries clean.
Config.setCrf(16);
Config.setOverwriteOutput(true);
Config.setConcurrency(4);
