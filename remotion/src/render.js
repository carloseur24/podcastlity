#!/usr/bin/env node

/**
 * Remotion Render Script
 * 
 * Renders video with kinetic subtitles using Remotion programmatic API.
 * Uses OffthreadVideo for FFmpeg-based frame extraction.
 * 
 * PROXY MODE: Use --proxy flag to render full video with faster encoding
 * 
 * RANGE MODE: Use --start and --end to render only a portion of the video
 *   - Perfect for quick iteration on specific segments
 *   - Example: --start 16 --end 48 renders only seconds 16-48
 * 
 * Usage:
 *   node render.js <input> <output> <captions> <preset> <fps> <total_duration> <width> <height> [options]
 * 
 * Options:
 *   --proxy           Faster encoding (higher CRF)
 *   --start <sec>    Start time in seconds
 *   --end <sec>      End time in seconds
 * 
 * Examples:
 *   node render.js input.mp4 output.mp4 caps.json preset.json 30 57 1920 1080
 *   node render.js input.mp4 output.mp4 caps.json preset.json 30 57 1920 1080 --proxy
 *   node render.js input.mp4 output.mp4 caps.json preset.json 30 57 1920 1080 --start 16 --end 48 --proxy
 */

const fs = require('fs');
const path = require('path');

async function renderVideo(inputPath, outputPath, captionsPath, presetPath, fps, duration, width, height, options = {}) {
  const startTime = Date.now();
  const isProxy = options.proxy || false;
  const rangeStart = options.start || null;
  const rangeEnd = options.end || null;
  const scale = options.scale || null;
  
  // Auto-bundle if needed (faster than separate build step)
  const bundlePath = path.join(__dirname, '../build');
  if (!fs.existsSync(bundlePath) || !fs.existsSync(path.join(bundlePath, 'bundle.js'))) {
    console.log('[remotion] ⚡ Auto-bundling (first run or missing bundle)...');
    const { execSync } = require('child_process');
    try {
      execSync('npx remotion bundle src/index.tsx Main --out-dir build', { 
        cwd: path.join(__dirname, '..'), 
        stdio: 'pipe'
      });
      console.log('[remotion] ✓ Bundle ready');
    } catch (e) {
      console.log('[remotion] Bundle warning:', e.message);
    }
  }
  
  // Calculate actual duration based on range
  let actualDuration = duration;
  let frameOffset = 0;
  
  // FIX: For range mode, we DON'T use frameOffset anymore
  // Instead we shift caption timestamps so they start at 0
  // This way output frames 0-960 correspond to caption timestamps 0-32000ms
  // NO frame offset needed - captions are already adjusted
  
  if (rangeStart !== null && rangeEnd !== null) {
    actualDuration = rangeEnd - rangeStart;
    frameOffset = 0; // FIXED: No frame offset, captions are shifted to 0
    console.log('[remotion] ════════════════════════════════════════════════════');
    console.log('[remotion] ⚡ RANGE MODE - Rendering seconds', rangeStart, 'to', rangeEnd);
    console.log('[remotion]    Output: 0s to', actualDuration, 's (no frame offset, captions shifted)');
    console.log('[remotion] ════════════════════════════════════════════════════');
  }
  
  console.log('[remotion] ════════════════════════════════════════════════════');
  console.log('[remotion] STARTING RENDER');
  if (isProxy) {
    console.log('[remotion] ⚡ PROXY MODE - Faster encoding');
  }
  console.log('[remotion] ════════════════════════════════════════════════════');
  console.log('[remotion] Input:', inputPath);
  console.log('[remotion] Output:', outputPath);
  console.log('[remotion] Duration:', actualDuration, 'seconds (original:', duration + ')');
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
  const allCaptions = JSON.parse(fs.readFileSync(captionsPathAbs, 'utf8'));
  const preset = JSON.parse(fs.readFileSync(presetPathAbs, 'utf8'));

  // Resolution modes: 480p (default proxy), 720p, 1080p (full)
  const isLowRes = isProxy;
  const resolutionMode = options.resolution || (isLowRes ? '480p' : '1080p');
  
  let outputWidth, outputHeight;
  switch(resolutionMode) {
    case '144p':
      outputWidth = 256;
      outputHeight = 144;
      break;
    case '480p':
      outputWidth = 854;
      outputHeight = 480;
      break;
    case '720p':
      outputWidth = 1280;
      outputHeight = 720;
      break;
    case '1080p':
    default:
      outputWidth = parseInt(width);
      outputHeight = parseInt(height);
  }
  
  console.log('[remotion] Resolution mode:', resolutionMode, '→', outputWidth, 'x', outputHeight);
  
  // Calculate effective output resolution based on scale
  let effectiveWidth = outputWidth;
  let effectiveHeight = outputHeight;
  if (scale !== null && scale > 0 && scale < 1) {
    // Round to integers to avoid validation errors
    effectiveWidth = Math.round(outputWidth * scale);
    effectiveHeight = Math.round(outputHeight * scale);
    console.log('[remotion] Scale factor:', scale, '→ effective output:', effectiveWidth, 'x', effectiveHeight);
  } else {
    console.log('[remotion] Scale: none (1.0)');
  }

  // Calculate trim for video start (NOT for captions - keep original timestamps!)
  const trimStartFrames = rangeStart !== null ? Math.floor(rangeStart * fps) : 0;
  console.log('[remotion] Video trim:', trimStartFrames, 'frames (at second', rangeStart + ')');

  // Filter captions for range AND SHIFT timestamps to start from 0
  // The output video starts at rangeStart, so captions must be relative to that
  let captions = allCaptions;
  if (rangeStart !== null && rangeEnd !== null) {
    const rangeStartMs = rangeStart * 1000;
    const rangeEndMs = rangeEnd * 1000;
    
    // Filter captions within range AND SHIFT timestamps to 0
    captions = allCaptions
      .filter(c => c.startMs >= rangeStartMs && c.startMs <= rangeEndMs)
      .map(c => ({
        ...c,
        // Shift timestamps so first caption starts at 0
        startMs: c.startMs - rangeStartMs,
        endMs: c.endMs - rangeStartMs,
        timestampMs: c.timestampMs - rangeStartMs
      }));
    
    console.log('[remotion] Filtered & shifted captions:', captions.length, '/', allCaptions.length, 'items');
    console.log('[remotion] First caption after shift:', captions[0]?.text, 'at', captions[0]?.startMs, 'ms');
    console.log('[remotion] Last caption after shift:', captions[captions.length-1]?.text, 'at', captions[captions.length-1]?.startMs, 'ms');
    console.log('[remotion] Range seconds:', rangeStart, 'to', rangeEnd);
  }

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
    width: outputWidth,
    height: outputHeight,
    frameOffset: frameOffset,
    trimStartFrames: trimStartFrames  // Frames to skip at video start
  };

  console.log('[remotion] ───────────────────────────────────────────────────');
  console.log('[remotion] Resolution:', outputWidth, 'x', outputHeight, isLowRes ? '(low-res proxy)' : '(full)');
  console.log('[remotion] Video filename for staticFile:', videoFilename);
  console.log('[remotion] DurationInFrames:', inputProps.durationInFrames);
  
  try {
    // Bundle path - use the bundled output
    const bundlePath = path.join(__dirname, '../build');
    
    console.log('[remotion] Bundle path:', bundlePath);
    console.log('[remotion] Bundle exists:', fs.existsSync(bundlePath));
    
    // Select the composition - pass the adaptive resolution
    console.log('[remotion] ───────────────────────────────────────────────────');
    console.log('[remotion] SELECTING COMPOSITION...');
    const composition = await selectComposition({
      serveUrl: bundlePath,
      id: 'Main',
      inputProps: {
        ...inputProps,
        // Use OUTPUT resolution for rendering (not internal full resolution)
        // This ensures font scaling matches the actual output
        width: effectiveWidth || parseInt(width),
        height: effectiveHeight || parseInt(height),
        // Pass output dimensions for subtitle scaling
        outputWidth: effectiveWidth || parseInt(width),
        outputHeight: effectiveHeight || parseInt(height)
      },
    });
    
    console.log('[remotion] ✓ Composition selected:', composition.id);
    console.log('[remotion]   Duration:', composition.durationInFrames, 'frames');
    console.log('[remotion]   FPS:', composition.fps);
    console.log('[remotion]   Size:', composition.width, 'x', composition.height);
    
    console.log('[remotion] ════════════════════════════════════════════════════');
    console.log('[remotion] RENDERING...');
    console.log('[remotion] ════════════════════════════════════════════════════');
    
    // Set ANGLE environment for GPU rendering (uses Windows GPU via WSL2)
    process.env.LIBGL_ALWAYS_SOFTWARE = '0';
    console.log('[remotion] GPU: Using ANGLE (DirectX backend via WSL2)');
    
    const renderStartTime = Date.now();
    
    // Render the media with progress tracking and memory optimization
    await renderMedia({
      composition,
      serveUrl: bundlePath,
      outputLocation: outputPathAbs,
      inputProps,
      codec: 'h264',
      crf: isProxy ? 28 : 23,
      // Scale down output resolution without changing internal rendering
      scale: scale !== null ? scale : 1,
      // Hardware acceleration - disabled by default on Linux (CRF not compatible)
      hardwareAcceleration: 'disabled',
      // Optimized concurrency for WSL2 (reduce overhead)
      concurrency: 4,
      // Progress callback - with NaN handling
      onProgress: (progress) => {
        if (isNaN(progress)) return;
        const elapsed = Date.now() - renderStartTime;
        const eta = elapsed / progress - elapsed;
        if (progress > 0) {
          console.log(`[remotion] Progress: ${(progress * 100).toFixed(1)}% | Elapsed: ${(elapsed/1000).toFixed(1)}s | ETA: ${(eta/1000).toFixed(1)}s`);
        }
      },
      // Start callback
      onStart: (data) => {
        console.log('[remotion] ───────────────────────────────────────────────────');
        console.log('[remotion] RENDER STARTED');
        console.log('[remotion]   Frame count:', data.frameCount);
        console.log('[remotion]   Concurrency:', data.resolvedConcurrency, '(MAX)');
        console.log('[remotion]   Resolution:', effectiveWidth, 'x', effectiveHeight);
        console.log('[remotion]   Scale:', scale !== null ? scale : 'none');
        console.log('[remotion]   Mode:', isProxy ? 'PROXY (CRF 28)' : 'FULL (CRF 23)');
        console.log('[remotion]   HW Accel:', 'if-possible');
      },
      timeoutInMilliseconds: 600000,
      // GPU acceleration using ANGLE (DirectX backend on Windows/WSL2)
      // This uses Windows GPU through WSL2's GPU virtualization
      chromiumArgs: [
        '--disable-gpu-sandbox',
        '--enable-gpu-rasterization',
        '--enable-zero-copy',
        '--ignore-gpu-blocklist',
        '--disable-software-rasterizer',
        '--enable-hardware-overlay',
        '--single-process',
        '--no-sandbox',
        // ANGLE DirectX - uses Windows GPU through WSL2
        '--use-gl=angle',
        '--enable-webgl',
        '--enable-accelerated-2d-canvas',
        '--enable-gpu-compositing',
        '--enable-features=VaapiVideoDecoder,LinuxExternalNativeVulkan',
        // Memory limits
        '--js-flags=--max-old-space-size=2048',
      ],
      chromiumOptions: {
        disableWebSecurity: true,
        noSandbox: true,
        disableDevShmUsage: false, // Use /dev/shm for better performance
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

// Only run CLI when executed directly (not imported)
if (require.main === module) {
  // Parse arguments
  const args = process.argv.slice(2);

if (args.length < 8) {
  console.error('Usage: node render.js <input> <output> <captions> <preset> <fps> <duration> <width> <height> [options]');
  console.error('');
  console.error('Options:');
  console.error('  --proxy              Faster encoding (higher CRF)');
  console.error('  --start <sec>        Start time in seconds');
  console.error('  --end <sec>          End time in seconds');
  console.error('  --resolution <mode>  Resolution: 144p, 480p (default for proxy), 720p, 1080p');
  console.error('');
  console.error('Examples:');
  console.error('  Full render:           node render.js input.mp4 output.mp4 caps.json preset.json 30 57 1920 1080');
  console.error('  Proxy mode (480p):    node render.js input.mp4 output.mp4 caps.json preset.json 30 57 1920 1080 --proxy');
  console.error('  Proxy 144p (fast):    node render.js input.mp4 output.mp4 caps.json preset.json 30 57 1920 1080 --proxy --resolution 144p');
  console.error('  Range mode:           node render.js input.mp4 output.mp4 caps.json preset.json 30 57 1920 1080 --start 16 --end 48');
  process.exit(1);
}

// Parse flags
let isProxy = false;
let rangeStart = null;
let rangeEnd = null;
let resolution = '480p'; // default for proxy

// Check for --proxy
const proxyIndex = args.indexOf('--proxy');
if (proxyIndex !== -1) {
  isProxy = true;
}

// Check for --resolution
const resIndex = args.indexOf('--resolution');
if (resIndex !== -1 && resIndex + 1 < args.length) {
  resolution = args[resIndex + 1];
}

// Check for --scale (downscale factor: 0.5 = half size, 0.25 = quarter, etc.)
const scaleIndex = args.indexOf('--scale');
let scale = null;
if (scaleIndex !== -1 && scaleIndex + 1 < args.length) {
  scale = parseFloat(args[scaleIndex + 1]);
}

// Check for --start
const startIndex = args.indexOf('--start');
if (startIndex !== -1 && startIndex + 1 < args.length) {
  rangeStart = parseFloat(args[startIndex + 1]);
}

// Check for --end
const endIndex = args.indexOf('--end');
if (endIndex !== -1 && endIndex + 1 < args.length) {
  rangeEnd = parseFloat(args[endIndex + 1]);
}

// Remove all flags from args to get positional arguments
const cleanArgs = args.filter(arg => 
  arg !== '--proxy' && 
  arg !== '--start' && 
  arg !== '--end' &&
  arg !== '--resolution' &&
  arg !== '--scale' &&
  (startIndex === -1 || args.indexOf(arg) !== startIndex + 1) &&
  (endIndex === -1 || args.indexOf(arg) !== endIndex + 1) &&
  (resIndex === -1 || args.indexOf(arg) !== resIndex + 1) &&
  (scaleIndex === -1 || args.indexOf(arg) !== scaleIndex + 1)
);

const [inputPath, outputPath, captionsPath, presetPath, fpsArg, durationArg, widthArg, heightArg] = cleanArgs;
const fps = parseInt(fpsArg, 10);
const duration = parseFloat(durationArg);
const width = widthArg;
const height = heightArg;

// Options
const options = {
  proxy: isProxy,
  start: rangeStart,
  end: rangeEnd,
  resolution: resolution,
  scale: scale
};

console.log('[remotion] Options:', JSON.stringify(options));

renderVideo(inputPath, outputPath, captionsPath, presetPath, fps, duration, width, height, options);
}

// Export for CLI
module.exports = { renderVideo };
