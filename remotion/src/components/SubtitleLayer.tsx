import React from 'react';
import { 
  AbsoluteFill, 
  useCurrentFrame, 
  useVideoConfig,
  staticFile
} from 'remotion';
import { createTikTokStyleCaptions } from '@remotion/captions';

// Load Poppins font from local public folder
const fontLoaded = (async () => {
  try {
    const { loadFont } = await import('@remotion/fonts');
    await loadFont({
      family: 'Poppins',
      url: staticFile('fonts/poppins.ttf'),
    });
    console.log('[SubtitleLayer] Poppins font loaded successfully');
  } catch (e) {
    console.log('[SubtitleLayer] Font load warning:', e.message);
  }
})();

// Types for preset configuration
interface SubtitlePreset {
  name: string;
  description: string;
  engine: string;
  animation: {
    type: 'word_by_word' | 'full_line';
    entrance?: string;
    animation_style?: string;
    timing?: string;
    combine_tokens_ms?: number;
    spring?: {
      damping: number;
      stiffness: number;
      mass?: number;
    };
    stagger_ms?: number;
    duration_ms?: number;
    easing?: string;
    enabled?: boolean;
  };
  style: {
    font_family: string;
    font_size: number;
    font_weight: number;
    text_color: string;
    stroke_color?: string;
    stroke_width?: number;
    shadow_color?: string;
    shadow_opacity?: number;
    shadow_blur?: number;
    shadow_offset?: number;
    background?: string | null;
    bg_color?: string;
    bg_opacity?: number;
    padding_x?: number;
    padding_y?: number;
    border_radius?: number;
  };
  position: {
    anchor: string;
    y_offset: number;
    margin_percent?: number;
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
  frameOffset?: number;
  outputWidth?: number;
  outputHeight?: number;
}

// Calculate font size - use preset value directly (4K baseline)
// No resolution-based scaling - font size is fixed from preset
function getScaledFontSize(baseSize: number, width: number, height: number): number {
  // Return preset's font_size directly - it's designed for 4K
  // The render resolution doesn't affect font size
  return baseSize;
}

export const KineticSubtitle: React.FC<KineticSubtitleProps> = ({ 
  captions, 
  preset,
  style,
  frameOffset = 0,
  outputWidth,
  outputHeight
}) => {
  // Guard against missing preset
  if (!preset) {
    console.log('[SubtitleLayer] WARNING: No preset provided!');
    return null;
  }
  
  // Debug: Log preset values
  console.log('[SubtitleLayer] Preset name:', preset.name);
  console.log('[SubtitleLayer] Preset font_family:', preset.style?.font_family);
  console.log('[SubtitleLayer] Preset font_size:', preset.style?.font_size);
  console.log('[SubtitleLayer] Preset text_color:', preset.style?.text_color);
  
  const { fps, width, height } = useVideoConfig();
  const combineTokensMs = preset.animation?.combine_tokens_ms || 300;
  
  // Use output dimensions if provided, otherwise fall back to video config
  // This ensures font scaling works correctly with the --scale option
  const renderWidth = outputWidth || width;
  const renderHeight = outputHeight || height;
  
  console.log('[SubtitleLayer] Render dimensions:', renderWidth, 'x', renderHeight);
  
  // Calculate scaled font size based on OUTPUT resolution (not internal)
  const baseFontSize = preset.style?.font_size || 32;
  console.log('[SubtitleLayer] Base font size:', baseFontSize);
  const scaledFontSize = getScaledFontSize(baseFontSize, renderWidth, renderHeight);
  console.log('[SubtitleLayer] Scaled font size:', scaledFontSize);
  
  // Create pages by grouping words
  const { pages } = React.useMemo(() => {
    return createTikTokStyleCaptions({
      captions,
      combineTokensWithinMilliseconds: combineTokensMs
    });
  }, [captions, combineTokensMs]);
  
  console.log('[SubtitleLayer] Pages created:', pages.length);
  
  const frame = useCurrentFrame();
  const adjustedFrame = frame;
  
  // Find active page - check each page's time range
  const activePage = pages.find((page: TikTokPage) => {
    const startFrame = (page.startMs / 1000) * fps;
    const endFrame = ((page.startMs + page.durationMs) / 1000) * fps;
    const isActive = adjustedFrame >= startFrame && adjustedFrame < endFrame;
    return isActive;
  });

  if (!activePage) {
    return null;
  }

  // Find the CURRENT token based on time
  const currentTimeMs = (adjustedFrame / fps) * 1000;
  
  // Find current token index
  const currentTokenIndex = activePage.tokens.findIndex(token => 
    token.fromMs <= currentTimeMs && currentTimeMs < token.toMs
  );
  
  // If no exact match, find the last token that started
  const fallbackIndex = activePage.tokens.reduce((prevIndex, curr, idx) => {
    if (curr.fromMs <= currentTimeMs) return idx;
    return prevIndex;
  }, 0);
  
  const activeIndex = currentTokenIndex !== -1 ? currentTokenIndex : fallbackIndex;
  
  // Get up to 2 words: current + 1 previous
  const wordsPerGroup = preset.animation?.words_per_group || 2;
  const displayTokens = [];
  
  for (let i = 0; i < wordsPerGroup; i++) {
    const tokenIndex = activeIndex - i;
    if (tokenIndex >= 0 && tokenIndex < activePage.tokens.length) {
      displayTokens.push(activePage.tokens[tokenIndex]);
    }
  }
  
  // Reverse so oldest word is first
  displayTokens.reverse();
  
  console.log('[SubtitleLayer] Active page:', activePage.text.substring(0, 20), 
    '| Words:', displayTokens.map(t => t.text).join(' '), 'at frame', adjustedFrame);

  if (displayTokens.length === 0) {
    return null;
  }
  
  return (
    <AbsoluteFill style={style}>
      <SubtitleWord 
        words={displayTokens}
        preset={preset}
        fontSize={scaledFontSize}
        renderWidth={renderWidth}
      />
    </AbsoluteFill>
  );
};

interface SubtitleWordProps {
  words: Array<{
    text: string;
    fromMs: number;
    toMs: number;
  }>;
  preset: SubtitlePreset;
  fontSize: number;
  renderWidth?: number;
}

const SubtitleWord: React.FC<SubtitleWordProps> = ({ 
  words, 
  preset,
  fontSize,
  renderWidth = 1920
}) => {
  const position = preset.position || { y_offset: 30 };
  
  // Use position directly - no adjustment needed
  const yOffset = position.y_offset;
  
  const presetStyle = preset.style || {};
  
  // Debug logging
  console.log('[SubtitleWord] Font family:', presetStyle.font_family);
  console.log('[SubtitleWord] Font size (raw):', presetStyle.font_size);
  console.log('[SubtitleWord] Font size (scaled):', fontSize);
  console.log('[SubtitleWord] Text color:', presetStyle.text_color);
  console.log('[SubtitleWord] Y offset:', yOffset);
  
  // Container - no background, centered on screen
  const animationStyle = preset.animation?.animation_style || 'ease_in_out';
  const marginPercent = position.margin_percent || 5;
  const safeMargin = Math.round(renderWidth * (marginPercent / 100));
  
  const containerStyle: React.CSSProperties = {
    position: 'absolute',
    bottom: yOffset,
    left: safeMargin,
    right: safeMargin,
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '8px',
    // No background - disabled by default
  };

  // Text style - use preset values with ease-in-out transition
  // Replace stroke with smooth shadow that looks like stroke
  const shadowColor = presetStyle.shadow_color || '#000000';
  const shadowOpacity = presetStyle.shadow_opacity !== undefined ? presetStyle.shadow_opacity : 0.5;
  const shadowBlur = presetStyle.shadow_blur !== undefined ? presetStyle.shadow_blur : 0;
  const shadowOffset = presetStyle.shadow_offset !== undefined ? presetStyle.shadow_offset : 1;
  
  // Convert hex to rgba for shadow
  const hexToRgba = (hex: string, alpha: number) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };
  
  // Create stroke-like shadow with minimal blur and offset
  const textStyle: React.CSSProperties = {
    fontFamily: `"Poppins", ${presetStyle.font_family || 'sans-serif'}`,
    fontSize: fontSize,
    fontWeight: presetStyle.font_weight || 600,
    color: presetStyle.text_color || '#FFFFFF',
    textShadow: `${shadowOffset}px ${shadowOffset}px ${shadowBlur}px ${hexToRgba(shadowColor, shadowOpacity)}`,
    textAlign: 'center',
    // Smooth ease-in-out transition for word changes
    transition: animationStyle === 'ease_in_out' ? 'all 0.15s ease-in-out' : 'none',
    // No background
  };
  
  // Combine words into a single display string
  const displayText = words.map(w => w.text).join(' ');
  
  console.log('[SubtitleWord] Display text:', displayText);
  
  return (
    <div style={containerStyle}>
      <span style={textStyle}>
        {displayText}
      </span>
    </div>
  );
};

export default KineticSubtitle;