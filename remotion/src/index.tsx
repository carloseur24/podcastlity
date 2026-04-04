import { registerRoot, Composition, AbsoluteFill, Audio, staticFile, getInputProps } from 'remotion';
import { Video } from '@remotion/media';
import { KineticSubtitle } from './components/SubtitleLayer';
import type { SubtitlePreset } from './components/SubtitleLayer';

interface MainCompositionProps {
  videoSrc: string;
  audioSrc?: string;
  captions: any[];
  preset: SubtitlePreset;
  durationInFrames: number;
  fps: number;
  width: number;
  height: number;
  frameOffset?: number;
  trimStartFrames?: number;
  outputWidth?: number;
  outputHeight?: number;
}

// Inner component that can use hooks
const MainComposition: React.FC = () => {
  const inputProps = getInputProps<MainCompositionProps>();
  
  const { videoSrc, audioSrc, captions, preset, trimStartFrames, outputWidth, outputHeight } = inputProps;
  
  const videoFilename = videoSrc?.split('/').pop() || 'input_video.mp4';
  const videoSource = staticFile(videoFilename);
  
  console.log('[Remotion] Video:', videoFilename, '| Trim:', trimStartFrames || 0, '| Captions:', captions?.length || 0);
  console.log('[Remotion] Output size:', outputWidth, 'x', outputHeight);
  
  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      {/* Using @remotion/media Video - WebCodecs-based, FASTEST */}
      <Video
        src={videoSource}
        trimBefore={trimStartFrames || 0}
        style={{ width: '100%', height: '100%' }}
      />
      
      {audioSrc && <Audio src={audioSrc} />}
      
      <KineticSubtitle
        captions={captions}
        preset={preset}
        outputWidth={outputWidth}
        outputHeight={outputHeight}
      />
    </AbsoluteFill>
  );
};

// Get duration from input props for Composition
const getCompositionDuration = () => {
  const props = getInputProps<MainCompositionProps>();
  return props.durationInFrames || 30 * 60;
};

// Export Composition - duration and dimensions from inputProps
export const RemotionRoot = () => {
  const durationInFrames = getCompositionDuration();
  const props = getInputProps<MainCompositionProps>();
  
  // Use dynamic dimensions from inputProps, fallback to 1920x1080
  const compositionWidth = props.width || 1920;
  const compositionHeight = props.height || 1080;
  
  console.log('[Remotion] Composition dimensions:', compositionWidth, 'x', compositionHeight);
  
  return (
    <Composition
      id="Main"
      component={MainComposition}
      durationInFrames={durationInFrames}
      fps={props.fps || 30}
      width={compositionWidth}
      height={compositionHeight}
    />
  );
};

// Register the root component
registerRoot(RemotionRoot);