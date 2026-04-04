#!/usr/bin/env node

/**
 * Remotion Render Script
 * 
 * Renders video with kinetic subtitles using Remotion programmatic API.
 * Uses OffthreadVideo for FFmpeg-based frame extraction.
 * 
 * PROXY MODE: Use --proxy flag to render full video with faster encoding
 *   - Renders entire video but with higher CRF (worse quality) for speed
 *   - Use --proxy for quick iteration checks
 * 
 * Usage:
 *   node render.js <input_video> <output_video> <captions_json> <preset_json> <fps> <duration> <width> <height> [--proxy]
 * 
 * Example:
 *   node render.js input.mp4 output.mp4 captions.json preset.json 30 57.78 1920 1080 --proxy
 */

const fs = require('fs');
const path = require('path');

async function renderVideo(inputPath, outputPath, captionsPath, presetPath, fps, duration, width, height, options = {}) {
  const startTime = Date.now();
  const isProxy = options.proxy || false;
  
  // In proxy mode, render full video but with faster encoding (higher CRF)
  const actualDuration = duration;
  
  console.log('[remotion] ════════════════════════════════════════════════════');
  console.log('[remotion] STARTING RENDER');
  if (isProxy) {
    console.log('[remotion] ⚡ PROXY MODE - Full duration, faster encoding');
  }
  console.log('[remotion] ════════════════════════════════════════════════════');
  console.log('[remotion] Input:', inputPath);
  console.log('[remotion] Output:', outputPath);
  console.log('[remotion] Duration:', duration, 'seconds');
  console.log('[remotion] FPS:', fps, 'Resolution:', width, 'x', height);
  
  // Resolve all paths to absolute
  const inputPathAbs = path.resolve(inputPath);
  const outputPathAbs = path.resolve(outputPath);
  const captionsPathAbs = path.resolve(captionsPath);
  const presetPathAbs = path.resolve(presetPath);
  
  console.log('[remotion] ───────────────────────────────────────────────────');
  console.log('[remotion] Absolute paths:');
  console.log('[remotion]   Input:', inputPathAbs);
  console.log('[remotion]   Output:', outputPathAbs);
  console.log('[remotion]   Captions:', captionsPathAbs);
  console.log('[remotion]   Preset:', presetPathAbs);
  
  // Load captions and preset
  const captions = JSON.parse(fs.readFileSync(captionsPathAbs, 'utf8'));
  const preset = JSON.parse(fs.readFileSync(presetPathAbs, 'utf8'));
  const frameCount = Math.ceil(actualDuration * fps);
  
  console.log('[remotion] ───────────────────────────────────────────────────');
  console.log('[remotion] Captions:', captions.length, 'items');
  console.log('[remotion] Frame count:', frameCount);
  console.log('[remotion] Preset:', preset.name || preset.animation?.type || 'unknown');
  
  // Log caption timing for debugging
  if (captions.length > 0) {
    console.log('[remotion] First caption:', captions[0].text, 'at', captions[0].startMs, 'ms');
    console.log('[remotion] Last caption:', captions[captions.length - 1].text, 'at', captions[captions.length - 1].startMs, 'ms');
    console.log('[remotion] Video duration:', duration * 1000, 'ms');
  }
  
  // Import Remotion modules
  const { renderMedia, selectComposition } = require('@remotion/renderer');
  
  // The video should be in public folder for staticFile to work
  const videoFilename = path.basename(inputPath);
  
  const inputProps = {
    videoSrc: videoFilename,
    captions: captions,
    preset: preset,
    durationInFrames: frameCount,
    fps: fps,
    width: parseInt(width),
    height: parseInt(height)
  };
  
  console.log('[remotion] ───────────────────────────────────────────────────');
  console.log('[remotion] Video filename for staticFile:', videoFilename);
  console.log('[remotion] DurationInFrames:', inputProps.durationInFrames);
  
  try {
    // Bundle path - use the bundled output
    const bundlePath = path.join(__dirname, 'build');
    
    console.log('[remotion] Bundle path:', bundlePath);
    console.log('[remotion] Bundle exists:', fs.existsSync(bundlePath));
    
    // Select the composition
    console.log('[remotion] ───────────────────────────────────────────────────');
    console.log('[remotion] SELECTING COMPOSITION...');
    const composition = await selectComposition({
      serveUrl: bundlePath,
      id: 'Main',
      inputProps: inputProps,
    });
    
    console.log('[remotion] ✓ Composition selected:', composition.id);
    console.log('[remotion]   Duration:', composition.durationInFrames, 'frames');
    console.log('[remotion]   FPS:', composition.fps);
    console.log('[remotion]   Size:', composition.width, 'x', composition.height);
    
    console.log('[remotion] ════════════════════════════════════════════════════');
    console.log('[remotion] RENDERING...');
    console.log('[remotion] ════════════════════════════════════════════════════');
    
    const renderStartTime = Date.now();
    
    // Render the media with progress tracking
    await renderMedia({
      composition,
      serveUrl: bundlePath,
      outputLocation: outputPathAbs,
      inputProps,
      codec: 'h264',
      crf: isProxy ? 28 : 23, // Higher CRF (worse quality) for proxy = faster
      // Progress callback
      onProgress: (progress) => {
        const elapsed = Date.now() - renderStartTime;
        const eta = elapsed / progress - elapsed;
        console.log(`[remotion] Progress: ${(progress * 100).toFixed(1)}% | Elapsed: ${(elapsed/1000).toFixed(1)}s | ETA: ${(eta/1000).toFixed(1)}s`);
      },
      // Start callback
      onStart: (data) => {
        console.log('[remotion] ───────────────────────────────────────────────────');
        console.log('[remotion] RENDER STARTED');
        console.log('[remotion]   Frame count:', data.frameCount);
        console.log('[remotion]   Concurrency:', data.resolvedConcurrency);
      },
      timeoutInMilliseconds: 600000, // 10 minute timeout
      chromiumOptions: {
        disableWebSecurity: true,
        noSandbox: true,
        disableDevShmUsage: true,
      },
    });
    
    const totalTime = Date.now() - startTime;
    const renderTime = Date.now() - renderStartTime;
    
    console.log('[remotion] ════════════════════════════════════════════════════');
    console.log('[remotion] ✓ RENDER COMPLETE');
    if (isProxy) {
      console.log('[remotion] ⚡ Proxy mode - faster encoding (CRF 28)');
    }
    console.log('[remotion] ════════════════════════════════════════════════════');
    console.log('[remotion] Total time:', (totalTime/1000).toFixed(2), 'seconds');
    console.log('[remotion] Render time:', (renderTime/1000).toFixed(2), 'seconds');
    
    // Check if output file exists
    if (fs.existsSync(outputPathAbs)) {
      const stats = fs.statSync(outputPathAbs);
      console.log('[remotion] Output file:', outputPathAbs);
      console.log('[remotion] Output size:', (stats.size / 1024 / 1024).toFixed(2), 'MB');
    } else {
      console.log('[remotion] WARNING: Output file not found at:', outputPathAbs);
    }
    
    return {
      success: true,
      isProxy,
      duration: actualDuration
    };
    
  } catch (error) {
    console.error('[remotion] ════════════════════════════════════════════════════');
    console.error('[remotion] ✗ RENDER FAILED');
    console.error('[remotion] ════════════════════════════════════════════════════');
    console.error('[remotion] Error:', error.message);
    console.error('[remotion] Stack:', error.stack);
    throw error;
  }
}

// Parse arguments
const args = process.argv.slice(2);

if (args.length < 8) {
  console.error('Usage: node render.js <input> <output> <captions> <preset> <fps> <duration> <width> <height> [--proxy]');
  console.error('Example (proxy mode - faster encoding): node render.js input.mp4 output.mp4 captions.json preset.json 30 57 1920 1080 --proxy');
  console.error('Example (full quality):                    node render.js input.mp4 output.mp4 captions.json preset.json 30 57 1920 1080');
  process.exit(1);
}

// Check for --proxy flag
const proxyIndex = args.indexOf('--proxy');
const isProxy = proxyIndex !== -1;

// Remove --proxy from args if present
const cleanArgs = isProxy ? args.slice(0, proxyIndex).concat(args.slice(proxyIndex + 1)) : args;

const [inputPath, outputPath, captionsPath, presetPath, fpsArg, durationArg, widthArg, heightArg] = cleanArgs;
const fps = parseInt(fpsArg, 10);
const duration = parseFloat(durationArg);
const width = widthArg;
const height = heightArg;

// Proxy mode options
const options = {
  proxy: isProxy
};

renderVideo(inputPath, outputPath, captionsPath, presetPath, fps, duration, width, height, options);
