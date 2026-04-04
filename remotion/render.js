#!/usr/bin/env node

/**
 * Remotion Render Script
 * 
 * Renders video with kinetic subtitles using Remotion CLI.
 * Uses --public-dir for local video serving.
 * 
 * Usage:
 *   node render.js <input_video> <output_video> <captions_json> <preset_json> <fps> <duration> <width> <height>
 * 
 * Example:
 *   node render.js input.mp4 output.mp4 captions.json preset.json 30 55.78 1920 1080
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

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
  
  // Create public directory for static files
  const publicDir = path.join(__dirname, 'public');
  if (!fs.existsSync(publicDir)) {
    fs.mkdirSync(publicDir, { recursive: true });
  }
  
  // Copy video to public folder using absolute path
  const publicVideoPath = path.join(publicDir, 'input_video.mp4');
  if (!fs.existsSync(publicVideoPath) || fs.statSync(inputPathAbs).size !== fs.statSync(publicVideoPath).size) {
    fs.copyFileSync(inputPathAbs, publicVideoPath);
    console.log('[remotion] Copied video to public folder:', publicVideoPath);
  }
  
  console.log('[remotion] Public directory:', publicDir);
  console.log('[remotion] Video file:', publicVideoPath);
  console.log('[remotion] Video exists:', fs.existsSync(publicVideoPath));
  
  try {
    // Create input props - use relative path for public-dir mode
    const inputProps = {
      videoSrc: 'input_video.mp4',  // Relative path works with --public-dir
      captions: captions,
      preset: preset,
      durationInFrames: frameCount,
      fps: fps,
      width: parseInt(width),
      height: parseInt(height)
    };
    
    const inputPropsPath = path.join(__dirname, 'input-props.json');
    fs.writeFileSync(inputPropsPath, JSON.stringify(inputProps));
    
    // Output path
    console.log('[remotion] Output path:', outputPathAbs);
    
    // Run Remotion render with public directory for static files
    const cmd = [
      'npx', 'remotion', 'render',
      'index.tsx',
      'Main',
      outputPathAbs,
      '--props', inputPropsPath,
      '--codec', 'h264',
      '--crf', '23',
      '--audio-codec', 'aac',
      '--public-dir', publicDir,
      '--offline'
    ];
    
    console.log('[remotion] Running:', cmd.join(' '));
    
    // Run and capture output
    try {
      const result = execSync(cmd.join(' '), {
        cwd: __dirname,
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'pipe']
      });
      console.log('[remotion] Remotion output (first 2000 chars):', result.substring(0, 2000));
    } catch (error) {
      console.log('[remotion] Remotion stdout:', error.stdout ? error.stdout.substring(0, 2000) : 'None');
      console.log('[remotion] Remotion stderr:', error.stderr ? error.stderr.substring(0, 2000) : 'None');
      throw error;
    }
    
    // Check if output file exists
    if (fs.existsSync(outputPathAbs)) {
      const stats = fs.statSync(outputPathAbs);
      console.log('[remotion] Render complete - file size:', stats.size, 'bytes');
    } else {
      console.log('[remotion] WARNING: Output file not found at:', outputPathAbs);
    }
    
  } catch (error) {
    console.error('[remotion] Render failed:', error.message);
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