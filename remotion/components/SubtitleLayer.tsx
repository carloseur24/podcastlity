import React from 'react';
import { 
  AbsoluteFill, 
  useCurrentFrame, 
  useVideoConfig, 
  interpolate,
  spring,
  Easing
} from 'remotion';
import { createTikTokStyleCaptions } from '@remotion/captions';

// Types for preset configuration
interface SubtitlePreset {
  name: string;
  description: string;
  engine: string;
  animation: {
    type: 'word_by_word' | 'full_line';
    entrance: string;
    timing: string;
    combine_tokens_ms: number;
    spring?: {
      damping: number;
      stiffness: number;
      mass?: number;
    };
    stagger_ms?: number;
    duration_ms?: number;
    easing?: string;
  };
  style: {
    font_family: string;
    font_size: number;
    font_weight: number;
    text_color: string;
    stroke_color?: string;
    stroke_width?: number;
    background?: string;
    bg_color?: string;
    bg_opacity?: number;
    padding_x?: number;
    padding_y?: number;
    border_radius?: number;
  };
  position: {
    anchor: string;
    y_offset: number;
  };
  highlight?: {
    enabled: boolean;
    color?: string;
    words?: string[];
  };
}

interface TikTokPage {
  text: string;
  startMs: number;
  durationMs: number;
  tokens: Array<{
    text: string;
    fromMs: number;
    toMs: number;
  }>;
}

interface KineticSubtitleProps {
  captions: any[];
  preset: SubtitlePreset;
  style?: React.CSSProperties;
}

export const KineticSubtitle: React.FC<KineticSubtitleProps> = ({ 
  captions, 
  preset,
  style 
}) => {
  const { fps } = useVideoConfig();
  
  // Create TikTok-style pages from captions
  const { pages } = React.useMemo(() => {
    return createTikTokStyleCaptions({
      captions,
      combineTokensWithinMilliseconds: preset.animation.combine_tokens_ms
    });
  }, [captions, preset.animation.combine_tokens_ms]);
  
  const frame = useCurrentFrame();
  
  // Calculate active page
  const activePage = pages.find((page: TikTokPage) => {
    const startFrame = (page.startMs / 1000) * fps;
    const endFrame = ((page.startMs + page.durationMs) / 1000) * fps;
    return frame >= startFrame && frame < endFrame;
  });
  
  if (!activePage) return null;
  
  return (
    <AbsoluteFill style={style}>
      <SubtitlePage 
        page={activePage} 
        preset={preset}
        globalFrame={frame}
        fps={fps}
      />
    </AbsoluteFill>
  );
};

interface SubtitlePageProps {
  page: TikTokPage;
  preset: SubtitlePreset;
  globalFrame: number;
  fps: number;
}

const SubtitlePage: React.FC<SubtitlePageProps> = ({ 
  page, 
  preset,
  globalFrame,
  fps
}) => {
  const { position, style: presetStyle, highlight } = preset;
  
  // Calculate position
  const containerStyle: React.CSSProperties = {
    position: 'absolute',
    bottom: position.y_offset,
    left: 0,
    right: 0,
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  };
  
  const textStyle: React.CSSProperties = {
    fontFamily: presetStyle.font_family,
    fontSize: presetStyle.font_size,
    fontWeight: presetStyle.font_weight,
    color: presetStyle.text_color,
    textAlign: 'center',
    padding: presetStyle.background ? 
      `${presetStyle.padding_y}px ${presetStyle.padding_x}px` : 0,
    backgroundColor: presetStyle.background ? 
      presetStyle.bg_color : 'transparent',
    background: presetStyle.background === 'gradient' ?
      `linear-gradient(135deg, ${presetStyle.bg_color}, #764BA2)` : undefined,
    opacity: presetStyle.bg_opacity,
    borderRadius: presetStyle.border_radius,
    WebkitTextStroke: presetStyle.stroke_width ? 
      `${presetStyle.stroke_width}px ${presetStyle.stroke_color}` : undefined,
  };
  
  if (preset.animation.type === 'full_line') {
    return (
      <div style={containerStyle}>
        <div style={textStyle}>
          {page.text}
        </div>
      </div>
    );
  }
  
  // Word-by-word animation
  return (
    <div style={containerStyle}>
      <div style={textStyle}>
        {page.tokens.map((token, index) => (
          <SubtitleWord
            key={`${token.fromMs}-${index}`}
            token={token}
            preset={preset}
            globalFrame={globalFrame}
            fps={fps}
          />
        ))}
      </div>
    </div>
  );
};

interface SubtitleWordProps {
  token: {
    text: string;
    fromMs: number;
    toMs: number;
  };
  preset: SubtitlePreset;
  globalFrame: number;
  fps: number;
}

const SubtitleWord: React.FC<SubtitleWordProps> = ({
  token,
  preset,
  globalFrame,
  fps
}) => {
  const startFrame = (token.fromMs / 1000) * fps;
  const endFrame = (token.toMs / 1000) * fps;
  const frame = globalFrame;
  
  const { animation, highlight, style } = preset;
  
  // Check if word should be highlighted
  const isHighlighted = highlight?.enabled && 
    highlight.words?.some(w => token.text.toLowerCase().includes(w.toLowerCase()));
  
  // Calculate animation based on entrance type
  let animatedStyle: React.CSSProperties = {};
  
  if (frame >= startFrame && frame < endFrame) {
    const progress = Math.min(1, (frame - startFrame) / ((endFrame - startFrame) / 3));
    
    if (animation.entrance === 'pop_in') {
      const scale = spring({
        frame: frame - startFrame,
        fps,
        config: animation.spring || { damping: 12, stiffness: 180 }
      });
      animatedStyle = {
        transform: `scale(${scale})`,
        opacity: interpolate(scale, [0, 1], [0, 1]),
        display: 'inline-block',
        marginRight: '4px',
      };
    } else if (animation.entrance === 'slide_in_left') {
      const translateX = interpolate(progress, [0, 1], [-50, 0]);
      const opacity = interpolate(progress, [0, 0.3], [0, 1]);
      animatedStyle = {
        transform: `translateX(${translateX}px)`,
        opacity,
        display: 'inline-block',
        marginRight: '4px',
      };
    } else if (animation.entrance === 'typewriter') {
      const opacity = interpolate(progress, [0, 0.5], [0, 1]);
      animatedStyle = {
        opacity,
        display: 'inline-block',
        marginRight: '4px',
      };
    } else {
      // Default: simple fade
      animatedStyle = {
        opacity: 1,
        display: 'inline-block',
        marginRight: '4px',
      };
    }
  } else if (frame >= endFrame) {
    animatedStyle = {
      opacity: 1,
      display: 'inline-block',
      marginRight: '4px',
    };
  } else {
    animatedStyle = {
      opacity: 0,
      display: 'inline-block',
      marginRight: '4px',
    };
  }
  
  const wordStyle: React.CSSProperties = {
    ...animatedStyle,
    color: isHighlighted ? highlight?.color : style.text_color,
    fontWeight: isHighlighted ? 700 : style.font_weight,
  };
  
  return <span style={wordStyle}>{token.text}</span>;
};

export default KineticSubtitle;
