#!/usr/bin/env node

/**
 * Remotion Render Script
 * 
 * Renders video with kinetic subtitles using Remotion.
 * Called from Python pipeline stage.
 * 
 * Usage:
 *   node render.js <input_video> <output_video> <captions_json> <preset_json> <fps> <duration>
 * 
 * Example:
 *   node render.js input.mp4 output.mp4 captions.json preset.json 30 1800
 */

const { render } = require('@remotion/renderer');
const fs = require('fs');
const path = require('path');

// Register the composition
const { default: MainComposition, defaultProps } = require('./index.tsx');

async function renderVideo(inputPath, outputPath, captionsPath, presetPath, fps, duration) {
  console.log('[remotion] Starting render...');
  console.log('[remotion] Input:', inputPath);
  console.log('[remotion] Output:', outputPath);
  console.log('[remotion] Captions:', captionsPath);
  console.log('[remotion] Preset:', presetPath);
  console.log('[remotion] FPS:', fps, 'Duration:', duration);
  
  // Load captions
  const captions = JSON.parse(fs.readFileSync(captionsPath, 'utf8'));
  
  // Load preset
  const preset = JSON.parse(fs.readFileSync(presetPath, 'utf8'));
  
  // Calculate frame count
  const frameCount = Math.ceil(duration * fps);
  
  console.log('[remotion] Captions loaded:', captions.length);
  console.log('[remotion] Frame count:', frameCount);
  
  try {
    await render({
      component: MainComposition,
      props: {
        videoSrc: inputPath,
        captions: captions,
        preset: preset,
        durationInFrames: frameCount,
        fps: fps
      },
      outputPath: outputPath,
      config: {
        fps: fps,
        width: 1080,
        height: 1920,
        durationInFrames: frameCount
      }
    });
    
    console.log('[remotion] Render complete:', outputPath);
    process.exit(0);
  } catch (error) {
    console.error('[remotion] Render failed:', error);
    process.exit(1);
  }
}

// Parse arguments
const args = process.argv.slice(2);

if (args.length < 6) {
  console.error('Usage: node render.js <input> <output> <captions> <preset> <fps> <duration>');
  process.exit(1);
}

const [inputPath, outputPath, captionsPath, presetPath, fpsArg, durationArg] = args;
const fps = parseInt(fpsArg, 10);
const duration = parseFloat(durationArg);

renderVideo(inputPath, outputPath, captionsPath, presetPath, fps, duration);
