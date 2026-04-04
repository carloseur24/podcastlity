#!/usr/bin/env node

/**
 * Remotion Render Script
 * 
 * Renders video with kinetic subtitles using Remotion programmatic API.
 * Uses chromiumOptions.disableWebSecurity to allow loading local video files.
 * 
 * Usage:
 *   node render.js <input_video> <output_video> <captions_json> <preset_json> <fps> <duration> <width> <height>
 * 
 * Example:
 *   node render.js input.mp4 output.mp4 captions.json preset.json 30 55.78 1920 1080
 */

const fs = require('fs');
const path = require('path');

async function renderVideo(inputPath, outputPath, captionsPath, presetPath, fps, duration, width, height) {
  console.log('[remotion] Starting render...');
  console.log('[remotion] Input:', inputPath);
  console.log('[remotion] Output:', outputPath);
  console.log('[remotion] FPS:', fps, 'Duration:', duration, 'Resolution:', width, 'x', height);
  
  // Resolve all paths to absolute
  const inputPathAbs = path.resolve(inputPath);
  const outputPathAbs = path.resolve(outputPath);
  const captionsPathAbs = path.resolve(captionsPath);
  const presetPathAbs = path.resolve(presetPath);
  
  console.log('[remotion] Absolute paths:');
  console.log('[remotion]   Input:', inputPathAbs);
  console.log('[remotion]   Output:', outputPathAbs);
  console.log('[remotion]   Captions:', captionsPathAbs);
  console.log('[remotion]   Preset:', presetPathAbs);
  
  // Load captions and preset
  const captions = JSON.parse(fs.readFileSync(captionsPathAbs, 'utf8'));
  const preset = JSON.parse(fs.readFileSync(presetPathAbs, 'utf8'));
  const frameCount = Math.ceil(duration * fps);
  
  console.log('[remotion] Captions loaded:', captions.length);
  console.log('[remotion] Frame count:', frameCount);
  
  // Import Remotion modules
  const { renderMedia, selectComposition } = require('@remotion/renderer');
  
  // Use absolute file path - with disableWebSecurity, browser can access local files
  const videoSrc = inputPathAbs;
  
  const inputProps = {
    videoSrc: videoSrc,
    captions: captions,
    preset: preset,
    durationInFrames: frameCount,
    fps: fps,
    width: parseInt(width),
    height: parseInt(height)
  };
  
  console.log('[remotion] Input props videoSrc:', inputProps.videoSrc);
  
  try {
    // Bundle path - use the bundled output
    const bundlePath = path.join(__dirname, 'build');
    
    console.log('[remotion] Bundle path:', bundlePath);
    
    // Select the composition
    const composition = await selectComposition({
      serveUrl: bundlePath,
      id: 'Main',
      inputProps: inputProps,
    });
    
    console.log('[remotion] Composition selected:', composition.id, composition.durationInFrames, 'frames');
    
    console.log('[remotion] Rendering with disableWebSecurity...');
    
    // Render the media with security disabled
    await renderMedia({
      composition,
      serveUrl: bundlePath,
      outputLocation: outputPathAbs,
      inputProps,
      codec: 'h264',
      timeoutInMilliseconds: 300000, // 5 minute timeout for video loading
      // Key: disable web security to allow local file access
      chromiumOptions: {
        disableWebSecurity: true,
        allowFileAccessFromFiles: true,
        noSandbox: true,
        disableDevShmUsage: true,
      },
    });
    
    console.log('[remotion] Render complete!');
    
    // Check if output file exists
    if (fs.existsSync(outputPathAbs)) {
      const stats = fs.statSync(outputPathAbs);
      console.log('[remotion] Output file size:', stats.size, 'bytes');
    } else {
      console.log('[remotion] WARNING: Output file not found at:', outputPathAbs);
    }
    
  } catch (error) {
    console.error('[remotion] Render failed:', error.message);
    console.error('[remotion] Stack:', error.stack);
    throw error;
  }
}

// Parse arguments
const args = process.argv.slice(2);

if (args.length < 8) {
  console.error('Usage: node render.js <input> <output> <captions> <preset> <fps> <duration> <width> <height>');
  process.exit(1);
}

const [inputPath, outputPath, captionsPath, presetPath, fpsArg, durationArg, widthArg, heightArg] = args;
const fps = parseInt(fpsArg, 10);
const duration = parseFloat(durationArg);
const width = widthArg;
const height = heightArg;

renderVideo(inputPath, outputPath, captionsPath, presetPath, fps, duration, width, height);
