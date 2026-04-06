#!/usr/bin/env node

console.log('Running CLI...');
const { renderVideo } = require('./src/render.js');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// CLI Colors
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m'
};

function log(color, ...args) {
  console.log(color, ...args, colors.reset);
}

// Get video duration using ffprobe
function getVideoDuration(videoPath) {
  try {
    const output = execSync(
      `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${videoPath}"`,
      { encoding: 'utf8' }
    );
    return parseFloat(output.trim());
  } catch (e) {
    log(colors.yellow, 'Warning: Could not detect video duration, using default');
    return null;
  }
}

// Get last caption timestamp from JSON
function getLastCaptionTime(captionsPath) {
  try {
    const captions = JSON.parse(fs.readFileSync(captionsPath, 'utf8'));
    if (!captions || captions.length === 0) return null;
    const lastCaption = captions[captions.length - 1];
    if (lastCaption.endMs) {
      return lastCaption.endMs / 1000;
    }
    return lastCaption.end || null;
  } catch (e) {
    return null;
  }
}

// Copy video to public folder for Remotion (file:// doesn't work with server-side rendering)
function copyVideoToPublic(inputPath) {
  const publicDir = path.join(__dirname, 'public');
  const videoFilename = path.basename(inputPath);
  const destPath = path.join(publicDir, videoFilename);
  
  // Check if already exists
  if (fs.existsSync(destPath)) {
    const srcStat = fs.statSync(inputPath);
    const destStat = fs.statSync(destPath);
    if (srcStat.size === destStat.size && srcStat.mtime <= destStat.mtime) {
      log(colors.dim, `Video already in public folder: ${videoFilename}`);
      return { filename: videoFilename, wasCopied: false };
    }
  }
  
  // Check file size (warn if > 500MB)
  const fileSizeMB = fs.statSync(inputPath).size / (1024 * 1024);
  if (fileSizeMB > 500) {
    log(colors.yellow, `Warning: Video is ${fileSizeMB.toFixed(1)}MB (> 500MB). This may be slow.`);
  }
  
  log(colors.cyan, `Copying video to public folder (${fileSizeMB.toFixed(1)}MB)...`);
  fs.copyFileSync(inputPath, destPath);
  
  // Update mtime to prevent unnecessary re-copies
  fs.utimesSync(destPath, new Date(), fs.statSync(inputPath).mtime);
  
  return { filename: videoFilename, wasCopied: true };
}

// Get video duration using ffprobe
function getVideoDuration(videoPath) {
  try {
    const output = execSync(
      `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${videoPath}"`,
      { encoding: 'utf8' }
    );
    return parseFloat(output.trim());
  } catch (e) {
    log(colors.yellow, 'Warning: Could not detect video duration, using default');
    return null;
  }
}

// Get last caption timestamp from JSON
function getLastCaptionTime(captionsPath) {
  try {
    const captions = JSON.parse(fs.readFileSync(captionsPath, 'utf8'));
    if (!captions || captions.length === 0) return null;
    // Captions have 'end' in seconds or 'endMs' in milliseconds
    const lastCaption = captions[captions.length - 1];
    if (lastCaption.endMs) {
      return lastCaption.endMs / 1000;
    }
    return lastCaption.end || null;
  } catch (e) {
    return null;
  }
}

// Resolution presets
const resolutions = {
  '144p': { width: 256, height: 144 },
  '240p': { width: 426, height: 240 },
  '360p': { width: 640, height: 360 },
  '480p': { width: 854, height: 480 },
  '720p': { width: 1280, height: 720 },
  '1080p': { width: 1920, height: 1080 },
  '1440p': { width: 2560, height: 1440 },
  '4k': { width: 3840, height: 2160 }
};

// Parse arguments
const args = process.argv.slice(2);
const options = {
  proxy: false,
  resolution: '480p',
  start: null,
  end: null,
  scale: null,
  output: null,
  input: null,
  captions: null,
  preset: null,
  help: false
};

// Parse flags
for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  switch (arg) {
    case '--proxy':
    case '-p':
      options.proxy = true;
      break;
    case '--resolution':
    case '-r':
      options.resolution = args[++i] || '480p';
      break;
    case '--start':
    case '-s':
      options.start = parseInt(args[++i]);
      break;
    case '--end':
    case '-e':
      options.end = parseInt(args[++i]);
      break;
    case '--scale':
      options.scale = parseFloat(args[++i]);
      break;
    case '--output':
    case '-o':
      options.output = args[++i];
      break;
    case '--help':
    case '-h':
      options.help = true;
      break;
    default:
      // Positional args
      if (!options.input) options.input = arg;
      else if (!options.captions) options.captions = arg;
      else if (!options.preset) options.preset = arg;
  }
}

