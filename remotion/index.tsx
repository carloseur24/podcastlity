import { AbsoluteFill, Audio, Video } from 'remotion';
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

export const MainComposition: React.FC<MainCompositionProps> = ({
  videoSrc,
  audioSrc,
  captions,
  preset,
  durationInFrames,
  fps,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      {/* Video */}
      <Video
        src={videoSrc}
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

// Default props for development
export const defaultProps = {
  videoSrc: '',
  captions: [],
  preset: {
    name: 'Kinetic Pop',
    description: 'Default kinetic preset',
    engine: 'remotion',
    animation: {
      type: 'word_by_word' as const,
      entrance: 'pop_in',
      timing: 'sync_to_speech',
      combine_tokens_ms: 800,
      spring: { damping: 12, stiffness: 180 }
    },
    style: {
      font_family: 'Inter',
      font_size: 36,
      font_weight: 700,
      text_color: '#FFFFFF',
      stroke_color: '#000000',
      stroke_width: 2,
      background: 'rounded_box',
      bg_color: '#000000',
      bg_opacity: 0.7,
      padding_x: 24,
      padding_y: 16,
      border_radius: 12
    },
    position: {
      anchor: 'bottom_center',
      y_offset: 120
    },
    highlight: {
      enabled: true,
      color: '#FFD700',
      words: ['important', 'key', 'main']
    }
  },
  durationInFrames: 1800,
  fps: 30
};
