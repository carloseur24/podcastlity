import { registerRoot, Composition, AbsoluteFill, Audio, OffthreadVideo, staticFile, getInputProps } from 'remotion';
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
}

// Inner component that can use hooks
const MainComposition: React.FC = () => {
  const inputProps = getInputProps<MainCompositionProps>();
  
  const { videoSrc, audioSrc, captions, preset } = inputProps;
  
  // Use staticFile() to load video from public folder
  const videoFilename = videoSrc?.split('/').pop() || 'input_video.mp4';
  const videoSource = staticFile(videoFilename);
  
  console.log('[Remotion] Video source:', videoSource);
  console.log('[Remotion] Video filename:', videoFilename);
  console.log('[Remotion] Captions count:', captions?.length || 0);
  
  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      {/* Video - Using OffthreadVideo for FFmpeg-based frame extraction */}
      <OffthreadVideo
        src={videoSource}
        style={{ width: '100%', height: '100%' }}
      />
      
      {/* Audio (if provided) */}
      {audioSrc && (
        <Audio src={audioSrc} />
      )}
      
      {/* Kinetic Subtitles */}
      <KineticSubtitle
        captions={captions}
        preset={preset}
      />
    </AbsoluteFill>
  );
};

// Get duration from input props for Composition
const getCompositionDuration = () => {
  const props = getInputProps<MainCompositionProps>();
  return props.durationInFrames || 30 * 60;
};

// Export Composition - duration will be set dynamically
export const RemotionRoot = () => {
  const durationInFrames = getCompositionDuration();
  const props = getInputProps<MainCompositionProps>();
  
  return (
    <Composition
      id="Main"
      component={MainComposition}
      durationInFrames={durationInFrames}
      fps={props.fps || 30}
      width={props.width || 1920}
      height={props.height || 1080}
    />
  );
};

// Register the root component
registerRoot(RemotionRoot);