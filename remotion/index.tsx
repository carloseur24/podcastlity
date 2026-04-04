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
  // Use staticFile() to properly serve local video files
  // videoSrc should be a relative path like "public/video.mp4"
  const videoSource = videoSrc.startsWith('/') || videoSrc.startsWith('http') 
    ? videoSrc 
    : staticFile(videoSrc);
  
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