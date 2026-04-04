import { registerRoot, Composition, AbsoluteFill, Audio, Video, staticFile } from 'remotion';
import { KineticSubtitle } from './components/SubtitleLayer';
import type { SubtitlePreset } from './components/SubtitleLayer';

interface MainCompositionProps {
  videoSrc: string;
  audioSrc?: string;
  captions: any[];
  preset: SubtitlePreset;
  durationInFrames: number;
  fps: number;
}

const MainComposition: React.FC<MainCompositionProps> = ({
  videoSrc,
  audioSrc,
  captions,
  preset,
}) => {
  // Use staticFile() to load video from public folder
  // This works because the video is in the public/ folder and gets bundled
  // The video filename is extracted from the absolute path
  const videoFilename = videoSrc.split('/').pop() || 'input_video.mp4';
  const videoSource = staticFile(videoFilename);
  
  console.log('[Remotion] Video source:', videoSource);
  console.log('[Remotion] Video filename:', videoFilename);
  
  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      {/* Video */}
      <Video
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

// Export Composition for Remotion CLI
export const RemotionRoot = () => {
  return (
    <Composition
      id="Main"
      component={MainComposition}
      durationInFrames={30 * 60}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};

// Register the root component
registerRoot(RemotionRoot);