// Show help
if (options.help) {
  log(colors.cyan, `
${colors.bright}Remotion Subtitle Renderer CLI${colors.reset}

${colors.yellow}Usage:${colors.reset}
  node cli.js <input_video> <captions_json> <preset_json> [options]

${colors.yellow}Options:${colors.reset}
  -p, --proxy           Use proxy mode (faster encoding)
  -r, --resolution     Resolution: 144p, 240p, 360p, 480p, 720p, 1080p, 4k (default: 480p)
  -s, --start N        Start second (default: 0)
  -e, --end N          End second (default: video duration)
  -o, --output N       Output filename
  -h, --help           Show this help

${colors.yellow}Examples:${colors.reset}
  # Quick proxy render at 480p (seconds 10-20)
  node cli.js input.mp4 caps.json preset.json -p -s 10 -e 20

  # Full quality 1080p render
  node cli.js input.mp4 caps.json preset.json -r 1080p

  # 4K render with range
  node cli.js input.mp4 caps.json preset.json -r 4k -s 5 -e 15

  # Custom scale (0.5 = half size)
  node cli.js input.mp4 caps.json preset.json --scale 0.5
`);
  process.exit(0);
}

// Validate required args
if (!options.input || !options.captions || !options.preset) {
  log(colors.yellow, 'Missing required arguments!');
  log(colors.cyan, 'Use: node cli.js <input> <captions> <preset> [options]');
  log(colors.cyan, 'Or: node cli.js --help for usage info');
  process.exit(1);
}

// Resolve paths
const inputPath = path.resolve(options.input);
const captionsPath = path.resolve(options.captions);
const presetPath = path.resolve(options.preset);

// Default output filename
if (!options.output) {
  const res = options.resolution.replace('p', 'p_').replace('4k', '4k');
  const range = options.start ? `_${options.start}-${options.end}` : '';
  options.output = `output/render_${res}${range}.mp4`;
}

const outputPath = path.resolve(options.output);

// Get resolution dimensions
const res = resolutions[options.resolution] || resolutions['480p'];
const width = res.width;
const height = res.height;

// Build render options
const renderOptions = {
  proxy: options.proxy,
  start: options.start,
  end: options.end,
  resolution: options.resolution,
  scale: options.scale
};

// Banner
log(colors.cyan, `
╔═══════════════════════════════════════════════════╗
║   ${colors.bright}Remotion Subtitle Renderer CLI${colors.reset}                    ║
╚═══════════════════════════════════════════════════╝
`);

// Show config
log(colors.green, '┌─ Configuration ─────────────────────────────────────┐');
log(colors.green, '│ '), log(colors.yellow, 'Input:     '), log(colors.reset, options.input);
log(colors.green, '│ '), log(colors.yellow, 'Output:     '), log(colors.reset, options.output);
log(colors.green, '│ '), log(colors.yellow, 'Resolution: '), log(colors.reset, options.resolution, ` (${width}x${height})`);
log(colors.green, '│ '), log(colors.yellow, 'Range:      '), log(colors.reset, options.start || 0, 's →', options.end ? options.end + 's' : 'end');
log(colors.green, '│ '), log(colors.yellow, 'Proxy:      '), log(colors.reset, options.proxy ? 'Yes (faster)' : 'No (quality)');
if (options.scale) {
  log(colors.green, '│ '), log(colors.yellow, 'Scale:      '), log(colors.reset, options.scale);
}
log(colors.green, '└──────────────────────────────────────────────────┘');

// Run render
log(colors.cyan, '\n▶ Starting render...\n');

// Calculate duration: use video duration or caption end time
let videoDuration = getVideoDuration(inputPath);
let captionDuration = getLastCaptionTime(captionsPath);

// Use the shorter of video/caption duration, default to 60s
let duration = 60;
if (videoDuration && captionDuration) {
  duration = Math.min(videoDuration, captionDuration);
  log(colors.dim, `Duration: video=${videoDuration.toFixed(1)}s, captions=${captionDuration.toFixed(1)}s, using=${duration.toFixed(1)}s`);
} else if (videoDuration) {
  duration = videoDuration;
  log(colors.dim, `Duration: video=${videoDuration.toFixed(1)}s`);
} else if (captionDuration) {
  duration = captionDuration;
  log(colors.dim, `Duration: captions=${captionDuration.toFixed(1)}s`);
}

renderVideo(
  inputPath,
  outputPath,
  captionsPath,
  presetPath,
  30, // fps
  Math.ceil(duration), // duration in seconds
  width,
  height,
  renderOptions
).then(() => {
  log(colors.green, '\n✅ Render complete!');
  log(colors.cyan, `Output: ${outputPath}\n`);
}).catch((err) => {
  log(colors.yellow, '\n❌ Render failed:', err.message);
  process.exit(1);
});
